"""
Train and compare all three emission forecasting models.

Models:
  1. SARIMA    (statsmodels baseline — one per sector)
  2. LSTM      (PyTorch — multi-step, MC Dropout intervals)
  3. TFT       (pytorch-forecasting — quantile outputs, attention)

Outputs:
  saved_models/forecasting/sarima.pkl
  saved_models/forecasting/lstm.pt
  saved_models/forecasting/tft.pt
  saved_models/forecasting/best_model.json
  results/forecasting_comparison.json
  results/plots/forecast_*.png

Usage:
  cd scope3-ml
  python train/train_forecasting.py
"""

import sys, os, json, time
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import set_seed, load_config, get_logger, save_json, ensure_dir
from data.fetch_forecast_data import (
    _build_from_annual, add_time_features, build_sequence_dataset
)
from preprocessing.forecast_prep import load_splits

from models.forecasting import sarima_model  as SARIMA
from models.forecasting import lstm_model    as LSTM
try:
    from models.forecasting import tft_model as TFT
    TFT_AVAILABLE = True
except ImportError:
    TFT_AVAILABLE = False

from evaluation.metrics  import forecast_metrics, diebold_mariano_test, coverage
from evaluation.plots    import (plot_forecast_comparison, plot_training_curves)

logger = get_logger('train_forecasting')


