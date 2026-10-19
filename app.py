"""Interfaz Streamlit de PHISHGUARD-AGENT (despliegue). Ejecutar:  streamlit run app.py"""
import streamlit as st, pandas as pd
from phishguard.training import load_or_train
from phishguard.simulator import MailEnvironment, ALL_KINDS
from phishguard.agent import PhishGuardAgent
from phishguard.memory import Memory
from phishguard.logger import RunLogger
from phishguard.evaluation import run_all

st.set_page_config(page_title="PhishGuard-Agent", page_icon="🛡️", layout="wide")

@st.cache_resource(show_spinner="Cargando/entrenando el modelo (solo la primera vez)...")
def get_bundle():
    return load_or_train()

if "agent" not in st.session_state:
    env = MailEnvironment(seed=7)
    st.session_state.env = env
    st.session_state.agent = PhishGuardAgent(get_bundle(), env.reputation_service(0.0), RunLogger("logs/app_log.jsonl", "app"), Memory())
    st.session_state.last = None
agent, env = st.session_state.agent, st.session_state.env

st.title("🛡️ PhishGuard-Agent")
st.caption("Agente de aprendizaje para detección de phishing · UTB · Inteligencia Artificial")
tab1, tab2, tab3 = st.tabs(["1. Analizar correo", "2. Retroalimentación y aprendizaje", "3. Ejecutar pruebas (Fase 3)"])

with tab1:
    c1, c2 = st.columns([3, 2])
    with c2:
        down = st.toggle("Simular caída del servicio de reputación", value=False)
        agent.rep.service.p_fail = 1.0 if down else 0.0
        kind = st.selectbox("Generar correo simulado de tipo", ALL_KINDS, index=5)
        if st.button("🎲 Generar correo"):
            st.session_state.raw = env.sample(kind).raw
    with c1:
        raw = st.text_area("Correo crudo (RFC-822). Pegue uno propio o genere uno →", st.session_state.get("raw", ""), height=300)
        up = st.file_uploader("…o suba un archivo .eml", type=["eml", "txt"])
        if up: raw = up.read().decode("utf-8", errors="replace")
    if st.button("Analizar", type="primary"):
        st.session_state.last = agent.step(raw)
    r = st.session_state.last
    if r:
        icon = {"legitimo": "🟢", "sospechoso": "🟠", "phishing": "🔴", "indeterminado": "⚪"}[r["label"]]
        st.subheader(f"{icon} {r['label'].upper()} → acción: {r['action']}")
        m = st.columns(4)
        m[0].metric("Riesgo", "—" if r["risk"] is None else f"{r['risk']:.2f}")
        m[1].metric("Confianza", f"{r['confidence']:.2f}")
        m[2].metric("Tiempo", f"{r['analysis_ms']:.1f} ms")
        m[3].metric("Revisión humana", "Sí" if r["needs_review"] else "No")
        st.write("**Razones:**"); [st.write(f"- {x}") for x in (r["reasons"] or ["Sin señales de riesgo relevantes"])]
        st.caption(f"ID del caso: {r['email_id']} · Bandeja: {len(agent.mail.inbox)} · Cuarentena: {len(agent.mail.quarantine)} · Cola admin: {len(agent.mail.admin_queue)}")
        with st.expander("Log de ejecución (percepción → decisión → acción)"):
            st.code(open("logs/app_log.jsonl", encoding="utf-8").read().splitlines()[-3:].__str__().replace("', '", "'\n'"))

with tab2:
    st.write("El usuario reporta la etiqueta real; el caso queda **pendiente**. Solo tras la aprobación del administrador se usa para reentrenar.")
    ids = list(agent.memory.cases.keys())[-30:]
    if ids:
        eid = st.selectbox("Caso analizado", ids)
        true = st.radio("Etiqueta real", ["legítimo", "phishing"], horizontal=True)
        if st.button("Enviar retroalimentación"):
            agent.memory.submit_feedback(eid, 1 if true == "phishing" else 0)
    pend = agent.memory.pending_ids()
    st.write(f"Casos pendientes de revisión: **{len(pend)}** · Aprobados: **{len(agent.memory.approved())}** · Versión del modelo: **{agent.version}**")
    cA, cB = st.columns(2)
    if cA.button("✅ Aprobar todos los pendientes"):
        for p in pend: agent.memory.review(p, True)
    if cB.button("🔁 Reentrenar (mín. 20 casos aprobados)"):
        n = agent.retrain(); st.success(f"Reentrenado con {n} casos" if n else "Aún no hay suficientes casos aprobados")
    if st.button("Generar 40 correos simulados y cargarlos con su etiqueta real (demo)"):
        for k in ["phish_new_campaign", "legit_newsletter"]:
            for s in env.batch(k, 20):
                e = agent.step(s.raw)["email_id"]; agent.memory.submit_feedback(e, s.label, "demo"); 
        st.rerun()

with tab3:
    reps = st.slider("Repeticiones por escenario", 1, 5, 2); n = st.slider("Correos por escenario", 20, 100, 30, 10)
    st.caption("La configuración completa de la entrega es 5 repeticiones × 100 correos (~4 min). Los umbrales están en thresholds.py.")
    if st.button("▶ Ejecutar pruebas"):
        bar = st.progress(0.0)
        tabla, detalle, extras = run_all(get_bundle(), reps=reps, n=n, results_dir="results_app", log_path="logs/pruebas_app_log.jsonl",
                                         progress=lambda p, msg: bar.progress(min(p, 1.0), msg))
        bar.progress(1.0, "Listo")
        st.dataframe(tabla[["medida", "formula", "umbral", "casos", "resultado", "cumple"]], use_container_width=True)
        st.dataframe(detalle, use_container_width=True)
