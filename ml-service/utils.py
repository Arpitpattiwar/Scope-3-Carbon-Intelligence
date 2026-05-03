"""Shared utilities across all ML tasks."""

import os
import json
import yaml
import random
import logging
import numpy as np
import torch
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            '[%(asctime)s] %(levelname)s %(name)s — %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ── Config ────────────────────────────────────────────────────────────────────

def load_config(path: str = 'config.yaml') -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


# ── Reproducibility ───────────────────────────────────────────────────────────

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ── Device ────────────────────────────────────────────────────────────────────

def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


# ── Serialisation ─────────────────────────────────────────────────────────────

def save_json(obj: dict, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2, default=str)


def load_json(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
