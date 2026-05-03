"""
Preprocessing pipeline for spend-based emission estimation.
Handles label encoding for categorical features (NIC codes, region, year).
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, set_seed

logger = get_logger(__name__)

CATEGORICAL_FEATURES = ['nic_4digit', 'nic_2digit', 'region', 'year']
NUMERICAL_FEATURES   = ['inr_usd']   # exchange rate as a numeric context feature
TARGET               = 'log_intensity'
TARGET_ORIG          = 'intensity_kg_co2e_per_inr_lakh'


class SpendPreprocessor:
    def __init__(self):
        self.cat_maps  = {}   # feature → {value: int_code}
        self.n_classes = {}   # feature → num unique values
        self.num_scaler = StandardScaler()
        self.fitted = False

    def fit_transform(self, df: pd.DataFrame) -> dict:
        """Returns dict with separate arrays for categorical and numerical."""
        # Encode categoricals
        cat_arrays = {}
        for col in CATEGORICAL_FEATURES:
            vals = sorted(df[col].unique().tolist())
            self.cat_maps[col]  = {v: i for i, v in enumerate(vals)}
            self.n_classes[col] = len(vals)
            cat_arrays[col] = df[col].map(self.cat_maps[col]).values.astype(np.int64)

        # Scale numericals
        num_arr = self.num_scaler.fit_transform(
            df[NUMERICAL_FEATURES].values.astype(np.float32)
        )

        self.fitted = True
        return {**cat_arrays, 'numerical': num_arr.astype(np.float32)}

    def transform(self, df: pd.DataFrame) -> dict:
        cat_arrays = {}
        for col in CATEGORICAL_FEATURES:
            cat_arrays[col] = np.array([
                self.cat_maps[col].get(v, 0) for v in df[col].values
            ], dtype=np.int64)
        num_arr = self.num_scaler.transform(
            df[NUMERICAL_FEATURES].values.astype(np.float32)
        )
        return {**cat_arrays, 'numerical': num_arr.astype(np.float32)}

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'cat_maps':   self.cat_maps,
            'n_classes':  self.n_classes,
            'num_scaler': self.num_scaler,
        }, path)
        logger.info(f"SpendPreprocessor saved → {path}")

    @classmethod
    def load(cls, path: str) -> 'SpendPreprocessor':
        obj = cls()
        data = joblib.load(path)
        obj.cat_maps   = data['cat_maps']
        obj.n_classes  = data['n_classes']
        obj.num_scaler = data['num_scaler']
        obj.fitted = True
        return obj

    def to_flat_array(self, enc_dict: dict) -> np.ndarray:
        """Concatenate all encoded features into a flat float array for XGBoost/TabNet."""
        parts = []
        for col in CATEGORICAL_FEATURES:
            parts.append(enc_dict[col].reshape(-1, 1).astype(np.float32))
        parts.append(enc_dict['numerical'])
        return np.hstack(parts)


def load_splits(data_path: str = 'data/processed/spend_dataset.csv',
                val_size: float = 0.15,
                test_size: float = 0.15,
                seed: int = 42) -> dict:
    set_seed(seed)
    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df):,} rows. Target (log_intensity) stats:")
    logger.info(df[TARGET].describe().round(4).to_string())

    # Stratified by nic_2digit group to ensure all sector groups in each split
    df_tv, df_test = train_test_split(
        df, test_size=test_size, stratify=df['nic_2digit'], random_state=seed
    )
    val_frac = val_size / (1 - test_size)
    df_train, df_val = train_test_split(
        df_tv, test_size=val_frac, stratify=df_tv['nic_2digit'], random_state=seed
    )

    logger.info(
        f"Split: train={len(df_train):,}  val={len(df_val):,}  test={len(df_test):,}"
    )

    prep      = SpendPreprocessor()
    enc_train = prep.fit_transform(df_train)
    enc_val   = prep.transform(df_val)
    enc_test  = prep.transform(df_test)
    prep.save('saved_models/spend_preprocessor.pkl')

    # Flat arrays for XGBoost and TabNet
    X_flat_train = prep.to_flat_array(enc_train)
    X_flat_val   = prep.to_flat_array(enc_val)
    X_flat_test  = prep.to_flat_array(enc_test)

    return {
        # Encoded dicts for MLP (uses embedding layers)
        'enc_train': enc_train,
        'enc_val':   enc_val,
        'enc_test':  enc_test,
        # Flat arrays for XGBoost / TabNet
        'X_train': X_flat_train,
        'X_val':   X_flat_val,
        'X_test':  X_flat_test,
        # Targets
        'y_train': df_train[TARGET].values.astype(np.float32),
        'y_val':   df_val[TARGET].values.astype(np.float32),
        'y_test':  df_test[TARGET].values.astype(np.float32),
        # Original scale targets (for MAPE evaluation)
        'y_train_orig': df_train[TARGET_ORIG].values.astype(np.float32),
        'y_val_orig':   df_val[TARGET_ORIG].values.astype(np.float32),
        'y_test_orig':  df_test[TARGET_ORIG].values.astype(np.float32),
        # Sector labels for per-group evaluation
        'sector_groups_test': df_test['nic_2digit'].values,
        'sector_names_test':  df_test['sector_name'].values,
        # Metadata
        'n_classes':    prep.n_classes,
        'n_numerical':  len(NUMERICAL_FEATURES),
        'n_flat_features': X_flat_train.shape[1],
        'preprocessor': prep,
        'df_test':      df_test,
    }
