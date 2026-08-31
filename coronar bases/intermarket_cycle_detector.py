#!/usr/bin/env python3
"""
INTERMARKET CYCLE DETECTOR — v3.0 (INTEGRADO)
================================================
Unifica en UN solo script:
  • Ratios intermarket (Murphy) — 10 ratios clave
  • Fase del ciclo económico (Pring + Murphy por convergencia)
  • Ciclo de crédito corporativo (spreads, percentiles históricos)
  • Rotación sectorial (Stovall + Murphy) con validación crediticia
  • Correlaciones históricas, leading indicators, detección de estrés
  • Diagnóstico integrado vs. condiciones reales de mercado

Uso:  python intermarket_cycle_detector.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import feedparser
import requests
import re
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
LOOKBACK = 252
START_DATE = "2007-01-01"   # Desde GFC hasta hoy (necesario para percentiles)
END_DATE = datetime.today().strftime("%Y-%m-%d")

# Umbrales de riesgo crediticio
CREDIT_WARNING_PCT = 90   # Percentil a partir del cual se activa alerta de crédito
CREDIT_CRITICAL_PCT = 95  # Percentil de alerta crítica

# ============================================================================
# TICKERS — COMPLETO
# ============================================================================

MACRO = {
    "DX-Y.NYB": "Dólar Index (DXY)",
    "^VIX":     "VIX (Volatilidad)",
    "TIP":      "TIPS (Inflación)",
}

BONDS = {
    "IEF": "Bonos 7-10Y (Medio)",
    "TLT": "Bonos 20+Y (Largo)",
    "BIL": "Bonos 1-3M (Corto Tesoro)",
    "HYG": "High Yield Corporativo",
    "LQD": "Investment Grade Corp.",
}

COMMODITIES = {
    "GSG":   "GSCI All Commodities",
    "USO":   "Petróleo WTI",
    "UNG":   "Gas Natural",
    "GLD":   "Oro",
    "SLV":   "Plata",
    "DBA":   "Agricultura",
    "COPX":  "Cobre",
    "LIT":   "Litio",
    "JJN":   "Níquel",
    "JJC":   "Cobre Físico",
}

SECTORS = {
    "XLF": "Finanzas",
    "XLV": "Salud",
    "XLE": "Energía",
    "XLC": "Comunicación",
    "XLY": "Consumo Discrecional",
    "XLP": "Consumo Básico (Staples)",
    "XLI": "Industrial",
    "XLB": "Materiales",
    "XLRE": "Inmobiliario",
    "XLU": "Utilities",
    "XLK": "Tecnología",
}

EQUITY = {
    "SPY":  "S&P 500",
    "DIA":  "Dow Industrial",
    "QQQ":  "NASDAQ QQQ",
    "IWM":  "Russell 2000 (Small Caps)",
    "IYT":  "Dow Transports",
    "XRT":  "S&P Retail ETF",
    "RSP":  "S&P 500 Equal Weight",
}

GLOBAL = {
    "EFA": "Desarrollados ex-US",
    "EEM": "Emerging Markets",
    "EWW": "MSCI México",
    "EWZ": "MSCI Brasil",
}

STYLE = {
    "IVE": "S&P 500 Value",
    "IVW": "S&P 500 Growth",
    "QUAL": "Calidad",
    "MTUM": "Momentum",
}

ALL_TICKERS = list(dict.fromkeys(
    list(MACRO.keys()) + list(BONDS.keys()) + list(COMMODITIES.keys()) +
    list(SECTORS.keys()) + list(EQUITY.keys()) + list(GLOBAL.keys()) +
    list(STYLE.keys())
))

# ============================================================================
# 2. DESCARGA
# ============================================================================
print("=" * 72)
print("  INTERMARKET CYCLE DETECTOR — v3.0 INTEGRADO")
print("  Murphy + Pring + Stovall + Crédito + Liquidez")
print("=" * 72)
print(f"\n  Descargando {len(ALL_TICKERS)} tickers desde {START_DATE}...\n")

df_raw = yf.download(ALL_TICKERS, start=START_DATE, end=END_DATE,
                      progress=False, auto_adjust=True)
if isinstance(df_raw.columns, pd.MultiIndex):
    df = df_raw["Close"].copy()
else:
    df = df_raw.copy()

df.columns = [str(c).strip() for c in df.columns]
present = [t for t in ALL_TICKERS if t in df.columns and df[t].dropna().shape[0] > 20]
print(f"  Tickers disponibles: {len(present)}/{len(ALL_TICKERS)}")
for t in ALL_TICKERS:
    if t not in present:
        print(f"    ⚠️  No disponible: {t}")

if len(present) < 10:
    print("ERROR: muy pocos datos. Verifica conexión.")
    exit(1)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def safe_trend(ser, lb=LOOKBACK):
    if ser is None or len(ser.dropna()) < 60:
        return None
    s = ser.dropna().tail(min(lb, len(ser.dropna())))
    if len(s) < 60:
        return None
    x = np.arange(len(s))
    slope = np.polyfit(x, s.values, 1)[0]
    chg = (s.iloc[-1] / s.iloc[0] - 1) * 100
    if slope > 0 and chg > 2:
        return "up"
    elif slope < 0 and chg < -2:
        return "down"
    return "flat"

def fmt_trend(ser, lb=LOOKBACK):
    if ser is None:
        return "⚪ Sin datos"
    s = ser.dropna()
    if len(s) < 60:
        return "⚪ Insuf."
    tr = safe_trend(ser, lb)
    chg = (s.iloc[-1] / s.iloc[-min(lb, len(s))] - 1) * 100 if len(s) >= 60 else 0
    if tr == "up":
        return f"🟢 Alcista ({chg:+.1f}%)"
    elif tr == "down":
        return f"🔴 Bajista ({chg:+.1f}%)"
    return f"⚪ Lateral ({chg:+.1f}%)"

def cross_signal(ser, fast=50, slow=200):
    if ser is None or len(ser.dropna()) < slow + 5:
        return "⚪"
    s = ser.dropna()
    mf = s.rolling(fast, min_periods=max(fast//2, 10)).mean()
    ms = s.rolling(slow, min_periods=max(slow//2, 30)).mean()
    if mf.iloc[-1] > ms.iloc[-1] and mf.iloc[-2] <= ms.iloc[-2]:
        return "🟢 Cruce alcista ↑"
    if mf.iloc[-1] < ms.iloc[-1] and mf.iloc[-2] >= ms.iloc[-2]:
        return "🔴 Cruce bajista ↓"
    if mf.iloc[-1] > ms.iloc[-1]:
        return "🟢 Alcista"
    if mf.iloc[-1] < ms.iloc[-1]:
        return "🔴 Bajista"
    return "⚪"

def trend_to_num(t):
    return 1 if t == "up" else (-1 if t == "down" else 0)

def percentile_rank(ser, current_val=None):
    s = ser.dropna()
    if len(s) < 10:
        return None
    val = current_val if current_val is not None else s.iloc[-1]
    return (s[s <= val].count() / len(s)) * 100

def regime_avg(ser, start, end=None):
    if ser is None:
        return None
    s = ser.dropna()
    if end:
        masked = s.loc[start:end]
    else:
        masked = s.loc[start:]
    if len(masked) < 5:
        return None
    return masked.mean()

def get_tick(name):
    for t in present:
        if t == name:
            return t
    return None

# ============================================================================
# VALIDACIÓN CON NOTICIAS (RSS)
# ============================================================================

NEWS_CACHE = {}
YAHOO_FEED_CACHE = None

def fetch_yahoo_feed(max_results=10):
    """Fetch Yahoo Finance RSS feed once and cache it."""
    global YAHOO_FEED_CACHE
    if YAHOO_FEED_CACHE is not None:
        return YAHOO_FEED_CACHE
    try:
        resp = requests.get("https://finance.yahoo.com/news/rssindex", timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        feed = feedparser.parse(resp.text)
        results = []
        for entry in feed.entries[:max_results]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            pub = entry.get("published", "")
            results.append((title, link, pub))
        YAHOO_FEED_CACHE = results
        return results
    except Exception:
        YAHOO_FEED_CACHE = []
        return []

def fetch_news(query, max_results=2):
    """Busca noticias: intenta Google News RSS; fallback a Yahoo Finance."""
    if query in NEWS_CACHE:
        return NEWS_CACHE[query]
    results = []
    # Intento 1: Google News RSS
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=es-419&gl=MX&ceid=MX:es-419"
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:max_results]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            pub = entry.get("published", "")
            title_clean = re.sub(r'\s*[-–—]\s*[A-Za-zÀ-ÖØ-öø-ÿ\s]+$', '', title).strip()
            results.append((title_clean, link, pub))
    except Exception:
        pass
    
    # Intento 2: Si Google no dio resultados, usar Yahoo Finance (1 vez, cacheado)
    if len(results) == 0:
        yahoo_articles = fetch_yahoo_feed(max_results=10)
        # Escoger artículos que coincidan con la query
        q_words = set(query.lower().split())
        for title, link, pub in yahoo_articles:
            title_match = sum(1 for w in q_words if w in title.lower())
            if title_match >= 2:  # Al menos 2 palabras clave coinciden
                results.append((title, link, pub))
            if len(results) >= max_results:
                break
        # Si aún así no hay matches, tomar los primeros artículos generales
        if len(results) == 0 and yahoo_articles:
            for title, link, pub in yahoo_articles[:max_results]:
                results.append((title, link, pub))
    
    NEWS_CACHE[query] = results
    return results

def fetch_news_bulk(queries, max_per=3):
    """Fetch multiple queries in parallel using a single pass."""
    all_results = {}
    for q in queries:
        all_results[q] = fetch_news(q, max_per)
    return all_results

def evaluar_noticia(title, finding_type, finding_signal=""):
    """
    Evalúa si una noticia APOYA o CONTRADICE un hallazgo.
    Returns: 'support', 'contradict', 'neutral'
    """
    title_lower = title.lower()
    
    # Palabras clave por tipo de hallazgo (versión ampliada)
    support_kw = []
    contradict_kw = []
    
    if finding_type == "credit_complacency":
        support_kw = ["complacency", "complacencia", "tight spreads", "credit risk",
                       "credit spreads", "spread compression", "credit market",
                       "corporate bonds", "high yield", "investment grade",
                       "credito", "bonos corporativos", "spreads", "default",
                       "credit cycle", "late cycle credit", "junk bond",
                       "credit warning", "credit crisis", "debt market",
                       "riesgo crediticio", "mercado de credito", "bonos basura"]
        contradict_kw = ["credit improving", "spreads widening", "defaults falling",
                         "credito mejora", "spreads se amplian", "credit boom"]
    elif finding_type == "energy_over_tech":
        support_kw = ["energy", "oil", "petroleo", "petróleo", "crude", "brent",
                       "energia", "energía", "xle", "oil prices", "oil rally",
                       "energy sector", "oil market", "gasoline", "refinery",
                       "wti", "commodities energy", "fuel", "gas", "offshore",
                       "energy stock", "sector energetico", "petroleras",
                       "produccion de petroleo", "medio oriente", "middle east",
                       "iran", "hormuz"]
        contradict_kw = ["tech rebound", "technology rally", "tech leads",
                         "tecnologia recupera", "AI rally", "semiconductor",
                         "chip stock", "xlk", "big tech"]
    elif finding_type == "consumer_weakness":
        support_kw = ["consumer", "consumidor", "consumo", "retail",
                       "discretionary", "discrecional", "spending", "gasto",
                       "xly", "xlp", "consumer weakness", "consumer confidence",
                       "spending slowdown", "retail sales", "consumer cautious",
                       "gasto disminuye", "ventas minoristas", "comercio",
                       "shopping", "consumers pull back", "household",
                       "paycheck to paycheck", "price sensitivity",
                       "trading down", "essential purchases"]
        contradict_kw = ["consumer strength", "consumer spending surge",
                         "strong retail", "consumidor fuerte", "gasto aumenta",
                         "consumer boom", "retail boom"]
    elif finding_type == "industrial_expansion":
        support_kw = ["copper", "cobre", "industrial", "manufacturing",
                       "manufactura", "industrial metals", "metales",
                       "mining", "mineria", "minerals", "minerales",
                       "factory", "fabrica", "fabril", "production",
                       "produccion", "cobre", "copx", "jjc",
                       "industrial production", "pmi", "manufacturing pmi",
                       "supply chain", "cadena de suministro", "infrastructure",
                       "infraestructura", "construction", "construccion",
                       "critical minerals", "minerales criticos"]
        contradict_kw = ["industrial recession", "manufacturing contraction",
                         "recesion industrial", "factory shutdown",
                         "industrial decline"]
    elif finding_type == "dollar_commodities":
        support_kw = ["dollar", "dolar", "dólar", "commodities",
                       "inflation", "inflacion", "inflación", "cpi",
                       "fed", "federal reserve", "tasas", "rates",
                       "interest rate", "monetary policy", "politica monetaria",
                       "gold", "oro", "gld", "gsg", "commodity",
                       "brent", "wti", "crude", "precios", "prices",
                       "commodity rally", "rally commodities"]
        contradict_kw = ["dollar weakness", "commodities crash", "deflation",
                         "deflacion", "desinflacion", "disinflation"]
    elif finding_type == "late_cycle":
        support_kw = ["late cycle", "cycle peak", "market mature", "market top",
                       "ciclo tardio", "mercado maduro", "final de ciclo",
                       "peak cycle", "mature cycle", "late-cycle",
                       "bear market warning", "correction warning",
                       "recession warning", "recession risk",
                       "alerta recesion", "economic slowdown",
                       "desaceleracion", "desaceleración",
                       "economic uncertainty", "incertidumbre economica",
                       "stagflation", "estanflacion"]
        contradict_kw = ["early cycle", "new bull market", "expansion ahead",
                         "nuevo ciclo alcista", "economic boom",
                         "growth acceleration"]
    elif finding_type == "narrow_market":
        support_kw = ["narrow market", "mega caps", "mega-cap",
                       "concentration risk", "market breadth",
                       "few stocks", "mercado angosto", "market narrow",
                       "top heavy market", "market leadership narrow",
                       "s&p 500 concentration", "index concentration",
                       "technology concentration", "big tech dominance"]
        contradict_kw = ["broad market rally", "market width",
                         "participation broad", "rsp", "equal weight",
                         "market rally broad", "small caps lead",
                         "value stocks rally"]
    
    # Evaluar coincidencias
    support_score = sum(1 for kw in support_kw if kw in title_lower)
    contradict_score = sum(1 for kw in contradict_kw if kw in title_lower)
    
    if support_score > contradict_score:
        return "support"
    elif contradict_score > support_score:
        return "contradict"
    else:
        if support_score > 0:
            return "support"
        return "neutral"

def build_news_queries(FASE_DETECTADA, rotation_signals, credit_alert_level,
                       xly_xlp_t, gsg, dxy, vix, df, safe_trend, ig_pct, hy_pct):
    """Genera las queries de búsqueda según los hallazgos del análisis."""
    queries = []
    query_labels = []
    
    fn = FASE_DETECTADA.get("fase_num")
    fname = FASE_DETECTADA.get("fase_nombre", "")
    
    # Query 1: Por fase detectada
    if credit_alert_level == "CRITICAL":
        queries.append("credit spreads complacency corporate bonds late cycle 2026")
        query_labels.append(("credit_complacency", "🔴 Crédito en complacencia extrema"))
    elif fn is not None and fn >= 3:
        queries.append("late cycle economy risks 2026")
        query_labels.append(("late_cycle", "🔍 Fase tardía del ciclo"))
    else:
        queries.append("economic expansion growth outlook 2026")
        query_labels.append(("late_cycle", "📈 Expansión económica"))
    
    # Query 2: Energy > Tech (de rotation_signals)
    has_energy_over_tech = any("Energy > Tech" in s[2] for s in rotation_signals)
    if has_energy_over_tech:
        queries.append("energy sector outperformance oil rally 2026")
        query_labels.append(("energy_over_tech", "🛢️ Energy > Tech (late cycle)"))
    else:
        queries.append("technology sector leads market 2026")
        query_labels.append(("energy_over_tech", "💻 Tech lidera mercado"))
    
    # Query 3: Consumidor
    if xly_xlp_t == "down":
        queries.append("consumer discretionary weakness spending slowdown 2026")
        query_labels.append(("consumer_weakness", "🛍️ Consumidor débil (XLY/XLP ↓)"))
    else:
        queries.append("consumer confidence spending growth 2026")
        query_labels.append(("consumer_weakness", "🛍️ Consumidor fuerte"))
    
    # Query 4: Cobre / Industrial (si copper>gold)
    has_copper = any("Copper > Gold" in s[2] for s in rotation_signals)
    if has_copper:
        queries.append("copper industrial metals demand manufacturing 2026")
        query_labels.append(("industrial_expansion", "🥉 Cobre lidera (expansión industrial)"))
    
    # Query 5: Dólar + Commodities
    if gsg:
        gsg_t = safe_trend(df[gsg])
        if gsg_t == "up":
            queries.append("commodities rally energy prices inflation 2026")
            query_labels.append(("dollar_commodities", "📦 Commodities en rally"))
    
    # Query 6: VIX
    if vix:
        v_val = df[vix].dropna().iloc[-1]
        if v_val > 25:
            queries.append("market volatility uncertainty risk 2026")
            query_labels.append(("dollar_commodities", "😱 Volatilidad elevada"))
    
    # Mercado angosto
    has_narrow = any("angosto" in s[2] or "mega-caps" in s[2] for s in rotation_signals)
    if has_narrow:
        queries.append("narrow stock market mega cap concentration 2026")
        query_labels.append(("narrow_market", "🎯 Mercado angosto (solo mega-caps)"))
    
    return queries, query_labels


# ============================================================================
# PERFILES DE FASE (Murphy + Pring)
# ============================================================================

PHASE_PROFILES = [
    {"num": 0, "name": "Recession Bottom",
     "b": 1,  "s": -1, "c": -1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Bonos suben anticipando recorte. Stocks y commod caen.",
     "sectores_clave": "Bonos largos, Utilities, Staples, Salud, Oro"},
    {"num": 1, "name": "Early Recovery",
     "b": 1,  "s": 1,  "c": -1,
     "xly_xlp": 1,  "iwm_spy": 1,  "qqq_spy": 1,
     "desc": "Bonos y stocks suben. Comm débiles. Small caps lideran.",
     "sectores_clave": "Tech, Discrecional, Small Caps, Finanzas"},
    {"num": 2, "name": "Mid Expansion",
     "b": 0,  "s": 1,  "c": 1,
     "xly_xlp": 1,  "iwm_spy": 0,  "qqq_spy": 0,
     "desc": "Stocks fuertes, comm suben, bonos laterales. Industriales lideran.",
     "sectores_clave": "Industrial, Materiales, Finanzas, Cobre, Energía"},
    {"num": 3, "name": "Late Expansion",
     "b": -1, "s": 1,  "c": 1,
     "xly_xlp": 0,  "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Bonos caen (inflación). Comm fuertes. Energy lidera. Mercado angosto.",
     "sectores_clave": "Energía, Oro, Agricultura, Salud, Utilities"},
    {"num": 4, "name": "Early Contraction",
     "b": 0,  "s": -1, "c": 1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Stocks caen, comm aún firmes. Bonos rebotan.",
     "sectores_clave": "Salud, Staples, Utilities, Oro, Bonos largos"},
    {"num": 5, "name": "Full Contraction",
     "b": 1,  "s": -1, "c": -1,
     "xly_xlp": -1, "iwm_spy": -1, "qqq_spy": -1,
     "desc": "Todo cae excepto bonos largos. Cash.",
     "sectores_clave": "Bonos largos, Oro, Cash, VIX"},
]

def detect_murphy_phase(b, s, c, extra=None):
    """Encuentra la fase MÁS PROBABLE por distancia al perfil esperado."""
    current = {"b": trend_to_num(b), "s": trend_to_num(s), "c": trend_to_num(c)}
    if extra:
        for k in ["xly_xlp", "iwm_spy", "qqq_spy"]:
            if k in extra and extra[k] is not None:
                current[k] = trend_to_num(extra[k])

    best, best_dist = None, 999
    for p in PHASE_PROFILES:
        ok = tot = 0
        dist = 0.0
        for key, val in current.items():
            if key in p and p[key] is not None:
                tot += 1
                ex = p[key]
                match = (val == ex) or (ex == 0 and abs(val) <= 1) or (val == 0 and abs(ex) <= 1)
                if match:
                    ok += 1
                    dist += abs(val - ex) * 0.3
                else:
                    dist += abs(val - ex)
        avg_d = dist / tot if tot else 99
        if avg_d < best_dist:
            best_dist = avg_d
            pct = ok / tot * 100 if tot else 0
            best = (p["num"], p["name"],
                    "🟢 ALTA" if pct >= 80 else ("🟡 MEDIA" if pct >= 60 else
                    "🟠 BAJA" if pct >= 40 else "🔴 MUY BAJA"),
                    ok, tot, avg_d)
    return best

# Rotación sectorial por fase (Murphy + Stovall + Pring)
SECTOR_ROTATION = {
    0: {"nombre": "RECESSION BOTTOM", "ico": "🔴",
        "comprar": ["TLT/IEF (Bonos largos)", "XLU (Utilities)", "XLP (Staples)",
                     "XLV (Salud)", "GLD (Oro)", "BIL (Cash)"],
        "vender": ["XLK (Tech)", "XLY (Discrecional)", "XLE (Energía)", "XLF (Finanzas)"],
        "estilo": "Value defensivo / Baja Beta"},
    1: {"nombre": "EARLY RECOVERY", "ico": "🟢",
        "comprar": ["XLK (Tecnología)", "XLY (Cons. Discrecional)", "IWM (Small Caps)",
                     "XLF (Finanzas)", "QQQ (Nasdaq)"],
        "vender": ["XLP (Staples)", "XLU (Utilities)", "TLT (Bonos)"],
        "estilo": "Growth / Small Cap / Momentum"},
    2: {"nombre": "MID EXPANSION", "ico": "🟢",
        "comprar": ["XLI (Industrial)", "XLB (Materiales)", "XLF (Finanzas)",
                     "COPX/JJC (Cobre)", "XLE (Energía)"],
        "vender": ["TLT (Bonos)", "XLU (Utilities)", "XLP (Staples)"],
        "estilo": "Cíclico Industrial / Value"},
    3: {"nombre": "LATE EXPANSION", "ico": "🟡",
        "comprar": ["XLE (Energía)", "GLD (Oro)", "DBA (Agricultura)",
                     "XLV (Salud)", "XLU (Utilities)", "BIL/SGOV (T-bills)"],
        "vender": ["XLK (Tech)", "XLY (Discrecional)", "IWM (Small Caps)",
                    "LQD (IG Corp)", "HYG (High Yield)"],
        "estilo": "Commodities / Energía / Cobertura inflación / Defensivo"},
    4: {"nombre": "EARLY CONTRACTION", "ico": "🔴",
        "comprar": ["XLV (Salud)", "XLP (Staples)", "XLU (Utilities)",
                     "GLD (Oro)", "TLT (Bonos)", "BIL (T-bills)"],
        "vender": ["XLK (Tech)", "XLY (Discrecional)", "XLE (Energía)",
                    "XLB (Materiales)", "HYG (High Yield)"],
        "estilo": "Defensivo / Healthcare / Oro / Cash"},
    5: {"nombre": "FULL CONTRACTION", "ico": "🔴🔴",
        "comprar": ["TLT/IEF (Bonos)", "GLD (Oro)", "BIL/SHV (Cash)", "VIX (Hedge)"],
        "vender": ["Todo: stocks, commod, crédito"],
        "estilo": "Cash / Bonos / Volatilidad"},
}

# ============================================================================
# 3. RATIOS INTERMARKET (Murphy)
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 1 — RATIOS INTERMARKET CLAVE (Murphy)")
print("─" * 72)

ratios = {}
t = get_tick

# --- A) CRB/Bond: GSG ÷ TLT ---
gsg = t("GSG"); tlt = t("TLT")
crb_bond = None
if gsg and tlt:
    ratio = df[gsg] / df[tlt]
    rat_name = "GSG/TLT (Commodities/Bonos proxy)"
    ratios[rat_name] = ratio
    crb_bond = ratio
    print(f"\n  📊 {rat_name}")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Señal:        {cross_signal(ratio)}")
    pct = (ratio.dropna().iloc[-1] / ratio.dropna().iloc[-min(252, len(ratio.dropna()))] - 1) * 100 if len(ratio.dropna()) > 60 else 0
    if pct > 5:
        print(f"     → Sube (+{pct:.0f}% 1yr): Commodities > Bonos. Inflación. ⚠️")
        print(f"     → Murphy: commodities > bonos = inflación de demanda o temor inflacionario")
    elif pct < -5:
        print(f"     → Baja ({pct:.0f}% 1yr): Bonos > Commodities. Desinflación. ✅")
        print(f"     → Murphy: bonos > commodities = desinflación, buen entorno para bonds")
    else:
        print(f"     → Neutral")

# --- B) Cyclical/Staples: XLY ÷ XLP ---
xly = t("XLY"); xlp = t("XLP")
if xly and xlp:
    ratio = df[xly] / df[xlp]
    rat_name = "Cyclical/Staples (XLY÷XLP)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Confianza consumidor / fase ciclo")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Señal:        {cross_signal(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Ciclo EXPANSIVO — Consumidor confiado, gasta en discrecional")
        print(f"     → Murphy: señal de early/mid expansion")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Ciclo CONTRACTIVO — Miedo, refugio en Staples")
        print(f"     → Murphy: señal de late expansion o contracción entrante")
        print(f"     → ⚠️ ESTA SEÑAL DEBERÍA DOMINAR otras señales expansivas")
    else:
        print(f"     → ⚪ Neutral")

# --- C) Small/Large Cap: IWM ÷ SPY ---
iwm = t("IWM"); spy = t("SPY")
if iwm and spy:
    ratio = df[iwm] / df[spy]
    rat_name = "Small/Large Cap (IWM÷SPY)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Señal de recovery")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Señal:        {cross_signal(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Small caps lideran → Recovery post-recesión")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Large caps dominan → Aversión al riesgo / late cycle")
    else:
        print(f"     → ⚪ Neutral")

# --- D) Transports/Industrial: IYT ÷ DIA ---
iyt = t("IYT"); dia = t("DIA")
if iyt and dia:
    ratio = df[iyt] / df[dia]
    rat_name = "Transports/Industrial (IYT÷DIA)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Dow Theory + ciclo")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Transports fuertes → petróleo bajo, economía activa")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Transports débiles → petróleo caro, economía débil")
    else:
        print(f"     → ⚪ Neutral")

# --- E) Discretionary/S&P: XLY ÷ SPY ---
if xly and spy:
    ratio = df[xly] / df[spy]
    rat_name = "Discretionary/S&P 500 (XLY÷SPY)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Confianza consumidor")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Gasto discrecional fuerte → economía mejorando")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Consumidor en modo ahorro → precaución")
    else:
        print(f"     → ⚪ Neutral")

# --- F) Nasdaq/S&P 500: QQQ ÷ SPY ---
qqq = t("QQQ")
if qqq and spy:
    ratio = df[qqq] / df[spy]
    rat_name = "Nasdaq/S&P 500 (QQQ÷SPY)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Liderazgo tecnológico")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Tecnología lidera → Early Expansion")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Tecnología débil → Late Exp. o Contracción")
    else:
        print(f"     → ⚪ Neutral")

# --- G) Gold/Oil Ratio: GLD ÷ USO ---
gld = t("GLD"); uso = t("USO")
if gld and uso:
    ratio = df[gld] / df[uso]
    rat_name = "Gold/Oil (GLD÷USO)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Inflación de demanda vs incertidumbre")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Oro > Petróleo: miedo / incertidumbre geopolítica")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Petróleo > Oro: inflación de demanda, economía activa")
    else:
        print(f"     → ⚪ Neutral")

# --- H) Developed/Emerging: EFA ÷ EEM ---
efa = t("EFA"); eem = t("EEM")
if efa and eem:
    ratio = df[efa] / df[eem]
    rat_name = "Developed/Emerging (EFA÷EEM)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Rotación global")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Desarrollados > Emergentes: flight to quality")
    elif safe_trend(ratio) == "down":
        print(f"     → 🟢 Emergentes > Desarrollados: risk-on global")
    else:
        print(f"     → ⚪ Neutral")

# --- I) Yield Curve Proxy: IEF ÷ BIL ---
ief = t("IEF"); bil = t("BIL")
if ief and bil:
    ratio = df[ief] / df[bil]
    rat_name = "Yield Curve Proxy (IEF÷BIL)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Pendiente de curva (inversión)")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "down":
        print(f"     → ⚠️  CURVA INVIRTIÉNDOSE (IEF débil vs BIL) — señal recesión")
    elif safe_trend(ratio) == "up":
        print(f"     → 🟢 Curva normalizándose (IEF fuerte) — salud")
    else:
        print(f"     → ⚪ Estable — sin pendiente clara")

# --- J) Growth/Value ---
ivw = t("IVW"); ive = t("IVE")
if ivw and ive:
    ratio = df[ivw] / df[ive]
    rat_name = "Growth/Value (IVW÷IVE)"
    ratios[rat_name] = ratio
    print(f"\n  📊 {rat_name} — Estilo de mercado")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    if safe_trend(ratio) == "up":
        print(f"     → 🟢 Growth lidera (risk-on, típico expansión)")
    elif safe_trend(ratio) == "down":
        print(f"     → 🔴 Value lidera (cautela, típico contracción)")
    else:
        print(f"     → ⚪ Neutral")

# ============================================================================
# 4. CICLO DE CRÉDITO (Spreads Corporativos)
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 2 — CICLO DE CRÉDITO CORPORATIVO (Spreads)")
print("─" * 72)

# Obtener tickers de crédito
hyg_t = t("HYG")
lqd_t = t("LQD")
hyg_ser = df[hyg_t] if hyg_t else None
lqd_ser = df[lqd_t] if lqd_t else None
ief_ser = df[ief] if ief else None

# IG Spread Proxy: LQD/IEF
ig_pct = None
ig_spread_proxy = None
if lqd_t and ief:
    ig_spread_proxy = df[lqd_t] / df[ief]
    ig_pct = percentile_rank(ig_spread_proxy)
    ig_current = ig_spread_proxy.dropna().iloc[-1]
    print(f"\n  📊 LQD/IEF (IG Spread Proxy) — Riesgo de Investment Grade")
    print(f"     Relación:  Ratio ALTO = spread COMPRIMIDO (complacencia)")
    print(f"                Ratio BAJO  = spread AMPLIO (estrés)")
    print(f"     Valor:     {ig_current:.4f}")
    print(f"     Percentil: {ig_pct:.1f}% (desde {START_DATE})")
    if ig_pct is not None and ig_pct >= CREDIT_CRITICAL_PCT:
        print(f"     ⚠️⚠️  ** CRÍTICO ** — IG en percentil {ig_pct:.0f} — COMPLACENCIA EXTREMA")
        print(f"     → Desde 1997 no se veía este nivel de compresión (Report #63: 80 bps OAS)")
    elif ig_pct is not None and ig_pct >= CREDIT_WARNING_PCT:
        print(f"     ⚠️  IG elevado (percentil {ig_pct:.0f}) — complacencia elevada")
    elif ig_pct is not None and ig_pct < 20:
        print(f"     🔴 IG amplio (percentil {ig_pct:.0f}) — estrés")
    else:
        print(f"     → IG neutral (percentil {ig_pct:.0f})")
    
    # Comparación histórica
    gfc_ig = regime_avg(ig_spread_proxy, "2007-09-01", "2009-06-30")
    cov_ig = regime_avg(ig_spread_proxy, "2020-02-01", "2020-06-30")
    now_ig = ig_spread_proxy.dropna().iloc[-min(21, len(ig_spread_proxy.dropna())):].mean() if len(ig_spread_proxy.dropna()) > 20 else 0
    print(f"     vs GFC 2008:  {gfc_ig:.4f}  vs COVID 2020: {cov_ig:.4f}  vs HOY: {now_ig:.4f}")

# HY Spread Proxy: HYG/IEF
hy_pct = None
hy_spread_proxy = None
if hyg_t and ief:
    hy_spread_proxy = df[hyg_t] / df[ief]
    hy_pct = percentile_rank(hy_spread_proxy)
    hy_current = hy_spread_proxy.dropna().iloc[-1]
    print(f"\n  📊 HYG/IEF (HY Spread Proxy) — Riesgo de High Yield")
    print(f"     Valor:     {hy_current:.4f}")
    print(f"     Percentil: {hy_pct:.1f}% (desde {START_DATE})")
    if hy_pct is not None and hy_pct >= CREDIT_CRITICAL_PCT:
        print(f"     ⚠️⚠️  ** CRÍTICO ** — HY en percentil {hy_pct:.0f} — COMPLACENCIA EXTREMA")
        print(f"     → Report #63: HY OAS en 269 bps — más ajustado que pre-GFC 2007")
    elif hy_pct is not None and hy_pct >= CREDIT_WARNING_PCT:
        print(f"     ⚠️  HY elevado (percentil {hy_pct:.0f})")
    elif hy_pct is not None and hy_pct < 20:
        print(f"     🔴 HY amplio (percentil {hy_pct:.0f}) — estrés")
    else:
        print(f"     → HY neutral (percentil {hy_pct:.0f})")
    
    gfc_hy = regime_avg(hy_spread_proxy, "2007-09-01", "2009-06-30")
    cov_hy = regime_avg(hy_spread_proxy, "2020-02-01", "2020-06-30")
    now_hy = hy_spread_proxy.dropna().iloc[-min(21, len(hy_spread_proxy.dropna())):].mean() if len(hy_spread_proxy.dropna()) > 20 else 0
    print(f"     vs GFC 2008: {gfc_hy:.4f}  vs COVID 2020: {cov_hy:.4f}  vs HOY: {now_hy:.4f}")

# Risk Appetite: HYG/LQD
ra_trend = None
risk_appetite = None
if hyg_t and lqd_t:
    risk_appetite = df[hyg_t] / df[lqd_t]
    ra_trend = safe_trend(risk_appetite)
    ra_pct = percentile_rank(risk_appetite)
    print(f"\n  📊 HYG/LQD (Risk Appetite) — Apetito de riesgo crediticio")
    print(f"     Tendencia:  {fmt_trend(risk_appetite)}")
    print(f"     Percentil:  {ra_pct:.1f}%")
    if ra_trend == "up":
        print(f"     → 🟢 HY > IG: risk-on. Inversores buscan rendimiento.")
    elif ra_trend == "down":
        print(f"     → 🔴 IG > HY: flight to quality. Miedo.")
    else:
        print(f"     → ⚪ Neutral")

# ALERTA DE CRÉDITO
print(f"\n  {'='*60}")
print(f"  💳 ALERTA DE CRÉDITO:")
credit_alert_level = "NONE"
if ig_pct is not None and hy_pct is not None:
    if ig_pct >= CREDIT_CRITICAL_PCT or hy_pct >= CREDIT_CRITICAL_PCT:
        credit_alert_level = "CRITICAL"
    elif ig_pct >= CREDIT_WARNING_PCT or hy_pct >= CREDIT_WARNING_PCT:
        credit_alert_level = "WARNING"
elif ig_pct is not None and ig_pct >= CREDIT_CRITICAL_PCT:
    credit_alert_level = "CRITICAL"
elif hy_pct is not None and hy_pct >= CREDIT_CRITICAL_PCT:
    credit_alert_level = "CRITICAL"

if credit_alert_level == "CRITICAL":
    print(f"     🔴🔴 ALERTA CRÍTICA — Crédito en complacencia extrema")
    print(f"     → IG: percentil {ig_pct:.0f}% | HY: percentil {hy_pct:.0f}%")
    print(f"     → Murphy: spreads extremos = señal de late cycle / final de ciclo")
    print(f"     → ESTA ALERTA DOMINA el diagnóstico económico")
elif credit_alert_level == "WARNING":
    print(f"     🟡 ALERTA — Crédito elevado")
    print(f"     → IG: percentil {ig_pct:.0f}% | HY: percentil {hy_pct:.0f}%")
else:
    print(f"     🟢 Sin alerta — crédito en zona normal")

# ============================================================================
# SEÑALES DE ROTACIÓN (Murphy) — 5 indicadores clave
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 2B — SEÑALES DE ROTACIÓN INTERMARKET (Murphy)")
print("─" * 72)

print(f"""
  Los 5 ratios que Murphy usa para detectar CAMBIOS de fase ANTES de que ocurran:
  ─────────────────────────────────────────────────────────────────────────────
  1. Copper/Gold (COPX/GLD)  — Dr. Copper: adelanta el ciclo industrial
  2. Bonds/Stocks (TLT/SPY)  — Rotación activos: risk-on vs risk-off
  3. Equal/Cap (RSP/SPY)     — Participación de mercado: ancho vs angosto
  4. Tech/Energy (XLK/XLE)   — Rotación sectorial: early vs late cycle
  5. Cyclical/Defensive       — Confianza: consumo vs proteccion
