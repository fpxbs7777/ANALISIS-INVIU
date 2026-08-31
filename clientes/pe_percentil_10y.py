"""
P/E PERCENTIL 10 AÑOS — Cartera CORONAR
----------------------------------------
Usa get_earnings_dates(limit=40) para obtener EPS trimestrales
reales reportados, calcula TTM EPS, y lo combina con precios
históricos para obtener P/E trailing trimestral.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

CARTERA = {
    "PAMP":  "PAMP.BA",   # Pampa Energía (Argentina)
    "AMZN":  "AMZN",      # Amazon
    "GOOGL": "GOOGL",     # Alphabet (Google)
    "MP":    "MP",        # MP Materials
    "MSFT":  "MSFT",      # Microsoft
    "NVDA":  "NVDA",      # NVIDIA
    "SMH":   "SMH",       # VanEck Semiconductor ETF
    "SPY":   "SPY",       # SPDR S&P 500 ETF
    "TSM":   "TSM",       # Taiwan Semiconductor
    "URA":   "URA",       # Global X Uranium ETF
}

ETF_TICKERS = {"SMH", "SPY", "URA"}


def calc_pe_10y_earnings_dates(ticker_str, years=10, debug=False):
    """
    Calcula P/E trailing trimestral usando get_earnings_dates().
    Retorna (df_pe, pe_actual, nombre_empresa) o (None, None, "").
    """
    try:
        t = yf.Ticker(ticker_str)
    except Exception as e:
        if debug: print(f"  {ticker_str}: ERROR Ticker — {e}")
        return None, None, ""

    # Nombre
    try:
        info = t.info
        nombre = info.get("longName", info.get("shortName", ticker_str))[:30]
    except:
        nombre = ticker_str

    # ── Earnings dates (hasta 10-12 años) ──
    try:
        # limit=44 cubre ~11 años (4 trimestres/año)
        ed = t.get_earnings_dates(limit=44)
        if ed is None or ed.empty:
            if debug: print(f"  {ticker_str}: earnings_dates vacío")
            return None, None, nombre
    except Exception as e:
        if debug: print(f"  {ticker_str}: ERROR earnings_dates — {e}")
        return None, None, nombre

    # Buscar columna de EPS reportado
    eps_col = None
    for col in ['Reported EPS', 'epsActual', 'EPS']:
        if col in ed.columns:
            eps_col = col
            break
    if eps_col is None:
        if debug: print(f"  {ticker_str}: sin columna EPS en earnings_dates")
        if debug: print(f"    Columnas: {list(ed.columns)}")
        return None, None, nombre

    # Limpiar: solo filas con EPS reportado, orden ascendente
    eps_series = ed[eps_col].dropna().sort_index()
    # Convertir index a tz-naive
    if hasattr(eps_series.index, 'tz') and eps_series.index.tz is not None:
        eps_series.index = eps_series.index.tz_localize(None)

    if len(eps_series) < 8:  # mínimo 2 años
        if debug: print(f"  {ticker_str}: solo {len(eps_series)} EPS reportados")
        return None, None, nombre

    # ── Precios históricos ──
    end = datetime.now()
    start = end - timedelta(days=years*365 + 90)
    try:
        hist = t.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            if debug: print(f"  {ticker_str}: history vacío")
            return None, None, nombre
        if hasattr(hist.index, 'tz') and hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)
    except Exception as e:
        if debug: print(f"  {ticker_str}: ERROR history — {e}")
        return None, None, nombre

    # ── Calcular P/E para cada trimestre ──
    # TTM EPS = suma de 4 trimestres consecutivos
    eps_values = eps_series.values
    eps_dates = eps_series.index

    pe_records = []
    for i in range(3, len(eps_values)):
        ttm_eps = sum(eps_values[i-3:i+1])
        if ttm_eps <= 0:
            continue
        q_date = eps_dates[i]
        # Precio de cierre en la fecha del earnings report (o la más cercana ±5 días)
        for offset in [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5]:
            check_date = q_date + timedelta(days=offset)
            # Buscar si hay precio en esa fecha exacta
            if check_date in hist.index:
                px = hist.loc[check_date, 'Close']
                break
            # Si no hay precio exacto, buscar el más cercano
            # (solo para el primer offset que no encuentra)
        else:
            # No se encontró en ±5 días, buscar el más cercano
            mask = (hist.index >= q_date - timedelta(days=10)) & (hist.index <= q_date + timedelta(days=10))
            candidates = hist[mask]
            if candidates.empty:
                continue
            diffs = (candidates.index - q_date).total_seconds()
            best_idx = np.abs(diffs).argmin()
            px = candidates.iloc[best_idx]['Close']
            check_date = candidates.index[best_idx]

        if px > 0:
            pe = px / ttm_eps
            pe_records.append({'date': check_date, 'pe': pe, 'ttm_eps': ttm_eps, 'price': px})

    if len(pe_records) < 4:
        if debug: print(f"  {ticker_str}: solo {len(pe_records)} P/E calculados")
        return None, None, nombre

    df = pd.DataFrame(pe_records).sort_values('date')
    return df, df['pe'].iloc[-1], nombre


def pe_actual_etf(ticker_str, debug=False):
    """P/E actual para ETF desde info o funds_data."""
    try:
        t = yf.Ticker(ticker_str)
        info = t.info
        pe = info.get("trailingPE", None) or info.get("forwardPE", None)
        if pe and 0 < pe < 200:
            try:
                nombre = info.get("longName", info.get("shortName", ticker_str))[:30]
            except:
                nombre = ticker_str
            return pe, nombre, "info"
        fd = t.funds_data
        if fd:
            eq = fd.equity_holdings
            if eq is not None and 'priceEarnings' in eq.columns:
                pe_val = eq['priceEarnings'].mean()
                if pe_val and pe_val > 0:
                    return pe_val, nombre, "equity_holdings"
    except:
        pass
    return None, "", ""


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

print("=" * 105)
print("  📊 P/E PERCENTIL 10 AÑOS — Cartera CORONAR Inversiones ETR")
print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("  Método: EPS trimestral reportado (get_earnings_dates) + precio de cierre")
print("=" * 105)
print()
print(f"{'Ticker':<7} {'Nombre':<30} {'P/E Act':<8} {'P/E 10y Min':<12} {'P/E 10y Max':<12} {'Pctl%':<7} {'Obs':<5} {'Señal':<20}")
print("-" * 105)

resultados = []

for nombre_corto, yf_ticker in CARTERA.items():
    es_etf = nombre_corto in ETF_TICKERS

    if es_etf:
        pe_actual, nombre_largo, fuente = pe_actual_etf(yf_ticker, debug=False)
        if pe_actual:
            print(f"{nombre_corto:<7} {nombre_largo:<30} {pe_actual:<8.1f} {'N/A':<12} {'N/A':<12} {'N/A':<7} {'-':<5} {'⚠️ ETF (P/E actual)':<20}")
            print(f"{'':>7} {'→ P/E del índice subyacente, no hay histórico trimestral':<86}")
        else:
            print(f"{nombre_corto:<7} {'ETF sin P/E disponible':<30} {'N/A':<8} {'N/A':<12} {'N/A':<12} {'N/A':<7} {'-':<5} {'⚠️ s/d':<20}")
        resultados.append({'ticker': nombre_corto, 'pe_actual': pe_actual,
                          'pe_min': None, 'pe_max': None, 'percentil': None,
                          'senal': 'ETF', 'n_obs': 0})
        continue

    # ── ACCIONES ──
    df, pe_actual, nombre_largo = calc_pe_10y_earnings_dates(yf_ticker, years=10, debug=False)

    if df is not None and len(df) >= 4:
        pe_vals = df['pe'].values
        pe_actual = float(pe_vals[-1])
        pe_min = float(np.min(pe_vals))
        pe_max = float(np.max(pe_vals))
        percentil = float(np.sum(pe_vals <= pe_actual) / len(pe_vals) * 100)
        n_obs = len(pe_vals)
        fecha_min = df['date'].min().strftime('%Y-%m')
        fecha_max = df['date'].max().strftime('%Y-%m')

        if percentil <= 15:
            senal = "🟢 COMPRAR"
        elif percentil <= 30:
            senal = "🟡 COMPRA PARCIAL"
        elif percentil <= 70:
            senal = "⚪ NEUTRAL"
        elif percentil <= 85:
            senal = "🟠 VENTA PARCIAL"
        else:
            senal = "🔴 VENDER"

        print(f"{nombre_corto:<7} {nombre_largo:<30} {pe_actual:<8.1f} {pe_min:<12.1f} {pe_max:<12.1f} {percentil:<7.0f} {n_obs:<5} {senal:<20}")
        print(f"{'':>7} {'→ Rango ' + fecha_min + ' a ' + fecha_max + ' (' + str(n_obs) + ' trimestres)':<86}")
    else:
        # Fallback: solo P/E actual de info
        try:
            info = yf.Ticker(yf_ticker).info
            pe_actual = info.get("trailingPE", None) or info.get("forwardPE", None)
            if not nombre_largo:
                nombre_largo = info.get("longName", info.get("shortName", ""))[:30]
        except:
            pe_actual = None
        if pe_actual:
            print(f"{nombre_corto:<7} {nombre_largo:<30} {pe_actual:<8.1f} {'N/A':<12} {'N/A':<12} {'N/A':<7} {'-':<5} {'⚠️ s/d histórico':<20}")
            print(f"{'':>7} {'→ Solo P/E actual disponible, sin histórico 10y':<86}")
        else:
            print(f"{nombre_corto:<7} {'SIN DATOS':<30} {'N/A':<8} {'N/A':<12} {'N/A':<12} {'N/A':<7} {'-':<5} {'⚠️ s/d':<20}")

    resultados.append({'ticker': nombre_corto, 'nombre': nombre_largo,
                       'pe_actual': pe_actual, 'pe_min': pe_min if df is not None else None,
                       'pe_max': pe_max if df is not None else None,
                       'percentil': percentil if df is not None else None,
                       'senal': senal if df is not None else '⚠️ s/d',
                       'n_obs': n_obs if df is not None else 0})
    print()

print("-" * 105)
print()
print("  Leyenda de señales (basadas en percentil histórico 10 años):")
print("    🟢 COMPRAR       = pctl ≤ 15  → muy barato vs su historia, oportunidad")
print("    🟡 COMPRA PARCIAL = pctl 16-30 → ligeramente barato, acumular gradual")
print("    ⚪ NEUTRAL        = pctl 31-70 → valoración justa, mantener")
print("    🟠 VENTA PARCIAL  = pctl 71-85 → algo caro, reducir parcialmente")
print("    🔴 VENDER         = pctl > 85  → caro vs historia, considerar ganancias")
print()

# ── Resumen de acción ──
print("=" * 105)
print("  📋 RESUMEN DE ACCIÓN SUGERIDA (basado únicamente en P/E percentil 10y)")
print("=" * 105)
print(f"{'Ticker':<7} {'P/E':<8} {'Pctl%':<8} {'Señal':<20} {'Interpretación':<50}")
print("-" * 105)

for r in resultados:
    if r['percentil'] is not None:
        ctx = {
            '🟢 COMPRAR': 'Históricamente barato — oportunidad si fundamentos intactos',
            '🟡 COMPRA PARCIAL': 'Ligeramente barato — acumular en correcciones',
            '⚪ NEUTRAL': 'Valoración justa — mantener posición actual',
            '🟠 VENTA PARCIAL': 'Algo sobrevalorado — reducir ligeramente',
            '🔴 VENDER': 'Sobrevalorado vs su historia — considerar tomar ganancias',
        }.get(r['senal'], '')
        print(f"{r['ticker']:<7} {r['pe_actual']:<8.1f} {r['percentil']:<8.0f}% {r['senal']:<20} {ctx:<50}")
    else:
        if r['senal'] == 'ETF':
            if r['pe_actual']:
                print(f"{r['ticker']:<7} {r['pe_actual']:<8.1f} {'N/A':<8} {'⚠️ ETF':<20} {'P/E del índice — no hay histórico 10y':<50}")
            else:
                print(f"{r['ticker']:<7} {'N/A':<8} {'N/A':<8} {'⚠️ s/d':<20} {'ETF sin P/E disponible':<50}")
        else:
            print(f"{r['ticker']:<7} {r['pe_actual'] if r['pe_actual'] else 'N/A':<8} {'N/A':<8} {r['senal']:<20} {'Sin datos históricos suficientes':<50}")

print("-" * 105)
print()
print("⚠️  IMPORTANTE:")
print("  1. El percentil del P/E es UNA métrica — no decidir solo con esto.")
print("  2. Combinar con: análisis intermarket (Murphy), margen de seguridad")
print("     (value investing), contexto macro, y perfil Schvarz.")
print("  3. PAMP.BA (Argentina): datos pueden estar distorsionados por inflación")
print("     y cambios de política cambiaria. Usar con precaución.")
print("  4. CEDEARs: el P/E es el del subyacente en USD, no del CEDEAR.")
print("  5. SPY (P/E 27.8) está caro históricamente — el S&P 500 ha tenido")
print("     expansión múltiplo en los últimos años.")
print("=" * 105)