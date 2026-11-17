import markdown
from weasyprint import HTML

# Leer el informe Markdown
with open("docs/hito2_informe.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Convertir Markdown a HTML con estilo básico
html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

html_full = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
  h1, h2, h3 {{ color: #1a365d; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
  th, td {{ border: 1px solid #cbd5e0; padding: 8px 12px; text-align: left; }}
  th {{ background-color: #f7fafc; }}
  code {{ background-color: #edf2f7; padding: 2px 4px; border-radius: 4px; }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

# Guardar como PDF
HTML(string=html_full).write_pdf("docs/hito2_informe.pdf")
print("¡PDF generado con éxito en docs/hito2_informe.pdf!")