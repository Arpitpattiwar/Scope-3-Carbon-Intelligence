import numpy as np
import pandas as pd
from app.db.seed import DEFRA_EF_RANGES  # your seeded EF values

# Normal records: sample from realistic distributions
def generate_synthetic_records(n=10000):
    records = []
    
    CATEGORY_CONFIGS = {
        1: {'unit': 'tonne', 'ef_range': (500, 3000), 'activity_range': (10, 5000)},
        4: {'unit': 'tonne-km', 'ef_range': (0.05, 0.3), 'activity_range': (1000, 500000)},
        5: {'unit': 'tonne', 'ef_range': (10, 500), 'activity_range': (1, 500)},
        6: {'unit': 'passenger-km', 'ef_range': (0.1, 0.3), 'activity_range': (100, 50000)},
        7: {'unit': 'passenger-km', 'ef_range': (0.03, 0.2), 'activity_range': (1000, 100000)},
    }
    
    for _ in range(n):
        cat = np.random.choice(list(CATEGORY_CONFIGS.keys()))
        cfg = CATEGORY_CONFIGS[cat]
        ef = np.random.uniform(*cfg['ef_range'])
        activity = np.random.lognormal(
            mean=np.log(np.mean(cfg['activity_range'])), sigma=0.5
        )
        co2e = (activity * ef) / 1000
        
        records.append({
            'category_id': cat,
            'activity_value': activity,
            'calculated_co2e': co2e,
            'ef_value': ef,
            'data_quality': np.random.choice([0, 1, 2], p=[0.3, 0.5, 0.2]),  # A/B/C
            'region': np.random.randint(0, 5),
            'is_anomaly': 0
        })
    
    # Inject 5% anomalies
    n_anomalies = int(n * 0.05)
    for _ in range(n_anomalies):
        cat = np.random.choice(list(CATEGORY_CONFIGS.keys()))
        cfg = CATEGORY_CONFIGS[cat]
        
        anomaly_type = np.random.choice(['unit_error', 'magnitude', 'wrong_ef'])
        
        if anomaly_type == 'unit_error':
            # kg submitted instead of tonnes — 1000x off
            activity = np.random.uniform(*cfg['activity_range']) * 1000
        elif anomaly_type == 'magnitude':
            activity = np.random.uniform(*cfg['activity_range']) * np.random.choice([100, 0.001])
        else:
            ef = np.random.uniform(*cfg['ef_range']) * 50  # wrong EF
            activity = np.random.uniform(*cfg['activity_range'])
            
        ef = np.random.uniform(*cfg['ef_range'])
        co2e = (activity * ef) / 1000
        
        records.append({
            'category_id': cat,
            'activity_value': activity,
            'calculated_co2e': co2e,
            'ef_value': ef,
            'data_quality': 2,  # C grade
            'region': np.random.randint(0, 5),
            'is_anomaly': 1
        })
    
    records.to_csv('Anomaly Detection.csv', index=False)