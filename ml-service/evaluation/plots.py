"""
Visualisation functions for all three tasks.
Saves publication-quality plots to results/plots/.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from pathlib import Path

sns.set_theme(style='whitegrid', palette='tab10')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
Path('results/plots').mkdir(parents=True, exist_ok=True)


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def plot_pr_curves(results: dict, save_path: str = 'results/plots/anomaly_pr_curves.png'):
    """Precision-Recall curves for all anomaly models overlaid."""
    from sklearn.metrics import precision_recall_curve, average_precision_score

    fig, ax = plt.subplots(figsize=(8, 6))
    for i, (name, data) in enumerate(results.items()):
        y_true, scores = data['y_true'], data['scores']
        prec, rec, _   = precision_recall_curve(y_true, scores)
        ap             = average_precision_score(y_true, scores)
        ax.plot(rec, prec, lw=2, color=COLORS[i],
                label=f'{name}  (AP={ap:.3f})')

    # Baseline: random classifier
    baseline = results[list(results.keys())[0]]['y_true'].mean()
    ax.axhline(baseline, ls='--', color='gray', lw=1, label=f'Random  (AP={baseline:.3f})')

    ax.set_xlabel('Recall', fontsize=12)
    ax.set_ylabel('Precision', fontsize=12)
    ax.set_title('Precision-Recall Curves — Anomaly Detection', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.05])
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_roc_curves(results: dict, save_path: str = 'results/plots/anomaly_roc_curves.png'):
    from sklearn.metrics import roc_curve, roc_auc_score

    fig, ax = plt.subplots(figsize=(8, 6))
    for i, (name, data) in enumerate(results.items()):
        fpr, tpr, _ = roc_curve(data['y_true'], data['scores'])
        auc         = roc_auc_score(data['y_true'], data['scores'])
        ax.plot(fpr, tpr, lw=2, color=COLORS[i],
                label=f'{name}  (AUC={auc:.3f})')

    ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random (AUC=0.500)')
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('ROC Curves — Anomaly Detection', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_reconstruction_errors(normal_errors: dict, anomaly_errors: dict,
                                 save_path: str = 'results/plots/recon_error_dist.png'):
    """
    Distribution of reconstruction errors for normal vs anomaly records.
    Only for Autoencoder and VAE (Isolation Forest has no reconstruction error).
    """
    models = list(normal_errors.keys())
    fig, axes = plt.subplots(1, len(models), figsize=(6 * len(models), 5))
    if len(models) == 1:
        axes = [axes]

    for ax, model_name in zip(axes, models):
        ne = np.log1p(normal_errors[model_name])   # log for readability
        ae = np.log1p(anomaly_errors[model_name])

        ax.hist(ne, bins=60, alpha=0.6, color='steelblue', label='Normal',   density=True)
        ax.hist(ae, bins=60, alpha=0.6, color='tomato',    label='Anomaly',  density=True)
        ax.set_xlabel('log(1 + Reconstruction Error)', fontsize=11)
        ax.set_ylabel('Density', fontsize=11)
        ax.set_title(f'{model_name}\nError Distributions', fontsize=11, fontweight='bold')
        ax.legend()

    fig.suptitle('Reconstruction Error: Normal vs Anomaly', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_per_type_recall(recall_data: dict,
                          save_path: str = 'results/plots/per_type_recall.png'):
    """Bar chart of recall per anomaly type, grouped by model."""
    models = list(recall_data.keys())
    if not models:
        return

    all_types = sorted({
        t for m in recall_data.values() for t in m.keys()
    })

    x    = np.arange(len(all_types))
    w    = 0.25
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, model in enumerate(models):
        recalls = [recall_data[model].get(t, {}).get('recall', 0) for t in all_types]
        ax.bar(x + i * w, recalls, w, label=model, color=COLORS[i], alpha=0.85)

    ax.set_xticks(x + w)
    ax.set_xticklabels(all_types, rotation=25, ha='right', fontsize=9)
    ax.set_ylabel('Recall', fontsize=12)
    ax.set_ylim([0, 1.1])
    ax.set_title('Recall per Anomaly Type — All Models', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.axhline(0.8, ls='--', color='gray', lw=1, label='0.8 target')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


# ── Forecasting ───────────────────────────────────────────────────────────────

def plot_forecast_comparison(actuals: np.ndarray, forecasts: dict,
                               intervals: dict = None,
                               sector: str = '',
                               save_path: str = None):
    """
    Overlay SARIMA, LSTM, TFT forecasts against actual values.
    Includes prediction intervals as shaded bands.
    """
    if save_path is None:
        save_path = f'results/plots/forecast_{sector}.png'

    fig, ax = plt.subplots(figsize=(14, 6))
    t = np.arange(len(actuals))

    ax.plot(t, actuals, 'k-', lw=2.5, label='Actual', zorder=5)

    for i, (name, pred) in enumerate(forecasts.items()):
        n = min(len(pred), len(actuals))
        ax.plot(t[:n], pred[:n], '--', lw=2, color=COLORS[i], label=name, alpha=0.85)
        if intervals and name in intervals:
            lo, hi = intervals[name]
            n2 = min(len(lo), len(actuals))
            ax.fill_between(t[:n2], lo[:n2], hi[:n2],
                            alpha=0.15, color=COLORS[i])

    ax.set_xlabel('Month (test period)', fontsize=12)
    ax.set_ylabel('CO₂ (scaled)', fontsize=12)
    ax.set_title(f'Emission Forecasts — {sector}', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_training_curves(loss_dict: dict, title: str,
                          save_path: str = 'results/plots/training_curves.png'):
    """Plot train/val loss curves for neural models."""
    n_models = len(loss_dict)
    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4))
    if n_models == 1:
        axes = [axes]

    for ax, (name, curves) in zip(axes, loss_dict.items()):
        if 'train_losses' in curves:
            ax.plot(curves['train_losses'], label='Train loss', lw=2)
        if 'val_maes' in curves or 'val_aps' in curves:
            key = 'val_aps' if 'val_aps' in curves else 'val_maes'
            label = 'Val AP' if key == 'val_aps' else 'Val MAE'
            ax.plot(curves[key], label=label, lw=2)
        ax.set_title(name, fontsize=11, fontweight='bold')
        ax.set_xlabel('Epoch')
        ax.legend(fontsize=9)

    fig.suptitle(title, fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


# ── Spend Estimation ──────────────────────────────────────────────────────────

def plot_pred_vs_actual(y_true: np.ndarray, preds: dict,
                         save_path: str = 'results/plots/spend_pred_vs_actual.png'):
    """
    Scatter plot of predicted vs actual log-intensity.
    Diagonal line = perfect prediction.
    """
    n = len(preds)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    if n == 1:
        axes = [axes]

    for ax, (name, y_pred) in zip(axes, preds.items()):
        ax.scatter(y_true, y_pred, alpha=0.3, s=8, color='steelblue')
        lo = min(y_true.min(), y_pred.min())
        hi = max(y_true.max(), y_pred.max())
        ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='Perfect')
        r2  = float(np.corrcoef(y_true, y_pred)[0, 1] ** 2)
        ax.set_title(f'{name}\n$R^2$={r2:.3f}', fontsize=11, fontweight='bold')
        ax.set_xlabel('Actual log(intensity)', fontsize=10)
        ax.set_ylabel('Predicted log(intensity)', fontsize=10)
        ax.legend(fontsize=9)

    fig.suptitle('Predicted vs Actual — Spend Estimation', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


def plot_feature_importance(importance_data: dict,
                             save_path: str = 'results/plots/feature_importance.png'):
    """
    SHAP / TabNet attention-based feature importance comparison.
    """
    fig, axes = plt.subplots(1, len(importance_data), figsize=(7 * len(importance_data), 6))
    if len(importance_data) == 1:
        axes = [axes]

    for ax, (name, data) in zip(axes, importance_data.items()):
        if 'importance_dict' not in data:
            continue
        items    = sorted(data['importance_dict'].items(), key=lambda x: x[1], reverse=True)
        features = [x[0] for x in items[:15]]
        vals     = [x[1] for x in items[:15]]
        ax.barh(features[::-1], vals[::-1], color='steelblue', alpha=0.85)
        ax.set_xlabel('Importance', fontsize=11)
        ax.set_title(f'{name}\nFeature Importance', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


# ── Summary Comparison Table Plot ─────────────────────────────────────────────

def plot_comparison_table(results: dict, task: str,
                           save_path: str = None):
    """
    Render the metric comparison table as a matplotlib figure (for slides).
    """
    if save_path is None:
        save_path = f'results/plots/{task}_comparison_table.png'

    models  = list(results.keys())
    metrics = list(next(iter(results.values())).keys())

    cell_text = [[str(results[m].get(metric, '—')) for metric in metrics] for m in models]

    fig, ax = plt.subplots(figsize=(max(10, len(metrics) * 1.8), len(models) * 0.8 + 1.5))
    ax.axis('off')
    table = ax.table(
        cellText=cell_text,
        rowLabels=models,
        colLabels=metrics,
        loc='center',
        cellLoc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)

    # Highlight header
    for j in range(len(metrics)):
        table[0, j].set_facecolor('#2c7bb6')
        table[0, j].set_text_props(color='white', fontweight='bold')

    ax.set_title(f'Model Comparison — {task}', fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path}")


# ── Adapter functions matching train script call signatures ───────────────────

def plot_pr_curves(model_scores: dict, save_path: str, title: str = ''):
    """
    Adapter: model_scores = {name: (y_true, scores)} or {name: {'y_true':..,'scores':..}}
    """
    from sklearn.metrics import precision_recall_curve, average_precision_score
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, (name, data) in enumerate(model_scores.items()):
        if isinstance(data, tuple):
            y_true, scores = data
        else:
            y_true, scores = data['y_true'], data['scores']
        prec, rec, _ = precision_recall_curve(y_true, scores)
        ap = average_precision_score(y_true, scores)
        ax.plot(rec, prec, lw=2, color=COLORS[i % len(COLORS)],
                label=f'{name}  (AP={ap:.3f})')
    baseline = y_true.mean()
    ax.axhline(baseline, ls='--', color='gray', lw=1, label=f'Random ({baseline:.3f})')
    ax.set_xlabel('Recall'); ax.set_ylabel('Precision')
    ax.set_title(title or 'Precision-Recall Curves', fontweight='bold')
    ax.legend(); ax.set_xlim([0,1]); ax.set_ylim([0,1.05])
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_roc_curves(model_scores: dict, save_path: str, title: str = ''):
    from sklearn.metrics import roc_curve, roc_auc_score
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, (name, data) in enumerate(model_scores.items()):
        y_true, scores = data if isinstance(data, tuple) else (data['y_true'], data['scores'])
        fpr, tpr, _ = roc_curve(y_true, scores)
        auc = roc_auc_score(y_true, scores)
        ax.plot(fpr, tpr, lw=2, color=COLORS[i % len(COLORS)],
                label=f'{name}  (AUC={auc:.3f})')
    ax.plot([0,1],[0,1],'k--',lw=1,label='Random'); ax.set_xlabel('FPR'); ax.set_ylabel('TPR')
    ax.set_title(title or 'ROC Curves', fontweight='bold'); ax.legend()
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()


def plot_reconstruction_histograms(model_scores: dict, save_path: str):
    """model_scores = {name: (y_true, scores)}"""
    n = len(model_scores)
    fig, axes = plt.subplots(1, n, figsize=(6*n, 5))
    if n == 1: axes = [axes]
    for ax, (name, (y_true, scores)) in zip(axes, model_scores.items()):
        normal_s  = scores[y_true == 0]
        anomaly_s = scores[y_true == 1]
        ax.hist(np.log1p(normal_s),  bins=60, alpha=0.6, label='Normal',  color='steelblue')
        ax.hist(np.log1p(anomaly_s), bins=60, alpha=0.6, label='Anomaly', color='tomato')
        ax.set_title(f'{name} — Score Distribution', fontweight='bold')
        ax.set_xlabel('log(Anomaly Score)'); ax.legend()
    plt.suptitle('Reconstruction Error Distributions', fontsize=13, fontweight='bold')
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_training_curves(loss_dict: dict, save_path: str, ylabel: str = 'Loss',
                          title: str = 'Training Curves'):
    """loss_dict = {model_name: [loss_per_epoch]}"""
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (name, losses) in enumerate(loss_dict.items()):
        if losses:
            ax.plot(losses, lw=2, color=COLORS[i % len(COLORS)], label=name)
    ax.set_xlabel('Epoch'); ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight='bold'); ax.legend()
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_per_type_recall(recall_data: dict, save_path: str):
    """recall_data = {model_name: {anomaly_type: {recall, n_total, n_caught}}}"""
    all_types = set()
    for m_data in recall_data.values():
        all_types.update(m_data.keys())
    all_types = sorted(all_types)
    if not all_types:
        return

    x      = np.arange(len(all_types))
    n_m    = len(recall_data)
    width  = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (model_name, m_data) in enumerate(recall_data.items()):
        vals = [m_data.get(t, {}).get('recall', 0) for t in all_types]
        ax.bar(x + i * width, vals, width, label=model_name,
               color=COLORS[i % len(COLORS)], alpha=0.85)
    ax.set_xticks(x + width)
    ax.set_xticklabels(all_types, rotation=30, ha='right', fontsize=9)
    ax.set_ylabel('Recall'); ax.set_ylim([0, 1.1])
    ax.set_title('Recall per Anomaly Type', fontweight='bold'); ax.legend()
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_forecast_comparison(forecasts: dict, save_path: str, title: str = ''):
    """forecasts = {model: {preds, actuals, lowers, uppers}}"""
    n = len(forecasts)
    fig, axes = plt.subplots(n, 1, figsize=(12, 4 * n), sharex=False)
    if n == 1: axes = [axes]
    for ax, (name, fc) in zip(axes, forecasts.items()):
        t = np.arange(len(fc['actuals']))
        ax.plot(t, fc['actuals'], 'k-',  lw=1.5, label='Actual')
        ax.plot(t, fc['preds'],   '--',  lw=1.5, label='Predicted',
                color='steelblue')
        if 'lowers' in fc and 'uppers' in fc:
            ax.fill_between(t, fc['lowers'][:len(t)], fc['uppers'][:len(t)],
                            alpha=0.25, color='steelblue', label='90% PI')
        ax.set_title(f'{name}', fontweight='bold'); ax.legend(fontsize=9)
        ax.set_ylabel('CO₂ (scaled)')
    axes[-1].set_xlabel('Time step')
    plt.suptitle(title or 'Forecasting Comparison', fontsize=13, fontweight='bold')
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_regression_scatter(model_preds: dict, save_path: str, title: str = ''):
    """model_preds = {name: (y_true, y_pred)}"""
    n = len(model_preds)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1: axes = [axes]
    for ax, (name, (yt, yp)) in zip(axes, model_preds.items()):
        from sklearn.metrics import r2_score
        r2 = r2_score(yt, yp)
        ax.scatter(yt, yp, alpha=0.3, s=8, color='steelblue')
        lim = [min(yt.min(), yp.min()), max(yt.max(), yp.max())]
        ax.plot(lim, lim, 'r--', lw=1.5)
        ax.set_xlabel('Actual (log)'); ax.set_ylabel('Predicted (log)')
        ax.set_title(f'{name}\nR²={r2:.4f}', fontweight='bold')
    plt.suptitle(title or 'Predicted vs Actual', fontsize=13, fontweight='bold')
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_feature_importance(importance_data: dict, save_path: str):
    """importance_data = {model_name: {feature: importance_value}}"""
    n = len(importance_data)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6))
    if n == 1: axes = [axes]
    for ax, (name, imp_dict) in zip(axes, importance_data.items()):
        if not imp_dict: continue
        sorted_items = sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)[:15]
        features, vals = zip(*sorted_items)
        ax.barh(list(reversed(features)), list(reversed(vals)),
                color='steelblue', alpha=0.85)
        ax.set_title(f'{name}\nFeature Importance', fontweight='bold')
        ax.set_xlabel('Importance')
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")


def plot_per_sector_r2(model_sector_data: dict, save_path: str):
    """model_sector_data = {name: (y_true, y_pred, sector_labels)}"""
    from sklearn.metrics import r2_score
    all_sectors = set()
    for _, (yt, yp, sl) in model_sector_data.items():
        all_sectors.update(np.unique(sl).tolist())
    all_sectors = sorted(all_sectors)[:20]  # top 20

    x     = np.arange(len(all_sectors))
    width = 0.25
    n_m   = len(model_sector_data)
    fig, ax = plt.subplots(figsize=(max(12, len(all_sectors) * 0.8), 6))
    for i, (name, (yt, yp, sl)) in enumerate(model_sector_data.items()):
        r2s = []
        for s in all_sectors:
            mask = sl == s
            if mask.sum() >= 5:
                r2s.append(r2_score(yt[mask], yp[mask]))
            else:
                r2s.append(0.0)
        ax.bar(x + i * width, r2s, width, label=name,
               color=COLORS[i % len(COLORS)], alpha=0.85)
    ax.set_xticks(x + width); ax.set_xticklabels(all_sectors, rotation=45, ha='right')
    ax.set_ylabel('R²'); ax.set_title('R² per NIC-2 Sector Group', fontweight='bold')
    ax.legend(); ax.axhline(0, color='k', lw=0.5)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved: {save_path}")
