# -*- coding: utf-8 -*-
"""Comparación MU vs AMD en un DataFrame único con 5 bloques:

1. PERFIL ......... nombre, sector e industria reales via yfinance
2. CUANTITATIVO ... retorno/vol/Sharpe/VaR/drawdown/skew/kurtosis (3y),
                    alpha/beta/R2 vs SPY (mercado), XLK (sector) y SMH (semis),
                    correlacion y ratio MU/AMD (core.ratio)
3. FUNDAMENTAL .... ratios de analisis.portafolio.salud_fundamental (Altman Z,
                    DuPont, liquidez, deuda, FCF, margenes) + multiplos de info
4. TECNICO ........ SMA20/50/200 + cruces, RSI14, MACD, Bollinger %B, ATR14,
                    ADX14, rango 52s, momentum 1M/3M/6M/12M, volumen relativo
5. NOTICIAS ....... fetch_news + score_sentiment (lexico bullish/bearish)

Salida: DataFrame unico (seccion/metrica x ticker) impreso y guardado en
comparacion_mu_amd.csv (+ metricas_individuales_mu_amd.csv).

Uso: python clientes/comparar_mu_amd.py
"""
import os
import sys
import threading
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import scipy.stats as st
import yfinance as yf

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
from core.ratio import analyze_pair

TICKERS = ["MU", "AMD"]
PERIODO = "3y"
BENCHMARKS = {"SPY": "Mercado (SPY)", "XLK": "Sector Tech (XLK)", "SMH": "Semis (SMH)"}
INFO_TIMEOUT = 30


def _con_timeout(fn, segundos=INFO_TIMEOUT):
    """Ejecuta fn() en un hilo con timeout (yfinance a veces se cuelga)."""
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
        raise TimeoutError("timeout de %ss" % segundos)
    if "error" in resultado:
        raise resultado["error"]
    return resultado.get("data")


_INFO_CACHE = {}


def obtener_info(ticker):
    """info real de yfinance con cache en memoria."""
    if ticker not in _INFO_CACHE:
        _INFO_CACHE[ticker] = _con_timeout(lambda: yf.Ticker(ticker).info or {}) or {}
    return _INFO_CACHE[ticker]


def download_ohlcv(ticker, periodo=PERIODO):
    """OHLCV diario ajustado via Ticker.history con timeout."""
    df = _con_timeout(lambda: yf.Ticker(ticker).history(period=periodo))
    if df is None or df.empty:
        raise ValueError("sin datos para %s" % ticker)
    df = df.sort_index().dropna(subset=["Close"])
    print("    %s: %d barras (%s -> %s)" % (ticker, len(df), df.index[0].date(), df.index[-1].date()))
    return df


def armar_ts(ohlcv):
    """DataFrame date/close/return que esperan Distribution y CAPMModel."""
    ts = pd.DataFrame()
    ts["date"] = ohlcv.index
    ts["close"] = ohlcv["Close"].values
    ts["close_previous"] = ts["close"].shift(1)
    ts["return"] = ts["close"] / ts["close_previous"] - 1
    return ts.dropna().reset_index(drop=True)


# ==================== CUANTITATIVO ====================

class Distribution:
    """Estadisticas de la distribucion de retornos diarios."""

    def __init__(self, ticker, timeseries_data, factor=252):
        self.ticker = ticker
        self.timeseries = timeseries_data
        self.factor = factor
        self.vector = None

    def compute_stats(self):
        self.vector = self.timeseries["return"].values
        p = self.timeseries["close"]
        self.current_price = float(p.iloc[-1])
        self.min_price = float(p.min())
        self.max_price = float(p.max())
        self.mean_annual = float(np.mean(self.vector) * self.factor)
        self.volatility_annual = float(np.std(self.vector) * np.sqrt(self.factor))
        self.sharpe_ratio = self.mean_annual / self.volatility_annual if self.volatility_annual > 0 else 0.0
        self.var_95 = float(np.percentile(self.vector, 5))
        self.skewness = float(st.skew(self.vector))
        self.kurtosis = float(st.kurtosis(self.vector))
        jb = len(self.vector) / 6 * (self.skewness**2 + 0.25 * self.kurtosis**2)
        self.p_value = float(1 - st.chi2.cdf(jb, df=2))
        self.is_normal = self.p_value > 0.05
        drawdown = p / p.cummax() - 1
        self.max_drawdown = float(drawdown.min())


