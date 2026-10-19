"""Registro (log) de ejecucion en JSON Lines: percepcion, decision y accion con marca de tiempo."""
import json, os
from datetime import datetime


class RunLogger:
    def __init__(self, path, run_id="run"):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.f = open(path, "a", encoding="utf-8")
        self.run_id = run_id

    def log(self, email_id, phase, **data):
        rec = {"ts": datetime.now().isoformat(timespec="milliseconds"), "run_id": self.run_id,
               "email_id": email_id, "phase": phase, **data}
        self.f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


class NullLogger:
    def log(self, *a, **k): pass
    def close(self): pass
