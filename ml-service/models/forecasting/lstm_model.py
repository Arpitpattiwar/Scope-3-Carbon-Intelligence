"""
LSTM for multi-step emission forecasting.

Architecture:
  Input:  (batch, seq_len=12, n_features=4)
          Features: [co2_scaled, month_sin, month_cos, year_norm]
  LSTM Layer 1: hidden=64, return_sequences=True,  dropout=0.2
  LSTM Layer 2: hidden=32, return_sequences=False, dropout=0.2
  Dense(16, ReLU) → Dense(horizon=3)

Loss: Huber loss (robust to the occasional extreme outlier)
Prediction intervals: Monte Carlo Dropout (100 forward passes with dropout active)
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils import get_logger, get_device

logger = get_logger(__name__)


class LSTMForecaster(nn.Module):
    def __init__(self, n_features: int = 4, hidden_size: int = 64,
                 num_layers: int = 2, dropout: float = 0.2, horizon: int = 3):
        super().__init__()
        self.horizon    = horizon
        self.hidden_size = hidden_size
        self.num_layers  = num_layers

        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        # Dropout applied after LSTM for MC Dropout inference
        self.dropout = nn.Dropout(dropout)
        self.fc1     = nn.Linear(hidden_size, 16)
        self.relu    = nn.ReLU()
        self.fc2     = nn.Linear(16, horizon)

    def forward(self, x):
        # x: (batch, seq_len, n_features)
        out, _  = self.lstm(x)
        out     = out[:, -1, :]        # take last timestep
        out     = self.dropout(out)
        out     = self.relu(self.fc1(out))
        return self.fc2(out)           # (batch, horizon)

    def mc_predict(self, x: torch.Tensor, n_samples: int = 100) -> tuple:
        """
        Monte Carlo Dropout inference.
        Run n_samples forward passes with dropout active → sample distribution.
        Returns (mean, std) both shape (batch, horizon).
        """
        self.train()   # activate dropout for MC sampling
        with torch.no_grad():
            preds = torch.stack([self.forward(x) for _ in range(n_samples)], dim=0)
        # preds: (n_samples, batch, horizon)
        self.eval()
        return preds.mean(dim=0), preds.std(dim=0)


def train(X_train: np.ndarray, y_train: np.ndarray,
          X_val:   np.ndarray, y_val:   np.ndarray,
          config: dict) -> dict:
    device = get_device()
    logger.info(f"Training LSTM on {device}")

    n_features  = X_train.shape[2]
    horizon     = y_train.shape[1]
    hidden_size = config.get('hidden_size', 64)
    num_layers  = config.get('num_layers', 2)
    dropout     = config.get('dropout', 0.2)
    lr          = config.get('lr', 0.001)
    batch_size  = config.get('batch_size', 64)
    epochs      = config.get('epochs', 150)
    patience    = config.get('patience', 20)

    model     = LSTMForecaster(n_features, hidden_size, num_layers,
                                dropout, horizon).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, patience=7, factor=0.5, min_lr=1e-5
    )
    criterion = nn.HuberLoss(delta=1.0)

    X_t = torch.tensor(X_train, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    X_v = torch.tensor(X_val,   dtype=torch.float32).to(device)
    y_v = torch.tensor(y_val,   dtype=torch.float32).to(device)

    loader = DataLoader(TensorDataset(X_t, y_t), batch_size=batch_size,
                        shuffle=True, drop_last=False)

    train_losses, val_maes      = [], []
    best_val_mae, best_state, wait = np.inf, None, 0

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimiser.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            epoch_loss += loss.item() * len(xb)
        epoch_loss /= len(X_train)

        model.eval()
        with torch.no_grad():
            val_pred = model(X_v)
            val_mae  = (val_pred - y_v).abs().mean().item()
        scheduler.step(val_mae)

        train_losses.append(epoch_loss)
        val_maes.append(val_mae)

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            best_state   = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                logger.info(f"Early stop at epoch {epoch+1}")
                break

        if (epoch + 1) % 20 == 0:
            logger.info(
                f"Epoch {epoch+1:3d} | loss={epoch_loss:.5f} | val_MAE={val_mae:.5f}"
            )

    model.load_state_dict(best_state)
    logger.info(f"Best val MAE: {best_val_mae:.5f}")
    return {
        'model':        model,
        'train_losses': train_losses,
        'val_maes':     val_maes,
        'best_val_mae': best_val_mae,
    }


def get_forecast(model: LSTMForecaster, X: np.ndarray,
                 device: torch.device = None,
                 n_mc: int = 100) -> dict:
    """Returns point forecast + 90% prediction interval."""
    if device is None:
        device = get_device()
    model.to(device)
    X_t  = torch.tensor(X, dtype=torch.float32).to(device)
    mean, std = model.mc_predict(X_t, n_samples=n_mc)
    mean = mean.detach().cpu().numpy()
    std  = std.detach().cpu().numpy()
    z    = 1.645   # 90% PI z-score
    return {
        'mean':  mean,
        'lower': mean - z * std,
        'upper': mean + z * std,
        'std':   std,
    }


def save(model: LSTMForecaster, path: str = 'saved_models/forecasting/lstm.pt'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'state_dict':  model.state_dict(),
        'n_features':  model.lstm.input_size,
        'hidden_size': model.hidden_size,
        'num_layers':  model.num_layers,
        'horizon':     model.horizon,
    }, path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/forecasting/lstm.pt',
         device: torch.device = None) -> LSTMForecaster:
    if device is None:
        device = get_device()
    ckpt  = torch.load(path, map_location=device, weights_only=False)
    model = LSTMForecaster(
        ckpt['n_features'], ckpt['hidden_size'],
        ckpt['num_layers'], horizon=ckpt['horizon'],
    ).to(device)
    model.load_state_dict(ckpt['state_dict'])
    model.eval()
    return model
