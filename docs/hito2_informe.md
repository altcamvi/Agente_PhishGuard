# PhishGuard-Agent · Hito 2: datos reales, preprocesamiento y líneas base

Inteligencia Artificial · Universidad Tecnológica de Bolívar · Docente: Edwin Puertas del Castillo · Rubén Enrique González Caro · Camilo Villadiego Iriarte · 16-11-2026

Ruta principal: **C (aprendizaje automático)**. Repositorio: github.com/altcamvi/Agente_PhishGuard. Propuesta que este informe desarrolla: `docs/phishguard_agent_hito1.pdf`.

## 1. Qué se hizo en este hito

Se construyó el pipeline que lleva el agente de correo sintético a correo real: descarga con verificación de términos, anonimización, deduplicación, partición 70/15/15 (semilla 42), exploración y líneas base B0 y B1 de la propuesta. Todo el código está en el repositorio y se probó con corpus sintéticos (`python -m unittest discover -s tests -v`). Los resultados de este informe provienen de la ejecución con los corpus reales, registrada en `experiments/hito2/`.

> **[COMPLETAR POR EL EQUIPO]** Resumir en 3–4 frases qué se logró y qué no, con sus palabras.

## 2. Datos

| Fuente | Rol | Condiciones de uso |
|---|---|---|
| Nazario Phishing Corpus | Phishing | Colección pública de su autor; términos por confirmar en el sitio |
| SpamAssassin public corpus (solo *ham*) | Legítimo | Sin licencia formal; no enviarlo a un sistema de correo activo |
| Enron (Carnegie Mellon) | Legítimo | Distribuido para investigación, sin licencia formal; se pide cuidar la privacidad |
| Nigerian Fraud | Phishing (pago anticipado) | Por confirmar |

Detalle y estado de cada verificación: `data/README.md` y `docs/verificacion_fuentes.md`.

**Archivos descargados** (hash SHA-256 abreviado; manifiesto completo en `experiments/hito2/download_manifest.json`):

| fuente | archivo | bytes | sha256 |
|---|---|---|---|
| spamassassin | 20030228_easy_ham.tar.bz2 | 1612216 |  |
| spamassassin | 20030228_easy_ham_2.tar.bz2 | 1077892 |  |
| spamassassin | 20030228_hard_ham.tar.bz2 | 1029898 |  |
| enron | enron_mail_20150507.tar.gz | 443254787 |  |
| nazario | phishing-2015 | 8815568 |  |
| nazario | phishing-2016 | 12578274 |  |
| nazario | phishing-2017 | 11352450 |  |
| nazario | phishing-2018 | 8775701 |  |
| nazario | phishing-2019 | 5211476 |  |
| nazario | phishing-2020 | 5826445 |  |
| nazario | phishing-2021 | 2719946 |  |
| nazario | phishing-2022 | 4775954 |  |
| nazario | phishing-2023 | 7763704 |  |
| nazario | phishing-2024 | 15457816 |  |
| nazario | phishing-2025 | 18769863 |  |
| nazario | phishing0.mbox | 3119972 |  |
| nazario | phishing1.mbox | 4191770 |  |
| nazario | phishing2.mbox | 10420294 |  |
| nazario | phishing3.mbox | 20067215 | b29336d2e31c |

### Tamaños y balance

Tras anonimizar y deduplicar hay **18564** correos: 6553 de phishing (35.3 %) y 12011 legítimos.

| fuente | clase (1 = phishing) | correos |
|---|---|---|
| enron | 0 | 7894 |
| nigerian | 1 | 6553 |
| spamassassin | 0 | 4117 |

> **[COMPLETAR POR EL EQUIPO]** Comparar con los tamaños esperados de la propuesta (≈ 11 500 / 4 100 / 8 000 / 4 000) y explicar diferencias.

## 3. Preprocesamiento

Anonimización: direcciones de correo y nombres de encabezado con hash HMAC (sal local, no compartida); teléfonos enmascarados; se eliminan encabezados que delatan fuente o época (Received, Message-ID, Date, X-*); los adjuntos se vacían conservando sus extensiones; se borran marcadores de fuente (nombres de corpus, listas de correo).

