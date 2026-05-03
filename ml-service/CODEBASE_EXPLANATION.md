# Scope 3 Emissions — ML Module: Codebase Explanation

> Comprehensive guide to the repository structure, data pipelines, model architectures, training procedures, and serving infrastructure.

---

## 1. Overview & Purpose

This repository implements **three deep-learning tasks** for Scope 3 emissions intelligence under the GHG Protocol:

| Task | Business Problem | Input → Output |
|---|---|---|
| **Anomaly Detection** | Flag suspicious emission submissions before they enter the ledger | Emission record → anomaly score + flag |
| **Emission Forecasting** | Predict next-quarter emissions for planning and target-setting | 12-month history → 3-month forecast + intervals |
| **Spend Estimation** | Estimate emissions from financial spend when activity data is missing | Spend (INR) + NIC sector + region → tCO₂e |

Each task trains **three competing models**, evaluates them with statistical rigor, selects a winner, and exposes a unified inference API.

**Key principle:** All data is synthetic but statistically realistic (derived from DEFRA 2024, IPCC AR6, BEE PAT, EDGAR, and RBI sources). Replacing with real data requires no code changes — only swapping CSV files.

---

## 2. Repository Structure

```
scope3-ml/
├── config.yaml                     # Central hyperparameters for all 9 models
├── run_all.py                      # Master pipeline: data → train → evaluate → test inference
├── utils.py                        # Shared utilities: seed, device, logging, JSON/YAML I/O
├── requirements.txt                # Python dependencies
│
├── data/
│   ├── generate_anomaly_data.py    # Synthetic anomaly dataset (7 real-world error types)
│   ├── fetch_forecast_data.py      # India monthly CO₂ downloader + synthetic fallback
│   ├── fetch_spend_data.py         # NIC-sector intensity table + regional/yearly adjustments
│   └── processed/                  # Generated CSVs, encoders, scalers
│
├── preprocessing/
│   ├── anomaly_prep.py             # Stratified splits + StandardScaler + LabelEncoder
│   ├── forecast_prep.py            # Strict temporal splits + MinMaxScaler + sequence builder
│   └── spend_prep.py               # Categorical embedding maps + flat-array converter
│
├── models/
│   ├── anomaly/
│   │   ├── isolation_forest.py     # sklearn baseline with small grid search
│   │   ├── autoencoder.py          # Symmetric encoder-decoder MLP (bottleneck=8)
│   │   └── vae.py                  # Variational Autoencoder (reconstruction-only score)
│   ├── forecasting/
│   │   ├── sarima_model.py         # Per-sector SARIMA(p,d,q)(P,D,Q)[12]
│   │   ├── lstm_model.py           # 2-layer LSTM + Monte Carlo Dropout intervals
│   │   └── tft_model.py            # Temporal Fusion Transformer (quantile attention)
│   └── spend/
│       ├── xgboost_model.py        # Gradient boosting with SHAP explanations
│       ├── mlp_embeddings.py       # Entity embeddings for NIC/region/year
│       └── tabnet_model.py         # Sequential attention-based tabular DL
│
├── train/
│   ├── train_anomaly.py            # Train 3 anomaly models, select winner (PR-AUC)
│   ├── train_forecasting.py        # Train 3 forecast models, select winner (MAE + coverage)
│   └── train_spend.py              # Train 3 spend models, select winner (R² + MAPE)
│
├── evaluation/
│   ├── metrics.py                  # Unified metrics: PR-AUC, MAE, R², Diebold-Mariano, DeLong
│   └── plots.py                    # Publication-quality matplotlib/seaborn visualisations
│
├── serving/
│   └── inference.py                # FastAPI-ready inference with lazy model loading
│
├── saved_models/                   # Best model per task + preprocessors
│   ├── anomaly/
│   ├── forecasting/
│   └── spend/
│
└── results/
    ├── *.json                      # Comparison tables per task
    └── plots/                      # All generated figures
```

---

