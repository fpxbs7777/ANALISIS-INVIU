# -*- coding: utf-8 -*-
"""Screener de empresas en los SECTORES BENEFICIADOS por el ciclo intermarket.

Pipeline (reutiliza metodologias existentes del proyecto):
[1] FASE ........ MurphyDaily completo (15 capitulos, datos de hoy) ->
                  cap13.liderazgo_sectorial_200d -> top-3 ETFs sectoriales.
                  Fallback: contexto_actual.json. Etapa Pring desde cap12.
[2] INDUSTRIAS .. yf.Sector(key).industries ordenadas por market weight -> top-4
[3] UNIVERSO .... screener Yahoo por industria (EquityQuery paginado,
                  replica get_tickers_by_industry) + filtro liquidez mcap>=5B
[4] RANKING ..... fuerza relativa vs SPY (score 0.45*r6m_ex + 0.35*r3m_ex +
                  0.20*tendencia, formula de screener_sectores_fav) +
                  regla_oro/accion del ratio ticker-vs-ETF sectorial
                  (core.senales sobre core.ratio.analyze_pair) + R2 validacion
[5] DETALLE ..... top-3 por industria: comparacion completa 5 bloques
                  (perfil / cuantitativo 3y / fundamental / tecnico / noticias),
                  framework de clientes/comparar_mu_amd.py generalizado a N
[6] CEDEAR ...... mapa US->.BA desde unificado_completo - copia.json
[7] SALIDAS ..... CSV en clientes/rotacion_<fecha>/

Uso: python clientes/rotacion_ciclo_empresas.py
     python clientes/rotacion_ciclo_empresas.py --json   # usa contexto_actual.json
"""
import argparse
import json
import os
import sys
import threading
import time
import unicodedata
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import scipy.stats as st
import yfinance as yf
from yfinance import EquityQuery

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analisis.portafolio.salud_fundamental import descargar_empresa, zona_altman
from analisis.portafolio.noticias import fetch_news, score_sentiment
from analisis.portafolio.constructor import descargar_precios
from core.ratio import analyze_pair
from core.senales import regla_oro, accion

# ==================== CONFIG ====================
TOP_SECTORES = 3
TOP_INDUSTRIAS = 4          # por sector, por market weight
CANDIDATOS_POR_INDUSTRIA = 10
TOP_EMPRESAS = 3            # finalistas que pasan a comparacion detallada
MCAP_MIN = 5e9              # filtro de liquidez
PERIODO_RANKING = "1y"
PERIODO_DETALLE = "3y"
RAIZ = os.path.dirname(os.path.abspath(__file__))
UNIFICADO = os.path.join(ROOT, "unificado_completo - copia.json")
CONTEXTO_FALLBACK = os.path.join(ROOT, "contexto_actual.json")

# ETF sectorial -> (nombre es, sector key de Yahoo)
ETF_SECTOR_YAHOO = {
    "XLE": ("Energia", "energy"),
    "XLK": ("Tecnologia", "technology"),
    "XLI": ("Industriales", "industrials"),
    "XLB": ("Materiales", "basic-materials"),
    "XLY": ("Consumo Ciclico", "consumer-cyclical"),
    "XLP": ("Defensiva del Consumidor", "consumer-defensive"),
    "XLV": ("Salud", "healthcare"),
    "XLF": ("Financieros", "financial-services"),
    "XLC": ("Comunicacion", "communication-services"),
    "XLU": ("Utilidades", "utilities"),
    "XLRE": ("Inmobiliario", "real-estate"),
}


def _con_timeout(fn, segundos=30):
    resultado = {}

    def worker():
        try:
            resultado["data"] = fn()
        except Exception as e:
            resultado["error"] = e

    hilo = threading.Thread(target=worker, daemon=True)
    hilo.start()
    hilo.join(segundos)
    if hilo.is_alive():
        raise TimeoutError("timeout %ss" % segundos)
    if "error" in resultado:
        raise resultado["error"]
    return resultado.get("data")


def slug(txt):
    n = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in n).strip("_").lower()[:60]


def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/D"
    if isinstance(v, bool):
        return "SI" if v else "NO"
    if isinstance(v, float):
        return "{:,.4f}".format(v) if abs(v) < 10 else "{:,.2f}".format(v)
    return str(v)


# ==================== [1] FASE DEL CICLO ====================