| fuente | leidos | conservados | sust_telefonos | sust_emails | sust_marcadores_fuente | sust_nombres_encabezado | sust_adjuntos |
|---|---|---|---|---|---|---|---|
| spamassassin | 4150 | 4150 | 360 | 15723 | 7160 | 5533 | 51 |
| enron | 8000 | 8000 | 4146 | 50621 | 59515 | 189 | 0 |
| nigerian | 6973 | 6973 | 762 | 1223 | 676 | 0 | 0 |

### Duplicados

Duplicados exactos (asunto + cuerpo normalizados) y correos con etiqueta contradictoria, que se descartan:

| source | label | duplicados_exactos | etiqueta_contradictoria |
|---|---|---|---|
| enron | 0 | 106 | 0 |
| nigerian | 1 | 420 | 0 |
| spamassassin | 0 | 33 | 0 |

Casi duplicados (misma plantilla con distinta URL, nombre o número). No se eliminan salvo con `--near-dedup`; si el porcentaje es alto, una partición al azar deja copias casi idénticas en entrenamiento y prueba y **infla las métricas**:

| source | label | correos | con_clave | en_plantilla_repetida | pct_en_plantilla_repetida |
|---|---|---|---|---|---|
| enron | 0 | 7894 | 6777 | 329 | 4.2 |
| nigerian | 1 | 6553 | 6151 | 460 | 7 |
| spamassassin | 0 | 4117 | 3895 | 49 | 1.2 |

> **[COMPLETAR POR EL EQUIPO]** ¿Qué porcentaje de plantilla repetida hay? Decidir si se usa --near-dedup y justificarlo.

### Partición

70 % entrenamiento, 15 % validación, 15 % prueba; estratificada por clase y fuente; semilla 42. El umbral de decisión se calibra solo en validación; la prueba se usa una vez.

| split | label | correos |
|---|---|---|
| test | 0 | 1802 |
| test | 1 | 983 |
| train | 0 | 8407 |
| train | 1 | 4587 |
| val | 0 | 1802 |
| val | 1 | 983 |

## 4. Exploración y posibles atajos

Idioma (heurística de palabras vacías, no un detector entrenado): en 94.3 %, desconocido 5.1 %, es 0.5 %, mixto 0.1 %.

La propuesta pide no afirmar nada sobre español si no hay un subconjunto en ese idioma.

Ninguna de las palabras más discriminantes coincide con la lista de vigilancia (nombres de fuente, años, listas de correo); eso no demuestra que no haya otros atajos: revisar la tabla completa.

| token | log_odds_phishing_vs_legitimo | df_phishing | df_legitimo |
|---|---|---|---|
| phishing | 18.18 | 0.9998 | 0.0001 |
| sample | 13.87 | 0.9998 | 0.0062 |
| cialis | 5.8 | 0.0267 | 0.0001 |
| corel | 5.58 | 0.0217 | 0.0001 |
| wiil | 5.52 | 0.0204 | 0.0001 |
| paliourg | 5.44 | 0.0188 | 0.0001 |
| freshrpms | -5.39 | 0.0002 | 0.0323 |
| ena | -5.38 | 0.0002 | 0.032 |
| u582ae15d | -5.38 | 0.0002 | 0.032 |
| ail | 5.32 | 0.0168 | 0.0001 |
| ees | -5.31 | 0.0002 | 0.0301 |
| piease | 5.27 | 0.0159 | 0.0001 |
| meds | 5.19 | 0.0291 | 0.0002 |
| oniy | 5.13 | 0.0139 | 0.0001 |
| newsisfree | -5.12 | 0.0002 | 0.0249 |

**Limitación estructural:** cada fuente contiene una sola clase (Nazario y Nigerian Fraud, phishing; SpamAssassin y Enron, legítimo), de modo que la fuente por sí sola predice la etiqueta. Por eso la prueba de dejar una fuente fuera (M5), el análisis por subgrupo (M6) y la revisión de atajos no son opcionales.

> **[COMPLETAR POR EL EQUIPO]** Interpretar la tabla de palabras: ¿qué atajos hay y qué se hizo con ellos?

## 5. Líneas base (validación)

