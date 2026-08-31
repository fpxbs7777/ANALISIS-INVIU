# -*- coding: utf-8 -*-
"""Estrategias: Hedger beta-neutral (recicla Labadie capm.Hedger) + overlays."""
import numpy as np
import pandas as pd

try:
    import scipy.optimize as op
    import scipy.stats as st
except Exception:
    op = st = None


def _beta(bench_ret, sec_ret):
    df = pd.concat([bench_ret, sec_ret], axis=1, join="inner").dropna()
    if len(df) < 60:
        return None
    df.columns = ["bench", "sec"]
    slope, _, _, _, _ = st.linregress(df["bench"].values, df["sec"].values)
    return float(slope)


def hedger_pesos(close_df, benchmark="SPY", posicion_ticker=None,
                 posicion_delta=1_000_000, universo_hedge=None,
                 regularisation=0):
    rets = np.log(close_df / close_df.shift(1)).dropna()
    if benchmark not in rets.columns or posicion_ticker not in rets.columns:
        return None
    if universo_hedge is None:
        universo_hedge = [c for c in rets.columns if c not in (benchmark, posicion_ticker)][:6]
    bench_ret = rets[benchmark]
    pos_beta = _beta(bench_ret, rets[posicion_ticker])
    if pos_beta is None:
        return None
    hedge_betas = []
    valid = []
    for h in universo_hedge:
        b = _beta(bench_ret, rets[h])
        if b is not None:
            hedge_betas.append(b)
            valid.append(h)
    if len(valid) < 2:
        return None

    def cost(x, betas, td, tb, reg):
        return (np.sum(x) + td) ** 2 + (np.dot(betas, x) + tb) ** 2 + reg * np.sum(x ** 2)

    pos_beta_usd = pos_beta * posicion_delta
    betas = np.array(hedge_betas)
    x0 = np.array([-posicion_delta / len(valid)] * len(valid))
    res = op.minimize(cost, x0, args=(betas, posicion_delta, pos_beta_usd, regularisation))
    hedge_pesos = dict(zip(valid, res.x))
    return {"posicion": posicion_ticker, "pos_beta": round(pos_beta, 3),
            "pos_beta_usd": round(pos_beta_usd, 2),
            "hedge_pesos": {k: round(float(v), 2) for k, v in hedge_pesos.items()},
            "hedge_beta_usd": round(float(np.dot(betas, res.x)), 2)}


def ordenes_desde_pesos(pesos, precios, capital=1_000_000):
    filas = []
    for t, w in pesos.items():
        if w < 1e-4:
            continue
        px = float(precios.get(t, 0)) if isinstance(precios, dict) else 0
        if px <= 0:
            continue
        monto = capital * w
        qty = int(monto // px)
        filas.append({"ticker": t, "peso": round(w, 4), "precio": px,
                      "qty": qty, "monto": round(qty * px, 2)})
    return filas
