# -*- coding: utf-8 -*-
"""Calendario de earnings: proxima fecha + acierto/sorp historicos.

Fuente: yfinance Ticker.earnings_dates (8T) y Ticker.calendar.
Metodologia: acierto% = beats/8 (Reported>=Estimate), sorp media.
Fundamento: PEAD Ball & Brown 1968.
"""
import json
import os
import sys
import threading
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CFG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "estado", "cache_earnings.json")


def _con_timeout(fn, segundos=20):
    res = {}

    def w():
        try:
            res["data"] = fn()
        except Exception as e:
            res["error"] = e

    t = threading.Thread(target=w, daemon=True)
    t.start()
    t.join(segundos)
    if t.is_alive():
        raise TimeoutError
    if "error" in res:
        raise res["error"]
    return res.get("data")


def _cargar_cache(ttl_h=12):
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            c = json.load(f)
        ts = datetime.fromisoformat(c.get("_ts", "2000-01-01"))
        if datetime.now() - ts > timedelta(hours=ttl_h):
            return {}
        return c.get("data", {})
    except Exception:
        return {}


def _guardar_cache(data):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"_ts": datetime.now().isoformat(), "data": data}, f, indent=1, default=str)


def earnings_ticker(ticker, n_hist=8):
    try:
        ed = _con_timeout(lambda: yf.Ticker(ticker).earnings_dates, 20)
        cal = None
        try:
            cal = _con_timeout(lambda: yf.Ticker(ticker).calendar, 15)
        except Exception:
            pass
    except Exception:
        return None
    if ed is None or ed.empty:
        return None
    ed = ed.copy()
    proxima = None
    hora = None
    # futuras tienen Reported NaN y fecha > hoy
    ahora = pd.Timestamp.now(tz=ed.index.tz) if ed.index.tz else pd.Timestamp.now()
    futuras = ed[ed["Reported EPS"].isna() & (ed.index > ahora - pd.Timedelta(days=1))]
    if not futuras.empty:
        proxima = futuras.index.min()
        try:
            hora = proxima.tz_convert("US/Eastern").hour if proxima.tz else proxima.hour
        except Exception:
            hora = None
    elif cal and isinstance(cal, dict) and cal.get("Earnings Date"):
        try:
            proxima = pd.Timestamp(cal["Earnings Date"][0])
        except Exception:
            pass
    # historico: ultimos n con Reported no NaN
    hist = ed[ed["Reported EPS"].notna()].head(n_hist)
    if hist.empty:
        acierto = sorp = None
        semaforo = "⚪"
    else:
        beats = (hist["Reported EPS"] >= hist["EPS Estimate"]).sum()
        acierto = round(beats / len(hist) * 100, 0)
        sorp = round(hist["Surprise(%)"].mean(), 1) if "Surprise(%)" in hist.columns else None
        if acierto >= 75 and (sorp or 0) > 0:
            semaforo = "🟩"
        elif acierto >= 50:
            semaforo = "⚪"
        else:
            semaforo = "🟥"
    # market cap
    try:
        mc = _con_timeout(lambda: yf.Ticker(ticker).info.get("marketCap"), 8)
        mcap_b = round(float(mc) / 1e9, 0) if mc else None
    except Exception:
        mcap_b = None
    # hora -> emoji BMO/AMC
    momento = "🌅" if hora is not None and hora < 12 else "🌙" if hora is not None else ""
    return {
        "ticker": ticker,
        "proxima": proxima.date() if proxima is not None and hasattr(proxima, "date") else None,
        "hora_et": hora,
        "momento": momento,
        "mcap_b": mcap_b,
        "acierto": acierto,
        "sorp": sorp,
        "semaforo": semaforo,
        "n_hist": int(len(hist)),
    }


def universo_earnings(finalistas=None, watchlist=None):
    """Watchlist = finalistas del screener + portafolio Inviu + config."""
    tickers = set(watchlist or [])
    if finalistas:
        for v in finalistas.values():
            tickers.update(v if isinstance(v, (list, tuple)) else [v])
    # portafolio Inviu (cuentas -> tenencias) — usa subyacente US, filtra bonos
    try:
        with open(os.path.join(ROOT, "portafolios_inviu.json"), encoding="utf-8") as f:
            pf = json.load(f)
        for cuenta in pf.get("cuentas", []):
            for pos in cuenta.get("tenencias", []):
                if pos.get("tipo") == "bono":
                    continue
                tk = pos.get("ticker", "")
                if tk:
                    tk = tk.upper().replace(".BA", "").replace(".D", "")
                    if tk and tk.replace("-", "").isalnum():
                        tickers.add(tk)
    except Exception:
        pass
    # config watchlist_extra
    try:
        import json as _j
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = _j.load(f)
        tickers.update(cfg.get("watchlist_extra", []))
    except Exception:
        pass
    # solo tickers de 1-5 letras (evita basura)
    return sorted(t for t in tickers if 1 <= len(t) <= 6 and t.replace("-", "").replace(".", "").isalnum())


def ejecutar(dias=7, universo=None):
    cfg = {}
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        dias = cfg.get("earnings", {}).get("dias_adelante", dias)
    except Exception:
        pass
    if universo is None:
        universo = universo_earnings()
    cache = _cargar_cache(cfg.get("earnings", {}).get("ttl_horas", 12))
    hoy = datetime.now().date()
    hasta = hoy + timedelta(days=dias)
    filas = []
    for tk in universo[:60]:  # limite 60 para no saturar
        if tk in cache:
            filas.append(cache[tk])
            continue
        info = earnings_ticker(tk)
        if info and info["proxima"] and hoy <= info["proxima"] <= hasta:
            filas.append(info)
            cache[tk] = info
    _guardar_cache(cache)
    filas.sort(key=lambda r: r["proxima"] or hoy)
    return filas


def formatear(filas):
    if not filas:
        return "Sin earnings en los próximos 7 días para el universo seguido."
    por_dia = {}
    for r in filas:
        por_dia.setdefault(str(r["proxima"]), []).append(r)
    lineas = ["*EARNINGS · próximos 7 días*  _%s_" % datetime.now().strftime("%d/%m"),
              "🟩 beat ≥75% · ⚪ 50-74% · 🟥 <50%  — educativo, no recomendación. Fuente: Yahoo Finance\n"]
    for dia, lst in sorted(por_dia.items()):
        lineas.append("— *%s* —" % dia)
        for r in lst:
            lineas.append("%s *%s* · %sB · %s %s  acierto %s%% · sorp %s%%" % (
                r["semaforo"], r["ticker"], r["mcap_b"] or "—", r["momento"] or "—",
                r["proxima"], int(r["acierto"]) if r["acierto"] is not None else "—",
                r["sorp"] if r["sorp"] is not None else "—"))
    return "\n".join(lineas)
