"""
Preprocessing pipeline for anomaly detection dataset.
Handles feature selection, encoding, scaling, and train/val/test splitting.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, set_seed

logger = get_logger(__name__)

# Features used for model input
NUMERICAL_FEATURES = [
    'log_activity',
    'log_co2e',
    'log_ef',
    'log_intensity',
    'log_co2e_check',
]
CATEGORICAL_FEATURES = [
    'category_id',
    'activity_unit',
    'data_quality',
    'region',
]
ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
TARGET       = 'is_anomaly'


class AnomalyPreprocessor:
    def __init__(self):
        self.scaler    = StandardScaler()
        self.encoders  = {c: LabelEncoder() for c in CATEGORICAL_FEATURES}
        self.fitted    = False

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        X_num = df[NUMERICAL_FEATURES].values.astype(np.float32)
        X_num = self.scaler.fit_transform(X_num)

        cat_parts = []
        for col in CATEGORICAL_FEATURES:
            enc = self.encoders[col]
            enc.fit(df[col])
            cat_parts.append(enc.transform(df[col]).reshape(-1, 1))

        X_cat = np.hstack(cat_parts).astype(np.float32)
        self.fitted = True
        return np.hstack([X_num, X_cat]).astype(np.float32)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        X_num = self.scaler.transform(df[NUMERICAL_FEATURES].values.astype(np.float32))
        cat_parts = []
        for col in CATEGORICAL_FEATURES:
            enc = self.encoders[col]
            vals = df[col].values
            # Handle unseen categories gracefully
            safe = np.array([
                enc.transform([v])[0] if v in enc.classes_ else 0 for v in vals
            ])
            cat_parts.append(safe.reshape(-1, 1))
        X_cat = np.hstack(cat_parts).astype(np.float32)
        return np.hstack([X_num, X_cat]).astype(np.float32)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({'scaler': self.scaler, 'encoders': self.encoders}, path)
        logger.info(f"Preprocessor saved → {path}")

    @classmethod
    def load(cls, path: str) -> 'AnomalyPreprocessor':
        obj = cls()
        data = joblib.load(path)
        obj.scaler   = data['scaler']
        obj.encoders = data['encoders']
        obj.fitted   = True
        return obj


def load_splits(data_path: str = 'data/processed/anomaly_dataset.csv',
                val_size: float = 0.15,
                test_size: float = 0.15,
                seed: int = 42) -> dict:
    """
    Load dataset and return stratified train/val/test splits.

    Stratified on is_anomaly to preserve the 7% anomaly rate in each split.
    Returns dict with keys: X_train, X_val, X_test, y_train, y_val, y_test,
                            preprocessor, anomaly_types_test
    """
    set_seed(seed)
    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df):,} records. Anomaly rate: {df[TARGET].mean():.3f}")

    # Stratified split
    df_train_val, df_test = train_test_split(
        df, test_size=test_size, stratify=df[TARGET], random_state=seed
    )
    val_frac = val_size / (1 - test_size)
    df_train, df_val = train_test_split(
        df_train_val, test_size=val_frac, stratify=df_train_val[TARGET], random_state=seed
    )

    logger.info(
        f"Split: train={len(df_train):,}  val={len(df_val):,}  test={len(df_test):,}"
    )

    prep   = AnomalyPreprocessor()
    X_train = prep.fit_transform(df_train)
    X_val   = prep.transform(df_val)
    X_test  = prep.transform(df_test)

    prep.save('saved_models/anomaly_preprocessor.pkl')

    return {
        'X_train':          X_train,
        'X_val':            X_val,
        'X_test':           X_test,
        'y_train':          df_train[TARGET].values.astype(np.int32),
        'y_val':            df_val[TARGET].values.astype(np.int32),
        'y_test':           df_test[TARGET].values.astype(np.int32),
        'anomaly_types_test': df_test['anomaly_type'].values,
        'n_features':       X_train.shape[1],
        'preprocessor':     prep,
    }
