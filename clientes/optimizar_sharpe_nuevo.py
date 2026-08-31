# -*- coding: utf-8 -*-
"""
OPTIMIZACION MAX-SHARPE NUEVO UNIVERSO — 06/08/2026
Tareas 3-5: nuevo universo desde unificadocompleto.json (sectores favorecidos,
DISTINTO al optimizado anterior: sin XOM/PANW/UNH/LMT/MRVL/IWM/PFE/BMA/SLV) +
salud financiera + tecnico + cuantitativo + filtro de maximos + Max-Sharpe.
Recicla metodologia de backtest_markowitz.py y pt/09_efficient_frontier.py.
"""
import yfinance as yf, pandas as pd, numpy as np, warnings, json, math
from scipy.optimize import minimize
warnings.filterwarnings('ignore')

RF_ANN = 0.0368
PRES_REF = 1_000_000  # escala de referencia (montos por % — luego se escala al cliente)

# ---------------------------------------------------------- NUEVO universo (sectores favorecidos, nombres nuevos)
# (ticker_yf, sector, nombre)
NEW = [
 ('GLD', 'Metales', 'Oro'), ('SLV', 'Metales', 'Plata'), ('COPX', 'Metales', 'Cobre ETF'),
 ('CVX', 'Energia', 'Chevron'), ('COP', 'Energia', 'ConocoPhillips'), ('EOG', 'Energia', 'EOG'),
 ('FANG', 'Energia', 'Diamondback'), ('SLB', 'Energia', 'Schlumberger'), ('VIST', 'Energia', 'Vista'),
 ('HUM', 'Salud', 'Humana'), ('ABBV', 'Salud', 'AbbVie'), ('GILD', 'Salud', 'Gilead'),
 ('VRTX', 'Salud', 'Vertex'), ('JNJ', 'Salud', 'Johnson & Johnson'), ('AMGN', 'Salud', 'Amgen'),
 ('GS', 'Financiero', 'Goldman Sachs'), ('V', 'Financiero', 'Visa'), ('MA', 'Financiero', 'Mastercard'),
 ('BX', 'Financiero', 'Blackstone'), ('XYZ', 'Financiero', 'Block'), ('GGAL.BA', 'Financiero', 'Galicia'),
 ('CAT', 'Industrial', 'Caterpillar'), ('GE', 'Industrial', 'GE Aerospace'), ('HON', 'Industrial', 'Honeywell'),
 ('ETN', 'Industrial', 'Eaton'), ('NOC', 'Industrial', 'Northrop'), ('GD', 'Industrial', 'General Dynamics'),
 ('NVDA', 'Tecnologia', 'Nvidia'), ('GOOGL', 'Tecnologia', 'Alphabet'), ('MSFT', 'Tecnologia', 'Microsoft'),
 ('AMAT', 'Tecnologia', 'Applied Materials'), ('MU', 'Tecnologia', 'Micron'), ('TSM', 'Tecnologia', 'TSMC'),
 ('CEG', 'Nuclear', 'Constellation'), ('OKLO', 'Nuclear', 'Oklo'), ('VST', 'Nuclear', 'Vistra'),
]

# ---------------------------------------------------------- 1) serie 1y + tecnicos + salud
def rsi14(c):
    if len(c) < 15: return None
    d = c.diff(); g = d.where(d > 0, 0).rolling(14).mean(); l = (-d.where(d < 0, 0)).rolling(14).mean()
    return float((100 - 100/(1 + g/l)).iloc[-1])

print('[1] Descargando series + fundamentals (nuevo universo, %d tickers)...' % len(NEW))
prices, meta = {}, {}
for t, sec, nombre in NEW:
    try:
        h = yf.Ticker(t).history(period='1y')['Close'].dropna()
        if len(h) > 100:
            h.index = pd.DatetimeIndex([d.date() for d in h.index])
            prices[t] = h
    except Exception:
        pass
    try:
        i = yf.Ticker(t).info
        meta[t] = dict(pe=i.get('trailingPE'), pef=i.get('forwardPE'), margen=i.get('profitMargins'),
                       roe=i.get('returnOnEquity'), deuda=i.get('debtToEquity'), eg=i.get('earningsGrowth'),
                       rg=i.get('revenueGrowth'), fcf=i.get('freeCashflow'), beta=i.get('beta'),
                       nombre=i.get('longName') or nombre)
    except Exception:
        meta[t] = dict(nombre=nombre)

