# Scope 3 Emissions — ML Module

Three DL-based models for Scope 3 emissions intelligence:
- **Anomaly Detection**: Isolation Forest vs Autoencoder vs VAE
- **Emission Forecasting**: SARIMA vs LSTM vs TFT
- **Spend Estimation**: XGBoost vs MLP+Embeddings vs TabNet

---

## Setup

```bash
cd scope3-ml
pip install -r requirements.txt
```

Minimum Python: 3.10. GPU optional (CPU works fine for all models).

---

## Run Everything

```bash
python run_all.py
```

This runs in sequence:
1. Data generation/download (~2 min)
2. Anomaly training — all 3 models (~10 min CPU)
3. Forecasting training — SARIMA + LSTM + TFT (~20 min CPU)
4. Spend estimation — XGBoost + MLP + TabNet (~10 min CPU)
5. Prints comparison tables + saves plots

**Total: ~40 minutes on CPU. ~10 minutes with GPU.**

---

## Run Individual Tasks

```bash
python train/train_anomaly.py      # Task 1 only
python train/train_forecasting.py  # Task 2 only  
python train/train_spend.py        # Task 3 only
```

---

## Expected Results (approximate, CPU, full epochs)

### Task 1 — Anomaly Detection
```
Model                PR-AUC   ROC-AUC    F1@FPR   Time(s)
────────────────────────────────────────────────────────
Isolation Forest     0.60     0.85       0.44      30
Autoencoder          0.72     0.91       0.51      120
VAE                  0.35     0.75       0.30      150
Winner: Autoencoder
```

### Task 2 — Emission Forecasting
```
Model         MAE      MAPE%   Cover90   Time(s)
──────────────────────────────────────────────────
SARIMA        2.40     6.28    0.67      180
LSTM          0.08     9.24    0.72      300
TFT           —        —       —         600 (optional)
Winner: LSTM (lower MAE, better calibration)
```

### Task 3 — Spend Estimation
```
Model                R²(log)   MAPE%    MAE(log)   Time(s)
────────────────────────────────────────────────────────────
Naive EEIO baseline  0.85      28.0     —           0
XGBoost              0.97      21.1     0.21        30
MLP+Embeddings       0.99      13.3     0.13        200
TabNet               0.96      22.0     0.24        600
Winner: MLP+Embeddings (highest R², lowest MAPE, beats naive by 15%)
```

---

## Output Files

```
saved_models/
  anomaly/
    isolation_forest.pkl   — sklearn IsolationForest
    autoencoder.pt         — PyTorch Autoencoder state dict
    vae.pt                 — PyTorch VAE state dict
    best_model.json        — winner + reason + threshold
  forecasting/
    sarima.pkl             — per-sector fitted SARIMA models
    lstm.pt                — PyTorch LSTM state dict
    tft.pt                 — TFT model (if pytorch-forecasting installed)
    best_model.json        — winner
  spend/
    xgboost.pkl            — XGBoost model
    mlp_embeddings.pt      — PyTorch MLP state dict
    tabnet/                — TabNet model files
    best_model.json        — winner

results/
  anomaly_comparison.json
  forecasting_comparison.json
  spend_comparison.json
  plots/
    anomaly_pr_curves.png
    anomaly_roc_curves.png
    anomaly_reconstruction_errors.png
    anomaly_per_type_recall.png
    anomaly_training_curves.png
    forecast_comparison.png
    spend_scatter.png
    spend_feature_importance.png
    spend_per_sector_r2.png
```

---

## Use in Platform (FastAPI)

```python
from ml.serving.inference import predict_anomaly, predict_forecast, predict_spend

# Flag suspicious emission record
result = predict_anomaly({
    'category_id': 1, 'activity_value': 500.0,
    'activity_unit': 0, 'ef_value': 1890.0,
    'calculated_co2e': 0.945, 'data_quality': 0, 'region': 0
})
# → {'anomaly_score': 0.12, 'is_flagged': False, 'confidence': 'high', ...}

# Forecast next 3 months
result = predict_forecast('oil', history=[300, 310, 295, ...])
# → {'forecast': [312, 308, 320], 'lower_90': [...], 'upper_90': [...]}

# Estimate emissions from spend
result = predict_spend(spend_inr=5_000_000, nic_4digit=2410,
                       region='north', year=2023)
# → {'estimated_co2e': 47.3, 'intensity_t_per_lakh_inr': 0.9456, ...}
```

---

## Model Architecture Notes

### Autoencoder (Anomaly Detection winner)
- Symmetric encoder-decoder MLP
- Bottleneck dimension 8 — forces compression of normal patterns
- Anomaly score = per-sample MSE reconstruction error
- Trained only on the joint distribution — anomalies cause high reconstruction error
- Training: ~100 epochs, early stopping on val PR-AUC

### VAE
- Same architecture + reparameterisation trick
- Anomaly score = reconstruction loss + KL(q||p)
- Learns probabilistic latent space — should generalise better with more data
- Currently underperforms Autoencoder on synthetic data (early stopping)

### LSTM (Forecasting winner)
- 2-layer LSTM, hidden size 64
- Multi-step direct forecast (outputs 3 months simultaneously)
- Prediction intervals via Monte Carlo Dropout (100 forward passes, dropout active)
- Trained on India sector CO2 series 1990-2023 (408 months × 4 sectors)

### MLP+Embeddings (Spend Estimation winner)
- Entity embeddings for NIC-4 (16-dim), NIC-2 (8-dim), region (4-dim), year (4-dim)
- Embeddings capture semantic similarity between industries
- Reference: Guo & Berkhahn (2016) "Entity Embeddings of Categorical Variables"
- Outperforms XGBoost by ~8% MAPE due to learned industry representations

### TabNet
- Sequential attention masks select relevant features per decision step
- Sparsemax activation produces sparse (interpretable) feature selection
- If hangs: set `num_workers=0` (already default in this code)

---

## Data Sources

| Task | Source | Type |
|---|---|---|
| Anomaly | Synthetic (DEFRA/IPCC valid ranges) | Generated |
| Forecasting | India CO2 monthly 1990-2023 (annual disaggregation) | Synthetic from literature |
| Spend | 110 NIC sectors × 14 years × 5 regions (BEE/DEFRA intensities) | Synthetic from literature |

Real data can replace synthetic without code changes — just swap the CSV files.
For forecasting, replace with Robbie Andrew dataset when available.
For spend, replace with EXIOBASE 3.8.2 via `pymrio` (see `data/fetch_spend_data.py`).
