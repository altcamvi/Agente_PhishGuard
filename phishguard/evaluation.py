"""Pruebas de la Fase 3: cada medida de desempeno -> formula, umbral previo, escenarios, repeticiones."""
import os, json, random, statistics as st
from collections import defaultdict
import numpy as np, pandas as pd
from .simulator import MailEnvironment, PHISH_KINDS
from .agent import PhishGuardAgent
from .memory import Memory
from .logger import RunLogger
import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from thresholds import THRESHOLDS

# (id, tipo de caso, generador, etiqueta esperada)
SCENARIOS = [
    ("S01", "normal", "legit_newsletter"), ("S02", "normal", "legit_internal"),
    ("S03", "normal", "legit_transactional"), ("S04", "limite", "legit_urgent"),
    ("S05", "limite", "legit_personal"),
    ("S06", "normal", "phish_credential"), ("S07", "normal", "phish_brand_spoof"),
    ("S08", "normal", "phish_lookalike"), ("S09", "normal", "phish_attachment"),
    ("S10", "limite", "phish_bec"), ("S11", "limite", "phish_compromised"),
    ("S12", "falla esperada", "reputacion_caida"), ("S13", "falla esperada", "entradas_invalidas"),
    ("S14", "aprendizaje", "campana_nueva"),
]
LEGIT_S = ["S01", "S02", "S03", "S04", "S05"]
PHISH_S = ["S06", "S07", "S08", "S09", "S10", "S11"]


def invalid_inputs(rng):
    garbage = "".join(chr(rng.randint(1, 255)) for _ in range(200))
    return ["", "   \n\t", None, 12345, b"\x00\x01\xff\xfe binario", "texto suelto sin encabezados",
            "To: a@b.com\nSubject: x\n\nhola", "From: roto\n\nhola", "From: a@b.com\nSubject: vacio\n\n",
            "x" * 300000 if rng.random() < 2 else garbage, garbage]


def detected(r):  # el agente lo marco como riesgo (advertencia o cuarentena)
    return r["action"] in ("warn", "quarantine")


def mean_std(v):
    return float(np.mean(v)), (float(st.stdev(v)) if len(v) > 1 else 0.0)


def run_all(bundle, reps=5, n=100, results_dir="results", log_path="logs/pruebas_agent_log.jsonl", progress=None):
    os.makedirs(results_dir, exist_ok=True)
    if os.path.exists(log_path): os.remove(log_path)
    logger = RunLogger(log_path, run_id="pruebas")
    rows = []          # una fila por correo
    for rep in range(reps):
        base = 90_000 + rep * 1000
        for idx, (sid, tipo, kind) in enumerate(SCENARIOS):
            if progress: progress((rep * len(SCENARIOS) + idx) / (reps * len(SCENARIOS)), f"rep {rep + 1}/{reps} - {sid}")
            env = MailEnvironment(base + idx)
            rng = random.Random(base + idx)
            mk = lambda p_fail, s: env.reputation_service(p_fail, seed=base + idx + s)
            if sid == "S13":
                agent = PhishGuardAgent(bundle, mk(0.0, 0), logger, Memory())
                for i, raw in enumerate(invalid_inputs(rng)):
                    eid = f"T-{sid}-r{rep}-{i}"
                    try:
                        r = agent.step(raw, eid); ok = (not r["valid"]) and r["action"] == "report_admin"
                        err = ""
                    except Exception as e:
                        r, ok, err = {"action": "EXCEPCION", "analysis_ms": 0.0, "label": ""}, False, type(e).__name__
                    rows.append(dict(rep=rep, scenario=sid, kind=kind, email_id=eid, true=-1, action=r["action"],
                                     label=r["label"], risk=None, ms=r["analysis_ms"], ok=ok, err=err))
                continue
            if sid == "S14":
                rows += run_learning(bundle, env, mk, rep, sid, logger, n)
                continue
            if sid == "S12":
                samples = [env.sample(rng.choice(PHISH_KINDS)) for _ in range(n)] + \
                          [env.sample(rng.choice(["legit_newsletter", "legit_internal", "legit_transactional", "legit_urgent", "legit_personal"])) for _ in range(n)]
                svc = mk(1.0, 0)            # servicio de reputacion caido
            else:
                samples = env.batch(kind, n); svc = mk(0.05, 0)
            agent = PhishGuardAgent(bundle, svc, logger, Memory())
            for i, s in enumerate(samples):
                eid = f"T-{sid}-r{rep}-{i}"
                r = agent.step(s.raw, eid)
                rows.append(dict(rep=rep, scenario=sid, kind=s.kind, email_id=eid, true=s.label, action=r["action"],
                                 label=r["label"], risk=r["risk"], ms=r["analysis_ms"], ok=(detected(r) == bool(s.label)), err=""))
    logger.close()
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(results_dir, "casos.csv"), index=False)
    return summarize(df, reps, log_path, results_dir)


