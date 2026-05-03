"""
Master pipeline — runs all three tasks in sequence.

Steps:
  1. Generate / download all datasets
  2. Train all 9 models (3 per task)
  3. Evaluate and compare
  4. Save best model per task
  5. Print final summary table
  6. Test inference service

Usage:
  cd scope3-ml
  pip install -r requirements.txt
  python run_all.py

Individual tasks:
  python train/train_anomaly.py
  python train/train_forecasting.py
  python train/train_spend.py
"""

import sys
import os
import json
import time
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
from utils import set_seed, get_logger, ensure_dir

logger = get_logger('run_all')


def print_banner(text: str):
    bar = "=" * 70
    print(f"\n{bar}")
    print(f"  {text}")
    print(f"{bar}\n")


def run_data_pipeline():
    print_banner("STEP 1: DATA GENERATION & DOWNLOAD")
    ensure_dir('data/processed')

    # Task 1: anomaly (fully synthetic — fast)
    if not Path('data/processed/anomaly_dataset.csv').exists():
        logger.info("Generating anomaly dataset...")
        from data.generate_anomaly_data import generate_dataset
        df = generate_dataset(n_normal=15000, anomaly_rate=0.07)
        df.to_csv('data/processed/anomaly_dataset.csv', index=False)
        logger.info(f"  → {len(df):,} records saved")
    else:
        logger.info("Anomaly dataset already exists — skipping")

    # Task 2: forecasting (try download, fallback synthetic)
    if not Path('data/processed/forecast_dataset.csv').exists():
        logger.info("Fetching India monthly CO2 data...")
        from data.fetch_forecast_data import (
            _try_download_robbie_andrew, _parse_robbie_andrew,
            _build_from_annual, add_time_features
        )
        raw = _try_download_robbie_andrew()
        if raw is not None:
            monthly = _parse_robbie_andrew(raw)
        if raw is None or monthly is None:
            logger.info("  → Using synthetic annual disaggregation")
            monthly = _build_from_annual()
        df = add_time_features(monthly)
        df.to_csv('data/processed/forecast_dataset.csv', index=False)
        logger.info(f"  → {len(df):,} rows saved")
    else:
        logger.info("Forecast dataset already exists — skipping")

    # Task 3: spend estimation (synthetic from NIC sector profiles)
    if not Path('data/processed/spend_dataset.csv').exists():
        logger.info("Building spend estimation dataset...")
        from data.fetch_spend_data import build_dataset
        df = build_dataset(augmentation_factor=5, noise_std=0.15)
        df.to_csv('data/processed/spend_dataset.csv', index=False)
        logger.info(f"  → {len(df):,} rows saved")
    else:
        logger.info("Spend dataset already exists — skipping")

    print("✅ All datasets ready")


def run_anomaly_training():
    print_banner("STEP 2a: ANOMALY DETECTION — Training 3 Models")
    from train.train_anomaly import run
    run()


def run_forecasting_training():
    print_banner("STEP 2b: EMISSION FORECASTING — Training 3 Models")
    from train.train_forecasting import run
    run()


def run_spend_training():
    print_banner("STEP 2c: SPEND ESTIMATION — Training 3 Models")
    from train.train_spend import run
    run()


def print_final_summary():
    print_banner("FINAL SUMMARY — All Tasks")

    results_files = {
        'Anomaly Detection':  'results/anomaly_comparison.json',
        'Emission Forecasting': 'results/forecasting_comparison.json',
        'Spend Estimation':   'results/spend_comparison.json',
    }

    for task, fpath in results_files.items():
        if not Path(fpath).exists():
            print(f"  {task}: results not found (training may have failed)")
            continue
        with open(fpath) as f:
            res = json.load(f)
        winner = res.get('winner', {})
        print(f"\n{'─'*60}")
        print(f"  Task:   {task}")
        print(f"  Winner: {winner.get('winner', '?').upper()}")
        print(f"  Reason: {winner.get('reason', '?')}")

        models = res.get('models', {})
        # Print compact comparison
        if task == 'Anomaly Detection':
            print(f"  {'Model':<22} {'PR-AUC':>8} {'ROC-AUC':>8} {'F1@10%FPR':>10}")
            for m, v in models.items():
                marker = " ✓" if m == winner.get('winner') else "  "
                print(f"  {m:<22}{marker}"
                      f"{v.get('pr_auc',0):>8.4f}"
                      f"{v.get('roc_auc',0):>8.4f}"
                      f"{v.get('f1',0):>10.4f}")

        elif task == 'Emission Forecasting':
            print(f"  {'Model':<12} {'MAE':>8} {'MAPE%':>8} {'Cover90':>9}")
            for m, v in models.items():
                if 'error' in v: continue
                marker = " ✓" if m == winner.get('winner') else "  "
                print(f"  {m:<12}{marker}"
                      f"{v.get('mae',0):>8.4f}"
                      f"{v.get('mape_pct', v.get('mape', 0)):>8.2f}"
                      f"{v.get('pi_coverage_90', v.get('coverage_90', 0)):>9.3f}")

        elif task == 'Spend Estimation':
            print(f"  {'Model':<22} {'R²':>8} {'MAPE%':>8} {'MAE(log)':>10}")
            for m, v in models.items():
                marker = " ✓" if m == winner.get('winner') else "  "
                print(f"  {m:<22}{marker}"
                      f"{v.get('r2_log',v.get('r2',0)):>8.4f}"
                      f"{v.get('mape_pct', v.get('mape', 0)):>8.2f}"
                      f"{v.get('mae_log',0):>10.4f}")

    print(f"\n{'─'*60}")
    print("\n  Saved models: saved_models/")
    print("  Plots:        results/plots/")
    print("  Results JSON: results/")


def run_inference_test():
    print_banner("STEP 3: INFERENCE SERVICE TEST")
    from serving.inference import health_check, predict_anomaly, predict_spend
    import numpy as np

    status = health_check()
    print(f"Model status: {json.dumps(status, indent=2)}")

    if status.get('anomaly') == 'ready':
        # Test with a normal record
        normal = {'category_id': 1, 'activity_value': 500.0,
                  'activity_unit': 0, 'ef_value': 1890.0,
                  'calculated_co2e': 0.945, 'data_quality': 0, 'region': 0}
        r = predict_anomaly(normal)
        print(f"\n  Normal record — score: {r['anomaly_score']}  flagged: {r['is_flagged']}")

        # Test with an anomalous record (unit error)
        anomalous = {**normal, 'activity_value': 500000.0, 'calculated_co2e': 945.0}
        r = predict_anomaly(anomalous)
        print(f"  Anomalous record — score: {r['anomaly_score']}  flagged: {r['is_flagged']}")
        print(f"  Explanation: {r['explanation']}")

    if status.get('spend') == 'ready':
        r = predict_spend(5_000_000, 2410, 'north', 2023)
        print(f"\n  Spend estimate (₹50L, NIC 2410 — Steel, North India):")
        print(f"    CO₂e: {r['estimated_co2e']} tCO₂e")
        print(f"    Band: {r['confidence_band']}")

    print("\n✅ Inference service working")


if __name__ == '__main__':
    set_seed(42)
    total_start = time.time()

    run_data_pipeline()
    run_anomaly_training()
    run_forecasting_training()
    run_spend_training()
    print_final_summary()
    run_inference_test()

    elapsed = time.time() - total_start
    print(f"\n{'='*70}")
    print(f"  Total pipeline time: {elapsed/60:.1f} minutes")
    print(f"{'='*70}")
