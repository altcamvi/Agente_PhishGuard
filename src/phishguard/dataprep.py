"""
PREPARACION DE DATOS (Hito 2): lectura de corpus reales, anonimizacion, deduplicacion,
particiones y resumenes. Solo usa la biblioteca estandar, numpy, pandas y scikit-learn.

Limitaciones declaradas (tambien en data/README.md):
- Los NOMBRES se anonimizan solo en encabezados (From/To/Reply-To). En el cuerpo no hay deteccion de
  nombres (no se usa NER); direcciones de correo y telefonos si se detectan por expresiones regulares.
- Los telefonos se detectan por patrones y pueden tener falsos positivos (p. ej. numeros de 10 digitos).
- La lista de marcadores de fuente (SOURCE_MARKERS) no es exhaustiva: despues de construir el conjunto hay que
  revisar `shortcut_tokens.csv`, que lista las palabras que mas separan las clases.
- La deteccion de idioma es una heuristica de palabras vacias (es/en), no un detector entrenado.
"""
from __future__ import annotations

import bz2
import gzip
import hashlib
import hmac
import json
import lzma
import os
import re
import tarfile
from collections import Counter
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formataddr, getaddresses
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
FRACTIONS = (0.70, 0.15, 0.15)
HASH_LEN = 8
MAX_RECIPIENTS = 20
MIN_STRATUM = 10          # estratos (clase|fuente) mas pequenos se estratifican solo por clase
SKIP_NAMES = {"cmds", "readme", "readme.txt", "manifest.json"}

# Encabezados que se conservan. El resto (Received, Message-ID, Date, X-*, ...) delata fuente o epoca.
KEEP_HEADERS = ("from", "reply-to", "to", "subject")

# Palabras que delatan la fuente; se sustituyen por un termino neutro. NO es exhaustiva.
SOURCE_MARKERS = (
    "enron", "spamassassin", "monkey.org", "nazario", "sourceforge", "listman.redhat.com",
    "exmh-workers", "razor-users", "spambayes", "zzzzteana", "irregulars",
)
# Un marcador dentro de un dominio/URL se cambia por uno de N dominios neutros (rotando) y en texto libre se borra.
# NO se usa un token unico: ese token apareceria solo en la clase legitima y seria un atajo por construccion.
NEUTRAL_POOL = 40

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RES = (
    re.compile(r"(?<![\w/.])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]\d{3,4}[\s.-]\d{3,4}(?![\w/.])"),
    re.compile(r"(?<![\w/.])\+?\d{10,13}(?![\w/.])"),
)

_ES = set("de la que el en y los se del las por un para con una su al es lo como mas más pero sus le ya "
          "este si sí porque esta entre cuando muy sin sobre tambien también me hasta hay donde quien desde "
          "todo nos durante todos uno les ni contra otros ese eso ante ellos esto antes algunos que qué unos "
          "yo otro otras otra el tanto esa estos mucho nada muchos cual poco ella estar estas algunas algo "
          "nosotros estimado cliente usted cuenta banco correo".split())
_EN = set("the of and to in is that it for was on are as with his they at be this from have or by one had "
          "not but what all were when we there can an your which their said if do will each about how up out "
          "them then she many some so these would other into has more her two like him see time could make "
          "than first been its who now people my made over did only way find use may very after where most "
          "know dear customer account bank email".split())
_BOTH = _ES & _EN
_ES, _EN = _ES - _BOTH, _EN - _BOTH
_WORD_RE = re.compile(r"[a-záéíóúñü]+")


# --------------------------------------------------------------------------- lectura

def _decompress(path: Path) -> bytes:
    n = path.name.lower()
    if n.endswith(".gz"):
        return gzip.open(path, "rb").read()
    if n.endswith(".bz2"):
        return bz2.open(path, "rb").read()
    if n.endswith(".xz"):
        return lzma.open(path, "rb").read()
    return path.read_bytes()


