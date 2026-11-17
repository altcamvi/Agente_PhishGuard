#!/usr/bin/env python3
"""
Arma el INFORME del Hito 2 a partir de lo que dejo el pipeline en experiments/hito2/ (no inventa nada: si un archivo
falta, la seccion dice que aun no se ejecuto ese paso). Las interpretaciones las escribe el equipo.

  python make_hito2_report.py              # escribe docs/hito2_informe.md
  python make_hito2_report.py --docx --pdf # ademas docs/hito2_informe.docx y .pdf (requiere pandoc y LibreOffice)

Antes de entregar: buscar en el informe el texto «COMPLETAR» y reemplazarlo; revisar la seccion de atajos.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
from datetime import date

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
TEAM = "Rubén Enrique González Caro · Camilo Villadiego Iriarte"
TODO = "> **[COMPLETAR POR EL EQUIPO]** {}\n"

# Umbrales de la propuesta (Hito 1, seccion 5). M4 y M6 necesitan 5 corridas / subgrupos: no se evaluan en el Hito 2.
M1, M2, M3_F1, M3_AUC, M5_RECALL, M5_FPR, M7_MS = 0.95, 0.02, 0.95, 0.98, 0.85, 0.05, 200.0
WATCH = re.compile(r"^(enron|spamassassin|monkey|nazario|sourceforge|mailman|redhat|exmh|spambayes|(19|20)\d\d)$", re.I)


def md_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "_(sin filas)_\n"
    cols = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for v in r:
            cells.append("" if pd.isna(v) else (f"{v:.4g}" if isinstance(v, float) else str(v)))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows) + "\n"


def load(d: pathlib.Path, name: str):
    f = d / name
    return pd.read_csv(f) if f.exists() else None


def missing(name: str, step: str) -> str:
    return f"_Aún no hay `{name}`: falta ejecutar `{step}` con los datos reales._\n"


def ok(b: bool) -> str:
    return "Sí" if b else "**No**"


def build(d: pathlib.Path) -> str:
    out = []
    w = out.append
    conteo = load(d, "resumen_conteo_por_fuente_clase.csv")
    part = load(d, "resumen_particion.csv")
    idioma = load(d, "resumen_idioma_por_fuente.csv")
    dedup = load(d, "dedup_report.csv")
    near = load(d, "near_duplicates.csv")
    loso = load(d, "loso_plan.csv")
    tokens = load(d, "shortcut_tokens.csv")
    base_v = load(d, "baseline_validacion.csv")
    base_l = load(d, "baseline_loso.csv")
    base_t = load(d, "baseline_test.csv")
    anon = json.loads((d / "anonymization_report.json").read_text()) if (d / "anonymization_report.json").exists() else None
    man = json.loads((d / "download_manifest.json").read_text()) if (d / "download_manifest.json").exists() else None

    w("# PhishGuard-Agent · Hito 2: datos reales, preprocesamiento y líneas base\n")
    w(f"Inteligencia Artificial · Universidad Tecnológica de Bolívar · Docente: Edwin Puertas del Castillo · "
      f"{TEAM} · {date.today().strftime('%d-%m-%Y')}\n")
    w("Ruta principal: **C (aprendizaje automático)**. Repositorio: github.com/altcamvi/Agente_PhishGuard. "
      "Propuesta que este informe desarrolla: `docs/phishguard_agent_hito1.pdf`.\n")

    w("## 1. Qué se hizo en este hito\n")
    w("Se construyó el pipeline que lleva el agente de correo sintético a correo real: descarga con verificación de "
      "términos, anonimización, deduplicación, partición 70/15/15 (semilla 42), exploración y líneas base B0 y B1 de la "
      "propuesta. Todo el código está en el repositorio y se probó con corpus sintéticos (`python -m unittest discover -s tests -v`). "
      "Los resultados de este informe provienen de la ejecución con los corpus reales, registrada en `experiments/hito2/`.\n")
    w(TODO.format("Resumir en 3–4 frases qué se logró y qué no, con sus palabras."))

    w("## 2. Datos\n")
    w("| Fuente | Rol | Condiciones de uso |\n|---|---|---|\n"
      "| Nazario Phishing Corpus | Phishing | Colección pública de su autor; términos por confirmar en el sitio |\n"
      "| SpamAssassin public corpus (solo *ham*) | Legítimo | Sin licencia formal; no enviarlo a un sistema de correo activo |\n"
      "| Enron (Carnegie Mellon) | Legítimo | Distribuido para investigación, sin licencia formal; se pide cuidar la privacidad |\n"
      "| Nigerian Fraud | Phishing (pago anticipado) | Por confirmar |\n")
    w("Detalle y estado de cada verificación: `data/README.md` y `docs/verificacion_fuentes.md`.\n")
    if man:
        rows = [{"fuente": k, "archivo": f.get("file"), "bytes": f.get("bytes"), "sha256": (f.get("sha256") or "")[:12]}
                for k, v in man.items() for f in v.get("files", [])]
        w("**Archivos descargados** (hash SHA-256 abreviado; manifiesto completo en `experiments/hito2/download_manifest.json`):\n")
        w(md_table(pd.DataFrame(rows)))
    else:
        w(missing("download_manifest.json", "python download_data.py --accept-terms ..."))
    w("### Tamaños y balance\n")
    if conteo is not None:
        tot = int(conteo["correos"].sum())
        ph = int(conteo.loc[conteo["label"] == 1, "correos"].sum())
        w(f"Tras anonimizar y deduplicar hay **{tot}** correos: {ph} de phishing ({100*ph/tot:.1f} %) y {tot-ph} legítimos.\n")
        w(md_table(conteo.rename(columns={"source": "fuente", "label": "clase (1 = phishing)"})))
    else:
        w(missing("resumen_conteo_por_fuente_clase.csv", "python make_splits.py"))
    w(TODO.format("Comparar con los tamaños esperados de la propuesta (≈ 11 500 / 4 100 / 8 000 / 4 000) y explicar diferencias."))

    w("## 3. Preprocesamiento\n")
    w("Anonimización: direcciones de correo y nombres de encabezado con hash HMAC (sal local, no compartida); teléfonos "
      "enmascarados; se eliminan encabezados que delatan fuente o época (Received, Message-ID, Date, X-*); los adjuntos se "
      "vacían conservando sus extensiones; se borran marcadores de fuente (nombres de corpus, listas de correo).\n")
    if anon:
        rows = [{"fuente": k, **{kk: vv for kk, vv in v.items() if kk != "sustituciones"},
                 **{f"sust_{a}": b for a, b in v.get("sustituciones", {}).items()}}
                for k, v in anon.items() if isinstance(v, dict) and k != "total_sustituciones"]
        w(md_table(pd.DataFrame(rows)))
    else:
        w(missing("anonymization_report.json", "python anonymize.py"))
    w("### Duplicados\n")
    if dedup is not None:
        w("Duplicados exactos (asunto + cuerpo normalizados) y correos con etiqueta contradictoria, que se descartan:\n")
        w(md_table(dedup))
    else:
        w(missing("dedup_report.csv", "python make_splits.py"))
    if near is not None:
        w("Casi duplicados (misma plantilla con distinta URL, nombre o número). No se eliminan salvo con `--near-dedup`; "
          "si el porcentaje es alto, una partición al azar deja copias casi idénticas en entrenamiento y prueba y "
          "**infla las métricas**:\n")
        w(md_table(near))
    w(TODO.format("¿Qué porcentaje de plantilla repetida hay? Decidir si se usa --near-dedup y justificarlo."))

    w("### Partición\n")
    w("70 % entrenamiento, 15 % validación, 15 % prueba; estratificada por clase y fuente; semilla 42. El umbral de "
      "decisión se calibra solo en validación; la prueba se usa una vez.\n")
    w(md_table(part) if part is not None else missing("resumen_particion.csv", "python make_splits.py"))

    w("## 4. Exploración y posibles atajos\n")
    if idioma is not None:
        agg = idioma.groupby("lang")["correos"].sum()
        w("Idioma (heurística de palabras vacías, no un detector entrenado): " +
          ", ".join(f"{k} {100*v/agg.sum():.1f} %" for k, v in agg.sort_values(ascending=False).items()) + ".\n")
        w("La propuesta pide no afirmar nada sobre español si no hay un subconjunto en ese idioma.\n")
    if tokens is not None:
        hits = tokens[tokens["token"].astype(str).str.match(WATCH)]
        if len(hits):
            w(f"**ALERTA:** entre las {len(tokens)} palabras que más separan las clases aparecen marcadores de fuente o de época: "
              + ", ".join(f"`{t}`" for t in hits["token"]) + ". Añadirlos a `SOURCE_MARKERS` en `src/phishguard/dataprep.py` y repetir `anonymize.py`.\n")
        else:
            w("Ninguna de las palabras más discriminantes coincide con la lista de vigilancia (nombres de fuente, años, listas de correo); "
              "eso no demuestra que no haya otros atajos: revisar la tabla completa.\n")
        w(md_table(tokens.head(15)))
    else:
        w(missing("shortcut_tokens.csv", "python make_splits.py"))
    w("**Limitación estructural:** cada fuente contiene una sola clase (Nazario y Nigerian Fraud, phishing; SpamAssassin y Enron, "
      "legítimo), de modo que la fuente por sí sola predice la etiqueta. Por eso la prueba de dejar una fuente fuera (M5), "
      "el análisis por subgrupo (M6) y la revisión de atajos no son opcionales.\n")
    w(TODO.format("Interpretar la tabla de palabras: ¿qué atajos hay y qué se hizo con ellos?"))

    w("## 5. Líneas base (validación)\n")
    w("B0: clasificador mayoritario. B1: TF-IDF (1–2 gramas) + regresión logística con pesos balanceados. Umbral: el que maximiza "
      "el recall con FPR ≤ 2 % en validación. Estas cifras son de **validación**, no de prueba: no se contrastan con los umbrales "
      "como resultado final.\n")
    if base_v is not None:
        w(md_table(base_v))
        b1 = base_v[base_v["modelo"].str.startswith("B1")].iloc[0]
        t = pd.DataFrame([
            {"medida": "M1 recall", "umbral": f"≥ {M1:.2f}", "B1 en validación": round(b1["recall"], 4), "cumple": ok(b1["recall"] >= M1)},
            {"medida": "M2 FPR", "umbral": f"≤ {M2:.2f}", "B1 en validación": round(b1["fpr"], 4), "cumple": ok(b1["fpr"] <= M2)},
            {"medida": "M3 F1", "umbral": f"≥ {M3_F1:.2f}", "B1 en validación": round(b1["f1"], 4), "cumple": ok(b1["f1"] >= M3_F1)},
            {"medida": "M3 AUC", "umbral": f"≥ {M3_AUC:.2f}", "B1 en validación": round(b1["auc"], 4), "cumple": ok(b1["auc"] >= M3_AUC)},
            {"medida": "M7 ms/correo", "umbral": f"≤ {M7_MS:.0f}", "B1 en validación": round(b1["ms_por_correo"], 3), "cumple": ok(b1["ms_por_correo"] <= M7_MS)},
        ])
        w("Comparación con los umbrales de la propuesta (M4 y M6 requieren 5 corridas y subgrupos, y quedan para el Hito 3):\n")
        w(md_table(t))
        w("**Cuidado:** valores casi perfectos con fuentes de una sola clase suelen indicar atajos, no un problema resuelto.\n")
    else:
        w(missing("baseline_validacion.csv", "python baseline.py"))
    w(TODO.format("Interpretar: ¿B1 supera a B0? ¿Son creíbles estas cifras tras la sección 4?"))

    w("### Prueba dejando una fuente fuera (M5)\n")
    if base_l is not None:
        t = base_l.copy()
        if "valor" in t:
            def passes(r):
                if pd.isna(r["valor"]):
                    return "No calculable"
                return ok(r["valor"] >= M5_RECALL) if r["metrica"] == "recall" else ok(r["valor"] <= M5_FPR)
            t["umbral"] = t["metrica"].map({"recall": f"≥ {M5_RECALL:.2f}", "FPR": f"≤ {M5_FPR:.2f}"})
            t["cumple"] = t.apply(passes, axis=1)
        w(md_table(t[[c for c in ("fuente_excluida", "metrica", "valor", "umbral", "cumple", "n", "nota") if c in t]]))
    elif loso is not None:
        w(md_table(loso))
        w(missing("baseline_loso.csv", "python baseline.py --loso"))
    else:
        w(missing("loso_plan.csv", "python make_splits.py"))
    w(TODO.format("¿Cuánto se degrada B1 con una fuente no vista? ¿Qué fuente es la más difícil y por qué?"))
    if base_t is not None:
        w("### Evaluación en prueba\n")
        w(md_table(base_t))
    else:
        w("_El conjunto de prueba no se ha usado todavía (`python baseline.py --final`, una sola vez)._\n")

    w("## 6. Limitaciones\n")
    w("- Los nombres solo se anonimizan en encabezados; en el cuerpo no se detectan (no hay NER).\n"
      "- Teléfonos y direcciones se detectan por expresiones regulares: pueden quedar casos sueltos o haber falsos positivos.\n"
      "- La lista de marcadores de fuente no es exhaustiva.\n"
      "- Épocas distintas por clase (legítimo de 2000–2003; Nazario, según fuentes de terceros, de 2005–2007 y 2020–2025): el estilo de época puede quedar en el texto.\n"
      "- El idioma es una heurística; casi todo el corpus está en inglés.\n"
      "- Los textos anonimizados siguen siendo correo real: no se comparten ni se suben al repositorio.\n")

    w("## 7. Reproducibilidad\n")
    w("```bash\npython -m unittest discover -s tests -v\npython download_data.py --source all --accept-terms spamassassin,enron,nazario\n"
      "python anonymize.py && python make_splits.py\npython baseline.py && python baseline.py --loso   # --final solo una vez\n"
      "python make_hito2_report.py --docx --pdf\n```\n")
    w("Semillas: partición y submuestra de Enron `42`; B1 `random_state = 42`. Versiones: `requirements.txt`.\n")

    w("## 8. Uso de IA generativa\n")
    w("Se usó Claude (Anthropic) para diseñar y programar el pipeline, redactar documentación y buscar fuentes. El registro está en "
      "`docs/bitacora_ia.md`. La IA probó el código con corpus sintéticos y no ejecutó los corpus reales; las cifras de este informe "
      "salen de la ejecución del equipo.\n")
    w(TODO.format("Confirmar quién ejecutó el pipeline, en qué equipo y fecha, y qué se verificó a mano."))

    w("## 9. Pendientes para el Hito 3\n")
    w("Comparación de Random Forest y gradient boosting con búsqueda de hiperparámetros, validación cruzada de 5 pliegues, "
      "5 corridas con semillas distintas (M4), análisis por subgrupo (M6), clasificación de al menos 10 errores y evaluación "
      "final en prueba.\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(ROOT / "experiments" / "hito2"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "hito2_informe.md"))
    ap.add_argument("--docx", action="store_true")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(pathlib.Path(a.dir)), encoding="utf-8")
    print("Escrito", out, "| pendientes de completar:", out.read_text(encoding="utf-8").count("COMPLETAR POR EL EQUIPO"))
    if a.docx or a.pdf:
        docx = out.with_suffix(".docx")
        subprocess.run(["pandoc", str(out), "-o", str(docx)], check=True)
        print("Escrito", docx)
        if a.pdf:
            soffice = shutil.which("soffice") or shutil.which("libreoffice")
            if not soffice:
                raise SystemExit("No se encontro LibreOffice: abrir el .docx y exportar a PDF.")
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out.parent), str(docx)], check=True)
            print("Escrito", docx.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
