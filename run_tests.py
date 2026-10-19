"""Ejecuta las pruebas de la Fase 3.  Uso:  python run_tests.py [--reps 5] [--n 100]"""
import argparse, time
import pandas as pd
from phishguard.training import load_or_train
from phishguard.evaluation import run_all

ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=5); ap.add_argument("--n", type=int, default=100)
a = ap.parse_args()
t0 = time.time()
tabla, detalle, extras = run_all(load_or_train(), reps=a.reps, n=a.n,
                                 progress=lambda p, m: print(f"\r{p * 100:5.1f}%  {m}   ", end="", flush=True))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
print("\n\n=== TABLA DE RESULTADOS ===")
print(tabla[["medida", "umbral", "casos", "resultado", "cumple"]].to_string(index=False))
print("\n=== DETALLE POR ESCENARIO ===")
print(detalle.to_string(index=False))
print("\nAprendizaje (campana nueva): recall antes/despues/FPR despues =", extras)
print(f"\nTiempo total: {time.time() - t0:.0f}s")
