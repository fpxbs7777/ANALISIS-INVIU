# -*- coding: utf-8 -*-
"""Motor intermarket: ratios Murphy, fase Pring/Murphy, credito y VIX.

Destilado de coronar bases/intermarket_cycle_detector.py v3.0 para operar
dentro de un scanner continuo ligero.
"""
import numpy as np
import pandas as pd
import yfinance as yf


PHASE_PROFILES = [
    {"num": 0, "name": "Recession Bottom", "b": 1, "s": -1, "c": -1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Bonos suben anticipando recorte. Stocks y commod caen.",
     "clave": "Bonos largos, Utilities, Staples, Salud, Oro"},
    {"num": 1, "name": "Early Recovery", "b": 1, "s": 1, "c": -1,
     "xly_xlp": 1, "iwm_spy": 1, "qqq_spy": 1,
     "desc": "Bonos y stocks suben. Commod debiles. Small caps lideran.",
     "clave": "Tech, Discrecional, Small Caps, Finanzas"},
    {"num": 2, "name": "Mid Expansion", "b": 0, "s": 1, "c": 1,
     "xly_xlp": 1, "iwm_spy": 0, "qqq_spy": 0,
     "desc": "Stocks fuertes, comm suben, bonos laterales.",
     "clave": "Industrial, Materiales, Finanzas, Cobre, Energia"},
    {"num": 3, "name": "Late Expansion", "b": -1, "s": 1, "c": 1,
     "xly_xlp": 0, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Bonos caen (inflacion). Comm fuertes. Mercado angosto.",
     "clave": "Energia, Oro, Agricultura, Salud, Utilities"},
    {"num": 4, "name": "Early Contraction", "b": 0, "s": -1, "c": 1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Stocks caen, comm aun firmes. Bonos rebotan.",
     "clave": "Salud, Staples, Utilities, Oro, Bonos largos"},
    {"num": 5, "name": "Full Contraction", "b": 1, "s": -1, "c": -1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Todo cae excepto bonos largos. Cash.",
     "clave": "Bonos largos, Oro, Cash, VIX"},
]

SECTOR_ROTATION = {
    0: {"nombre": "RECESSION BOTTOM", "ico": "*",
        "comprar": ["TLT/IEF (Bonos largos)", "XLU", "XLP", "XLV", "GLD", "BIL"],
        "vender": ["XLK", "XLY", "XLE", "XLF"], "estilo": "Value defensivo"},
    1: {"nombre": "EARLY RECOVERY", "ico": "+",
        "comprar": ["XLK", "XLY", "IWM", "XLF", "QQQ"],
        "vender": ["XLP", "XLU", "TLT"], "estilo": "Growth / Small Cap / Momentum"},
    2: {"nombre": "MID EXPANSION", "ico": "+",
        "comprar": ["XLI", "XLB", "XLF", "COPX/JJC", "XLE"],
        "vender": ["TLT", "XLU", "XLP"], "estilo": "Ciclico Industrial / Value"},
    3: {"nombre": "LATE EXPANSION", "ico": "~",
        "comprar": ["XLE", "GLD", "DBA", "XLV", "XLU", "BIL/SGOV"],
        "vender": ["XLK", "XLY", "IWM", "LQD", "HYG"],
        "estilo": "Commodities / Cobertura inflacion"},
    4: {"nombre": "EARLY CONTRACTION", "ico": "-",
        "comprar": ["XLV", "XLP", "XLU", "GLD", "TLT", "BIL"],
        "vender": ["XLK", "XLY", "XLE", "XLB", "HYG"], "estilo": "Defensivo / Cash"},
    5: {"nombre": "FULL CONTRACTION", "ico": "--",
        "comprar": ["TLT/IEF", "GLD", "BIL/SHV", "VIX (hedge)"],
        "vender": ["Todo riesgo"], "estilo": "Cash / Bonos / Vol"},
}


