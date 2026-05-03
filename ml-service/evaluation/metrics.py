"""
Unified evaluation metrics for all three tasks.
All functions return plain Python dicts for easy JSON serialisation.
"""

import numpy as np
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    precision_recall_curve, roc_curve,
    f1_score, precision_score, recall_score,
    mean_absolute_error, mean_squared_error, r2_score,
)
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


# ── Task 1: Anomaly Detection ─────────────────────────────────────────────────

def anomaly_metrics(y_true: np.ndarray, scores: np.ndarray,
                    fpr_threshold: float = 0.10,
                    k_precision: int = None) -> dict:
    """
    Comprehensive anomaly detection evaluation.

    Parameters
    ----------
    y_true        : binary labels (0=normal, 1=anomaly)
    scores        : anomaly scores (higher = more anomalous)
    fpr_threshold : FPR operating point for F1/precision reporting
    k_precision   : top-K for precision@K (defaults to 1% of dataset)
    """
    n = len(y_true)
    if k_precision is None:
        k_precision = max(1, int(n * 0.01))   # top 1%

    # AUC metrics
    roc_auc = roc_auc_score(y_true, scores)
    pr_auc  = average_precision_score(y_true, scores)   # PRIMARY metric

    # Operating point: threshold at fpr_threshold FPR
    fpr_arr, tpr_arr, thresholds = roc_curve(y_true, scores)
    idx       = np.searchsorted(fpr_arr, fpr_threshold)
    idx       = min(idx, len(thresholds) - 1)
    threshold = float(thresholds[idx])
    y_pred    = (scores >= threshold).astype(int)

    f1   = f1_score(y_true, y_pred, zero_division=0)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec  = recall_score(y_true, y_pred, zero_division=0)

    # Precision @ K
    top_k_idx  = np.argsort(scores)[::-1][:k_precision]
    prec_at_k  = float(y_true[top_k_idx].sum()) / k_precision

    # Recall @ K
    n_anomalies = y_true.sum()
    rec_at_k    = float(y_true[top_k_idx].sum()) / max(n_anomalies, 1)

    return {
        'pr_auc':        round(float(pr_auc),  4),     # PRIMARY
        'roc_auc':       round(float(roc_auc), 4),
        'f1':            round(float(f1),   4),
        'precision':     round(float(prec), 4),
        'recall':        round(float(rec),  4),
        f'precision_at_{k_precision}': round(prec_at_k, 4),
        f'recall_at_{k_precision}':    round(rec_at_k,  4),
        'threshold':     round(threshold, 6),
        'fpr_threshold': fpr_threshold,
        'n_total':       n,
        'n_anomaly':     int(y_true.sum()),
        'n_flagged':     int(y_pred.sum()),
    }


def anomaly_per_type_recall(y_true: np.ndarray, scores: np.ndarray,
                             anomaly_types: np.ndarray,
                             threshold: float) -> dict:
    """
    Compute recall per anomaly type at a given threshold.
    Useful for diagnosing which types of errors each model catches.
    """
    y_pred   = (scores >= threshold).astype(int)
    results  = {}
    for atype in np.unique(anomaly_types):
        if atype == 'none':
            continue
        mask = (anomaly_types == atype)
        n    = mask.sum()
        if n == 0:
            continue
        caught = (y_pred[mask] == 1).sum()
        results[atype] = {
            'recall':  round(float(caught / n), 4),
            'n_total': int(n),
            'n_caught': int(caught),
        }
    return results


def reconstruction_error_stats(errors_normal: np.ndarray,
                                 errors_anomaly: np.ndarray) -> dict:
    """
    Separation statistics between normal and anomaly reconstruction errors.
    Higher separation → better anomaly detection.
    """
    overlap_coeff = _overlap_coefficient(errors_normal, errors_anomaly)
    return {
        'normal_mean':   round(float(errors_normal.mean()),  4),
        'normal_std':    round(float(errors_normal.std()),   4),
        'anomaly_mean':  round(float(errors_anomaly.mean()), 4),
        'anomaly_std':   round(float(errors_anomaly.std()),  4),
        'separation_ratio': round(
            float(errors_anomaly.mean() / max(errors_normal.mean(), 1e-10)), 4
        ),
        'overlap_coefficient': round(float(overlap_coeff), 4),
    }


def _overlap_coefficient(a: np.ndarray, b: np.ndarray,
                          n_bins: int = 50) -> float:
    """Bhattacharyya overlap coefficient between two distributions."""
    lo  = min(a.min(), b.min())
    hi  = max(a.max(), b.max())
    edges = np.linspace(lo, hi, n_bins + 1)
    ha, _ = np.histogram(a, bins=edges, density=True)
    hb, _ = np.histogram(b, bins=edges, density=True)
    width = edges[1] - edges[0]
    return float(np.sum(np.minimum(ha, hb)) * width)


# ── Task 2: Forecasting ───────────────────────────────────────────────────────