## 3. Configuration (`config.yaml`)

A single YAML file drives all hyperparameters across the three tasks:

```yaml
paths:
  raw_data: data/raw
  processed_data: data/processed
  saved_models: saved_models
  results: results
  plots: results/plots

seed: 42

anomaly:
  dataset: { n_normal: 15000, anomaly_rate: 0.07, test_size: 0.15, val_size: 0.15 }
  isolation_forest: { n_estimators: 200, contamination: 0.07, max_samples: 256 }
  autoencoder: { hidden_dims: [64,32,16], bottleneck: 8, dropout: 0.1, lr: 0.001, ... }
  vae: { hidden_dims: [64,32], latent_dim: 8, beta: 1.0, lr: 0.001, ... }
  evaluation: { fpr_threshold: 0.10 }

forecasting:
  dataset: { seq_len: 12, horizon: 3, test_months: 24, val_months: 24 }
  sarima: { order: [2,1,1], seasonal_order: [1,1,0,12] }
  lstm: { hidden_size: 64, num_layers: 2, dropout: 0.2, mc_dropout_samples: 100 }
  tft: { hidden_size: 32, attention_head_size: 4, ... }

spend:
  dataset: { test_size: 0.15, val_size: 0.15, augmentation_factor: 5, noise_std: 0.15 }
  xgboost: { n_estimators: 500, max_depth: 6, learning_rate: 0.05, ... }
  mlp: { embed_dim_nic4: 16, embed_dim_nic2: 8, embed_dim_region: 4, embed_dim_year: 4, ... }
  tabnet: { n_d: 32, n_a: 32, n_steps: 5, gamma: 1.3, ... }
```

Every training script calls `load_config()` and extracts its relevant subtree. This makes experiments fully reproducible and hyperparameter sweeps trivial.

---

## 4. Shared Infrastructure

### 4.1 `utils.py`

| Function | Purpose |
|---|---|
| `set_seed(seed)` | Sets Python, NumPy, PyTorch, and CUDA seeds for reproducibility |
| `get_device()` | Returns `cuda` > `mps` > `cpu` automatically |
| `get_logger(name)` | Creates a consistently formatted `logging.Logger` |
| `load_config()` | Reads `config.yaml` into a Python dict |
| `save_json()` / `load_json()` | Safe JSON I/O with automatic directory creation |
| `ensure_dir()` | `mkdir -p` wrapper |

### 4.2 `run_all.py` — Master Pipeline

Runs the full workflow in sequence:

1. **Data Generation** — Calls each `data/` module to produce CSVs (skips if already present)
2. **Anomaly Training** — `train/train_anomaly.py`
3. **Forecasting Training** — `train/train_forecasting.py`
4. **Spend Training** — `train/train_spend.py`
5. **Final Summary** — Prints comparison tables for all three tasks
6. **Inference Test** — Runs `health_check()`, `predict_anomaly()`, `predict_spend()` to verify the serving layer

**Total runtime:** ~40 minutes on CPU, ~10 minutes on GPU.

### 4.3 `evaluation/metrics.py`

A unified metrics library returning plain Python dicts for JSON serialisation:

- **Anomaly:** `pr_auc` (primary), `roc_auc`, `f1` at FPR threshold, precision, recall
- **Forecasting:** `mae` (primary), `rmse`, `mape_pct`, `smape_pct`, `pi_coverage_90` (co-primary), directional accuracy
- **Regression (Spend):** `r2_log` (primary), `mae_log`, `rmse_log`, `mape_pct` (co-primary)

**Statistical tests:**
- `delong_auc_test()` — Bootstrap DeLong test for ROC-AUC difference significance
- `diebold_mariano_test()` — Harvey-Leybourne-Newbold corrected DM test for forecast accuracy
- `bootstrap_r2_ci()` — 95% bootstrap confidence interval on R²

### 4.4 `evaluation/plots.py`

Adapter-based plotting functions that accept the exact data structures produced by training scripts:

