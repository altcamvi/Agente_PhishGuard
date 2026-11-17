# Bitácora humano-IA — PhishGuard-Agent

Registro de cada uso relevante de asistentes de IA generativa. Formato exigido: fecha, integrante, herramienta,
para qué se usó, qué se aceptó/modificó/descartó y cómo se verificó.

> **Por completar por el equipo.** Donde dice «Por completar» o «PENDIENTE», un integrante debe escribir lo
> que realmente hizo. No se rellenó con suposiciones.

| Fecha | Integrante | Herramienta | Para qué se usó | Qué se aceptó / modificó / descartó | Cómo se verificó |
|---|---|---|---|---|---|
| 2026-10-18 | Ruben Gonzalez | Claude (Anthropic) | Matriz de decisión de la Fase 1: propuesta de puntajes y evidencias para los dos agentes | Se aceptó la propuesta como base; los integrantes debían validar cada puntaje | Recálculo de S y de la sensibilidad (ver informe, sección Fase 1) |
| 2026-10-18 | Ruben Gonzalez | Claude | Diseño y código del agente (percepción, decisión, acción, memoria, reentrenamiento), simulador de correo y app Streamlit | Código aceptado tras ejecutarlo; se corrigió el simulador al ver que la validación daba recall 100 % (rasgos que eran artefactos de plantillas) | Ejecución de `python -m phishguard.training`, `python run_tests.py` y prueba de arranque de la app |
| 2026-10-18 | Ruben Gonzalez | Claude | Scripts de pruebas Fase 3 y umbrales | Umbrales fijados en `thresholds.py` antes de ejecutar las pruebas | Una sola ejecución completa de las pruebas; resultados en `experiments/` |
| 2026-10-18 | Ruben Gonzalez | Claude | Diagramas (arquitectura y secuencia) y redacción del documento ajustado | Texto de las secciones 1–8 adaptado del diseño original de Rubén González; secciones nuevas redactadas con IA | Revisión visual del PDF; cifras tomadas de `experiments/*.csv` |
| 2026-11-11 | Ruben Gonzalez | Claude | Hito 1 del proyecto final: evaluar si el proyecto servía, redactar la propuesta (PDF y Word), buscar fuentes de relevancia y proponer corpus, línea base, métricas y umbrales | Por completar (qué texto, cifras o umbrales se cambiaron o descartaron) | **PENDIENTE:** abrir las páginas de MinTIC y Bloomberg Línea y confirmar 79,83 %, 835 casos y 74 %; confirmar la referencia arXiv:2405.11619; leer los términos de uso de los tres corpus y copiarlos a `data/README.md` |
| 2026-11-11 | Ruben Gonzalez | Claude | Revisión del repositorio y reorganización: carpetas `src/`, `data/`, `notebooks/`, `experiments/`, `docs/`; `.gitignore`; versiones fijas en `requirements.txt`; corrección de `train.py`; actualización del README | Por completar (cambios aceptados o revertidos) | Claude ejecutó `train.py` y `run_tests.py` en un entorno limpio (Python 3.12.3): la tabla resumen coincidió, 35 de 9 555 decisiones individuales variaron y el tiempo (M3) cambió. **PENDIENTE:** que un integrante repita los pasos del README en su equipo y compruebe la app desplegada |
| 2026-11-11 | Ruben Gonzalez | Claude | Búsqueda de las verificaciones pendientes (cifras de MinTIC y Bloomberg Línea, arXiv:2405.11619, términos de uso de los tres corpus), corrección del README (Python 3.11+, porque las dependencias fijadas lo exigen) y borrador de esta bitácora | Por completar (qué resultados se adoptaron o descartaron) | Resultados en `docs/verificacion_fuentes.md` y `data/README.md`; la IA **no** abrió monkey.org ni arxiv.org directamente. **PENDIENTE:** un integrante abre cada enlace y firma en `docs/verificacion_fuentes.md`; los requisitos de Python se comprobaron en PyPI |
| 2026-11-12 | Ruben Gonzalez | Claude | Corrección de la propuesta del Hito 1 (fuente de phishing adicional, condiciones de uso, referencia [6]) y construcción del pipeline de datos del Hito 2: `dataprep.py`, `download_data.py`, `anonymize.py`, `make_splits.py`, `baseline.py`, `make_hito2_report.py`, pruebas, cuaderno de exploración y lista de entrega; detección de casi duplicados tras ver un estudio de terceros | Por completar (qué se aceptó, cambió o descartó; p. ej. Nigerian Fraud como segunda fuente de phishing) | La IA lo probó **solo con corpus sintéticos** (`python -m unittest discover -s tests -v`, 15 pruebas) y no pudo descargar los corpus reales (red bloqueada). **PENDIENTE:** un integrante ejecuta el pipeline con datos reales, revisa `shortcut_tokens.csv` y confirma los términos de uso antes de usar `--accept-terms` |

## Reflexión sobre errores de la IA (borrador para el informe, media página)

Casos detectados hasta ahora; el equipo debe completarlos con sus palabras y añadir los que encuentre:

1. **Simulador demasiado fácil.** La primera versión del simulador producía recall 100 % porque el modelo
   aprendía artefactos de las plantillas (proporción de mayúsculas, longitud del cuerpo, signos de
   exclamación), no señales reales de phishing. Se detectó porque una validación perfecta resultaba
   sospechosa; se eliminaron esos rasgos y se añadió solapamiento entre clases.
2. **`train.py` roto.** El script de la raíz importaba una función `train` que no existía, y no se había notado
   porque el README indicaba `python -m phishguard.training`. Se detectó el 2026-11-11 al ejecutar todo el flujo
   desde un entorno limpio, y se corrigió añadiendo `train()` al módulo.

**Limitaciones reconocidas:** los datos actuales son sintéticos; la dificultad del simulador la fijó la IA con
nuestra aprobación. Ver sección 9.8 del informe.