def split_mbox(data: bytes) -> list[bytes]:
    """Separa un mbox en mensajes. Una linea 'From ' abre un mensaje solo al inicio o tras una linea en blanco."""
    starts = []
    for m in re.finditer(rb"^From [^\n]*\n", data, re.M):
        p = m.start()
        if p == 0 or data[max(0, p - 2):p] == b"\n\n" or data[max(0, p - 4):p] == b"\r\n\r\n":
            starts.append((p, m.end()))
    if not starts:
        return [data]
    out = []
    for i, (_, body_start) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(data)
        out.append(data[body_start:end])
    return out


def iter_raw_messages(root: Path, include: str | None = None, exclude: str | None = None
                      ) -> Iterator[tuple[str, Callable[[], bytes]]]:
    """Recorre un directorio con carpetas, archivos sueltos, mbox o comprimidos (.tar.*, .gz, .bz2).
    Devuelve (nombre, lector). El lector de un miembro tar debe llamarse ANTES de pedir el siguiente."""
    inc = re.compile(include, re.I) if include else None
    exc = re.compile(exclude, re.I) if exclude else None

    def ok(name: str) -> bool:
        base = os.path.basename(name).lower()
        return (base not in SKIP_NAMES and not base.startswith(".")
                and (inc is None or inc.search(name) is not None)
                and not (exc and exc.search(name)))

    root = Path(root)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    for path in files:
        low = path.name.lower()
        if low.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
            with tarfile.open(path, "r|*") as tf:
                for m in tf:
                    name = f"{path.name}/{m.name}"
                    if m.isfile() and ok(name):
                        fobj = tf.extractfile(m)
                        yield name, (lambda f=fobj: f.read())
        else:
            name = str(path.relative_to(root)) if root.is_dir() else path.name
            if ok(name):
                yield name, (lambda p=path: _decompress(p))


def reservoir_sample(items: Iterable[tuple[str, Callable[[], bytes]]], k: int | None, seed: int = SEED
                     ) -> list[tuple[str, bytes]]:
    """Muestra aleatoria de k elementos leyendo solo los elegidos (sirve para el tar de Enron)."""
    rng = np.random.default_rng(seed)
    out: list[tuple[str, bytes]] = []
    for i, (name, read) in enumerate(items):
        if k is None or i < k:
            out.append((name, read()))
        else:
            j = int(rng.integers(0, i + 1))
            if j < k:
                out[j] = (name, read())
    return out


def expand_messages(pairs: Iterable[tuple[str, bytes]]) -> Iterator[tuple[str, bytes]]:
    """Cada archivo puede ser un correo o un mbox con varios."""
    for name, data in pairs:
        if data.startswith(b"From "):
            for i, part in enumerate(split_mbox(data)):
                yield f"{name}#{i}", part
        else:
            yield name, data


# --------------------------------------------------------------------------- anonimizacion

def load_salt(path: Path) -> bytes:
    """Sal para los hashes: variable PHISHGUARD_SALT, o un archivo local (gitignored) creado la primera vez."""
    env = os.environ.get("PHISHGUARD_SALT")
    if env:
        return env.encode()
    path = Path(path)
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(16).hex().encode()
    path.write_bytes(salt)
    return salt


def _dec_header(v) -> str:
    try:
        return str(make_header(decode_header(str(v))))
    except Exception:
        return str(v)


