"""Configuración y base de conocimiento del agente.

Los UMBRALES DE ACEPTACIÓN se fijan aquí ANTES de ejecutar las pruebas (Fase 3).
"""

# ---- Política de decisión (riesgo en [0,1]) --------------------------------
RISK_WARN = 0.30          # >= : sospechoso -> advertencia + revisión humana
RISK_QUARANTINE = 0.70    # >= : phishing  -> cuarentena
FEED_FLOOR = 0.85         # riesgo mínimo si el dominio está en la fuente de amenazas
MEMORY_PHISH_FLOOR = 0.90 # riesgo mínimo si un caso confirmado previo lo marcó phishing
MEMORY_LEGIT_CAP = 0.29   # riesgo máximo si el remitente fue confirmado legítimo y autentica

# ---- Umbrales de aceptación (fijados antes de las pruebas) -----------------
ACCEPTANCE = {
    "M1_recall": 0.95,          # >= 95 % de phishing detectado
    "M2_fpr": 0.02,             # <= 2 % de falsos positivos
    "M3_latencia_ms": 200.0,    # <= 200 ms por correo (media)
    "M4_manejo_seguro": 1.00,   # 100 % de entradas inválidas/sin dato sin caída
}
REPETICIONES = 5

# ---- Conocimiento del dominio ----------------------------------------------
TRUSTED_BRANDS = {
    "BancoAndino": "bancoandino.com",
    "ShopMax": "shopmax.com",
    "CloudDocs": "clouddocs.io",
    "Universidad Ejemplo": "universidad-ejemplo.edu.co",
    "PagoRapido": "pagorapido.co",
}
TRUSTED_DOMAINS = set(TRUSTED_BRANDS.values())
BRAND_TOKENS = {"bancoandino", "shopmax", "clouddocs", "universidad-ejemplo", "pagorapido"}
TRUSTED_THIRD_PARTY = {"list-manage.com", "mailchimp.com"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "is.gd", "rb.gy"}
SUSPICIOUS_TLDS = {"xyz", "top", "click", "info", "online", "zip", "work", "icu"}
RISKY_EXT = {".exe", ".scr", ".js", ".vbs", ".docm", ".xlsm", ".zip", ".html", ".htm", ".iso", ".rar"}
TWO_LEVEL_SUFFIXES = {"com.co", "edu.co", "org.co", "net.co", "gov.co"}

URGENCY_TERMS = [
    "urgente", "inmediata", "inmediatamente", "24 horas", "suspendid", "bloquead",
    "último aviso", "ultimo aviso", "actividad inusual", "verifique", "confirme ahora",
    "de lo contrario", "immediately", "urgent", "suspended", "final notice", "act now",
]
CREDENTIAL_TERMS = [
    "contraseña", "clave", "tarjeta", "código de seguridad", "codigo de seguridad",
    "cvv", "pin", "número de cuenta", "numero de cuenta", "iniciar sesión", "inicie sesión",
    "password", "credentials", "login", "datos bancarios", "identidad",
]
LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})
