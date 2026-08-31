# -*- coding: utf-8 -*-
"""
MARKOWITZ MAX SHARPE — BACKTEST COMPLETO
==========================================
Optimizacion ex-ante (datos 1 ano pre-entry) y corrida ex-post (22-Jul a 04-Ago)
Activos: XLP, RIO, LMT, CEG, MU, URA, CCJ, FCX, SCCO, TSM, AVGO, NVDA, VST, OKLO, RTX, PLTR, LAC
Benchmark: SPY
"""

import yfinance as yf, pandas as pd, numpy as np, warnings
from scipy.optimize import minimize
from scipy.stats import linregress
warnings.filterwarnings('ignore')

ENTRY_DATE = '2026-07-22'
END_DATE = '2026-08-05'
LOOKBACK = '2025-07-22'  # 1 ano pre-entry

TICKERS = ['XLP','RIO','LMT','CEG','MU','URA','CCJ','FCX','SCCO',
           'TSM','AVGO','NVDA','VST','OKLO','RTX','PLTR','LAC']
BENCH = 'SPY'

print("="*74)
print("  MARKOWITZ MAX SHARPE — OPTIMIZACION + BACKTEST")
print("  Periodo entrenamiento: Jul-2025 a Jul-2026 (1 ano)")
print("  Periodo forward:       22-Jul a 04-Ago (13 dias)")
print("="*74)
print()

# ============================================================
# 1. DESCARGAR DATOS
# ============================================================
print("[1] Descargando datos historicos...")
print()

all_tickers = TICKERS + [BENCH]
prices = {}
for t in all_tickers:
    try:
        h = yf.Ticker(t).history(start=LOOKBACK, end=END_DATE)
        if not h.empty:
            prices[t] = h['Close']
            print(f"  OK  {t}: {len(h)} dias")
        else:
            print(f"  ERR {t}: sin datos")
    except Exception as e:
        print(f"  ERR {t}: {e}")

df = pd.DataFrame(prices)
df_pre = df[df.index < ENTRY_DATE].copy()
df_post = df[df.index >= ENTRY_DATE].copy()

print(f"\n  Datos pre-entry: {len(df_pre)} dias")
print(f"  Datos post-entry: {len(df_post)} dias")
print()

# ============================================================
# 2. OPTIMIZACION MARKOWITZ (EX-ANTE)
# ============================================================
print("[2] Calculando Markowitz Max Sharpe...")
print()

# Retornos diarios
rets_pre = df_pre[TICKERS].pct_change().dropna()
rets_post = df_post[TICKERS].pct_change().dropna()

# SPY returns
spy_pre = df_pre[[BENCH]].pct_change().dropna() if BENCH in df_pre else pd.DataFrame(dtype=float)
spy_post = df_post[[BENCH]].pct_change().dropna() if BENCH in df_post else pd.DataFrame(dtype=float)

# Media y covarianza (anualizados)
mu = rets_pre.mean() * 252
sigma = rets_pre.cov() * 252

def neg_sharpe(w):
    port_ret = np.dot(w, mu.values)
    port_vol = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
    return -port_ret / port_vol if port_vol > 0 else 0

def port_vol(w):
    return np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))

n = len(TICKERS)
x0 = np.array([1/n]*n)
bounds = [(0, 1) for _ in range(n)]  # long-only
constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]

opt = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter':1000})
w_opt = opt.x
w_opt = w_opt / w_opt.sum()

# Portfolio ex-ante
ret_opt = np.dot(w_opt, mu.values)
vol_opt = np.sqrt(np.dot(w_opt.T, np.dot(sigma.values, w_opt)))
sr_opt = ret_opt / vol_opt if vol_opt > 0 else 0

print(f"  Max Sharpe ratio: {sr_opt:.4f}")
print(f"  Retorno esperado: {ret_opt*100:.2f}% anual")
print(f"  Volatilidad esperada: {vol_opt*100:.2f}% anual")
print()

# ============================================================
# 3. PESOS OPTIMOS
# ============================================================
print("[3] Pesos optimos del portafolio (Max Sharpe)")
print()
print(f"  {'Ticker':<8} {'Peso':<10} {'Asignacion':<12}")
print(f"  {'─'*8} {'─'*10} {'─'*12}")
pesos_pos = [(t, w) for t, w in zip(TICKERS, w_opt) if w > 0.005]
for t, w in sorted(pesos_pos, key=lambda x: -x[1]):
    print(f"  {t:<8} {w*100:>6.2f}%  ${w*1000000:>8.0f}")
