#!/usr/bin/env python3
"""
Lee data/raw/<fuente>/ y escribe data/processed/emails.jsonl.gz con los correos ANONIMIZADOS
(direcciones y nombres de encabezado con hash HMAC, telefonos enmascarados, encabezados que delatan fuente o
epoca eliminados, adjuntos vaciados conservando extensiones).

  python anonymize.py                      # todas las fuentes presentes en data/raw/
  python anonymize.py --sources enron      # solo una

Salidas: data/processed/emails.jsonl.gz (gitignored) y experiments/hito2/anonymization_report.json (solo conteos).
La sal de los hashes se toma de PHISHGUARD_SALT o de data/processed/.salt (gitignored); no se comparte.
Limitaciones (nombres en el cuerpo sin detectar, falsos positivos de telefonos): ver src/phishguard/dataprep.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from phishguard import dataprep as dp  # noqa: E402

# label 1 = phishing, 0 = legitimo. 'include' se aplica a la ruta dentro del archivo comprimido.
SOURCE_SPECS = {
    "spamassassin": dict(label=0, include=r"(easy_ham|hard_ham)", exclude=r"spam(?!assassin)", max_n=None),
    "enron": dict(label=0, include=None, exclude=None, max_n=8000),      # submuestra aleatoria, semilla 42
    "nazario": dict(label=1, include=None, exclude=r"private", max_n=None),
    "nigerian": dict(label=1, include=None, exclude=None, max_n=None),
}


def build(raw_dir: pathlib.Path, out_dir: pathlib.Path, report_dir: pathlib.Path, sources=None, seed=dp.SEED) -> dict:
    anon = dp.Anonymizer(dp.load_salt(out_dir / ".salt"))
    rows, report = [], {}
    for name, spec in SOURCE_SPECS.items():
        if sources and name not in sources:
            continue
        src_dir = raw_dir / name
        if not src_dir.exists():
            report[name] = {"estado": "sin datos en " + str(src_dir)}
            continue
        before = dict(anon.stats)
        pairs = dp.reservoir_sample(dp.iter_raw_messages(src_dir, spec["include"], spec["exclude"]),
                                    spec["max_n"], seed) if spec["max_n"] else \
            [(n, r()) for n, r in dp.iter_raw_messages(src_dir, spec["include"], spec["exclude"])]
        recs, rep = dp.build_records(name, spec["label"], pairs, anon)
        rows += recs
        report[name] = dict(rep) | {"sustituciones": {k: v - before.get(k, 0) for k, v in anon.stats.items()}}
        print(f"{name}: {dict(rep)}")
    if not rows:
        raise SystemExit("No se encontro ningun correo. Ejecuta primero download_data.py (o coloca los archivos en data/raw/).")
    dp.write_jsonl_gz(rows, out_dir / "emails.jsonl.gz")
    report["total_sustituciones"] = dict(anon.stats)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "anonymization_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--report", default=str(ROOT / "experiments" / "hito2"))
    ap.add_argument("--sources", nargs="*", default=None)
    a = ap.parse_args()
    build(pathlib.Path(a.raw), pathlib.Path(a.out), pathlib.Path(a.report), a.sources)
