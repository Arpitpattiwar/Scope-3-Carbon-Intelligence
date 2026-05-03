"""
Train and compare all three spend-based emission estimation models.

Models:
  0. Naive EEIO lookup (floor baseline — deterministic, no ML)
  1. XGBoost + SHAP  (gradient boosting baseline)
  2. MLP + Entity Embeddings (DL with structured embeddings)
  3. TabNet            (attention-based tabular DL)

Outputs:
  saved_models/spend/xgboost.pkl
  saved_models/spend/mlp_embeddings.pt
  saved_models/spend/tabnet/
  saved_models/spend/best_model.json
  results/spend_comparison.json
  results/plots/spend_*.png

Usage:
  cd scope3-ml
  python train/train_spend.py
"""

import sys, os, json, time
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import set_seed, load_config, get_logger, save_json, ensure_dir
from data.fetch_spend_data import build_dataset
from preprocessing.spend_prep import load_splits, CATEGORICAL_FEATURES

from models.spend import xgboost_model  as XGB
from models.spend import mlp_embeddings as MLP
from models.spend import tabnet_model   as TABNET

from evaluation.metrics import regression_metrics, bootstrap_r2_ci
from evaluation.plots   import (plot_regression_scatter, plot_feature_importance,
                                  plot_training_curves, plot_per_sector_r2)

logger = get_logger('train_spend')


def naive_eeio_predict(df_test, preprocessor) -> np.ndarray:
    """
    Floor baseline: look up sector average intensity from training data.
    This is exactly what the platform does today (no ML).
    """
    # Use sector median from the full dataset as the naive prediction
    import pandas as pd
    df_all = pd.read_csv('data/processed/spend_dataset.csv')
    sector_medians = df_all.groupby('nic_4digit')['log_intensity'].median()

    preds = []
    for nic in df_test['nic_4digit'].values:
        if nic in sector_medians:
            preds.append(sector_medians[nic])
        else:
            preds.append(df_all['log_intensity'].median())   # global fallback
    return np.array(preds, dtype=np.float32)


