#!/usr/bin/env python3
"""
Descarga de los corpus publicos (Hito 2). Nunca sube datos al repositorio: todo queda en data/raw/ (gitignored).

Uso:
  python download_data.py --list                          # muestra que archivos publica cada sitio
  python download_data.py --source spamassassin --accept-terms spamassassin
  python download_data.py --source all --accept-terms spamassassin,enron,nazario

Por que --accept-terms: las condiciones de uso se verifican en la pagina de cada fuente y UN INTEGRANTE debe
haberlas leido (ver data/README.md y docs/verificacion_fuentes.md). Sin ese indicador el script no descarga.

Los archivos se eligen a partir del indice de cada sitio (no por nombres fijos) y se registra SHA-256, tamano
y fecha en experiments/hito2/download_manifest.json (sin datos, solo metadatos; es evidencia para la bitacora).
Nigerian Fraud no tiene descarga automatica: colocar los archivos en data/raw/nigerian/ a mano.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "experiments" / "hito2" / "download_manifest.json"
UA = {"User-Agent": "PhishGuard-student-project/1.0 (academic research)"}

SOURCES = {
    "spamassassin": {
        "index": "https://spamassassin.apache.org/old/publiccorpus/",
        "pattern": r"^20030228_(easy_ham|easy_ham_2|hard_ham)\.tar\.bz2$",   # solo ham; el spam no es phishing
        "terms": "https://spamassassin.apache.org/old/publiccorpus/readme.html",
    },
    "enron": {
        "index": "https://www.cs.cmu.edu/~enron/",
        "pattern": r"^enron_mail_\d+\.tar\.gz$",
        "terms": "https://www.cs.cmu.edu/~enron/",
    },
    "nazario": {
        "index": "https://monkey.org/~jose/phishing/",
        "pattern": r"^phishing[\w.-]*$",
        "exclude": r"private|\.html?$|\.txt$",   # un tercero advierte que 'private-*' puede tener restricciones
        "terms": "https://monkey.org/~jose/phishing/",
    },
}


def fetch(url: str, timeout: int = 60, retries: int = 3) -> bytes:
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def list_index(index_url: str, pattern: str, exclude: str | None = None, include: str | None = None) -> list[str]:
    """Nombres de archivo enlazados en la pagina de indice que cumplen el patron."""
    html = fetch(index_url).decode("utf-8", errors="replace")
    names = []
    for href in re.findall(r'href="([^"#?]+)"', html, flags=re.I):
        name = href.rstrip("/").split("/")[-1]
        if href.endswith("/") or not name:
            continue
        if re.search(pattern, name) and not (exclude and re.search(exclude, name, re.I)) \
                and (include is None or re.search(include, name)):
            names.append(name)
    return sorted(set(names))


def download_file(url: str, dest: Path, timeout: int = 120) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r, open(part, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    part.replace(dest)
    return {"url": url, "file": dest.name, "bytes": size, "sha256": sha.hexdigest(),
            "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def download_source(name: str, index_url: str | None = None, raw_dir: Path = RAW, dry_run: bool = False,
                    include: str | None = None) -> list[dict]:
    cfg = SOURCES[name]
    index = index_url or cfg["index"]
    names = list_index(index, cfg["pattern"], cfg.get("exclude"), include)
    if not names:
        raise RuntimeError(f"{name}: el indice {index} no lista archivos que cumplan el patron "
                           f"{cfg['pattern']!r}. Revisar la pagina y ajustar SOURCES en download_data.py.")
    out = []
    for n in names:
        url = urljoin(index if index.endswith("/") else index + "/", n)
        dest = raw_dir / name / n
        if dry_run:
            print(f"  [simulacion] {url} -> {dest}")
            continue
        if dest.exists():
            print(f"  ya existe: {dest}")
            out.append({"url": url, "file": n, "bytes": dest.stat().st_size, "sha256": None, "note": "ya existia"})
            continue
        print(f"  descargando {url}")
        out.append(download_file(url, dest))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="all", help="spamassassin | enron | nazario | all")
    ap.add_argument("--list", action="store_true", help="solo listar los archivos que se descargarian")
    ap.add_argument("--accept-terms", default="", help="fuentes cuyos terminos ya leyo un integrante (separadas por coma)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--index-url", default=None, help="sustituye el indice (pruebas locales)")
    ap.add_argument("--include", default=None, help="regex extra sobre los nombres (p. ej. 'phishing-202[0-5]' para Nazario)")
    args = ap.parse_args(argv)

    names = list(SOURCES) if args.source == "all" else [args.source]
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        print(f"Fuente desconocida: {unknown}. Opciones: {list(SOURCES)}")
        return 2
    accepted = set(a.strip() for a in args.accept_terms.split(",") if a.strip())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    rc = 0
    for n in names:
        print(f"== {n}")
        if args.list or args.dry_run:
            try:
                for f in list_index(args.index_url or SOURCES[n]["index"], SOURCES[n]["pattern"], SOURCES[n].get("exclude"), args.include):
                    print("  ", f)
            except Exception as e:
                print(f"  no se pudo leer el indice: {e}")
                rc = 1
            continue
        if n not in accepted:
            print(f"  FALTA confirmar los terminos de uso. Abrir {SOURCES[n]['terms']}, leerlos, copiarlos a "
                  f"data/README.md y repetir con --accept-terms {n}")
            rc = 2
            continue
        try:
            manifest[n] = {"terms_url": SOURCES[n]["terms"], "terms_accepted": True,
                           "files": download_source(n, args.index_url, raw_dir=RAW, include=args.include)}
        except Exception as e:
            print(f"  ERROR: {e}")
            rc = 1
    if not (args.list or args.dry_run) and manifest:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"Manifiesto: {MANIFEST}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