def forecast_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                     y_lower: np.ndarray = None,
                     y_upper: np.ndarray = None) -> dict:
    """
    Comprehensive forecasting evaluation.

    Parameters
    ----------
    y_true  : actual values (n_samples,) or (n_samples, horizon)
    y_pred  : point forecast (same shape)
    y_lower : lower bound of prediction interval
    y_upper : upper bound of prediction interval
    """
    y_true = y_true.flatten()
    y_pred = y_pred.flatten()

    mae   = mean_absolute_error(y_true, y_pred)
    rmse  = np.sqrt(mean_squared_error(y_true, y_pred))

    # MAPE — skip near-zero actuals
    nonzero = y_true != 0
    mape    = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100)

    # sMAPE — symmetric, handles near-zero
    denom  = (np.abs(y_true) + np.abs(y_pred))
    smape  = float(np.mean(2 * np.abs(y_true - y_pred) / np.where(denom == 0, 1, denom)) * 100)

    # Directional accuracy
    if len(y_true) > 1:
        dir_true = np.diff(y_true) > 0
        dir_pred = np.diff(y_pred) > 0
        dir_acc  = float(np.mean(dir_true == dir_pred))
    else:
        dir_acc = float('nan')

    result = {
        'mae':               round(float(mae),    5),   # PRIMARY
        'rmse':              round(float(rmse),   5),
        'mape_pct':          round(mape, 3),
        'smape_pct':         round(smape, 3),
        'directional_acc':   round(dir_acc, 4),
    }

    # Prediction interval coverage (if provided)
    if y_lower is not None and y_upper is not None:
        y_lo = y_lower.flatten()
        y_hi = y_upper.flatten()
        inside   = ((y_true >= y_lo) & (y_true <= y_hi)).mean()
        avg_width = float((y_hi - y_lo).mean())
        result['pi_coverage_90'] = round(float(inside), 4)   # CO-PRIMARY
        result['pi_avg_width']   = round(avg_width, 5)

    return result


def diebold_mariano_test(y_true: np.ndarray,
                          pred_a: np.ndarray,
                          pred_b: np.ndarray,
                          h: int = 1) -> dict:
    """
    Diebold-Mariano test for equal predictive accuracy.
    H0: models A and B have equal forecast accuracy (MAE-based).
    p < 0.05 → significant difference; prefer lower-error model.
    """
    e_a = np.abs(y_true.flatten() - pred_a.flatten())
    e_b = np.abs(y_true.flatten() - pred_b.flatten())
    d   = e_a - e_b   # loss differential: positive means A is worse

    n      = len(d)
    d_mean = d.mean()

    # Harvey, Leybourne, Newbold (1997) correction
    gamma_0 = np.var(d, ddof=1)
    gamma   = [np.cov(d[:-k], d[k:])[0, 1] for k in range(1, h + 1)]
    var_d   = (gamma_0 + 2 * sum(gamma)) / n
    dm_stat = d_mean / np.sqrt(max(var_d, 1e-12))

    p_value = 2 * (1 - stats.norm.cdf(np.abs(dm_stat)))
    return {
        'dm_statistic': round(float(dm_stat), 4),
        'p_value':      round(float(p_value), 4),
        'significant':  p_value < 0.05,
        'better_model': 'B' if d_mean > 0 else 'A',
        'mean_loss_diff': round(float(d_mean), 5),
    }


# ── Task 3: Spend Estimation ──────────────────────────────────────────────────

def regression_metrics(y_true: np.ndarray, y_pred_log: np.ndarray,
                        y_true_orig: np.ndarray = None,
                        y_pred_orig: np.ndarray = None) -> dict:
    """
    Regression metrics for emission intensity estimation.
    Log-scale metrics are PRIMARY. Original-scale MAPE is CO-PRIMARY.

    Parameters
    ----------
    y_true      : log-scale targets
    y_pred_log  : log-scale predictions
    y_true_orig : original-scale targets (optional)
    y_pred_orig : original-scale predictions (optional, else computed from y_pred_log)
    """
    mae_log  = mean_absolute_error(y_true, y_pred_log)
    rmse_log = np.sqrt(mean_squared_error(y_true, y_pred_log))
    r2_log   = r2_score(y_true, y_pred_log)

    result = {
        'r2_log':   round(float(r2_log),   4),   # PRIMARY
        'mae_log':  round(float(mae_log),  5),
        'rmse_log': round(float(rmse_log), 5),
    }

    # Original-scale metrics
    if y_true_orig is not None:
        if y_pred_orig is None:
            y_pred_orig = np.exp(y_pred_log)

        # MAPE — skip near-zero
        nonzero = y_true_orig > 1e-10
        if nonzero.sum() > 0:
            mape = float(np.mean(
                np.abs(y_true_orig[nonzero] - y_pred_orig[nonzero]) / y_true_orig[nonzero]
            ) * 100)
        else:
            mape = float('nan')

        mae_orig  = mean_absolute_error(y_true_orig, y_pred_orig)
        rmse_orig = np.sqrt(mean_squared_error(y_true_orig, y_pred_orig))
        r2_orig   = r2_score(y_true_orig, y_pred_orig)

        result.update({
            'mape_pct':   round(mape,            3),   # CO-PRIMARY
            'mae_orig':   round(float(mae_orig),  6),
            'rmse_orig':  round(float(rmse_orig), 6),
            'r2_orig':    round(float(r2_orig),   4),
        })

    return result


