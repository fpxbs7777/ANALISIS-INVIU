# -*- coding: utf-8 -*-
"""
OPTIMIZACION MAX-SHARPE — BERTUCCI deploy $7.900.000 (06/08/2026)
Recicla la metodologia de clientes/backtest_markowitz.py (neg_sharpe + SLSQP)
y del toolkit pt/ (09_efficient_frontier). Universo FILTRADO:
  - Descartados por estar EN MAXIMOS sin correccion: RTX (RSI 87,8 a +0,0% del max),
    JPM (RSI 68,5 a -0,1% del max)
  - Se mantienen los que corrigieron bien (dist_max < -8%) o cercanos con RSI moderado
Tasa libre de riesgo: ^IRX 3M (3,68% anual). Restricciones: 0 <= w <= 0,35, suma=1.
Salida: pesos optimos + mapeo a montos/cantidades ARS + tramos + fee 0,90%.
"""
import yfinance as yf, pandas as pd, numpy as np, warnings, json, math
from scipy.optimize import minimize
warnings.filterwarnings('ignore')

RF_ANN = 0.0368  # Treasury 3M (^IRX) real 05/08
PRES = 7_900_000
FEE = 0.009

# universo filtrado: (ticker_yf, nombre, ticker_ars_para_cantidad, precio_ars)
UNIV = [
 ('GLD', 'Oro (corrigio -21%)', 'GLD.BA', 12310.0),
 ('SLV', 'Plata (corrigio -47%)', 'SLV.BA', 14750.0),
 ('NVDA', 'Nvidia', 'NVDA.BA', 14410.0),
 ('PANW', 'Palo Alto', 'PANW.BA', 11460.0),
 ('MRVL', 'Marvell (corrigio -33%)', 'MRVL.BA', 23960.0),
 ('CRWD', 'CrowdStrike', 'CRWD.BA', 4185.0),
 ('PFE', 'Pfizer (RSI 73, cuidado)', 'PFE.BA', 10100.0),
 ('UNH', 'UnitedHealth (RSI 39)', 'UNH.BA', 19680.0),
 ('HUM', 'Humana (RSI 29)', 'HUM', None),  # CEDEAR USD al CCL
 ('LMT', 'Lockheed (corrigio -14%)', 'LMT.BA', 45540.0),
 ('CVX', 'Chevron (corrigio -10%)', 'CVX.BA', 18350.0),
 ('XOM', 'Exxon (corrigio -10%)', 'XOM.BA', 23850.0),
 ('URA', 'Uranium ETF (corrigio -30%)', 'URA.BA', 13520.0),
 ('CCJ', 'Cameco (corrigio -29%)', 'CCJ.BA', 6480.0),
 ('IWM', 'Small Caps (a -0,6% del max)', 'IWM.BA', 47340.0),
 ('GGAL.BA', 'Galicia (corrigio -14%)', 'GGAL.BA', 7640.0),
 ('BMA.BA', 'Macro', 'BMA.BA', 14130.0),
 ('SUPV.BA', 'Supervielle (corrigio -28%)', 'SUPV.BA', 2825.0),
 ('VIST', 'Vista (shale)', 'VIST.BA', 33680.0),
 ('YPFD.BA', 'YPF (corrigio -8%)', 'YPFD.BA', 7685.0),
]
CCL = 1580.4
HUM_USD = 363.82

# ---------------------------------------------------------- 1) datos 1y
print('[1] Descargando series 1y ...')
prices = {}
for t, _, _, _ in UNIV:
    try:
        h = yf.Ticker(t).history(period='1y')['Close'].dropna()
        if len(h) > 100:
            # normalizar indice a solo fecha (US tiene timezone, .BA no) para alinear
            h.index = pd.DatetimeIndex([d.date() for d in h.index])
            prices[t] = h
            print('  %-9s %d pts' % (t, len(h)))
    except Exception as e:
        print('  %s ERR %s' % (t, str(e)[:60]))

df = pd.DataFrame(prices).dropna()
print('  serie sincronizada: %d filas x %d activos' % df.shape)
rets = df.pct_change().dropna()
mu = rets.mean() * 252
sigma = rets.cov() * 252

# ---------------------------------------------------------- 2) max sharpe
print('[2] Optimizando Max-Sharpe (SLSQP, 0<=w<=0.35) ...')
tickers = list(df.columns)
n = len(tickers)

def neg_sharpe(w):
    pr = float(np.dot(w, mu.loc[tickers].values))
    pv = float(np.sqrt(np.dot(w, np.dot(sigma.loc[tickers, tickers].values, w))))
    return -(pr - RF_ANN)/pv if pv > 0 else 0

x0 = np.ones(n)/n
bounds = [(0, 0.35)]*n
cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
opt = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=cons, options={'maxiter': 3000})
w = opt.x
pr = float(np.dot(w, mu.loc[tickers].values))
pv = float(np.sqrt(np.dot(w, np.dot(sigma.loc[tickers, tickers].values, w))))
sr = (pr - RF_ANN)/pv
print('  Sharpe maximo: %.3f | Retorno esp anual: %.1f%% | Vol anual: %.1f%%' % (sr, pr*100, pv*100))
print('  Benchmark SPY 1y: ret %+.1f%% vol ~14%% (ref)' % ((df['GLD'] if 'GLD' in df else df.iloc[:,0]).pct_change().mean()*252*100))

# ---------------------------------------------------------- 3) pesos -> montos/cantidades
print()
print('[3] Asignacion optimizada sobre $%s (fee %s%%):' % ('{:,.0f}'.format(PRES), FEE*100))
tot = 0
plan = []
for i, t in enumerate(tickers):
    wi = w[i]
    if wi < 0.005:
        continue
    monto = PRES*wi
    _, nombre, ars_tk, precio_ars = next(u for u in UNIV if u[0] == t)
    if precio_ars is None:  # HUM vía USD
        usd = monto/CCL
        cant = usd
        plan.append((t, nombre, wi, monto, None, usd, 'USD'))
        print('  %-9s %-26s %6.1f%% %12s  ~%6.0f USD' % (t, nombre, wi*100, '{:,.0f}'.format(monto), usd))
    else:
        cant = math.floor(monto/precio_ars)
        mr = cant*precio_ars
        plan.append((t, nombre, wi, mr, cant, precio_ars, 'ARS'))
        print('  %-9s %-26s %6.1f%% %12s  %5d x %9.0f' % (t, nombre, wi*100, '{:,.0f}'.format(mr), cant, precio_ars))
    tot += monto
caja = PRES - tot
print('  Caja residual: %s (%.1f%%)' % ('{:,.0f}'.format(caja), caja/PRES*100))
fee_total = tot*FEE
print('  Fee compras 0,90%%: %s | por tramo (1/3): %s' % ('{:,.0f}'.format(fee_total), '{:,.0f}'.format(fee_total/3)))

json.dump({'sharpe': sr, 'ret_anual': pr, 'vol_anual': pv, 'rf': RF_ANN,
           'presupuesto': PRES, 'caja': caja, 'fee': fee_total,
           'plan': [[p[0], p[1], p[2], p[3], p[4], p[5], p[6]] for p in plan]},
          open('clientes/optimizacion_sharpe_20260806.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('guardado clientes/optimizacion_sharpe_20260806.json')
