# Lista de entrega del Hito 2

Marquen cada punto cuando esté hecho **y** anoten quién lo hizo. Nada de lo que sigue está hecho por la IA: ella dejó el
código y las pruebas con datos sintéticos (`python -m unittest discover -s tests -v`), no corrió los corpus reales.

## A. Antes de descargar
- [ ] Un integrante abrió monkey.org/~jose/phishing, spamassassin.apache.org/old/publiccorpus/readme.html y
      cs.cmu.edu/~enron, copió lo que dicen a `data/README.md` y firmó en `docs/verificacion_fuentes.md`. (quién / fecha: ______)
- [ ] Decidieron la segunda fuente de phishing (Nigerian Fraud u otra) y copiaron sus archivos a `data/raw/nigerian/`.
      Si no hay segunda fuente, la prueba M5 de Nazario **no se puede calcular**: decirlo en el informe.

## B. Ejecución (en un equipo con internet; Enron pesa ≈ 1,7 GB)
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python download_data.py --list
python download_data.py --source all --accept-terms spamassassin,enron,nazario
python anonymize.py
python make_splits.py                       # o con --near-dedup si near_duplicates.csv muestra mucha plantilla repetida
python baseline.py && python baseline.py --loso
```
- [ ] Todo corrió sin errores. Si `download_data.py` dice que un índice no lista el archivo esperado, ajustar `SOURCES`.
- [ ] Abrieron `experiments/hito2/shortcut_tokens.csv`. Si aparecen nombres de fuente, años o listas de correo, los añadieron a
      `SOURCE_MARKERS` en `src/phishguard/dataprep.py` y repitieron desde `anonymize.py`.
- [ ] Revisaron a mano 20 correos anonimizados por fuente (`data/processed/emails.jsonl.gz`): ¿quedan nombres, teléfonos o
      direcciones? Anotaron lo que encontraron.

## C. Informe
```bash
python make_hito2_report.py --docx --pdf     # escribe docs/hito2_informe.{md,docx,pdf}
```
- [ ] Reemplazaron **todos** los bloques «COMPLETAR POR EL EQUIPO» (el script imprime cuántos quedan).
- [ ] No citan métricas de validación como resultado final; el conjunto de prueba (`--final`) se usa una sola vez y solo si ya está
      todo congelado.
- [ ] Si las cifras de B1 son casi perfectas, lo explican con lo visto en `shortcut_tokens.csv` y en M5 antes de presentarlas como logro.

## D. Repositorio
- [ ] `docs/bitacora_ia.md`: integrante, qué aceptaron y cómo verificaron en cada fila (guía: `docs/bitacora_guia_para_completar.md`).
- [ ] Commits **con el usuario de cada integrante**, por separado y con mensajes que digan qué hizo quién. Para repartir el trabajo:
      uno corre y sube `experiments/hito2/` y la bitácora de esa ejecución; el otro revisa anonimización (los 20 correos) y
      `shortcut_tokens.csv`, y sube el informe; cada uno firma su verificación de fuentes.
- [ ] Subir **solo** `experiments/hito2/`, código, docs y notebook. Nunca `data/raw/`, `data/processed/` ni `.salt` (ya están en `.gitignore`;
      comprobar con `git status` antes de `git add`).
- [ ] Tras el push, abrir agentephishguard.streamlit.app y confirmar que carga (cambió `requirements.txt` y el README exige Python 3.11+;
      si falla, revisar la versión de Python en *Advanced settings*).

## E. Qué entregar
- [ ] `docs/hito2_informe.pdf` (y `.docx` si lo piden) y enlace al repositorio.
- [ ] Si el curso pide algo más (presentación, demo, informe de otro formato), no está cubierto aquí: la IA no tuvo la rúbrica del Hito 2.