class CAPMModel:
    """Regresion de retornos security vs benchmark: alpha, beta, R2, corr."""

    def __init__(self, benchmark, security):
        self.benchmark = benchmark
        self.security = security

    def fit(self, data_dict):
        bx = data_dict[self.benchmark]
        sy = data_dict[self.security]
        comunes = sorted(set(bx["date"]).intersection(set(sy["date"])))
        x = bx.set_index("date").loc[comunes, "return"].values
        y = sy.set_index("date").loc[comunes, "return"].values
        pendiente, intercepto, r_value, p_value, _ = st.linregress(x, y)
        self.alpha = float(intercepto)
        self.beta = float(pendiente)
        self.correlation = float(r_value)
        self.r_squared = float(r_value**2)
        self.p_value = float(p_value)
        return self


def max_drawdown_serie(close):
    dd = close / close.cummax() - 1
    return float(dd.min()), dd.idxmin()


# ==================== TECNICO ====================

def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def indicadores_tecnicos(ohlcv):
    c = ohlcv["Close"]
    h, l, v = ohlcv["High"], ohlcv["Low"], ohlcv["Volume"]
    out = {}
    precio = float(c.iloc[-1])

    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    out["precio"] = precio
    out["sma20"] = float(sma20.iloc[-1])
    out["sma50"] = float(sma50.iloc[-1])
    out["sma200"] = float(sma200.iloc[-1])
    out["tendencia"] = "ALCISTA" if precio > sma200.iloc[-1] else "BAJISTA"
    out["cruce_50_200"] = "GOLDEN CROSS" if sma50.iloc[-1] > sma200.iloc[-1] else "DEATH CROSS"

    r = rsi(c).iloc[-1]
    out["rsi14"] = float(r)
    out["rsi_zona"] = "SOBRECOMPRA" if r > 70 else "SOBREVENTA" if r < 30 else "NEUTRAL"

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    senal = macd.ewm(span=9, adjust=False).mean()
    out["macd"] = float(macd.iloc[-1])
    out["macd_senal"] = float(senal.iloc[-1])
    out["macd_hist"] = float((macd - senal).iloc[-1])

    sd20 = c.rolling(20).std()
    sup, inf = sma20 + 2 * sd20, sma20 - 2 * sd20
    out["bollinger_pctb"] = float(((c - inf) / (sup - inf)).iloc[-1])

    prev_close = c.shift(1)
    tr = pd.concat([h - l, (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    out["atr14"] = float(atr14.iloc[-1])
    out["atr14_pct"] = float(atr14.iloc[-1] / precio * 100)

    up, down = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=c.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=c.index)
    tr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False).mean() / tr14
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False).mean() / tr14
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]
    out["adx14"] = float(adx)
    out["adx_zona"] = "TENDENCIA FUERTE" if adx >= 25 else "TENDENCIA MODERADA" if adx >= 20 else "SIN TENDENCIA"

    w52 = c.iloc[-252:] if len(c) >= 252 else c
    out["rango_52s_pct"] = float((precio - w52.min()) / (w52.max() - w52.min()) * 100)
    out["dist_max_52s_pct"] = float((precio / w52.max() - 1) * 100)

    for etiqueta, dias in (("1M", 21), ("3M", 63), ("6M", 126), ("12M", 252)):
        out["momentum_" + etiqueta] = float(c.iloc[-1] / c.iloc[-dias] - 1) * 100 if len(c) > dias else np.nan

    out["vol_relativa"] = float(v.iloc[-1] / v.iloc[-21:].mean())
    return out


# ==================== FUNDAMENTAL ====================