df = pd.DataFrame(prices).dropna()
print('  serie sincronizada: %d filas x %d activos' % df.shape)
rets = df.pct_change().dropna()
spy = None
try:
    hs = yf.Ticker('SPY').history(period='1y')['Close'].dropna()
    hs.index = pd.DatetimeIndex([d.date() for d in hs.index])
    spy = hs.reindex(df.index).ffill().dropna()
except Exception:
    pass

screen = []
for t in df.columns:
    c = df[t].dropna(); last = float(c.iloc[-1]); mx = float(c.max())
    dist = (last/mx - 1)*100
    rsi = rsi14(c)
    def r(n): return (last/float(c.iloc[max(len(c)-n-1, 0)]) - 1)*100 if len(c) > n else None
    b = None
    if spy is not None:
        j = pd.concat([c, spy], axis=1, join='inner').dropna().pct_change().dropna()
        if len(j) > 30:
            b = round(float(np.polyfit(j.iloc[:, 1], j.iloc[:, 0], 1)[0]), 2)
    m = meta.get(t, {})
    screen.append(dict(tk=t, sec=dict((s, n) for s, n in NEW)[t] if False else next(x[1] for x in NEW if x[0] == t),
                       nombre=m.get('nombre', t), last=round(last, 2), dist=round(dist, 1), rsi=round(rsi, 1) if rsi else None,
                       r1m=round(r(21), 1) if r(21) is not None else None, r3m=round(r(63), 1) if r(63) is not None else None,
                       r6m=round(r(126), 1) if r(126) is not None else None,
                       pe=m.get('pe'), pef=m.get('pef'), margen=m.get('margen'), roe=m.get('roe'),
                       deuda=m.get('deuda'), eg=m.get('eg'), rg=m.get('rg'), beta=b))
    flag = 'EN MAXIMO' if dist > -3 and (rsi or 99) > 65 else ('OK' if dist < -8 else 'cerca')
    print('  %-8s %-13s dist %+5.1f%% RSI %5.1f PEf %6s %s' % (t, screen[-1]['sec'], dist, rsi or 0, ('%.1f' % m['pef']) if m.get('pef') else '-', flag))

# ---------------------------------------------------------- 2) filtro: excluir EN MAXIMO
excl = [s['tk'] for s in screen if s['dist'] > -3 and (s['rsi'] or 99) > 65]
keep = [s['tk'] for s in screen if s['tk'] not in excl]
print('\n[2] Excluidos por EN MAXIMO (sin correccion):', excl)
print('    Universo para optimizar (%d):' % len(keep), keep)

# ---------------------------------------------------------- 3) Max-Sharpe
mu = rets[keep].mean()*252
sigma = rets[keep].cov()*252
n = len(keep)
def neg_sharpe(w):
    pr = float(np.dot(w, mu.values)); pv = float(np.sqrt(np.dot(w, np.dot(sigma.values, w))))
    return -(pr - RF_ANN)/pv if pv > 0 else 0
opt = minimize(neg_sharpe, np.ones(n)/n, method='SLSQP', bounds=[(0, 0.35)]*n,
               constraints=[{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}], options={'maxiter': 3000})
w = opt.x
pr = float(np.dot(w, mu.values)); pv = float(np.sqrt(np.dot(w, np.dot(sigma.values, w))))
sr = (pr - RF_ANN)/pv
print('\n[3] MAX-SHARPE: Sharpe %.2f | Ret anual %.1f%% | Vol %.1f%% | rf %.2f%%' % (sr, pr*100, pv*100, RF_ANN*100))

plan = []
print('\n[4] Composicion optimizada (pesos > 0.5%%):')
tot = 0
for i, t in enumerate(keep):
    wi = w[i]
    if wi < 0.005: continue
    s = next(x for x in screen if x['tk'] == t)
    monto = PRES_REF*wi
    plan.append((t, s['sec'], s['nombre'], round(wi*100, 1), monto))
    tot += monto
    print('  %-8s %-13s %6.1f%%  %s' % (t, s['sec'], wi*100, s['nombre'][:26]))
print('  Caja residual: %.1f%%' % ((PRES_REF-tot)/PRES_REF*100))

json.dump({'sharpe': sr, 'ret': pr, 'vol': pv, 'rf': RF_ANN, 'excluidos': excl,
           'screen': screen, 'plan': plan},
          open('clientes/optimizacion_nuevo_universo_20260806.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nguardado clientes/optimizacion_nuevo_universo_20260806.json')
