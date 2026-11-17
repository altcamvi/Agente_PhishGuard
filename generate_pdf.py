from fpdf import FPDF
class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "PhishGuard - Informe Hito 2", 0, 1, "R")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_font("helvetica", "", 11)

with open("docs/hito2_informe.md", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            pdf.ln(4)
            continue
        if line.startswith("# "):
            pdf.set_font("helvetica", "B", 16)
            pdf.set_text_color(26, 54, 93)
            pdf.cell(0, 10, line.replace("# ", ""), 0, 1)
            pdf.set_font("helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
        elif line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("helvetica", "B", 13)
            pdf.set_text_color(43, 108, 176)
            pdf.cell(0, 8, line.replace("## ", ""), 0, 1)
            pdf.set_font("helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:].replace("**", "")
            pdf.cell(10)
            pdf.multi_cell(0, 6, f"- {text}")
        else:
            clean_text = line.replace("**", "").replace("`", "")
            pdf.multi_cell(0, 6, clean_text)

pdf.output("docs/hito2_informe.pdf")
print("¡PDF generado con exito en docs/hito2_informe.pdf!")