def obtener_fase(usar_json=False):
    """Ranking sectorial completo + etapa Pring. MurphyDaily fresco o JSON."""
    if not usar_json:
        try:
            from analisis.ejecutivo.diario import MurphyDaily
            print("  Ejecutando MurphyDaily (15 capitulos, puede tardar)...")
            ctx = MurphyDaily(periodo="6y", verbose=True).run()
            lid = ctx["cap13"]["resultados"]["liderazgo_sectorial_200d"]
            etapa = ctx.get("cap12", {}).get("resultados", {}).get("etapa_pring")
            return dict(lid), etapa or "N/D", "MurphyDaily %s" % ctx.get("fecha")
        except Exception as e:
            print("  ! MurphyDaily fallo (%s); usando contexto_actual.json" % e)
    with open(CONTEXTO_FALLBACK, encoding="utf-8") as f:
        ctx = json.load(f)
    lid = ctx["cap13"]["resultados"]["liderazgo_sectorial_200d"]
    etapa = ctx.get("cap12", {}).get("resultados", {}).get("etapa_pring", "N/D")
    fecha = ctx.get("fecha", "?")
    print("  Contexto fallback: %s (%s)" % (CONTEXTO_FALLBACK, fecha))
    return dict(lid), etapa, "contexto_actual.json %s" % fecha


# ==================== [6] MAPA CEDEAR US -> .BA ====================

def cargar_mapa_cedear():
    """ticker US -> ticker .BA (desde unificado_completo; cedears tipo='cedear')."""
    mapa = {}
    try:
        with open(UNIFICADO, encoding="utf-8") as f:
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
    except Exception as e:
        print("  ! No se pudo cargar mapa CEDEAR: %s" % e)
    return mapa


# ==================== [2] INDUSTRIAS POR SECTOR ====================

def industrias_de_sector(sector_key, n=TOP_INDUSTRIAS):
    df = _con_timeout(lambda: yf.Sector(sector_key).industries, 40)
    df = df.sort_values("market weight", ascending=False)
    return [(str(r["name"]), float(r["market weight"])) for _, r in df.head(n).iterrows()]


# ==================== [3] SCREENER YAHOO POR INDUSTRIA ====================

EXCHANGES_US = ["NMS", "NGM", "NYQ", "ASE"]  # Nasdaq GS/GM, NYSE, NYSE American


def _variantes_nombre_industria(nombre):
    """El enum 'industry' del screener difiere del display de Sector.industries
    (ej: 'Software—Infrastructure' con em-dash vs 'Software - Infrastructure').
    Mapea contra la lista autoritativa de EquityQuery.valid_values."""
    variantes = []
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

        objetivo = norm(nombre)
        for cand in lista:
            if norm(cand) == objetivo:
                variantes.insert(0, cand)
                break
    except Exception:
        pass
    if nombre not in variantes:
        variantes.append(nombre)
    if " - " in nombre:
        em = nombre.replace(" - ", " \u2014 ")
        if em not in variantes:
            variantes.append(em)
    return variantes


def screener_industria(nombre_industria, max_paginas=2):
    """Replica de get_tickers_by_industry acotada a exchanges EE.UU.

    Yahoo ordena marketCap en moneda local si no se filtra bolsa, por lo que
    se consulta por exchange y luego se une.
    """
    filas = []
    size = 250
    for exch in EXCHANGES_US:
        offset = 0
        for variante in _variantes_nombre_industria(nombre_industria):
            exito_variante = False
            for _ in range(max_paginas):
                try:
                    q = EquityQuery("and", [
                        EquityQuery("eq", ["industry", variante]),
                        EquityQuery("eq", ["exchange", exch]),
                    ])
                    r = _con_timeout(lambda: yf.screen(q, size=size, offset=offset), 40)
                    if r is None or len(r) == 0:
                        break
                    if isinstance(r, dict):
                        r = pd.DataFrame([r])
                    if not isinstance(r, pd.DataFrame):
                        break
                    if "quotes" in r.columns:
                        expandidos = []
                        for _, row in r.iterrows():
                            raw = row["quotes"]
                            try:
                                data = json.loads(raw) if isinstance(raw, str) else (raw or [])
                            except Exception:
                                data = []
                            if isinstance(data, list):
                                expandidos.extend(data)
                        if not expandidos:
                            break
                        r = pd.DataFrame(expandidos)
                    if r.empty:
                        break
                    filas.append(r)
                    exito_variante = True
                    if len(r) < size:
                        break
                    offset += size
                    time.sleep(0.3)
                except Exception as e:
                    if variante == _variantes_nombre_industria(nombre_industria)[-1]:
                        print("      ! screener error '%s' [%s]: %s" % (nombre_industria, exch, str(e)[:80]))
                    break
            if exito_variante:
                break
    if not filas:
        return pd.DataFrame()
    df = pd.concat(filas, ignore_index=True)
    if "symbol" not in df.columns:
        return pd.DataFrame()
    df = df.dropna(subset=["symbol"]).drop_duplicates(subset=["symbol"])
    df["symbol"] = df["symbol"].astype(str)
    # cinturon de seguridad: sin sufijos extranjeros ni OTC grises
    df = df[~df["symbol"].str.contains(r"\.", regex=True)]
    if "quoteType" in df.columns:
        df = df[df["quoteType"].astype(str).str.upper() == "EQUITY"]
    if "currency" in df.columns:
        mask_usd = df["currency"].astype(str).str.upper().eq("USD") | df["currency"].isna()
        df = df[mask_usd]
    return df