def descargar(tickers, period=None, start=None):
    raw = yf.download(sorted(set(tickers)), period=period, start=start,
                      progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
    close.columns = [str(c).strip() for c in close.columns]
    return close


def trend_num(serie, roc_umbral=2.0, lb=252):
    s = serie.dropna()
    if len(s) < 60:
        return None, None
    s = s.tail(min(lb, len(s)))
    x = np.arange(len(s))
    slope = np.polyfit(x, s.values, 1)[0]
    chg = (s.iloc[-1] / s.iloc[0] - 1) * 100
    if slope > 0 and chg > roc_umbral:
        return 1, chg
    if slope < 0 and chg < -roc_umbral:
        return -1, chg
    return 0, chg


def cruz_ma(serie, fast=50, slow=200):
    s = serie.dropna()
    if len(s) < slow + 5:
        return "insuf", False
    mf = s.rolling(fast, min_periods=max(fast // 2, 10)).mean()
    ms = s.rolling(slow, min_periods=max(slow // 2, 30)).mean()
    estado = "alcista" if mf.iloc[-1] > ms.iloc[-1] else (
        "bajista" if mf.iloc[-1] < ms.iloc[-1] else "neutro")
    prev = "alcista" if mf.iloc[-2] > ms.iloc[-2] else (
        "bajista" if mf.iloc[-2] < ms.iloc[-2] else "neutro")
    return estado, (estado != prev)


def evaluar_ratios(close_df, ratios_cfg, roc_umbral, fast, slow):
    out = []
    for r in ratios_cfg:
        num, den = r["num"], r["den"]
        if num not in close_df.columns or den not in close_df.columns:
            continue
        ratio = (close_df[num] / close_df[den]).dropna()
        tend, roc63 = trend_num(ratio.tail(63), roc_umbral, lb=63)
        estado, nuevo = cruz_ma(ratio, fast, slow)
        out.append({**r, "tend": tend, "roc63": round(roc63, 2) if roc63 is not None else None,
                    "ma": estado, "nuevo_cruce": nuevo})
    return out


def detectar_fase(b, s, c, extras):
    current = {"b": b or 0, "s": s or 0, "c": c or 0}
    for k in ("xly_xlp", "iwm_spy", "qqq_spy"):
        current[k] = (extras.get(k) or 0)
    best, best_dist = None, 999.0
    for p in PHASE_PROFILES:
        dist = ok = tot = 0.0
        for key, val in current.items():
            if key in p and isinstance(p[key], int):
                tot += 1
                ex = p[key]
                match = (val == ex) or (ex == 0 and abs(val) <= 1) or (val == 0 and abs(ex) <= 1)
                if match:
                    ok += 1
                    dist += abs(val - ex) * 0.3
                else:
                    dist += abs(val - ex)
        avg = dist / tot if tot else 99
        if avg < best_dist:
            best_dist = avg
            pct = ok / tot * 100 if tot else 0
            conf = ("ALTA" if pct >= 80 else "MEDIA" if pct >= 60 else
                    "BAJA" if pct >= 40 else "MUY BAJA")
            best = {"num": p["num"], "name": p["name"], "conf": conf,
                    "match_pct": round(pct), "desc": p["desc"], "clave": p["clave"]}
    return best


def credito(close_credit, warn, critical, stress):
    res = {}
    pairs = {"IG": ("LQD", "IEF"), "HY": ("HYG", "IEF")}
    for k, (a, b_) in pairs.items():
        if a not in close_credit.columns or b_ not in close_credit.columns:
            res[k] = None
            continue
        proxy = (close_credit[a] / close_credit[b_]).dropna()
        if len(proxy) < 100:
            res[k] = None
            continue
        val = proxy.iloc[-1]
        pct = float((proxy[proxy <= val].count() / len(proxy)) * 100)
        nivel = "OK"
        if pct >= critical:
            nivel = "ALERTA_COMPLACENCIA"
        elif pct >= warn:
            nivel = "WARN_COMPLACENCIA"
        elif pct <= stress:
            nivel = "ALERTA_ESTRES"
        res[k] = {"pct": round(pct, 1), "valor": round(float(val), 4), "nivel": nivel}
    return res


def vix_regime(close_main, warn, alert):
    col = next((c for c in close_main.columns if "VIX" in c.upper()), None)
    if col is None:
        return None
    s = close_main[col].dropna()
    if s.empty:
        return None
    val = float(s.iloc[-1])
    nivel = "OK"
    if val >= alert:
        nivel = "ALERTA_RIESGO"
    elif val >= warn:
        nivel = "WARN"
    z = float((val - s.tail(252).mean()) / max(1e-9, s.tail(252).std()))
    return {"valor": round(val, 2), "z252": round(z, 2), "nivel": nivel}
