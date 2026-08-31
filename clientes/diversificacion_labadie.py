# -*- coding: utf-8 -*-
"""
DIVERSIFICACION DE PORTAFOLIO — Metodologia Labadie
====================================================
Basada en la metodologia oficial de optimizacion de portafolios.
NO comprime pesos — muestra TODOS los activos con su peso real.

Metodologia:
1. Matriz de correlacion completa (9 activos)
2. Optimizacion Max Sharpe (SCIPY SLSQP, multiple initial points)
3. Optimizacion Min Variance
4. Simulacion Monte Carlo (5000 portafolios)
5. Frontera Eficiente
6. Comparacion: Optimo vs Equal-Weight vs SPY

Activos: XLP, RIO, LMT, CEG, MU, URA, CCJ, FCX, SCCO
Benchmark: SPY
Periodo entrenamiento: Jul-2025 a Jul-2026 (1 ano)
Periodo forward: 22-Jul a 04-Ago (13 dias)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.stats import linregress, skew, kurtosis
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACION
# ============================================================
TICKERS = ['XLP','RIO','LMT','CEG','MU','URA','CCJ','FCX','SCCO']
BENCH = 'SPY'
ENTRY_DATE = '2026-07-22'
END_DATE = '2026-08-05'
LOOKBACK = '2025-07-22'
RISK_FREE = 0.08  # 8% anual USD
TRADING_DAYS = 252
N_SIMULATIONS = 5000

print("=" * 74)
print("  DIVERSIFICACION DE PORTAFOLIO — Metodologia Labadie")
print("  9 activos | 1 ano de entrenamiento | 13 dias forward")
print("=" * 74)
print()

# ============================================================
# 1. DESCARGA DE DATOS
# ============================================================
print("[1] Descargando datos historicos...")
print()

all_t = TICKERS + [BENCH]
prices = {}
for t in all_t:
    h = yf.Ticker(t).history(start=LOOKBACK, end=END_DATE)
    if not h.empty:
        prices[t] = h['Close']
        print(f"  OK  {t}: {len(h)} dias")
    else:
        print(f"  ERR {t}: sin datos")

df = pd.DataFrame(prices)
df_pre = df[df.index < ENTRY_DATE].copy()
df_post = df[df.index >= ENTRY_DATE].copy()

rets_pre = df_pre[TICKERS].pct_change().dropna()
rets_post = df_post[TICKERS].pct_change().dropna()
spy_pre = df_pre[[BENCH]].pct_change().dropna()
spy_post = df_post[[BENCH]].pct_change().dropna()

print(f"\n  Pre-entry: {len(rets_pre)} dias")
print(f"  Post-entry: {len(rets_post)} dias")
print()

# ============================================================
# 2. MATRIZ DE CORRELACION
# ============================================================
print("[2] Matriz de correlacion (9 activos)")
print()

corr = rets_pre.corr()
print(f"  {'':<8}", end='')
for t in TICKERS:
    print(f"{t:<8}", end='')
print()
for t1 in TICKERS:
    print(f"  {t1:<8}", end='')
    for t2 in TICKERS:
        v = corr.loc[t1, t2]
        if v > 0.5:
            print(f"{v:>7.2f} ", end='')
        elif v > 0:
            print(f" {v:>6.2f} ", end='')
        else:
            print(f"{v:>7.2f} ", end='')
    print()
print()

# ============================================================
# 3. OPTIMIZACION MAX SHARPE (Metodologia Labadie)
# ============================================================
print("[3] Optimizacion Max Sharpe")
print()

mean_ret = rets_pre.mean() * TRADING_DAYS
cov_mat = rets_pre.cov() * TRADING_DAYS
n = len(TICKERS)

def neg_sharpe(w):
    pr = np.sum(mean_ret * w)
    pv = np.sqrt(np.dot(w.T, np.dot(cov_mat, w)))
    if pv == 0:
        return 1e10
    return -(pr - RISK_FREE) / pv

cons = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
bnds = tuple((0, 1) for _ in range(n))

# Multiple initial points (Labadie methodology)
best_res = None
best_sr = -np.inf
for seed in range(10):
    np.random.seed(seed)
    x0 = np.random.random(n)
    x0 = x0 / x0.sum()
    res = minimize(neg_sharpe, x0, method='SLSQP', bounds=bnds, constraints=cons, options={'maxiter': 1000})
    if res.success:
        w = res.x / res.x.sum()
        sr = -(neg_sharpe(w))
        if sr > best_sr:
            best_sr = sr
            best_res = res

w_ms = best_res.x / best_res.x.sum() if best_res is not None else np.array([1/n]*n)
ret_ms = np.sum(mean_ret * w_ms)
vol_ms = np.sqrt(np.dot(w_ms.T, np.dot(cov_mat, w_ms)))
sr_ms = (ret_ms - RISK_FREE) / vol_ms

print(f"  Max Sharpe ratio: {sr_ms:.4f}")
print(f"  Retorno esperado: {ret_ms*100:.2f}% anual")
print(f"  Volatilidad esperada: {vol_ms*100:.2f}% anual")
print()

print(f"  {'Ticker':<8} {'Peso':>8}")
print(f"  {'─'*8} {'─'*8}")
for t, w in sorted(zip(TICKERS, w_ms), key=lambda x: -x[1]):
    print(f"  {t:<8} {w*100:>7.2f}%")
print(f"  {'─'*8} {'─'*8}")
print(f"  {'TOTAL':<8} {sum(w_ms)*100:>7.2f}%")
print()

# ============================================================
# 4. OPTIMIZACION MIN VARIANCE
# ============================================================
print("[4] Optimizacion Min Variance")
print()

def port_var(w):
    return np.dot(w.T, np.dot(cov_mat, w))

best_res2 = None
best_var = np.inf
for seed in range(10):
    np.random.seed(seed)
    x0 = np.random.random(n)
    x0 = x0 / x0.sum()
    res = minimize(port_var, x0, method='SLSQP', bounds=bnds, constraints=cons, options={'maxiter': 1000})
    if res.success:
        v = port_var(res.x / res.x.sum())
        if v < best_var:
            best_var = v
            best_res2 = res

w_mv = best_res2.x / best_res2.x.sum() if best_res2 is not None else np.array([1/n]*n)
ret_mv = np.sum(mean_ret * w_mv)
vol_mv = np.sqrt(port_var(w_mv))
sr_mv = (ret_mv - RISK_FREE) / vol_mv

print(f"  Min Variance: {vol_mv*100:.2f}% anual")
print(f"  Retorno esperado: {ret_mv*100:.2f}% anual")
print(f"  Sharpe ratio: {sr_mv:.4f}")
print()
print(f"  {'Ticker':<8} {'Peso':>8}")
print(f"  {'─'*8} {'─'*8}")
for t, w in sorted(zip(TICKERS, w_mv), key=lambda x: -x[1]):
    print(f"  {t:<8} {w*100:>7.2f}%")
print(f"  {'─'*8} {'─'*8}")
print(f"  {'TOTAL':<8} {sum(w_mv)*100:>7.2f}%")
print()

# ============================================================
# 5. SIMULACION MONTE CARLO (5000 portafolios)
# ============================================================
print("[5] Simulacion Monte Carlo (5000 portafolios)")
print()

np.random.seed(42)
sim_rets = np.zeros(N_SIMULATIONS)
sim_vols = np.zeros(N_SIMULATIONS)
sim_srs = np.zeros(N_SIMULATIONS)
sim_weights = np.zeros((N_SIMULATIONS, n))

for i in range(N_SIMULATIONS):
    w = np.random.random(n)
    w = w / w.sum()
    sim_weights[i] = w
    sim_rets[i] = np.sum(mean_ret * w)
    sim_vols[i] = np.sqrt(np.dot(w.T, np.dot(cov_mat, w)))
    sim_srs[i] = (sim_rets[i] - RISK_FREE) / sim_vols[i] if sim_vols[i] > 0 else 0

print(f"  Portafolios simulados: {N_SIMULATIONS}")
print(f"  Sharpe maximo simulado: {sim_srs.max():.4f}")
print(f"  Sharpe promedio simulado: {sim_srs.mean():.4f}")
print(f"  Sharpe minimo simulado: {sim_srs.min():.4f}")
print()

# ============================================================
# 6. COMPARATIVA EX-ANTE (3 portafolios + SPY)
# ============================================================
print("[6] Comparativa Ex-Ante")
print()

# Equal weight
w_eq = np.array([1/n]*n)
ret_eq = np.sum(mean_ret * w_eq)
vol_eq = np.sqrt(np.dot(w_eq.T, np.dot(cov_mat, w_eq)))
sr_eq = (ret_eq - RISK_FREE) / vol_eq

# SPY
ret_spy_pre = spy_pre.mean().iloc[0] * TRADING_DAYS
vol_spy_pre = spy_pre.std().iloc[0] * np.sqrt(TRADING_DAYS)
sr_spy_pre = (ret_spy_pre - RISK_FREE) / vol_spy_pre

print(f"  {'Portafolio':<20} {'Retorno':>10} {'Volatilidad':>12} {'Sharpe':>10}")
print(f"  {'─'*20} {'─'*10} {'─'*12} {'─'*10}")
print(f"  {'Max Sharpe':<20} {ret_ms*100:>9.2f}% {vol_ms*100:>11.2f}% {sr_ms:>9.4f}")
print(f"  {'Min Variance':<20} {ret_mv*100:>9.2f}% {vol_mv*100:>11.2f}% {sr_mv:>9.4f}")
print(f"  {'Equal Weight':<20} {ret_eq*100:>9.2f}% {vol_eq*100:>11.2f}% {sr_eq:>9.4f}")
print(f"  {'SPY':<20} {ret_spy_pre*100:>9.2f}% {vol_spy_pre*100:>11.2f}% {sr_spy_pre:>9.4f}")
print()

# ============================================================
# 7. CORRIDA FORWARD (EX-POST)
# ============================================================
print("[7] Corrida Forward (22-Jul a 04-Ago)")
print()

def forward(w, label):
    pf_rets = rets_post.dot(w)
    pf_cum = (1 + pf_rets).cumprod()
    ret = pf_cum.iloc[-1] - 1
    vol = pf_rets.std() * np.sqrt(TRADING_DAYS)
    sr = (ret * TRADING_DAYS / len(pf_rets) - RISK_FREE) / vol if vol > 0 else 0
    dd = ((pf_cum / pf_cum.cummax()) - 1).min()
    return ret, vol, sr, dd

ret_ms_f, vol_ms_f, sr_ms_f, dd_ms_f = forward(w_ms, 'Max Sharpe')
ret_mv_f, vol_mv_f, sr_mv_f, dd_mv_f = forward(w_mv, 'Min Variance')
ret_eq_f, vol_eq_f, sr_eq_f, dd_eq_f = forward(w_eq, 'Equal Weight')

# SPY forward
spy_rets_f = spy_post.iloc[:, 0]
spy_cum_f = (1 + spy_rets_f).cumprod()
ret_spy_f = spy_cum_f.iloc[-1] - 1
vol_spy_f = spy_rets_f.std() * np.sqrt(TRADING_DAYS)
sr_spy_f = (ret_spy_f * TRADING_DAYS / len(spy_rets_f) - RISK_FREE) / vol_spy_f if vol_spy_f > 0 else 0

print(f"  {'Portafolio':<20} {'Retorno 13d':>12} {'Vol. Anual':>12} {'Sharpe':>10} {'MaxDD':>10}")
print(f"  {'─'*20} {'─'*12} {'─'*12} {'─'*10} {'─'*10}")
print(f"  {'Max Sharpe':<20} {ret_ms_f*100:>11.2f}% {vol_ms_f*100:>11.2f}% {sr_ms_f:>9.4f} {dd_ms_f*100:>9.2f}%")
print(f"  {'Min Variance':<20} {ret_mv_f*100:>11.2f}% {vol_mv_f*100:>11.2f}% {sr_mv_f:>9.4f} {dd_mv_f*100:>9.2f}%")
print(f"  {'Equal Weight':<20} {ret_eq_f*100:>11.2f}% {vol_eq_f*100:>11.2f}% {sr_eq_f:>9.4f} {dd_eq_f*100:>9.2f}%")
print(f"  {'SPY':<20} {ret_spy_f*100:>11.2f}% {vol_spy_f*100:>11.2f}% {sr_spy_f:>9.4f} {'':>9}")
print()

# ============================================================
# 8. CONTRIBUCION AL RETORNO POR ACTIVO
# ============================================================
print("[8] Contribucion al retorno por activo (13d)")
print()

print(f"  {'Ticker':<8} {'Peso MS':>8} {'Peso MV':>8} {'Peso EQ':>8} {'Retorno':>8} {'Contrib MS':>10} {'Contrib MV':>10}")
print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")
contribs = []
for i, t in enumerate(TICKERS):
    r = (1 + rets_post.iloc[:, i]).prod() - 1
    c_ms = w_ms[i] * r
    c_mv = w_mv[i] * r
    c_eq = w_eq[i] * r
    contribs.append((t, w_ms[i], w_mv[i], w_eq[i], r, c_ms, c_mv))
    print(f"  {t:<8} {w_ms[i]*100:>7.2f}% {w_mv[i]*100:>7.2f}% {w_eq[i]*100:>7.2f}% {r*100:>7.2f}% {c_ms*100:>9.2f}% {c_mv*100:>9.2f}%")

print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")
tot_c_ms = sum(c[5] for c in contribs)
tot_c_mv = sum(c[6] for c in contribs)
print(f"  {'TOTAL':<8} {sum(w_ms)*100:>7.2f}% {sum(w_mv)*100:>7.2f}% {sum(w_eq)*100:>7.2f}% {'':>8} {tot_c_ms*100:>9.2f}% {tot_c_mv*100:>9.2f}%")
print()

# ============================================================
# 9. CORRELACION DE LOS PORTafolIOS CON SPY
# ============================================================
print("[9] Correlacion de los portafolios con SPY")
print()

pf_ms_rets = rets_post.dot(w_ms)
pf_mv_rets = rets_post.dot(w_mv)
pf_eq_rets = rets_post.dot(w_eq)
spy_ret_vec = spy_rets_f

for label, vec in [('Max Sharpe', pf_ms_rets), ('Min Variance', pf_mv_rets), ('Equal Weight', pf_eq_rets)]:
    n_min = min(len(vec), len(spy_ret_vec))
    r = np.corrcoef(vec.iloc[:n_min], spy_ret_vec.iloc[:n_min])[0, 1]
    print(f"  {label:<20} correlacion con SPY: {r:.4f}")
print()

# ============================================================
# 10. CONCLUSION
# ============================================================
print("[10] CONCLUSION: ¿LA DIVERSIFICACION RESPALDO LA CARTERA?")
print()

print("  ┌"+"─"*55+"┐")
print("  │  COMPARATIVA EX-POST (13 DIAS)                     │")
print("  ├"+"─"*55+"┤")
print(f"  │  {'Portafolio':<20} {'Retorno':<12} {'Vol':<12} {'Sharpe':<10} │")
print(f"  │  {'─'*20} {'─'*12} {'─'*12} {'─'*10} │")
print(f"  │  {'Max Sharpe':<20} {ret_ms_f*100:<11.2f}% {vol_ms_f*100:<11.2f}% {sr_ms_f:<9.4f} │")
print(f"  │  {'Min Variance':<20} {ret_mv_f*100:<11.2f}% {vol_mv_f*100:<11.2f}% {sr_mv_f:<9.4f} │")
print(f"  │  {'Equal Weight':<20} {ret_eq_f*100:<11.2f}% {vol_eq_f*100:<11.2f}% {sr_eq_f:<9.4f} │")
print(f"  │  {'SPY':<20} {ret_spy_f*100:<11.2f}% {vol_spy_f*100:<11.2f}% {sr_spy_f:<9.4f} │")
print("  ├"+"─"*55+"┤")

# Determine best
best_ret = max([(ret_ms_f, 'Max Sharpe'), (ret_mv_f, 'Min Variance'), (ret_eq_f, 'Equal Weight'), (ret_spy_f, 'SPY')])
best_sr_f = max([(sr_ms_f, 'Max Sharpe'), (sr_mv_f, 'Min Variance'), (sr_eq_f, 'Equal Weight'), (sr_spy_f, 'SPY')])
best_dd = max([(dd_ms_f, 'Max Sharpe'), (dd_mv_f, 'Min Variance'), (dd_eq_f, 'Equal Weight')], key=lambda x: x[0])

print(f"  │  Mejor retorno: {best_ret[1]:<20} {best_ret[0]*100:>+.2f}%{'':>19}│")
print(f"  │  Mejor Sharpe:  {best_sr_f[1]:<20} {best_sr_f[0]:>.4f}{'':>19}│")
print(f"  │  Mejor MaxDD:   {best_dd[1]:<20} {best_dd[0]*100:>+.2f}%{'':>19}│")
print("  ├"+"─"*55+"┤")
print("  │  PESOS DEL PORTAFOLIO MAX SHARPE                    │")
print("  │  (sin comprimir — todos los activos)               │")
for t, w in sorted(zip(TICKERS, w_ms), key=lambda x: -x[1]):
    if w > 0.01:
        print(f"  │  {t:<8} {w*100:>5.2f}%{'':>40}│")
    else:
        print(f"  │  {t:<8} {w*100:>5.2f}% (peso menor){'':>26}│")
print("  └"+"─"*55+"┘")
print()
print("  NOTA: La optimizacion se realizo con datos de 1 ano (Jul-2025 a Jul-2026)")
print("  usando la metodologia Labadie: SLSQP con 10 initial points, matriz de")
print("  covarianza anualizada, restriccion long-only, suma de pesos = 1.")
print("  El resultado forward de 13 dias no valida ni invalida la optimizacion")
print("  ex-ante — las correlaciones y volatilidades cambian en el tiempo.")
print()
print("="*74)
print("  Fin del analisis de diversificacion — Metodologia Labadie")
print("="*74)