""")

# Para almacenar señales de rotación
rotation_signals = []
# Obtener referencias a tickers necesarios para rotacion
xlk = get_tick("XLK")
xle = get_tick("XLE")
rsp = get_tick("RSP")
copx = get_tick("COPX")
xli = get_tick("XLI")
xlu = get_tick("XLU")

# --- 1. COPPER/GOLD (COPX÷GLD) — Dr. Copper ---
if copx and gld:
    ratio = df[copx] / df[gld]
    rat_name = "Copper/Gold (COPX÷GLD)"
    trend = safe_trend(ratio)
    pct = percentile_rank(ratio)
    print(f"\n  📊 {rat_name} — 'Dr. Copper' (Murphy: mejor leading indicator)")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Percentil:    {pct:.1f}%")
    print(f"     Señal:        {cross_signal(ratio)}")
    if trend == "up":
        print(f"     → 🟢 Cobre > Oro: expansión industrial, crecimiento económico")
        print(f"     → Murphy: 'Cuando el cobre sube, las tasas subirán en 3-6 meses'")
        rotation_signals.append(("copx_gld", "🟢", "Copper > Gold: expansion industrial"))
    elif trend == "down":
        print(f"     → 🔴 Oro > Cobre: miedo, contracción industrial anticipada")
        print(f"     → ⚠️ Adelanta recesión por 3-6 meses")
        rotation_signals.append(("copx_gld", "🔴", "Gold > Copper: contraccion anticipada"))
    else:
        print(f"     → ⚪ Neutral")

    # Valor actual comparado con GFC y COVID
    now_val = ratio.dropna().iloc[-min(21, len(ratio.dropna())):].mean() if len(ratio.dropna()) > 20 else 0
    print(f"     Hoy (21d avg): {now_val:.4f}")

# --- 2. BONDS/STOCKS (TLT÷SPY) — Rotación de activos ---
if tlt and spy:
    ratio = df[tlt] / df[spy]
    rat_name = "Bonds/Stocks (TLT÷SPY)"
    trend = safe_trend(ratio)
    print(f"\n  📊 {rat_name} — Rotación de activos (Murphy: la relacion mas importante)")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Señal:        {cross_signal(ratio)}")
    if trend == "up":
        print(f"     → 🟢 Bonos > Stocks: flight to quality. Riesgo-off.")
        print(f"     → Adelanta correccion de equities")
        rotation_signals.append(("tlt_spy", "🔴", "Bonds > Stocks: flight to quality"))
    elif trend == "down":
        print(f"     → 🟢 Stocks > Bonos: risk-on. Expansion.")
        print(f"     → Normal en mid-expansion")
        rotation_signals.append(("tlt_spy", "🟢", "Stocks > Bonds: risk-on"))
    else:
        print(f"     → ⚪ Neutral")

    # Correlación (ya estaba, pero ahora la usamos)
    b_ser = df[tlt].dropna()
    s_ser = df[spy].dropna()
    idx_bs = b_ser.index.intersection(s_ser.index)
    b_r = b_ser.loc[idx_bs].pct_change()
    s_r = s_ser.loc[idx_bs].pct_change()
    corr_bs = b_r.rolling(252, min_periods=100).corr(s_r)
    corr_val = corr_bs.dropna().iloc[-1] if len(corr_bs.dropna()) else 0
    print(f"     Correlacion 1y: {corr_val:.2f} ", end="")
    if corr_val < 0:
        print("⚠️ Negativa = regimen anomalo")
    else:
        print("(normal)")

# --- 3. EQUAL/CAP (RSP÷SPY) — Participación de mercado ---
if rsp and spy:
    ratio = df[rsp] / df[spy]
    rat_name = "Equal/Cap (RSP÷SPY)"
    trend = safe_trend(ratio)
    pct = percentile_rank(ratio)
    print(f"\n  📊 {rat_name} — Amplitud de mercado (Murphy: mercado angosto = late cycle)")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Percentil:    {pct:.1f}%")
    if trend == "up":
        print(f"     → 🟢 RSP > SPY: participacion AMPLIA. Mercado saludable.")
        rotation_signals.append(("rsp_spy", "🟢", "Mercado amplio: participacion general"))
    elif trend == "down":
        print(f"     → 🔴 SPY > RSP: mercado ANGOSTO. Solo mega-caps suben.")
        print(f"     → Murphy: 'Cuando el promedio sube pero la mayoria de acciones no,"
              f" es señal de bull market maduro'")
        rotation_signals.append(("rsp_spy", "🔴", "Mercado angosto: solo mega-caps"))
    else:
        print(f"     → ⚪ Neutral")

# --- 4. TECH/ENERGY (XLK÷XLE) — Rotación sectorial ---
if xlk and xle:
    ratio = df[xlk] / df[xle]
    rat_name = "Tech/Energy (XLK÷XLE)"
    trend = safe_trend(ratio)
    print(f"\n  📊 {rat_name} — Rotacion sectorial clave (Murphy)")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Señal:        {cross_signal(ratio)}")
    if trend == "up":
        print(f"     → 🟢 Tech > Energy: early/mid cycle. Innovacion lidera.")
        rotation_signals.append(("xlk_xle", "🟢", "Tech > Energy: early-mid cycle"))
    elif trend == "down":
        print(f"     → 🔴 Energy > Tech: late cycle. Rotacion clasica.")
        print(f"     → Murphy: 'Cuando la energia supera a tecnologia, el ciclo esta maduro'")
        print(f"     → ⚠️ ESTO ESTA OCURRIENDO AHORA (Energy +41% vs Tech +38%)")
        rotation_signals.append(("xlk_xle", "🔴", "Energy > Tech: LATE CYCLE"))
    else:
        print(f"     → ⚪ Neutral")

# --- 5. CYCLICAL/DEFENSIVE ((XLY+XLI)÷(XLP+XLU)) ---
if xly and xli and xlp and xlu:
    cyclical = df[xly] + df[xli]
    defensive = df[xlp] + df[xlu]
    ratio = cyclical / defensive
    rat_name = "Cyclical/Defensive ((XLY+XLI)÷(XLP+XLU))"
    trend = safe_trend(ratio)
    pct = percentile_rank(ratio)
    print(f"\n  📊 {rat_name} — Confianza vs. proteccion")
    print(f"     Tendencia:    {fmt_trend(ratio)}")
    print(f"     Percentil:    {pct:.1f}%")
    if trend == "up":
        print(f"     → 🟢 Ciclicos > Defensivas: risk-on. Expansion.")
        rotation_signals.append(("cyc_def", "🟢", "Ciclicos > Defensivas: risk-on"))
    elif trend == "down":
        print(f"     → 🔴 Defensivas > Ciclicos: flight to safety. Contracion.")
        rotation_signals.append(("cyc_def", "🔴", "Defensivas > Ciclicos: miedo"))
    else:
        print(f"     → ⚪ Neutral")

# --- Síntesis de señales de rotación ---
print(f"\n  {'='*60}")
print(f"  🔄 SÍNTESIS DE ROTACIÓN ({len(rotation_signals)} senales):")
print(f"  {'='*60}")

if rotation_signals:
    bull_rot = sum(1 for _, ic, _ in rotation_signals if ic == "🟢")
    bear_rot = sum(1 for _, ic, _ in rotation_signals if ic == "🔴")
    for name, ic, msg in rotation_signals:
        print(f"     {ic} {msg}")

    # Señales específicas de late cycle
    late_cycle_signals = [s for s in rotation_signals if "LATE CYCLE" in s[2]]
    narrow_market = [s for s in rotation_signals if "angosto" in s[2] or "mega-caps" in s[2]]

    print(f"\n     ✅ Bull={bull_rot} | 🔴 Bear={bear_rot}")
    if late_cycle_signals:
        print(f"     ⚠️  Detectada rotacion LATE CYCLE: Energy > Tech")
    if narrow_market:
        print(f"     ⚠️  Mercado angosto: confirma diagnostico de late cycle")
    if bull_rot >= 3:
        print(f"     🟢 Mayoria de senales alcistas → expansion confirmada")
    elif bear_rot >= 3:
        print(f"     🔴 Mayoria de senales bajistas → contraccion anticipada")

# ============================================================================
# 6. FASE DEL CICLO ECONÓMICO (Murphy + Pring)
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 3 — FASE DEL CICLO ECONÓMICO (Murphy + Pring)")
print("─" * 72)

# Señales base (Pring)
b  = safe_trend(df[tlt]) if tlt else None
s  = safe_trend(df[spy]) if spy else None
c  = safe_trend(df[gsg]) if gsg else None

# Señales adicionales (confirmación Murphy)
xly_xlp_t = safe_trend(df[xly] / df[xlp]) if xly and xlp else None
iwm_spy_t = safe_trend(df[iwm] / df[spy]) if iwm and spy else None
qqq_spy_t = safe_trend(df[qqq] / df[spy]) if qqq and spy else None

print(f"\n  Señales CORE (Pring):")
print(f"    📜 Bonos (TLT):      {'🟢 Suben' if b=='up' else '🔴 Bajan' if b=='down' else '⚪ Laterales'}")
print(f"    📈 Acciones (SPY):   {'🟢 Suben' if s=='up' else '🔴 Bajan' if s=='down' else '⚪ Laterales'}")
print(f"    🛢️  Comm. (GSG):     {'🟢 Suben' if c=='up' else '🔴 Bajan' if c=='down' else '⚪ Laterales'}")
print(f"\n  Señales de CONFIRMACIÓN (Murphy):")
print(f"    🏪 Cyclical/Staples: {'🟢 Sube' if xly_xlp_t=='up' else '🔴 Baja' if xly_xlp_t=='down' else '⚪ Lateral'}")
print(f"    📦 Small/Large Cap:  {'🟢 Sube' if iwm_spy_t=='up' else '🔴 Baja' if iwm_spy_t=='down' else '⚪ Lateral'}")
print(f"    💻 Nasdaq/S&P:       {'🟢 Sube' if qqq_spy_t=='up' else '🔴 Baja' if qqq_spy_t=='down' else '⚪ Lateral'}")

# Detección por convergencia
extra_signals = {"xly_xlp": xly_xlp_t, "iwm_spy": iwm_spy_t, "qqq_spy": qqq_spy_t}
match = detect_murphy_phase(b, s, c, extra_signals)

print(f"\n  {'='*60}")
print(f"  🎯 FASE ECONÓMICA DETECTADA")
print(f"  {'='*60}")

if match:
    phase_num, phase_name, conf, ok, total, dist = match
    
    # --- MODIFICADOR POR CRÉDITO ---
    # Si el crédito está en nivel crítico, la fase económica se ve MODIFICADA
    # Murphy: crédito lidera equities → una alerta crediticia domina
    credit_modifier = ""
    adjusted_phase = phase_num
    adjusted_name = phase_name
    
    if credit_alert_level == "CRITICAL":
        # Si estamos en fase temprana/media con crédito crítico → mover a fase más tardía
        if phase_num <= 1:
            adjusted_phase = 2
            adjusted_name = "Mid Expansion (con advertencia crediticia)"
            credit_modifier = "⬆️ Credit alert PUSHES phase UP from early to mid"
        elif phase_num == 2:
            # Mid Expansion + crédito crítico → Late Expansion
            adjusted_phase = 3
            adjusted_name = "Late Expansion (crédito en complacencia extrema)"
            credit_modifier = "⬆️ Credit alert PUSHES phase UP from mid to late"
        # Si ya está en 3 o más, se mantiene pero se refuerza la alerta
    
    print(f"\n     Fase económica base:     {phase_num}. {phase_name}  ({conf})")
    if credit_modifier:
        print(f"     ⚠️  MODIFICADOR CREDITICIO: {credit_modifier}")
        print(f"     Fase INTEGRADA (final):   {adjusted_phase}. {adjusted_name}")
    
    print(f"     Confianza:    {ok}/{total} señales coinciden ({ok/total*100:.0f}%)")
    print(f"     Distancia:    {dist:.2f} (0=perfecto)")
    
    # Desglose
    print(f"\n     🔍 DESGLOSE DE CONFIRMACIÓN:")
    current = {"b": trend_to_num(b), "s": trend_to_num(s), "c": trend_to_num(c)}
    for k in ["xly_xlp", "iwm_spy", "qqq_spy"]:
        if k in extra_signals and extra_signals[k] is not None:
            current[k] = trend_to_num(extra_signals[k])
    
    profile = {p["num"]: p for p in PHASE_PROFILES}[phase_num]
    sig_names = {"b": "Bonos ↑↓", "s": "Acciones ↑↓", "c": "Comm. ↑↓",
                 "xly_xlp": "Cycl/Stap", "iwm_spy": "Small/Large", "qqq_spy": "Nasdaq/SPY"}
    for key, val in current.items():
        expected = profile.get(key, "—")
        if expected is None:
            continue
        ok_sig = (val == expected) or (expected == 0 and abs(val) <= 1) or (val == 0 and abs(expected) <= 1)
        arrow_val = "↑" if val == 1 else ("↓" if val == -1 else "→")
        arrow_exp = "↑" if expected == 1 else ("↓" if expected == -1 else "→")
        status = "✅" if ok_sig else "❌"
        print(f"     {status} {sig_names.get(key, key):15s}: actual {arrow_val}  esperado {arrow_exp}")

# Diagnóstico Pring (exacto) como respaldo
print(f"\n  {'='*60}")
print(f"  📚 COMPARATIVA: 6 ETAPAS DE PRING (exacto)")
print(f"  {'='*60}")

def pring_stage(b, s, c):
    if   b=="up" and s=="down" and c=="down":
        return 0, "Stage 0: Recesión → Bonos lideran. Comprar bonos / tasa-sensibles."
    elif b=="up" and s=="up" and c=="down":
        return 1, "Stage 1: Early Recovery → Comprar acciones. Comm. débiles."
    elif b=="up" and s=="up" and c=="up":
        return 2, "Stage 2: Expansión plena → Todo sube. Añadir gold/comm."
    elif b=="down" and s=="up" and c=="up":
        return 3, "Stage 3: Late Expansion → Inflación. Rotar a commodities, vender bonos."
    elif b=="down" and s=="down" and c=="up":
        return 4, "Stage 4: Early Contraction → Solo commodities / inflación-hedge."
    elif b=="down" and s=="down" and c=="down":
        return 5, "Stage 5: Contracción plena → Cash is king."
    elif b=="up" and s=="down" and c=="up":
        return None, "⚠️  PATRÓN DEFLACIÓN (B↑ S↓ C↑)"
    else:
        return None, f"Transición B:{'↑' if b=='up' else '↓' if b=='down' else '→'} S:{'↑' if s=='up' else '↓' if s=='down' else '→'} C:{'↑' if c=='up' else '↓' if c=='down' else '→'}"

stage_num, stage_txt = pring_stage(b, s, c)
print(f"\n     Stage Pring: {stage_num if stage_num is not None else '—'}")
print(f"     {stage_txt}")

# Guardar variables para diagnóstico posterior
PASE_FINAL = adjusted_phase if 'adjusted_phase' in dir() else (match[0] if match else None)
FASE_DETECTADA = {
    "fase_num": PASE_FINAL,
    "fase_nombre": adjusted_name if 'adjusted_name' in dir() else (match[1] if match else None),
    "fase_base_num": match[0] if match else None,
    "fase_base_nombre": match[1] if match else None,
    "confianza": match[2] if match else "N/A",
    "ok": match[3] if match else 0,
    "total": match[4] if match else 0,
    "credit_alert": credit_alert_level,
    "pring_stage": stage_num,
    "pring_txt": stage_txt,
}

# ============================================================================
# 6. ROTACIÓN SECTORIAL (Stovall)
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 4 — ROTACIÓN SECTORIAL (Sam Stovall)")
print("─" * 72)

perf = {}
for tick, name in SECTORS.items():
    if tick in present:
        ser = df[tick].dropna()
        if len(ser) >= 252:
            ret = (ser.iloc[-1] / ser.iloc[-252] - 1) * 100
        elif len(ser) >= 126:
            ret = (ser.iloc[-1] / ser.iloc[-126] - 1) * 100
        else:
            ret = 0
        perf[name] = ret

perf_sorted = sorted(perf.items(), key=lambda x: x[1], reverse=True)
print(f"\n  Ranking sectores (rendimiento 1yr):")
for i, (n, r) in enumerate(perf_sorted, 1):
    ic = "🟢" if r > 2 else ("🔴" if r < -2 else "⚪")
    print(f"    {i}. {ic} {n}: {r:+.1f}%")

top3 = [n for n, _ in perf_sorted[:3]]
print(f"\n  Top 3: {', '.join(top3)}")

# Determinar fase Stovall
if "Energía" in top3 and not any(x in top3 for x in ["Consumo Básico (Staples)", "Utilities"]):
    stovall_phase = "TARDÍA EXPANSIÓN"
    print(f"  → Fase Stovall: TARDÍA EXPANSIÓN — Energy lidera (típico final de ciclo)")
elif any(x in top3 for x in ["Consumo Básico (Staples)", "Utilities"]):
    stovall_phase = "CONTRACCIÓN"
    if "Finanzas" in top3:
        print(f"  → Fase Stovall: TARDÍA CONTRACCIÓN (Financials + defensivas)")
    else:
        print(f"  → Fase Stovall: TEMPRANA CONTRACCIÓN (refugio en defensivas)")
elif "Tecnología" in top3 and "Consumo Discrecional" in top3:
    stovall_phase = "TEMPRANA EXPANSIÓN"
    print(f"  → Fase Stovall: TEMPRANA EXPANSIÓN (Tech + Discrecional lideran)")
elif "Industrial" in top3 or "Materiales" in top3:
    if "Energía" in top3:
        stovall_phase = "EXPANSIÓN MEDIA-TARDÍA"
        print(f"  → Fase Stovall: EXPANSIÓN MEDIA-TARDÍA (Ind+Mat+Energy)")
    else:
        stovall_phase = "MEDIA EXPANSIÓN"
        print(f"  → Fase Stovall: MEDIA EXPANSIÓN (Industriales/Materiales fuertes)")
else:
    stovall_phase = "TRANSICIÓN"
    print(f"  → Fase Stovall: TRANSICIÓN — Combinación no concluyente")

# ============================================================================
# 7. DEFLACIÓN Y CORRELACIONES
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 5 — CORRELACIONES Y RIESGOS")
print("─" * 72)

# Detección de deflación (correlación TLT-SPY)
if tlt and spy:
    b_ser = df[tlt].dropna()
    s_ser = df[spy].dropna()
    idx = b_ser.index.intersection(s_ser.index)
    b_r = b_ser.loc[idx].pct_change()
    s_r = s_ser.loc[idx].pct_change()
    rc = b_r.rolling(252, min_periods=100).corr(s_r)
    lc = rc.dropna().iloc[-1] if len(rc.dropna()) else 0
    print(f"\n  📊 Correlación TLT-SPY rolling 1y: {lc:.2f}")
    if lc < -0.3:
        print(f"     ⚠️  DESACOPLE DEFLACIONARIO: bonos↗ stocks↘ (como 1998-2002, 1929-1932)")
        print(f"     → Las bajadas de tipos NO ayudan a las acciones.")
    elif lc < 0.1:
        print(f"     ⚠️  Correlación baja → posible transición de régimen.")
    else:
        print(f"     🟢 Correlación positiva normal → modelo intermarket estándar.")

# Correlación HYG-TLT (flight to quality)
flight_to_quality = False
if hyg_t and tlt:
    hyg_r = df[hyg_t].pct_change().dropna()
    tlt_r2 = df[tlt].pct_change().dropna()
    idx_ftq = hyg_r.index.intersection(tlt_r2.index)
    corr_hy_tlt = hyg_r.loc[idx_ftq].rolling(126, min_periods=60).corr(tlt_r2.loc[idx_ftq])
    corr_hy_tlt_val = corr_hy_tlt.dropna().iloc[-1] if len(corr_hy_tlt.dropna()) else 0
    print(f"\n  📊 Correlación HYG-TLT rolling 6m (flight to quality): {corr_hy_tlt_val:.2f}")
    if corr_hy_tlt_val < -0.3:
        print(f"     🔴 Flight to quality en curso: HY cae, TLT sube")
        flight_to_quality = True
    elif corr_hy_tlt_val < -0.1:
        print(f"     🟡 Flight to quality incipiente")
    else:
        print(f"     🟢 Sin flight to quality")

# ============================================================================
# 8. MACRO — DÓLAR, TASAS, VOLATILIDAD
# ============================================================================
print("\n" + "─" * 72)
print("  SECCIÓN 6 — DÓLAR, TASAS, VOLATILIDAD")
print("─" * 72)

dxy = t("DX-Y.NYB")
vix = t("^VIX")

if dxy:
    print(f"\n  💵 DXY (Dólar):   {fmt_trend(df[dxy])}")
    val = df[dxy].dropna().iloc[-1]
    print(f"     Valor: {val:.2f}")
    if gsg:
        gsg_trend_val = safe_trend(df[gsg])
        dxy_trend_val = safe_trend(df[dxy])
        if dxy_trend_val == "up" and gsg_trend_val == "up":
            print(f"     ⚠️  Dólar + Commodities subiendo: estrés inflacionario atípico")
if vix:
    print(f"\n  😱 VIX (Miedo):   {fmt_trend(df[vix])}")
    val = df[vix].dropna().iloc[-1]
    print(f"     Valor: {val:.1f}")
    if val > 30:
        print(f"     ⚠️  Pánico extremo")
    elif val > 20:
        print(f"     ⚠️  Volatilidad elevada")
    elif val < 15:
        print(f"     🟡 VIX muy bajo — complacencia (riesgo de reversión)")
    else:
        print(f"     → Normal")
if gsg:
    print(f"\n  🛢️  GSG (Comm.):  {fmt_trend(df[gsg])}")
if tlt:
    print(f"\n  📜 TLT (Bonos):   {fmt_trend(df[tlt])}")
if spy:
    print(f"\n  📈 SPY (Acc.):    {fmt_trend(df[spy])}")
if gld:
    print(f"\n  🥇 GLD (Oro):     {fmt_trend(df[gld])}")

# ============================================================================
# 9. DIAGNÓSTICO INTEGRADO — LA DECISIÓN
# ============================================================================
print("\n" + "=" * 72)
print("  🔍 DIAGNÓSTICO INTEGRADO — ¿DÓNDE POSICIONARSE?")
print("=" * 72)

fn = FASE_DETECTADA.get("fase_num")
fname = FASE_DETECTADA.get("fase_nombre", "N/A")
fbase_num = FASE_DETECTADA.get("fase_base_num")
fbase_name = FASE_DETECTADA.get("fase_base_nombre", "N/A")
conf = FASE_DETECTADA.get("confianza", "N/A")
ok = FASE_DETECTADA.get("ok", 0)
total = FASE_DETECTADA.get("total", 0)
cal = FASE_DETECTADA.get("credit_alert", "NONE")

print(f"\n  📌 SÍNTESIS:")
if fn is not None:
    phase_profile = {p["num"]: p for p in PHASE_PROFILES}
    profile = phase_profile.get(fbase_num, {})
    
    print(f"     Fase base (Murphy-Pring):  {fbase_num}. {fbase_name}") if fbase_num is not None else None
    print(f"     Ajuste crediticio:         {cal}")
    if fbase_num != fn:
        print(f"     🔄 Fase INTEGRADA final:    {fn}. {fname}")
        print(f"     → El crédito MODIFICA la fase: pasar a postura más defensiva")
    
    print(f"     Confianza señales:         {ok}/{total}")
    print(f"     Sectores líderes (Stovall): {', '.join(top3)}")

# --- Evaluar el escenario ---
# Factores que determinan la postura:
score_bull = 0
score_bear = 0
factors_bull = []
factors_bear = []

# 1. CICLO ECONÓMICO (60% peso)
if fn is not None:
    if fn <= 1:
        score_bull += 3
        factors_bull.append("Early Recovery → riesgo recompensado")
    elif fn == 2:
        score_bull += 2
        factors_bull.append("Mid Expansion → crecimiento sólido")
    elif fn == 3:
        score_bull += 1
        factors_bear.append("Late Expansion — mercado angosto, precaución")
    elif fn >= 4:
        score_bear += 3
        factors_bear.append("Contracción — riesgo de recesión")

# 2. CRÉDITO (30% peso — modificador principal)
if credit_alert_level == "CRITICAL":
    score_bear += 3
    factors_bear.append(f"🔴 Crédito en complacencia extrema (IG {ig_pct:.0f}%, HY {hy_pct:.0f}%)")
    factors_bear.append("→ Murphy: spreads extremos = señal de final de ciclo")
elif credit_alert_level == "WARNING":
    score_bear += 1
    factors_bear.append("🟡 Crédito elevado — monitorear")

# 3. CONSUMIDOR (10%)
if xly_xlp_t == "down":
    score_bear += 2
    factors_bear.append("🔴 XLY/XLP bajando — consumidor débil, contradice expansión")
if xly_xlp_t == "up":
    score_bull += 1
    factors_bull.append("🟢 Consumidor fuerte (XLY/XLP subiendo)")

# 4. VIX
if vix:
    v_val = df[vix].dropna().iloc[-1]
    if v_val > 30:
        score_bear += 2
        factors_bear.append(f"VIX={v_val:.0f} — pánico")
    elif v_val < 15:
        score_bear += 1  # complacencia es señal de alerta también
        factors_bear.append(f"VIX={v_val:.0f} — complacencia, riesgo de reversión")

# 5. CURVA
if ief and bil:
    curve_trend = safe_trend(df[ief] / df[bil])
    if curve_trend == "down":
        score_bear += 2
        factors_bear.append("Curva invirtiéndose — señal de recesión")

# 6. FLIGHT TO QUALITY
if flight_to_quality:
    score_bear += 2
    factors_bear.append("Flight to quality HY→TLT activo")

# --- NETO ---
net_score = score_bull - score_bear

print(f"\n  {'='*50}")
print(f"  📊 BALANCE: 🟢 Bull={score_bull} | 🔴 Bear={score_bear} | NETO={net_score:+d}")
print(f"  {'='*50}")

if factors_bull:
    print(f"\n  🟢 FACTORES A FAVOR:")
    for f in factors_bull:
        print(f"    + {f}")
if factors_bear:
    print(f"\n  🔴 FACTORES EN CONTRA:")
    for f in factors_bear:
        print(f"    - {f}")

# --- POSTURA FINAL ---
print(f"\n  {'='*72}")
print(f"  🎯 POSTURA RECOMENDADA (según Murphy + crédito)")
print(f"  {'='*72}")

if net_score >= 4:
    posture = "AGRESIVO RISK-ON"
    posture_desc = "Todas las señales alcistas. Sobreponderar acciones, ciclicos, small caps."
    print(f"\n  🟢🟢🟢 {posture}")
    print(f"     {posture_desc}")
    print(f"     COMPRAR: XLK, XLY, IWM, XLF, QQQ")
    print(f"     VENDER:  XLP, XLU, TLT")
elif net_score >= 1:
    posture = "RISK-ON MODERADO"
    posture_desc = "Señales mayormente alcistas pero con algunas advertencias creíticas."
    print(f"\n  🟢 {posture}")
    print(f"     {posture_desc}")
    print(f"     COMPRAR: XLI, XLB, XLF, COPX, XLE")
    print(f"     VENDER:  XLP, XLU, TLT, LQD")
    if credit_alert_level == "CRITICAL" or xly_xlp_t == "down":
        print(f"     ⚠️  Pero REDUCIR exposicion a credito y monitorear consumidor")
elif net_score >= -2:
    posture = "CAUTELA DEFENSIVA"
    posture_desc = "Señales mixtas con riesgo crediticio elevado. Postura defensiva."
    print(f"\n  🟡 {posture}")
    print(f"     {posture_desc}")
    print(f"     COMPRAR: XLE, GLD, XLV, XLU, BIL/SGOV")
    print(f"     VENDER:  XLK, XLY, HYG, LQD, IWM")
    print(f"     → Murphy: 'Cuando los spreads estan en extremos, la correccion es inminente'")
elif net_score >= -4:
    posture = "DEFENSIVO / REDUCIR RIESGO"
    print(f"\n  🔴 {posture}")
    print(f"     COMPRAR: TLT, GLD, XLP, XLU, XLV, BIL")
    print(f"     VENDER:  Todo riesgo: stocks, HY, commod, IG largos")
else:
    posture = "RISK-OFF / CAJA"
    print(f"\n  🔴🔴 {posture}")
    print(f"     COMPRAR: Solo TLT, GLD, Cash")
    print(f"     VENDER:  Todo")

# --- DECISIÓN DETALLADA POR ACTIVO ---
print(f"\n  {'='*72}")
print(f"  📋 PLAN DE ACCIÓN — ¿QUÉ HACER CON CADA ACTIVO?")
print(f"  {'='*72}")

# Determinar fase efectiva (la usada para sector rotation)
fase_efectiva = fn if fn is not None else 3  # Default to late expansion if unclear
# Pero si el crédito está crítico y la fase base es <=2, forzar Late Expansion rotation
if credit_alert_level == "CRITICAL" and fase_efectiva is not None and fase_efectiva <= 2:
    fase_rotation = min(3, fase_efectiva + 1)  # Mover una fase más defensiva
    if fase_rotation < 3:
        fase_rotation = 3  # Mínimo Late Expansion si crédito crítico
else:
    fase_rotation = fase_efectiva

rot = SECTOR_ROTATION.get(fase_rotation)
if rot:
    print(f"\n  Basado en fase integrada: {rot['ico']} {fase_rotation}. {rot['nombre']}")
    if fbase_num != fn:
        print(f"  (Ajustada desde fase base {fbase_num} por alerta crediticia)")
    
    print(f"\n  ✅ COMPRAR / SOBREPONDER:")
    for item in rot["comprar"]:
        print(f"     + {item}")
    
    print(f"\n  ❌ VENDER / INFRAPONDERAR:")
    for item in rot["vender"]:
        print(f"     - {item}")
    
    print(f"\n  📊 MOMENTUM ACTUAL DE CADA SECTOR (6m):")
    print(f"  {'Sector':<22s} {'Fase rec.':<14s} {'6m ret.':<10s} {'Acción':<12s}")
    print(f"  {'─'*22} {'─'*14} {'─'*10} {'─'*12}")
    for tick, name in SECTORS.items():
        if tick not in present:
            continue
        ser = df[tick].dropna()
        ret_6m = (ser.iloc[-1] / ser.iloc[-126] - 1) * 100 if len(ser) >= 126 else 0
        mom_icon = "🟢" if ret_6m > 5 else ("🔴" if ret_6m < -5 else "⚪")
        
        # Determinar si está en comprar o vender según rotación (por ticker)
        in_buy = any(tick in s for s in rot["comprar"])
        in_sell = any(tick in s for s in rot["vender"])
        if in_buy:
            accion = "COMPRAR ✅"
        elif in_sell:
            accion = "VENDER ❌"
        else:
            accion = "NEUTRO ⚪"
        print(f"  {name:<22s} {accion:<14s} {mom_icon} ({ret_6m:+.0f}%)")

# --- RIESGOS Y EXCEPCIONES ---
print(f"\n  {'='*72}")
print(f"  ⚠️  RIESGOS Y EXCEPCIONES (Murphy)")
print(f"  {'='*72}")
print(f"  • Si la correlacion TLT-SPY es negativa → REGIMEN DEFLACIONARIO")
print(f"    (el modelo intermarket NO funciona)")
print(f"  • Si commodities suben con stocks → REFLACION (Fed expansiva)")
print(f"    (commodities subiendo con stocks es BUENO — no es inflacion mala)")
print(f"  • Si el dolar baja pero commodities NO suben → BUENO para emergentes")
print(f"  • El COBRE (COPX/JJC) es el mejor LEADING INDICADOR de bonos")
print(f"    (precede cambios en yields por 3-6 meses)")
print(f"  • HYG > LQD (risk-on) | LQD > HYG (risk-off) — Monitorear diariamente")

# ============================================================================
# 10. VALIDACIÓN CON NOTICIAS — ¿Los titulares respaldan al modelo?
# ============================================================================
print(f"\n" + "=" * 72)
print("  📰 VALIDACIÓN CON NOTICIAS — ¿CONFIRMAN O CONTRADICEN?")
print("=" * 72)

try:
    # Generar queries según hallazgos
    news_queries, query_labels = build_news_queries(
        FASE_DETECTADA, rotation_signals, credit_alert_level,
        xly_xlp_t, gsg, dxy, vix, df, safe_trend, ig_pct, hy_pct
    )
    
    total_support = 0
    total_contradict = 0
    total_articles = 0
    all_results = []
    
    print(f"\n  Buscando noticias para {len(news_queries)} líneas de evidencia...\n")
    
    for qi, (query, (ftype, label)) in enumerate(zip(news_queries, query_labels)):
        articles = fetch_news(query, max_results=2)
        if not articles:
            continue
        
        print(f"  🔎 {label}")
        print(f"     Búsqueda: \"{query[:60]}{'...' if len(query)>60 else ''}\"")
        
        article_votes = []
        for title, link, pub in articles:
            verdict = evaluar_noticia(title, ftype, "")
            if verdict == "support":
                icon = "🟢"
                total_support += 1
            elif verdict == "contradict":
                icon = "🔴"
                total_contradict += 1
            else:
                icon = "⚪"
            total_articles += 1
            article_votes.append(verdict)
            
            # Truncar fecha
            pub_short = pub.split("+")[0].split(",")[0] if pub else ""
            print(f"     {icon} {title[:75]}{'...' if len(title)>75 else ''}")
            if pub_short:
                print(f"       ({pub_short})")
        
        # Resumen de esta query
        supports = sum(1 for v in article_votes if v == "support")
        contradicts = sum(1 for v in article_votes if v == "contradict")
        if supports > contradicts:
            print(f"     ✅ → Noticias CONFIRMAN este hallazgo")
        elif contradicts > supports:
            print(f"     ⚠️ → Noticias CONTRADICEN este hallazgo — ¡revisar!")
        else:
            print(f"     ➖ → Neutral / mixto")
        print()
    
    # --- Score de validación global ---
    print(f"  {'='*60}")
    if total_articles == 0:
        print(f"  📊 No se pudieron obtener noticias — verifica conexión a internet")
        print(f"     ⚠️  La validación por noticias requiere acceso a news.google.com")
    else:
        neutral_count = total_articles - total_support - total_contradict
        total_checked = total_support + total_contradict
        if total_checked > 0:
            validation_pct = (total_support / total_checked) * 100
            print(f"  📊 VALIDACIÓN GLOBAL: {validation_pct:.0f}% de las noticias CONFIRMAN el modelo")
        else:
            validation_pct = 0
            print(f"  📊 VALIDACIÓN GLOBAL: {neutral_count} artículos neutrales — no se detectó sesgo claro")
        
        print(f"     🟢 Confirman: {total_support} | 🔴 Contradicen: {total_contradict} | ⚪ Neutrales: {neutral_count} | 📰 Total: {total_articles}")
        
        if total_checked > 0:
            if validation_pct >= 80:
                print(f"     🟣 VALIDACIÓN ALTA — Las noticias respaldan fuertemente el diagnóstico")
            elif validation_pct >= 60:
                print(f"     🟡 VALIDACIÓN MODERADA — Mayoría respalda, pero hay señales mixtas")
            elif validation_pct >= 40:
                print(f"     🟠 VALIDACIÓN BAJA — Las noticias no respaldan claramente al modelo")
            else:
                print(f"     🔴 CONTRADICCIÓN — Las noticias contradicen al modelo. ¡Revisar premisas!")
        else:
            if neutral_count > 0:
                print(f"     💡 Los artículos son neutrales al modelo — revisarlos manualmente para contexto")
    
    # Sugerencia de búsqueda manual
    if news_queries:
        print(f"\n  💡 Para explorar más a fondo, busca en tu navegador:")
        for qi, (query, (ftype, label)) in enumerate(zip(news_queries[:3], query_labels[:3])):
            print(f"     {qi+1}. {query}")
    
except Exception as e:
    print(f"\n  ⚠️  Error en validación de noticias: {e}")
    print("     (El resto del análisis continúa normalmente)")

# ============================================================================
# 11. VEREDICTO ÚLTIMO
# ============================================================================
print(f"\n" + "=" * 72)
print(f"  🏆 VEREDICTO: UNA SOLA VOZ, SIN CONTRADICCIONES")
print("=" * 72)

fbase_num_check = FASE_DETECTADA.get("fase_base_num", fn)

if cal == "CRITICAL" and fbase_num_check is not None and fbase_num_check <= 2:
    print(f"""
  ╔══════════════════════════════════════════════════════════════════╗
  ║  ⚠️  LA ECONOMIA DICE {PHASE_PROFILES[fbase_num_check]['name'].upper()},                              ║
  ║     PERO EL CREDITO DICE LATE CYCLE.                            ║
  ║     MURPHY: CUANDO EL CREDITO Y LA ECONOMIA                     ║
  ║     SE CONTRADICEN, EL CREDITO GANA (LEADING 3-6M).             ║
  ║                                                                  ║
  ║  ✅ POSTURA CORRECTA: CAUTELA DEFENSIVA                         ║
  ║     • Reducir exposicion a credito corporativo                   ║
  ║     • Rotar a Energia, Oro, Salud, Utilities                     ║
  ║     • Aumentar T-bills (BIL, SGOV) como colchon                  ║
  ║     • Vender HY, IG largos, Tech (si esta sobreponderado)         ║
  ║                                                                  ║
  ║  📊 VEREDICTO CONSISTENTE CON GLOBAL WEEKLY REPORT #63           ║
  ║     'Complacencia mal remunerada — reducir riesgo crediticio'    ║
  ╚══════════════════════════════════════════════════════════════════╝