B0: clasificador mayoritario. B1: TF-IDF (1–2 gramas) + regresión logística con pesos balanceados. Umbral: el que maximiza el recall con FPR ≤ 2 % en validación. Estas cifras son de **validación**, no de prueba: no se contrastan con los umbrales como resultado final.

| modelo | conjunto | n | recall | fpr | f1 | auc | umbral | ms_por_correo |
|---|---|---|---|---|---|---|---|---|
| B0_mayoritario | val | 2785 | 0 | 0 | 0 | 0.5 | 0.5 | 3.594e-05 |
| B1_tfidf_logreg | val | 2785 | 0.999 | 0.0172 | 0.984 | 0.9996 | 0.4094 | 0.3388 |

Comparación con los umbrales de la propuesta (M4 y M6 requieren 5 corridas y subgrupos, y quedan para el Hito 3):

| medida | umbral | B1 en validación | cumple |
|---|---|---|---|
| M1 recall | ≥ 0.95 | 0.999 | Sí |
| M2 FPR | ≤ 0.02 | 0.0172 | Sí |
| M3 F1 | ≥ 0.95 | 0.984 | Sí |
| M3 AUC | ≥ 0.98 | 0.9996 | Sí |
| M7 ms/correo | ≤ 200 | 0.339 | Sí |

**Cuidado:** valores casi perfectos con fuentes de una sola clase suelen indicar atajos, no un problema resuelto.

> **[COMPLETAR POR EL EQUIPO]** Interpretar: ¿B1 supera a B0? ¿Son creíbles estas cifras tras la sección 4?

### Prueba dejando una fuente fuera (M5)

| fuente_excluida | metrica | valor | umbral | cumple | n | nota |
|---|---|---|---|---|---|---|
| enron | FPR | 0.6646 | ≤ 0.05 | **No** | 7894 |  |
| nigerian | recall |  | ≥ 0.85 | No calculable |  | sin la fuente solo queda una clase para entrenar |
| spamassassin | FPR | 0.2937 | ≤ 0.05 | **No** | 4117 |  |

> **[COMPLETAR POR EL EQUIPO]** ¿Cuánto se degrada B1 con una fuente no vista? ¿Qué fuente es la más difícil y por qué?

_El conjunto de prueba no se ha usado todavía (`python baseline.py --final`, una sola vez)._

## 6. Limitaciones

- Los nombres solo se anonimizan en encabezados; en el cuerpo no se detectan (no hay NER).
- Teléfonos y direcciones se detectan por expresiones regulares: pueden quedar casos sueltos o haber falsos positivos.
- La lista de marcadores de fuente no es exhaustiva.
- Épocas distintas por clase (legítimo de 2000–2003; Nazario, según fuentes de terceros, de 2005–2007 y 2020–2025): el estilo de época puede quedar en el texto.
- El idioma es una heurística; casi todo el corpus está en inglés.
- Los textos anonimizados siguen siendo correo real: no se comparten ni se suben al repositorio.

## 7. Reproducibilidad

```bash
python -m unittest discover -s tests -v
python download_data.py --source all --accept-terms spamassassin,enron,nazario
python anonymize.py && python make_splits.py
python baseline.py && python baseline.py --loso   # --final solo una vez
python make_hito2_report.py --docx --pdf
```

Semillas: partición y submuestra de Enron `42`; B1 `random_state = 42`. Versiones: `requirements.txt`.

## 8. Uso de IA generativa

Se usó Claude (Anthropic) para diseñar y programar el pipeline, redactar documentación y buscar fuentes. El registro está en `docs/bitacora_ia.md`. La IA probó el código con corpus sintéticos y no ejecutó los corpus reales; las cifras de este informe salen de la ejecución del equipo.

> **[COMPLETAR POR EL EQUIPO]** Confirmar quién ejecutó el pipeline, en qué equipo y fecha, y qué se verificó a mano.

## 9. Pendientes para el Hito 3

Comparación de Random Forest y gradient boosting con búsqueda de hiperparámetros, validación cruzada de 5 pliegues, 5 corridas con semillas distintas (M4), análisis por subgrupo (M6), clasificación de al menos 10 errores y evaluación final en prueba.
