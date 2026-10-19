# PhishGuard-Agent

Agente de aprendizaje que clasifica correos como **legítimo / sospechoso / phishing** y actúa
(permitir, advertir, cuarentena, reportar al administrador). Proyecto de *Inteligencia Artificial* — UTB.

## Ciclo del agente (`phishguard/agent.py`)
`perceive()` (parseo + rasgos + consulta de reputación) → `decide()` (modelo + umbrales + confianza) → `act()` (sistema de correo, memoria, log).

## Estructura
| Archivo | Rol | Componente IBM |
|---|---|---|
| `phishguard/features.py` | Percepción: encabezados, SPF/DKIM/DMARC, URLs, adjuntos, texto | Percepción |
| `phishguard/agent.py` | `perceive/decide/act`, orden de comprobaciones | Planificación, Razonamiento |
| `phishguard/memory.py` | Memoria corta/larga, cola de retroalimentación | Memoria |
| `phishguard/tools.py` | Reputación (reintento + degradación) y sistema de correo | Herramientas |
| `phishguard/agent.py` (`REASONS`, `needs_review`) y `app.py` | Alertas y reportes | Comunicación |
| `agent.retrain()` + `memory.review()` | Reentrenamiento tras revisión | Aprendizaje |
| `phishguard/simulator.py` | Entorno simulado (correos + servicio de reputación) | — |
| `phishguard/evaluation.py`, `run_tests.py`, `thresholds.py` | Pruebas Fase 3 | — |

## Ejecución en otro equipo (Python 3.10+)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m phishguard.training      # entrena y guarda models/phishguard_model.joblib (~1 min)
python run_tests.py                # pruebas completas: 5 repeticiones x 100 correos (~4 min)
streamlit run app.py               # interfaz web
```
Si `models/phishguard_model.joblib` no existe (o es de otra versión de scikit-learn), se reentrena automáticamente.
Salidas: `results/tabla_resultados.csv`, `results/detalle_por_escenario.csv`, `results/casos.csv`, `logs/pruebas_agent_log.jsonl`.

## Despliegue (Streamlit Community Cloud)
Subir el repositorio a GitHub → https://share.streamlit.io → *New app* → archivo principal `app.py`.

## Casos de prueba sugeridos en la app
1. Pestaña 1 → tipo `phish_lookalike` → *Generar* → *Analizar* (esperado: cuarentena).
2. `legit_internal` → *Analizar* (esperado: permitir).
3. `phish_compromised` (caso límite) con y sin la caída del servicio de reputación.
4. Falla esperada: borrar el texto y pulsar *Analizar*, o pegar `hola` (esperado: *indeterminado* → reporte al administrador).
5. Pestaña 2: *Demo* de retroalimentación → *Aprobar* → *Reentrenar*; luego analizar `phish_new_campaign`.
6. Pestaña 3: ejecutar las pruebas.

## Datos y limitaciones
Los correos son **sintéticos** (simulador con aleatoriedad y solapamiento entre clases). Los resultados describen el
comportamiento sobre ese entorno, no sobre correo real. `phishguard/features.py` acepta cualquier correo `.eml` real.
