"""
Fetch and preprocess India monthly CO2 emission data for forecasting.

Primary source: Robbie Andrew India GHG monthly series
  URL: https://robbieandrew.github.io/india/data/India_GHG_monthly.csv
  Coverage: 1990-present, monthly, multiple sectors

Fallback: Synthetic India-like monthly series using EDGAR annual
  totals + seasonal profiles from literature.

Output: data/processed/forecast_dataset.csv
  Columns: date, sector, co2_mt, sector_id, month_sin, month_cos, year_norm
  Plus sequence arrays saved as NPZ for direct model loading.
"""

import requests
import numpy as np
import pandas as pd
from pathlib import Path
from io import StringIO
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, set_seed

logger = get_logger(__name__)

# Map dataset sectors → your Scope 3 category IDs
SECTOR_TO_CATEGORY = {
    'oil':     4,   # Oil combustion → Upstream Transport proxy
    'coal':    1,   # Coal → Purchased Goods / industrial
    'gas':     3,   # Natural gas → Fuel & Energy
    'cement':  1,   # Cement → Purchased Goods (industrial process)
}

# India monthly seasonal patterns (fraction of annual, by month)
# Derived from EDGAR monthly disaggregation profiles for India
SEASONAL_PROFILES = {
    'oil':    [0.088, 0.080, 0.085, 0.082, 0.084, 0.080, 0.082, 0.083, 0.083, 0.087, 0.086, 0.090],
    'coal':   [0.086, 0.076, 0.083, 0.082, 0.086, 0.085, 0.085, 0.084, 0.084, 0.086, 0.082, 0.081],
    'gas':    [0.090, 0.082, 0.082, 0.078, 0.075, 0.073, 0.076, 0.079, 0.085, 0.090, 0.093, 0.097],
    'cement': [0.074, 0.070, 0.082, 0.088, 0.090, 0.090, 0.088, 0.087, 0.085, 0.082, 0.080, 0.084],
}

# India annual CO2 by sector (MtCO2), approximate historical values
# Sources: EDGAR, IEA, Global Carbon Project
INDIA_ANNUAL_CO2 = {
    'oil': {
        1990: 142, 1991: 147, 1992: 153, 1993: 158, 1994: 165,
        1995: 175, 1996: 182, 1997: 190, 1998: 195, 1999: 200,
        2000: 207, 2001: 212, 2002: 218, 2003: 225, 2004: 235,
        2005: 248, 2006: 260, 2007: 272, 2008: 278, 2009: 285,
        2010: 300, 2011: 315, 2012: 325, 2013: 335, 2014: 348,
        2015: 360, 2016: 372, 2017: 385, 2018: 400, 2019: 410,
        2020: 370, 2021: 395, 2022: 420, 2023: 435,
    },
    'coal': {
        1990: 560, 1991: 578, 1992: 596, 1993: 612, 1994: 630,
        1995: 655, 1996: 678, 1997: 700, 1998: 715, 1999: 730,
        2000: 760, 2001: 785, 2002: 815, 2003: 852, 2004: 900,
        2005: 948, 2006: 1002, 2007: 1058, 2008: 1105, 2009: 1148,
        2010: 1205, 2011: 1285, 2012: 1358, 2013: 1432, 2014: 1505,
        2015: 1558, 2016: 1595, 2017: 1648, 2018: 1712, 2019: 1748,
        2020: 1658, 2021: 1742, 2022: 1852, 2023: 1920,
    },
    'gas': {
        1990: 28, 1991: 30, 1992: 33, 1993: 35, 1994: 38,
        1995: 42, 1996: 46, 1997: 50, 1998: 54, 1999: 57,
        2000: 60, 2001: 63, 2002: 65, 2003: 66, 2004: 68,
        2005: 72, 2006: 75, 2007: 80, 2008: 88, 2009: 95,
        2010: 102, 2011: 108, 2012: 112, 2013: 115, 2014: 118,
        2015: 122, 2016: 128, 2017: 132, 2018: 136, 2019: 140,
        2020: 132, 2021: 138, 2022: 145, 2023: 152,
    },
    'cement': {
        1990: 45, 1991: 48, 1992: 51, 1993: 54, 1994: 58,
        1995: 63, 1996: 68, 1997: 73, 1998: 77, 1999: 82,
        2000: 89, 2001: 95, 2002: 102, 2003: 110, 2004: 120,
        2005: 130, 2006: 142, 2007: 155, 2008: 165, 2009: 175,
        2010: 188, 2011: 202, 2012: 215, 2013: 228, 2014: 240,
        2015: 248, 2016: 255, 2017: 262, 2018: 272, 2019: 280,
        2020: 248, 2021: 268, 2022: 288, 2023: 302,
    },
}


