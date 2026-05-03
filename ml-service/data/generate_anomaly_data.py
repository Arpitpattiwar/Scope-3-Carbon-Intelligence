"""
Generate synthetic Scope 3 emission records for anomaly detection training.

Normal records are sampled from realistic distributions derived from
DEFRA 2024 and IPCC AR6 emission factor ranges.

Anomaly types injected (7 types matching real-world submission errors):
  1. unit_error_kg_vs_tonne     — vendor enters kg instead of tonnes (1000x)
  2. unit_error_km_vs_tonne_km  — distance only, missing weight factor
  3. magnitude_spike            — 100-1000x normal activity value
  4. magnitude_underflow        — 0.001x normal (decimal point error)
  5. wrong_ef_applied           — EF from a different category used
  6. copy_paste_duplicate       — suspiciously round repeated value
  7. ef_unit_mismatch           — activity in litres, EF expects kWh

Output: data/processed/anomaly_dataset.csv  (~16,000 rows)
"""

import numpy as np
import pandas as pd
from scipy.stats import lognorm
from pathlib import Path
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, set_seed, load_config

logger = get_logger(__name__)

# ── Ground-truth valid ranges from DEFRA 2024 / IPCC AR6 ─────────────────────
# ef_range:        (min, max) kgCO2e per activity unit
# activity_range:  realistic (min, max) for a single quarterly submission
# intensity_range: valid tCO2e / activity_value range (used as anomaly check)

CATEGORY_PROFILES = {
    1: {   # Purchased Goods & Services
        'name':            'Purchased Goods',
        'ef_range':        (400.0,  6700.0),   # steel 1890 to aluminium 6700
        'activity_range':  (5.0,    8000.0),   # tonnes
        'unit_code':       0,                  # tonne
        'intensity_range': (0.05,   9.0),      # tCO2e/tonne
    },
    4: {   # Upstream Transport
        'name':            'Upstream Transport',
        'ef_range':        (0.016,  1.17),     # sea 0.016 to air 1.17 kgCO2e/tonne-km
        'activity_range':  (500.0,  800000.0), # tonne-km
        'unit_code':       1,                  # tonne-km
        'intensity_range': (1e-5,   2e-3),     # tCO2e/tonne-km
    },
    5: {   # Waste
        'name':            'Waste',
        'ef_range':        (21.0,   467.0),    # recycled 21 to landfill 467 kgCO2e/tonne
        'activity_range':  (0.5,    800.0),    # tonnes
        'unit_code':       0,                  # tonne
        'intensity_range': (0.01,   0.55),
    },
    6: {   # Business Travel
        'name':            'Business Travel',
        'ef_range':        (0.041,  0.255),    # rail 0.041 to domestic air 0.255 kgCO2e/pass-km
        'activity_range':  (200.0,  400000.0), # passenger-km
        'unit_code':       2,                  # passenger-km
        'intensity_range': (3e-5,   3e-4),
    },
    7: {   # Employee Commuting
        'name':            'Employee Commuting',
        'ef_range':        (0.031,  0.192),    # metro 0.031 to petrol car 0.192 kgCO2e/pass-km
        'activity_range':  (1000.0, 1500000.0),
        'unit_code':       2,
        'intensity_range': (2e-5,   2.5e-4),
    },
    3: {   # Fuel & Energy
        'name':            'Fuel & Energy',
        'ef_range':        (0.4,    2.5),      # kgCO2e/kWh or kgCO2e/litre
        'activity_range':  (100.0,  500000.0), # kWh
        'unit_code':       3,                  # kWh
        'intensity_range': (1e-4,   3e-3),
    },
}

UNIT_NAMES = {0: 'tonne', 1: 'tonne-km', 2: 'passenger-km', 3: 'kWh',
              4: 'litre', 5: 'INR', 6: 'kg', 7: 'km'}

ANOMALY_TYPES = [
    'unit_error_kg_vs_tonne',
    'unit_error_km_vs_tonne_km',
    'magnitude_spike',
    'magnitude_underflow',
    'wrong_ef_applied',
    'copy_paste_duplicate',
    'ef_unit_mismatch',
]

REGIONS      = [0, 1, 2, 3, 4]          # north/south/east/west/central
QUALITY_DIST = [0.30, 0.50, 0.20]       # A / B / C
CATEGORIES   = list(CATEGORY_PROFILES.keys())


# ── Record generators ─────────────────────────────────────────────────────────

def _normal_record(cat: int, rng: np.random.Generator) -> dict:
    cfg   = CATEGORY_PROFILES[cat]
    ef    = rng.uniform(*cfg['ef_range'])
    # Lognormal: most submissions are small, a few are large
    mu    = np.log(np.sqrt(cfg['activity_range'][0] * cfg['activity_range'][1]))
    sigma = 0.75
    activity = np.exp(rng.normal(mu, sigma))
    activity = float(np.clip(activity, cfg['activity_range'][0], cfg['activity_range'][1]))
    co2e  = (activity * ef) / 1000.0
    return {
        'category_id':    cat,
        'activity_value': round(activity, 4),
        'activity_unit':  cfg['unit_code'],
        'ef_value':       round(ef, 6),
        'calculated_co2e': round(co2e, 6),
        'intensity':      round(co2e / max(activity, 1e-9), 10),
        'data_quality':   int(rng.choice([0, 1, 2], p=QUALITY_DIST)),
        'region':         int(rng.choice(REGIONS)),
        'is_anomaly':     0,
        'anomaly_type':   'none',
    }


