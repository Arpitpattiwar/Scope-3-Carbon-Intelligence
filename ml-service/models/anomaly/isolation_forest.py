"""Isolation Forest baseline for anomaly detection."""

import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import ParameterGrid
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger

logger = get_logger(__name__)


def train(X_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray,
          config: dict) -> dict:
    """
    Train Isolation Forest with contamination rate matching dataset anomaly rate.
    Performs a small grid search over n_estimators and max_samples.
    
    Note: IF is unsupervised — it does NOT use y_train.
    Validation labels are used only to pick the best hyperparameter set.
    """
    from sklearn.metrics import average_precision_score

    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_samples':  [128, 256, 'auto'],
        'contamination': [config.get('contamination', 0.07)],
    }

    best_ap, best_model, best_params = -1, None, None

    for params in ParameterGrid(param_grid):
        model = IsolationForest(
            **params,
            random_state=config.get('random_state', 42),
            n_jobs=-1,
        )
        model.fit(X_train)
        # decision_function returns higher = more normal; negate for anomaly score
        scores = -model.decision_function(X_val)
        ap = average_precision_score(y_val, scores)
        if ap > best_ap:
            best_ap, best_model, best_params = ap, model, params

    logger.info(f"Best IF params: {best_params}  |  Val AP: {best_ap:.4f}")
    return {'model': best_model, 'best_params': best_params, 'val_ap': best_ap}


def get_scores(model, X: np.ndarray) -> np.ndarray:
    """Return anomaly scores (higher = more anomalous)."""
    return -model.decision_function(X)


def save(model, path: str = 'saved_models/anomaly/isolation_forest.pkl'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/anomaly/isolation_forest.pkl'):
    return joblib.load(path)