- `plot_pr_curves()` / `plot_roc_curves()` — Anomaly model overlays
- `plot_reconstruction_histograms()` — Normal vs anomaly score distributions
- `plot_training_curves()` — Loss curves for any neural model
- `plot_forecast_comparison()` — Actual vs predicted with prediction intervals
- `plot_regression_scatter()` — Predicted vs actual for spend models
- `plot_feature_importance()` — SHAP and TabNet attention side-by-side
- `plot_per_type_recall()` / `plot_per_sector_r2()` — Disaggregated performance

---

## 5. Task 1 — Anomaly Detection

### 5.1 Data Generation (`data/generate_anomaly_data.py`)

**Source:** Synthetic, based on DEFRA 2024 and IPCC AR6 valid ranges.

**Categories modelled:**
- 1 — Purchased Goods & Services (steel, aluminium)
- 3 — Fuel & Energy
- 4 — Upstream Transport
- 5 — Waste
- 6 — Business Travel
- 7 — Employee Commuting

**Seven anomaly types injected (7% of total):**

| # | Type | Mechanism |
|---|---|---|
| 1 | `unit_error_kg_vs_tonne` | Activity entered in kg instead of tonnes (1000×) |
| 2 | `unit_error_km_vs_tonne_km` | Distance only, missing weight factor |
| 3 | `magnitude_spike` | Activity 100–1000× normal |
| 4 | `magnitude_underflow` | Activity 0.001× normal (decimal error) |
| 5 | `wrong_ef_applied` | EF from a different category |
| 6 | `copy_paste_duplicate` | Suspiciously round repeated value |
| 7 | `ef_unit_mismatch` | Activity in litres, EF expects kWh (~10× off) |

**Feature engineering:**
- `log_activity`, `log_co2e`, `log_ef` — Log-transform skewed numerics
- `log_intensity` — `co2e / activity`, the key anomaly signal
- `co2e_check_ratio` — `calculated_co2e / (activity × ef / 1000)`, should be ~1.0

### 5.2 Preprocessing (`preprocessing/anomaly_prep.py`)

- **Stratified split** on `is_anomaly` to preserve 7% rate in train/val/test
- `StandardScaler` on 5 numerical features
- `LabelEncoder` on 4 categorical features (`category_id`, `activity_unit`, `data_quality`, `region`)
- Saved to `saved_models/anomaly_preprocessor.pkl` for inference

### 5.3 Models (`models/anomaly/`)

#### Isolation Forest
- Unsupervised tree ensemble from sklearn
- Small grid search over `n_estimators` and `max_samples`
- `contamination=0.07` matches dataset anomaly rate
- Anomaly score = `-decision_function()` (higher = more anomalous)

#### Autoencoder
- Symmetric MLP: `input → 64 → 32 → 16 → bottleneck(8) → 16 → 32 → 64 → input`
- BatchNorm + ReLU + Dropout(0.1) on all hidden layers
- Loss: MSE reconstruction
- Early stopping on validation PR-AUC (not loss)
- **Anomaly score:** per-sample MSE reconstruction error

#### VAE
- Encoder: `input → 64 → 32 → [mu(8), log_var(8)]`
- Reparameterisation trick during training; deterministic `mu` at inference
- Loss: `MSE_recon + β·KL(q(z|x) || N(0,I))`
- **Critical design decision:** Anomaly score uses **reconstruction error only**, not ELBO. The KL term adds noise (1.20× separation) compared to reconstruction (3.30× separation). This is consistent with Xu et al. 2018 and OmniAnomaly literature.

### 5.4 Training (`train/train_anomaly.py`)

1. Load stratified splits
2. Train IF → AE → VAE sequentially
3. Compute PR-AUC, ROC-AUC, F1@10%FPR, precision@K for each
4. **DeLong test** on top-2 models for statistical significance
5. **Winner selection:** Primary = PR-AUC; tiebreak = precision@10% recall
6. Save `best_model.json` (winner + reason + threshold), `anomaly_comparison.json`, and 5 plots