# ==================== [4] RANKING FUERZA RELATIVA ====================

def metricas_ranking(serie):
    p = serie.dropna()
    if len(p) < 40:
        return None
    out = {"precio": float(p.iloc[-1])}
    for etiqueta, dias in (("r1m", 21), ("r3m", 63), ("r6m", 126)):
        out[etiqueta] = float(p.iloc[-1] / p.iloc[-dias] - 1) * 100 if len(p) > dias else np.nan
    s20 = float(p.rolling(20).mean().iloc[-1])
    s50 = float(p.rolling(50).mean().iloc[-1])
    s200 = float(p.rolling(200).mean().iloc[-1]) if len(p) >= 200 else np.nan
    if not np.isnan(s200):
        tend = 2 if p.iloc[-1] > s50 > s200 else 1 if p.iloc[-1] > s200 else 0
        out["tendencia"] = {2: "ALCISTA", 1: "MIXTA", 0: "BAJISTA"}[tend]
    else:
        tend = 1 if p.iloc[-1] > s50 else 0
        out["tendencia"] = "ALCISTA" if tend else "BAJISTA"
    out["_tend_pts"] = tend
    delta = p.pct_change()
    out["vol60"] = float(delta.iloc[-60:].std() * np.sqrt(252))
    out["rsi14"] = _rsi_last(p)
    return out


def _rsi_last(p, n=14):
    d = p.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def r2_vs_benchmark(serie_tk, serie_bench):
    """R2/corr/beta de retornos diarios alineados (logica motor/02_validacion_r2)."""
    idx = serie_tk.index.intersection(serie_bench.index)
    if len(idx) < 30:
        return None
    a = serie_tk.loc[idx].pct_change().dropna()
    b = serie_bench.loc[idx].pct_change().dropna()
    ci = a.index.intersection(b.index)
    if len(ci) < 30:
        return None
    a, b = a.loc[ci], b.loc[ci]
    corr = float(a.corr(b))
    varb = float(b.var())
    beta = float(a.cov(b) / varb) if varb else np.nan
    return {"r2": corr**2, "corr": corr, "beta": beta, "n": int(len(ci))}


# ==================== [5] FRAMEWORK DE COMPARACION (N tickers) ====================

class Distribution:
    def __init__(self, close_series, factor=252):
        self.p = close_series.dropna()
        self.factor = factor

    def compute(self):
        p = self.p
        r = p.pct_change().dropna().values
        self.current_price = float(p.iloc[-1])
        self.min_price = float(p.min())
        self.max_price = float(p.max())
        self.mean_annual = float(np.mean(r) * self.factor)
        self.volatility_annual = float(np.std(r) * np.sqrt(self.factor))
        self.sharpe_ratio = self.mean_annual / self.volatility_annual if self.volatility_annual > 0 else 0.0
        self.var_95 = float(np.percentile(r, 5))
        self.skewness = float(st.skew(r))
        self.kurtosis = float(st.kurtosis(r))
        jb = len(r) / 6 * (self.skewness**2 + 0.25 * self.kurtosis**2)
        self.p_value = float(1 - st.chi2.cdf(jb, df=2))
        self.max_drawdown = float((p / p.cummax() - 1).min())


def download_ohlcv(ticker, periodo=PERIODO_DETALLE):
    df = _con_timeout(lambda: yf.Ticker(ticker).history(period=periodo), 30)
    if df is None or df.empty:
        raise ValueError("sin datos %s" % ticker)
    return df.sort_index().dropna(subset=["Close"])


_INFO_CACHE = {}


def obtener_info(ticker):
    if ticker not in _INFO_CACHE:
        try:
            _INFO_CACHE[ticker] = _con_timeout(lambda: yf.Ticker(ticker).info or {}, 25) or {}
        except Exception:
            _INFO_CACHE[ticker] = {}
    return _INFO_CACHE[ticker]


