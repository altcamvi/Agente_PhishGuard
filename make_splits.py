#!/usr/bin/env python3
"""
Deduplica y particiona el conjunto anonimizado (70/15/15 estratificado por clase y fuente, semilla 42).

  python make_splits.py

Entrada : data/processed/emails.jsonl.gz
Salidas : data/processed/emails_dedup.jsonl.gz (gitignored) y, en experiments/hito2/ (solo conteos, se pueden subir):
          splits.csv (id, fuente, clase, particion), dedup_report.csv, near_duplicates.csv, loso_plan.csv, resumen_*.csv,
          shortcut_tokens.csv (palabras que mas separan las clases: revisar a mano en busca de atajos).
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from phishguard import dataprep as dp  # noqa: E402


def run(processed: pathlib.Path, report_dir: pathlib.Path, seed: int = dp.SEED, near_dedup: bool = False):
    df = dp.read_jsonl_gz(processed / "emails.jsonl.gz")
    n0 = len(df)
    df, dd = dp.drop_duplicates(df)
    report_dir.mkdir(parents=True, exist_ok=True)
    dp.near_duplicate_report(df).to_csv(report_dir / "near_duplicates.csv", index=False)
    if near_dedup:
        df, n_near = dp.drop_near_duplicates(df)
        print(f"casi duplicados descartados: {n_near}")
    df["split"] = dp.stratified_split(df, seed=seed)
    report_dir.mkdir(parents=True, exist_ok=True)
    df[["id", "source", "label", "split"]].to_csv(report_dir / "splits.csv", index=False)
    dd.to_csv(report_dir / "dedup_report.csv", index=False)
    dp.loso_plan(df).to_csv(report_dir / "loso_plan.csv", index=False)
    for name, tab in dp.summarize(df).items():
        tab.to_csv(report_dir / f"resumen_{name}.csv", index=False)
    dp.shortcut_tokens(df).to_csv(report_dir / "shortcut_tokens.csv", index=False)
    dp.write_jsonl_gz(df.to_dict("records"), processed / "emails_dedup.jsonl.gz")
    print(f"{n0} correos -> {len(df)} tras deduplicar")
    print(df.groupby(["split", "label"]).size().unstack(fill_value=0))
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processed", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--report", default=str(ROOT / "experiments" / "hito2"))
    ap.add_argument("--seed", type=int, default=dp.SEED)
    ap.add_argument("--near-dedup", action="store_true",
                    help="ademas de los duplicados exactos, deja un correo por plantilla (ver near_duplicates.csv)")
    a = ap.parse_args()
    run(pathlib.Path(a.processed), pathlib.Path(a.report), a.seed, a.near_dedup)
