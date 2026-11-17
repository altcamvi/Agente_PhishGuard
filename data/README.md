# data/

Esta carpeta **no contiene correos**. Los datos crudos no se suben al repositorio (ver `.gitignore`);
se descargan con un script y se anonimizan antes de usarse.

## Estado

- **Hito 1 (propuesta):** fuentes y condiciones de uso declaradas. El simulador (`src/phishguard/simulator.py`)
  sigue siendo la única fuente usada por el código actual.
- **Hito 2 (código listo, falta correrlo con datos reales):** `download_data.py` (descarga con confirmación de
  términos, hash y manifiesto), `anonymize.py` (direcciones y nombres de encabezado con hash, teléfonos
  enmascarados, encabezados que delatan fuente o época eliminados) y `make_splits.py` (deduplicación y
  partición 70/15/15 estratificada por clase y fuente, semilla 42). Probado solo con corpus **sintéticos**
  (`python -m unittest discover -s tests -v`); las tablas reales las genera quien ejecute el pipeline.

## Cómo se ejecuta (en un equipo con acceso a internet)

```bash
python download_data.py --list                        # revisar qué archivos publica cada sitio
python download_data.py --source all --accept-terms spamassassin,enron,nazario   # SOLO tras leer los términos
# Nigerian Fraud: copiar los archivos a data/raw/nigerian/ a mano (no hay descarga automática)
python anonymize.py                                   # data/raw/ -> data/processed/emails.jsonl.gz
python make_splits.py                                 # deduplica, particiona y escribe experiments/hito2/*.csv
                                                      # (--near-dedup además deja un correo por plantilla)
python baseline.py                                    # B0 y B1 en validación; luego --loso; --final una sola vez
```

El archivo de Enron pesa ≈ 1,7 GB: descargarlo con buena conexión. Para limitar Nazario a ciertos años: `--include "phishing-202[0-5]"`.
`data/raw/` y `data/processed/` están en `.gitignore`. Lo que sí se sube son los conteos de `experiments/hito2/`.
`--accept-terms` existe a propósito: el script se niega a descargar una fuente hasta que alguien confirme haber leído
sus condiciones. De Nazario se excluyen los archivos `private-*` (un tercero advierte posibles restricciones).

## Limitaciones del preprocesamiento (declarar en el informe)

- Los **nombres** se anonimizan solo en encabezados; en el cuerpo no se detectan (no hay NER). Direcciones de correo y
  teléfonos sí se enmascaran por expresiones regulares, que pueden dejar casos sueltos o dar falsos positivos.
- Los marcadores de fuente (`SOURCE_MARKERS`) se borran, o se cambian por un dominio neutro rotativo, pero la lista no es
  exhaustiva. Tras construir el conjunto hay que revisar `experiments/hito2/shortcut_tokens.csv` y ampliarla.
- Se eliminan fechas y encabezados técnicos, pero el **estilo de época** sigue en el texto (2000–2003 frente a
  2020–2025): se mide con la prueba de dejar una fuente fuera y con el análisis por subgrupo.
- El idioma se estima con una heurística de palabras vacías, no con un detector entrenado.
- El texto anonimizado de `data/processed/` sigue siendo correo real: no se comparte ni se sube al repositorio.

## Fuentes previstas y condiciones de uso

Consulta hecha el 2026-11-11 mediante búsqueda asistida por IA (ver `docs/verificacion_fuentes.md`).
**Un integrante debe abrir cada enlace, confirmar lo que sigue y anotar su nombre y la fecha** (hasta entonces no
correr `download_data.py` con `--accept-terms`).
Ninguna de las tres fuentes publica una licencia formal en las páginas consultadas; lo que hay son avisos del autor.

| Fuente | Rol | Condiciones de uso (resumen, en nuestras palabras) | Estado |
|---|---|---|---|
| Nazario Phishing Corpus (monkey.org/~jose/phishing) | Phishing | **No se pudo abrir la página** desde el entorno de búsqueda, así que no hay texto de condiciones recuperado. Repositorios de terceros la describen como publicada para investigación y recomiendan revisar los términos vigentes; uno advierte que el archivo `private-phishing4.mbox` podría tener restricciones. | **PENDIENTE**: abrir la página y copiar lo que diga. Datos de terceros (no oficiales, 2026-11-12): el sitio ofrece archivos anuales `phishing-2020` a `phishing-2025`, los antiguos `phishing0.mbox` a `phishing3.mbox` (2005–2007) y `private-phishing4.mbox`; una ficha de Hugging Face afirma licencia CC-BY-4.0 con atribución a Jose Nazario, **sin confirmar en el sitio**. Si se cumple, basta citarlo, y ya se cita |
| SpamAssassin public corpus (spamassassin.apache.org/old/publiccorpus/readme.html) | Legítimo (ham: `easy_ham`, `hard_ham`) | El README del corpus dice que los mensajes salieron de foros públicos, fueron enviados a su mantenedor sabiendo que podían publicarse, los envió él mismo o son boletines de sitios públicos. Pide **no enviar estos correos a un sistema de correo activo** y avisar si se publica un trabajo que los use. Los encabezados tienen ofuscación parcial de direcciones. No declara licencia. | Leído en el README; el índice de archivos se verificó el 2026-11-12 (`20030228_easy_ham`, `20030228_easy_ham_2`, `20030228_hard_ham`). Confirmar abriendo el enlace |
| Enron, Carnegie Mellon (cs.cmu.edu/~enron) | Legítimo, correo corporativo | El responsable (W. W. Cohen) lo distribuye como recurso para investigación sobre herramientas de correo y pide **sensibilidad con la privacidad** de las personas, muchas ajenas a la investigación. Versión vigente: 7-may-2015, sin adjuntos y con algunos mensajes eliminados por solicitud de empleados. No declara licencia. | Releído el 2026-11-12; el archivo es `enron_mail_20150507.tar.gz` (≈ 1,7 GB según la página). Confirmar abriendo el enlace |
| Nigerian Fraud (usado en arXiv:2405.11619 y arXiv:2507.17978; fuente de descarga por definir) | Phishing (fraude de pago anticipado), segunda fuente de phishing | No consultadas todavía. | **PENDIENTE**: ubicar la fuente original y copiar sus condiciones |

### Consecuencias para el diseño (a discutir en el equipo)

- El `.gitignore` y el plan de no subir correos crudos son coherentes con las tres condiciones.
- Anonimizar direcciones, nombres y teléfonos (`anonymize.py`) es necesario por la petición de privacidad de Enron.
- La propuesta del Hito 1 añade Nigerian Fraud como segunda fuente de phishing para que la prueba «dejando una fuente fuera» sea calculable (excluir Nazario dejaría sin clase positiva). Decisión a confirmar por el equipo.
- Del corpus SpamAssassin solo se usaría el *ham*; su *spam* no es phishing y no debe entrar en la clase positiva.
- Nunca ejecutar el agente conectado a un buzón real con estos correos (aviso de SpamAssassin).

Subconjunto en español: por buscar. Si no existe, se declara como limitación.
