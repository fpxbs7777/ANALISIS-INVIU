# -*- coding: utf-8 -*-
"""
===============================================================================
  ANÁLISIS PORTAFOLIO CEDEARS — Composición Actual vs Optimizaciones
  Usa yfinance para datos reales. Compara tu portafolio con:
  - Equi-Weight, Vol-Weighted, Min-Variance, Max-Sharpe, Markowitz
===============================================================================
  Ejecutar: python analisis_cedears.py
===============================================================================
"""

import numpy as np
import pandas as pd
import scipy.optimize as op
import scipy.stats as st
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# TU PORTAFOLIO CEDEARS — Composición actual
# ─────────────────────────────────────────────────────────────────────────────
TICKERS = [
    'AAPL.BA', 'AMZN.BA', 'GOOGL.BA', 'JD.BA',
    'LMT.BA',  'MSFT.BA',  'NU.BA',    'PEP.BA',
    'PFE.BA',  'SLV.BA',   'URA.BA',   'XLE.BA'
]

CANTIDADES = {
    'AAPL.BA': 170, 'AMZN.BA': 489, 'GOOGL.BA': 50,  'JD.BA': 44,
    'LMT.BA':  65,  'MSFT.BA': 145, 'NU.BA':    280, 'PEP.BA': 246,
    'PFE.BA':  62,  'SLV.BA':  84,  'URA.BA':   35,  'XLE.BA': 8
}

# Precios actuales en USD (del extracto que compartiste)
PRECIOS_USD = {
    'AAPL.BA': 12.24,  'AMZN.BA': 1.29,   'GOOGL.BA': 2.61,  'JD.BA': 6.97,
    'LMT.BA':  25.28,  'MSFT.BA': 13.32,  'NU.BA':    6.47,  'PEP.BA': 8.25,
    'PFE.BA':  6.50,   'SLV.BA':  12.56,  'URA.BA':   9.20,  'XLE.BA': 20.87
}

START_DATE  = "2022-01-01"
FACTOR       = 252          # días hábiles
NOTIONAL_MM  = 1.0

print("=" * 70)
print("  ANÁLISIS PORTAFOLIO CEDEARS — Composición Actual vs Optimizaciones")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# 1. DESCARGA DE DATOS HISTÓRICOS
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[→] Descargando datos para {len(TICKERS)} Cedears desde {START_DATE}...")
raw = yf.download(TICKERS, start=START_DATE, auto_adjust=True, progress=False)

if isinstance(raw.columns, pd.MultiIndex):
    prices = raw["Close"].copy()
else:
    prices = raw[["Close"]].copy()
    prices.columns = TICKERS

valid = [c for c in prices.columns if prices[c].count() >= 60]
dropped = set(TICKERS) - set(valid)
if dropped:
    print(f"  [!] Descartados por datos insuficientes: {dropped}")
prices = prices[valid].ffill().dropna(how="all")
print(f"  [✓] {len(valid)} activos válidos, {len(prices)} fechas")

returns_df = np.log(prices / prices.shift(1)).dropna()
tickers_final = list(returns_df.columns)

# ─────────────────────────────────────────────────────────────────────────────
# 2. OBTENER PRECIOS ACTUALES DE yfinance (para calcular pesos reales)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[→] Obteniendo precios actuales...")
precios_actuales = {}
for t in tickers_final:
    try:
        info = yf.Ticker(t).info
        px = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if px:
            precios_actuales[t] = float(px)
        else:
            # fallback: último precio de la serie histórica
            precios_actuales[t] = float(prices[t].dropna().iloc[-1])
    except:
        precios_actuales[t] = float(prices[t].dropna().iloc[-1])

# ─────────────────────────────────────────────────────────────────────────────
# 3. CALCULAR PESOS ACTUALES DEL PORTAFOLIO
# ─────────────────────────────────────────────────────────────────────────────
valores = {}
for t in tickers_final:
    qty = CANTIDADES.get(t, 0)
    values = precios_actuales.get(t, 0) * qty
    valores[t] = values

total_valor = sum(valores.values())
pesos_actuales = {t: valores[t] / total_valor for t in tickers_final}

print("\n── COMPOSICIÓN ACTUAL DEL PORTAFOLIO ────────────────────────")
print(f"{'Ticker':<12} {'Cant.':>6} {'Precio USD':>10} {'Valor USD':>12} {'Peso %':>8}")
print("-" * 55)
for t in tickers_final:
    print(f"{t:<12} {CANTIDADES.get(t,0):>6} {precios_actuales[t]:>10.2f} {valores[t]:>12.2f} {pesos_actuales[t]*100:>7.1f}%")
