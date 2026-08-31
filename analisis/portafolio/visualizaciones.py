# -*- coding: utf-8 -*-
"""Visualizaciones para el constructor y backtest de portafolio.

Genera charts estáticos con matplotlib:
- Efficient frontier con portafolio óptimo, min-vol y activos individuales.
- Pesos del portafolio óptimo.
- Retornos acumulados y drawdown vs benchmark.
"""
import os

import numpy as np
import pandas as pd


def _ensure_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        raise ImportError(
            "matplotlib es necesario para generar visualizaciones. "
            "Instalar con: pip install matplotlib"
        )


def plot_efficient_frontier(returns_df, pesos_opt, out_path, risk_free=0.04, n_random=3000):
    """Grafica la frontera eficiente y el portafolio max-Sharpe."""
    plt = _ensure_matplotlib()
    returns_df = returns_df.dropna(axis=1, thresh=int(len(returns_df) * 0.9)).fillna(0)
    if returns_df.shape[1] < 2:
        return False

    mu = returns_df.mean() * 252
    sigma = returns_df.cov() * 252
    n = len(mu)

    # portafolios aleatorios
    weights = np.random.dirichlet(np.ones(n), n_random)
    rets = weights.dot(mu.values)
    vols = np.sqrt(np.einsum("ij,jk,ik->i", weights, sigma.values, weights))
    sharpes = (rets - risk_free) / np.where(vols > 0, vols, 1e-9)

    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(vols, rets, c=sharpes, cmap="viridis", alpha=0.4, s=10)
    plt.colorbar(sc, ax=ax, label="Sharpe")

    # activos individuales
    for ticker, m in mu.items():
        v = np.sqrt(sigma.loc[ticker, ticker])
        ax.scatter(v, m, c="red", s=50, zorder=5)
        ax.annotate(ticker, (v, m), fontsize=8, alpha=0.8)

    # portafolio optimo
    if pesos_opt is not None and isinstance(pesos_opt, dict):
        w_opt = np.array([pesos_opt.get(t, 0) for t in mu.index])
        r_opt = w_opt.dot(mu.values)
        v_opt = np.sqrt(np.dot(w_opt.T, np.dot(sigma.values, w_opt)))
        ax.scatter(v_opt, r_opt, c="gold", edgecolors="black", s=200, marker="*", zorder=6,
                   label="Max Sharpe")
        ax.legend()

    ax.set_xlabel("Volatilidad anualizada")
    ax.set_ylabel("Retorno esperado anualizado")
    ax.set_title("Frontera Eficiente")
    ax.grid(True, alpha=0.3)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return True


def plot_weights(pesos, out_path, titulo="Pesos del portafolio óptimo"):
    """Bar chart horizontal de pesos."""
    plt = _ensure_matplotlib()
    if not pesos:
        return False
    df = pd.DataFrame(sorted(pesos.items(), key=lambda x: -x[1]), columns=["ticker", "peso"])
    df = df[df["peso"] >= 0.005]
    if df.empty:
        return False

    fig, ax = plt.subplots(figsize=(8, max(4, len(df) * 0.4)))
    colors = plt.cm.Spectral(np.linspace(0.15, 0.85, len(df)))
    ax.barh(df["ticker"][::-1], df["peso"][::-1] * 100, color=colors[::-1])
    ax.set_xlabel("Peso (%)")
    ax.set_title(titulo)
    ax.grid(True, axis="x", alpha=0.3)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return True


def plot_cumulative_and_drawdown(pf_rets, benchmark_rets, out_path, label_pf="Portafolio",
                                  label_bm="Benchmark"):
    """Grafica retorno acumulado y drawdown."""
    plt = _ensure_matplotlib()
    pf_cum = (1 + pf_rets).cumprod()
    pf_dd = (pf_cum / pf_cum.cummax()) - 1

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})

    axes[0].plot(pf_cum.index, pf_cum, label=label_pf, linewidth=2)
    if benchmark_rets is not None and not benchmark_rets.empty:
        bm_cum = (1 + benchmark_rets).cumprod()
        axes[0].plot(bm_cum.index, bm_cum, label=label_bm, alpha=0.7)
    axes[0].set_ylabel("Retorno acumulado")
    axes[0].set_title("Backtest Out-of-Sample")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].fill_between(pf_dd.index, pf_dd * 100, 0, color="red", alpha=0.3)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Fecha")
    axes[1].grid(True, alpha=0.3)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return True