def indicadores_tecnicos(ohlcv):
    c, h, l, v = ohlcv["Close"], ohlcv["High"], ohlcv["Low"], ohlcv["Volume"]
    precio = float(c.iloc[-1])
    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    senal = macd.ewm(span=9, adjust=False).mean()
    sd20 = c.rolling(20).std()
    prev = c.shift(1)
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    up, down = h.diff(), -l.diff()
    tr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=c.index).ewm(alpha=1 / 14, adjust=False).mean() / tr14
    mdi = 100 * pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=c.index).ewm(alpha=1 / 14, adjust=False).mean() / tr14
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = float(dx.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])
    w52 = c.iloc[-252:] if len(c) >= 252 else c
    out = {
        "sma20": float(sma20.iloc[-1]), "sma50": float(sma50.iloc[-1]),
        "sma200": float(sma200.iloc[-1]) if not np.isnan(sma200.iloc[-1]) else None,
        "tendencia": "ALCISTA" if precio > sma200.iloc[-1] else "BAJISTA",
        "cruce_50_200": "GOLDEN CROSS" if sma50.iloc[-1] > sma200.iloc[-1] else "DEATH CROSS",
        "rsi14": _rsi_last(c),
        "rsi_zona": None,
        "macd": float(macd.iloc[-1]), "macd_senal": float(senal.iloc[-1]),
        "macd_hist": float((macd - senal).iloc[-1]),
        "bollinger_pctb": float(((c - (sma20 - 2 * sd20)) / (4 * sd20)).iloc[-1]),
        "atr14_pct": float(atr14.iloc[-1] / precio * 100),
        "adx14": adx,
        "adx_zona": "TENDENCIA FUERTE" if adx >= 25 else "TENDENCIA MODERADA" if adx >= 20 else "SIN TENDENCIA",
        "rango_52s_pct": float((precio - w52.min()) / (w52.max() - w52.min()) * 100),
        "dist_max_52s_pct": float((precio / w52.max() - 1) * 100),
        "vol_relativa": float(v.iloc[-1] / v.iloc[-21:].mean()),
    }
    out["rsi_zona"] = "SOBRECOMPRA" if out["rsi14"] > 70 else "SOBREVENTA" if out["rsi14"] < 30 else "NEUTRAL"
    for etiqueta, dias in (("1M", 21), ("3M", 63), ("6M", 126), ("12M", 252)):
        out["momentum_" + etiqueta] = float(c.iloc[-1] / c.iloc[-dias] - 1) * 100 if len(c) > dias else np.nan
    return out


def percentil_pe_historico(info, ohlcv):
    eps = info.get("trailingEps")
    if not eps or ohlcv is None or ohlcv.empty:
        return None
    pe = ohlcv["Close"] / float(eps)
    actual = float(pe.iloc[-1])
    return actual, float((pe < actual).mean() * 100)


def metricas_fundamentales(ticker, ohlcv):
    info = obtener_info(ticker)

    def f(x, dec=4):
        try:
            x = float(x)
            return round(x, dec) if not pd.isna(x) else None
        except (TypeError, ValueError):
            return None

    salud = descargar_empresa(ticker)
    pe_hist = percentil_pe_historico(info, ohlcv)
    target = f(info.get("targetMeanPrice"), 2)
    precio = f(info.get("currentPrice"), 2) or float(ohlcv["Close"].iloc[-1])
    market_cap = f(info.get("marketCap")) or f(info.get("nonDilutedMarketCap"))
    revenue = f(info.get("totalRevenue"))

    return {
        "nombre": info.get("longName") or salud.get("empresa") or ticker,
        "sector": info.get("sector"),
        "industria": info.get("industry"),
        "market_cap_B": round(market_cap / 1e9, 1) if market_cap else None,
        "pe_trailing": f(info.get("trailingPE"), 2),
        "pe_forward": f(info.get("forwardPE"), 2),
        "peg": f(info.get("trailingPegRatio") or info.get("pegRatio"), 2),
        "ps": f(info.get("priceToSalesTrailing12Months"), 2)
              or (round(market_cap / revenue, 2) if market_cap and revenue else None),
        "pb": f(info.get("priceToBook"), 2),
        "ev_ebitda": f(info.get("enterpriseToEbitda"), 2),
        "div_yield_pct": f(info.get("dividendYield") * 100 if info.get("dividendYield") and info.get("dividendYield") < 1 else info.get("dividendYield"), 2),
        "pe_aprox": round(pe_hist[0], 2) if pe_hist else None,
        "pe_percentil": round(pe_hist[1], 1) if pe_hist else None,
        "margen_bruto": f(salud.get("margen_bruto")),
        "margen_op": f(salud.get("margen_operativo")),
        "margen_neto": f(salud.get("margen_neto")),
        "roe": f(salud.get("roe")),
        "roa": f(salud.get("roa")),
        "deuda_patrimonio": f(salud.get("deuda_patrimonio"), 3),
        "deuda_ebitda": f(salud.get("deuda_ebitda"), 2),
        "razon_corriente": f(salud.get("razon_corriente"), 2),
        "prueba_acida": f(salud.get("prueba_acida"), 2),
        "fcf_B": round(f(salud.get("fcf")) / 1e9, 2) if salud.get("fcf") else None,
        "crec_ingresos": f(salud.get("crec_ingresos")),
        "altman_z": f(salud.get("z"), 2),
        "altman_zona": zona_altman(salud.get("z")),
        "target_price": target,
        "upside_pct": round((target / precio - 1) * 100, 1) if target and precio else None,
    }


