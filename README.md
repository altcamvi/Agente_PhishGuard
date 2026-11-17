# PhishGuard-Agent

Agente de aprendizaje que clasifica correos como **legítimo / sospechoso / phishing** y actúa
(permitir, advertir, cuarentena, reportar al administrador). Proyecto de *Inteligencia Artificial* — UTB.

## Estructura del repositorio
```
src/phishguard/   código del agente (percepción, decisión, acción, memoria, simulador, evaluación)
data/             datos o script de descarga (nunca correos crudos); ver data/README.md
notebooks/        exploración
experiments/      resultados, log y semillas que respaldan las tablas del informe
docs/             diagramas y bitácora de uso de IA (docs/bitacora_ia.md)
app.py  train.py  run_tests.py  thresholds.py   puntos de entrada y umbrales de aceptación
```

## Alcance del proyecto final (Hito 1)
La entrega anterior evaluó el agente solo con correos **sintéticos**. El proyecto final lo lleva a **correo real**
(Nazario, SpamAssassin, Enron) con línea base, comparación de modelos (regresión logística, Random Forest,
gradient boosting), validación cruzada, prueba dejando una fuente fuera y análisis por subgrupo. Las métricas y
umbrales están declarados en la propuesta (`nombre_proyecto_hito1.pdf`). **Estado actual:** el código y los
resultados de este repositorio siguen siendo los del simulador.

## Ciclo del agente (`src/phishguard/agent.py`)
`perceive()` (parseo + rasgos + consulta de reputación) → `decide()` (modelo + umbrales + confianza) → `act()` (sistema de correo, memoria, log).

## Estructura
| Archivo | Rol | Componente IBM |
|---|---|---|
| `src/phishguard/features.py` | Percepción: encabezados, SPF/DKIM/DMARC, URLs, adjuntos, texto | Percepción |
| `src/phishguard/agent.py` | `perceive/decide/act`, orden de comprobaciones | Planificación, Razonamiento |
| `src/phishguard/memory.py` | Memoria corta/larga, cola de retroalimentación | Memoria |
| `src/phishguard/tools.py` | Reputación (reintento + degradación) y sistema de correo | Herramientas |
| `src/phishguard/agent.py` (`REASONS`, `needs_review`) y `app.py` | Alertas y reportes | Comunicación |
| `agent.retrain()` + `memory.review()` | Reentrenamiento tras revisión | Aprendizaje |
| `src/phishguard/simulator.py` | Entorno simulado (correos + servicio de reputación) | — |
| `src/phishguard/evaluation.py`, `run_tests.py`, `thresholds.py` | Pruebas Fase 3 | — |

