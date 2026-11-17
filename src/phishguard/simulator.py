"""
Entorno simulado de correo (seccion 5 del diseno: entradas y sensores).
Genera correos RFC-822 completos (encabezados, SPF/DKIM/DMARC, URLs, adjuntos) con
aleatoriedad (ambiente estocastico) y SOLAPAMIENTO deliberado entre clases:
legitimos con urgencia o autenticacion fallida, phishing con autenticacion valida o sin enlaces.
Tambien simula el servicio externo de reputacion (puede caer).
"""
import random
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from dataclasses import dataclass
from .constants import *

PRE = ["tienda", "revista", "cafe", "viaje", "libro", "salud", "energia", "cine", "moda", "deporte", "clinica", "hotel", "museo", "radio"]
SUF = ["verde", "norte", "andina", "plus", "online", "mundo", "express", "digital", "caribe", "global"]
NAMES = ["Laura Gomez", "Carlos Perez", "Ana Torres", "Jorge Ruiz", "Marta Diaz", "Luis Herrera", "Sofia Castro"]
LEGIT_NEWS = ["Conoce las novedades de este mes en nuestra tienda.", "Te compartimos los articulos mas leidos de la semana.",
              "Descubre nuestra nueva coleccion de temporada.", "Gracias por suscribirte a nuestro boletin.",
              "Estas son las actividades del fin de semana en la ciudad.", "Consulta el calendario de eventos y reserva tu lugar."]
LEGIT_INTERNAL = ["Adjunto el acta de la reunion de ayer.", "Les recuerdo que el comite se realizara el jueves a las 3 pm.",
                  "Por favor revisen el documento y envien sus comentarios.", "Quedo atento a sus observaciones sobre el cronograma.",
                  "Les comparto el enlace a la carpeta del proyecto."]
LEGIT_TRANS = ["Hemos recibido tu pedido y lo estamos preparando.", "Tu factura del mes esta disponible en tu cuenta.",
               "Para restablecer tu contrasena usa el enlace que solicitaste. Si no fuiste tu, ignora este mensaje.",
               "Confirma tu reserva ingresando a tu cuenta.", "Tu codigo de verificacion es {code}. No lo compartas con nadie."]
URGENCY = ["Es urgente que actue", "Hagalo inmediatamente", "Ultima oportunidad", "Tiene 24 horas", "Accion requerida",
           "Su cuenta sera suspendida", "Esta oferta expira hoy", "Responda ahora mismo", "Sin demora, por favor", "No lo pase por alto"]
CRED = ["Verifique su cuenta", "Confirme su contrasena", "Actualice sus datos bancarios", "Inicie sesion para continuar",
        "Valide su identidad", "Ingrese sus credenciales", "Revise el acceso a su cuenta"]
MONEY = ["Tiene un pago pendiente", "Factura vencida", "Realice la transferencia", "Reembolso disponible", "Ha ganado un premio"]
RISKY_FILES = ["factura.html", "documento.zip", "pago.exe", "orden.docm", "factura.pdf.exe", "scan.iso", "reporte.pdf"]
PHISH_KINDS = ["phish_credential", "phish_brand_spoof", "phish_lookalike", "phish_attachment", "phish_bec", "phish_compromised"]
LEGIT_KINDS = ["legit_newsletter", "legit_internal", "legit_transactional", "legit_urgent", "legit_personal"]
ALL_KINDS = LEGIT_KINDS + PHISH_KINDS + ["phish_new_campaign"]


class ServiceUnavailable(Exception):
    pass


class ReputationService:
    """Servicio externo simulado (inteligencia de amenazas). Cobertura parcial y disponibilidad estocastica."""
    def __init__(self, bad, good, p_fail=0.0, seed=0):
        self.bad, self.good, self.p_fail = bad, good, p_fail
        self.rng = random.Random(seed)

    def lookup(self, domain):
        if self.rng.random() < self.p_fail:
            raise ServiceUnavailable("timeout del servicio de reputacion")
        if domain in self.bad:
            return 0.95
        if domain in self.good:
            return 0.05
        return 0.5


@dataclass
class Sample:
    raw: str
    label: int          # 1 = phishing, 0 = legitimo
    kind: str


