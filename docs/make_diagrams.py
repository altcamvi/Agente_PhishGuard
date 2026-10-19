import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

def box(ax, x, y, w, h, text, fc="#E8F0FE", ec="#1F3A93", fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal", wrap=True)

def arrow(ax, p, q, text="", dashed=False, fs=7.5, off=(0, 0.12)):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", lw=1.2, color="#333", ls="--" if dashed else "-"))
    if text: ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, fontsize=fs, ha="center", color="#222")

# ---------- ARQUITECTURA ----------
fig, ax = plt.subplots(figsize=(11, 6.6)); ax.set_xlim(0, 11); ax.set_ylim(0, 6.6); ax.axis("off")
box(ax, 0.2, 5.0, 2.2, 1.1, "Usuario / Administrador\n(Streamlit app.py)", "#FFF4E0", "#B26A00")
box(ax, 0.2, 2.6, 2.2, 1.3, "ENTORNO\nsimulator.py\ncorreos RFC-822\n(SPF/DKIM/DMARC, URLs, adjuntos)", "#EEF7EE", "#2E7D32")
ax.add_patch(Rectangle((3.0, 0.5), 5.3, 5.8, fc="#FAFAFA", ec="#1F3A93", lw=1.8, ls="--"))
ax.text(5.65, 6.08, "PHISHGUARD-AGENT  (agent.py: step = percibir → decidir → actuar)", ha="center", fontsize=9, weight="bold", color="#1F3A93")
box(ax, 3.3, 4.2, 4.7, 1.2, "PERCEPCIÓN  (features.py)\nparse_email · extract · 34 rasgos\n[Percepción · Planificación de comprobaciones]", bold=False)
box(ax, 3.3, 2.5, 4.7, 1.3, "DECISIÓN  (agent.decide)\nRandomForest (modelo aprendido) + umbrales t_warn/t_quar\nconfianza · razones · needs_review\n[Razonamiento y toma de decisiones]")
box(ax, 3.3, 0.8, 4.7, 1.2, "ACCIÓN  (agent.act)\nallow · warn · quarantine · report_admin\n[Llamada de herramientas / Comunicación]")
box(ax, 8.9, 4.6, 1.9, 1.3, "Servicio de\nreputación\n(externo, puede caer)", "#FDECEA", "#B71C1C")
box(ax, 8.9, 2.6, 1.9, 1.3, "MEMORIA\nmemory.py\nestado interno + casos\n+ cola de revisión", "#F3E5F5", "#6A1B9A")
box(ax, 8.9, 0.8, 1.9, 1.2, "Sistema de correo\n(MailSystem)\nbandeja/cuarentena/\nalertas/admin", "#EEF7EE", "#2E7D32")
box(ax, 3.3, 0.05, 4.7, 0.4, "Log JSONL con marca de tiempo (logger.py)", "#FFFFFF", "#555", fs=8)
arrow(ax, (2.4, 3.2), (3.3, 4.6), "correo crudo")
arrow(ax, (2.4, 5.5), (3.3, 5.0), "analizar / feedback", off=(0, 0.15))
arrow(ax, (5.65, 4.2), (5.65, 3.8)); arrow(ax, (5.65, 2.5), (5.65, 2.0))
arrow(ax, (8.0, 4.8), (8.9, 5.1), "lookup()", dashed=True); arrow(ax, (8.9, 4.9), (8.0, 4.6), "", dashed=True)
arrow(ax, (8.0, 2.9), (8.9, 2.9), "estado / casos", dashed=True, off=(0,-0.28)); arrow(ax, (8.0, 1.3), (8.9, 1.3), "efecto")
arrow(ax, (8.9, 3.4), (8.0, 3.4), "reentrena (retrain)", dashed=True, off=(0, 0.12))
plt.savefig("arquitectura.png", dpi=170, bbox_inches="tight"); plt.close()

