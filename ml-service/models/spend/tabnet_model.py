"""
TabNet for spend-based emission estimation.

TabNet (Arik & Pfister, Google, 2021) uses sequential attention to select
which features to use at each decision step. Gives built-in feature
importance through attention masks — directly interpretable.
"""

import numpy as np
import torch
from pathlib import Path
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger

logger = get_logger(__name__)


def train(X_train: np.ndarray, y_train: np.ndarray,
          X_val:   np.ndarray, y_val:   np.ndarray,
          config: dict) -> dict:
    try:
        from pytorch_tabnet.tab_model import TabNetRegressor
    except ImportError:
        logger.error("pytorch-tabnet not installed. Run: pip install pytorch-tabnet")
        raise

    model = TabNetRegressor(
        n_d              = config.get('n_d',       32),
        n_a              = config.get('n_a',       32),
        n_steps          = config.get('n_steps',   5),
        gamma            = config.get('gamma',     1.3),
        momentum         = config.get('momentum',  0.02),
        optimizer_fn     = torch.optim.Adam,
        optimizer_params = {'lr': config.get('lr', 0.02)},
        mask_type        = 'sparsemax',
        verbose          = 5,
        seed             = 42,
        device_name      = 'auto',
    )

    model.fit(
        X_train        = X_train.astype(np.float32),
        y_train        = y_train.astype(np.float32).reshape(-1, 1),
        eval_set       = [(X_val.astype(np.float32),
                           y_val.astype(np.float32).reshape(-1, 1))],
        eval_name      = ['val'],
        eval_metric    = ['mae'],
        max_epochs     = config.get('epochs',   200),
        patience       = config.get('patience', 20),
        batch_size     = config.get('batch_size', 1024),
        virtual_batch_size = config.get('virtual_batch_size', 128),
        num_workers    = 0,   # disable multiprocessing — avoids hangs
        drop_last      = False,
    )

    val_pred = model.predict(X_val.astype(np.float32)).flatten()
    from sklearn.metrics import mean_absolute_error, r2_score
    val_mae = mean_absolute_error(y_val, val_pred)
    val_r2  = r2_score(y_val, val_pred)
    logger.info(f"TabNet — val MAE(log): {val_mae:.4f}  R²: {val_r2:.4f}")

    # Extract training history
    history = {}
    if hasattr(model, 'history') and model.history:
        # pytorch_tabnet history is a special object, extract keys safely
        try:
            history = {key: model.history[key] for key in model.history.keys()}
        except Exception:
            history = {}

    return {
        'model':   model,
        'val_mae': val_mae,
        'val_r2':  val_r2,
        'history': history,
    }


def get_predictions(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X.astype(np.float32)).flatten()


def get_feature_importance(model, feature_names: list = None) -> dict:
    importance = model.feature_importances_
    result = {'importance': importance.tolist()}
    if feature_names:
        result['importance_dict'] = dict(zip(feature_names, importance.tolist()))
        result['ranked'] = sorted(
            zip(feature_names, importance.tolist()),
            key=lambda x: x[1], reverse=True
        )
    return result


def save(model, path: str = 'saved_models/spend/tabnet'):
    Path(path).mkdir(parents=True, exist_ok=True)
    model.save_model(str(Path(path) / 'tabnet_model'))
    logger.info(f"Saved → {path}/tabnet_model.zip")


def load(path: str = 'saved_models/spend/tabnet'):
    try:
        from pytorch_tabnet.tab_model import TabNetRegressor
    except ImportError:
        raise ImportError("pytorch-tabnet not installed")
    model = TabNetRegressor()
    model.load_model(str(Path(path) / 'tabnet_model.zip'))
    return model
