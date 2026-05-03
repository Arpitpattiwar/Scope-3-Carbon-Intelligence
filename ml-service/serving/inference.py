"""
Inference service — loads the best saved model per task and exposes
predict() functions that the platform's FastAPI backend can call.

Usage from FastAPI route:
    from ml.serving.inference import (
        predict_anomaly, predict_forecast, predict_spend
    )

All functions return a dict with prediction + confidence/score + explanation.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger

logger = get_logger('inference')

# ── Model registry — loaded lazily on first call ──────────────────────────────

_anomaly_model    = None
_anomaly_prep     = None
_forecast_models  = None
_forecast_scalers = None
_spend_model      = None
_spend_prep       = None

BASE = Path(__file__).parent.parent


def _get_anomaly_threshold(winner: str) -> float:
    meta_path = BASE / 'saved_models' / 'anomaly' / 'best_model.json'
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        if 'threshold' in meta:
            return float(meta['threshold'])

    comparison_path = BASE / 'results' / 'anomaly_comparison.json'
    if comparison_path.exists():
        with open(comparison_path) as f:
            comparison = json.load(f)
        return float(comparison['models'][winner]['threshold'])

    return 0.5


def _normalise_anomaly_score(score: float, threshold: float) -> float:
    scale = max(abs(threshold), 1e-6)
    margin = np.clip((score - threshold) / scale, -20, 20)
    return float(1.0 / (1.0 + np.exp(-margin)))


def _load_anomaly():
    global _anomaly_model, _anomaly_prep
    if _anomaly_model is not None:
        return

    meta_path = BASE / 'saved_models' / 'anomaly' / 'best_model.json'
    if not meta_path.exists():
        raise FileNotFoundError(
            "No trained anomaly model found. Run: python train/train_anomaly.py"
        )
    with open(meta_path) as f:
        meta = json.load(f)

    winner = meta['winner']
    logger.info(f"Loading anomaly model: {winner}")

    if winner == 'isolation_forest':
        from models.anomaly import isolation_forest as M
        _anomaly_model = M.load(str(BASE / 'saved_models/anomaly/isolation_forest.pkl'))
        _anomaly_type  = 'if'
    elif winner == 'autoencoder':
        from models.anomaly import autoencoder as M
        _anomaly_model = M.load(str(BASE / 'saved_models/anomaly/autoencoder.pt'))
        _anomaly_type  = 'ae'
    elif winner == 'vae':
        from models.anomaly import vae as M
        _anomaly_model = M.load(str(BASE / 'saved_models/anomaly/vae.pt'))
        _anomaly_type  = 'vae'
    else:
        raise ValueError(f"Unknown anomaly winner: {winner}")

    # Store type on model object for dispatch
    _anomaly_model._winner_type = _anomaly_type

    from preprocessing.anomaly_prep import AnomalyPreprocessor
    _anomaly_prep = AnomalyPreprocessor.load(
        str(BASE / 'saved_models/anomaly_preprocessor.pkl')
    )


def _load_forecast():
    global _forecast_models, _forecast_scalers
    if _forecast_models is not None:
        return

    meta_path = BASE / 'saved_models' / 'forecasting' / 'best_model.json'
    if not meta_path.exists():
        raise FileNotFoundError(
            "No trained forecast model found. Run: python train/train_forecasting.py"
        )
    with open(meta_path) as f:
        meta = json.load(f)

    winner = meta['winner']
    logger.info(f"Loading forecast model: {winner}")

    if winner == 'sarima':
        from models.forecasting import sarima_model as M
        _forecast_models = M.load(str(BASE / 'saved_models/forecasting/sarima.pkl'))
    elif winner == 'lstm':
        from models.forecasting import lstm_model as M
        _forecast_models = M.load(str(BASE / 'saved_models/forecasting/lstm.pt'))
    elif winner == 'tft':
        from models.forecasting import tft_model as M
        _forecast_models = M.load(str(BASE / 'saved_models/forecasting/tft.pt'))
    else:
        raise ValueError(f"Unknown forecast winner: {winner}")

    _forecast_models._winner = winner
    import joblib
    scalers_path = BASE / 'saved_models' / 'forecast_scalers.pkl'
    if scalers_path.exists():
        _forecast_scalers = joblib.load(scalers_path)


def _load_spend():
    global _spend_model, _spend_prep
    if _spend_model is not None:
        return

    meta_path = BASE / 'saved_models' / 'spend' / 'best_model.json'
    if not meta_path.exists():
        raise FileNotFoundError(
            "No trained spend model found. Run: python train/train_spend.py"
        )
    with open(meta_path) as f:
        meta = json.load(f)

    winner = meta['winner']
    logger.info(f"Loading spend model: {winner}")

    if winner == 'xgboost':
        from models.spend import xgboost_model as M
        _spend_model = M.load(str(BASE / 'saved_models/spend/xgboost.pkl'))
    elif winner == 'mlp_embeddings':
        from models.spend import mlp_embeddings as M
        import joblib
        prep = joblib.load(str(BASE / 'saved_models/spend_preprocessor.pkl'))
        cfg  = {'embed_dim_nic4': 16, 'embed_dim_nic2': 8,
                'embed_dim_region': 4, 'embed_dim_year': 4,
                'hidden_dims': [128, 64, 32]}
        _spend_model = M.load(
            M.MLPWithEmbeddings,
            str(BASE / 'saved_models/spend/mlp_embeddings.pt'),
            n_classes   = prep['n_classes'],
            n_numerical = 1,
            embed_dims  = {k: cfg[f'embed_dim_{k.replace("nic_4digit","nic4").replace("nic_2digit","nic2")}']
                           for k in prep['n_classes']},
            hidden_dims = cfg['hidden_dims'],
        )
    elif winner == 'tabnet':
        from models.spend import tabnet_model as M
        _spend_model = M.load(str(BASE / 'saved_models/spend/tabnet'))
    elif winner == 'naive_eeio':
        _spend_model = 'naive_eeio'

    _spend_model._winner = winner

    from preprocessing.spend_prep import SpendPreprocessor
    _spend_prep = SpendPreprocessor.load(
        str(BASE / 'saved_models/spend_preprocessor.pkl')
    )


# ── Public API ────────────────────────────────────────────────────────────────

def predict_anomaly(record: dict) -> dict:
    """
    Score a single emission record for anomalies.

    Parameters (all optional — missing fields use defaults)
    ----------
    record: {
        category_id:    int  (1-15)
        activity_value: float
        activity_unit:  int  (0=tonne, 1=tonne-km, 2=pass-km, 3=kWh)
        ef_value:       float
        calculated_co2e: float
        data_quality:   int  (0=A, 1=B, 2=C)
        region:         int  (0-4)
    }

    Returns
    -------
    {
        anomaly_score:  float   (0-1, higher = more suspicious)
        is_flagged:     bool    (True if score above threshold)
        confidence:     str     ('high' / 'medium' / 'low')
        explanation:    str
        model_used:     str
    }
    """
    import pandas as pd
    import numpy as np

    _load_anomaly()

    # Compute derived features
    act = float(record.get('activity_value', 1.0))
    ef  = float(record.get('ef_value',       1.0))
    co2 = float(record.get('calculated_co2e', (act * ef) / 1000.0))

    row = {
        'category_id':    record.get('category_id',    1),
        'activity_value': act,
        'activity_unit':  record.get('activity_unit',  0),
        'ef_value':       ef,
        'calculated_co2e': co2,
        'data_quality':   record.get('data_quality',   1),
        'region':         record.get('region',         0),
        'log_activity':   np.log1p(act),
        'log_co2e':       np.log1p(co2),
        'log_ef':         np.log1p(ef),
        'log_intensity':  np.log1p(co2 / max(act, 1e-9)),
        'log_co2e_check': np.log(np.clip(co2 / max((act * ef / 1000.0), 1e-10), 1e-6, 1e6)),
    }
    df  = pd.DataFrame([row])
    X   = _anomaly_prep.transform(df)

    wtype = getattr(_anomaly_model, '_winner_type', 'ae')
    if wtype == 'if':
        from models.anomaly import isolation_forest as M
        raw_scores = M.get_scores(_anomaly_model, X)
    elif wtype == 'ae':
        from models.anomaly import autoencoder as M
        raw_scores = M.get_scores(_anomaly_model, X)
    else:
        from models.anomaly import vae as M
        raw_scores = M.get_scores(_anomaly_model, X)

    score = float(raw_scores[0])
    meta_path = BASE / 'saved_models' / 'anomaly' / 'best_model.json'
    with open(meta_path) as f:
        meta = json.load(f)
    threshold = _get_anomaly_threshold(meta['winner'])
    normalised_score = _normalise_anomaly_score(score, threshold)
    is_flagged = score > threshold

    # Explanation heuristics
    intensity = co2 / max(act, 1e-9)
    explanation = _anomaly_explanation(record, intensity, is_flagged)
    relative_distance = abs(score - threshold) / max(abs(threshold), 1e-6)

    return {
        'anomaly_score':  round(normalised_score, 4),
        'raw_score':      round(score, 6),
        'threshold':      round(threshold, 6),
        'is_flagged':     bool(is_flagged),
        'confidence':     'high' if relative_distance > 1.0 else
                          'medium' if relative_distance > 0.25 else 'low',
        'explanation':    explanation,
        'model_used':     meta['winner'],
    }


def _anomaly_explanation(record: dict, intensity: float,
                          is_flagged: bool) -> str:
    if not is_flagged:
        return "Record appears normal based on activity-to-emission ratio."

    cat   = record.get('category_id', 1)
    unit  = record.get('activity_unit', 0)
    act   = record.get('activity_value', 1)

    hints = []
    # Unit error check
    if cat == 1 and unit == 0 and act > 100000:
        hints.append("Activity value unusually large for category 1 — possible kg/tonne unit error")
    elif cat == 4 and unit != 1 and act < 1000:
        hints.append("Activity looks like distance (km) rather than tonne-km for transport")

    # Magnitude check
    INTENSITY_LIMITS = {1: (0.05, 9.0), 4: (1e-5, 2e-3), 5: (0.01, 0.55),
                        6: (3e-5, 3e-4), 7: (2e-5, 2.5e-4)}
    limits = INTENSITY_LIMITS.get(cat)
    if limits:
        if intensity > limits[1] * 10:
            hints.append(f"Emission intensity {intensity:.6f} is >10× the expected maximum")
        elif intensity < limits[0] / 10:
            hints.append(f"Emission intensity {intensity:.6f} is <1/10 the expected minimum")

    if not hints:
        hints.append("Unusual combination of activity value, emission factor, and CO₂e")

    return " | ".join(hints)


def predict_forecast(sector: str,
                     history: list[float],
                     scaler=None) -> dict:
    """
    Forecast next 3 months for a sector/vendor.

    Parameters
    ----------
    sector  : one of 'oil', 'coal', 'gas', 'cement'
              or 'vendor' for a custom vendor series
    history : list of last 12 monthly CO₂ values (raw, not scaled)
    scaler  : optional MinMaxScaler fitted on the sector (for inverse transform)

    Returns
    -------
    {
        forecast:    [float, float, float]  next 3 months
        lower_90:    [float, float, float]
        upper_90:    [float, float, float]
        model_used:  str
    }
    """
    import torch
    from utils import get_device

    _load_forecast()
    winner = _forecast_models._winner

    if winner == 'sarima':
        # Re-fit on provided history and forecast
        import warnings
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            series = np.array(history, dtype=np.float64)
            # Use stored order for the sector if available
            if sector in _forecast_models and isinstance(_forecast_models, dict):
                order    = _forecast_models[sector]['order']
                seasonal = _forecast_models[sector]['seasonal']
            else:
                order = (2, 1, 1); seasonal = (1, 1, 0, 12)
            res = SARIMAX(series, order=order, seasonal_order=seasonal,
                          enforce_stationarity=False,
                          enforce_invertibility=False).fit(disp=False)
            fc  = res.get_forecast(steps=3)
            ci  = fc.conf_int(alpha=0.10)
        return {
            'forecast':   [round(v, 3) for v in fc.predicted_mean.tolist()],
            'lower_90':   [round(v, 3) for v in ci.iloc[:, 0].tolist()],
            'upper_90':   [round(v, 3) for v in ci.iloc[:, 1].tolist()],
            'model_used': 'SARIMA',
        }

    elif winner in ('lstm', 'tft'):
        # TFT training failed with a shape-mismatch error ("Found input variables
        # with inconsistent numbers of samples: [264, 4344]") so it should never
        # be the production winner.  If it somehow ends up as winner (e.g. after a
        # partial retrain), we fall back to LSTM weights transparently rather than
        # crashing or returning an empty dict.
        from models.forecasting import lstm_model as M

        active_model  = _forecast_models
        reported_name = 'LSTM'

        if winner == 'tft':
            logger.warning(
                "TFT is marked as winner but its training pipeline is broken "
                "(shape mismatch during evaluation). Falling back to LSTM weights."
            )
            lstm_path = BASE / 'saved_models' / 'forecasting' / 'lstm.pt'
            if not lstm_path.exists():
                raise FileNotFoundError(
                    "TFT fallback failed: LSTM weights not found at "
                    f"{lstm_path}. Run: python train/train_forecasting.py"
                )
            active_model         = M.load(str(lstm_path))
            active_model._winner = 'lstm'
            reported_name        = 'LSTM (TFT fallback)'

        # Scale input
        # The scaler was fitted on a DataFrame with column 'co2_mt' (see forecast_prep.py).
        # We must pass a DataFrame with the same column name to suppress sklearn's
        # 'X does not have valid feature names' UserWarning and ensure correct behaviour.
        import pandas as pd
        local_scaler = scaler or (_forecast_scalers.get(sector) if _forecast_scalers else None)
        series = np.array(history, dtype=np.float32)

        def _scale(arr_1d):
            """Scale a 1-D numpy array using the sector MinMaxScaler."""
            df_in = pd.DataFrame(arr_1d.reshape(-1, 1), columns=['co2_mt'])
            return local_scaler.transform(df_in).flatten()

        def _unscale(arr_1d):
            """Inverse-transform a 1-D numpy array using the sector MinMaxScaler."""
            df_in = pd.DataFrame(arr_1d.reshape(-1, 1), columns=['co2_mt'])
            return local_scaler.inverse_transform(df_in).flatten()

        if local_scaler:
            series_s = _scale(series)
        else:
            series_s = (series - series.mean()) / (series.std() + 1e-8)

        # Build feature sequence  (seq_len=12, n_features=4)
        months   = np.arange(len(series_s))
        m_sin    = np.sin(2 * np.pi * months % 12 / 12).astype(np.float32)
        m_cos    = np.cos(2 * np.pi * months % 12 / 12).astype(np.float32)
        yr_norm  = (months / max(len(series_s) - 1, 1)).astype(np.float32)
        features = np.column_stack([series_s, m_sin, m_cos, yr_norm])
        X        = features[-12:][np.newaxis]   # (1, 12, 4)

        device = get_device()
        fc     = M.get_forecast(active_model, X, device=device, n_mc=100)
        mean_s  = fc['mean'][0]
        lower_s = fc['lower'][0]
        upper_s = fc['upper'][0]

        # Inverse scale — use named DataFrame to match fitting context
        if local_scaler:
            mean_r  = _unscale(mean_s)
            lower_r = _unscale(lower_s)
            upper_r = _unscale(upper_s)
        else:
            mean_r  = mean_s * series.std() + series.mean()
            lower_r = lower_s * series.std() + series.mean()
            upper_r = upper_s * series.std() + series.mean()

        return {
            'forecast':   [round(v, 3) for v in mean_r.tolist()],
            'lower_90':   [round(v, 3) for v in lower_r.tolist()],
            'upper_90':   [round(v, 3) for v in upper_r.tolist()],
            'model_used': reported_name,
        }

    raise ValueError(
        f"Unsupported forecast winner '{winner}'. "
        "Expected one of: sarima, lstm, tft."
    )


def predict_spend(spend_inr: float, nic_4digit: int, region: str,
                  year: int = 2023) -> dict:
    """
    Estimate tCO₂e from spend data.

    Parameters
    ----------
    spend_inr  : total spend in INR
    nic_4digit : 4-digit NIC industry code
    region     : 'north' | 'south' | 'east' | 'west' | 'central'
    year       : reporting year

    Returns
    -------
    {
        estimated_co2e:    float   (tCO₂e)
        intensity:         float   (tCO₂e per INR lakh)
        confidence_band:   [lower, upper]
        data_quality:      'C'     (spend-based always C-grade)
        methodology:       str
        model_used:        str
    }
    """
    _load_spend()

    # Encode using preprocessor
    import pandas as pd
    row = pd.DataFrame([{
        'nic_4digit': nic_4digit,
        'nic_2digit': nic_4digit // 100,
        'region':     region,
        'year':       year,
        'inr_usd':    83.0,  # approx
    }])

    enc = _spend_prep.transform(row)
    winner = _spend_model._winner if hasattr(_spend_model, '_winner') else 'unknown'

    if winner == 'xgboost':
        from models.spend import xgboost_model as M
        X_flat  = _spend_prep.to_flat_array(enc)
        log_int = float(M.get_predictions(_spend_model, X_flat)[0])
    elif winner == 'mlp_embeddings':
        from models.spend import mlp_embeddings as M
        log_int = float(M.get_predictions(_spend_model, enc)[0])
    elif winner == 'tabnet':
        from models.spend import tabnet_model as M
        X_flat  = _spend_prep.to_flat_array(enc)
        log_int = float(M.get_predictions(_spend_model, X_flat)[0])
    else:
        # Naive lookup
        log_int = -10.0  # fallback

    # The trained spend targets are on a tCO2e/INR-lakh scale.
    # An older comment/key name referred to kg, which would understate
    # outputs by 1000x if we divided again here.
    intensity_t_per_lakh = float(np.exp(log_int))
    spend_lakh = spend_inr / 100000.0
    co2e_tonne = intensity_t_per_lakh * spend_lakh

    # Uncertainty: ±20% (typical spend-based estimation error)
    lower = co2e_tonne * 0.80
    upper = co2e_tonne * 1.20

    return {
        'estimated_co2e':  round(co2e_tonne, 4),
        'intensity_t_per_lakh_inr': round(intensity_t_per_lakh, 6),
        # Legacy compatibility alias for older clients reading the kg field.
        'intensity_kg_per_lakh_inr': round(intensity_t_per_lakh * 1000.0, 6),
        'confidence_band': [round(lower, 4), round(upper, 4)],
        'data_quality':    'C',
        'spend_inr':       spend_inr,
        'methodology':     (
            f'Spend-based estimation using {winner} model. '
            f'CO₂e = (spend ÷ 1,00,000) × {intensity_t_per_lakh:.4f} tCO₂e/₹lakh. '
            f'Aligned to GHG Protocol Category 1 spend-based method.'
        ),
        'model_used': winner,
    }


# ── Health check ──────────────────────────────────────────────────────────────

def health_check() -> dict:
    """Check which models are loaded and ready."""
    status = {}
    for task, loader, var in [
        ('anomaly',     _load_anomaly,    '_anomaly_model'),
        ('forecasting', _load_forecast,   '_forecast_models'),
        ('spend',       _load_spend,      '_spend_model'),
    ]:
        try:
            loader()
            status[task] = 'ready'
        except FileNotFoundError:
            status[task] = 'not_trained'
        except Exception as e:
            status[task] = f'error: {e}'
    return status


if __name__ == '__main__':
    print("Running inference health check...")
    status = health_check()
    print(json.dumps(status, indent=2))

    if status.get('anomaly') == 'ready':
        test_record = {
            'category_id': 1, 'activity_value': 1200.0,
            'activity_unit': 0, 'ef_value': 1890.0,
            'calculated_co2e': 2.268, 'data_quality': 0, 'region': 0
        }
        result = predict_anomaly(test_record)
        print("\nAnomaly test:", json.dumps(result, indent=2))

    if status.get('forecasting') == 'ready':
        history = [300 + i * 2 + np.random.randn() * 5 for i in range(12)]
        result  = predict_forecast('oil', history)
        print("\nForecast test:", json.dumps(result, indent=2))

    if status.get('spend') == 'ready':
        result = predict_spend(
            spend_inr  = 5_000_000,   # ₹50 lakh
            nic_4digit = 2410,        # Basic iron and steel
            region     = 'north',
            year       = 2023,
        )
        print("\nSpend estimation test:", json.dumps(result, indent=2))
