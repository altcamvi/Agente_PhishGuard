"""
Modulo de PERCEPCION: convierte un correo crudo en un vector de rasgos (componente IBM: Percepcion).
"""
import re, math, unicodedata, email
from email import policy
from email.utils import parseaddr
from urllib.parse import urlparse
from .constants import *

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.I)
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
SECOND_LEVEL = {"com", "edu", "org", "gov", "net", "co"}

FEATURE_NAMES = [
    "spf_pass", "spf_fail", "dkim_pass", "dkim_fail", "dmarc_pass", "dmarc_fail", "auth_missing",
    "from_free_provider", "display_brand_mismatch", "reply_to_mismatch", "sender_lookalike",
    "sender_digits", "sender_susp_tld", "sender_internal",
    "n_urls", "url_ip", "url_shortener", "url_at", "url_susp_tld", "url_lookalike", "url_free_hosting",
    "url_frac_differs", "url_max_len", "url_http",
    "urgency_count", "credential_count", "money_count",
    "n_attach", "attach_risky", "attach_double_ext",
    "rep_sender", "rep_url_max", "rep_sender_ok", "rep_url_ok",
]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def registered_domain(host):
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_lookalike(domain):
    """Parecido (pero no igual) a un dominio de marca conocida."""
    if domain in BRANDS.values():
        return False
    label = domain.split(".")[0].replace("-secure", "").replace("1", "l").replace("0", "o").replace("rn", "m")
    for b in BRANDS.values():
        bl = b.split(".")[0]
        if levenshtein(label, bl) <= 1 and domain.split(".")[0] != bl:
            return True
        if bl in domain.split(".")[0] and domain != b and not domain.endswith("." + b):
            return True
    return False


def parse_auth(msg):
    res = str(msg.get("Authentication-Results", "") or "").lower()
    out = {}
    for k in ("spf", "dkim", "dmarc"):
        m = re.search(rf"{k}=(\w+)", res)
        out[k] = m.group(1) if m else None
    return out, bool(res)


def get_text(msg):
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return None
    txt = body.get_content()
    if body.get_content_type() == "text/html":
        txt = re.sub(r"<[^>]+>", " ", txt)
    return txt


def parse_email(raw):
    """Devuelve (msg, error). error != None indica entrada invalida (sensor sin dato / formato roto)."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str) or not raw.strip():
        return None, "entrada vacia o de tipo no valido"
    msg = email.message_from_string(raw[:MAX_CHARS], policy=policy.default)
    frm = msg.get("From")
    if not frm:
        return None, "correo sin encabezado From"
    name, addr = parseaddr(str(frm))
    if "@" not in addr or not addr.split("@")[1]:
        return None, "remitente malformado"
    atts = [p.get_filename() for p in msg.walk() if p.get_filename()]
    text = get_text(msg)
    if (text is None or not text.strip()) and not atts:
        return None, "correo sin cuerpo ni adjuntos"
    return msg, None


def extract(msg, rep_tool):
    """Extrae rasgos de un mensaje valido. rep_tool: ReputationTool (puede devolver None si el servicio cae)."""
    name, addr = parseaddr(str(msg["From"]))
    sdom = addr.split("@")[1].lower()
    sreg = registered_domain(sdom)
    auth, has_auth = parse_auth(msg)
    text = get_text(msg) or ""
    norm = strip_accents((str(msg.get("Subject", "")) + " " + text).lower())
    urls = URL_RE.findall(text)
    atts = [a.lower() for a in (p.get_filename() for p in msg.walk()) if a]

    hosts = []
    for u in urls:
        try: hosts.append((urlparse(u).hostname or "").lower())
        except ValueError: hosts.append("")
    regs = [registered_domain(h) for h in hosts if h]
    reply = parseaddr(str(msg.get("Reply-To", "")))[1]
    brand_in_name = any(b.lower() in name.lower() for b in BRANDS)
    brand_dom_ok = any(sreg == d or sdom.endswith("." + d) for d in BRANDS.values())

    # Reputacion: planificacion -> primero el remitente; luego (bucle) los dominios de las URLs
    rep_s = rep_tool.lookup(sreg)
    rep_urls, url_ok = [], 1
    if regs:
        for d in sorted(set(regs))[:5]:
            v = rep_tool.lookup(d)
            if v is None: url_ok = 0
            else: rep_urls.append(v)
    f = {
        "spf_pass": auth["spf"] == "pass", "spf_fail": auth["spf"] in ("fail", "softfail"),
        "dkim_pass": auth["dkim"] == "pass", "dkim_fail": auth["dkim"] == "fail",
        "dmarc_pass": auth["dmarc"] == "pass", "dmarc_fail": auth["dmarc"] == "fail",
        "auth_missing": not has_auth,
        "from_free_provider": sreg in FREE_PROVIDERS,
        "display_brand_mismatch": brand_in_name and not brand_dom_ok,
        "reply_to_mismatch": bool(reply) and registered_domain(reply.split("@")[-1]) != sreg,
        "sender_lookalike": is_lookalike(sreg),
        "sender_digits": any(c.isdigit() for c in sreg.split(".")[0]),
        "sender_susp_tld": sreg.split(".")[-1] in SUSPICIOUS_TLDS,
        "sender_internal": sreg == INTERNAL_DOMAIN,
        "n_urls": min(len(urls), 10),
        "url_ip": any(IP_RE.match(h) for h in hosts),
        "url_shortener": any(r in SHORTENERS for r in regs),
        "url_at": any("@" in u.split("//", 1)[-1].split("/")[0] for u in urls),
        "url_susp_tld": any(r.split(".")[-1] in SUSPICIOUS_TLDS for r in regs),
        "url_lookalike": any(is_lookalike(r) for r in regs),
        "url_free_hosting": any(r in FREE_HOSTING for r in regs),
        "url_frac_differs": (sum(r != sreg for r in regs) / len(regs)) if regs else 0.0,
        "url_max_len": max((len(u) for u in urls), default=0) / 100.0,
        "url_http": any(u.lower().startswith("http://") for u in urls),
        "urgency_count": sum(w in norm for w in URGENCY_WORDS),
        "credential_count": sum(w in norm for w in CREDENTIAL_WORDS),
        "money_count": sum(w in norm for w in MONEY_WORDS),
        "n_attach": len(atts),
        "attach_risky": any(a.rsplit(".", 1)[-1] in RISKY_EXT for a in atts if "." in a),
        "attach_double_ext": any(a.count(".") >= 2 for a in atts),
        "rep_sender": 0.5 if rep_s is None else rep_s,
        "rep_url_max": max(rep_urls) if rep_urls else 0.5,
        "rep_sender_ok": rep_s is not None, "rep_url_ok": bool(url_ok),
    }
    vec = [float(f[k]) for k in FEATURE_NAMES]
    meta = {"sender": addr, "sender_domain": sreg, "urls": urls[:5], "attachments": atts, "auth": auth}
    return vec, f, meta
