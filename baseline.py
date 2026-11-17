#!/usr/bin/env python3
"""
Lineas base de la propuesta (Hito 1, seccion 4): B0 clasificador mayoritario y B1 TF-IDF + regresion logistica.

  python baseline.py                # entrena con 'train', calibra el umbral en 'val' y reporta SOLO en 'val'
  python baseline.py --loso         # prueba dejando una fuente fuera (M5)
  python baseline.py --final        # evalua en 'test'. Hacerlo UNA sola vez, con la configuracion ya congelada

Umbral de decision: el que maximiza el recall con FPR <= 2 % en validacion (M2); nunca se ajusta con 'test'.
Las salidas van a experiments/hito2/. No se afirma ningun resultado hasta correr esto con los datos reales.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from phishguard import dataprep as dp  # noqa: E402

FPR_MAX = 0.02   # M2


def make_b1(seed: int = dp.SEED):
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True, strip_accents="unicode"),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
    )


def calibrate_threshold(y_val, p_val, fpr_max: float = FPR_MAX) -> float:
    """Mayor recall con FPR <= fpr_max; si ninguna cumple, maximiza TPR - FPR (Youden)."""
    fpr, tpr, thr = roc_curve(y_val, p_val)
    ok = np.where(fpr <= fpr_max)[0]
    i = ok[np.argmax(tpr[ok])] if len(ok) else int(np.argmax(tpr - fpr))
    t = float(thr[i])
    return t if np.isfinite(t) else float(np.nextafter(1.0, 2.0))


def metrics(y, p, threshold: float, ms_per_email: float) -> dict:
    y = np.asarray(y)
    pred = (np.asarray(p) >= threshold).astype(int)
    pos, neg = (y == 1), (y == 0)
    return {
        "n": int(len(y)),
        "recall": float(pred[pos].mean()) if pos.any() else float("nan"),
        "fpr": float(pred[neg].mean()) if neg.any() else float("nan"),
        "f1": float(f1_score(y, pred, zero_division=0)) if pos.any() else float("nan"),
        "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else float("nan"),
        "umbral": threshold, "ms_por_correo": ms_per_email,
    }


def _timed_proba(model, texts):
    t0 = time.perf_counter()
    p = model.predict_proba(texts)[:, 1]
    return p, 1000 * (time.perf_counter() - t0) / max(len(texts), 1)


def run_split(df: pd.DataFrame, eval_split: str, seed: int = dp.SEED) -> pd.DataFrame:
    tr, va, ev = (df[df["split"] == s] for s in ("train", "val", eval_split))
    rows = []
    b0 = DummyClassifier(strategy="most_frequent").fit(tr["text"], tr["label"])
    p0, ms0 = _timed_proba(b0, ev["text"])
    rows.append({"modelo": "B0_mayoritario", "conjunto": eval_split,
                 **metrics(ev["label"], p0, 0.5, ms0)})
    b1 = make_b1(seed).fit(tr["text"], tr["label"])
    p_val, _ = _timed_proba(b1, va["text"])
    thr = calibrate_threshold(va["label"], p_val)
    p1, ms1 = _timed_proba(b1, ev["text"])
    rows.append({"modelo": "B1_tfidf_logreg", "conjunto": eval_split, **metrics(ev["label"], p1, thr, ms1)})
    return pd.DataFrame(rows)


def run_loso(df: pd.DataFrame, seed: int = dp.SEED) -> pd.DataFrame:
    rows = []
    for _, plan in dp.loso_plan(df).iterrows():
        src = plan["fuente_excluida"]
        if not plan["calculable"]:
            rows.append({"fuente_excluida": src, "metrica": plan["metrica"], "valor": float("nan"),
                         "nota": plan["motivo"]})
            continue
        rest, held = df[df["source"] != src], df[df["source"] == src]
        tr, va = rest[rest["split"] == "train"], rest[rest["split"] == "val"]
        b1 = make_b1(seed).fit(tr["text"], tr["label"])
        thr = calibrate_threshold(va["label"], b1.predict_proba(va["text"])[:, 1])
        p, ms = _timed_proba(b1, held["text"])
        m = metrics(held["label"], p, thr, ms)
        rows.append({"fuente_excluida": src, "metrica": plan["metrica"], "valor": m[plan["metrica"].lower()],
                     "n": m["n"], "umbral": thr, "ms_por_correo": ms, "nota": ""})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processed", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--report", default=str(ROOT / "experiments" / "hito2"))
    ap.add_argument("--final", action="store_true", help="evaluar en test (una sola vez)")
    ap.add_argument("--loso", action="store_true")
    ap.add_argument("--seed", type=int, default=dp.SEED)
    a = ap.parse_args()
    data = dp.read_jsonl_gz(pathlib.Path(a.processed) / "emails_dedup.jsonl.gz")
    out = pathlib.Path(a.report)
    out.mkdir(parents=True, exist_ok=True)
    if a.loso:
        res = run_loso(data, a.seed)
        res.to_csv(out / "baseline_loso.csv", index=False)
    else:
        res = run_split(data, "test" if a.final else "val", a.seed)
        res.to_csv(out / ("baseline_test.csv" if a.final else "baseline_validacion.csv"), index=False)
    print(res.round(4).to_string(index=False))
