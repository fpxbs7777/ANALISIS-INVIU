# -*- coding: utf-8 -*-
"""
SCREENER SECTORES FAVORECIDOS (intermarket top-down) — 05/08/2026
Universo: 266 empresas de Tech / Financiero / Salud / Industrial / Energia
Etapa 1 (batch yfinance): rendimientos 1M/3M/6M/1Y, RSI14, SMA50/200, tendencia,
                          MDD, beta vs SPY, volumen medio -> score de fuerza relativa
Etapa 2: fundamentales (.info) para el top N
Salida: screener_sectores_fav_20260805.json
"""
import yfinance as yf, pandas as pd, numpy as np, json, re, warnings
warnings.filterwarnings('ignore')

univ = json.load(open('clientes/universo_sectores_fav_20260805.json', encoding='utf-8'))
cache = json.load(open('clientes/sectores_industrias_cache.json', encoding='utf-8'))

BAD = re.compile(r'\.(SA|DE|L|VI|PA|MI|TO|NE|AX|MC|SW|CO|HK|T|SS)$')
tickers = []
for sector, lst in univ.items():
    for tk in lst:
        if not BAD.search(tk) and tk not in tickers:
            tickers.append(tk)
print('Universe US-listed:', len(tickers))

data = yf.download(tickers + ['SPY'], start='2025-08-01', end='2026-08-05',
                   group_by='column', auto_adjust=True, threads=True, progress=False)
close = data['Close'].dropna(how='all')
vol = data['Volume'].dropna(how='all') if 'Volume' in data else None
spy = close['SPY'].dropna()

def rsi14(c):
    if len(c) < 15: return None
    d = c.diff(); g = d.where(d > 0, 0).rolling(14).mean(); l = (-d.where(d < 0, 0)).rolling(14).mean()
    return float((100 - 100/(1 + g/l)).iloc[-1])

rows = []
for tk in close.columns:
    if tk == 'SPY': continue
    c = close[tk].dropna()
    if len(c) < 40:
        continue
    last = float(c.iloc[-1])
    def r(n): return (last/float(c.iloc[max(len(c)-n-1, 0)]) - 1)*100 if len(c) > n else None
    m = {'tk': tk, 'sector': cache.get(tk, {}).get('sector'),
         'industria': cache.get(tk, {}).get('industry'), 'ultimo': round(last, 2),
         'r1m': round(r(21), 1) if r(21) is not None else None,
         'r3m': round(r(63), 1) if r(63) is not None else None,
         'r6m': round(r(126), 1) if r(126) is not None else None,
         'r1y': round(r(252), 1) if r(252) is not None else None}
    if len(c) >= 50:
        s20 = c.rolling(20).mean().iloc[-1]; s50 = c.rolling(50).mean().iloc[-1]
        s200 = c.rolling(200).mean().iloc[-1] if len(c) >= 200 else None
        m['vs20'] = round((last/s20 - 1)*100, 1)
        m['vs50'] = round((last/s50 - 1)*100, 1)
        m['vs200'] = round((last/s200 - 1)*100, 1) if s200 else None
        if s200:
            m['tend'] = 'ALCISTA' if s20 > s50 > s200 else ('BAJISTA' if s20 < s50 < s200 else 'MIXTA')
        else:
            m['tend'] = 'ALCISTA' if s20 > s50 else 'BAJISTA'
    m['rsi'] = round(rsi14(c), 1) if rsi14(c) is not None else None
    m['mdd'] = round((float(c.min()/c.cummax().max()) - 1)*100, 1)
    m['vol_prom'] = int(vol[tk].tail(60).mean()) if vol is not None and len(vol[tk].dropna()) > 20 else 0
    # beta vs SPY
    try:
        j = pd.concat([c, spy], axis=1, join='inner').dropna()
        j = j.pct_change().dropna()
        if len(j) > 30:
            m['beta'] = round(float(np.polyfit(j.iloc[:, 1], j.iloc[:, 0], 1)[0]), 2)
        else:
            m['beta'] = None
    except Exception:
        m['beta'] = None
    # score de fuerza relativa vs SPY
    spy6 = (spy.iloc[-1]/spy.iloc[max(len(spy)-127, 0)] - 1)*100
    spy3 = (spy.iloc[-1]/spy.iloc[max(len(spy)-64, 0)] - 1)*100
    x6 = (m['r6m'] or 0) - spy6; x3 = (m['r3m'] or 0) - spy3
    trend_s = {'ALCISTA': 2, 'MIXTA': 1, 'BAJISTA': 0}.get(m.get('tend'), 1)
    m['x6'] = round(x6, 1); m['x3'] = round(x3, 1)
    m['score'] = round(0.45*x6 + 0.35*x3 + 0.20*trend_s, 1)
    rows.append(m)

rows.sort(key=lambda r: -r['score'])
print('Screener OK: %d tickers con datos' % len(rows))

# ---------------------------------------------------------- fundamentales top N
TOP = 35
top = rows[:TOP]
print('Fundamentales de top %d ...' % TOP)
for m in top:
    try:
        i = yf.Ticker(m['tk']).info
        m['pe'] = i.get('trailingPE'); m['pef'] = i.get('forwardPE')
        m['margen'] = i.get('profitMargins'); m['roe'] = i.get('returnOnEquity')
        m['eg'] = i.get('earningsGrowth'); m['rg'] = i.get('revenueGrowth')
        m['mcap'] = i.get('marketCap'); m['tgt'] = i.get('targetMeanPrice')
        m['nombre'] = i.get('longName') or i.get('shortName')
        m['beta_f'] = i.get('beta')
    except Exception as e:
        m['fund_err'] = str(e)[:80]
    print('  %-6s %s' % (m['tk'], m.get('nombre') or m.get('fund_err') or ''))

json.dump(rows, open('clientes/screener_sectores_fav_20260805.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('Guardado. Top 20:')
for m in rows[:20]:
    print('%-6s %-13s %-13s score %6.1f | x6 %+6.1f | x3 %+6.1f | 1M %+6.1f | RSI %s | %s' % (
        m['tk'], (m.get('nombre') or '')[:13], (m.get('sector') or '')[:13], m['score'],
        m.get('x6') or 0, m.get('x3') or 0, m.get('r1m') or 0,
        ('%.0f' % m['rsi']) if m.get('rsi') is not None else 'n/d', m.get('tend')))