def percentil_pe_historico(info, ohlcv):
    """Aproximacion: P/E historico = precio historico / EPS TTM actual."""
    eps = info.get("trailingEps")
    if not eps or ohlcv is None or ohlcv.empty:
        return None
    pe_serie = ohlcv["Close"] / float(eps)
    pe_actual = float(pe_serie.iloc[-1])
    return pe_actual, float((pe_serie < pe_actual).mean() * 100)


def metricas_fundamentales(ticker, ohlcv):
    info = obtener_info(ticker)
    salud = descargar_empresa(ticker)

    def f(x, dec=4):
        return round(float(x), dec) if isinstance(x, (int, float)) and not pd.isna(x) else None

    pe_hist = percentil_pe_historico(info, ohlcv)
    target = f(info.get("targetMeanPrice"), 2)
    precio = f(info.get("currentPrice"), 2) or float(ohlcv["Close"].iloc[-1])

    # Fallbacks cuando info no trae el campo (pasa con MU)
    market_cap = f(info.get("marketCap")) or f(info.get("nonDilutedMarketCap"))
    if market_cap is None:
        shares = f(info.get("sharesOutstanding")) or f(info.get("impliedSharesOutstanding"))
        market_cap = round(shares * precio, 0) if shares else None
    revenue = f(info.get("totalRevenue"))

    return {
        # Perfil
        "nombre": info.get("longName") or salud.get("empresa") or ticker,
        "sector": info.get("sector"),
        "industria": info.get("industry"),
        "market_cap_B": round(market_cap / 1e9, 1) if market_cap else None,
        # Multiplos
        "pe_trailing": f(info.get("trailingPE"), 2),
        "pe_forward": f(info.get("forwardPE"), 2),
        "peg": f(info.get("trailingPegRatio") or info.get("pegRatio"), 2),
        "ps": f(info.get("priceToSalesTrailing12Months"), 2)
              or (round(market_cap / revenue, 2) if market_cap and revenue else None),
        "pb": f(info.get("priceToBook"), 2),
        "ev_ebitda": f(info.get("enterpriseToEbitda"), 2),
        "div_yield_pct": f(info.get("dividendYield") * 100 if info.get("dividendYield") and info.get("dividendYield") < 1 else info.get("dividendYield"), 2),
        "pe_actual_aprox": round(pe_hist[0], 2) if pe_hist else None,
        "pe_percentil_hist": round(pe_hist[1], 1) if pe_hist else None,
        # Salud fundamental (salud_fundamental.py, caché 7 dias)
        "margen_bruto_pct": f(salud.get("margen_bruto"), 4),
        "margen_op_pct": f(salud.get("margen_operativo"), 4),
        "margen_neto_pct": f(salud.get("margen_neto"), 4),
        "roe": f(salud.get("roe"), 4),
        "roa": f(salud.get("roa"), 4),
        "roe_dupont": f(salud.get("roe_dupont"), 4),
        "deuda_patrimonio": f(salud.get("deuda_patrimonio"), 3),
        "deuda_ebitda": f(salud.get("deuda_ebitda"), 2),
        "razon_corriente": f(salud.get("razon_corriente"), 2),
        "prueba_acida": f(salud.get("prueba_acida"), 2),
        "fcf_B": round(f(salud.get("fcf")) / 1e9, 2) if salud.get("fcf") else None,
        "fcf_ingresos": f(salud.get("fcf_ingresos"), 3),
        "crec_ingresos_pct": f(salud.get("crec_ingresos"), 4),
        "altman_z": f(salud.get("z"), 2),
        "altman_zona": zona_altman(salud.get("z")),
        # Analista
        "target_price": target,
        "upside_pct": round((target / precio - 1) * 100, 1) if target and precio else None,
    }


# ==================== NOTICIAS ====================