def run():
    set_seed(42)
    cfg = load_config()
    ensure_dir('results/plots')
    ensure_dir('saved_models/spend')

    # ── 1. Generate / load data ───────────────────────────────────────────────
    data_path = 'data/processed/spend_dataset.csv'
    if not os.path.exists(data_path):
        logger.info("Building spend estimation dataset...")
        os.makedirs('data/processed', exist_ok=True)
        df = build_dataset(
            augmentation_factor = cfg['spend']['dataset'].get('augmentation_factor', 5),
            noise_std           = cfg['spend']['dataset'].get('noise_std', 0.15),
        )
        df.to_csv(data_path, index=False)
        logger.info(f"Saved {len(df):,} rows → {data_path}")

    splits = load_splits(
        data_path,
        val_size  = cfg['spend']['dataset']['val_size'],
        test_size = cfg['spend']['dataset']['test_size'],
    )

    X_train  = splits['X_train']
    X_val    = splits['X_val']
    X_test   = splits['X_test']
    y_train  = splits['y_train']
    y_val    = splits['y_val']
    y_test   = splits['y_test']
    y_test_orig = splits['y_test_orig']
    prep     = splits['preprocessor']

    feature_names = CATEGORICAL_FEATURES + ['inr_usd']

    logger.info(f"Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")
    logger.info(f"Features: {X_train.shape[1]}")

    results     = {}
    predictions = {}

    # ── 2. Naive EEIO baseline (Model 0) ─────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 0: Naive EEIO Baseline\n" + "="*50)
    naive_preds = naive_eeio_predict(splits['df_test'], prep)
    naive_m     = regression_metrics(y_test, naive_preds, y_true_orig=y_test_orig)
    results['naive_eeio']  = {**naive_m, 'train_time_s': 0.0}
    predictions['Naive EEIO'] = naive_preds
    logger.info(f"Naive — R²: {naive_m['r2_log']:.4f}  MAPE: {naive_m['mape_pct']:.2f}%")

    # ── 3. XGBoost ────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 1: XGBoost\n" + "="*50)
    t0 = time.time()

    xgb_result = XGB.train(X_train, y_train, X_val, y_val, cfg['spend']['xgboost'])
    XGB.save(xgb_result['model'])
    xgb_time   = time.time() - t0

    xgb_preds  = XGB.get_predictions(xgb_result['model'], X_test)
    xgb_m      = regression_metrics(y_test, xgb_preds, y_true_orig=y_test_orig)
    xgb_m['train_time_s'] = round(xgb_time, 2)
    results['xgboost']     = xgb_m
    predictions['XGBoost'] = xgb_preds

    # SHAP values for XGBoost
    shap_result = XGB.compute_shap(
        xgb_result['model'],
        X_test[:500],   # sample for speed
        feature_names=feature_names
    )

    logger.info(f"XGB  — R²: {xgb_m['r2_log']:.4f}  MAPE: {xgb_m['mape_pct']:.2f}%")

    # ── 4. MLP + Entity Embeddings ────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 2: MLP + Entity Embeddings\n" + "="*50)
    t0 = time.time()

    mlp_result = MLP.train(
        splits['enc_train'], y_train,
        splits['enc_val'],   y_val,
        n_classes   = splits['n_classes'],
        n_numerical = splits['n_numerical'],
        config      = cfg['spend']['mlp'],
    )
    MLP.save(mlp_result['model'])
    mlp_time   = time.time() - t0

    mlp_preds  = MLP.get_predictions(mlp_result['model'], splits['enc_test'])
    mlp_m      = regression_metrics(y_test, mlp_preds, y_true_orig=y_test_orig)
    mlp_m['train_time_s'] = round(mlp_time, 2)
    results['mlp_embeddings']     = mlp_m
    predictions['MLP+Embeddings'] = mlp_preds

    logger.info(f"MLP  — R²: {mlp_m['r2_log']:.4f}  MAPE: {mlp_m['mape_pct']:.2f}%")

    # ── 5. TabNet ─────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 3: TabNet\n" + "="*50)
    t0 = time.time()

    tabnet_result = TABNET.train(X_train, y_train, X_val, y_val,
                                  cfg['spend']['tabnet'])
    TABNET.save(tabnet_result['model'])
    tabnet_time   = time.time() - t0

    tabnet_preds  = TABNET.get_predictions(tabnet_result['model'], X_test)
    tabnet_m      = regression_metrics(y_test, tabnet_preds, y_true_orig=y_test_orig)
    tabnet_m['train_time_s'] = round(tabnet_time, 2)
    results['tabnet']      = tabnet_m
    predictions['TabNet']  = tabnet_preds

    # TabNet attention-based importance
    tabnet_imp = TABNET.get_feature_importance(
        tabnet_result['model'], feature_names=feature_names
    )

    logger.info(f"TabNet — R²: {tabnet_m['r2_log']:.4f}  MAPE: {tabnet_m['mape_pct']:.2f}%")

    # ── 6. Bootstrap CI on R² for top two DL models ──────────────────────────
    mlp_ci    = bootstrap_r2_ci(y_test, mlp_preds)
    tabnet_ci = bootstrap_r2_ci(y_test, tabnet_preds)
    xgb_ci    = bootstrap_r2_ci(y_test, xgb_preds)
    results['mlp_embeddings']['r2_ci_95']  = mlp_ci
    results['tabnet']['r2_ci_95']           = tabnet_ci
    results['xgboost']['r2_ci_95']          = xgb_ci

    # ── 7. Select best model ──────────────────────────────────────────────────
    # Primary: R² on log scale (explained variance, scale-invariant)
    # Co-primary: MAPE on original scale (business-interpretable)
    # Must beat naive EEIO baseline on MAPE, otherwise no ML selected
    ml_models  = {k: v for k, v in results.items() if k != 'naive_eeio'}
    naive_mape = results['naive_eeio'].get('mape_pct', 0)

    def selection_score(m_name):
        m = results[m_name]
        r2   = m.get('r2_log', -999)
        mape = m.get('mape_pct', 999)
        # Disqualify if doesn't beat naive baseline by >5%
        if mape > naive_mape * 0.95:
            return -999
        return results[m_name].get('r2_log', -999)

    winner = max(ml_models.keys(), key=selection_score)
    beats_naive = results[winner].get('mape_pct', 0) < naive_mape

    if not beats_naive:
        logger.warning("No ML model beats the naive EEIO baseline by >5%!")
        winner = 'naive_eeio'

    logger.info(f"\nWINNER: {winner.upper()}  "
                f"(R²={results[winner].get('r2_log', 0):.4f}, "
                f"MAPE={results[winner].get('mape_pct', 0):.2f}%)")
    logger.info(f"Naive EEIO MAPE: {naive_mape:.2f}%  |  "
                f"Improvement: {(naive_mape - results[winner].get('mape_pct', 0)):.2f}%")

    best_info = {
        'winner':        winner,
        'r2':            results[winner].get('r2_log', 0),
        'mape':          results[winner].get('mape_pct', 0),
        'beats_naive':   beats_naive,
        'naive_mape':    naive_mape,
        'improvement_pct': round(naive_mape - results[winner].get('mape_pct', 0), 2),
        'model_path': (f"saved_models/spend/{winner}.pkl"
                       if winner in ('xgboost', 'naive_eeio')
                       else f"saved_models/spend/{winner.replace('_', '_')}.pt"),
    }
    save_json(best_info, 'saved_models/spend/best_model.json')

    # ── 8. Save all results ───────────────────────────────────────────────────
    full_results = {
        'task':    'spend_emission_estimation',
        'models':  results,
        'winner':  best_info,
        'shap_top_features': (
            sorted(shap_result.get('importance_dict', {}).items(),
                   key=lambda x: x[1], reverse=True)[:5]
            if shap_result else []
        ),
    }
    save_json(full_results, 'results/spend_comparison.json')

    # ── 9. Plots ──────────────────────────────────────────────────────────────
    plot_regression_scatter(
        {k: (y_test, v) for k, v in predictions.items()},
        save_path='results/plots/spend_scatter.png',
        title='Spend Estimator — Predicted vs Actual (log scale)'
    )
    if shap_result.get('importance_dict'):
        plot_feature_importance(
            {'XGBoost (SHAP)': shap_result['importance_dict'],
             'TabNet (Attn)':  tabnet_imp.get('importance_dict', {})},
            save_path='results/plots/spend_feature_importance.png'
        )
    curves = {}
    if mlp_result.get('train_losses'):
        curves['MLP+Embeddings'] = mlp_result['train_losses']
    tabnet_hist = tabnet_result.get('history', {})
    if tabnet_hist and isinstance(tabnet_hist, dict):
        loss_key = next((k for k in tabnet_hist if 'loss' in k.lower()), None)
        if loss_key:
            curves['TabNet'] = tabnet_hist[loss_key]
    if curves:
        plot_training_curves(
            curves,
            save_path='results/plots/spend_training_curves.png',
            ylabel='Loss', title='Spend Estimator — Training Curves'
        )
    plot_per_sector_r2(
        {
            'XGBoost':         (y_test, xgb_preds,    splits['sector_groups_test']),
            'MLP+Embeddings':  (y_test, mlp_preds,    splits['sector_groups_test']),
            'TabNet':          (y_test, tabnet_preds,  splits['sector_groups_test']),
        },
        save_path='results/plots/spend_per_sector_r2.png'
    )

    # ── 10. Print comparison table ────────────────────────────────────────────
    print("\n" + "="*85)
    print(f"{'SPEND ESTIMATION — MODEL COMPARISON':^85}")
    print("="*85)
    print(f"{'Model':<20} {'R² (log)':>10} {'MAPE%':>8} {'MAE (log)':>10} "
          f"{'RMSE (log)':>10} {'Time(s)':>8}")
    print("-"*85)
    for name, m in results.items():
        marker = " ✓" if name == winner else "  "
        print(
            f"{name:<20}{marker}"
            f"{m.get('r2_log', 0):>10.4f}"
            f"{m.get('mape_pct', m.get('mape', 0)):>8.2f}"
            f"{m.get('mae_log', 0):>10.4f}"
            f"{m.get('rmse_log', 0):>10.4f}"
            f"{m.get('train_time_s', 0):>8.1f}"
        )
    print("="*85)
    print(f"\nPrimary: R² on log scale  |  Co-primary: MAPE on original scale")
    print(f"Must beat naive EEIO baseline (MAPE={naive_mape:.2f}%) to be selected")
    print(f"Winner: {winner.upper()} — saved to results/spend_comparison.json")


if __name__ == '__main__':
    run()