print("-" * 55)
print(f"{'TOTAL':<12} {'':>6} {'':>10} {total_valor:>12.2f} {'100.0%':>8}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. ESTADÍSTICAS INDIVIDUALES
# ─────────────────────────────────────────────────────────────────────────────
mean_vec = returns_df.mean().values * FACTOR
vol_vec  = returns_df.std().values * np.sqrt(FACTOR)
mtx_cov  = np.cov(returns_df.values, rowvar=False) * FACTOR
mtx_corr = np.corrcoef(returns_df.values, rowvar=False)
sharpe_vec = np.where(vol_vec > 0, mean_vec / vol_vec, 0)

print("\n── ESTADÍSTICAS INDIVIDUALES ─────────────────────────────────")
df_stats = pd.DataFrame({
    "Ticker":    tickers_final,
    "Ret Anual": [f"{r*100:.2f}%" for r in mean_vec],
    "Vol Anual": [f"{v*100:.2f}%" for v in vol_vec],
    "Sharpe":    [f"{s:.3f}" for s in sharpe_vec],
    "Peso Act.": [f"{pesos_actuales[t]*100:.1f}%" for t in tickers_final],
})
df_stats = df_stats.sort_values("Sharpe", key=lambda x: [float(i) for i in x], ascending=False)
print(df_stats.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# 5. PORTAFOLIO ACTUAL — Estadísticas
# ─────────────────────────────────────────────────────────────────────────────
n = len(tickers_final)
w_actual = np.array([pesos_actuales[t] for t in tickers_final])

port_actual_ret = float(mean_vec @ w_actual)
port_actual_vol = float(np.sqrt(w_actual @ mtx_cov @ w_actual))
port_actual_sharpe = port_actual_ret / port_actual_vol if port_actual_vol > 0 else 0

# Daily returns of actual portfolio
port_actual_daily = (returns_df.values * w_actual).sum(axis=1)
var_95_actual = np.percentile(port_actual_daily, 5)

print("\n── PORTAFOLIO ACTUAL — Estadísticas ──────────────────────────")
print(f"  Retorno anual:   {port_actual_ret*100:.2f}%")
print(f"  Volatilidad:     {port_actual_vol*100:.2f}%")
print(f"  Sharpe Ratio:    {port_actual_sharpe:.3f}")
print(f"  VaR 95% (diario): {var_95_actual*100:.4f}%")
print(f"  Valor total:     USD {total_valor:,.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. OPTIMIZACIÓN DE PORTAFOLIOS
# ─────────────────────────────────────────────────────────────────────────────
print("\n── OPTIMIZANDO PORTAFOLIOS ───────────────────────────────────")

def _port_variance(w, cov):
    return float(w @ cov @ w)

x0 = np.array([1/n] * n)
l1_eq = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
bounds = [(0, None)] * n
tr = float(np.mean(mean_vec))
ret_eq = {"type": "eq", "fun": lambda x, r=tr: mean_vec @ x - r}

resultados = []

# ── 6.1 Equi-Weight ──────────────────────────────────────────────────────
w_ew = x0.copy()
r_ew = float(mean_vec @ w_ew)
v_ew = float(np.sqrt(_port_variance(w_ew, mtx_cov)))
s_ew = r_ew / v_ew if v_ew > 0 else 0
resultados.append({"Nombre": "Equi-Weight", "Ret": r_ew, "Vol": v_ew, "Sharpe": s_ew, "Pesos": w_ew})

# ── 6.2 Volatility-Weighted ───────────────────────────────────────────────
inv_vol = 1 / np.where(vol_vec > 0, vol_vec, 1e-8)
w_vw = inv_vol / np.sum(inv_vol)
r_vw = float(mean_vec @ w_vw)
v_vw = float(np.sqrt(_port_variance(w_vw, mtx_cov)))
s_vw = r_vw / v_vw if v_vw > 0 else 0
resultados.append({"Nombre": "Vol-Weighted", "Ret": r_vw, "Vol": v_vw, "Sharpe": s_vw, "Pesos": w_vw})

# ── 6.3 Min-Variance (Long-Only) ──────────────────────────────────────────
try:
    res_mv = op.minimize(_port_variance, x0, args=(mtx_cov,),
                         constraints=[l1_eq], bounds=bounds, method="SLSQP")
    w_mv = res_mv.x
    w_mv /= np.sum(w_mv)
    r_mv = float(mean_vec @ w_mv)
    v_mv = float(np.sqrt(_port_variance(w_mv, mtx_cov)))
    s_mv = r_mv / v_mv if v_mv > 0 else 0
    resultados.append({"Nombre": "Min-Variance", "Ret": r_mv, "Vol": v_mv, "Sharpe": s_mv, "Pesos": w_mv})
except Exception as e:
    print(f"  [!] Min-Variance falló: {e}")

# ── 6.4 Max-Sharpe ────────────────────────────────────────────────────────
def neg_sharpe(w):
    r = float(mean_vec @ w)
    v = float(np.sqrt(_port_variance(w, mtx_cov)))
    return -r / v if v > 0 else 1e9

try:
    res_ms = op.minimize(neg_sharpe, x0, constraints=[l1_eq],
                         bounds=bounds, method="SLSQP")
    w_ms = res_ms.x
    w_ms /= np.sum(w_ms)
    r_ms = float(mean_vec @ w_ms)
    v_ms = float(np.sqrt(_port_variance(w_ms, mtx_cov)))
    s_ms = r_ms / v_ms if v_ms > 0 else 0
    resultados.append({"Nombre": "Max-Sharpe", "Ret": r_ms, "Vol": v_ms, "Sharpe": s_ms, "Pesos": w_ms})
except Exception as e:
    print(f"  [!] Max-Sharpe falló: {e}")

# ── 6.5 Markowitz ─────────────────────────────────────────────────────────
try:
    res_mk = op.minimize(_port_variance, x0, args=(mtx_cov,),
                         constraints=[l1_eq, ret_eq], bounds=bounds, method="SLSQP")
    w_mk = res_mk.x
    w_mk /= np.sum(w_mk)
    r_mk = float(mean_vec @ w_mk)
    v_mk = float(np.sqrt(_port_variance(w_mk, mtx_cov)))
    s_mk = r_mk / v_mk if v_mk > 0 else 0
    resultados.append({"Nombre": "Markowitz", "Ret": r_mk, "Vol": v_mk, "Sharpe": s_mk, "Pesos": w_mk})
except Exception as e:
    print(f"  [!] Markowitz falló: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. TABLA COMPARATIVA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  COMPARATIVA: PORTAFOLIO ACTUAL vs OPTIMIZACIONES")
print("=" * 70)
print(f"{'Estrategia':<18} {'Retorno %':>10} {'Vol %':>10} {'Sharpe':>10} {'Mejora Sharpe':>16}")
print("-" * 70)

# Actual primero
print(f"{'*** ACTUAL ***':<18} {port_actual_ret*100:>9.2f}% {port_actual_vol*100:>9.2f}% {port_actual_sharpe:>10.3f} {'—':>16}")

for r in sorted(resultados, key=lambda x: x["Sharpe"], reverse=True):
    mejora = (r["Sharpe"] - port_actual_sharpe) / abs(port_actual_sharpe) * 100 if port_actual_sharpe != 0 else 0
    print(f"{r['Nombre']:<18} {r['Ret']*100:>9.2f}% {r['Vol']*100:>9.2f}% {r['Sharpe']:>10.3f} {mejora:>15.1f}%")
print("-" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# 8. MEJOR PORTAFOLIO — DESGLOSE DE PESOS
# ─────────────────────────────────────────────────────────────────────────────
best = max(resultados, key=lambda x: x["Sharpe"])
print(f"\n── MEJOR ESTRATEGIA: {best['Nombre']} (Sharpe={best['Sharpe']:.3f}) ──")
print(f"{'Ticker':<12} {'Peso Óptimo':>12} {'Peso Actual':>12} {'Diferencia':>12}")
print("-" * 52)
for i, t in enumerate(tickers_final):
    diff = (best["Pesos"][i] - w_actual[i]) * 100
    marker = " <<<" if abs(diff) > 5 else ""
    print(f"{t:<12} {best['Pesos'][i]*100:>11.1f}% {w_actual[i]*100:>11.1f}% {diff:>11.1f}%{marker}")
print("-" * 52)

# ─────────────────────────────────────────────────────────────────────────────
# 9. GRÁFICOS (opcional, si hay matplotlib)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Gráfico 1: Barras comparativas Sharpe
    nombres = ["ACTUAL"] + [r["Nombre"] for r in sorted(resultados, key=lambda x: x["Sharpe"], reverse=True)]
    sharpes = [port_actual_sharpe] + [r["Sharpe"] for r in sorted(resultados, key=lambda x: x["Sharpe"], reverse=True)]
    colors = ["#ef4444" if n == "ACTUAL" else "#3b82f6" for n in nombres]
    axes[0].barh(nombres, sharpes, color=colors, height=0.6)
    axes[0].set_xlabel("Sharpe Ratio")
    axes[0].set_title("Sharpe Ratio por Estrategia")
    for i, v in enumerate(sharpes):
        axes[0].text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)
    axes[0].invert_yaxis()
    axes[0].grid(axis="x", alpha=0.3)

    # Gráfico 2: Pesos Actual vs Óptimo (Max-Sharpe)
    best_sharpe = max(resultados, key=lambda x: x["Sharpe"])
    x_ticks = range(len(tickers_final))
    w_opt = best_sharpe["Pesos"] * 100
    w_curr = w_actual * 100
    width = 0.35
    bars1 = axes[1].bar([x - width/2 for x in x_ticks], w_curr, width, label="Actual", color="#ef4444", alpha=0.8)
    bars2 = axes[1].bar([x + width/2 for x in x_ticks], w_opt, width, label=best_sharpe["Nombre"], color="#3b82f6", alpha=0.8)
    axes[1].set_xlabel("Ticker")
    axes[1].set_ylabel("Peso %")
    axes[1].set_title(f"Composición Actual vs {best_sharpe['Nombre']}")
    axes[1].set_xticks(x_ticks)
    axes[1].set_xticklabels([t.replace(".BA", "") for t in tickers_final], rotation=45, ha="right", fontsize=9)
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.show()
    print("\n[✓] Gráficos generados.")
except ImportError:
    print("\n[!] matplotlib no disponible — omitiendo gráficos.")

print("\n[✓] Análisis completado.")
