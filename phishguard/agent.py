"""
PHISHGUARD-AGENT: ciclo PERCEPCION -> DECISION -> ACCION.
Tipo de agente: de aprendizaje (modelo supervisado + reentrenamiento controlado con casos revisados),
con reglas de politica (umbrales) y estado interno (memoria).
"""
import time, uuid, copy
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from .features import parse_email, extract, FEATURE_NAMES
from .tools import ReputationTool, MailSystem, NullReputationService
from .logger import NullLogger
from .memory import Memory

REASONS = {
    "spf_fail": "SPF fallido (el servidor no esta autorizado a enviar por ese dominio)",
    "dkim_fail": "Firma DKIM invalida", "dmarc_fail": "DMARC fallido",
    "auth_missing": "Sin resultados de autenticacion (SPF/DKIM/DMARC)",
    "from_free_provider": "Remitente de un proveedor de correo gratuito",
    "display_brand_mismatch": "El nombre mostrado aparenta una marca, pero el dominio no coincide",
    "reply_to_mismatch": "Reply-To apunta a un dominio distinto del remitente",
    "sender_lookalike": "Dominio del remitente muy parecido al de una marca conocida",
    "sender_susp_tld": "TLD sospechoso en el remitente",
    "url_ip": "Enlace con direccion IP en lugar de dominio", "url_shortener": "Enlace acortado (destino oculto)",
    "url_susp_tld": "Enlace con TLD sospechoso", "url_lookalike": "Enlace a dominio parecido a una marca",
    "url_free_hosting": "Enlace a hosting gratuito", "url_http": "Enlace sin cifrado (http)",
    "attach_risky": "Adjunto de tipo potencialmente peligroso", "attach_double_ext": "Adjunto con doble extension",
    "urgency_count": "Lenguaje de urgencia/presion", "credential_count": "Solicita credenciales o datos sensibles",
    "money_count": "Menciona pagos o transferencias",
}


def make_model(seed=0):
    return RandomForestClassifier(n_estimators=150, min_samples_leaf=3, class_weight="balanced",
                                  random_state=seed, n_jobs=1)


class PhishGuardAgent:
    def __init__(self, bundle, reputation_service=None, logger=None, memory=None, mail=None, min_conf=0.5):
        self.bundle = bundle
        self.model = bundle["model"]
        self.t_warn, self.t_quar = bundle["t_warn"], bundle["t_quar"]
        self.version = bundle.get("version", 1)
        self.rep = ReputationTool(reputation_service or NullReputationService())
        self.log = logger or NullLogger()
        self.memory = memory or Memory()
        self.mail = mail or MailSystem()
        self.min_conf = min_conf

    # ---------------- PERCEPCION ----------------
    def perceive(self, raw, eid):
        try:
            msg, err = parse_email(raw)
            if err:
                percept = {"valid": False, "error": err}
            else:
                vec, feats, meta = extract(msg, self.rep)
                percept = {"valid": True, "vec": vec, "feats": feats, "meta": meta}
        except Exception as e:  # el agente nunca debe caerse por una entrada rara
            percept = {"valid": False, "error": f"excepcion de percepcion: {type(e).__name__}"}
        self.memory.remember_current(email_id=eid, percept=percept)
        self.log.log(eid, "percepcion", valid=percept["valid"], error=percept.get("error"),
                     meta=percept.get("meta"),
                     signals=[k for k in REASONS if percept.get("feats", {}).get(k)] if percept["valid"] else None,
                     rep_ok=(percept["feats"]["rep_sender_ok"] and percept["feats"]["rep_url_ok"]) if percept["valid"] else None)
        return percept

    # ---------------- DECISION ----------------
    def decide(self, percept, eid):
        if not percept["valid"]:
            d = {"label": "indeterminado", "risk": None, "confidence": 0.0, "needs_review": True,
                 "reasons": [percept["error"]], "action": "report_admin"}
        else:
            risk = float(self.model.predict_proba(np.array([percept["vec"]]))[0][1])
            label = "legitimo" if risk < self.t_warn else ("sospechoso" if risk < self.t_quar else "phishing")
            conf = abs(risk - 0.5) * 2
            f = percept["feats"]
            if not (f["rep_sender_ok"] and f["rep_url_ok"]):
                conf *= 0.85   # menor confianza si la fuente externa no respondio
            needs_review = label == "sospechoso" and conf < self.min_conf
            reasons = [txt for k, txt in REASONS.items() if f.get(k)]
            action = {"legitimo": "allow", "sospechoso": "warn", "phishing": "quarantine"}[label]
            d = {"label": label, "risk": risk, "confidence": conf, "needs_review": needs_review,
                 "reasons": reasons, "action": action}
        self.log.log(eid, "decision", **d)
        return d

    # ---------------- ACCION ----------------
    def act(self, percept, d, eid):
        a = d["action"]
        if a == "allow": self.mail.deliver(eid)
        elif a == "warn": self.mail.warn(eid, d["risk"], d["reasons"])
        elif a == "quarantine": self.mail.quarantine_msg(eid)
        if a == "report_admin" or d["needs_review"]:
            self.mail.notify_admin(eid, {"label": d["label"], "risk": d["risk"], "reasons": d["reasons"]})
        if percept["valid"]:
            self.memory.store_case(eid, percept["vec"], d["label"], d["risk"])
        self.log.log(eid, "accion", action=a, reported_to_admin=(a == "report_admin" or d["needs_review"]))

    def step(self, raw, email_id=None):
        eid = email_id or uuid.uuid4().hex[:8]
        t0 = time.perf_counter()
        percept = self.perceive(raw, eid)
        d = self.decide(percept, eid)
        self.act(percept, d, eid)
        out = dict(d, email_id=eid, valid=percept["valid"], analysis_ms=(time.perf_counter() - t0) * 1000)
        out["meta"] = percept.get("meta")
        return out

    # ---------------- APRENDIZAJE (controlado) ----------------
    def retrain(self, min_cases=20):
        """Reentrena SOLO con casos aprobados por un revisor. Devuelve numero de casos incorporados."""
        new = self.memory.approved()
        if len(new) < min_cases:
            return 0
        X = np.vstack([self.bundle["X"], np.array([v for v, _ in new])])
        y = np.concatenate([self.bundle["y"], np.array([l for _, l in new])])
        m = make_model(seed=self.version)
        m.fit(X, y)
        self.model = m
        self.version += 1
        self.bundle = dict(self.bundle, model=m, X=X, y=y, version=self.version)
        self.log.log("-", "aprendizaje", version=self.version, casos_incorporados=len(new))
        return len(new)
