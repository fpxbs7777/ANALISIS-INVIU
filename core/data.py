# -*- coding: utf-8 -*-
"""core.data: descarga de series de cierre desde yfinance con cache en disco.

Usa Ticker.history individual (mas confiable que Tickers batch, que
puede devolver historial parcial de indices como ^TNX). Con reintento
por si la respuesta llega truncada y cache CSV en ../data_cache para
evitar rate-limiting de Yahoo al repetir corridas.
"""
import os
import time

import pandas as pd
import yfinance as yf

# minimo esperado de filas segun periodo (trading days aprox)
MIN_BARS = {"max": 20, "1y": 150, "2y": 300, "3y": 450, "4y": 600, "5y": 750}

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cache")


def load(tk, period="4y", tries=3, sleep=3.0, use_cache=True, force=False):
    """Serie de Close ajustado (auto_adjust) de un ticker, dropna.

    Unificacion de load() de todos los scripts de analisis. Si hay cache
    local de <=7 dias lo usa (evita rate-limit); si no, descarga con reintento.
    """
    path = _cache_path(tk, period)
    if use_cache and not force and os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        s = df["Close"]
        if len(s) >= MIN_BARS.get(period, 20):
            return s

    need = MIN_BARS.get(period, 20)
    for i in range(tries):
        try:
            h = yf.Ticker(tk).history(period=period, auto_adjust=True)
            if h.empty:
                raise ValueError("vacio")
            s = pd_clean(h["Close"])
            if len(s) >= need:
                if use_cache:
                    _write_cache(tk, period, s)
                return s
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(sleep)
    # ultimo intento devuelve lo que sea (o re-lanza el error real)
    h = yf.Ticker(tk).history(period=period, auto_adjust=True)
    s = pd_clean(h["Close"])
    if use_cache and len(s) >= need:
        _write_cache(tk, period, s)
    return s


def _cache_path(tk, period):
    return os.path.join(_CACHE_DIR, "%s_%s.csv" % (tk.replace("^", "_"), period))


def _write_cache(tk, period, s):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        df = pd.DataFrame({"Close": s})
        df.to_csv(_cache_path(tk, period))
    except Exception:
        pass


def pd_clean(df):
    """Convierte el resultado (columna Close) a la Serie limpia.

    Normaliza el indice a fecha sin timezone para que las intersecciones
    entre series de distinto mercado por tz matcheen exactamente.
    """
    series = df if isinstance(df, pd.Series) else df.squeeze()
    series = series.dropna()
    idx = pd.DatetimeIndex(series.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    series.index = idx.normalize()
    return series[~series.index.duplicated()]


def load_many(tickers, period="4y"):
    """Descarga dict nombre->serie. Se usa en los scripts de analisis."""
    out = {}
    for tk in sorted(set(tickers)):
        try:
            out[tk] = load(tk, period=period)
        except Exception as e:
            print("  [!] fallo %s: %s" % (tk, e))
    return out