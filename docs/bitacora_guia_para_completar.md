# Guía para completar la bitácora (`docs/bitacora_ia.md`)

Cada fila de la bitácora tiene tres huecos que solo ustedes pueden llenar. Esta guía no contiene respuestas:
son preguntas para que cada integrante escriba, con sus palabras, lo que realmente hizo.
Si no participó en una fila, que no la firme.

## Reglas

1. **Integrante:** nombre de quien hizo la sesión con la IA o revisó su resultado, no de todo el equipo.
2. **Qué se aceptó / modificó / descartó:** una frase concreta por cada cambio (qué texto, cifra o archivo).
   «Se aceptó todo» es válido si es verdad, pero debe decir qué se revisó.
3. **Cómo se verificó:** algo que otra persona pueda repetir (comando, página abierta, cálculo, comparación).
4. No copiar lo que dice la columna de la IA: escribirlo en primera persona del equipo.

## Preguntas por fila

| Fila (fecha · tema) | Preguntas para quien la firma |
|---|---|
| 2026-10-18 · Matriz de decisión Fase 1 | ¿Qué puntajes cambiaron respecto a la propuesta de la IA y por qué? ¿Quién recalculó S y la sensibilidad? ¿Coincide con el informe? |
| 2026-10-18 · Diseño y código del agente, simulador y app | ¿Quién ejecutó `python -m phishguard.training`, `python run_tests.py` y la app? ¿Qué parte del código leyó y entendió, y cuál no? ¿Quién notó que el recall del 100 % era sospechoso? |
| 2026-10-18 · Scripts de pruebas y umbrales | ¿Quién aprobó los umbrales antes de ejecutar? ¿Cómo comprobaron que se fijaron antes (historial de git, fecha de `thresholds.py`)? |
| 2026-10-18 · Diagramas y documento | ¿Qué secciones del texto de la IA se reescribieron? ¿Quién contrastó las cifras con `experiments/*.csv`? ¿De qué partes es autor Rubén González? |
| 2026-11-11 · Hito 1 (propuesta y fuentes) | ¿Qué cifras, textos o umbrales se cambiaron o descartaron? ¿Quién abrió MinTIC y Bloomberg Línea? Ver `docs/verificacion_fuentes.md`: ¿la propuesta dice «fraude» y «origen en correo» donde corresponde? |
| 2026-11-11 · Reorganización del repositorio | ¿Qué cambios se aceptaron o revirtieron? ¿Quién repitió los pasos del README en su equipo (sistema operativo y versión de Python) y qué vio? ¿Quién comprobó la app desplegada tras el push? |
| 2026-11-11 · Verificación de fuentes y README | ¿Quién abrió cada enlace de `docs/verificacion_fuentes.md` y firmó? ¿Se consiguió abrir monkey.org? ¿Qué dicen sus condiciones? |

## Reflexión sobre errores de la IA (media página)

Los dos casos ya anotados (simulador demasiado fácil, `train.py` roto) vienen de la IA. Para completar con
sus palabras, conviene añadir al menos uno propio. Ideas de dónde mirar, **si de verdad ocurrió**:

- ¿Hubo una cifra o referencia que la IA dio y no se pudo confirmar o resultó imprecisa? (Por ejemplo, el 79,83 %
  es el peso del fraude en general, no del phishing.)
- ¿Una instrucción del README resultó incorrecta? (Ejemplo hallado el 2026-11-11: «Python 3.10+», cuando las
  dependencias fijadas exigen 3.11 o superior.)
- ¿Algo que la IA dio por hecho sin poder comprobarlo? (No pudo abrir monkey.org ni arxiv.org directamente.)

## Para el criterio de commits distribuidos

Hoy los 4 commits son de una sola persona. Sugerencia: que cada integrante suba con su usuario lo que realmente
hizo (la bitácora de su fila, la verificación de una fuente, la prueba en su equipo) en commits separados y con
mensajes que digan qué hizo cada uno.