def _anomaly_record(cat: int, rng: np.random.Generator) -> dict:
    rec   = _normal_record(cat, rng)
    cfg   = CATEGORY_PROFILES[cat]
    atype = ANOMALY_TYPES[rng.integers(len(ANOMALY_TYPES))]

    if atype == 'unit_error_kg_vs_tonne':
        rec['activity_value'] *= 1000.0
        rec['activity_unit']   = 6              # kg instead of tonne
        rec['calculated_co2e'] = (rec['activity_value'] * rec['ef_value']) / 1000.0

    elif atype == 'unit_error_km_vs_tonne_km':
        # Only meaningful for transport-like categories
        rec['activity_value']  = float(rng.uniform(50.0, 5000.0))   # looks like km
        rec['activity_unit']   = 7              # km not tonne-km
        rec['calculated_co2e'] = (rec['activity_value'] * rec['ef_value']) / 1000.0

    elif atype == 'magnitude_spike':
        factor = rng.choice([100.0, 500.0, 1000.0])
        rec['activity_value']  *= factor
        rec['calculated_co2e'] *= factor

    elif atype == 'magnitude_underflow':
        rec['activity_value']  *= 0.001
        rec['calculated_co2e'] *= 0.001

    elif atype == 'wrong_ef_applied':
        wrong_cat = rng.choice([c for c in CATEGORIES if c != cat])
        rec['ef_value'] = float(rng.uniform(*CATEGORY_PROFILES[wrong_cat]['ef_range']))
        rec['calculated_co2e'] = (rec['activity_value'] * rec['ef_value']) / 1000.0

    elif atype == 'copy_paste_duplicate':
        round_values = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0, 100000.0]
        rec['activity_value']  = float(rng.choice(round_values))
        rec['calculated_co2e'] = (rec['activity_value'] * rec['ef_value']) / 1000.0
        rec['data_quality']    = 2   # C grade

    elif atype == 'ef_unit_mismatch':
        # Activity in kWh, EF meant for litres — ~10x off
        rec['ef_value']        *= float(rng.uniform(8.0, 12.0))
        rec['calculated_co2e'] = (rec['activity_value'] * rec['ef_value']) / 1000.0

    rec['intensity']    = round(
        rec['calculated_co2e'] / max(rec['activity_value'], 1e-9), 10
    )
    rec['is_anomaly']   = 1
    rec['anomaly_type'] = atype
    return rec


# ── Feature engineering ───────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that help models detect anomalies."""
    df = df.copy()

    # Log-transform skewed numerics
    df['log_activity']  = np.log1p(df['activity_value'])
    df['log_co2e']      = np.log1p(df['calculated_co2e'])
    df['log_ef']        = np.log1p(df['ef_value'])

    # Intensity = co2e / activity — the key anomaly signal
    df['log_intensity'] = np.log1p(df['intensity'])

    # Ratio: calculated co2e vs what activity × ef would give
    # Should always be ~1/1000 for valid records
    df['co2e_check_ratio'] = df['calculated_co2e'] / (
        (df['activity_value'] * df['ef_value'] / 1000.0) + 1e-10
    )
    # Perfect = 1.0. Anomalies cause this to deviate.
    df['log_co2e_check']   = np.log(np.clip(df['co2e_check_ratio'], 1e-6, 1e6))

    return df


# ── Main generation function ──────────────────────────────────────────────────

def generate_dataset(n_normal: int = 15000, anomaly_rate: float = 0.07,
                     seed: int = 42) -> pd.DataFrame:
    rng        = np.random.default_rng(seed)
    n_anomaly  = int(n_normal * anomaly_rate / (1.0 - anomaly_rate))
    records    = []

    logger.info(f"Generating {n_normal:,} normal + {n_anomaly:,} anomaly records...")

    for _ in range(n_normal):
        cat = int(rng.choice(CATEGORIES))
        records.append(_normal_record(cat, rng))

    for _ in range(n_anomaly):
        cat = int(rng.choice(CATEGORIES))
        records.append(_anomaly_record(cat, rng))

    df = pd.DataFrame(records)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df = engineer_features(df)
    return df


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    set_seed(42)
    out_path = Path('data/processed/anomaly_dataset.csv')
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_dataset(n_normal=15000, anomaly_rate=0.07)
    df.to_csv(out_path, index=False)

    # Stats
    total    = len(df)
    n_anom   = int(df.is_anomaly.sum())
    n_normal = total - n_anom
    stats = {
        'total':         total,
        'normal':        n_normal,
        'anomaly':       n_anom,
        'anomaly_rate':  round(n_anom / total, 4),
        'by_type':       df[df.is_anomaly == 1].anomaly_type.value_counts().to_dict(),
        'by_category':   df.category_id.value_counts().to_dict(),
        'features':      list(df.columns),
        'n_features':    len(df.columns),
    }

    import json
    print(json.dumps(stats, indent=2))
    logger.info(f"Saved {total:,} records → {out_path}")