class Anonymizer:
    def __init__(self, salt: bytes, markers: Iterable[str] = SOURCE_MARKERS):
        self.salt = salt
        self.stats: Counter = Counter()
        self._markers = re.compile("|".join(re.escape(m) for m in markers), re.I)

    def _h(self, kind: str, value: str) -> str:
        return hmac.new(self.salt, f"{kind}:{value.lower()}".encode(), hashlib.sha256).hexdigest()[:HASH_LEN]

    def _email(self, m: re.Match) -> str:
        addr = m.group(0)
        _, _, domain = addr.rpartition("@")
        self.stats["emails"] += 1
        return f"u{self._h('e', addr)}@{domain}"

    def _marker(self, m: re.Match) -> str:
        s, a, b = m.string, m.start(), m.end()
        prev = s[a - 1] if a > 0 else ""
        nxt = s[b] if b < len(s) else ""
        self.stats["marcadores_fuente"] += 1
        if prev in "@./-" or nxt in "./":
            return f"org{self.stats['marcadores_fuente'] % NEUTRAL_POOL}"
        return ""

    def text(self, s: str) -> str:
        s = EMAIL_RE.sub(self._email, s)
        for rx in PHONE_RES:
            s, n = rx.subn("[TEL]", s)
            self.stats["telefonos"] += n
        return self._markers.sub(self._marker, s)

    def addresses(self, value: str) -> str:
        out = []
        for name, addr in getaddresses([_dec_header(value)])[:MAX_RECIPIENTS]:
            if not addr and not name:
                continue
            a = EMAIL_RE.sub(self._email, addr) if addr else ""
            n = ""
            if name:
                n = "N" + self._h("n", name)
                self.stats["nombres_encabezado"] += 1
            a = self._markers.sub(self._marker, a)
            out.append(formataddr((n, a)) if a else n)
        return ", ".join(out)

    def filename(self, name: str) -> str:
        """Cambia el nombre del adjunto pero conserva TODAS las extensiones (doble extension = rasgo de riesgo)."""
        parts = name.split(".")
        stem, exts = parts[0], parts[1:]
        self.stats["adjuntos"] += 1
        return ".".join([f"adj{self._h('f', stem)}"] + [e[:8] for e in exts[:3]])


def _decode_part(part) -> str:
    data = part.get_payload(decode=True)
    if data is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("latin-1", errors="replace")