def run_learning(bundle, env, mk, rep, sid, logger, n):
    """S14: campana nueva -> retroalimentacion -> revision -> reentrenamiento controlado."""
    rows = []
    agent = PhishGuardAgent(bundle, mk(0.05, 0), logger, Memory())
    def evalset(tag, new_n, leg_n):
        out = []
        for i, s in enumerate(env.batch("phish_new_campaign", new_n) + [env.sample("legit_" + env.rng.choice(["newsletter", "internal", "transactional", "personal"])) for _ in range(leg_n)]):
            eid = f"T-{sid}-r{rep}-{tag}-{i}"
            r = agent.step(s.raw, eid)
            out.append(dict(rep=rep, scenario=sid, kind=f"{tag}:{s.kind}", email_id=eid, true=s.label, action=r["action"],
                            label=r["label"], risk=r["risk"], ms=r["analysis_ms"], ok=(detected(r) == bool(s.label)), err=""))
        return out
    rows += evalset("antes", n, 2 * n)
    # retroalimentacion: 60 campana nueva + 60 legitimos + 5 etiquetas ERRONEAS que el revisor rechaza
    fb = []
    for s in env.batch("phish_new_campaign", 60) + [env.sample("legit_newsletter") for _ in range(60)]:
        eid = f"T-{sid}-r{rep}-fb-{len(fb)}"; agent.step(s.raw, eid); fb.append((eid, s.label))
    for j, (eid, lab) in enumerate(fb):
        wrong = j in (0, 1, 2, 70, 71)
        agent.memory.submit_feedback(eid, (1 - lab) if wrong else lab, source="usuario")
        agent.memory.review(eid, approve=not wrong)
    agent.retrain(min_cases=20)
    rows += evalset("despues", n, 2 * n)
    return rows


def check(name, value):
    t = THRESHOLDS[name]
    return (value >= t["value"]) if t["op"] == ">=" else (value <= t["value"])


