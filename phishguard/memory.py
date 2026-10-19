"""Memoria (componente IBM): corto plazo = caso en curso; largo plazo = casos analizados + retroalimentacion."""
import json, os
from datetime import datetime


class Memory:
    def __init__(self, path=None):
        self.short = {}
        self.cases = {}       # email_id -> dict
        self.path = path
        if path and os.path.exists(path):
            self.cases = json.load(open(path, encoding="utf-8"))

    def remember_current(self, **kw):
        self.short = kw

    def store_case(self, eid, vec, predicted, risk):
        self.cases[eid] = {"ts": datetime.now().isoformat(timespec="seconds"), "vec": vec,
                           "predicted": predicted, "risk": risk, "status": "none", "true_label": None}

    def submit_feedback(self, eid, true_label, source="usuario"):
        """El usuario/administrador reporta la etiqueta real; queda PENDIENTE de revision (no entrena aun)."""
        c = self.cases[eid]
        c.update(status="pending", true_label=int(true_label), source=source)
        self._save()

    def review(self, eid, approve):
        self.cases[eid]["status"] = "approved" if approve else "rejected"
        self._save()

    def approved(self):
        return [(c["vec"], c["true_label"]) for c in self.cases.values() if c["status"] == "approved"]

    def pending_ids(self):
        return [k for k, c in self.cases.items() if c["status"] == "pending"]

    def _save(self):
        if self.path:
            json.dump(self.cases, open(self.path, "w", encoding="utf-8"))
