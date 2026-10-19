"""Construccion del conjunto de entrenamiento (en el entorno simulado) y calibracion de umbrales."""
import os, sys, random
import numpy as np, joblib
from .simulator import MailEnvironment, LEGIT_KINDS, PHISH_KINDS
from .features import parse_email, extract
from .tools import ReputationTool
from .agent import make_model

LEGIT_W = {"legit_newsletter": .30, "legit_internal": .20, "legit_transactional": .20, "legit_urgent": .10, "legit_personal": .20}
PHISH_W = {"phish_credential": .30, "phish_brand_spoof": .20, "phish_lookalike": .20,
           "phish_attachment": .12, "phish_bec": .08, "phish_compromised": .10}


def vectorize(sample, tool):
    msg, err = parse_email(sample.raw)
    assert err is None, err
    return extract(msg, tool)[0]


def build_dataset(seed, n_legit, n_phish):
    env = MailEnvironment(seed)
    rng = random.Random(seed + 7)
    samples = []
    for kinds, w, n in ((LEGIT_W, LEGIT_W, n_legit), (PHISH_W, PHISH_W, n_phish)):
        for k, p in w.items():
            samples += env.batch(k, int(n * p))
    rng.shuffle(samples)
    X, y = [], []
    for i, s in enumerate(samples):
        p_fail = rng.choices([0.0, 0.05, 1.0], weights=[.75, .05, .20])[0]  # entorno adverso incluido
        tool = ReputationTool(env.reputation_service(p_fail, seed=seed + i))
        X.append(vectorize(s, tool)); y.append(s.label)
    return np.array(X), np.array(y)


def train_bundle(seed=2026, n=3000, target_fpr=0.015, verbose=True):
    X, y = build_dataset(seed, n, n)
    Xv, yv = build_dataset(seed + 1, 1500, 1500)       # validacion: semillas distintas a las de prueba
    model = make_model(seed).fit(X, y)
    pv = model.predict_proba(Xv)[:, 1]
    legit_scores = np.sort(pv[yv == 0])
    # t_warn: menor umbral cuyo FPR (cualquier alerta sobre legitimo) en validacion <= target_fpr
    t_warn = float(legit_scores[int(np.ceil((1 - target_fpr) * len(legit_scores))) - 1]) + 1e-6
    t_warn = max(t_warn, 0.30)
    t_quar = max(0.75, t_warn + 0.2)
    if verbose:
        print(f"validacion: t_warn={t_warn:.3f} t_quar={t_quar:.3f} "
              f"recall={np.mean(pv[yv == 1] >= t_warn):.3f} fpr={np.mean(pv[yv == 0] >= t_warn):.3f}")
    return {"model": model, "t_warn": t_warn, "t_quar": t_quar, "version": 1, "X": X, "y": y}


def load_or_train(path="models/phishguard_model.joblib"):
    if os.path.exists(path):
        try:
            return joblib.load(path)
        except Exception:
            pass
    b = train_bundle()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(b, path)
    return b


if __name__ == "__main__":
    b = train_bundle()
    os.makedirs("models", exist_ok=True)
    joblib.dump(b, "models/phishguard_model.joblib")
    print("modelo guardado en models/phishguard_model.joblib")