def summarize(df, reps, log_path, results_dir):
    per_rep = defaultdict(list)
    for rep in range(reps):
        d = df[df.rep == rep]
        phish = d[d.scenario.isin(PHISH_S)]; legit = d[d.scenario.isin(LEGIT_S)]
        per_rep["M1"].append((phish.ok).mean()); per_rep["M2"].append(1 - (legit.ok).mean())
        per_rep["M3"].append(d[d.scenario.isin(LEGIT_S + PHISH_S)].ms.mean())
        per_rep["M4"].append(d[d.scenario == "S13"].ok.mean())
        s12 = d[d.scenario == "S12"]
        per_rep["M5a"].append(s12[s12.true == 1].ok.mean()); per_rep["M5b"].append(1 - s12[s12.true == 0].ok.mean())
        s14 = d[d.scenario == "S14"]
        a = s14[s14.kind.str.startswith("antes:phish")].ok.mean(); b = s14[s14.kind.str.startswith("despues:phish")].ok.mean()
        per_rep["M7"].append(b - a); per_rep["M7_antes"].append(a); per_rep["M7_despues"].append(b)
        per_rep["M7_fpr"].append(1 - s14[s14.kind.str.startswith("despues:legit")].ok.mean())
    # M6: trazabilidad del log
    ev = defaultdict(set); ts_ok = True
    for line in open(log_path, encoding="utf-8"):
        r = json.loads(line)
        if str(r["email_id"]).startswith("T-"):
            ev[r["email_id"]].add(r["phase"]); ts_ok &= bool(r.get("ts"))
    m6 = np.mean([{"percepcion", "decision", "accion"} <= p for p in ev.values()]) if ev and ts_ok else 0.0
    per_rep["M6"] = [m6]
    n_ok = lambda ids: int(df[df.scenario.isin(ids)].shape[0])
    spec = [
        ("M1_recall_phishing", "M1", "Recall = phishing detectados (advertencia o cuarentena) / phishing totales", n_ok(PHISH_S), "S06-S11"),
        ("M2_falsos_positivos", "M2", "FPR = legitimos con alerta (advertencia o cuarentena) / legitimos totales", n_ok(LEGIT_S), "S01-S05"),
        ("M3_tiempo_medio_ms", "M3", "Tiempo medio de step() por correo (ms), incluye registro en log", n_ok(LEGIT_S + PHISH_S), "S01-S11"),
        ("M4_manejo_entradas_invalidas", "M4", "Entradas invalidas manejadas sin excepcion y reportadas / entradas invalidas", n_ok(["S13"]), "S13"),
        ("M5a_recall_sin_reputacion", "M5a", "Recall con servicio de reputacion caido (p_fail=1)", int((df[df.scenario == 'S12'].true == 1).sum()), "S12"),
        ("M5b_fpr_sin_reputacion", "M5b", "FPR con servicio de reputacion caido (p_fail=1)", int((df[df.scenario == 'S12'].true == 0).sum()), "S12"),
        ("M6_trazabilidad_log", "M6", "Ejecuciones con eventos percepcion+decision+accion y ts / ejecuciones", len(ev), "todos"),
        ("M7_mejora_por_aprendizaje", "M7", "Recall(despues) - Recall(antes) en campana nueva tras reentrenar", int(df[df.scenario == 'S14'].shape[0]), "S14"),
    ]
    out = []
    for name, key, formula, cases, scn in spec:
        m, s = mean_std(per_rep[key]); t = THRESHOLDS[name]
        pct = key not in ("M3",)
        fmt = (lambda x: f"{x * 100:.2f}%") if pct else (lambda x: f"{x:.1f} ms")
        out.append(dict(medida=name, formula=formula, umbral=f"{t['op']} {fmt(t['value'])}", casos=cases, escenarios=scn,
                        resultado=f"{fmt(m)} ± {fmt(s) if pct else f'{s:.1f} ms'}", cumple="SI" if check(name, m) else "NO",
                        media=m, desv=s, repeticiones=len(per_rep[key]), evidencia="results/casos.csv; logs/pruebas_agent_log.jsonl"))
    tabla = pd.DataFrame(out)
    tabla.to_csv(os.path.join(results_dir, "tabla_resultados.csv"), index=False)
    # detalle por escenario
    det = []
    for sid, tipo, kind in SCENARIOS:
        g = df[df.scenario == sid]
        if g.empty: continue
        per = [g[g.rep == r].ok.mean() for r in range(reps)]
        m, s = mean_std(per)
        det.append(dict(escenario=sid, tipo=tipo, generador=kind, casos_por_rep=len(g[g.rep == 0]), repeticiones=reps,
                        acierto_media=round(m, 4), acierto_std=round(s, 4), ms_medio=round(g.ms.mean(), 2)))
    detalle = pd.DataFrame(det); detalle.to_csv(os.path.join(results_dir, "detalle_por_escenario.csv"), index=False)
    extras = {"M7_antes": mean_std(per_rep["M7_antes"]), "M7_despues": mean_std(per_rep["M7_despues"]), "M7_fpr_despues": mean_std(per_rep["M7_fpr"])}
    json.dump(extras, open(os.path.join(results_dir, "extras.json"), "w"))
    return tabla, detalle, extras