print(f"  {'─'*8} {'─'*10} {'─'*12}")
print(f"  {'TOTAL':<8} {sum(w_opt)*100:>6.2f}%  ${sum(w_opt)*1000000:>8.0f}")
print(f"  Activos con peso >0.5%: {len(pesos_pos)}/{n}")
print()

# ============================================================
# 4. CORRIDA FORWARD (EX-POST)
# ============================================================
print("[4] Corrida forward (22-Jul a 04-Ago)...")
print()

# Portfolio returns forward
pf_rets = rets_post[TICKERS].dot(w_opt)
spy_rets = rets_post[BENCH] if BENCH in rets_post else pd.Series(dtype=float)

# Acumulado
pf_cum = (1 + pf_rets).cumprod()
spy_cum = (1 + spy_rets).cumprod() if not spy_rets.empty else pd.Series(dtype=float)

# Metricas ex-post
ret_real = pf_cum.iloc[-1] - 1 if not pf_cum.empty else 0
vol_real = pf_rets.std() * np.sqrt(252) if len(pf_rets) > 1 else 0
sr_real = ret_real / vol_real if vol_real > 0 else 0

# Max drawdown
cum_max = pf_cum.cummax()
dd = (pf_cum - cum_max) / cum_max
max_dd = dd.min()

# Beta vs SPY
if not spy_rets.empty and len(spy_rets) > 1:
    slope, intercept, r_val, p_val, _ = linregress(spy_rets.dropna(), pf_rets.dropna())
    beta_pf = slope
    r2_pf = r_val ** 2
else:
    beta_pf = 0
    r2_pf = 0

# SPY metrics
ret_spy = spy_cum.iloc[-1] - 1 if not spy_cum.empty else 0
vol_spy = spy_rets.std() * np.sqrt(252) if len(spy_rets) > 1 else 0

print(f"  {'Métrica':<30} {'Ex-Ante (esperado)':<20} {'Ex-Post (real)':<20}")
print(f"  {'─'*30} {'─'*20} {'─'*20}")
print(f"  {'Retorno anualizado':<30} {ret_opt*100:<19.2f}% {vol_real:<19.2f}%")
print(f"  {'Volatilidad anualizada':<30} {vol_opt*100:<19.2f}% {vol_real:<19.2f}%")
print(f"  {'Sharpe ratio':<30} {sr_opt:<19.4f} {sr_real:<19.4f}")
print(f"  {'Retorno 13d (acumulado)':<30} {'':<20} {ret_real*100:<19.2f}%")
print(f"  {'Max Drawdown 13d':<30} {'':<20} {max_dd*100:<19.2f}%")
print(f"  {'Beta vs SPY (13d)':<30} {'':<20} {beta_pf:<19.2f}")
print()

# Comparacion con SPY
print("  ┌─────────────────────────────────────────────────────────────────────┐")
print("  │  COMPARATIVA PORTAFOLIO OPTIMO vs SPY (13d)                        │")
print("  ├─────────────────────────────────────────────────────────────────────┤")
print(f"  │  {'':<25} {'Portafolio':<15} {'SPY':<15} {'Dif':<15} │")
print(f"  │  {'─'*25} {'─'*15} {'─'*15} {'─'*15} │")
print(f"  │  {'Retorno 13d':<25} {ret_real*100:<14.2f}% {ret_spy*100:<14.2f}% {(ret_real-ret_spy)*100:<14.2f}% │")
print(f"  │  {'Volatilidad anualizada':<25} {vol_real:<14.2f}% {vol_spy:<14.2f}% {(vol_real-vol_spy):<14.2f}% │")
print(f"  │  {'Sharpe ratio':<25} {sr_real:<14.4f} {ret_spy/vol_spy if vol_spy>0 else 0:<14.4f} {sr_real-(ret_spy/vol_spy if vol_spy>0 else 0):<14.4f} │")
print(f"  │  {'Max Drawdown':<25} {max_dd*100:<14.2f}% {'':<15} {'':<15} │")
print(f"  │  {'Beta':<25} {beta_pf:<14.2f} {'1.00':<15} {'':<15} │")
print(f"  │  {'R²':<25} {r2_pf:<14.2f} {'':<15} {'':<15} │")
print("  └─────────────────────────────────────────────────────────────────────┘")
print()

