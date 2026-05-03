"""
Autoencoder for anomaly detection.
Learns to reconstruct normal emission records.
High reconstruction error = anomaly.

Architecture:
  Encoder: input → 64 → 32 → 16 (bottleneck 8)
  Decoder: 8  → 16 → 32 → 64 → input
  Loss: MSE reconstruction
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


class Autoencoder(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: list, bottleneck: int,
                 dropout: float = 0.1):
        super().__init__()
        # Encoder
        enc_layers = []
        in_dim = input_dim
        for h in hidden_dims:
            enc_layers += [nn.Linear(in_dim, h), nn.BatchNorm1d(h),
                           nn.ReLU(), nn.Dropout(dropout)]
            in_dim = h
        enc_layers.append(nn.Linear(in_dim, bottleneck))
        self.encoder = nn.Sequential(*enc_layers)

        # Decoder (mirror of encoder)
        dec_layers = []
        in_dim = bottleneck
        for h in reversed(hidden_dims):
            dec_layers += [nn.Linear(in_dim, h), nn.BatchNorm1d(h),
                           nn.ReLU(), nn.Dropout(dropout)]
            in_dim = h
        dec_layers.append(nn.Linear(in_dim, input_dim))
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x):
        z    = self.encoder(x)
        x_hat = self.decoder(z)
        return x_hat

    def encode(self, x):
        return self.encoder(x)

    def reconstruction_error(self, x):
        """Per-sample MSE reconstruction error — used as anomaly score."""
        with torch.no_grad():
            x_hat = self.forward(x)
            return ((x - x_hat) ** 2).mean(dim=1)


def train(X_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray,
          config: dict) -> dict:
    device = get_device()
    logger.info(f"Training Autoencoder on {device}")

    input_dim   = X_train.shape[1]
    hidden_dims = config.get('hidden_dims', [64, 32, 16])
    bottleneck  = config.get('bottleneck', 8)
    dropout     = config.get('dropout', 0.1)
    lr          = config.get('lr', 0.001)
    batch_size  = config.get('batch_size', 256)
    epochs      = config.get('epochs', 100)
    patience    = config.get('patience', 15)

    model = Autoencoder(input_dim, hidden_dims, bottleneck, dropout).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, patience=5, factor=0.5, min_lr=1e-5
    )
    criterion = nn.MSELoss()

    # Only train on NORMAL records (unsupervised: model learns normal distribution)
    # In practice for anomaly detection, we train the autoencoder only on clean data
    # Here we use all training data since labels aren't available in production;
    # the model still learns mostly normal patterns (93% of data)
    X_t = torch.tensor(X_train, dtype=torch.float32)
    X_v = torch.tensor(X_val,   dtype=torch.float32).to(device)
    y_v = torch.tensor(y_val,   dtype=torch.float32).to(device)

    loader = DataLoader(TensorDataset(X_t), batch_size=batch_size, shuffle=True)

    train_losses, val_aps = [], []
    best_val_ap, best_state, wait = -1.0, None, 0

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for (xb,) in loader:
            xb = xb.to(device)
            optimiser.zero_grad()
            x_hat = model(xb)
            loss  = criterion(x_hat, xb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            epoch_loss += loss.item() * len(xb)
        epoch_loss /= len(X_train)

        # Validation: compute AP on validation set
        model.eval()
        with torch.no_grad():
            scores = model.reconstruction_error(X_v).cpu().numpy()
        from sklearn.metrics import average_precision_score
        val_ap = average_precision_score(y_val, scores)
        scheduler.step(1 - val_ap)   # minimise 1 - AP

        train_losses.append(epoch_loss)
        val_aps.append(val_ap)

        if val_ap > best_val_ap:
            best_val_ap = val_ap
            best_state  = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                logger.info(f"Early stop at epoch {epoch+1}")
                break

        if (epoch + 1) % 10 == 0:
            logger.info(
                f"Epoch {epoch+1:3d} | train_loss={epoch_loss:.5f} | val_AP={val_ap:.4f}"
            )

    model.load_state_dict(best_state)
    logger.info(f"Best val AP: {best_val_ap:.4f}")
    return {
        'model':        model,
        'train_losses': train_losses,
        'val_aps':      val_aps,
        'best_val_ap':  best_val_ap,
    }


def get_scores(model: Autoencoder, X: np.ndarray,
               device: torch.device = None) -> np.ndarray:
    if device is None:
        device = get_device()
    model.eval().to(device)
    X_t = torch.tensor(X, dtype=torch.float32).to(device)
    with torch.no_grad():
        scores = model.reconstruction_error(X_t).cpu().numpy()
    return scores


def save(model: Autoencoder, path: str = 'saved_models/anomaly/autoencoder.pt'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'state_dict':  model.state_dict(),
        'input_dim':   model.encoder[0].in_features,
        'hidden_dims': [
            model.encoder[i].out_features
            for i in range(0, len(model.encoder) - 1, 4)
        ],
        'bottleneck': model.encoder[-1].out_features,
    }, path)
    logger.info(f"Saved → {path}")


def load(path: str = 'saved_models/anomaly/autoencoder.pt',
         device: torch.device = None) -> Autoencoder:
    if device is None:
        device = get_device()
    ckpt  = torch.load(path, map_location=device, weights_only=False)
    model = Autoencoder(
        ckpt['input_dim'], ckpt['hidden_dims'], ckpt['bottleneck']
    ).to(device)
    model.load_state_dict(ckpt['state_dict'])
    model.eval()
    return model