def _try_download_robbie_andrew() -> pd.DataFrame | None:
    """Attempt to download the Robbie Andrew India monthly dataset."""
    url = 'https://robbieandrew.github.io/india/data/india_co2_emissions_data.csv'
    try:
        logger.info(f"Attempting download: {url}")
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        logger.info(f"Downloaded Robbie Andrew data: {df.shape}")
        return df
    except Exception as e:
        logger.warning(f"Download failed ({e}). Falling back to synthetic.")
        return None


def _build_from_annual(start_year: int = 1990, end_year: int = 2023) -> pd.DataFrame:
    """
    Build monthly series from annual totals + seasonal profiles.
    This is the standard disaggregation method used by EDGAR itself.
    """
    rows = []
    for sector, annual in INDIA_ANNUAL_CO2.items():
        profile = np.array(SEASONAL_PROFILES[sector])
        for year in range(start_year, end_year + 1):
            if year not in annual:
                continue
            annual_total = annual[year]
            # Apply seasonal profile + small random noise for realism
            monthly = annual_total * profile
            monthly += np.random.normal(0, annual_total * 0.005, 12)
            monthly = np.clip(monthly, 0, None)
            for month in range(1, 13):
                rows.append({
                    'year':    year,
                    'month':   month,
                    'sector':  sector,
                    'co2_mt':  round(float(monthly[month - 1]), 3),
                })
    return pd.DataFrame(rows)


def _parse_robbie_andrew(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise the Robbie Andrew CSV into our standard format."""
    # The Robbie Andrew CSV may have different column names depending on version
    # Common format: Year, Month, then sector columns
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]

    # Try to identify columns
    year_col   = next((c for c in df_raw.columns if 'year' in c), None)
    month_col  = next((c for c in df_raw.columns if 'month' in c), None)

    if year_col is None or month_col is None:
        logger.warning("Could not parse Robbie Andrew format, using fallback")
        return None

    rows = []
    for sector in ['oil', 'coal', 'gas', 'cement']:
        # Try several possible column name variants
        variants = [sector, f'{sector}_co2', f'co2_{sector}', f'{sector}co2']
        col = next((c for c in variants if c in df_raw.columns), None)
        if col is None:
            logger.warning(f"Sector '{sector}' not found in columns: {df_raw.columns.tolist()}")
            continue
        sub = df_raw[[year_col, month_col, col]].copy()
        sub.columns = ['year', 'month', 'co2_mt']
        sub['sector'] = sector
        rows.append(sub)

    if not rows:
        return None
    return pd.concat(rows, ignore_index=True)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical and normalised time features."""
    df = df.copy()
    df['date'] = pd.to_datetime(
        df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2) + '-01'
    )
    # Cyclical month encoding (avoids Dec/Jan discontinuity)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # Normalised year (0–1 range over data period)
    y_min, y_max = df['year'].min(), df['year'].max()
    df['year_norm'] = (df['year'] - y_min) / max(y_max - y_min, 1)

    # Sector integer code for model embedding
    sector_map = {'oil': 0, 'coal': 1, 'gas': 2, 'cement': 3}
    df['sector_id'] = df['sector'].map(sector_map).fillna(0).astype(int)

    # Scope 3 category mapping
    df['category_id'] = df['sector'].map(SECTOR_TO_CATEGORY).fillna(1).astype(int)

    df = df.sort_values(['sector', 'date']).reset_index(drop=True)
    return df


