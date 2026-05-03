"""
MLP with Entity Embeddings for spend-based emission estimation.

Key architectural choice: learned embeddings for NIC codes and region.
NIC code 2410 (steel) and 2430 (aluminium) should have similar embeddings
because they are both primary metal industries with similar emission profiles.
A one-hot encoding treats them as completely unrelated — embeddings capture structure.

Reference: Guo & Berkhahn, "Entity Embeddings of Categorical Variables" (2016)
This architecture won the Rossmann Kaggle competition.
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


class MLPWithEmbeddings(nn.Module):
    def __init__(self, n_classes: dict, n_numerical: int,
                 embed_dims: dict, hidden_dims: list, dropout: float = 0.3):
        """
        n_classes:   {'nic_4digit': 94, 'nic_2digit': 21, 'region': 5, 'year': 14}
        embed_dims:  {'nic_4digit': 16, 'nic_2digit': 8, 'region': 4, 'year': 4}
        """
        super().__init__()
        self.embeddings = nn.ModuleDict({
            col: nn.Embedding(n_classes[col], embed_dims[col])
            for col in embed_dims
        })

        # Total input dimension after concatenating all embeddings + numerical
        total_emb = sum(embed_dims.values())
        in_dim    = total_emb + n_numerical

        layers = []
        for h in hidden_dims:
            layers += [
                nn.Linear(in_dim, h),
                nn.BatchNorm1d(h),
                nn.ReLU(),
                nn.Dropout(dropout),
            ]
            in_dim = h
        layers.append(nn.Linear(in_dim, 1))
        self.mlp = nn.Sequential(*layers)

        self._init_weights()

    def _init_weights(self):
        for emb in self.embeddings.values():
            nn.init.normal_(emb.weight, std=0.01)
        for m in self.mlp.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                nn.init.zeros_(m.bias)

    def forward(self, cat_inputs: dict, num_input: torch.Tensor) -> torch.Tensor:
        """
        cat_inputs: {'nic_4digit': LongTensor, 'nic_2digit': ..., ...}
        num_input:  FloatTensor (batch, n_numerical)
        """
        emb_parts = [self.embeddings[col](cat_inputs[col]) for col in self.embeddings]
        x = torch.cat(emb_parts + [num_input], dim=1)
        return self.mlp(x).squeeze(1)


def _to_tensors(enc_dict: dict, y: np.ndarray,
                device: torch.device) -> tuple:
    cat_t = {
        col: torch.tensor(enc_dict[col], dtype=torch.long).to(device)
        for col in ['nic_4digit', 'nic_2digit', 'region', 'year']
    }
    num_t = torch.tensor(enc_dict['numerical'], dtype=torch.float32).to(device)
    y_t   = torch.tensor(y, dtype=torch.float32).to(device)
    return cat_t, num_t, y_t


def train(enc_train: dict, y_train: np.ndarray,
          enc_val:   dict, y_val:   np.ndarray,
          n_classes: dict, n_numerical: int,
          config: dict) -> dict:
    device = get_device()
    logger.info(f"Training MLP+Embeddings on {device}")

    embed_dims  = {
        'nic_4digit': config.get('embed_dim_nic4',   16),
        'nic_2digit': config.get('embed_dim_nic2',   8),
        'region':     config.get('embed_dim_region', 4),
        'year':       config.get('embed_dim_year',   4),
    }
    hidden_dims = config.get('hidden_dims', [128, 64, 32])
    dropout     = config.get('dropout', 0.3)
    lr          = config.get('lr', 0.001)
    batch_size  = config.get('batch_size', 512)
    epochs      = config.get('epochs', 200)
    patience    = config.get('patience', 20)

    model     = MLPWithEmbeddings(n_classes, n_numerical,
                                   embed_dims, hidden_dims, dropout).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, patience=7, factor=0.5, min_lr=1e-6
    )
    criterion = nn.MSELoss()

    # Build full tensors for validation (small enough to keep on device)
    cat_v, num_v, y_v = _to_tensors(enc_val, y_val, device)

    # Build training DataLoader using flat indices
    n = len(y_train)
    idx_t = torch.arange(n)
    loader = DataLoader(TensorDataset(idx_t), batch_size=batch_size, shuffle=True)

    # Pre-convert training data to CPU tensors
    cat_train_t = {
        col: torch.tensor(enc_train[col], dtype=torch.long)
        for col in ['nic_4digit', 'nic_2digit', 'region', 'year']
    }
    num_train_t = torch.tensor(enc_train['numerical'], dtype=torch.float32)
    y_train_t   = torch.tensor(y_train, dtype=torch.float32)

    train_losses, val_maes      = [], []
    best_val_mae, best_state, wait = np.inf, None, 0

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0

        for (idx,) in loader:
            cat_b = {col: cat_train_t[col][idx].to(device)
                     for col in cat_train_t}
            num_b = num_train_t[idx].to(device)
            y_b   = y_train_t[idx].to(device)

            optimiser.zero_grad()
            pred  = model(cat_b, num_b)
            loss  = criterion(pred, y_b)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            epoch_loss += loss.item() * len(idx)

        epoch_loss /= n

        model.eval()
        with torch.no_grad():
            val_pred = model(cat_v, num_v)
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
    logger.info(f"Best val MAE (log): {best_val_mae:.5f}")
    return {
        'model':        model,
        'train_losses': train_losses,
        'val_maes':     val_maes,
        'best_val_mae': best_val_mae,
        'embed_dims':   embed_dims,
    }


def get_predictions(model: MLPWithEmbeddings, enc_dict: dict,
                    device: torch.device = None) -> np.ndarray:
    if device is None:
        device = get_device()
    model.eval().to(device)
    cat_t = {
        col: torch.tensor(enc_dict[col], dtype=torch.long).to(device)
        for col in ['nic_4digit', 'nic_2digit', 'region', 'year']
    }
    num_t = torch.tensor(enc_dict['numerical'], dtype=torch.float32).to(device)
    with torch.no_grad():
        return model(cat_t, num_t).cpu().numpy()


def save(model: MLPWithEmbeddings, path: str = 'saved_models/spend/mlp_embeddings.pt'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({'state_dict': model.state_dict()}, path)
    logger.info(f"Saved → {path}")


def load(model_class, state_path: str, n_classes: dict, n_numerical: int,
         embed_dims: dict, hidden_dims: list,
         device: torch.device = None) -> MLPWithEmbeddings:
    if device is None:
        device = get_device()
    model = MLPWithEmbeddings(n_classes, n_numerical,
                               embed_dims, hidden_dims).to(device)
    ckpt  = torch.load(state_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['state_dict'])
    model.eval()
    return model
