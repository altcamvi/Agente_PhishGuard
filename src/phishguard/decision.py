"""Módulo de DECISIÓN: modelo de aprendizaje (regresión logística) + política de riesgo."""
import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MaxAbsScaler


class RiskModel:
    """P(phishing | características numéricas + TF-IDF del texto)."""

    def __init__(self):
        self.dv = DictVectorizer()
        self.tf = TfidfVectorizer(max_features=150, ngram_range=(1, 2), min_df=3, sublinear_tf=True)
        self.sc = MaxAbsScaler()
        self.clf = LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced")
        self.fitted = False

    def _matrix(self, feats, texts, fit=False):
        if fit:
            A = self.sc.fit_transform(self.dv.fit_transform(feats))
            T = self.tf.fit_transform(texts)
        else:
            A = self.sc.transform(self.dv.transform(feats))
            T = self.tf.transform(texts)
        return hstack([csr_matrix(A), T]).tocsr()

    def fit(self, feats, texts, y):
        X = self._matrix(feats, texts, fit=True)
        self.clf.fit(X, np.asarray(y))
        self.fitted = True
        return self

    def predict_risk(self, feats: dict, text: str) -> float:
        X = self._matrix([feats], [text])
        return float(self.clf.predict_proba(X)[0, 1])

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)
