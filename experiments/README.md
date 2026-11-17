# experiments/

Resultados que respaldan las tablas del informe (entrega del 18-oct-2026, entorno simulado).

| Archivo | Contenido | Tabla del informe |
|---|---|---|
| `tabla_resultados.csv` | Medidas M1–M7: fórmula, umbral, casos, media ± desv., ¿cumple? | Tabla 1 |
| `detalle_por_escenario.csv` | Acierto y tiempo por escenario S01–S14 | Tabla 2 |
| `casos.csv` | Una fila por correo (9 555 filas): escenario, acción, riesgo, tiempo | Base de ambas tablas |
| `extras.json` | Recall antes/después y FPR tras reentrenar (M7) | Sección «Aprendizaje (M7)» |
| `pruebas_agent_log.jsonl` | Log con marca de tiempo de percepción, decisión y acción | M6 (trazabilidad) |

## Semillas

| Uso | Semilla |
|---|---|
| Entrenamiento (`train_bundle`) | `2026` (`random_state` del RandomForest = `2026`) |
| Validación y calibración del umbral | `2027` (`seed + 1`) |
| Pruebas | `90000 + 1000 * repetición + índice de escenario` (5 repeticiones) |
| Reentrenamiento por revisión | `random_state = versión del modelo` |

## Cómo se regeneran

```bash
python run_tests.py     # sobrescribe los archivos de esta carpeta (~2-4 min)
```

> **Aviso de reproducibilidad.** Al repetir las pruebas en otro entorno (Python 3.12.3, versiones de
> `requirements.txt`) la tabla resumen coincidió (M1, M2, M4, M5, M6 y M7 con los mismos valores); el tiempo (M3)
> cambia según la máquina y 35 de 9 555 decisiones individuales (0,37 %) variaron. Antes de volver a ejecutar,
> copie esta carpeta si necesita conservar la evidencia original del informe.

## Hito 2 (`experiments/hito2/`, se crea al ejecutar el pipeline con datos reales)

Solo conteos y métricas; nunca correos. Hasta correr `anonymize.py`, `make_splits.py` y `baseline.py` con los corpus
reales esta carpeta no existe y no hay resultados que citar.

| Archivo | Lo genera | Contenido |
|---|---|---|
| `download_manifest.json` | `download_data.py` | URL, tamaño, SHA-256 y fecha de cada archivo; términos confirmados |
| `anonymization_report.json` | `anonymize.py` | Correos leídos/conservados y sustituciones por fuente |
| `splits.csv`, `dedup_report.csv`, `loso_plan.csv` | `make_splits.py` | Partición 70/15/15 (semilla 42), duplicados, plan de dejar una fuente fuera |
| `near_duplicates.csv` | `make_splits.py` | Correos que comparten plantilla con otro, por fuente y clase |
| `resumen_*.csv`, `shortcut_tokens.csv` | `make_splits.py` | Tamaños, idioma, longitud, adjuntos y palabras que más separan las clases |
| `baseline_validacion.csv`, `baseline_loso.csv`, `baseline_test.csv` | `baseline.py` | B0/B1; el de test se genera una sola vez con `--final` |

Semillas: partición y submuestra de Enron `42`; B1 `random_state = 42`.
