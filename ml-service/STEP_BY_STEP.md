# Step-by-Step Run Guide (Windows)

## 1. Install dependencies

```cmd
cd scope3-ml
pip install -r requirements.txt
```

If pytorch-tabnet fails:
```cmd
pip install pytorch-tabnet==4.1.0
```

If TFT not needed (saves install time):
Comment out the TFT block in `train/train_forecasting.py` — SARIMA and LSTM will still run.

---

## 2. Generate all datasets

```cmd
python data/generate_anomaly_data.py
python data/fetch_forecast_data.py
python data/fetch_spend_data.py
```

Each takes < 30 seconds. Creates files in `data/processed/`.

---

## 3. Train each task

```cmd
python train/train_anomaly.py
python train/train_forecasting.py
python train/train_spend.py
```

Or all at once:
```cmd
python run_all.py
```

---

## 4. What to expect

After training:
- `results/plots/` — 9 comparison plots (PR curves, scatter plots, training curves)
- `results/anomaly_comparison.json` — metrics table for all 3 anomaly models
- `results/forecasting_comparison.json` — metrics for SARIMA/LSTM/TFT
- `results/spend_comparison.json` — metrics for XGBoost/MLP/TabNet
- `saved_models/*/best_model.json` — which model won and why

---

## 5. If TabNet hangs

TabNet can hang on Windows due to multiprocessing. Fix already applied (`num_workers=0`).
If it still hangs, skip TabNet by editing `train/train_spend.py`:

```python
# Comment out the TabNet section (lines starting with "## 5. TabNet")
# The script will still compare XGBoost vs MLP+Embeddings vs Naive EEIO
```

---

## 6. Viewing results

Open any JSON in `results/` to see the comparison table.
Open any PNG in `results/plots/` for visual comparison.

The `best_model.json` files in `saved_models/` tell you exactly which model
won, why, and where the saved file is.

---

## 7. TFT (optional)

TFT requires pytorch-forecasting:
```cmd
pip install pytorch-forecasting lightning
```

If install fails, SARIMA and LSTM still run and compare.
TFT results will show `error` in the comparison table if not installed.
