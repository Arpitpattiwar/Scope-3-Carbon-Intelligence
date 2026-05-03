"""
Temporal Fusion Transformer (TFT) for emission forecasting.

TFT (Lim et al., 2021) combines:
  - LSTM encoder-decoder for local temporal processing
  - Multi-head self-attention for long-range dependencies
  - Variable Selection Networks for input feature importance
  - Quantile output head for native prediction intervals

Using pytorch-forecasting which wraps TFT in PyTorch Lightning.

Key advantages over LSTM for this task:
  1. Quantile outputs give calibrated prediction intervals (no MC Dropout needed)
  2. Attention weights show which past timesteps the model relies on
  3. Handles both static (sector) and temporal (co2, month) covariates
  4. State-of-the-art on M4 and other forecasting benchmarks
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger

logger = get_logger(__name__)


def _build_tft_dataframe(sector_data: dict, split: str = 'train',
                          seq_len: int = 12, horizon: int = 3) -> pd.DataFrame:
    """
    Build the long-format DataFrame that pytorch-forecasting expects.

    Columns required by TimeSeriesDataSet:
      time_idx:     integer time index (0, 1, 2, ...)
      group_id:     series identifier (sector name)
      target:       value to forecast (co2_scaled)
      + known covariates: month_sin, month_cos, year_norm
    """
    rows = []
    for sector, data in sector_data.items():
        if split == 'train':
            end = data['val_start']
        elif split == 'val':
            end = data['test_start']
        else:
            end = len(data['raw'])

        start = 0
        series = data['scaled']   # use scaled values

        df_sector = pd.DataFrame({
            'time_idx':  np.arange(start, end),
            'group_id':  sector,
            'target':    series[start:end].astype(np.float32),
            'month_sin': np.sin(2 * np.pi * np.arange(start, end) % 12 / 12).astype(np.float32),
            'month_cos': np.cos(2 * np.pi * np.arange(start, end) % 12 / 12).astype(np.float32),
            'year_norm': (np.arange(start, end) / max(len(data['scaled']) - 1, 1)).astype(np.float32),
        })
        rows.append(df_sector)

    return pd.concat(rows, ignore_index=True)


def train(sector_data: dict, config: dict) -> dict:
    """
    Train TFT using pytorch-forecasting + PyTorch Lightning.
    Returns the trained trainer and model objects.
    """
    try:
        from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
        from pytorch_forecasting.metrics import QuantileLoss
        import lightning as L
        from torch.utils.data import DataLoader
    except ImportError:
        logger.error("pytorch-forecasting not installed. Run: pip install pytorch-forecasting lightning")
        raise

    seq_len  = config.get('seq_len', 12)
    horizon  = config.get('horizon', 3)
    q        = config.get('quantiles', [0.05, 0.25, 0.5, 0.75, 0.95])
    epochs   = config.get('epochs', 50)
    lr       = config.get('lr', 0.003)
    bs       = config.get('batch_size', 64)
    clip     = config.get('gradient_clip', 0.1)
    hidden   = config.get('hidden_size', 32)
    attn_h   = config.get('attention_head_size', 4)
    dropout  = config.get('dropout', 0.1)
    hcs      = config.get('hidden_continuous_size', 16)

    # Build training DataFrame (train + val combined for dataset definition)
    df_full = _build_tft_dataframe(sector_data, split='val')   # up to test start

    # Separate train and val indices
    max_train_idx = min(
        data['val_start'] - 1 for data in sector_data.values()
    )

    training = TimeSeriesDataSet(
        df_full[df_full.time_idx <= max_train_idx],
        time_idx='time_idx',
        target='target',
        group_ids=['group_id'],
        min_encoder_length=seq_len // 2,
        max_encoder_length=seq_len,
        min_prediction_length=1,
        max_prediction_length=horizon,
        time_varying_known_reals=['month_sin', 'month_cos', 'year_norm'],
        time_varying_unknown_reals=['target'],
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation = TimeSeriesDataSet.from_dataset(
        training,
        df_full,
        predict=True,
        stop_randomization=True,
    )

    train_loader = training.to_dataloader(train=True,  batch_size=bs,  num_workers=0)
    val_loader   = validation.to_dataloader(train=False, batch_size=bs*2, num_workers=0)

    tft = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=lr,
        hidden_size=hidden,
        attention_head_size=attn_h,
        dropout=dropout,
        hidden_continuous_size=hcs,
        output_size=len(q),
        loss=QuantileLoss(quantiles=q),
        reduce_on_plateau_patience=5,
    )
    logger.info(f"TFT parameters: {sum(p.numel() for p in tft.parameters()):,}")

    trainer = L.Trainer(
        max_epochs=epochs,
        enable_progress_bar=True,
        gradient_clip_val=clip,
        limit_train_batches=1.0,
        logger=False,
        enable_checkpointing=True,
        default_root_dir='saved_models/forecasting/tft_checkpoints',
    )
    trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=val_loader)

    # Load best checkpoint
    best_path = trainer.checkpoint_callback.best_model_path
    if best_path:
        tft = TemporalFusionTransformer.load_from_checkpoint(best_path)
        logger.info(f"Loaded best checkpoint: {best_path}")

    return {
        'model':   tft,
        'trainer': trainer,
        'dataset': training,
        'quantiles': q,
    }


def get_forecast(model, sector_data: dict, val_loader,
                 quantiles: list = None) -> dict:
    """
    Generate quantile forecasts and extract attention weights.
    """
    if quantiles is None:
        quantiles = [0.05, 0.5, 0.95]

    predictions = model.predict(val_loader, mode='quantiles', return_x=True)
    # predictions.output: (n_samples, horizon, n_quantiles)

    # Get attention weights for interpretability
    try:
        interp = model.interpret_output(predictions, reduction='sum')
        attn   = interp.get('attention', None)
    except Exception:
        attn = None

    preds     = predictions.output.numpy()
    q_idx_lo  = 0    # 5th percentile
    q_idx_mid = 2    # 50th percentile (median)
    q_idx_hi  = 4    # 95th percentile

    return {
        'mean':      preds[:, :, q_idx_mid],
        'lower':     preds[:, :, q_idx_lo],
        'upper':     preds[:, :, q_idx_hi],
        'all_quantiles': preds,
        'attention': attn,
    }


def save(result: dict, path: str = 'saved_models/forecasting/tft.pt'):
    """Save TFT using Lightning's save mechanism."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    result['trainer'].save_checkpoint(path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/forecasting/tft.pt'):
    try:
        from pytorch_forecasting import TemporalFusionTransformer
        model = TemporalFusionTransformer.load_from_checkpoint(path)
        model.eval()
        return model
    except Exception as e:
        logger.error(f"Could not load TFT: {e}")
        raise
