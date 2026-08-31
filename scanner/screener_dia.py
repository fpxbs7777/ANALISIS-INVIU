# -*- coding: utf-8 -*-
"""Screener diario ligero: sectores lideres -> industrias -> ranking por fuerza.

Versión recortada de clientes/rotacion_ciclo_empresas.py: hace ranking
por score + regla_oro/R2 vs ETF, pero NO la comparación 5-bloques pesada.
Exporta resumen_empresas.csv para run_scanner.
"""
import json
import os
import sys
import threading
import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analisis.portafolio.constructor import descargar_precios
from core.ratio import analyze_pair
from core.senales import regla_oro, accion

ETF_SECTOR_YAHOO = {
    "XLE": ("Energia", "energy"), "XLK": ("Tecnologia", "technology"),
    "XLI": ("Industriales", "industrials"), "XLB": ("Materiales", "basic-materials"),
    "XLY": ("Consumo Ciclico", "consumer-cyclical"), "XLP": ("Defensiva", "consumer-defensive"),
    "XLV": ("Salud", "healthcare"), "XLF": ("Financieros", "financial-services"),
    "XLC": ("Comunicacion", "communication-services"), "XLU": ("Utilidades", "utilities"),
    "XLRE": ("Inmobiliario", "real-estate"),
}
EXCHANGES_US = ["NMS", "NGM", "NYQ", "ASE"]


