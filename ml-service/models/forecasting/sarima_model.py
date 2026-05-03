"""
SARIMA baseline for emission forecasting.
Seasonal ARIMA: (p,d,q)(P,D,Q)[s=12]

Trains a separate model per sector series.
Uses AIC to select best (p,d,q) order automatically.
"""

import numpy as np
import warnings
import joblib
from pathlib import Path
from itertools import product
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger

warnings.filterwarnings('ignore')
logger = get_logger(__name__)


def _select_order(series: np.ndarray, max_p: int = 2, max_q: int = 1) -> tuple:
    """
    Select SARIMA (p,d,q) via AIC grid search.
    Reduced grid (max_p=2, max_q=1) keeps wall time per sector under 60s.
    D=1 and S=12 fixed (monthly seasonality, one seasonal difference).
    Grid: 3 * 2 * 2 = 12 candidate models per sector.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    best_aic, best_order = np.inf, (1, 1, 1)

    for p, d, q in product(range(max_p + 1), [0, 1], range(max_q + 1)):
        if p == 0 and q == 0:
            continue
        try:
            res = SARIMAX(
                series,
                order=(p, d, q),
                seasonal_order=(1, 1, 0, 12),
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False, maxiter=100)
            if res.aic < best_aic:
                best_aic   = res.aic
                best_order = (p, d, q)
        except Exception:
            continue

    logger.info(f"  Best order: {best_order}  AIC: {best_aic:.2f}")
    return best_order


def train(sector_data: dict, config: dict) -> dict:
    """
    Train one SARIMA model per sector.

    sector_data: dict from forecast_prep.load_splits() — per-sector raw series
    Returns dict: sector → fitted model
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    default_order    = tuple(config.get('order',          [2, 1, 1]))
    default_seasonal = tuple(config.get('seasonal_order', [1, 1, 0, 12]))

    models = {}
    for sector, data in sector_data.items():
        logger.info(f"Fitting SARIMA for sector: {sector}")
        train_series = data['raw'][:data['val_start']]   # train only

        # Auto-select order via AIC
        order = _select_order(train_series)

        model = SARIMAX(
            train_series,
            order=order,
            seasonal_order=default_seasonal,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=500)

        models[sector] = {
            'result':   model,
            'order':    order,
            'seasonal': default_seasonal,
            'n_train':  len(train_series),
        }
        logger.info(f"  {sector}: AIC={model.aic:.2f}")

    return models


def get_forecast(models: dict, sector_data: dict, horizon: int = 3,
                 split: str = 'test') -> dict:
    """
    Generate rolling forecasts for val or test split.

    For each split window, the model is refitted on all data up to that point
    (expanding window), which is the correct SARIMA evaluation protocol.
    """
    results = {}
    for sector, m in models.items():
        data = sector_data[sector]
        raw  = data['raw']

        if split == 'val':
            start = data['val_start']
            end   = data['test_start']
        else:
            start = data['test_start']
            end   = len(raw)

        preds_all, lowers_all, uppers_all, actuals_all = [], [], [], []

        for t in range(start, end - horizon + 1, horizon):
            # Refit on expanding window up to t
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                res = SARIMAX(
                    raw[:t],
                    order=m['order'],
                    seasonal_order=m['seasonal'],
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False, maxiter=300)

            fc = res.get_forecast(steps=horizon)
            mean_fc = fc.predicted_mean
            ci      = fc.conf_int(alpha=0.10)   # 90% prediction interval
            # conf_int() returns DataFrame or ndarray depending on statsmodels version
            import pandas as _pd
            if isinstance(ci, _pd.DataFrame):
                ci_lo = ci.iloc[:, 0].values
                ci_hi = ci.iloc[:, 1].values
            else:
                ci_lo = ci[:, 0]
                ci_hi = ci[:, 1]

            actual = raw[t:t + horizon]
            n_obs  = min(horizon, len(actual))

            preds_all.extend(mean_fc[:n_obs].tolist())
            lowers_all.extend(ci_lo[:n_obs].tolist())
            uppers_all.extend(ci_hi[:n_obs].tolist())
            actuals_all.extend(actual[:n_obs].tolist())

        results[sector] = {
            'preds':   np.array(preds_all),
            'lowers':  np.array(lowers_all),
            'uppers':  np.array(uppers_all),
            'actuals': np.array(actuals_all),
        }
    return results


def save(models: dict, path: str = 'saved_models/forecasting/sarima.pkl'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # Save only serialisable parts (result objects are statsmodels SARIMAXResults)
    to_save = {}
    for sector, m in models.items():
        to_save[sector] = {
            'result':   m['result'],
            'order':    m['order'],
            'seasonal': m['seasonal'],
        }
    joblib.dump(to_save, path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/forecasting/sarima.pkl') -> dict:
    return joblib.load(path)