**Expected winner:** Autoencoder (PR-AUC ~0.72 vs IF ~0.60 vs VAE ~0.35 on synthetic data).

---

## 6. Task 2 — Emission Forecasting

### 6.1 Data Fetching (`data/fetch_forecast_data.py`)

**Primary source:** Robbie Andrew India GHG monthly series (`india_co2_emissions_data.csv`)
- Automatic download via `requests`
- Flexible column name parsing for multiple CSV versions

**Fallback:** Synthetic disaggregation from EDGAR annual totals
- 4 sectors: oil, coal, gas, cement
- India annual CO₂ 1990–2023 (Mt)
- Seasonal profiles per sector (monthly fraction of annual)

**Features added:**
- `month_sin`, `month_cos` — cyclical encoding (avoids Dec/Jan discontinuity)
- `year_norm` — normalised year [0,1]
- `sector_id` — integer code for embedding
- `category_id` — Scope 3 category mapping

**Sequence builder:** `build_sequence_dataset()`
- `X` shape: `(n_samples, seq_len=12, n_features=4)`
- `y` shape: `(n_samples, horizon=3)`
- Per-sector `MinMaxScaler` saved for inverse transform

### 6.2 Preprocessing (`preprocessing/forecast_prep.py`)

**Strict temporal split** — a sequence belongs to the split where its *target* falls, not its input window:

```
Train targets:  months 0 .. val_start-1
Val targets:    months val_start .. test_start-1
Test targets:   months test_start .. T-1
```

This is the correct rolling evaluation protocol. Input windows can overlap period boundaries.

### 6.3 Models (`models/forecasting/`)

#### SARIMA
- Per-sector `SARIMAX(p,d,q)(P,D,Q)[12]` from statsmodels
- Default order: `(2,1,1)(1,1,0,12)`
- Generates point forecast + 90% confidence interval via `get_forecast()`

#### LSTM
- 2-layer LSTM: `hidden_size=64`, `dropout=0.2`, `batch_first=True`
- Takes last timestep → Dense(16, ReLU) → Dense(horizon=3)
- Loss: Huber loss (robust to outliers)
- **Prediction intervals:** Monte Carlo Dropout — 100 forward passes with dropout active → mean ± 1.645·std for 90% PI

#### TFT
- Temporal Fusion Transformer from `pytorch-forecasting`
- Variable selection attention + interpretable multi-horizon attention
- Quantile outputs: [0.05, 0.25, 0.5, 0.75, 0.95]
- Optional — gracefully skipped if library not installed

### 6.4 Training (`train/train_forecasting.py`)

1. Load temporal splits and sequence arrays
2. Train SARIMA → LSTM → TFT (if available)
3. Compute MAE, MAPE, RMSE, sMAPE, directional accuracy, 90% PI coverage
4. **Diebold-Mariano test** between LSTM and TFT
5. **Winner selection:** Primary = MAE; disqualify if `coverage_90 < 0.70`; penalty = `max(0, 0.70 - coverage) × 100`
6. Save `best_model.json`, `forecasting_comparison.json`, and comparison plot

**Expected winner:** LSTM (lower MAE, better calibration than SARIMA; TFT optional).

---

## 7. Task 3 — Spend Estimation

### 7.1 Data Construction (`data/fetch_spend_data.py`)

**Source:** Synthetic fallback based on:
- BEE PAT scheme benchmarks
- DEFRA 2024 sector averages (EUR→INR converted)
- TERI India sector reports

**NIC 2008 structure:** 110 sectors at 4-digit level, grouped into 2-digit divisions.

**Per-record formula:**
```
intensity = base_intensity × (1 + INTENSITY_TREND)^(year - base_year) × REGION_ADJUSTMENT[region]
```

- `INTENSITY_TREND = -0.022` (2.2% annual improvement, IEA India data)
- `REGION_ADJUSTMENTS`: north 1.08, south 0.94, east 1.15, west 0.98, central 1.05
- `USD_INR` from RBI annual averages

