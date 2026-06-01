"""interceptor.py — sliding-window risk engine with XGBoost and TreeSHAP."""

from __future__ import annotations

import os
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import dump, load
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import shap

MODEL_PATH = "compliance_model.joblib"
SCALER_PATH = "compliance_scaler.joblib"

FEATURE_NAMES = [
    "avg_logprob",
    "min_logprob",
    "max_logprob",
    "logprob_std",
    "token_count",
    "punctuation_ratio",
    "uppercase_ratio",
    "digits_ratio",
    "avg_token_length",
]


@dataclass
class TokenFeature:
    token: str
    logprob: Optional[float]


class SlidingWindowFeatureExtractor:
    def __init__(self, window_size: int = 4) -> None:
        self.window_size = window_size
        self.window: List[TokenFeature] = []

    def append(self, token: str, logprob: Optional[float]) -> Dict[str, float]:
        self.window.append(TokenFeature(token=token, logprob=logprob))
        if len(self.window) > self.window_size:
            self.window.pop(0)
        return self.features()

    def features(self) -> Dict[str, float]:
        tokens = [t.token for t in self.window]
        logprobs = [t.logprob for t in self.window if t.logprob is not None]

        avg_logprob = float(np.mean(logprobs)) if logprobs else -3.5
        min_logprob = float(np.min(logprobs)) if logprobs else -5.0
        max_logprob = float(np.max(logprobs)) if logprobs else -1.5
        logprob_std = float(np.std(logprobs)) if logprobs else 0.5

        token_count = len(tokens)
        punctuation_ratio = self._compute_punctuation_ratio(tokens)
        uppercase_ratio = self._compute_uppercase_ratio(tokens)
        digits_ratio = self._compute_digits_ratio(tokens)
        avg_token_length = float(np.mean([len(t) for t in tokens])) if tokens else 0.0

        return {
            "avg_logprob": avg_logprob,
            "min_logprob": min_logprob,
            "max_logprob": max_logprob,
            "logprob_std": logprob_std,
            "token_count": float(token_count),
            "punctuation_ratio": punctuation_ratio,
            "uppercase_ratio": uppercase_ratio,
            "digits_ratio": digits_ratio,
            "avg_token_length": avg_token_length,
        }

    def _compute_punctuation_ratio(self, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        punct = sum(1 for t in tokens if any(ch in ",.?!;:" for ch in t))
        return punct / len(tokens)

    def _compute_uppercase_ratio(self, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        upper = sum(1 for t in tokens if any(ch.isupper() for ch in t))
        return upper / len(tokens)

    def _compute_digits_ratio(self, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        digits = sum(1 for t in tokens if any(ch.isdigit() for ch in t))
        return digits / len(tokens)


class ComplianceRiskModel:
    def __init__(self, model_path: str = MODEL_PATH, scaler_path: str = SCALER_PATH) -> None:
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model: Optional[XGBClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self._load_or_train()

    def _load_or_train(self) -> None:
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = load(self.model_path)
            self.scaler = load(self.scaler_path)
            return

        self._train_model()

    def _train_model(self) -> None:
        df = self._generate_synthetic_data(2500)
        X = df[FEATURE_NAMES].values
        y = df["label"].values

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        model = XGBClassifier(
            use_label_encoder=False,
            eval_metric="logloss",
            n_estimators=100,
            max_depth=4,
            learning_rate=0.2,
        )
        model.fit(X_train, y_train)

        self.model = model
        dump(model, self.model_path)
        dump(self.scaler, self.scaler_path)

    def _generate_synthetic_data(self, n_samples: int) -> pd.DataFrame:
        rows = []
        for _ in range(n_samples):
            token_count = random.randint(1, 6)
            is_hallucinated = random.random() < 0.35
            if is_hallucinated:
                logprobs = np.random.normal(-3.5, 0.8, size=token_count)
                punct_ratio = random.uniform(0.2, 0.6)
                uppercase_ratio = random.uniform(0.1, 0.5)
                digits_ratio = random.uniform(0.0, 0.3)
            else:
                logprobs = np.random.normal(-1.2, 0.5, size=token_count)
                punct_ratio = random.uniform(0.0, 0.3)
                uppercase_ratio = random.uniform(0.0, 0.2)
                digits_ratio = random.uniform(0.0, 0.15)

            avg_token_length = random.uniform(3.5, 6.5)
            rows.append({
                "avg_logprob": float(np.mean(logprobs)),
                "min_logprob": float(np.min(logprobs)),
                "max_logprob": float(np.max(logprobs)),
                "logprob_std": float(np.std(logprobs)),
                "token_count": float(token_count),
                "punctuation_ratio": punct_ratio,
                "uppercase_ratio": uppercase_ratio,
                "digits_ratio": digits_ratio,
                "avg_token_length": avg_token_length,
                "label": int(is_hallucinated),
            })
        return pd.DataFrame(rows)

    def predict_risk(self, features: Dict[str, float]) -> float:
        if self.model is None or self.scaler is None:
            return 0.0
        x = np.array([[features[name] for name in FEATURE_NAMES]], dtype=float)
        x_scaled = self.scaler.transform(x)
        proba = self.model.predict_proba(x_scaled)[0][1]
        return float(proba)


class TreeSHAPExplainer:
    def __init__(self, model: XGBClassifier) -> None:
        self.explainer = shap.TreeExplainer(model)

    def explain(self, features: Dict[str, float]) -> Dict[str, float]:
        x = np.array([[features[name] for name in FEATURE_NAMES]], dtype=float)
        shap_values = self.explainer.shap_values(x)
        if isinstance(shap_values, list) and len(shap_values) == 2:
            shap_values = shap_values[1]
        shap_dict = {name: float(shap_values[0, idx]) for idx, name in enumerate(FEATURE_NAMES)}
        return shap_dict


class InterceptionEngine:
    def __init__(self, threshold: float = 0.8, window_size: int = 4) -> None:
        self.window = SlidingWindowFeatureExtractor(window_size=window_size)
        self.risk_model = ComplianceRiskModel()
        self.explainer = TreeSHAPExplainer(self.risk_model.model)
        self.threshold = threshold
        self.last_features: Optional[Dict[str, float]] = None
        self.last_risk: Optional[float] = None
        self.last_shap: Optional[Dict[str, float]] = None

    def append_token(self, token: str, logprob: Optional[float]) -> Dict[str, float]:
        features = self.window.append(token, logprob)
        self.last_features = features
        self.last_risk = self.risk_model.predict_risk(features)
        self.last_shap = self.explainer.explain(features)
        return features

    def should_intercept(self) -> bool:
        return self.last_risk is not None and self.last_risk >= self.threshold

    def get_risk(self) -> float:
        return float(self.last_risk) if self.last_risk is not None else 0.0

    def get_shap(self) -> Dict[str, float]:
        return self.last_shap if self.last_shap is not None else {}

    def reset(self) -> None:
        self.window = SlidingWindowFeatureExtractor(window_size=self.window.window_size)
        self.last_features = None
        self.last_risk = None
        self.last_shap = None