# ---------- SECUENCIA ----------
def seq(title, parts, msgs, frags, fname, H):
    n = len(parts); fig, ax = plt.subplots(figsize=(11.5, H)); ax.set_xlim(0, n * 1.9); ax.set_ylim(-len(msgs) - 1.5, 1.2); ax.axis("off")
    xs = {p: 0.95 + i * 1.9 for i, p in enumerate(parts)}
    for p, x in xs.items():
        box(ax, x - 0.8, 0.1, 1.6, 0.8, p, "#E8F0FE", "#1F3A93", fs=8)
        ax.plot([x, x], [0.1, -len(msgs) - 1], color="#999", lw=1, ls=":")
    ax.set_title(title, fontsize=10, weight="bold")
    for kind, label, a, b, ins in frags:
        top = -a + 0.45 - ins * 0.15; bot = -b - 0.45 + ins * 0.15; x0 = 0.2 + ins * 0.35
        ax.add_patch(Rectangle((x0, bot), n * 1.9 - 0.4 - 2 * ins * 0.35, top - bot, fc="none", ec="#B26A00", lw=1.2))
        ax.text(x0 + 0.1, top - 0.08, f"{kind} [{label}]", fontsize=7.5, color="#B26A00", va="top", weight="bold")
    for i, (a, b, t, ret) in enumerate(msgs, 1):
        y = -i
        if a == b:
            ax.annotate("", xy=(xs[a] + 0.02, y - 0.2), xytext=(xs[a] + 0.02, y + 0.1), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-1.4", lw=1))
            ax.text(xs[a] + 0.3, y - 0.05, f"{i}. {t}", fontsize=7.2, va="center")
        else:
            ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="->" if not ret else "->", lw=1.1, ls="--" if ret else "-"))
            ax.text((xs[a] + xs[b]) / 2, y + 0.1, f"{i}. {t}", fontsize=7.2, ha="center", va="bottom")
    plt.savefig(fname, dpi=170, bbox_inches="tight"); plt.close()

P = ["Usuario", "Interfaz\n(Streamlit)", "Percepción", "Decisión", "Acción", "Servicio\nreputación", "Sist. correo\n/ Memoria"]
U, I, PE, D, A, R, S = P
m1 = [(U, I, "analizar(correo)", 0), (I, PE, "step(raw) → perceive()", 0), (PE, PE, "parse_email + extract(rasgos)", 0),
      (PE, R, "lookup(dominio remitente)", 0), (R, PE, "score", 1), (PE, R, "lookup(dominio URL)  [por cada URL]", 0), (R, PE, "score / ServiceUnavailable", 1),
      (PE, PE, "reintento; si falla → rep=0.5, confianza×0.85", 0),
      (PE, D, "percepto (vector de rasgos)", 0), (D, D, "predict_proba → riesgo; umbrales; razones", 0),
      (D, A, "decisión {etiqueta, riesgo, acción}", 0), (A, S, "quarantine_msg() / warn() / deliver()", 0),
      (A, S, "store_case(); log(percepción, decisión, acción)", 0), (S, A, "ok", 1), (A, I, "resultado", 1), (I, U, "etiqueta + razones + acción", 1)]
seq("Escenario típico: correo de phishing → cuarentena", P, m1,
    [("loop", "por cada dominio de URL (máx. 5)", 6, 8, 0), ("alt", "responde / no responde", 7, 8, 1)], "secuencia_tipica.png", 6.8)
m2 = [(U, I, "analizar(entrada vacía o sin encabezado From)", 0), (I, PE, "step(raw) → perceive()", 0), (PE, PE, "parse_email → error 'sin From'", 0),
      (PE, D, "percepto {valid=False, error}", 0), (D, D, "etiqueta=indeterminado, confianza=0", 0),
      (D, A, "decisión {acción=report_admin}", 0), (A, S, "notify_admin(evidencia)", 0), (A, S, "log(percepción, decisión, acción)", 0),
      (S, A, "ok", 1), (A, I, "resultado (sin excepción)", 1), (I, U, "aviso: entrada inválida, enviada a revisión humana", 1)]
seq("Escenario de excepción: entrada inválida (sensor sin dato)", P, m2, [("alt", "[else] entrada inválida", 3, 7, 0)], "secuencia_excepcion.png", 5.2)
