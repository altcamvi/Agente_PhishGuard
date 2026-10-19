"""Módulo de PERCEPCIÓN: convierte un correo crudo (bytes RFC 822) en un percepto estructurado."""
import re
import html as htmllib
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from urllib.parse import urlparse

from .config import (TRUSTED_DOMAINS, BRAND_TOKENS, TRUSTED_BRANDS, TRUSTED_THIRD_PARTY, SHORTENERS,
                     SUSPICIOUS_TLDS, RISKY_EXT, TWO_LEVEL_SUFFIXES, URGENCY_TERMS, CREDENTIAL_TERMS, LEET)

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.I)
AUTH_RE = {k: re.compile(rf"{k}=(\w+)", re.I) for k in ("spf", "dkim", "dmarc")}
AUTH_VAL = {"pass": 0.0, "none": 0.5, "neutral": 0.5, "softfail": 0.8, "fail": 1.0}


class InvalidEmail(Exception):
    """La entrada no es un correo analizable."""


@dataclass
class Percept:
    email_id: str
    sender_domain: str
    url_hosts: list
    features: dict
    text: str
    degraded: bool = False
    notes: list = field(default_factory=list)


def reg_domain(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_LEVEL_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def is_trusted(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in TRUSTED_DOMAINS)


def brand_in_untrusted(host: str) -> bool:
    h = host.lower().translate(LEET)
    return (not is_trusted(host)) and any(t in h for t in BRAND_TOKENS)


def lookalike_ratio(host: str) -> float:
    r = reg_domain(host).translate(LEET)
    return max(SequenceMatcher(None, r, d).ratio() for d in TRUSTED_DOMAINS) if not is_trusted(host) else 0.0


def _body_and_attachments(msg):
    text, atts = "", []
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        try:
            text = body.get_content()
        except Exception:
            text = ""
        if body.get_content_type() == "text/html":
            hrefs = re.findall(r'href="([^"]+)"', text)
            text = htmllib.unescape(re.sub(r"<[^>]+>", " ", text)) + " " + " ".join(hrefs)
    for part in msg.iter_attachments():
        atts.append((part.get_filename() or "", len(part.get_payload(decode=True) or b"")))
    return text or "", atts


def perceive(raw: bytes, email_id: str) -> Percept:
    if not raw or not raw.strip():
        raise InvalidEmail("entrada vacía")
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as e:  # pragma: no cover
        raise InvalidEmail(f"no se pudo analizar: {e}")
    if not msg.keys():
        raise InvalidEmail("sin encabezados RFC 822")

    notes, degraded = [], False
    name, addr = parseaddr(str(msg.get("From", "")))
    host = addr.split("@")[-1].lower() if "@" in addr else ""
    if not host:
        notes.append("remitente ausente"); degraded = True
    subject = str(msg.get("Subject", "") or "")
    text_body, atts = _body_and_attachments(msg)
    text = f"{subject} {text_body}".strip()
    low = text.lower()
    text_nourl = URL_RE.sub(" ", text)   # las URLs se analizan con señales estructurales, no con TF-IDF

    auth_hdr = str(msg.get("Authentication-Results", "") or "")
    auth = {}
    for k, rx in AUTH_RE.items():
        m = rx.search(auth_hdr)
        auth[k] = AUTH_VAL.get(m.group(1).lower(), 0.5) if m else 0.5
    auth_missing = 0.0 if auth_hdr else 1.0
    if auth_missing:
        notes.append("sin encabezado de autenticación"); degraded = True

    reply = parseaddr(str(msg.get("Reply-To", "") or ""))[1]
    reply_host = reply.split("@")[-1].lower() if "@" in reply else ""

    urls = URL_RE.findall(text)
    uhosts, f_ip, f_short, f_mismatch, f_tld, f_lookalike, f_http, f_long, f_at = [], 0, 0, 0, 0, 0, 0, 0, 0
    for u in urls:
        try:
            p = urlparse(u)
        except ValueError:
            continue
        h = (p.hostname or "").lower()
        if not h:
            continue
        uhosts.append(h)
        f_ip += bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", h))
        f_short += reg_domain(h) in SHORTENERS
        ok_dest = (host and reg_domain(h) == reg_domain(host)) or reg_domain(h) in TRUSTED_THIRD_PARTY
        f_mismatch += not ok_dest
        f_tld += h.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS
        f_lookalike += brand_in_untrusted(h)
        f_http += p.scheme == "http"
        f_long += len(u) > 75
        f_at += "@" in u
    n = len(uhosts)

    risky_att = sum(1 for fn, _ in atts if any(fn.lower().endswith(e) for e in RISKY_EXT))
    disp_brand = any(b.lower() in name.lower() for b in TRUSTED_BRANDS) and not is_trusted(host)
    feats = {
        "spf": auth["spf"], "dkim": auth["dkim"], "dmarc": auth["dmarc"], "auth_missing": auth_missing,
        "sender_trusted": float(is_trusted(host)),
        "sender_brand_untrusted": float(brand_in_untrusted(host)),
        "sender_lookalike": lookalike_ratio(host) if host else 0.0,
        "sender_susp_tld": float(host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS) if host else 0.0,
        "display_brand_mismatch": float(disp_brand),
        "reply_to_mismatch": float(bool(reply_host) and reg_domain(reply_host) != reg_domain(host)
                                   and reg_domain(reply_host) not in TRUSTED_THIRD_PARTY),
        "n_urls": float(min(n, 5)),
        "url_ip": float(f_ip > 0), "url_shortener": float(f_short > 0),
        "url_mismatch": float(f_mismatch > 0), "url_susp_tld": float(f_tld > 0),
        "url_brand_untrusted": float(f_lookalike > 0), "url_http": float(f_http > 0),
        "url_long": float(f_long > 0), "url_at": float(f_at > 0),
        "n_risky_att": float(min(risky_att, 3)), "n_att": float(min(len(atts), 3)),
        "urgency_terms": float(min(sum(t in low for t in URGENCY_TERMS), 4)),
        "credential_terms": float(min(sum(t in low for t in CREDENTIAL_TERMS), 4)),
        "body_empty": float(len(text_body.strip()) == 0),
        "log_len": float(min(len(text_body), 20000)) ** 0.5 / 100,
    }
    return Percept(email_id, host, uhosts, feats, text_nourl[:20000], degraded, notes)


REASONS = {
    "spf": (lambda f: f["spf"] >= 0.8, "SPF falló"),
    "dkim": (lambda f: f["dkim"] >= 0.8, "DKIM falló"),
    "dmarc": (lambda f: f["dmarc"] >= 0.8, "DMARC falló"),
    "sender_brand_untrusted": (lambda f: f["sender_brand_untrusted"], "dominio del remitente imita una marca conocida"),
    "display_brand_mismatch": (lambda f: f["display_brand_mismatch"], "el nombre mostrado suplanta una marca pero el dominio no coincide"),
    "reply_to_mismatch": (lambda f: f["reply_to_mismatch"], "Reply-To apunta a un dominio distinto"),
    "url_ip": (lambda f: f["url_ip"], "enlace con dirección IP"),
    "url_shortener": (lambda f: f["url_shortener"], "enlace acortado"),
    "url_susp_tld": (lambda f: f["url_susp_tld"], "enlace con dominio de alto riesgo (TLD)"),
    "url_brand_untrusted": (lambda f: f["url_brand_untrusted"], "enlace imita una marca conocida"),
    "url_http": (lambda f: f["url_http"], "enlace sin HTTPS"),
    "n_risky_att": (lambda f: f["n_risky_att"] > 0, "adjunto con extensión riesgosa"),
    "urgency_terms": (lambda f: f["urgency_terms"] >= 1, "lenguaje de urgencia/presión"),
    "credential_terms": (lambda f: f["credential_terms"] >= 1, "solicita credenciales o datos sensibles"),
    "rep_bad": (lambda f: f.get("rep_sender", 0) >= 0.9 or f.get("rep_url_max", 0) >= 0.9, "dominio listado en la fuente de amenazas"),
}


def explain(features: dict) -> list:
    return [msg for _, (fn, msg) in REASONS.items() if fn(features)]