def per_sector_r2(y_true: np.ndarray, y_pred: np.ndarray,
                   sector_labels: np.ndarray,
                   top_n: int = 10) -> dict:
    """
    R² per NIC-2 sector group. Shows where the model is strong vs weak.
    """
    groups = np.unique(sector_labels)
    results = {}
    for g in groups:
        mask = sector_labels == g
        if mask.sum() < 5:
            continue
        r2 = r2_score(y_true[mask], y_pred[mask])
        results[int(g)] = {'r2': round(float(r2), 4), 'n': int(mask.sum())}

    # Sort by R²
    sorted_groups = sorted(results.items(), key=lambda x: x[1]['r2'], reverse=True)
    return {
        'per_group': dict(sorted_groups),
        'best':  sorted_groups[:3]  if sorted_groups else [],
        'worst': sorted_groups[-3:] if sorted_groups else [],
    }


def naive_eeio_baseline(y_true_orig: np.ndarray) -> dict:
    """
    Simulate the naive EEIO lookup baseline:
    Use the sector mean as the prediction (what a simple lookup table gives).
    This is the floor that ML models must beat.
    """
    mean_pred = np.full_like(y_true_orig, y_true_orig.mean())
    mape = float(np.mean(
        np.abs(y_true_orig - mean_pred) / np.where(y_true_orig > 1e-10, y_true_orig, 1)
    ) * 100)
    return {
        'model':    'Naive EEIO Lookup (sector mean)',
        'r2':       0.0,   # by definition (predicting mean → R²=0)
        'mape_pct': round(mape, 3),
        'mae_log':  round(float(mean_absolute_error(
            np.log(np.maximum(y_true_orig, 1e-10)),
            np.log(np.full_like(y_true_orig, y_true_orig.mean()))
        )), 5),
    }

# ── Aliases matching train script call signatures ─────────────────────────────

def per_type_recall(y_true, scores, anomaly_types, fpr_threshold):
    """Alias: compute threshold then call anomaly_per_type_recall."""
    from sklearn.metrics import roc_curve
    fpr_arr, _, thresholds = roc_curve(y_true, scores)
    idx = min(np.searchsorted(fpr_arr, fpr_threshold), len(thresholds) - 1)
    threshold = float(thresholds[idx])
    return anomaly_per_type_recall(y_true, scores, anomaly_types, threshold)


def delong_auc_test(y_true, scores_a, scores_b):
    """
    Approximate DeLong test for difference in ROC-AUC between two models.
    Uses bootstrap resampling (simpler than exact DeLong, adequate for n>500).
    """
    n        = len(y_true)
    n_boot   = 1000
    rng      = np.random.default_rng(42)
    diffs    = []
    for _ in range(n_boot):
        idx   = rng.integers(0, n, n)
        auc_a = roc_auc_score(y_true[idx], scores_a[idx])
        auc_b = roc_auc_score(y_true[idx], scores_b[idx])
        diffs.append(auc_a - auc_b)
    diffs  = np.array(diffs)
    # Two-sided p-value: fraction of bootstrap samples where diff crosses zero
    p_val  = float(2 * min((diffs >= 0).mean(), (diffs <= 0).mean()))
    return {
        'auc_a':         round(float(roc_auc_score(y_true, scores_a)), 4),
        'auc_b':         round(float(roc_auc_score(y_true, scores_b)), 4),
        'mean_diff':     round(float(diffs.mean()), 4),
        'p_value':       round(p_val, 4),
        'significant':   p_val < 0.05,
    }


def coverage(y_true, y_lower, y_upper):
    """Fraction of actuals inside the prediction interval."""
    inside = ((y_true >= y_lower) & (y_true <= y_upper)).mean()
    return round(float(inside), 4)


def bootstrap_r2_ci(y_true, y_pred, n_boot=500, ci=0.95):
    """Bootstrap 95% confidence interval on R²."""
    rng    = np.random.default_rng(42)
    n      = len(y_true)
    scores = []
    for _ in range(n_boot):
        idx  = rng.integers(0, n, n)
        scores.append(r2_score(y_true[idx], y_pred[idx]))
    lo = round(float(np.percentile(scores, (1 - ci) / 2 * 100)), 4)
    hi = round(float(np.percentile(scores, (1 + ci) / 2 * 100)), 4)
    return [lo, hi]
