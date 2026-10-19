# Bitácora de uso de IA — PhishGuard-Agent

> Borrador generado al finalizar el trabajo. **Los integrantes deben revisarla, completar sus propias interacciones y confirmar que refleja lo que realmente hicieron.**

| Fecha | Herramienta | Para qué se usó | Qué se aceptó / modificó | Cómo se verificó |
|---|---|---|---|---|
| 2026-10-18 | Claude (Anthropic) | Matriz de decisión Fase 1: propuesta de puntajes y evidencias para los dos agentes | Se aceptó la propuesta como base; los integrantes deben validar cada puntaje | Recalculo de S y de la sensibilidad (ver informe, sección Fase 1) |
| 2026-10-18 | Claude | Diseño y código del agente (percepción, decisión, acción, memoria, reentrenamiento), simulador de correo y app Streamlit | Código aceptado tras ejecutarlo; se corrigió el simulador al ver que la validación daba recall 100 % (rasgos que eran artefactos de plantillas) | Ejecución de `python -m phishguard.training`, `python run_tests.py` y prueba de arranque de la app |
| 2026-10-18 | Claude | Scripts de pruebas Fase 3 y umbrales | Umbrales fijados en `thresholds.py` antes de ejecutar las pruebas | Una sola ejecución completa de las pruebas; resultados en `results/` y `logs/` |
| 2026-10-18 | Claude | Diagramas (arquitectura y secuencia) y redacción del documento ajustado | Texto de las secciones 1–8 adaptado del diseño original de Rubén González; secciones nuevas redactadas con IA | Revisión visual del PDF; cifras tomadas de `results/*.csv` |

**Limitaciones reconocidas:** los datos son sintéticos; la dificultad del simulador la fijó la IA con nuestra aprobación. Ver sección 9.8 del informe.