def _con_timeout(fn, segundos=30):
    res = {}

    def worker():
        try:
            res["data"] = fn()
        except Exception as e:
            res["error"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(segundos)
    if t.is_alive():
        raise TimeoutError("timeout %ss" % segundos)
    if "error" in res:
        raise res["error"]
    return res.get("data")


def _variantes_nombre(nombre):
    vs = []
    try:
        vv = EquityQuery.valid_values.fget(EquityQuery)
        inds = vv.get("industry", {})
        lista = set()
        if isinstance(inds, dict):
            for v in inds.values():
                lista.update(v or [])
        elif isinstance(inds, (list, set, tuple)):
            lista.update(inds)

        def norm(s):
            return "".join(c for c in str(s).lower() if c.isalnum())

        obj = norm(nombre)
        for c in lista:
            if norm(c) == obj:
                vs.insert(0, c)
                break
    except Exception:
        pass
    if nombre not in vs:
        vs.append(nombre)
    if " - " in nombre:
        em = nombre.replace(" - ", " \u2014 ")
        if em not in vs:
            vs.append(em)
    return vs


def industrias_de_sector(sector_key, n=4):
    df = _con_timeout(lambda: yf.Sector(sector_key).industries, 40)
    df = df.sort_values("market weight", ascending=False)
    return [(str(r["name"]), float(r["market weight"])) for _, r in df.head(n).iterrows()]


def screener_industria(nombre, max_paginas=2):
    filas, size = [], 250
    for exch in EXCHANGES_US:
        for var in _variantes_nombre(nombre):
            ok = False
            off = 0
            for _ in range(max_paginas):
                try:
                    q = EquityQuery("and", [EquityQuery("eq", ["industry", var]), EquityQuery("eq", ["exchange", exch])])
                    r = _con_timeout(lambda: yf.screen(q, size=size, offset=off), 40)
                    if r is None or len(r) == 0:
                        break
                    if isinstance(r, dict):
                        r = pd.DataFrame([r])
                    if not isinstance(r, pd.DataFrame):
                        break
                    if "quotes" in r.columns:
                        exp = []
                        for _, row in r.iterrows():
                            raw = row["quotes"]
                            try:
                                d = json.loads(raw) if isinstance(raw, str) else (raw or [])
                            except Exception:
                                d = []
                            if isinstance(d, list):
                                exp.extend(d)
                        if not exp:
                            break
                        r = pd.DataFrame(exp)
                    if r.empty:
                        break
                    filas.append(r)
                    ok = True
                    if len(r) < size:
                        break
                    off += size
                    time.sleep(0.3)
                except Exception:
                    break
            if ok:
                break
    if not filas:
        return pd.DataFrame()
    df = pd.concat(filas, ignore_index=True)
    if "symbol" not in df.columns:
        return pd.DataFrame()
    df = df.dropna(subset=["symbol"]).drop_duplicates(subset=["symbol"])
    df["symbol"] = df["symbol"].astype(str)
    df = df[~df["symbol"].str.contains(r"\.", regex=True)]
    if "quoteType" in df.columns:
        df = df[df["quoteType"].astype(str).str.upper() == "EQUITY"]
    if "currency" in df.columns:
        df = df[df["currency"].astype(str).str.upper().eq("USD") | df["currency"].isna()]
    return df


def metricas_ranking(s):
    p = s.dropna()
    if len(p) < 40:
        return None
    out = {"precio": float(p.iloc[-1])}
    for etiqueta, dias in (("r1m", 21), ("r3m", 63), ("r6m", 126)):
        out[etiqueta] = float(p.iloc[-1] / p.iloc[-dias] - 1) * 100 if len(p) > dias else np.nan
    s20, s50 = float(p.rolling(20).mean().iloc[-1]), float(p.rolling(50).mean().iloc[-1])
    s200 = float(p.rolling(200).mean().iloc[-1]) if len(p) >= 200 else np.nan
    if not np.isnan(s200):
        t = 2 if p.iloc[-1] > s50 > s200 else 1 if p.iloc[-1] > s200 else 0
        out["tendencia"] = {2: "ALCISTA", 1: "MIXTA", 0: "BAJISTA"}[t]
    else:
        t = 1 if p.iloc[-1] > s50 else 0
        out["tendencia"] = "ALCISTA" if t else "BAJISTA"
    out["_tend_pts"] = t
    d = p.pct_change()
    out["vol60"] = float(d.iloc[-60:].std() * np.sqrt(252))
    delta = p.diff()
    g = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    l = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    out["rsi14"] = float((100 - 100 / (1 + rs)).iloc[-1])
    return out


def r2_vs_benchmark(a, b):
    idx = a.index.intersection(b.index)
    if len(idx) < 30:
        return None
    ca = a.loc[idx].pct_change().dropna()
    cb = b.loc[idx].pct_change().dropna()
    ci = ca.index.intersection(cb.index)
    if len(ci) < 30:
        return None
    ca, cb = ca.loc[ci], cb.loc[ci]
    corr = float(ca.corr(cb))
    varb = float(cb.var())
    beta = float(ca.cov(cb) / varb) if varb else np.nan
    return {"r2": corr ** 2, "corr": corr, "beta": beta}


def cargar_mapa_cedear(path=None):
    path = path or os.path.join(ROOT, "unificado_completo - copia.json")
    mapa = {}
    try:
        with open(path, encoding="utf-8") as f:
            u = json.load(f)
        for sv in u.get("sectores", {}).values():
            for acts in sv.get("industrias", {}).values():
                for a in acts:
                    if a.get("tipo") == "cedear":
                        tk = str(a.get("ticker", "")).upper().replace(".BA", "")
                        if tk and tk not in mapa:
                            mapa[tk] = tk + ".BA"
        for a in u.get("adrsArgentina", {}).get("lista", []):
            if a.get("ticker") and a.get("bcba"):
                mapa[str(a["ticker"]).upper()] = a["bcba"]
    except Exception:
        pass
    return mapa


def ejecutar(liderazgo, top_sectores=3, top_industrias=4, mcap_min=5e9,
            candidatos_por_ind=10, periodo="1y", verbose=True):
    top_etfs = list(liderazgo.keys())[:top_sectores]
    candidatos = []
    for etf in top_etfs:
        nom, key = ETF_SECTOR_YAHOO[etf]
        if verbose:
            print("  %s | %s" % (etf, nom))
        try:
            inds = industrias_de_sector(key, n=top_industrias)
        except Exception as e:
            print("    ! industrias: %s" % e)
            continue
        for nombre_ind, peso in inds:
            if verbose:
                print("    %s (%.1f%%)" % (nombre_ind, peso * 100))
            df = screener_industria(nombre_ind)
            if df.empty:
                continue
            if "marketCap" in df.columns:
                df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
                df = df[df["marketCap"] >= mcap_min]
            df = df.sort_values("marketCap", ascending=False).head(candidatos_por_ind)
            for _, r in df.iterrows():
                candidatos.append({
                    "ticker": r["symbol"], "nombre": r.get("shortName") or r.get("longName") or r["symbol"],
                    "sector_etf": etf, "sector": nom, "industria": nombre_ind,
                    "peso_industria": peso,
                    "mcap_B": round(float(r["marketCap"]) / 1e9, 1) if pd.notna(r.get("marketCap")) else None,
                })
    tickers = sorted({c["ticker"] for c in candidatos} | set(top_etfs) | {"SPY"})
    precios = {}
    for i in range(0, len(tickers), 40):
        precios.update(descargar_precios(tickers[i:i + 40], period=periodo))
    spy = precios.get("SPY")
    mapa = cargar_mapa_cedear()
    filas = []
    for c in candidatos:
        s = precios.get(c["ticker"])
        m = metricas_ranking(s) if s is not None else None
        if m is None:
            continue
        ex6 = m["r6m"] - float(spy.iloc[-1] / spy.iloc[-126] - 1) * 100 if spy is not None and len(spy) > 126 and not np.isnan(m["r6m"]) else np.nan
        ex3 = m["r3m"] - float(spy.iloc[-1] / spy.iloc[-63] - 1) * 100 if spy is not None and len(spy) > 63 and not np.isnan(m["r3m"]) else np.nan
        score = 0.45 * ex6 + 0.35 * ex3 + 0.20 * m["_tend_pts"] if not np.isnan(ex6) else np.nan
        etf_c = precios.get(c["sector_etf"])
        regla = acc = "N/D"
        r2e = None
        if etf_c is not None and s is not None:
            try:
                _, st = analyze_pair(s, etf_c)
                regla = regla_oro(st)
                acc = accion(regla, st)
                rb = r2_vs_benchmark(s, etf_c)
                r2e = round(rb["r2"], 3) if rb else None
            except Exception:
                pass
        filas.append({**c, "precio": round(m["precio"], 2),
                      "r1m_pct": round(m["r1m"], 1) if not np.isnan(m["r1m"]) else None,
                      "r3m_pct": round(m["r3m"], 1) if not np.isnan(m["r3m"]) else None,
                      "r6m_pct": round(m["r6m"], 1) if not np.isnan(m["r6m"]) else None,
                      "exceso_r6m_pct": round(ex6, 1) if not np.isnan(ex6) else None,
                      "vol60": round(m["vol60"], 3), "rsi14": round(m["rsi14"], 1),
                      "tendencia": m["tendencia"], "score_fuerza": round(score, 2) if not np.isnan(score) else None,
                      "regla_oro_vs_etf": regla, "accion": acc, "r2_vs_etf": r2e,
                      "cedear_ba": mapa.get(c["ticker"].upper(), "")})
    df = pd.DataFrame(filas).sort_values(["sector_etf", "industria", "score_fuerza"], ascending=[True, True, False])
    return df, {k: g.head(3)["ticker"].tolist() for k, g in df.groupby(["sector_etf", "industria"]) if len(g) >= 2}