def run():
    set_seed(42)
    cfg = load_config()
    ensure_dir('results/plots')
    ensure_dir('saved_models/forecasting')

    # ── 1. Download / load data ───────────────────────────────────────────────
    data_path = 'data/processed/forecast_dataset.csv'
    if not os.path.exists(data_path):
        logger.info("Fetching / generating India monthly CO2 data...")
        os.makedirs('data/processed', exist_ok=True)
        # Try real download first, fall back to synthetic
        from data.fetch_forecast_data import (
            _try_download_robbie_andrew, _parse_robbie_andrew
        )
        raw = _try_download_robbie_andrew()
        if raw is not None:
            monthly = _parse_robbie_andrew(raw)
        if raw is None or monthly is None:
            monthly = _build_from_annual()
        df = add_time_features(monthly)
        df.to_csv(data_path, index=False)
        logger.info(f"Saved → {data_path}  ({len(df):,} rows)")

    splits = load_splits(
        data_path,
        test_months = cfg['forecasting']['dataset'].get('test_months', 12),
        val_months  = cfg['forecasting']['dataset'].get('val_months',  12),
        seq_len     = cfg['forecasting']['dataset']['seq_len'],
        horizon     = cfg['forecasting']['dataset']['horizon'],
    )

    X_train     = splits['X_train']
    y_train     = splits['y_train']
    X_val       = splits['X_val']
    y_val       = splits['y_val']
    X_test      = splits['X_test']
    y_test      = splits['y_test']
    sector_data = splits['sector_data']
    scalers     = splits['scalers']

    logger.info(
        f"Sequences — train: {X_train.shape}  val: {X_val.shape}  test: {X_test.shape}"
    )

    results    = {}
    forecasts  = {}

    # ── 2. SARIMA ─────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 1: SARIMA\n" + "="*50)
    t0 = time.time()

    sarima_models = SARIMA.train(sector_data, cfg['forecasting']['sarima'])
    SARIMA.save(sarima_models)
    sarima_time   = time.time() - t0

    # Generate test forecasts (rolling, expanding window — realistic protocol)
    sarima_fc = SARIMA.get_forecast(sarima_models, sector_data, horizon=splits['horizon'], split='test')

    # Aggregate across sectors for overall metrics
    sarima_preds   = np.concatenate([v['preds']   for v in sarima_fc.values()])
    sarima_actuals = np.concatenate([v['actuals'] for v in sarima_fc.values()])
    sarima_lowers  = np.concatenate([v['lowers']  for v in sarima_fc.values()])
    sarima_uppers  = np.concatenate([v['uppers']  for v in sarima_fc.values()])

    sarima_m = forecast_metrics(
        sarima_actuals, sarima_preds,
        y_lower=sarima_lowers, y_upper=sarima_uppers
    )
    sarima_m['train_time_s'] = round(sarima_time, 2)
    results['sarima']  = sarima_m
    forecasts['SARIMA'] = {'preds': sarima_preds, 'actuals': sarima_actuals,
                            'lowers': sarima_lowers, 'uppers': sarima_uppers}

    logger.info(f"SARIMA — MAE: {sarima_m['mae']:.4f}  MAPE: {sarima_m['mape_pct']:.2f}%  "
                f"Coverage90: {sarima_m.get('pi_coverage_90', 0):.3f}")

    # ── 3. LSTM ───────────────────────────────────────────────────────────────
    logger.info("\n" + "="*50 + "\n  MODEL 2: LSTM\n" + "="*50)
    t0 = time.time()

    lstm_result = LSTM.train(X_train, y_train, X_val, y_val, cfg['forecasting']['lstm'])
    LSTM.save(lstm_result['model'])
    lstm_time   = time.time() - t0

    lstm_fc    = LSTM.get_forecast(
        lstm_result['model'], X_test,
        n_mc = cfg['forecasting']['lstm'].get('mc_dropout_samples', 100)
    )
    lstm_m = forecast_metrics(
        y_test.flatten(), lstm_fc['mean'].flatten(),
        y_lower=lstm_fc['lower'].flatten(),
        y_upper=lstm_fc['upper'].flatten()
    )
    lstm_m['train_time_s'] = round(lstm_time, 2)
    results['lstm'] = lstm_m
    forecasts['LSTM'] = {
        'preds':   lstm_fc['mean'].flatten(),
        'actuals': y_test.flatten(),
        'lowers':  lstm_fc['lower'].flatten(),
        'uppers':  lstm_fc['upper'].flatten(),
    }

    logger.info(f"LSTM  — MAE: {lstm_m['mae']:.4f}  MAPE: {lstm_m['mape_pct']:.2f}%  "
                f"Coverage90: {lstm_m.get('pi_coverage_90', 0):.3f}")

    # ── 4. TFT ────────────────────────────────────────────────────────────────
    if not TFT_AVAILABLE:
        logger.warning("TFT skipped — install pytorch-forecasting to enable")
        results['tft'] = {'error': 'pytorch-forecasting not installed', 'mae': 999, 'mape_pct': 999, 'pi_coverage_90': 0}
    else:
        logger.info("\n" + "="*50 + "\n  MODEL 3: TFT\n" + "="*50)
        t0 = time.time()

    tft_cfg = {**cfg['forecasting']['tft'],
               'seq_len': splits['seq_len'],
               'horizon': splits['horizon']}
    try:
        tft_result = TFT.train(sector_data, tft_cfg)
        TFT.save(tft_result, 'saved_models/forecasting/tft.pt')
        tft_time   = time.time() - t0

        # Generate predictions using TFT's quantile output
        from torch.utils.data import DataLoader
        val_loader = tft_result['dataset'].to_dataloader(
            train=False, batch_size=128, num_workers=0
        )
        tft_fc = TFT.get_forecast(
            tft_result['model'], sector_data, val_loader,
            quantiles=tft_result['quantiles']
        )
        tft_mean = tft_fc['mean'].flatten()
        tft_lo   = tft_fc['lower'].flatten()
        tft_hi   = tft_fc['upper'].flatten()
        tft_act  = y_test.flatten()[:len(tft_mean)]   # align lengths

        tft_m = forecast_metrics(
            tft_act, tft_mean,
            y_lower=tft_lo[:len(tft_act)],
            y_upper=tft_hi[:len(tft_act)]
        )
        tft_m['train_time_s'] = round(tft_time, 2)
        results['tft'] = tft_m
        forecasts['TFT'] = {
            'preds': tft_mean, 'actuals': tft_act,
            'lowers': tft_lo,  'uppers': tft_hi,
        }
        logger.info(f"TFT   — MAE: {tft_m['mae']:.4f}  MAPE: {tft_m['mape_pct']:.2f}%  "
                    f"Coverage90: {tft_m.get('pi_coverage_90', 0):.3f}")
    except Exception as e:
        logger.warning(f"TFT training failed: {e}. Skipping TFT.")
        results['tft'] = {'error': str(e), 'mae': 999, 'mape_pct': 999, 'pi_coverage_90': 0}

    # ── 5. Statistical significance ───────────────────────────────────────────
    if 'tft' in results and 'error' not in results['tft']:
        dm = diebold_mariano_test(
            forecasts['LSTM']['actuals'],
            forecasts['LSTM']['preds'],
            forecasts['TFT']['preds']
        )
        logger.info(f"DM test (LSTM vs TFT): statistic={dm.get('dm_statistic', dm.get('statistic')):.3f}  "
                    f"p={dm['p_value']:.4f}")
    else:
        dm = {'statistic': None, 'p_value': None}

    # ── 6. Select best model ──────────────────────────────────────────────────
    # Primary: MAE (lower is better)
    # Co-primary: 90% PI Coverage (should be close to 0.90)
    # A model with good MAE but coverage < 0.70 is disqualified
    def selection_score(m_name):
        m = results[m_name]
        if 'error' in m:
            return 1e9
        mae      = m.get('mae', 1e9)
        cov      = m.get('pi_coverage_90', 0)
        cov_pen  = max(0, 0.70 - cov) * 100   # penalty if coverage < 70%
        return mae + cov_pen

    winner = min(results.keys(), key=selection_score)
    logger.info(f"\nWINNER: {winner.upper()}  "
                f"(MAE={results[winner]['mae']:.4f}, "
                f"Coverage={results[winner]['pi_coverage_90']:.3f})")

    best_info = {
        'winner':    winner,
        'reason':    f"Lowest MAE ({results[winner]['mae']:.4f}) with adequate 90% PI coverage",
        'dm_p_value': dm['p_value'],
        'model_path': f"saved_models/forecasting/{winner}.{'pkl' if winner == 'sarima' else 'pt'}",
    }
    save_json(best_info, 'saved_models/forecasting/best_model.json')

    # ── 7. Save all results ───────────────────────────────────────────────────
    full_results = {
        'task':   'emission_forecasting',
        'models': results,
        'winner': best_info,
        'dm_test': dm,
    }
    save_json(full_results, 'results/forecasting_comparison.json')

    # ── 8. Plots ──────────────────────────────────────────────────────────────
    plot_forecast_comparison(
        forecasts,
        save_path='results/plots/forecast_comparison.png',
        title='Emission Forecasting — Model Comparison (Test Set)'
    )
    if hasattr(lstm_result, 'get') and lstm_result.get('train_losses'):
        plot_training_curves(
            {'LSTM': lstm_result['train_losses']},
            save_path='results/plots/forecast_lstm_training.png',
            ylabel='Huber Loss', title='LSTM Training Curve'
        )

    # ── 9. Print comparison table ─────────────────────────────────────────────
    print("\n" + "="*80)
    print(f"{'EMISSION FORECASTING — MODEL COMPARISON':^80}")
    print("="*80)
    print(f"{'Model':<12} {'MAE':>8} {'RMSE':>8} {'MAPE%':>8} {'sMAPE%':>8}"
          f" {'Cover90':>8} {'Time(s)':>8}")
    print("-"*80)
    for name, m in results.items():
        if 'error' in m:
            print(f"{name:<12}  ERROR: {m['error'][:40]}")
            continue
        marker = " ✓" if name == winner else "  "
        print(
            f"{name:<12}{marker}"
            f"{m.get('mae',0):>8.4f}"
            f"{m.get('rmse',0):>8.4f}"
            f"{m.get('mape_pct',0):>8.2f}"
            f"{m.get('smape_pct',0):>8.2f}"
            f"{m.get('coverage_90',0):>8.3f}"
            f"{m.get('train_time_s',0):>8.1f}"
        )
    print("="*80)
    print("\nPrimary: MAE  |  Co-primary: 90% PI Coverage (calibration)")
    print(f"Winner: {winner.upper()} — saved to results/forecasting_comparison.json")


if __name__ == '__main__':
    run()