def sanitize_message(raw: bytes, anon: Anonymizer) -> dict | None:
    """Convierte un correo crudo en un registro anonimizado, o None si no tiene contenido analizable."""
    try:
        msg = BytesParser(policy=policy.compat32).parsebytes(raw)
    except Exception:
        return None
    plain, html, attach = [], [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        fname = part.get_filename()
        if fname:
            attach.append((part.get_content_maintype(), part.get_content_subtype(), _dec_header(fname)))
        elif part.get_content_type() == "text/html":
            html.append(_decode_part(part))
        elif part.get_content_maintype() == "text":
            plain.append(_decode_part(part))
    body = "\n".join(plain).strip() or "\n".join(html).strip()
    use_html = not "\n".join(plain).strip() and bool(body)
    subject = anon.text(_dec_header(msg.get("Subject", "")).strip())
    if not body and not subject:
        return None
    body = anon.text(body)

    out = EmailMessage()
    for h in KEEP_HEADERS:
        v = msg.get(h)
        if v is None:
            continue
        val_sanitized = subject if h == "subject" else anon.addresses(v)
        out[h.title()] = val_sanitized.replace('\n', ' ').replace('\r', ' ') if isinstance(val_sanitized, str) else val_sanitized
    if "From" not in out:
        out["From"] = ""
    out.set_content(body if body else " ", subtype="html" if use_html else "plain", charset="utf-8")
    for maintype, subtype, fname in attach:
        out.add_attachment(b"", maintype=maintype or "application", subtype=subtype or "octet-stream",
                           filename=anon.filename(fname))
    text_body = re.sub(r"<[^>]+>", " ", body) if use_html else body
    return {
        "subject": subject,
        "text": (subject + "\n" + text_body).strip(),
        "raw": out.as_string(),
        "n_attachments": len(attach),
    }


def lang_guess(text: str) -> str:
    """Heuristica es/en/mixto/otro/desconocido por palabras vacias."""
    words = _WORD_RE.findall(text.lower())[:400]
    es = sum(w in _ES for w in words)
    en = sum(w in _EN for w in words)
    if es + en < 3:
        return "desconocido"
    if es > 1.5 * en:
        return "es"
    if en > 1.5 * es:
        return "en"
    return "mixto"


# --------------------------------------------------------------------------- construccion

def build_records(source: str, label: int, pairs: Iterable[tuple[str, bytes]], anon: Anonymizer) -> tuple[list, Counter]:
    rep: Counter = Counter()
    rows = []
    for name, raw in expand_messages(pairs):
        rep["leidos"] += 1
        rec = sanitize_message(raw, anon)
        if rec is None:
            rep["vacios_o_ilegibles"] += 1
            continue
        rec.update(id=f"{source}-{hashlib.sha1(raw).hexdigest()[:12]}", source=source, label=int(label),
                   lang=lang_guess(rec["text"]))
        rows.append(rec)
        rep["conservados"] += 1
    return rows, rep


def write_jsonl_gz(rows: list[dict], path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl_gz(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return pd.DataFrame([json.loads(line) for line in f])


# --------------------------------------------------------------------------- deduplicacion y particiones

def dedup_key(text: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", text.lower()).strip().encode("utf-8")).hexdigest()


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Elimina duplicados exactos (asunto+cuerpo normalizados). Si el mismo texto aparece con etiquetas
    distintas, se descartan todas sus copias (etiqueta contradictoria). Devuelve (df limpio, reporte)."""
    df = df.copy()
    df["_key"] = df["text"].map(dedup_key)
    conflict_keys = set(df.groupby("_key")["label"].nunique().loc[lambda s: s > 1].index)
    is_conflict = df["_key"].isin(conflict_keys)
    dup = df.duplicated("_key", keep="first") & ~is_conflict
    report = pd.concat([
        df[dup].groupby(["source", "label"]).size().rename("duplicados_exactos"),
        df[is_conflict].groupby(["source", "label"]).size().rename("etiqueta_contradictoria"),
    ], axis=1).fillna(0).astype(int).reset_index()
    clean = df[~dup & ~is_conflict].drop(columns="_key").reset_index(drop=True)
    return clean, report


_URL_RE = re.compile(r"https?://\S+")
NEAR_MIN_CHARS = 150


def near_key(text: str) -> str | None:
    """Clave de 'casi duplicado': minusculas, sin URLs, digitos ni signos, primeros 600 caracteres.
    Atrapa correos de la misma plantilla que solo cambian la URL, el nombre o un numero. Textos muy cortos
    (< 150 caracteres normalizados) no tienen clave: colisionarian por ser genericos ('gracias', 'ok')."""
    t = _URL_RE.sub(" ", text.lower())
    t = re.sub(r"[^a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.sha1(t[:600].encode("utf-8")).hexdigest() if len(t) >= NEAR_MIN_CHARS else None


def near_duplicate_report(df: pd.DataFrame) -> pd.DataFrame:
    """Por fuente y clase: cuantos correos comparten plantilla con otro. Si es alto, la particion al azar
    pondra copias casi identicas en train y en test y las metricas saldran infladas."""
    k = df["text"].map(near_key)
    shared = k.notna() & k.duplicated(keep=False)
    out = (pd.DataFrame({"source": df["source"], "label": df["label"], "con_clave": k.notna(), "en_plantilla_repetida": shared})
           .groupby(["source", "label"]).agg(correos=("label", "size"), con_clave=("con_clave", "sum"),
                                             en_plantilla_repetida=("en_plantilla_repetida", "sum")).reset_index())
    out["pct_en_plantilla_repetida"] = (100 * out["en_plantilla_repetida"] / out["correos"]).round(1)
    return out


def drop_near_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Deja un correo por plantilla; si una plantilla aparece con etiquetas distintas se descartan todas sus copias."""
    k = df["text"].map(near_key)
    has = k.notna()
    conflict = has & k.map(df.assign(_k=k).groupby("_k")["label"].nunique()).fillna(1).gt(1)
    dup = has & k.duplicated(keep="first") & ~conflict
    keep = ~dup & ~conflict
    return df[keep].reset_index(drop=True), int((~keep).sum())


def stratified_split(df: pd.DataFrame, seed: int = SEED, fractions=FRACTIONS) -> pd.Series:
    """70/15/15 estratificado por clase y fuente; estratos pequenos caen a estratificacion por clase."""
    assert abs(sum(fractions) - 1) < 1e-9
    strat = df["label"].astype(str) + "|" + df["source"]
    small = strat.map(strat.value_counts()) < MIN_STRATUM
    strat = strat.where(~small, df["label"].astype(str) + "|_otras")
    if strat.value_counts().min() < 4:
        raise ValueError("Hay estratos con menos de 4 correos; faltan datos para una particion 70/15/15.")
    idx = np.arange(len(df))
    tr, tmp = train_test_split(idx, test_size=1 - fractions[0], stratify=strat, random_state=seed)
    va, te = train_test_split(tmp, test_size=fractions[2] / (fractions[1] + fractions[2]),
                              stratify=strat.iloc[tmp], random_state=seed)
    out = pd.Series("", index=df.index, dtype=object)
    out.iloc[tr], out.iloc[va], out.iloc[te] = "train", "val", "test"
    return out


def loso_plan(df: pd.DataFrame) -> pd.DataFrame:
    """Plan de 'dejar una fuente fuera': que metrica se mide y si es calculable."""
    rows = []
    for src in sorted(df["source"].unique()):
        held = df[df["source"] == src]
        rest = df[df["source"] != src]
        label = int(held["label"].iloc[0])
        ok = rest["label"].nunique() == 2
        rows.append({
            "fuente_excluida": src, "clase": "phishing" if label else "legitimo",
            "metrica": "recall" if label else "FPR", "correos_excluidos": len(held),
            "calculable": bool(ok),
            "motivo": "" if ok else "sin la fuente solo queda una clase para entrenar",
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- resumenes

def summarize(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    out["conteo_por_fuente_clase"] = (df.groupby(["source", "label"]).size().rename("correos").reset_index())
    out["balance_clases"] = (df["label"].map({0: "legitimo", 1: "phishing"}).value_counts()
                             .rename_axis("clase").rename("correos").reset_index())
    out["idioma_por_fuente"] = (df.groupby(["source", "lang"]).size().rename("correos").reset_index())
    lens = df["text"].str.len()
    out["longitud_texto"] = (lens.groupby([df["source"], df["label"]])
                             .describe()[["count", "mean", "50%", "max"]].round(1).reset_index())
    out["adjuntos_por_fuente"] = (df.groupby("source")["n_attachments"].agg(["mean", "max"]).round(3).reset_index())
    if "split" in df:
        out["particion"] = (df.groupby(["split", "label"]).size().rename("correos").reset_index())
    return out


def shortcut_tokens(df: pd.DataFrame, k: int = 30, min_df: int = 20) -> pd.DataFrame:
    """Palabras que mas separan las clases (log-odds por frecuencia de documento). Sirve para detectar atajos
    (nombres de fuente, de epoca, de una bandeja) que el modelo aprenderia en vez de aprender phishing."""
    from sklearn.feature_extraction.text import CountVectorizer
    cv = CountVectorizer(binary=True, min_df=min_df, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9_]{2,}\b",
                         lowercase=True, max_features=50000)
    X = cv.fit_transform(df["text"])
    y = df["label"].to_numpy()
    p1 = (np.asarray(X[y == 1].sum(0)).ravel() + 1) / ((y == 1).sum() + 2)
    p0 = (np.asarray(X[y == 0].sum(0)).ravel() + 1) / ((y == 0).sum() + 2)
    lo = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))
    tokens = np.array(cv.get_feature_names_out())
    order = np.argsort(-np.abs(lo))[:k]
    return pd.DataFrame({"token": tokens[order], "log_odds_phishing_vs_legitimo": lo[order].round(2),
                         "df_phishing": np.round(p1[order], 4), "df_legitimo": np.round(p0[order], 4)})
