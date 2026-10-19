"""
UMBRALES DE ACEPTACION (Fase 3).
Fijados ANTES de ejecutar las pruebas. No modificar despues de ver resultados;
si una medida se reformula, documentarlo en la tabla de cambios del informe.
"""
THRESHOLDS = {
    "M1_recall_phishing":        {"op": ">=", "value": 0.95, "desc": "Recall de phishing (condiciones normales)"},
    "M2_falsos_positivos":       {"op": "<=", "value": 0.02, "desc": "Tasa de falsos positivos (cualquier alerta sobre legitimo)"},
    "M3_tiempo_medio_ms":        {"op": "<=", "value": 200.0, "desc": "Tiempo medio de analisis por correo (ms)"},
    "M4_manejo_entradas_invalidas": {"op": ">=", "value": 1.00, "desc": "Entradas invalidas manejadas sin excepcion y escaladas al administrador"},
    "M5a_recall_sin_reputacion": {"op": ">=", "value": 0.85, "desc": "Recall con servicio de reputacion caido"},
    "M5b_fpr_sin_reputacion":    {"op": "<=", "value": 0.05, "desc": "Falsos positivos con servicio de reputacion caido"},
    "M6_trazabilidad_log":       {"op": ">=", "value": 1.00, "desc": "Ejecuciones con eventos percepcion+decision+accion y marca de tiempo"},
    "M7_mejora_por_aprendizaje": {"op": ">=", "value": 0.20, "desc": "Mejora de recall (puntos) en campana nueva tras reentrenar con casos aprobados"},
}