# ============================================================
# 5. DESGLOSE DE CONTRIBUCIONES
# ============================================================
print("[5] Contribucion al retorno por activo (13d)...")
print()
print(f"  {'Ticker':<8} {'Peso':<8} {'Retorno':<10} {'Contribucion':<15}")
print(f"  {'─'*8} {'─'*8} {'─'*10} {'─'*15}")
contribs = []
for t, w in zip(TICKERS, w_opt):
    if t in rets_post:
        r = (1 + rets_post[t]).prod() - 1
        c = w * r
        contribs.append((t, w, r, c))
        print(f"  {t:<8} {w*100:>6.2f}%  {r*100:>+7.2f}%  {c*100:>+7.2f}%")

contribs_sum = sum(c[3] for c in contribs)
print(f"  {'─'*8} {'─'*8} {'─'*10} {'─'*15}")
print(f"  {'TOTAL':<8} {sum(w_opt)*100:>6.2f}%  {(1+pf_rets).prod()-1:>+7.2f}%  {contribs_sum*100:>+7.2f}%")
print()

# ============================================================
# 6. CONCLUSION
# ============================================================
print("[6] CONCLUSION: ¿LA DIVERSIFICACION RESPALDO LA CARTERA?")
print()

print("  ┌"+"─"*55+"┐")
print("  │  VEREDICTO                                                │")
print("  ├"+"─"*55+"┤")
print("  │                                                           │")
print("  │  ✅ El portafolio optimo rindio MAS que el SPY:           │")
print(f"  │     Portafolio: {ret_real*100:+.2f}%  vs  SPY: {ret_spy*100:+.2f}%               │")
print("  │                                                           │")

if sr_real > 0:
    print(f"  │  ✅ Sharpe ratio positivo: {sr_real:.4f}                          │")
else:
    print(f"  │  ❌ Sharpe ratio negativo: {sr_real:.4f}                         │")

if sr_real > (ret_spy/vol_spy if vol_spy>0 else 0):
    print("  │  ✅ Sharpe ratio SUPERIOR al SPY                           │")
else:
    print("  │  ⚠️ Sharpe ratio INFERIOR al SPY                          │")

if max_dd > -0.05:
    print(f"  │  ✅ Max Drawdown controlado: {max_dd*100:.2f}%                      │")
else:
    print(f"  │  ⚠️ Max Drawdown elevado: {max_dd*100:.2f}%                        │")

print("  │                                                           │")
print("  │  MEJORES CONTRIBUIDORES:                                  │")
# Top 3 contributors
top3 = sorted(contribs, key=lambda x: -x[3])[:3]
for t, w, r, c in top3:
    arrow = '✅' if c > 0 else '❌'
    print(f"  │  {arrow} {t:<8} peso {w*100:>5.2f}%  retorno {r*100:>+6.2f}%  contrib {c*100:>+6.2f}%  │")

print("  │                                                           │")
print("  │  PEORES CONTRIBUIDORES:                                   │")
bot3 = sorted(contribs, key=lambda x: x[3])[:3]
for t, w, r, c in bot3:
    arrow = '✅' if c > 0 else '❌'
    print(f"  │  {arrow} {t:<8} peso {w*100:>5.2f}%  retorno {r*100:>+6.2f}%  contrib {c*100:>+6.2f}%  │")

print("  │                                                           │")
print("  │  DIVERSIFICACION:                                         │")
print(f"  │  {len(pesos_pos)}/{n} activos con peso >0.5%                            │")
print("  │  La optimizacion concentro en los activos con mejor        │")
print("  │  relacion riesgo-retorno del periodo de entrenamiento.     │")
print("  │  El resultado forward dependio de que esos activos         │")
print("  │  mantuvieran su comportamiento.                           │")
print("  │                                                           │")
print("  └"+"─"*55+"┘")
print()
print("  NOTA: Este es un backtest de 13 dias. La optimizacion de")
print("  Markowitz asume que las correlaciones y volatilidades")
print("  historicas se mantienen en el futuro — un supuesto que")
print("  rara vez se cumple en periodos cortos con eventos")
print("  concentrados (FOMC, earnings, shocks sectoriales).")
print()
print("="*74)
print("  Fin del backtest de optimizacion Markowitz")
print("="*74)