""")
elif cal == "CRITICAL" and fn is not None and fn >= 3:
    print(f"""
  ╔══════════════════════════════════════════════════════════════════╗
  ║  🔴 ECONOMIA + CREDITO ALINEADOS: LATE CYCLE O PEOR            ║
  ║     TODAS LAS SENALES APUNTAN A LA MISMA DIRECCION.             ║
  ║                                                                  ║
  ║  ✅ POSTURA CORRECTA: DEFENSIVA / REDUCIR RIESGO                ║
  ║     • Aumentar T-bills (BIL, SGOV)                              ║
  ║     • Comprar Oro, Bonos largos, Utilities                      ║
  ║     • Vender stocks ciclicos, HY, IG corporativo                 ║
  ╚══════════════════════════════════════════════════════════════════╝
""")
else:
    print(f"""
  ╔══════════════════════════════════════════════════════════════════╗
  ║  🟢 ECONOMIA + CREDITO SIN ALERTAS MAYORES                     ║
  ║     POSTURA ACORDE A LA FASE DETECTADA.                          ║
  ╚══════════════════════════════════════════════════════════════════╝
""")

print(f"\n" + "=" * 72)
print(f"  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"  Fuente: 'Intermarket Analysis' — John J. Murphy")
print(f"  + Global Weekly Report #63 (validación crediticia)")
print("=" * 72)