**Augmentation:** 5 perturbed copies per base row with lognormal noise (`noise_std=0.15`) to simulate enterprise-level variability.

**Target:** `log_intensity` (log of tCO₂e per ₹ lakh) — log scale stabilises variance and handles heavy-tailed sector intensities (steel 1.89 vs software 0.012).

### 7.2 Preprocessing (`preprocessing/spend_prep.py`)

- **Stratified split** on `nic_2digit` to ensure all sector groups appear in every split
- `SpendPreprocessor`:
  - `fit_transform()` → dict of `{feature: encoded_array}` for each categorical + `numerical` array
  - `to_flat_array()` → concatenates all features into a single float array for XGBoost/TabNet
- Saved to `saved_models/spend_preprocessor.pkl`

**Encoder maps** (`spend_encoders.json`) map raw values (NIC codes, region strings, years) to integer indices for embedding layers.

### 7.3 Models (`models/spend/`)

#### XGBoost
- Gradient boosting: `n_estimators=500`, `max_depth=6`, `learning_rate=0.05`
- L1/L2 regularisation (`reg_alpha=0.1`, `reg_lambda=1.0`)
- SHAP values computed on 500-sample test subset for feature importance

#### MLP + Entity Embeddings
- Entity embeddings per categorical variable:
  - NIC-4: 16-dim, NIC-2: 8-dim, region: 4-dim, year: 4-dim
- Embeddings capture semantic similarity between industries (e.g., steel vs aluminium both high-intensity)
- MLP head: `embedding_concat → 128 → 64 → 32 → 1`
- Reference: Guo & Berkhahn (2016) "Entity Embeddings of Categorical Variables"

#### TabNet
- Sequential attention: `n_d=32`, `n_a=32`, `n_steps=5`, `gamma=1.3`
- Sparsemax produces interpretable feature masks per decision step
- `num_workers=0` by default (avoids hangs on some systems)

### 7.4 Training (`train/train_spend.py`)

1. Load stratified splits
2. **Naive EEIO baseline** — sector median lookup (the current non-ML platform method)
3. Train XGBoost → MLP+Embeddings → TabNet
4. Compute R²(log), MAE(log), RMSE(log), MAPE(original scale)
5. **Bootstrap 95% CI** on R² for top models
6. **Winner selection:** Primary = R²(log); must beat naive baseline by >5% MAPE; otherwise fall back to naive
7. Save `best_model.json`, `spend_comparison.json`, SHAP importance, and 4 plots

**Expected winner:** MLP+Embeddings (R² ~0.99, MAPE ~13.3%, beating naive by ~15%).

---

## 8. Model Serving (`serving/inference.py`)

A FastAPI-ready inference module with **lazy loading** — models are loaded on first call, not at import time.

### 8.1 Architecture

```python
# Global registry (initially None)
_anomaly_model = None
_forecast_models = None
_spend_model = None
```

Each `_load_*()` function:
1. Reads `saved_models/<task>/best_model.json` to discover the winner
2. Imports the correct model module dynamically
3. Loads weights + preprocessor
4. Caches in global variable

### 8.2 Public API

#### `predict_anomaly(record: dict) → dict`

**Input fields:** `category_id`, `activity_value`, `activity_unit`, `ef_value`, `calculated_co2e`, `data_quality`, `region`

**Output:**
```json
{
  "anomaly_score": 0.8234,
  "is_flagged": true,
  "confidence": "high",
  "explanation": "Activity value unusually large for category 1 — possible kg/tonne unit error",
  "model_used": "autoencoder"
}
```

**Explanation heuristics:** Checks intensity limits per category, unit mismatches, and magnitude spikes.

#### `predict_forecast(sector: str, history: list[float]) → dict`

**Input:** Sector name + last 12 monthly values (raw, not scaled)

