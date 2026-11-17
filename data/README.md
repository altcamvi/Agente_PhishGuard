# data/

Esta carpeta **no contiene correos**. Los datos crudos no se suben al repositorio (ver `.gitignore`);
se descargan con un script y se anonimizan antes de usarse.

## Estado

- **Hito 1 (propuesta):** fuentes y condiciones de uso declaradas. El simulador (`src/phishguard/simulator.py`)
  sigue siendo la única fuente usada por el código actual.
- **Pendiente (Hito 2):** `download_data.py` (descarga y verificación), `anonymize.py` (direcciones, nombres,
  teléfonos) y partición 70/15/15 estratificada con semilla 42, tras eliminar duplicados.

## Fuentes previstas

| Fuente | Rol | Términos de uso |
|---|---|---|
| Nazario Phishing Corpus (monkey.org/~jose/phishing) | Phishing | **PENDIENTE DE VERIFICAR**: copiar aquí lo que diga el sitio |
| SpamAssassin public corpus (spamassassin.apache.org/publiccorpus) | Legítimo (ham) | **PENDIENTE DE VERIFICAR** |
| Enron, Carnegie Mellon (cs.cmu.edu/~enron) | Legítimo, correo corporativo | **PENDIENTE DE VERIFICAR** |

Subconjunto en español: por buscar. Si no existe, se declara como limitación.
