# -*- coding: utf-8 -*-
"""Salud hibrida 50/50: fundamental (yfinance.info) + cuantitativo (Distribution).

Salida: DataFrame con score_salud[0..1], rank y diagnostico por ticker.
"""
import numpy as np
import pandas as pd
import yfinance as yf

try:
    import scipy.stats as st
except Exception:
    st = None


def _score_fundamental(info):
    if not info:
        return 0.0, {}
    roe = info.get("returnOnEquity")
    margen = info.get("profitMargins")
    de = info.get("debtToEquity")
    fcf = info.get("freeCashflow")
    rev_g = info.get("revenueGrowth")
    pts = 0
    tot = 5
    det = {}
    try:
        det["roe"] = roe
        pts += 1 if roe is not None and roe > 0.12 else 0
    except Exception:
        det["roe"] = None
    try:
        det["margen"] = margen
        pts += 1 if margen is not None and margen > 0.08 else 0
    except Exception:
        det["margen"] = None
    try:
        det["de"] = de
        pts += 1 if de is not None and de < 100 else 0  # yfinance D/E en %
    except Exception:
        det["de"] = None
    try:
        det["fcf"] = fcf
        pts += 1 if fcf is not None and fcf > 0 else 0
    except Exception:
        det["fcf"] = None
    try:
        det["rev_g"] = rev_g
        pts += 1 if rev_g is not None and rev_g > 0.05 else 0
    except Exception:
        det["rev_g"] = None
    return pts / tot, det


def _score_cuant(serie_ret):
    v = pd.Series(serie_ret).dropna().values
    if len(v) < 60:
        return 0.0, {}
    mean_a = np.mean(v) * 252
    vol_a = np.std(v) * (252 ** 0.5)
    sharpe = mean_a / vol_a if vol_a > 0 else 0
    var95 = float(np.percentile(v, 5))
    # Sharpe normalizado 0..1 con sigmoide suave
    s_sharpe = 1 / (1 + np.exp(-sharpe))  # 0.5 en sharpe 0, ~0.73 en 1
    # VaR: menos negativo es mejor
    s_var = 1 / (1 + np.exp(var95 * 50))
    # skewness positivo leve premio
    skew = float(st.skew(v)) if st else 0
    s_skew = 0.5 + np.clip(skew / 4, -0.3, 0.3)
    score = 0.5 * s_sharpe + 0.3 * s_var + 0.2 * s_skew
    return float(np.clip(score, 0, 1)), {"sharpe": round(float(sharpe), 3),
                                          "var95": round(float(var95), 4),
                                          "skew": round(float(skew), 2)}


def scoring(close_df, peso_fund=0.5, peso_cuant=0.5):
    rets = np.log(close_df / close_df.shift(1))
    filas = []
    for col in close_df.columns:
        serie = rets[col].dropna()
        s_cuant, det_c = _score_cuant(serie)
        try:
            info = yf.Ticker(col).info
        except Exception:
            info = {}
        s_fund, det_f = _score_fundamental(info)
        score = peso_fund * s_fund + peso_cuant * s_cuant
        filas.append({"ticker": col, "score_salud": round(float(score), 3),
                      "s_fund": round(float(s_fund), 3),
                      "s_cuant": round(float(s_cuant), 3),
                      **{k: v for k, v in det_f.items()},
                      **{k: v for k, v in det_c.items()}})
    df = pd.DataFrame(filas).sort_values("score_salud", ascending=False)
    df["rank_salud"] = range(1, len(df) + 1)
    return df
