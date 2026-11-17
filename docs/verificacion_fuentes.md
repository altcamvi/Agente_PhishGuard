
## 1. Cifras de la propuesta

| Cifra | Resultado | Fuente encontrada | Cuidado al citarla |
|---|---|---|---|
| 79,83 % | **Confirmada**, pero es el peso del **fraude** en general, no del phishing. Corresponde a los últimos dos años de incidentes gestionados por ColCERT. | MinTIC, nota sobre el Informe de Tendencias de Amenazas Cibernéticas 2025 (mintic.gov.co/portal/715/w3-article-433511.html) | Redactar «el fraude representó el 79,83 % de los incidentes», no «el phishing». |
| 835 casos | **Confirmada**: casos de phishing en ese mismo periodo; el uso no autorizado de cuentas de correo suma 784. | Misma nota de MinTIC | Aclarar que son casos gestionados por ColCERT, no el total nacional de ataques. |
| 74 % | **Confirmada**: Bloomberg Línea atribuye a Policía Nacional y Fortinet que el 74 % de los ciberataques registrados en Colombia en 2024 empezó en un correo electrónico fraudulento. | Bloomberg Línea, «Colombia enciende alarmas…» (bloomberglinea.com/latinoamerica/colombia/colombia-es-el-cuarto-pais-de-la-region-con-mas-ciberataques/) | Es «origen en correo», no «phishing». **No confundir** con otro 74 % que circula (TransUnion: caída del fraude digital en 2025, publicado en La República) ni con el 74 % de errores humanos de otro informe. |

Verificado por (integrante / fecha): Ruben Gonzalez Caro / 16-11-2026

## 2. Referencia arXiv:2405.11619

- **Existe y coincide** con el tema: Al-Subaiey, Al-Thani, Alam, Antora, Khandakar y Zaman, *Novel Interpretable and
  Robust Web-based AI Platform for Phishing Email Detection*, enviada el 19-may-2024.
- Reporta F1 de 0,99 sobre un conjunto de unos 82 500 correos que combina Enron, Ling, CEAS, Nazario, Nigerian
  Fraud y SpamAssassin, y añade IA explicable y una aplicación web.
- **Limitación de esta verificación:** no pude abrir arxiv.org directamente. La confirmé por la ficha del conjunto
  de datos en Kaggle/Baselight (que cita el artículo con ese identificador), un resumen espejado del artículo y el
  listado de arXiv. Abrir https://arxiv.org/abs/2405.11619 y comprobar autores, título y año.
- Al citarla, tener presente que su F1 de 0,99 viene de mezclar fuentes de épocas distintas; la propia
  propuesta pretende evaluar dejando una fuente fuera, que es más exigente.

Verificado por (integrante / fecha): Camilo Villadiego Iriarte / 16-11-2026

## 3. Términos de uso de los corpus

Ver tabla en `data/README.md`. Resumen: SpamAssassin y Enron se leyeron en sus páginas oficiales (sin licencia
formal, con avisos del autor); 

Verificado por (integrante / fecha): Ruben Gonzalez Caro / 16-11-2026

## 3b. Actualización del 2026-11-12

- **SpamAssassin:** el índice (spamassassin.apache.org/old/publiccorpus/) se abrió y lista `20030228_easy_ham`, `20030228_easy_ham_2` y `20030228_hard_ham` (los tres `.tar.bz2`), que son los que descarga el script. Hay además versiones `20021010_*` que se solapan; el script no las baja.
- **Enron:** la página de CMU se releyó; la versión vigente es `enron_mail_20150507.tar.gz` (≈ 1,7 GB). Advierte, desde abril de 2026, de dudas sobre la autenticidad de algunas cuentas, que según la propia página probablemente no afectan los usos de NLP.
- **Nazario:** sigue sin poder abrirse el sitio desde la herramienta. Fuentes de terceros coinciden en que publica archivos anuales (`phishing-2020` a `phishing-2025`), los antiguos `phishing0` a `phishing3` (2005–2007) y `private-phishing4.mbox`. Una ficha de Hugging Face afirma licencia CC-BY-4.0,

## 4. Riesgos de datos que aparecieron al buscar (para discutir, no son hechos del proyecto)

1. **Época distinta por clase.** El *ham* previsto (SpamAssassin, Enron) es de 2000–2003 aproximadamente (los
   nombres de archivo de SpamAssassin indican 2002–2003; Enron termina en 2002). Un repositorio de terceros señala
   que el Nazario reciente es de 2020–2025. Si el phishing es nuevo y el legítimo es viejo, el modelo puede
   aprender la época y no el phishing.
2. **Una sola bandeja.** Ese mismo repositorio indica que el Nazario reciente se recolectó en un único buzón
   (jose@monkey.org) y que cerca del 70 % de esos correos lo nombran en el texto: otro atajo posible. Es una
   afirmación de un tercero; comprobarla en los datos.
3. **Duplicados casi idénticos.** Un estudio de 2026 (NHSJS, «Cross-Dataset Fragility of Phishing Detectors», solo se leyó el fragmento de la búsqueda) reporta que perdió cerca del 27 % de Nazario al quitar casi duplicados y que un clasificador que solo ve el nombre de la fuente alcanza AUC 1,000 cuando cada fuente tiene una sola clase. En el proyecto ocurre lo mismo: cada fuente es de una sola clase, así que la fuente predice la etiqueta por construcción. Por eso importan M5, M6 y `shortcut_tokens.csv`, y `make_splits.py` genera `near_duplicates.csv` (con `--near-dedup` se eliminan).
4. **«Dejar una fuente fuera».** Si todo el phishing viene de Nazario, dejarlo fuera elimina la clase positiva y
   la prueba no se puede calcular. La propuesta debe aclarar cómo se aplica o añadir otra fuente de phishing
   (por ejemplo, el Nigerian Fraud del conjunto de 82 500 correos). **La propuesta entregada ya lo incorpora** (tabla de fuentes y M5); falta consultar sus condiciones de uso.
