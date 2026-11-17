"""Herramientas externas (componente IBM: llamada de herramientas) y actuador del sistema de correo."""
from .simulator import ServiceUnavailable


class ReputationTool:
    """Envuelve el servicio de reputacion: reintenta una vez y degrada con gracia si no responde."""
    def __init__(self, service, retries=1):
        self.service, self.retries = service, retries
        self.calls = self.failures = 0

    def lookup(self, domain):
        for _ in range(self.retries + 1):
            self.calls += 1
            try:
                return self.service.lookup(domain)
            except ServiceUnavailable:
                self.failures += 1
        return None


class NullReputationService:
    def lookup(self, domain):
        return 0.5


class MailSystem:
    """Actuador simulado del sistema de correo: etiquetas, alertas, cuarentena y reportes."""
    def __init__(self):
        self.inbox, self.quarantine, self.alerts, self.admin_queue = [], [], [], []

    def deliver(self, eid):
        self.inbox.append({"id": eid, "tag": "normal"})

    def warn(self, eid, risk, reasons):
        self.inbox.append({"id": eid, "tag": "ADVERTENCIA"})
        self.alerts.append({"id": eid, "risk": round(risk, 3), "reasons": reasons[:3]})

    def quarantine_msg(self, eid):
        self.quarantine.append(eid)

    def notify_admin(self, eid, evidence):
        self.admin_queue.append({"id": eid, **evidence})
