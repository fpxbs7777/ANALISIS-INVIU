# -*- coding: utf-8 -*-
"""Analizar periodo exacto de la tesis original XLP"""
import yfinance as yf
import pandas as pd

ENTRY = pd.Timestamp('2026-07-22')
ENTRY_DATE = ENTRY.date()

# 1m antes = 22-Jun al 22-Jul
start_1m = '2026-06-22'
start_1y = '2025-07-22'
end = '2026-07-23'

# XLP
xlp = yf.Ticker('XLP')
h_xlp_1m = xlp.history(start=start_1m, end=end)
h_xlp_1y = xlp.history(start=start_1y, end=end)

# XLK
xlk = yf.Ticker('XLK')
h_xlk_1m = xlk.history(start=start_1m, end=end)

# SPY
spy = yf.Ticker('SPY')
h_spy_1y = spy.history(start=start_1y, end=end)

# Retornos
xlp_1m = ((h_xlp_1m.iloc[-1]['Close'] / h_xlp_1m.iloc[0]['Close']) - 1) * 100
xlk_1m = ((h_xlk_1m.iloc[-1]['Close'] / h_xlk_1m.iloc[0]['Close']) - 1) * 100
xlp_1y = ((h_xlp_1y.iloc[-1]['Close'] / h_xlp_1y.iloc[0]['Close']) - 1) * 100
spy_1y = ((h_spy_1y.iloc[-1]['Close'] / h_spy_1y.iloc[0]['Close']) - 1) * 100

print("=== TESIS: DATOS PRE-ENTRADA (22-Jun al 22-Jul) ===")
print(f"XLP 1m: {xlp_1m:.1f}%  (tesis decia +0.9%)")
print(f"XLK 1m: {xlk_1m:.1f}%  (tesis decia -2.0%)")
print()
print(f"XLP 1y: {xlp_1y:.1f}%  (tesis decia +6.4%)")
print(f"SPY 1y: {spy_1y:.1f}%  (tesis decia +20.3%)")
print()

# SMAs al entry
h_xlp_full = xlp.history(period='1y')
h_xlp_full['SMA20'] = h_xlp_full['Close'].rolling(20).mean()
h_xlp_full['SMA50'] = h_xlp_full['Close'].rolling(50).mean()
entry_row = h_xlp_full[h_xlp_full.index.date == ENTRY_DATE]
if not entry_row.empty:
    r = entry_row.iloc[0]
    print(f"SMA20 al entry: ${r['SMA20']:.2f}  (tesis: $84.27)")
    print(f"SMA50 al entry: ${r['SMA50']:.2f}  (tesis: $83.86)")
    print(f"SMA20 > SMA50: {r['SMA20'] > r['SMA50']}")

# Beta shield: 56 days where SPY fell >1%
print()
print("=== BETA SHIELD: dias donde SPY cayo >1% ===")
h_spy = spy.history(start='2021-01-01', end='2026-07-23')
h_xlp_long = xlp.history(start='2021-01-01', end='2026-07-23')

# Alinear
merged = pd.DataFrame({
    'spy_ret': h_spy['Close'].pct_change() * 100,
    'xlp_ret': h_xlp_long['Close'].pct_change() * 100
})
merged = merged.dropna()
spy_crash = merged[merged['spy_ret'] < -1]
print(f"Dias con SPY < -1%: {len(spy_crash)}")
if len(spy_crash) > 0:
    avg_spy = spy_crash['spy_ret'].mean()
    avg_xlp = spy_crash['xlp_ret'].mean()
    print(f"SPY promedio esos dias: {avg_spy:.2f}%  (tesis: -1.81%)")
    print(f"XLP promedio esos dias: {avg_xlp:.2f}%  (tesis: -0.16%)")
    print(f"Ratio defensivo: {avg_xlp/avg_spy:.2f}x  (tesis: 0.09x)")

# Intermarket ratios
print()
print("=== INTERMARKET RATIOS ===")
tlt = yf.Ticker('TLT')
dbc = yf.Ticker('DBC')
h_tlt = tlt.history(start='2025-01-01', end='2026-07-23')
h_dbc = dbc.history(start='2025-01-01', end='2026-07-23')

# Buscar precios al entry
tlt_entry = h_tlt[h_tlt.index.date == ENTRY_DATE]
dbc_entry = h_dbc[h_dbc.index.date == ENTRY_DATE]
if not tlt_entry.empty and not dbc_entry.empty:
    tlt_e = tlt_entry.iloc[0]['Close']
    dbc_e = dbc_entry.iloc[0]['Close']
    tlt_1y_ago = h_tlt.iloc[0]['Close']
    dbc_1y_ago = h_dbc.iloc[0]['Close']
    tlt_bcom_1y = ((tlt_e/dbc_e) / (tlt_1y_ago/dbc_1y_ago) - 1) * 100
    print(f"TLT/BCOM cambio 1y: {tlt_bcom_1y:.1f}%  (tesis: -18.6%)")

# SPY/TLT
spy_entry = h_spy_1y[h_spy_1y.index.date == ENTRY_DATE]
if not spy_entry.empty:
    spy_e = spy_entry.iloc[0]['Close']
    spy_1y_ago = h_spy_1y.iloc[0]['Close']
    spy_tlt_1y = ((spy_e/tlt_e) / (spy_1y_ago/tlt_1y_ago) - 1) * 100
    print(f"SPY/TLT cambio 1y: {spy_tlt_1y:.1f}%  (tesis: +19.4%)")

# 10Y-2Y spread
tnx = yf.Ticker('^TNX')
two = yf.Ticker('^2YR')
h_tnx = tnx.history(start='2025-01-01', end='2026-07-23')
try:
    h_two = two.history(start='2025-01-01', end='2026-07-23')
    tnx_entry = h_tnx[h_tnx.index.date == ENTRY_DATE]
    two_entry = h_two[h_two.index.date == ENTRY_DATE]
    if not tnx_entry.empty and not two_entry.empty:
        spread = tnx_entry.iloc[0]['Close'] - two_entry.iloc[0]['Close']
        print(f"10Y-2Y spread al entry: {spread:.2f}%  (tesis: +0.39%)")
except:
    print("10Y-2Y: no se pudo obtener ^2YR")

print()
print("=== DIVIDEND YIELD ===")
for t in ['PG', 'KO', 'PEP', 'MO']:
    info = yf.Ticker(t).info
    dy = info.get('dividendYield', 'N/A')
    if dy != 'N/A':
        print(f"  {t}: {float(dy):.2f}%")
    else:
        print(f"  {t}: N/A")

print()
print("=== PRICING POWER - HOLDINGS ===")
holdings = {'PG': '~13%', 'KO': '~11%', 'COST': '~10%', 'WMT': '~9%', 'PEP': '~8%', 'CL': '~5%'}
print(f"  {'Ticker':<8} {'Peso':<8} {'FwdPE':<10} {'Margen Bruto':<15} {'ROE':<10}")
for t, peso in holdings.items():
    info = yf.Ticker(t).info
    fpe = info.get('forwardPE', 'N/A')
    gm = info.get('grossMargins', 'N/A')
    roe = info.get('returnOnEquity', 'N/A')
    fpe_s = f"{float(fpe):.1f}x" if fpe != 'N/A' else 'N/A'
    gm_s = f"{float(gm)*100:.0f}%" if gm != 'N/A' else 'N/A'
    roe_s = f"{float(roe)*100:.0f}%" if roe != 'N/A' else 'N/A'
    print(f"  {t:<8} {peso:<8} {fpe_s:<10} {gm_s:<15} {roe_s:<10}")