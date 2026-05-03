"""
Preprocessing pipeline for emission forecasting.
Strict temporal train/val/test split — input window can overlap period boundary,
but target values must fall in the correct split period.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import joblib
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger

logger = get_logger(__name__)

SEQ_LEN  = 12
HORIZON  = 3


def load_splits(data_path: str = 'data/processed/forecast_dataset.csv',
                test_months:  int = 24,
                val_months:   int = 24,
                seq_len:      int = SEQ_LEN,
                horizon:      int = HORIZON,
                seed:         int = 42) -> dict:
    """
    Build per-sector sequences with a strict temporal split.

    A sequence belongs to a split based on where its TARGET falls,
    not where its input window starts. This means input windows can
    use data from the preceding period — this is correct rolling
    evaluation protocol.

    Train targets: months 0 .. val_start-1
    Val targets:   months val_start .. test_start-1
    Test targets:  months test_start .. T-1
    """
    df = pd.read_csv(data_path, parse_dates=['date'])
    sectors = df['sector'].unique().tolist()
    logger.info(
        f"Sectors: {sectors}  |  "
        f"Date range: {df['date'].min().date()} → {df['date'].max().date()}"
    )

    all_train_X, all_train_y = [], []
    all_val_X,   all_val_y   = [], []
    all_test_X,  all_test_y  = [], []

    sector_data = {}
    scalers     = {}

    for sector in sectors:
        sub = df[df['sector'] == sector].sort_values('date').reset_index(drop=True)
        T   = len(sub)

        scaler     = MinMaxScaler()
        co2_scaled = scaler.fit_transform(sub[['co2_mt']]).flatten().astype(np.float32)
        scalers[sector] = scaler

        features = np.column_stack([
            co2_scaled,
            sub['month_sin'].values,
            sub['month_cos'].values,
            sub['year_norm'].values,
        ]).astype(np.float32)

        # Period boundaries (index of first month in each split)
        test_start = T - test_months
        val_start  = test_start - val_months

        logger.info(
            f"  {sector}: T={T}  val_start={val_start}  "
            f"test_start={test_start}  "
            f"(train={val_start}, val={test_start-val_start}, test={T-test_start} months)"
        )

        # Build ALL sequences over the full series.
        # Assign each sequence to the split where its TARGET starts.
        for i in range(seq_len, T - horizon + 1):
            target_start = i                   # first target index
            x_seq  = features[i - seq_len:i]   # (seq_len, 4)
            y_seq  = co2_scaled[i:i + horizon] # (horizon,)

            if target_start < val_start:
                all_train_X.append(x_seq); all_train_y.append(y_seq)
            elif target_start < test_start:
                all_val_X.append(x_seq);   all_val_y.append(y_seq)
            else:
                all_test_X.append(x_seq);  all_test_y.append(y_seq)

        # Store raw series for SARIMA (uses its own evaluation)
        sector_data[sector] = {
            'raw':        sub['co2_mt'].values.astype(np.float64),
            'scaled':     co2_scaled,
            'dates':      sub['date'].values,
            'scaler':     scaler,
            'val_start':  val_start,
            'test_start': test_start,
        }

    def _stack(lst):
        return np.array(lst, dtype=np.float32) if lst else np.empty((0,), dtype=np.float32)

    Path('saved_models').mkdir(parents=True, exist_ok=True)
    joblib.dump(scalers, 'saved_models/forecast_scalers.pkl')

    result = {
        'X_train': _stack(all_train_X),
        'y_train': _stack(all_train_y),
        'X_val':   _stack(all_val_X),
        'y_val':   _stack(all_val_y),
        'X_test':  _stack(all_test_X),
        'y_test':  _stack(all_test_y),
        'sector_data': sector_data,
        'scalers':     scalers,
        'seq_len':     seq_len,
        'horizon':     horizon,
        'n_features':  4,
        'sectors':     sectors,
    }

    for split in ('train', 'val', 'test'):
        x = result[f'X_{split}']
        y = result[f'y_{split}']
        shape_x = x.shape if x.ndim > 1 else (len(x),)
        shape_y = y.shape if y.ndim > 1 else (len(y),)
        logger.info(f"  {split:5s}: X={shape_x}  y={shape_y}")

    return result