class MailEnvironment:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.bad, self.good = set(), set(BRANDS.values()) | {INTERNAL_DOMAIN, "drive.google.com"} | set(SHORTENERS[:0])
        self.good |= {"click.mailerservice.net", "links.sendmailer.com", "track.newsmailer.io"}
        self.n = 0

    def reputation_service(self, p_fail=0.0, seed=0):
        return ReputationService(self.bad, self.good, p_fail, seed)

    # ---------- utilidades ----------
    def _pick(self, d):
        return self.rng.choices(list(d.keys()), weights=list(d.values()))[0]

    def _legit_domain(self):
        return f"{self.rng.choice(PRE)}{self.rng.choice(SUF)}.{self.rng.choice(['com', 'co', 'org', 'net', 'com.co'])}"

    def _rand_domain(self, susp=False):
        w = "".join(self.rng.choices("abcdefghijklmnopqrstuvwxyz", k=self.rng.randint(5, 10)))
        if self.rng.random() < 0.3:
            w += f"-{self.rng.choice(['secure', 'login', 'verify', 'help'])}"
        if self.rng.random() < 0.25:
            w += str(self.rng.randint(1, 99))
        tld = self.rng.choice(SUSPICIOUS_TLDS) if susp else self.rng.choice(["com", "net", "info", "online", "xyz"])
        return f"{w}.{tld}"

    def _lookalike(self, dom):
        name, _, tld = dom.partition(".")
        r = self.rng.random()
        if r < 0.3: name = name.replace("o", "0", 1) if "o" in name else name + "-"
        elif r < 0.55: name = name.replace("l", "1", 1) if "l" in name else name + "1"
        elif r < 0.75: name = name.replace("m", "rn", 1) if "m" in name else name + "s"
        elif r < 0.9: name = name + "-secure"
        else: name = name[:-1] + name[-1] * 2
        if name == dom.partition(".")[0]:
            name += "x"
        return f"{name}.{tld}"

    def _register(self, dom, is_bad, p_known_bad=0.55, p_noise_good=0.03, p_known_good=0.65, p_noise_bad=0.01):
        if is_bad:
            if self.rng.random() < p_known_bad: self.bad.add(dom)
            elif self.rng.random() < p_noise_good: self.good.add(dom)
        else:
            if self.rng.random() < p_known_good: self.good.add(dom)
            elif self.rng.random() < p_noise_bad: self.bad.add(dom)

    def _auth(self, spf, dkim, dmarc):
        return {"spf": self._pick(spf), "dkim": self._pick(dkim), "dmarc": self._pick(dmarc)}

    def _compose(self, from_name, from_addr, subject, body, auth, reply_to=None, attachments=()):
        m = EmailMessage()
        m["From"] = f'"{from_name}" <{from_addr}>' if from_name else from_addr
        m["To"] = "usuario@utb.edu.co"
        m["Subject"] = subject
        m["Date"] = formatdate(1_760_000_000 + self.rng.randint(0, 5_000_000))
        m["Message-ID"] = make_msgid(domain=from_addr.split("@")[1])
        if reply_to: m["Reply-To"] = reply_to
        if auth: m["Authentication-Results"] = "mx.utb.edu.co; " + "; ".join(f"{k}={v}" for k, v in auth.items())
        m.set_content(body)
        for fn in attachments:
            m.add_attachment(self.rng.randbytes(self.rng.randint(300, 3000)), maintype="application", subtype="octet-stream", filename=fn)
        return m.as_string()

    def _url(self, dom, https=True):
        path = "/".join("".join(self.rng.choices("abcdefghij0123456789", k=self.rng.randint(3, 9))) for _ in range(self.rng.randint(1, 3)))
        return f"{'https' if https else 'http'}://{dom}/{path}"

    def _phish_url(self, brand_dom):
        k = self._pick({"ip": .12, "susp": .30, "look": .25, "short": .13, "free": .05, "plain": .15})
        if k == "ip": return f"http://{'.'.join(str(self.rng.randint(1, 254)) for _ in range(4))}/login/{self.rng.randint(100, 999)}"
        if k == "susp": d = self._rand_domain(susp=True)
        elif k == "look": d = self._lookalike(brand_dom)
        elif k == "short": return self._url(self.rng.choice(SHORTENERS))
        elif k == "free": d = f"{self._rand_domain().split('.')[0]}.{self.rng.choice(FREE_HOSTING)}"
        else: d = self._rand_domain()
        self._register(d, True)
        return self._url(d, https=self.rng.random() < 0.6)

    def _text(self, parts):
        return " ".join(parts)

    # ---------- generadores por tipo ----------
    def sample(self, kind):
        self.n += 1
        raw = getattr(self, f"_gen_{kind}")()
        return Sample(raw, 1 if kind.startswith("phish") else 0, kind)

    def batch(self, kind, n):
        return [self.sample(kind) for _ in range(n)]

    def _gen_legit_newsletter(self):
        r = self.rng
        dom = self._legit_domain() if r.random() < 0.85 else self._rand_domain(); self._register(dom, False)
        urls = []
        for _ in range(r.randint(1, 5)):
            k = self._pick({"own": .65, "esp": .25, "short": .07, "free": .03})
            if k == "own": urls.append(self._url(f"www.{dom}", https=r.random() > 0.05))
            elif k == "esp": urls.append(self._url(r.choice(["click.mailerservice.net", "links.sendmailer.com", "track.newsmailer.io"])))
            elif k == "short": urls.append(self._url(r.choice(SHORTENERS)))
            else: urls.append(self._url(f"{self._rand_domain().split('.')[0]}.{r.choice(FREE_HOSTING)}"))
        body = self._text(r.sample(LEGIT_NEWS, r.randint(2, 4)))
        if r.random() < 0.15: body += " " + r.choice(["Ultima oportunidad: la oferta expira hoy.", "Accion requerida: renueva tu suscripcion."])
        body += "\n\n" + "\n".join(urls)
        auth = self._auth({"pass": .88, "none": .08, "softfail": .04}, {"pass": .85, "none": .12, "fail": .03}, {"pass": .70, "none": .28, "fail": .02})
        rt = f"contacto@{self._legit_domain()}" if r.random() < 0.2 else None
        return self._compose(dom.split(".")[0].title(), f"noticias@{dom}", "Novedades de la semana", body, auth, reply_to=rt)

    def _gen_legit_internal(self):
        r = self.rng
        name = r.choice(NAMES)
        addr = f"{name.split()[0].lower()}.{name.split()[1].lower()}@{INTERNAL_DOMAIN}"
        urls = [self._url(r.choice(["campus.utb.edu.co", "drive.google.com", "www.utb.edu.co"])) for _ in range(r.randint(0, 2))]
        body = self._text(r.sample(LEGIT_INTERNAL, r.randint(1, 3))) + ("\n\n" + "\n".join(urls) if urls else "")
        att = [r.choice(["acta.pdf", "presupuesto.xlsx", "informe.docx", "slides.pptx", "datos.zip", "formulario.html"])] if r.random() < 0.3 else []
        auth = self._auth({"pass": .95, "none": .05}, {"pass": .93, "none": .07}, {"pass": .9, "none": .1})
        return self._compose(name, addr, r.choice(["Acta de reunion", "Re: cronograma", "Documentos del proyecto"]), body, auth, attachments=att)

    def _gen_legit_transactional(self):
        r = self.rng
        brand, bdom = r.choice(list(BRANDS.items()))
        sdom = bdom if r.random() < 0.85 else f"mail.{bdom}"
        self.good.add(sdom)
        body = r.choice(LEGIT_TRANS).format(code=r.randint(100000, 999999))
        if r.random() < 0.2: body += " Inicie sesion en su cuenta para ver los detalles."
        body += "\n\n" + "\n".join(self._url(f"www.{bdom}") for _ in range(r.randint(1, 2)))
        auth = self._auth({"pass": .9, "none": .08, "softfail": .02}, {"pass": .9, "none": .08, "fail": .02}, {"pass": .85, "none": .15})
        return self._compose(brand, f"no-reply@{sdom}", f"{brand}: actualizacion de tu cuenta", body, auth)

    def _gen_legit_urgent(self):
        r = self.rng
        dom = self._legit_domain() if r.random() < 0.6 else self._rand_domain(); self._register(dom, False)
        urls = []
        for _ in range(r.randint(1, 2)):
            k = self._pick({"own": .5, "short": .3, "esp": .2})
            urls.append(self._url(f"www.{dom}") if k == "own" else self._url(r.choice(SHORTENERS)) if k == "short" else self._url("click.mailerservice.net"))
        body = f"Recordatorio: su matricula vence hoy. {r.choice(URGENCY)}. Realice el pago en el portal. " + "\n\n" + "\n".join(urls)
        auth = self._auth({"pass": .6, "fail": .15, "softfail": .1, "none": .15}, {"pass": .5, "none": .4, "fail": .1}, {"pass": .4, "none": .5, "fail": .1})
        return self._compose("Cobranza", f"cobranza@{dom}", "Recordatorio importante", body, auth)

    def _gen_legit_personal(self):
        r = self.rng
        name = r.choice(NAMES)
        prov = r.choice(FREE_PROVIDERS)
        body = r.choice(["Hola, te escribo para confirmar la reunion de manana.", "Necesito que me envies el documento cuando puedas.",
                         "Gracias por tu ayuda con el trabajo, te debo una.", "Te comparto el enlace del proyecto para que lo revises.",
                         "Podrias confirmar el pago de la matricula? Gracias."])
        if r.random() < 0.25: body += " " + self._url(r.choice(["drive.google.com", "www.youtube.com", "docs.google.com"]))
        if r.random() < 0.10: body += " Es urgente, por favor respondeme hoy."
        auth = self._auth({"pass": .85, "none": .1, "softfail": .05}, {"pass": .85, "none": .12, "fail": .03}, {"pass": .6, "none": .38, "fail": .02})
        self.good.add(prov)
        att = [r.choice(["foto.jpg", "tarea.pdf", "notas.docx"])] if r.random() < 0.2 else []
        return self._compose(name, f"{name.split()[0].lower()}{r.randint(1, 99)}@{prov}", "Hola", body, auth, attachments=att)

    def _phish_auth_weak(self):
        return self._auth({"fail": .4, "softfail": .2, "none": .25, "pass": .15}, {"none": .6, "fail": .25, "pass": .15}, {"none": .55, "fail": .3, "pass": .15})

    def _phish_body(self, urgency_p=.9, cred_p=.85, money_p=.25):
        r = self.rng; parts = []
        if r.random() < urgency_p: parts += r.sample(URGENCY, r.randint(1, 2))
        if r.random() < cred_p: parts += r.sample(CRED, r.randint(1, 2))
        if r.random() < money_p: parts.append(r.choice(MONEY))
        if not parts: parts = [r.choice(CRED)]
        r.shuffle(parts)
        return ". ".join(parts) + "."

    def _gen_phish_credential(self):
        r = self.rng
        brand, bdom = r.choice(list(BRANDS.items()))
        dom = self._rand_domain(susp=r.random() < 0.4) if r.random() < 0.8 else self._legit_domain(); self._register(dom, True)
        name = brand if r.random() < 0.5 else r.choice(["Soporte", "Seguridad", "Administrador"])
        body = self._phish_body(urgency_p=.8) + "\n\n" + "\n".join(self._phish_url(bdom) for _ in range(r.randint(1, 2)))
        rt = f"cuenta{r.randint(1, 99)}@{r.choice(FREE_PROVIDERS)}" if r.random() < 0.4 else None
        return self._compose(name, f"{r.choice(['info', 'alerta', 'soporte'])}@{dom}", f"Aviso importante de {name}", body, self._phish_auth_weak(), reply_to=rt)

    def _gen_phish_brand_spoof(self):
        r = self.rng
        brand, bdom = r.choice(list(BRANDS.items()))
        k = self._pick({"free": .4, "rand": .4, "look": .2})
        dom = r.choice(FREE_PROVIDERS) if k == "free" else self._rand_domain() if k == "rand" else self._lookalike(bdom)
        if k != "free": self._register(dom, True)
        body = self._phish_body() + "\n\n" + self._phish_url(bdom)
        return self._compose(brand, f"{brand.lower()}.service@{dom}", f"{brand} - verificacion de seguridad", body, self._phish_auth_weak())

    def _gen_phish_lookalike(self):
        r = self.rng
        brand, bdom = r.choice(list(BRANDS.items()))
        dom = self._lookalike(bdom); self._register(dom, True)
        urls = [self._url(dom if r.random() < 0.8 else self._lookalike(bdom)) for _ in range(r.randint(1, 2))]
        body = self._phish_body(urgency_p=.6) + "\n\n" + "\n".join(urls)
        auth = self._auth({"pass": .35, "none": .3, "fail": .25, "softfail": .1}, {"pass": .25, "none": .6, "fail": .15}, {"pass": .1, "none": .8, "fail": .1})
        return self._compose(brand, f"no-reply@{dom}", f"{brand}: acceso a su cuenta", body, auth)

    def _gen_phish_attachment(self):
        r = self.rng
        dom = r.choice(FREE_PROVIDERS) if r.random() < 0.4 else (self._rand_domain() if r.random() < 0.8 else self._legit_domain())
        if dom not in FREE_PROVIDERS: self._register(dom, True)
        body = f"Adjunto factura {r.randint(1000, 9999)} pendiente de pago. Abra el archivo para ver los detalles."
        if r.random() < 0.4: body += " " + r.choice(URGENCY) + "."
        return self._compose(r.choice(NAMES), f"{r.choice(['facturacion', 'contabilidad', 'ventas'])}@{dom}", "Factura pendiente", body,
                             self._phish_auth_weak(), attachments=[r.choice(RISKY_FILES)])

    def _gen_phish_bec(self):
        r = self.rng
        dom = r.choice(FREE_PROVIDERS) if r.random() < 0.6 else self._rand_domain(); 
        if dom not in FREE_PROVIDERS: self._register(dom, True)
        body = "Estas disponible? Necesito que gestiones una transferencia hoy. Te envio los datos por este medio. Es confidencial."
        if r.random() < 0.4: body += " " + r.choice(URGENCY) + "."
        rt = f"jefe{r.randint(1, 99)}@{r.choice(FREE_PROVIDERS)}" if r.random() < 0.5 else None
        auth = self._auth({"pass": .4, "none": .3, "fail": .3}, {"none": .6, "pass": .3, "fail": .1}, {"none": .7, "pass": .2, "fail": .1})
        return self._compose(f"{r.choice(NAMES)} (Rectoria)", f"{r.choice(['direccion', 'gerencia'])}@{dom}", "Favor responder", body, auth, reply_to=rt)

    def _gen_phish_compromised(self):
        r = self.rng
        dom = self._legit_domain(); self._register(dom, False)
        k = self._pick({"short": .35, "rand": .35, "look": .3})
        if k == "short": url = self._url(r.choice(SHORTENERS))
        elif k == "rand": d = self._rand_domain(); self._register(d, True); url = self._url(d)
        else: d = self._lookalike(r.choice(list(BRANDS.values()))); self._register(d, True); url = self._url(d)
        body = "Revisa este documento compartido. " + (r.choice(CRED) + ". " if r.random() < .5 else "") + (r.choice(URGENCY) + ". " if r.random() < .3 else "") + "\n\n" + url
        auth = self._auth({"pass": .9, "none": .1}, {"pass": .85, "none": .15}, {"pass": .8, "none": .2})
        name = r.choice(NAMES)
        return self._compose(name, f"{name.split()[0].lower()}@{dom}", "Documento compartido contigo", body, auth)

    def _gen_phish_new_campaign(self):
        """Campana NUEVA (no vista en entrenamiento inicial): cuenta comprometida, autenticacion valida,
        sin palabras de urgencia, enlace a hosting gratuito."""
        r = self.rng
        dom = self._legit_domain(); self._register(dom, False)
        d = f"{self._rand_domain().split('.')[0]}.{r.choice(FREE_HOSTING)}"; self._register(d, True, p_known_bad=0.2)
        body = f"Te compartieron un documento. Ver documento: {self._url(d)}"
        auth = self._auth({"pass": .92, "none": .08}, {"pass": .9, "none": .1}, {"pass": .85, "none": .15})
        name = r.choice(NAMES)
        return self._compose(name, f"{name.split()[0].lower()}@{dom}", "Documento compartido", body, auth)
