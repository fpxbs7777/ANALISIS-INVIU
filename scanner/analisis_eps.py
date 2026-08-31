# -*- coding: utf-8 -*-
"""Análisis cuantitativo del EPS: tendencia, comparación sectorial y calidad.

Definiciones (citadas en README):
- EPS = (beneficio neto − dividendos preferentes) / acciones ordinarias
- EPS diluido = incluye opciones/bonos convertibles → usafila 'Diluted EPS'
Metodología: Fowler Newton cap.5 + Biondi cap.5.
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

CACHE_PATH = os.path.join(os.path.dirname(__file__), "estado", "cache_eps.json")


def _con_timeout(fn, s=20):
    r = {}

    def w():
        try:
            r["data"] = fn()
        except Exception as e:
            r["error"] = e

    t = threading.Thread(target=w, daemon=True)
    t.start()
    t.join(s)
    if t.is_alive():
        raise TimeoutError
    if "error" in r:
        raise r["error"]
    return r.get("data")


def eps_ticker(ticker):
    t = yf.Ticker(ticker)
    try:
        inc = _con_timeout(lambda: t.income_stmt, 20)
        qinc = _con_timeout(lambda: t.quarterly_income_stmt, 15)
    except Exception:
        inc = qinc = None

    def fila(df, nombres):
        if df is None or getattr(df, "empty", True):
            return None
        for n in nombres:
            if n in df.index:
                for col in df.columns:
                    try:
                        v = float(df.loc[n, col])
                        if not pd.isna(v):
                            return v
                    except Exception:
                        continue
        return None

    def serie_eps(df, n=8):
        if df is None or getattr(df, "empty", True):
            return None
        for nombre in ["Diluted EPS", "Basic EPS"]:
            if nombre in df.index:
                s = df.loc[nombre].dropna().astype(float)
                s.index = pd.to_datetime(s.index)
                s = s.sort_index()
                if len(s) >= 2:
                    return s.tail(n)
        return None

    annual = serie_eps(inc, 4)
    trim = serie_eps(qinc, 8)
    # YoY trimestral y CAGR anual
    yoy = None
    if trim is not None and len(trim) >= 5:
        try:
            yoy = (trim.iloc[-1] - trim.iloc[-5]) / abs(trim.iloc[-5]) * 100 if trim.iloc[-5] else None
            yoy = round(float(yoy), 1) if yoy is not None and not pd.isna(yoy) else None
        except Exception:
            pass
    cagr = None
    if annual is not None and len(annual) >= 2 and annual.iloc[0] and annual.iloc[0] > 0 and annual.iloc[-1] > 0:
        try:
            cagr = ((annual.iloc[-1] / annual.iloc[0]) ** (1 / (len(annual) - 1)) - 1) * 100
            cagr = round(float(cagr), 1)
        except Exception:
            pass
    tendencia = None
    if trim is not None and len(trim) >= 4:
        x = range(len(trim))
        pend = float(pd.Series(trim.values).diff().mean())
        tendencia = "📈 creciente" if pend > 0.02 else "📉 declinante" if pend < -0.02 else "➡️ estable"
    try:
        info = _con_timeout(lambda: t.info, 12) or {}
        trail = info.get("trailingEps")
        fwd = info.get("forwardEps")
    except Exception:
        trail = fwd = None
    return {
        "ticker": ticker,
        "eps_dil_ttm": round(float(trim.tail(4).sum()), 2) if trim is not None and len(trim) >= 4 else trail,
        "eps_basic_ttm": None,
        "eps_forward": fwd,
        "yoy_trim": yoy,
        "cagr_anual": cagr,
        "tendencia": tendencia,
        "n_trim": int(len(trim)) if trim is not None else 0,
    }


def buscar_pares(ticker, unificado_path=None):
    """Pares del mismo sector+industria en unificado_completo - copia.json."""
    path = unificado_path or os.path.join(ROOT, "unificado_completo - copia.json")
    try:
        with open(path, encoding="utf-8") as f:
            u = json.load(f)
    except Exception:
        return [], None, None
    import re
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
        return "".join(c for c in s.lower() if c.isalnum())

    # agrupar por sector/industria normalizados (fusiona duplicados ES/EN)
    grupos = {}  # (sec_norm, ind_norm) -> {tickers}
    representante = {}  # (sec_norm, ind_norm) -> (sec, ind) primer visto
    idx = {}  # ticker_norm -> (sec_norm, ind_norm)
    for sec, sv in u.get("sectores", {}).items():
        for ind, acts in sv.get("industrias", {}).items():
            key = (norm(sec), norm(ind))
            if key not in representante:
                representante[key] = (sec, ind)
            for a in acts:
                raw = str(a.get("ticker", "")).upper()
                # subyacente: quita .BA y sufijo D de cedear USD si existe base sin D
                base = raw.replace(".BA", "")
                if base.endswith("D") and len(base) > 1:
                    base = base[:-1]
                tk = base
                if 1 <= len(tk) <= 6 and re.match(r"^[A-Z][A-Z0-9.\-]*$", tk):
                    # filtra basura con numeros (PETR3) y rarezas
                    if any(c.isdigit() for c in tk):
                        continue
                    grupos.setdefault(key, set()).add(tk)
                    idx[norm(tk)] = key
    tk_norm = norm(ticker)
    key = idx.get(tk_norm)
    if not key:
        return [], None, None
    sec, ind = representante[key]
    candidatos = sorted(p for p in grupos.get(key, set()) if p != ticker.upper())
    # prioriza tickers que existen en yfinance (alfabético corto primero)
    candidatos = [c for c in candidatos if 1 <= len(c) <= 5 and c.isalpha()]
    return candidatos[:10], sec, ind


def comparar_sectorial(ticker, pares):
    """Rank del ticker entre sus pares por EPS diluido TTM."""
    # solo 3 pares para no saturar API; filtra a tickers reales
    pares = [p for p in pares if 1 <= len(p) <= 5 and p.isalpha()][:3]
    vals = {}
    for tk in [ticker] + pares:
        try:
            eps = eps_ticker(tk)
            vals[tk] = eps.get("eps_dil_ttm") if eps else None
        except Exception:
            vals[tk] = None
    orden = sorted([(k, v) for k, v in vals.items() if v is not None], key=lambda kv: kv[1], reverse=True)
    pos = next((i + 1 for i, (k, _) in enumerate(orden) if k.upper() == ticker.upper()), None)
    total = len(orden)
    return {"rank": pos, "total": total, "vals": vals}


CACHE_TTL_H = 24


def _cache_get():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            c = json.load(f)
        if datetime.fromisoformat(c.get("_ts", "2000-01-01")) + timedelta(hours=CACHE_TTL_H) < datetime.now():
            return {}
        return c.get("data", {})
    except Exception:
        return {}


def _cache_put(data):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"_ts": datetime.now().isoformat(), "data": data}, f, indent=1, default=str)


def ejecutar(universo, incluir_pares=True):
    cache = _cache_get()
    out = []
    for tk in universo[:40]:
        if tk in cache:
            out.append(cache[tk])
            continue
        eps = eps_ticker(tk)
        if incluir_pares:
            pares, sec, ind = buscar_pares(tk)
            cmp = comparar_sectorial(tk, pares) if pares else {"rank": None, "total": 0}
            eps["pares"] = pares[:5]
            eps["sector"] = sec
            eps["industria"] = ind
            eps["rank_pares"] = cmp["rank"]
            eps["total_pares"] = cmp["total"]
        cache[tk] = eps
        out.append(eps)
    _cache_put(cache)
    return out


def formatear(lista):
    if not lista:
        return "Sin datos EPS para el universo."
    lineas = ["*ANÁLISIS EPS* — cuantitativo", "EPS = (benef. neto − div. pref.) / acciones ordinarias; EPS diluido incluye dilución.\n"]
    for r in lista[:15]:
        lineas.append(
            "*%s* EPS dil TTM %.2f · YoY %s%% · CAGR %s%% · %s · rank %s/%s en *%s*"
            % (r["ticker"], r.get("eps_dil_ttm") or 0, r.get("yoy_trim") if r.get("yoy_trim") is not None else "—",
               r.get("cagr_anual") if r.get("cagr_anual") is not None else "—",
               r.get("tendencia") or "—", r.get("rank_pares") or "—", r.get("total_pares") or "—",
               r.get("industria") or "—"))
    lineas.append("\n_Ajustes por calidad_: el EPS diluido es el estándar conservador; normalización total (excluir extraordinarios) no disponible en fuente gratuita — ver limitación en README (Fowler Newton cap.5)._")
    return "\n".join(lineas)
