# -*- coding: utf-8 -*-
"""Factores: regresion CAPM multifactor y filtro por R2.

Recicla la clase CAPM de OPTIMIZADOR UNIFICADO.txt + dataframe_factors de Labadie.
"""
import numpy as np
import pandas as pd

try:
    import scipy.stats as st
except Exception:
    st = None


def _capm(bench_ret, sec_ret):
    df = pd.concat([bench_ret, sec_ret], axis=1, join="inner").dropna()
    if len(df) < 60:
        return None
    df.columns = ["bench", "sec"]
    x, y = df["bench"].values, df["sec"].values
    slope, intercept, r, p, _ = st.linregress(x, y)
    return {"beta": float(slope), "alpha": float(intercept),
            "r": float(r), "r2": float(r ** 2), "p": float(p)}


def factores(close_df, factores_lista, r2_umbral=0.40, ventana=252):
    rets = np.log(close_df / close_df.shift(1)).dropna(how="all")
    factores_disp = [f for f in factores_lista if f in rets.columns]
    if not factores_disp:
        return pd.DataFrame(), {}
    # factor principal por ticker: max R2
    filas = []
    detalle = {}
    for sec in [c for c in rets.columns if c not in factores_lista]:
        best = None
        best_f = None
        for f in factores_disp:
            res = _capm(rets[f].tail(ventana), rets[sec].tail(ventana))
            if res and (best is None or res["r2"] > best["r2"]):
                best, best_f = res, f
        if best:
            detalle[sec] = {"factor": best_f, **best}
            if best["r2"] >= r2_umbral:
                filas.append({"ticker": sec, "factor": best_f, "beta": round(best["beta"], 3),
                              "r2": round(best["r2"], 3), "alpha": round(best["alpha"], 5)})
        else:
            detalle[sec] = None
    df = pd.DataFrame(filas).sort_values("r2", ascending=False) if filas else pd.DataFrame()
    return df, detalle