def create_sequences(series_values: np.ndarray, seq_len: int = 12,
                     horizon: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert a 1D time series to (X, y) supervised learning pairs.

    X shape: (n_samples, seq_len)
    y shape: (n_samples, horizon)
    """
    X, y = [], []
    for i in range(len(series_values) - seq_len - horizon + 1):
        X.append(series_values[i:i + seq_len])
        y.append(series_values[i + seq_len:i + seq_len + horizon])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_sequence_dataset(df: pd.DataFrame, seq_len: int = 12,
                           horizon: int = 3) -> dict:
    """
    Build multi-feature sequence arrays for LSTM / TFT.

    Returns dict with:
      X:        (n, seq_len, n_features)  input sequences
      y:        (n, horizon)              target values
      scalers:  per-sector min/max for inverse transform
      metadata: sector, start index for each sequence
    """
    from sklearn.preprocessing import MinMaxScaler

    all_X, all_y, all_meta, scalers = [], [], [], {}

    for sector in df['sector'].unique():
        sub = df[df['sector'] == sector].sort_values('date').reset_index(drop=True)

        # Scale the target (co2_mt) to [0, 1]
        scaler = MinMaxScaler()
        co2_scaled = scaler.fit_transform(sub[['co2_mt']]).flatten()
        scalers[sector] = scaler

        # Feature matrix per timestep
        features = np.column_stack([
            co2_scaled,
            sub['month_sin'].values,
            sub['month_cos'].values,
            sub['year_norm'].values,
        ]).astype(np.float32)   # shape: (T, 4)

        for i in range(len(features) - seq_len - horizon + 1):
            all_X.append(features[i:i + seq_len])          # (seq_len, 4)
            all_y.append(co2_scaled[i + seq_len:i + seq_len + horizon])  # (horizon,)
            all_meta.append({'sector': sector, 'start_idx': i})

    return {
        'X':       np.array(all_X, dtype=np.float32),
        'y':       np.array(all_y, dtype=np.float32),
        'scalers': scalers,
        'meta':    all_meta,
        'sectors': df['sector'].unique().tolist(),
    }


if __name__ == '__main__':
    set_seed(42)
    np.random.seed(42)
    out_dir = Path('data/processed')
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Try real data, fall back to synthetic
    df_raw = _try_download_robbie_andrew()
    if df_raw is not None:
        df_monthly = _parse_robbie_andrew(df_raw)
        if df_monthly is None:
            logger.info("Parse failed — using annual disaggregation fallback")
            df_monthly = _build_from_annual()
    else:
        df_monthly = _build_from_annual()

    # Step 2: Add time features
    df = add_time_features(df_monthly)

    # Step 3: Save flat CSV
    df.to_csv(out_dir / 'forecast_dataset.csv', index=False)
    logger.info(f"Saved flat CSV: {len(df):,} rows, {df['sector'].nunique()} sectors")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Step 4: Build and save sequence arrays
    seq_data = build_sequence_dataset(df, seq_len=12, horizon=3)
    np.savez_compressed(
        out_dir / 'forecast_sequences.npz',
        X=seq_data['X'],
        y=seq_data['y'],
    )
    logger.info(
        f"Saved sequences: X={seq_data['X'].shape}, y={seq_data['y'].shape}"
    )

    # Save scaler params
    scaler_params = {}
    for sector, scaler in seq_data['scalers'].items():
        scaler_params[sector] = {
            'min': float(scaler.data_min_[0]),
            'max': float(scaler.data_max_[0]),
        }
    import json
    with open(out_dir / 'forecast_scalers.json', 'w') as f:
        json.dump(scaler_params, f, indent=2)

    # Print summary
    print("\n── Dataset Summary ──")
    print(df.groupby('sector')[['co2_mt']].describe().round(2))