def metricas_noticias(ticker, max_items=10):
    news = fetch_news(ticker, max_items=max_items)
    scores = [score_sentiment(n["title"] + " " + (n.get("summary") or "")) for n in news]
    detalle = [(str(n.get("published", ""))[:10], n.get("title", ""), s) for n, s in zip(news, scores)]
    return {
        "noticias_total": len(news),
        "score_neto": int(sum(scores)),
        "bullish": scores.count(1),
        "bearish": scores.count(-1),
        "neutrales": scores.count(0),
    }, detalle


def capm_vs(close_tk, close_bench):
    idx = close_tk.index.intersection(close_bench.index)
    if len(idx) < 60:
        return None
    a = close_bench.loc[idx].pct_change().dropna()
    b = close_tk.loc[idx].pct_change().dropna()
    ci = a.index.intersection(b.index)
    a, b = a.loc[ci], b.loc[ci]
    pend, inter, r_val, p_val, _ = st.linregress(a.values, b.values)
    return {"beta": float(pend), "alpha_anual": float(inter * 252),
            "r2": float(r_val**2), "corr": float(r_val)}


# ==================== PIPELINE ====================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="usar contexto_actual.json en vez de recalcular")
    args = ap.parse_args()

    t0 = datetime.now()
    print("=" * 95)
    print("SCREENER ROTACION CICLO INTERMARKET — %s" % t0.strftime("%Y-%m-%d %H:%M"))
    print("=" * 95)

    out_dir = os.path.join(RAIZ, "rotacion_%s" % t0.strftime("%Y%m%d"))
    os.makedirs(out_dir, exist_ok=True)

    # ---------- [1] FASE ----------
    print("\n[1/7] Fase del ciclo intermarket...")
    liderazgo, etapa_pring, fuente = obtener_fase(usar_json=args.json)
    df_fase = pd.DataFrame([{"etf": k, "slope_ratio_vs_spy_200d": v} for k, v in liderazgo.items()])
    df_fase.insert(0, "etapa_pring", etapa_pring)
    df_fase.insert(0, "fuente", fuente)
    top_etfs = list(liderazgo.keys())[:TOP_SECTORES]
    print(df_fase.head(8).to_string(index=False))
    print("  TOP-%d sectores beneficiados: %s" % (
        TOP_SECTORES, ", ".join("%s (%s)" % (e, ETF_SECTOR_YAHOO[e][0]) for e in top_etfs)))
    df_fase.to_csv(os.path.join(out_dir, "fase_ciclo.csv"), index=False, encoding="utf-8-sig")

    mapa_cedear = cargar_mapa_cedear()

    # ---------- [2]+[3] INDUSTRIAS Y UNIVERSO ----------
    print("\n[2/7] Industrias lideres por sector (market weight) + universo...")
    candidatos = []
    for etf in top_etfs:
        nombre_sector, key_yahoo = ETF_SECTOR_YAHOO[etf]
        print("  --- %s | %s ---" % (etf, nombre_sector))
        try:
            inds = industrias_de_sector(key_yahoo)
        except Exception as e:
            print("    ! no se pudieron listar industrias: %s" % e)
            continue
        for nombre_ind, peso in inds:
            print("    Industria: %s (peso %.1f%%)" % (nombre_ind, peso * 100))
            df_sc = screener_industria(nombre_ind)
            if df_sc.empty:
                print("      sin resultados del screener")
                continue
            if "marketCap" in df_sc.columns:
                df_sc["marketCap"] = pd.to_numeric(df_sc["marketCap"], errors="coerce")
                df_sc = df_sc[df_sc["marketCap"] >= MCAP_MIN]
            df_sc = df_sc.sort_values("marketCap", ascending=False).head(CANDIDATOS_POR_INDUSTRIA)
            print("      %d candidatas (mcap>=%.0fB): %s" % (
                len(df_sc), MCAP_MIN / 1e9, ", ".join(df_sc["symbol"].head(CANDIDATOS_POR_INDUSTRIA))))
            for _, r in df_sc.iterrows():
                candidatos.append({
                    "ticker": r["symbol"],
                    "nombre": r.get("shortName") or r.get("longName") or r["symbol"],
                    "sector_etf": etf,
                    "sector": nombre_sector,
                    "industria": nombre_ind,
                    "peso_industria": peso,
                    "mcap_B": round(float(r["marketCap"]) / 1e9, 1) if pd.notna(r.get("marketCap")) else None,
                })
    if not candidatos:
        print("Sin candidatos; abortando.")
        return None
    print("  Total candidatas: %d" % len(candidatos))

    # ---------- [4] RANKING ----------
    print("\n[3/7] Descarga batch %sy (candidatas + SPY + ETFs sectoriales)..." % PERIODO_RANKING.rstrip("y"))
    tickers_universo = sorted({c["ticker"] for c in candidatos} | set(top_etfs) | {"SPY"})
    precios = {}
    for i in range(0, len(tickers_universo), 40):
        precios.update(descargar_precios(tickers_universo[i:i + 40], period=PERIODO_RANKING, verbose=True))
    spy = precios.get("SPY")

    print("[4/7] Score de fuerza relativa + regla de oro vs ETF sectorial...")
    filas_resumen = []
    for c in candidatos:
        tk = c["ticker"]
        s = precios.get(tk)
        m = metricas_ranking(s) if s is not None else None
        if m is None:
            continue
        ex6 = m["r6m"] - float(spy.iloc[-1] / spy.iloc[-126] - 1) * 100 if (spy is not None and len(spy) > 126) and not np.isnan(m["r6m"]) else np.nan
        ex3 = m["r3m"] - float(spy.iloc[-1] / spy.iloc[-63] - 1) * 100 if (spy is not None and len(spy) > 63) and not np.isnan(m["r3m"]) else np.nan
        # score de screener_sectores_fav: 0.45*r6m_ex + 0.35*r3m_ex + 0.20*tendencia
        score = 0.45 * ex6 + 0.35 * ex3 + 0.20 * m["_tend_pts"]
        etf_close = precios.get(c["sector_etf"])
        regla = acc_txt = "N/D"
        r2e = None
        if etf_close is not None and s is not None:
            try:
                _, stats_pair = analyze_pair(s, etf_close)
                regla = regla_oro(stats_pair)
                acc_txt = accion(regla, stats_pair)
                rb = r2_vs_benchmark(s, etf_close)
                r2e = round(rb["r2"], 3) if rb else None
            except Exception:
                pass
        filas_resumen.append({
            **{k: c[k] for k in ("ticker", "nombre", "sector_etf", "sector", "industria", "peso_industria", "mcap_B")},
            "precio": round(m["precio"], 2),
            "r1m_pct": round(m["r1m"], 1) if not np.isnan(m["r1m"]) else None,
            "r3m_pct": round(m["r3m"], 1) if not np.isnan(m["r3m"]) else None,
            "r6m_pct": round(m["r6m"], 1) if not np.isnan(m["r6m"]) else None,
            "exceso_r6m_pct": round(ex6, 1) if not np.isnan(ex6) else None,
            "vol60": round(m["vol60"], 3),
            "rsi14": round(m["rsi14"], 1),
            "tendencia": m["tendencia"],
            "score_fuerza": round(score, 2),
            "regla_oro_vs_etf": regla,
            "accion": acc_txt,
            "r2_vs_etf": r2e,
            "cedear_ba": mapa_cedear.get(tk.upper(), ""),
        })
    df_resumen = pd.DataFrame(filas_resumen).sort_values(["sector_etf", "industria", "score_fuerza"], ascending=[True, True, False])
    df_resumen.to_csv(os.path.join(out_dir, "resumen_empresas.csv"), index=False, encoding="utf-8-sig")
    print(df_resumen[["ticker", "industria", "score_fuerza", "regla_oro_vs_etf", "accion", "cedear_ba"]]
          .to_string(index=False))

    # finalistas: top-N score por industria (con al menos 2 para comparar)
    finalistas = {}
    for (etf, ind), grupo in df_resumen.groupby(["sector_etf", "industria"]):
        top = grupo.head(TOP_EMPRESAS)["ticker"].tolist()
        if len(top) >= 2:
            finalistas[(etf, ind)] = top
    print("  Industrias con comparacion detallada: %d" % len(finalistas))

    # ---------- [5] DETALLE ----------
    print("\n[5/7] Comparacion detallada (%sy) por industria..." % PERIODO_DETALLE.rstrip("y"))
    benches_ohlcv = {b: download_ohlcv(b) for b in set(list(top_etfs) + ["SPY"])}
    resumen_noticias = []
    for (etf, ind), tks in finalistas.items():
        print("\n" + "#" * 95)
        print("# %s | %s — %s" % (etf, ind, ", ".join(tks)))
        print("#" * 95)
        datos = {}
        for tk in tks:
            try:
                ohlcv = download_ohlcv(tk)
                dist = Distribution(ohlcv["Close"])
                dist.compute()
                datos[tk] = {
                    "dist": dist,
                    "tec": indicadores_tecnicos(ohlcv),
                    "fund": metricas_fundamentales(tk, ohlcv),
                    "noti": metricas_noticias(tk)[0],
                    "close": ohlcv["Close"],
                }
                print("  OK %s" % tk)
            except Exception as e:
                print("  ! %s: %s" % (tk, e))
        if len(datos) < 2:
            print("  datos insuficientes; se omite")
            continue

        filas = []

        def fila(seccion, metrica, valores):
            filas.append({"seccion": seccion, "metrica": metrica, **valores})

        D = {tk: datos[tk]["dist"] for tk in datos}
        T = {tk: datos[tk]["tec"] for tk in datos}
        F = {tk: datos[tk]["fund"] for tk in datos}
        N = {tk: datos[tk]["noti"] for tk in datos}
        V = lambda d, k: {tk: d[tk].get(k) for tk in datos}

        fila("PERFIL", "Nombre", V(F, "nombre"))
        fila("PERFIL", "Sector / Industria (Yahoo)", {tk: "%s / %s" % (F[tk].get("sector") or "-", F[tk].get("industria") or "-") for tk in datos})
        fila("PERFIL", "CEDEAR (.BA)", {tk: mapa_cedear.get(tk.upper(), "") for tk in datos})
        fila("PERFIL", "Precio actual (USD)", {tk: round(D[tk].current_price, 2) for tk in datos})
        fila("PERFIL", "Market Cap (B USD)", V(F, "market_cap_B"))
        fila("CUANTITATIVO 3Y", "Retorno anualizado", {tk: round(D[tk].mean_annual, 4) for tk in datos})
        fila("CUANTITATIVO 3Y", "Volatilidad anualizada", {tk: round(D[tk].volatility_annual, 4) for tk in datos})
        fila("CUANTITATIVO 3Y", "Sharpe ratio", {tk: round(D[tk].sharpe_ratio, 3) for tk in datos})
        fila("CUANTITATIVO 3Y", "VaR diario 95%", {tk: round(D[tk].var_95, 4) for tk in datos})
        fila("CUANTITATIVO 3Y", "Max drawdown", {tk: round(D[tk].max_drawdown, 4) for tk in datos})
        fila("CUANTITATIVO 3Y", "Skewness", {tk: round(D[tk].skewness, 3) for tk in datos})
        fila("CUANTITATIVO 3Y", "Kurtosis (exceso)", {tk: round(D[tk].kurtosis, 3) for tk in datos})
        fila("CUANTITATIVO 3Y", "p-value Jarque-Bera", {tk: round(D[tk].p_value, 4) for tk in datos})
        for bench_tag, bench_key in (("SPY", "SPY"), (etf, etf)):
            caps = {tk: capm_vs(datos[tk]["close"], benches_ohlcv[bench_key]["Close"]) for tk in datos}
            fila("CUANTITATIVO 3Y", "Beta vs " + bench_tag, {tk: round(caps[tk]["beta"], 3) if caps[tk] else None for tk in datos})
            fila("CUANTITATIVO 3Y", "Alpha anual vs " + bench_tag, {tk: round(caps[tk]["alpha_anual"], 4) if caps[tk] else None for tk in datos})
            fila("CUANTITATIVO 3Y", "R² vs " + bench_tag, {tk: round(caps[tk]["r2"], 3) if caps[tk] else None for tk in datos})
        fila("FUNDAMENTAL", "P/E trailing", V(F, "pe_trailing"))
        fila("FUNDAMENTAL", "P/E forward", V(F, "pe_forward"))
        fila("FUNDAMENTAL", "PEG (trailing)", V(F, "peg"))
        fila("FUNDAMENTAL", "P/S", V(F, "ps"))
        fila("FUNDAMENTAL", "P/B", V(F, "pb"))
        fila("FUNDAMENTAL", "EV/EBITDA", V(F, "ev_ebitda"))
        fila("FUNDAMENTAL", "P/E aprox actual / percentil 3y", {tk: "%s (%s%%)" % (fmt(F[tk].get("pe_aprox")), fmt(F[tk].get("pe_percentil"))) for tk in datos})
        fila("FUNDAMENTAL", "Margen bruto", V(F, "margen_bruto"))
        fila("FUNDAMENTAL", "Margen operativo", V(F, "margen_op"))
        fila("FUNDAMENTAL", "Margen neto", V(F, "margen_neto"))
        fila("FUNDAMENTAL", "ROE", V(F, "roe"))
        fila("FUNDAMENTAL", "ROA", V(F, "roa"))
        fila("FUNDAMENTAL", "Deuda/Patrimonio", V(F, "deuda_patrimonio"))
        fila("FUNDAMENTAL", "Deuda/EBITDA", V(F, "deuda_ebitda"))
        fila("FUNDAMENTAL", "Liquidez corriente", V(F, "razon_corriente"))
        fila("FUNDAMENTAL", "FCF (B USD)", V(F, "fcf_B"))
        fila("FUNDAMENTAL", "Crecimiento ingresos YoY", V(F, "crec_ingresos"))
        fila("FUNDAMENTAL", "Altman Z (zona)", {tk: "%s (%s)" % (fmt(F[tk].get("altman_z")), F[tk].get("altman_zona") or "-") for tk in datos})
        fila("FUNDAMENTAL", "Target price / upside", {tk: "%s (+%s%%)" % (fmt(F[tk].get("target_price")), fmt(F[tk].get("upside_pct"))) for tk in datos})
        fila("TECNICO", "SMA20 / SMA50 / SMA200", {tk: "%s / %s / %s" % (fmt(round(T[tk]["sma20"], 2)), fmt(round(T[tk]["sma50"], 2)), fmt(T[tk]["sma200"] and round(T[tk]["sma200"], 2))) for tk in datos})
        fila("TECNICO", "Tendencia (vs SMA200)", V(T, "tendencia"))
        fila("TECNICO", "Cruce SMA50/200", V(T, "cruce_50_200"))
        fila("TECNICO", "RSI14 (zona)", {tk: "%s (%s)" % (round(T[tk]["rsi14"], 1), T[tk]["rsi_zona"]) for tk in datos})
        fila("TECNICO", "MACD hist", {tk: round(T[tk]["macd_hist"], 3) for tk in datos})
        fila("TECNICO", "Bollinger %B", {tk: round(T[tk]["bollinger_pctb"], 2) for tk in datos})
        fila("TECNICO", "ATR14 (% precio)", {tk: round(T[tk]["atr14_pct"], 2) for tk in datos})
        fila("TECNICO", "ADX14 (regimen)", {tk: "%s (%s)" % (round(T[tk]["adx14"], 1), T[tk]["adx_zona"]) for tk in datos})
        fila("TECNICO", "Posicion rango 52s (%)", {tk: round(T[tk]["rango_52s_pct"], 1) for tk in datos})
        fila("TECNICO", "Distancia a maximo 52s (%)", {tk: round(T[tk]["dist_max_52s_pct"], 1) for tk in datos})
        fila("TECNICO", "Momentum 1M / 3M (%)", {tk: "%s / %s" % (fmt(round(T[tk]["momentum_1M"], 1)), fmt(round(T[tk]["momentum_3M"], 1))) for tk in datos})
        fila("TECNICO", "Momentum 6M / 12M (%)", {tk: "%s / %s" % (fmt(round(T[tk]["momentum_6M"], 1)), fmt(round(T[tk]["momentum_12M"], 1))) for tk in datos})
        fila("TECNICO", "Volumen relativo (vs 20d)", {tk: round(T[tk]["vol_relativa"], 2) for tk in datos})
        fila("NOTICIAS", "Noticias / score neto", {tk: "%s / %+d" % (N[tk]["noticias_total"], N[tk]["score_neto"]) for tk in datos})
        fila("NOTICIAS", "Bullish / Bearish / Neutrales", {tk: "%d / %d / %d" % (N[tk]["bullish"], N[tk]["bearish"], N[tk]["neutrales"]) for tk in datos})

        df_comp = pd.DataFrame(filas)
        nombre_archivo = "comparacion_%s__%s.csv" % (slug(etf), slug(ind))
        df_comp.to_csv(os.path.join(out_dir, nombre_archivo), index=False, encoding="utf-8-sig")

        vista = df_comp.copy()
        for tk in datos:
            vista[tk] = df_comp[tk].map(fmt)
        print(vista[["seccion", "metrica"] + list(datos)].to_string(index=False))
        print("  -> guardado: %s" % nombre_archivo)

        for tk in datos:
            resumen_noticias.append({
                "ticker": tk, "industria": ind, "sector_etf": etf,
                "noticias_total": N[tk]["noticias_total"], "score_neto": N[tk]["score_neto"],
                "bullish": N[tk]["bullish"], "bearish": N[tk]["bearish"],
            })

    # ---------- [7] SALIDA FINAL ----------
    if resumen_noticias:
        pd.DataFrame(resumen_noticias).to_csv(
            os.path.join(out_dir, "sentimiento_finalistas.csv"), index=False, encoding="utf-8-sig")
    dur = (datetime.now() - t0).total_seconds() / 60
    print("\n" + "=" * 95)
    print("LISTO en %.1f min. Salidas en:\n  %s" % (dur, out_dir))
    for f in sorted(os.listdir(out_dir)):
        print("    - " + f)
    print("=" * 95)
    return df_resumen


if __name__ == "__main__":
    main()
