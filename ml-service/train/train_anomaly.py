"""
Train and compare all three anomaly detection models.

Models:
  1. Isolation Forest (sklearn baseline)
  2. Autoencoder     (PyTorch)
  3. VAE             (PyTorch)

Outputs:
  saved_models/anomaly/isolation_forest.pkl
  saved_models/anomaly/autoencoder.pt
  saved_models/anomaly/vae.pt
  saved_models/anomaly/best_model.json   ← which model won + why
  results/anomaly_comparison.json
  results/plots/anomaly_*.png

Usage:
  cd scope3-ml
  python train/train_anomaly.py
"""

import sys
import os
import json
import time
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import set_seed, load_config, get_logger, save_json, ensure_dir
from data.generate_anomaly_data import generate_dataset
from preprocessing.anomaly_prep import load_splits

from models.anomaly import isolation_forest as IF
from models.anomaly import autoencoder      as AE
from models.anomaly import vae              as VAE_MOD

from evaluation.metrics import anomaly_metrics, per_type_recall, delong_auc_test
from evaluation.plots   import (plot_pr_curves, plot_roc_curves,
                                 plot_reconstruction_histograms,
                                 plot_training_curves, plot_per_type_recall)

logger = get_logger('train_anomaly')


def run():
    set_seed(42)
    cfg = load_config()
    ensure_dir('results/plots')
    ensure_dir('saved_models/anomaly')

    # ── 1. Generate / load data ───────────────────────────────────────────────
    data_path = 'data/processed/anomaly_dataset.csv'
    if not os.path.exists(data_path):
        logger.info("Generating synthetic anomaly dataset...")
        df = generate_dataset(
            n_normal    = cfg['anomaly']['dataset']['n_normal'],
            anomaly_rate = cfg['anomaly']['dataset']['anomaly_rate'],
        )
        df.to_csv(data_path, index=False)
        logger.info(f"Saved {len(df):,} records → {data_path}")

    splits = load_splits(
        data_path,
        val_size  = cfg['anomaly']['dataset']['val_size'],
        test_size = cfg['anomaly']['dataset']['test_size'],
    )
    X_train = splits['X_train']
    X_val   = splits['X_val']
    X_test  = splits['X_test']
    y_train = splits['y_train']
    y_val   = splits['y_val']
    y_test  = splits['y_test']
    anomaly_types_test = splits['anomaly_types_test']

    logger.info(f"Features: {X_train.shape[1]}  |  "
                f"Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")

    results  = {}
    all_scores = {}
    histories  = {}

    # ── 2. Isolation Forest ───────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 1: Isolation Forest\n" + "="*50)
    t0 = time.time()

    if_result = IF.train(X_train, X_val, y_val, cfg['anomaly']['isolation_forest'])
    IF.save(if_result['model'])
    if_time = time.time() - t0

    if_scores_test = IF.get_scores(if_result['model'], X_test)
    if_metrics     = anomaly_metrics(
        y_test, if_scores_test,
        fpr_threshold = cfg['anomaly']['evaluation']['fpr_threshold']
    )
    if_per_type = per_type_recall(y_test, if_scores_test, anomaly_types_test,
                                   cfg['anomaly']['evaluation']['fpr_threshold'])

    results['isolation_forest'] = {**if_metrics, 'train_time_s': round(if_time, 2)}
    all_scores['Isolation Forest'] = if_scores_test
    logger.info(f"IF — PR-AUC: {if_metrics['pr_auc']:.4f}  "
                f"ROC-AUC: {if_metrics['roc_auc']:.4f}  "
                f"F1@FPR: {if_metrics['f1']:.4f}")

    # ── 3. Autoencoder ────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 2: Autoencoder\n" + "="*50)
    t0 = time.time()

    ae_result = AE.train(X_train, X_val, y_val, cfg['anomaly']['autoencoder'])
    AE.save(ae_result['model'])
    ae_time = time.time() - t0

    ae_scores_test = AE.get_scores(ae_result['model'], X_test)
    ae_metrics     = anomaly_metrics(
        y_test, ae_scores_test,
        fpr_threshold = cfg['anomaly']['evaluation']['fpr_threshold']
    )
    ae_per_type = per_type_recall(y_test, ae_scores_test, anomaly_types_test,
                                   cfg['anomaly']['evaluation']['fpr_threshold'])

    results['autoencoder'] = {**ae_metrics, 'train_time_s': round(ae_time, 2)}
    all_scores['Autoencoder']     = ae_scores_test
    histories['Autoencoder']      = ae_result['train_losses']
    logger.info(f"AE  — PR-AUC: {ae_metrics['pr_auc']:.4f}  "
                f"ROC-AUC: {ae_metrics['roc_auc']:.4f}  "
                f"F1@FPR: {ae_metrics['f1']:.4f}")

    # ── 4. VAE ────────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 3: VAE\n" + "="*50)
    t0 = time.time()

    vae_result = VAE_MOD.train(X_train, X_val, y_val, cfg['anomaly']['vae'])
    VAE_MOD.save(vae_result['model'])
    vae_time = time.time() - t0

    vae_scores_test = VAE_MOD.get_scores(vae_result['model'], X_test)
    vae_metrics     = anomaly_metrics(
        y_test, vae_scores_test,
        fpr_threshold = cfg['anomaly']['evaluation']['fpr_threshold']
    )
    vae_per_type = per_type_recall(y_test, vae_scores_test, anomaly_types_test,
                                    cfg['anomaly']['evaluation']['fpr_threshold'])

    results['vae'] = {**vae_metrics, 'train_time_s': round(vae_time, 2)}
    all_scores['VAE']          = vae_scores_test
    histories['VAE']           = vae_result['history']['train_loss']
    logger.info(f"VAE — PR-AUC: {vae_metrics['pr_auc']:.4f}  "
                f"ROC-AUC: {vae_metrics['roc_auc']:.4f}  "
                f"F1@FPR: {vae_metrics['f1']:.4f}")

    # ── 5. Statistical significance test ─────────────────────────────────────
    # Compare best two models on ROC-AUC using DeLong test
    pr_aucs = {k: v['pr_auc'] for k, v in results.items()}
    ranked  = sorted(pr_aucs, key=pr_aucs.get, reverse=True)
    best_m, second_m = ranked[0], ranked[1]
    scores_best   = all_scores[{
        'isolation_forest': 'Isolation Forest',
        'autoencoder': 'Autoencoder',
        'vae': 'VAE'
    }[best_m]]
    scores_second = all_scores[{
        'isolation_forest': 'Isolation Forest',
        'autoencoder': 'Autoencoder',
        'vae': 'VAE'
    }[second_m]]
    delong = delong_auc_test(y_test, scores_best, scores_second)
    logger.info(f"DeLong test ({best_m} vs {second_m}): p={delong['p_value']:.4f}")

    # ── 6. Select best model ──────────────────────────────────────────────────
    # Primary criterion: PR-AUC
    # Tiebreak (within 0.02): Precision@10%Recall
    def selection_score(m_name):
        m = results[m_name]
        return m['pr_auc'] * 1000 + m.get('precision_at_recall_10', 0)

    winner = max(results.keys(), key=selection_score)
    logger.info(f"\n{'='*50}")
    logger.info(f"WINNER: {winner.upper()}  (PR-AUC={results[winner]['pr_auc']:.4f})")
    logger.info(f"{'='*50}")

    best_info = {
        'winner':       winner,
        'reason':       f"Highest PR-AUC ({results[winner]['pr_auc']:.4f})",
        'delong_p':     delong['p_value'],
        'significant':  delong['p_value'] < 0.05,
        'model_path':   f"saved_models/anomaly/{winner.replace('_', '_')}.{'pkl' if winner == 'isolation_forest' else 'pt'}",
    }
    save_json(best_info, 'saved_models/anomaly/best_model.json')

    # ── 7. Save all results ───────────────────────────────────────────────────
    full_results = {
        'task':    'anomaly_detection',
        'models':  results,
        'winner':  best_info,
        'per_type_recall': {
            'isolation_forest': if_per_type,
            'autoencoder':      ae_per_type,
            'vae':              vae_per_type,
        },
    }
    save_json(full_results, 'results/anomaly_comparison.json')

    # ── 8. Plots ──────────────────────────────────────────────────────────────
    plot_pr_curves(
        {k: (y_test, v) for k, v in all_scores.items()},
        save_path='results/plots/anomaly_pr_curves.png',
        title='Anomaly Detection — Precision-Recall Curves'
    )
    plot_roc_curves(
        {k: (y_test, v) for k, v in all_scores.items()},
        save_path='results/plots/anomaly_roc_curves.png',
        title='Anomaly Detection — ROC Curves'
    )
    plot_reconstruction_histograms(
        {'Autoencoder': (y_test, ae_scores_test),
         'VAE':         (y_test, vae_scores_test)},
        save_path='results/plots/anomaly_reconstruction_errors.png'
    )
    if histories:
        plot_training_curves(
            histories,
            save_path='results/plots/anomaly_training_curves.png',
            ylabel='Reconstruction Loss',
            title='Anomaly Models — Training Loss'
        )
    plot_per_type_recall(
        {'Isolation Forest': if_per_type,
         'Autoencoder':      ae_per_type,
         'VAE':              vae_per_type},
        save_path='results/plots/anomaly_per_type_recall.png'
    )

    # ── 9. Print comparison table ─────────────────────────────────────────────
    print("\n" + "="*80)
    print(f"{'ANOMALY DETECTION — MODEL COMPARISON':^80}")
    print("="*80)
    hdr = f"{'Model':<20} {'PR-AUC':>8} {'ROC-AUC':>8} {'F1@FPR':>10} {'P@K':>8} {'Time(s)':>8}"
    print(hdr)
    print("-"*80)
    for name, m in results.items():
        marker = " ✓" if name == winner else "  "
        print(
            f"{name:<20}{marker}"
            f"{m['pr_auc']:>8.4f}"
            f"{m['roc_auc']:>8.4f}"
            f"{m['f1']:>10.4f}"
            f"{next((v for k,v in m.items() if k.startswith('precision_at_')), 0):>8.4f}"
            f"{m['train_time_s']:>8.1f}"
        )
    print("="*80)
    print(f"\nPrimary metric: PR-AUC (handles class imbalance correctly)")
    print(f"Winner: {winner.upper()} — saved to results/anomaly_comparison.json")


if __name__ == '__main__':
    run()