## Ejecución en otro equipo (Python 3.10+, probado con 3.12)
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # versiones fijas
python run_tests.py                # entrena si hace falta y ejecuta las pruebas (~2-4 min)
```
Opcional: `python train.py` (solo entrena y guarda `models/phishguard_model.joblib`) y `streamlit run app.py` (interfaz web).
Si `models/phishguard_model.joblib` no existe (o es de otra versión de scikit-learn), se reentrena automáticamente.
Salidas: `experiments/tabla_resultados.csv`, `experiments/detalle_por_escenario.csv`, `experiments/casos.csv`, `experiments/pruebas_agent_log.jsonl`.
Semillas y qué archivo respalda cada tabla del informe: ver `experiments/README.md`.

## Despliegue (Streamlit Community Cloud)
**Aplicación en línea:** https://agentephishguard.streamlit.app/

Para volver a desplegarla o actualizarla: subir el repositorio a GitHub → https://share.streamlit.io → *New app* → archivo principal `app.py`. Cada `git push` actualiza la app. La primera carga puede tardar 1–2 minutos porque, si no existe el modelo, se entrena automáticamente. Si la app está "dormida", pulsar *Wake up*.

## Instrucciones de uso de la app
La app tiene tres pestañas. No requiere instalar nada si se usa el enlace de arriba.

### Pestaña 1 · Analizar correo
1. A la derecha, elegir el **tipo de correo simulado** en la lista (por ejemplo `phish_lookalike` o `legit_internal`) y pulsar **🎲 Generar correo**. El correo crudo aparece en el cuadro de la izquierda. También se puede pegar un correo propio (formato RFC-822 con encabezados) o subir un archivo `.eml`.
2. Pulsar **Analizar**.
3. Interpretar el resultado:
   - 🟢 **legítimo** → acción `allow` (el correo llega a la bandeja).
   - 🟠 **sospechoso** → acción `warn` (llega con advertencia; si la confianza es baja, también se reporta al administrador).
   - 🔴 **phishing** → acción `quarantine` (se retira a cuarentena).
   - ⚪ **indeterminado** → acción `report_admin` (entrada inválida, se envía a revisión humana).
4. Se muestran el **riesgo** (0–1), la **confianza**, el **tiempo de análisis** y las **razones** que llevaron a la decisión. El contador inferior indica cuántos correos hay en bandeja, cuarentena y cola del administrador.
5. El interruptor **"Simular caída del servicio de reputación"** hace que el agente funcione sin esa fuente externa (menor confianza, mismo flujo).

### Pestaña 2 · Retroalimentación y aprendizaje
1. Analizar varios correos en la pestaña 1 (o pulsar **"Generar 40 correos simulados…"** para una demostración rápida).
2. Elegir un caso, indicar su **etiqueta real** (legítimo o phishing) y pulsar **Enviar retroalimentación**. El caso queda *pendiente*: todavía **no** entrena al modelo.
3. Pulsar **✅ Aprobar todos los pendientes** (rol del administrador/revisor).
4. Pulsar **🔁 Reentrenar**. Se necesitan al menos **20 casos aprobados**; al terminar, la versión del modelo aumenta.
5. Volver a la pestaña 1, generar `phish_new_campaign` y comparar el resultado antes y después de reentrenar.

### Pestaña 3 · Ejecutar pruebas (Fase 3)
1. Elegir **repeticiones** y **correos por escenario**. La configuración completa de la entrega es 5 repeticiones × 100 correos (~4 min); para una demostración rápida basta 2 × 30.
2. Pulsar **▶ Ejecutar pruebas**. Al finalizar aparecen la **tabla de resultados** (fórmula, umbral, casos, resultado, ¿cumple?) y el **detalle por escenario**.
3. Los umbrales de aceptación están fijados en `thresholds.py`.

## Casos de prueba sugeridos en la app
| # | Tipo | Qué hacer | Resultado esperado |
|---|---|---|---|
| 1 | Típico (phishing) | Pestaña 1 → `phish_lookalike` → *Generar* → *Analizar* | 🔴 phishing → `quarantine`; razones: dominio parecido a una marca, SPF/DKIM fallidos o ausentes |
| 2 | Típico (legítimo) | `legit_internal` → *Generar* → *Analizar* | 🟢 legítimo → `allow` |
| 3 | Típico (legítimo con marca) | `legit_transactional` → *Analizar* | 🟢 legítimo → `allow` (correo real de una marca con autenticación válida) |
| 4 | Límite | `phish_compromised` (cuenta legítima comprometida, autenticación válida) → *Analizar* | Suele detectarse, pero es el escenario más difícil (~95 % de recall en las pruebas); puede salir 🟠 o 🟢 |
| 5 | Límite | `legit_urgent` (legítimo con lenguaje de urgencia) → *Analizar* | Normalmente 🟢; ocasionalmente 🟠 (falso positivo posible) |
| 6 | Falla esperada | Borrar todo el texto y pulsar *Analizar* | ⚪ indeterminado → `report_admin`, sin errores |
| 7 | Falla esperada | Pegar `hola` o un texto sin encabezado `From:` | ⚪ indeterminado → `report_admin` |
| 8 | Entorno adverso | Activar **"Simular caída del servicio de reputación"** y repetir el caso 1 | Sigue detectándolo, con menor confianza |
| 9 | Aprendizaje | Pestaña 2: *Generar 40 correos…* → *Aprobar* → *Reentrenar*; luego `phish_new_campaign` en la pestaña 1 | Tras reentrenar, la campaña nueva se detecta mejor |
| 10 | Pruebas | Pestaña 3 → *Ejecutar pruebas* (2 × 30 para ir rápido) | Tabla con todas las medidas y su cumplimiento |

> Los correos generados son aleatorios: dos ejecuciones del mismo tipo pueden dar resultados distintos, sobre todo en los casos límite (4 y 5).

## Datos y limitaciones
Los correos son **sintéticos** (simulador con aleatoriedad y solapamiento entre clases). Los resultados describen el
comportamiento sobre ese entorno, no sobre correo real. `src/phishguard/features.py` acepta cualquier correo `.eml` real.
