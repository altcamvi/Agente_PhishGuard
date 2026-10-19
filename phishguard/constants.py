BRANDS = {"PayPal": "paypal.com", "Bancolombia": "bancolombia.com", "Microsoft": "microsoft.com",
          "Amazon": "amazon.com", "Google": "google.com", "DHL": "dhl.com",
          "Netflix": "netflix.com", "Davivienda": "davivienda.com"}
INTERNAL_DOMAIN = "utb.edu.co"
FREE_PROVIDERS = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]
SHORTENERS = ["bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd"]
SUSPICIOUS_TLDS = ["xyz", "top", "click", "icu", "rest", "gq", "tk"]
FREE_HOSTING = ["web.app", "pages.dev", "blogspot.com", "weebly.com", "github.io"]
RISKY_EXT = ["html", "htm", "zip", "exe", "docm", "iso", "js", "scr", "xlsm", "rar"]

# Listas de palabras que usa el agente (sin tildes, minuscula)
URGENCY_WORDS = ["urgente", "inmediatamente", "ultima oportunidad", "24 horas", "accion requerida",
                 "suspendida", "expira", "ahora mismo", "de inmediato"]
CREDENTIAL_WORDS = ["verifique", "confirme su", "contrasena", "clave", "inicie sesion",
                    "datos bancarios", "identidad", "credenciales"]
MONEY_WORDS = ["transferencia", "pago", "factura", "reembolso", "deposito", "premio"]

MAX_CHARS = 200_000
