"""
XGBoost baseline for spend-based emission estimation.
Trained on flat feature array (categorical codes + numerical).
SHAP values computed for explainability.
"""

import numpy as np
import joblib
from pathlib import Path
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger

logger = get_logger(__name__)


def train(X_train: np.ndarray, y_train: np.ndarray,
          X_val:   np.ndarray, y_val:   np.ndarray,
          config: dict) -> dict:
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    model = XGBRegressor(
        n_estimators      = config.get('n_estimators',      500),
        max_depth         = config.get('max_depth',         6),
        learning_rate     = config.get('learning_rate',     0.05),
        subsample         = config.get('subsample',         0.8),
        colsample_bytree  = config.get('colsample_bytree',  0.8),
        min_child_weight  = config.get('min_child_weight',  3),
        reg_alpha         = config.get('reg_alpha',         0.1),
        reg_lambda        = config.get('reg_lambda',        1.0),
        random_state      = config.get('random_state',      42),
        n_jobs            = -1,
        eval_metric       = 'mae',
        early_stopping_rounds = 30,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    val_pred = model.predict(X_val)
    val_mae  = mean_absolute_error(y_val, val_pred)
    val_r2   = r2_score(y_val, val_pred)
    logger.info(f"XGBoost — val MAE (log): {val_mae:.4f}  R²: {val_r2:.4f}")

    return {
        'model':        model,
        'best_iter':    model.best_iteration,
        'val_mae':      val_mae,
        'val_r2':       val_r2,
    }


def get_predictions(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X)


def compute_shap(model, X_sample: np.ndarray,
                 feature_names: list = None) -> dict:
    """
    Compute SHAP values for a sample of test records.
    Returns dict with values array and feature importance.
    """
    try:
        import shap
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        importance  = np.abs(shap_values).mean(axis=0)

        result = {'shap_values': shap_values, 'importance': importance}
        if feature_names:
            result['feature_names'] = feature_names
            result['importance_dict'] = dict(zip(feature_names, importance.tolist()))
        return result
    except ImportError:
        logger.warning("shap not installed — skipping SHAP computation")
        return {}


def save(model, path: str = 'saved_models/spend/xgboost.pkl'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/spend/xgboost.pkl'):
    return joblib.load(path)
