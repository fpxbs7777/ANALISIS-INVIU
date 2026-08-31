# -*- coding: utf-8 -*-
"""Optimizador refactorizado de OPTIMIZADOR UNIFICADO.txt.

Sin matplotlib en modo headless; expone construir_carteras(pool_df).
"""
import numpy as np
import pandas as pd

try:
    import scipy.optimize as op
    import scipy.stats as st
except Exception:
    op = st = None


def _var(w, cov):
    return float(w @ cov @ w)


def construir_carteras(close_df, tipos=None, max_peso=0.25, top_n=30):
    if tipos is None:
        tipos = ["long-only", "equi-weight", "volatility-weighted", "markowitz"]
    rets = np.log(close_df / close_df.shift(1)).dropna(how="all")
    if top_n and len(rets.columns) > top_n:
        # pre-filtro por Sharpe
        sharpe = (rets.mean() * 252) / (rets.std() * (252 ** 0.5)).replace(0, 1)
        keep = sharpe.sort_values(ascending=False).head(top_n).index.tolist()
        rets = rets[keep]
    cols = list(rets.columns)
    cov = np.cov(rets.values, rowvar=False) * 252
    mean = rets.mean().values * 252
    vol = rets.std().values * (252 ** 0.5)
    n = len(cols)
    carteras = {}
    for tipo in tipos:
        x0 = np.array([1 / n] * n)
        w = x0.copy()
        try:
            if tipo == "min-variance-l1":
                res = op.minimize(_var, x0, args=(cov,),
                                  constraints=[{"type": "eq", "fun": lambda x: np.sum(np.abs(x)) - 1}],
                                  method="SLSQP")
                w = res.x
            elif tipo == "long-only":
                res = op.minimize(_var, x0, args=(cov,),
                                  constraints=[{"type": "eq", "fun": lambda x: np.sum(np.abs(x)) - 1}],
                                  bounds=[(0, max_peso)] * n, method="SLSQP")
                w = res.x
            elif tipo == "markowitz":
                tr = float(np.mean(mean))
                res = op.minimize(_var, x0, args=(cov,),
                                  constraints=[{"type": "eq", "fun": lambda x: np.sum(np.abs(x)) - 1},
                                               {"type": "eq", "fun": lambda x, r=tr: mean @ x - r}],
                                  bounds=[(0, max_peso)] * n, method="SLSQP")
                w = res.x
            elif tipo == "volatility-weighted":
                w = 1 / np.where(vol > 0, vol, 1)
            # equi-weight ya es x0
        except Exception:
            w = x0
        w = w / np.sum(np.abs(w)) if np.sum(np.abs(w)) > 0 else x0
        # metrica
        port_ret = (rets.values * w).sum(axis=1)
        ret_a = float(mean @ w)
        vol_a = float(np.sqrt(_var(w, cov)))
        sharpe = ret_a / vol_a if vol_a > 0 else 0
        carteras[tipo] = {"pesos": dict(zip(cols, np.round(w, 4))),
                          "ret": round(ret_a, 4), "vol": round(vol_a, 4),
                          "sharpe": round(sharpe, 3),
                          "serie": pd.Series(port_ret, index=rets.index)}
    return carteras, rets
