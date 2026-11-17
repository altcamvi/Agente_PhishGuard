from fpdf import FPDF
import re

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'PhishGuard - Informe Hito 2', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# Inicializar PDF
pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# Configurar fuente
pdf.set_font('helvetica', '', 11)

# Leer el archivo Markdown
with open('docs/hito2_informe.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()
    if not line:
        pdf.ln(4)
        continue
    
    # Encabezados principales (#)
    if line.startswith('# '):
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 10, line.replace('# ', ''), 0, 1)
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
    # Subencabezados (##)
    elif line.startswith('## '):
        pdf.ln(4)
        pdf.set_font('helvetica', 'B', 13)
        pdf.set_text_color(43, 108, 176)
        pdf.cell(0, 8, line.replace('## ', ''), 0, 1)
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
    # Viñetas o listas
    elif line.startswith('- ') or line.startswith('* '):
        text = line[2:]
        # Limpiar negritas simples para FPDF básico
        text = text.replace('**', '')
        pdf.cell(10)
        pdf.multi_cell(0, 6, f"• {text}")
    else:
        # Texto normal (limpiando marcas de Markdown comunes)
        clean_text = line.replace('**', '').replace('`', '')
        pdf.multi_cell(0, 6, clean_text)

# Guardar el PDF resultante
pdf.output('docs/hito2_informe.pdf')
print("¡PDF generado con éxito en docs/hito2_informe.pdf!")