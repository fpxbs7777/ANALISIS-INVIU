# -*- coding: utf-8 -*-
"""Eventos/catalizadores: proximos earnings de la watchlist + ratio de acierto.

Reciclado del patron ESTIMACIONES.txt y analisis_nvda_earnings.py.
Cachea por dia en logs/eventos_cache.json para no golpear yfinance en cada scan.
"""
import json
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "logs", "eventos_cache.json")


def _cache_fresco():
    if not os.path.exists(CACHE):
        return None
    try:
        data = json.load(open(CACHE, encoding="utf-8"))
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if data.get("dia") == hoy:
            return data["eventos"]
    except Exception:
        pass
    return None


def _guardar_cache(eventos):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump({"dia": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "eventos": eventos}, open(CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def proximos_eventos(watchlist, dias=10):
    fresco = _cache_fresco()
    if fresco is not None:
        return fresco
    hoy = pd.Timestamp.now(tz="UTC")
    limite = hoy + pd.Timedelta(days=dias)
    eventos = []
    for sim in watchlist:
        try:
            tk = yf.Ticker(sim)
            ed = tk.get_earnings_dates(limit=12)
            if ed is None or ed.empty:
                continue
            futuras = ed[ed.index >= hoy].sort_index()
            if futuras.empty:
                continue
            fecha = futuras.index[0]
            if fecha > limite:
                continue
            eps_est = float(futuras.iloc[0].get("EPS Estimate") or 0) or None
            pasados = ed[ed.index < hoy].dropna(subset=["Reported EPS"]).head(8)
            hit = 0
            if not pasados.empty and "EPS Estimate" in pasados.columns:
                hit = int((pasados["Reported EPS"] > pasados["EPS Estimate"]).sum())
            eventos.append({
                "ticker": sim,
                "fecha": fecha.strftime("%Y-%m-%d"),
                "faltan_dias": int((fecha - hoy).days),
                "eps_est": eps_est,
                "beat_rate_8q": "%d/8" % hit if not pasados.empty else None,
            })
        except Exception:
            continue
    eventos.sort(key=lambda e: e["fecha"])
    _guardar_cache(eventos)
    return eventos