**Output:**
```json
{
  "forecast": [312.5, 308.2, 320.1],
  "lower_90": [298.4, 291.0, 305.8],
  "upper_90": [326.6, 325.4, 334.4],
  "model_used": "lstm"
}
```

- SARIMA: re-fits on provided history and forecasts
- LSTM: scales input, runs MC Dropout, inverse-transforms output

#### `predict_spend(spend_inr, nic_4digit, region, year) → dict`

**Output:**
```json
{
  "estimated_co2e": 47.3,
  "intensity_t_per_lakh_inr": 0.9456,
  "confidence_band": [37.8, 56.7],
  "data_quality": "C",
  "methodology": "Spend-based estimation using mlp_embeddings model...",
  "model_used": "mlp_embeddings"
}
```

Uncertainty: ±20% fixed band (typical spend-based estimation error per GHG Protocol).

### 8.3 Health Check

```python
health_check() → {'anomaly': 'ready', 'forecasting': 'ready', 'spend': 'ready'}
```

Returns `'not_trained'` if models haven't been trained yet, or `'error: ...'` on load failure.

---

## 9. Running the Pipeline

### Full Pipeline
```bash
cd scope3-ml
pip install -r requirements.txt
python run_all.py
```

### Individual Tasks
```bash
python train/train_anomaly.py      # ~10 min CPU
python train/train_forecasting.py  # ~20 min CPU
python train/train_spend.py        # ~10 min CPU
```

### Inference Test
```bash
python serving/inference.py
```

---

## 10. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Reconstruction-only VAE score** | KL term adds noise (1.20× separation) vs reconstruction (3.30×). Literature supports this (Xu et al. 2018). |
| **Strict temporal forecast splits** | Sequence assigned by target position, not input window. Correct rolling evaluation; prevents data leakage. |
| **Entity embeddings for NIC codes** | Captures semantic similarity between industries. MLP beats XGBoost by ~8% MAPE due to learned representations. |
| **MC Dropout for LSTM intervals** | Cheap uncertainty quantification without ensembling. 100 passes → mean ± 1.645·std for 90% PI. |
| **Stratified splits** | Anomaly: stratify on `is_anomaly` (7% rate). Spend: stratify on `nic_2digit` (sector group). Ensures representation. |
| **Log-scale target for spend** | Intensities span 3 orders of magnitude (0.006 to 6.7). Log transform stabilises variance and improves R². |
| **Naive EEIO baseline as floor** | Any ML model must beat sector-median lookup by >5% MAPE. Prevents overfitting to synthetic data. |
| **Centralised config.yaml** | Single source of truth for all hyperparameters. Easy to version-control and sweep. |
| **Lazy inference loading** | Models loaded on first prediction, not at server startup. Reduces cold-start memory if not all tasks are used. |
| **Synthetic data with realistic distributions** | Derived from peer-reviewed sources (DEFRA, IPCC, BEE, EDGAR, RBI). Can be swapped for real data without code changes. |

---

## 11. Output Artifacts

After running the full pipeline, the following are produced:

```
saved_models/
  anomaly_preprocessor.pkl
  forecast_scalers.pkl
  spend_preprocessor.pkl
  anomaly/
    isolation_forest.pkl, autoencoder.pt, vae.pt, best_model.json
  forecasting/
    sarima.pkl, lstm.pt, tft.pt, best_model.json
  spend/
    xgboost.pkl, mlp_embeddings.pt, tabnet/, best_model.json

results/
  anomaly_comparison.json
  forecasting_comparison.json
  spend_comparison.json
  plots/
    anomaly_pr_curves.png, anomaly_roc_curves.png, anomaly_reconstruction_errors.png,
    anomaly_per_type_recall.png, anomaly_training_curves.png,
    forecast_comparison.png, forecast_lstm_training.png,
    spend_scatter.png, spend_feature_importance.png, spend_per_sector_r2.png, spend_training_curves.png
```

These artifacts are fully self-contained and can be deployed directly to the inference service.