def metricas_noticias(ticker, max_items=10):
    news = fetch_news(ticker, max_items=max_items)
    scores = [score_sentiment(n["title"] + " " + (n.get("summary") or "")) for n in news]
    detalle = [(n.get("published", "")[:10], n.get("title", ""), s) for n, s in zip(news, scores)]
    return {
        "noticias_total": len(news),
        "score_neto": int(sum(scores)),
        "bullish": scores.count(1),
        "bearish": scores.count(-1),
        "neutrales": scores.count(0),
    }, detalle


# ==================== SALIDA ====================

def fila(seccion, metrica, mu, amd):
    return {"seccion": seccion, "metrica": metrica, "MU": mu, "AMD": amd}


def main():
    print("=" * 90)
    print("COMPARACIÓN MU vs AMD — %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 90)

    # [1/7] Descarga de datos
    print("\n[1/7] Descargando precios (%s)..." % PERIODO)
    ohlcv, ts_data = {}, {}
    for t in TICKERS:
        ohlcv[t] = download_ohlcv(t)
        ts_data[t] = armar_ts(ohlcv[t])
    for b in BENCHMARKS:
        ts_data[b] = armar_ts(download_ohlcv(b))

    # [2/7] Cuantitativo
    print("[2/7] Métricas cuantitativas...")
    dists = {t: Distribution(t, ts_data[t]) for t in TICKERS}
    for d in dists.values():
        d.compute_stats()
    capms = {(t, b): CAPMModel(b, t).fit(ts_data) for t in TICKERS for b in BENCHMARKS}

    pa = ohlcv["MU"]["Close"]
    pb = ohlcv["AMD"]["Close"]
    _, stats_ratio = analyze_pair(pa, pb, wins=[126, 252])
    sr = stats_ratio[252]

    # [3/7] Fundamental
    print("[3/7] Fundamentales (yfinance + salud_fundamental)...")
    fondos = {t: metricas_fundamentales(t, ohlcv[t]) for t in TICKERS}

    # [4/7] Técnico
    print("[4/7] Indicadores técnicos...")
    tecnicos = {t: indicadores_tecnicos(ohlcv[t]) for t in TICKERS}

    # [5/7] Noticias
    print("[5/7] Noticias + sentimiento...")
    noticias, detalle_noticias = {}, {}
    for t in TICKERS:
        noticias[t], detalle_noticias[t] = metricas_noticias(t)
        print("    %s: %d noticias | score neto %+d (bullish %d / bearish %d)"
              % (t, noticias[t]["noticias_total"], noticias[t]["score_neto"],
                 noticias[t]["bullish"], noticias[t]["bearish"]))

    # [6/7] DataFrame único
    print("[6/7] Armando DataFrame comparativo...")
    d, f, q, n = fondos, tecnicos, dists, noticias
    filas = [
        # PERFIL
        fila("PERFIL", "Nombre", d["MU"]["nombre"], d["AMD"]["nombre"]),
        fila("PERFIL", "Sector", d["MU"]["sector"], d["AMD"]["sector"]),
        fila("PERFIL", "Industria", d["MU"]["industria"], d["AMD"]["industria"]),
        fila("PERFIL", "Precio actual (USD)", q["MU"].current_price, q["AMD"].current_price),
        fila("PERFIL", "Market Cap (B USD)", d["MU"]["market_cap_B"], d["AMD"]["market_cap_B"]),
        # CUANTITATIVO (3y)
        fila("CUANTITATIVO 3Y", "Retorno anualizado", q["MU"].mean_annual, q["AMD"].mean_annual),
        fila("CUANTITATIVO 3Y", "Volatilidad anualizada", q["MU"].volatility_annual, q["AMD"].volatility_annual),
        fila("CUANTITATIVO 3Y", "Sharpe ratio", round(q["MU"].sharpe_ratio, 3), round(q["AMD"].sharpe_ratio, 3)),
        fila("CUANTITATIVO 3Y", "VaR diario 95%", round(q["MU"].var_95, 4), round(q["AMD"].var_95, 4)),
        fila("CUANTITATIVO 3Y", "Max drawdown", round(q["MU"].max_drawdown, 4), round(q["AMD"].max_drawdown, 4)),
        fila("CUANTITATIVO 3Y", "Skewness", round(q["MU"].skewness, 3), round(q["AMD"].skewness, 3)),
        fila("CUANTITATIVO 3Y", "Kurtosis (exceso)", round(q["MU"].kurtosis, 3), round(q["AMD"].kurtosis, 3)),
        fila("CUANTITATIVO 3Y", "p-value Jarque-Bera", round(q["MU"].p_value, 4), round(q["AMD"].p_value, 4)),
        fila("CUANTITATIVO 3Y", "Distribución normal (5%)", q["MU"].is_normal, q["AMD"].is_normal),
    ]
    for b in BENCHMARKS:
        m, a = capms[("MU", b)], capms[("AMD", b)]
        filas += [
            fila("CUANTITATIVO 3Y", "Beta vs " + BENCHMARKS[b], round(m.beta, 3), round(a.beta, 3)),
            fila("CUANTITATIVO 3Y", "Alpha anual vs " + BENCHMARKS[b], round(m.alpha * 252, 4), round(a.alpha * 252, 4)),
            fila("CUANTITATIVO 3Y", "R² vs " + BENCHMARKS[b], round(m.r_squared, 3), round(a.r_squared, 3)),
        ]
    filas += [
        fila("CUANTITATIVO 3Y", "Correlación MU-AMD (par)", round(sr["corr"], 3), round(sr["corr"], 3)),
        fila("CUANTITATIVO 3Y", "Z-score ratio MU/AMD (12M)", round(sr["z"], 2), round(sr["z"], 2)),
        fila("CUANTITATIVO 3Y", "Percentil ratio MU/AMD (12M)", round(sr["pct"], 1), round(sr["pct"], 1)),
        # FUNDAMENTAL
        fila("FUNDAMENTAL", "P/E trailing", d["MU"]["pe_trailing"], d["AMD"]["pe_trailing"]),
        fila("FUNDAMENTAL", "P/E forward", d["MU"]["pe_forward"], d["AMD"]["pe_forward"]),
        fila("FUNDAMENTAL", "PEG (trailing)", d["MU"]["peg"], d["AMD"]["peg"]),
        fila("FUNDAMENTAL", "P/S", d["MU"]["ps"], d["AMD"]["ps"]),
        fila("FUNDAMENTAL", "P/B", d["MU"]["pb"], d["AMD"]["pb"]),
        fila("FUNDAMENTAL", "EV/EBITDA", d["MU"]["ev_ebitda"], d["AMD"]["ev_ebitda"]),
        fila("FUNDAMENTAL", "Dividend yield (%)", d["MU"]["div_yield_pct"], d["AMD"]["div_yield_pct"]),
        fila("FUNDAMENTAL", "P/E aprox. actual (precio/EPS TTM)", d["MU"]["pe_actual_aprox"], d["AMD"]["pe_actual_aprox"]),
        fila("FUNDAMENTAL", "Percentil P/E histórico 3y (%)", d["MU"]["pe_percentil_hist"], d["AMD"]["pe_percentil_hist"]),
        fila("FUNDAMENTAL", "Margen bruto", d["MU"]["margen_bruto_pct"], d["AMD"]["margen_bruto_pct"]),
        fila("FUNDAMENTAL", "Margen operativo", d["MU"]["margen_op_pct"], d["AMD"]["margen_op_pct"]),
        fila("FUNDAMENTAL", "Margen neto", d["MU"]["margen_neto_pct"], d["AMD"]["margen_neto_pct"]),
        fila("FUNDAMENTAL", "ROE", d["MU"]["roe"], d["AMD"]["roe"]),
        fila("FUNDAMENTAL", "ROA", d["MU"]["roa"], d["AMD"]["roa"]),
        fila("FUNDAMENTAL", "ROE DuPont", d["MU"]["roe_dupont"], d["AMD"]["roe_dupont"]),
        fila("FUNDAMENTAL", "Deuda/Patrimonio", d["MU"]["deuda_patrimonio"], d["AMD"]["deuda_patrimonio"]),
        fila("FUNDAMENTAL", "Deuda/EBITDA", d["MU"]["deuda_ebitda"], d["AMD"]["deuda_ebitda"]),
        fila("FUNDAMENTAL", "Liquidez corriente", d["MU"]["razon_corriente"], d["AMD"]["razon_corriente"]),
        fila("FUNDAMENTAL", "Prueba ácida", d["MU"]["prueba_acida"], d["AMD"]["prueba_acida"]),
        fila("FUNDAMENTAL", "FCF (B USD)", d["MU"]["fcf_B"], d["AMD"]["fcf_B"]),
        fila("FUNDAMENTAL", "FCF/Ingresos", d["MU"]["fcf_ingresos"], d["AMD"]["fcf_ingresos"]),
        fila("FUNDAMENTAL", "Crecimiento ingresos YoY", d["MU"]["crec_ingresos_pct"], d["AMD"]["crec_ingresos_pct"]),
        fila("FUNDAMENTAL", "Altman Z", d["MU"]["altman_z"], d["AMD"]["altman_z"]),
        fila("FUNDAMENTAL", "Zona Altman", d["MU"]["altman_zona"], d["AMD"]["altman_zona"]),
        fila("FUNDAMENTAL", "Target price analistas (USD)", d["MU"]["target_price"], d["AMD"]["target_price"]),
        fila("FUNDAMENTAL", "Upside a target (%)", d["MU"]["upside_pct"], d["AMD"]["upside_pct"]),
        # TÉCNICO
        fila("TECNICO", "SMA20 (USD)", round(f["MU"]["sma20"], 2), round(f["AMD"]["sma20"], 2)),
        fila("TECNICO", "SMA50 (USD)", round(f["MU"]["sma50"], 2), round(f["AMD"]["sma50"], 2)),
        fila("TECNICO", "SMA200 (USD)", round(f["MU"]["sma200"], 2), round(f["AMD"]["sma200"], 2)),
        fila("TECNICO", "Tendencia (vs SMA200)", f["MU"]["tendencia"], f["AMD"]["tendencia"]),
        fila("TECNICO", "Cruce SMA50/200", f["MU"]["cruce_50_200"], f["AMD"]["cruce_50_200"]),
        fila("TECNICO", "RSI14", round(f["MU"]["rsi14"], 1), round(f["AMD"]["rsi14"], 1)),
        fila("TECNICO", "RSI zona", f["MU"]["rsi_zona"], f["AMD"]["rsi_zona"]),
        fila("TECNICO", "MACD línea", round(f["MU"]["macd"], 3), round(f["AMD"]["macd"], 3)),
        fila("TECNICO", "MACD señal", round(f["MU"]["macd_senal"], 3), round(f["AMD"]["macd_senal"], 3)),
        fila("TECNICO", "MACD histograma", round(f["MU"]["macd_hist"], 3), round(f["AMD"]["macd_hist"], 3)),
        fila("TECNICO", "Bollinger %B (0-1)", round(f["MU"]["bollinger_pctb"], 2), round(f["AMD"]["bollinger_pctb"], 2)),
        fila("TECNICO", "ATR14 (USD)", round(f["MU"]["atr14"], 2), round(f["AMD"]["atr14"], 2)),
        fila("TECNICO", "ATR14 (% precio)", round(f["MU"]["atr14_pct"], 2), round(f["AMD"]["atr14_pct"], 2)),
        fila("TECNICO", "ADX14", round(f["MU"]["adx14"], 1), round(f["AMD"]["adx14"], 1)),
        fila("TECNICO", "Régimen ADX", f["MU"]["adx_zona"], f["AMD"]["adx_zona"]),
        fila("TECNICO", "Posición rango 52s (%)", round(f["MU"]["rango_52s_pct"], 1), round(f["AMD"]["rango_52s_pct"], 1)),
        fila("TECNICO", "Distancia a máximo 52s (%)", round(f["MU"]["dist_max_52s_pct"], 1), round(f["AMD"]["dist_max_52s_pct"], 1)),
        fila("TECNICO", "Momentum 1M (%)", round(f["MU"]["momentum_1M"], 1), round(f["AMD"]["momentum_1M"], 1)),
        fila("TECNICO", "Momentum 3M (%)", round(f["MU"]["momentum_3M"], 1), round(f["AMD"]["momentum_3M"], 1)),
        fila("TECNICO", "Momentum 6M (%)", round(f["MU"]["momentum_6M"], 1), round(f["AMD"]["momentum_6M"], 1)),
        fila("TECNICO", "Momentum 12M (%)", round(f["MU"]["momentum_12M"], 1), round(f["AMD"]["momentum_12M"], 1)),
        fila("TECNICO", "Volumen relativo (vs 20d)", round(f["MU"]["vol_relativa"], 2), round(f["AMD"]["vol_relativa"], 2)),
        # NOTICIAS
        fila("NOTICIAS", "Noticias analizadas", n["MU"]["noticias_total"], n["AMD"]["noticias_total"]),
        fila("NOTICIAS", "Score neto sentimiento", n["MU"]["score_neto"], n["AMD"]["score_neto"]),
        fila("NOTICIAS", "Bullish", n["MU"]["bullish"], n["AMD"]["bullish"]),
        fila("NOTICIAS", "Bearish", n["MU"]["bearish"], n["AMD"]["bearish"]),
        fila("NOTICIAS", "Neutrales", n["MU"]["neutrales"], n["AMD"]["neutrales"]),
    ]
    df_comparacion = pd.DataFrame(filas)

    # [7/7] Salida
    print("[7/7] Guardando y mostrando resultados...\n")
    out_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparacion_mu_amd.csv")
    df_comparacion.to_csv(out_csv, index=False, encoding="utf-8-sig")

    df_metricas_individuales = pd.DataFrame([
        {
            "ticker": t,
            "current_price": dists[t].current_price,
            "min_price_3y": dists[t].min_price,
            "max_price_3y": dists[t].max_price,
            "mean_annual": dists[t].mean_annual,
            "volatility_annual": dists[t].volatility_annual,
            "sharpe_ratio": dists[t].sharpe_ratio,
            "var_95_daily": dists[t].var_95,
            "max_drawdown": dists[t].max_drawdown,
            "skewness": dists[t].skewness,
            "kurtosis": dists[t].kurtosis,
            "jb_p_value": dists[t].p_value,
            "is_normal": dists[t].is_normal,
        }
        for t in TICKERS
    ])
    csv_ind = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metricas_individuales_mu_amd.csv")
    df_metricas_individuales.to_csv(csv_ind, index=False, encoding="utf-8-sig")

    # Impresión por bloques
    def fmt(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "N/D"
        if isinstance(v, bool):
            return "SÍ" if v else "NO"
        if isinstance(v, float):
            return "{:,.4f}".format(v) if abs(v) < 10 else "{:,.2f}".format(v)
        return str(v)

    for seccion in df_comparacion["seccion"].unique():
        bloque = df_comparacion[df_comparacion["seccion"] == seccion]
        vista = bloque.copy()
        for col in ("MU", "AMD"):
            vista[col] = bloque[col].map(fmt)
        print("=" * 90)
        print(seccion)
        print("=" * 90)
        print(vista[["metrica", "MU", "AMD"]].to_string(index=False))
        print()

    print("Detalle noticias:")
    for t in TICKERS:
        print("  --- %s ---" % t)
        for fecha, titulo, s in detalle_noticias[t][:5]:
            etiqueta = {1: "[+]", -1: "[-]", 0: "[=]"}.get(s, "[=]")
            print("    [%s] %s %s" % (etiqueta, fecha, titulo[:80]))

    print("\nArchivos guardados:\n  - %s\n  - %s" % (out_csv, csv_ind))
    return df_comparacion


if __name__ == "__main__":
    df_comp = main()
