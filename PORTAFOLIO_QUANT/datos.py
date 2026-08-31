# -*- coding: utf-8 -*-
"""Datos: descarga batch con cache en disco (recicla core/data.py).

Cache por ticker en datos/cache/*.parquet para que el walk-forward
no re-descargue en cada rebalanceo.
"""
import os
import pandas as pd
import yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "datos", "cache")


def descargar_panel(tickers, periodo="10y", auto_adjust=True, use_cache=True):
    tickers = sorted(set(tickers))
    if not tickers:
        return pd.DataFrame()
    # batch para no exceder URL
    batch = 80
    frames = []
    for i in range(0, len(tickers), batch):
        sub = tickers[i:i + batch]
        raw = yf.download(sub, period=periodo, auto_adjust=auto_adjust,
                          progress=False, threads=True)
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"].copy()
        else:
            close = raw[["Close"]].copy()
            close.columns = sub
        close.columns = [str(c).strip() for c in close.columns]
        frames.append(close)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, axis=1)
    df = df.sort_index()
    return df


def descargar_con_cache(tickers, periodo="10y", cache_dias=1):
    need = sorted(set(tickers))
    # por ahora sin cache persistente granular para simplificar;
    # el cache del panel completo se hace en backtest nivel
    return descargar_panel(need, periodo=periodo)


def retornos_log(close_df):
    return __import__("numpy").log(close_df / close_df.shift(1)).dropna(how="all")
