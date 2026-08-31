# -*- coding: utf-8 -*-
"""Analisis de Sharpe mensual y escenarios de duplicacion de capital - Bertucci."""
import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import minimize

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data import load_many

# ============================================================
# DATOS BERTUCCI (portafolios_inviu.json)
# ============================================================
PATRIMONIO_TOTAL_USD = 16876.32
CASH_USD = 10011.57
CASH_ARS = 1028223.09
CASH_USD_C = 0.0

# Tenencias en ARS (todas cedears o acciones locales)
TENENCIAS = [
    {"ticker": "PAMP", "acciones": 74, "precio_ars": 5085.0, "sector": "Energia"},
    {"ticker": "AMZN", "acciones": 109, "precio_ars": 2915.0, "sector": "Discrecional"},
    {"ticker": "GOOGL", "acciones": 61, "precio_ars": 9610.0, "sector": "Comunicacion"},
    {"ticker": "IBM", "acciones": 4, "precio_ars": 24680.0, "sector": "Tecnologia"},
    {"ticker": "MU", "acciones": 1, "precio_ars": 298050.0, "sector": "Tecnologia"},
    {"ticker": "NU", "acciones": 16, "precio_ars": 11730.0, "sector": "Financieras"},
    {"ticker": "NVDA", "acciones": 56, "precio_ars": 14270.0, "sector": "Tecnologia"},
    {"ticker": "SMH", "acciones": 2, "precio_ars": 17820.0, "sector": "Tecnologia"},
    {"ticker": "SPY", "acciones": 331, "precio_ars": 20430.0, "sector": "Benchmark"},
    {"ticker": "TSM", "acciones": 1, "precio_ars": 74125.0, "sector": "Tecnologia"},
    {"ticker": "URA", "acciones": 3, "precio_ars": 15040.0, "sector": "Energia"},
    {"ticker": "XLE", "acciones": 6, "precio_ars": 49980.0, "sector": "Energia"},
]

# Tickers para optimizacion (USD)
TICKERS_OPTIMIZAR = [
    "SPY", "QQQ", "IWM", "XLK", "XLE", "XLI", "XLF", "XLY", "XLP", "XLV",
    "XLC", "XLB", "XLU", "XLRE", "GLD", "TLT", "VTV", "VUG",
    "AMZN", "NVDA", "AAPL", "MSFT", "GOOGL", "META", "TSLA",
    "LMT", "CVS", "PEP", "PFE", "SLV",
]

# ============================================================
# FUNCIONES
# ============================================================

def optimizar_max_sharpe(returns_df, risk_free_annual=0.05, min_peso=0.0):
    """Optimizacion Markowitz long-only max Sharpe."""
    returns_df = returns_df.dropna(how="any", axis=1).dropna(how="any", axis=0)
    if returns_df.shape[1] < 2 or len(returns_df) < 60:
        return None

    mu = returns_df.mean() * 252
    sigma = returns_df.cov() * 252
    n = len(mu)

    def neg_sharpe(w):
        rp = np.dot(w, mu.values)
        vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
        return -(rp - risk_free_annual) / vp if vp > 0 else 0

    x0 = np.array([1 / n] * n)
    bounds = [(min_peso, 1)] * n
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    opt = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 1000})
    if not opt.success:
        return None
    w = opt.x / opt.x.sum()
    rp = np.dot(w, mu.values)
    vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
    sharpe = (rp - risk_free_annual) / vp

    # Metricas mensuales
    returns_monthly = returns_df.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    port_monthly = (returns_monthly * w).sum(axis=1)
    sharpe_mensual = port_monthly.mean() / port_monthly.std() * np.sqrt(12) if port_monthly.std() > 0 else 0
    vol_mensual = port_monthly.std()
    ret_mensual = port_monthly.mean()
    max_dd_monthly = (port_monthly.cumsum() - port_monthly.cumsum().cummax()).min()

    return {
        "tickers": list(returns_df.columns),
        "pesos": w,
        "retorno_anual": rp,
        "volatilidad_anual": vp,
        "sharpe_anual": sharpe,
        "sharpe_mensual": sharpe_mensual,
        "ret_mensual": ret_mensual,
        "vol_mensual": vol_mensual,
        "max_dd_monthly": max_dd_monthly,
        "returns_monthly": port_monthly,
    }


def calcular_tenencias_usd():
    """Calcula el valor USD de cada tenencia."""
    filas = []
    for t in TENENCIAS:
        valor_ars = t["acciones"] * t["precio_ars"]
        valor_usd = valor_ars / 368.0  # TC oficial aprox
        filas.append({
            "ticker": t["ticker"],
            "acciones": t["acciones"],
            "precio_ars": t["precio_ars"],
            "valor_ars": valor_ars,
            "valor_usd": valor_usd,
            "sector": t["sector"],
        })
    return pd.DataFrame(filas)


def escenarios_duplicacion(capital_inicial, ret_mensual, max_dd):
    """Calcula meses necesarios para duplicar con diferentes rendimientos."""
    objetivo = capital_inicial * 2
    escenarios = []
    for r in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, ret_mensual]:
        if r <= 0:
            continue
        meses = np.log(objetivo / capital_inicial) / np.log(1 + r)
        ganancia = objetivo - capital_inicial
        # Con drawdown real
        meses_pesimista = np.log(objetivo / capital_inicial) / np.log(1 + r * 0.5)
        escenarios.append({
            "ret_mensual": r,
            "ret_mensual_pct": r * 100,
            "meses": round(meses, 1),
            "años": round(meses / 12, 2),
            "ganancia_usd": round(ganancia, 2),
            "meses_pesimista": round(meses_pesimista, 1),
        })
    return pd.DataFrame(escenarios)


def main():
    print("=" * 95)
    print("ANALISIS DE SHARPE Y DUPLICACION DE CAPITAL — BERTUCCI")
    print("=" * 95)

    # [1] Patrimonio
    print("\n[1/5] PATRIMONIO ACTUAL")
    df_ten = calcular_tenencias_usd()
    total_tenencias_usd = df_ten["valor_usd"].sum()
    total_todos = CASH_USD + CASH_USD_C + total_tenencias_usd
    print("-" * 60)
    print("  Cash USD:          $%12.2f" % CASH_USD)
    print("  Cash USD Cedear:   $%12.2f" % CASH_USD_C)
    print("  Cash ARS:          $%12.2f ARS (~$%.2f USD)" % (CASH_ARS, CASH_ARS / 368))
    print("  Tenencias (USD):   $%12.2f" % total_tenencias_usd)
    print("-" * 60)
    print("  TOTAL PATRIMONIO:  $%12.2f USD" % total_todos)
    print("  TOTAL A DUPLICAR:  $%12.2f USD" % (total_todos * 2))
    print("  GAP A DUPLICAR:    $%12.2f USD" % total_todos)
    print("-" * 60)
    print("\n  Desglose tenencias:")
    print("  %-8s %8s %12s %12s %s" % ("Ticker", "Acc", "Valor ARS", "Valor USD", "Sector"))
    print("  " + "-" * 70)
    for _, r in df_ten.sort_values("valor_usd", ascending=False).iterrows():
        print("  %-8s %8d %12.0f %12.2f %s" % (
            r["ticker"], r["acciones"], r["valor_ars"], r["valor_usd"], r["sector"]))
    print("  " + "-" * 70)
    print("  %-8s %8s %12.0f %12.2f" % ("TOTAL", "", df_ten["valor_ars"].sum(), total_tenencias_usd))

    # [2] Descarga de precios
    print("\n[2/5] Descargando precios para optimizacion (2y)...")
    data = load_many(TICKERS_OPTIMIZAR, period="2y")
    print("  Descargados: %d / %d" % (len(data), len(TICKERS_OPTIMIZAR)))

    # Construir DataFrame de precios
    precios = pd.DataFrame({tk: s for tk, s in data.items() if s is not None and len(s) > 100})
    print("  Activos con datos suficientes: %d" % len(precios.columns))

    # [3] Retornos
    print("\n[3/5] Calculando retornos y correlaciones...")
    retornos = precios.pct_change().dropna()
    retornos_mensuales = precios.resample("ME").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1).dropna()

    # Correlacion promedio
    corr_avg = retornos.corr().values[np.triu_indices_from(retornos.corr().values, 1)].mean()
    print("  Correlacion promedio entre activos: %.3f" % corr_avg)

    # [4] Optimizacion Max Sharpe
    print("\n[4/5] Optimizando Max Sharpe (risk-free = 5.0% anual)...")
    opt = optimizar_max_sharpe(retornos, risk_free_annual=0.05, min_peso=0.0)
    if opt is None:
        print("  ERROR: no se pudo optimizar")
        return

    print("\n  RESULTADOS DEL PORTAFOLIO OPTIMIZADO:")
    print("  " + "=" * 70)
    print("  Retorno anualizado:     %+.2f%%" % (opt["retorno_anual"] * 100))
    print("  Volatilidad anualizada: %.2f%%" % (opt["volatilidad_anual"] * 100))
    print("  Sharpe anual:           %.3f" % opt["sharpe_anual"])
    print("  " + "-" * 70)
    print("  Retorno mensual:        %+.2f%%" % (opt["ret_mensual"] * 100))
    print("  Volatilidad mensual:    %.2f%%" % (opt["vol_mensual"] * 100))
    print("  Sharpe mensual:         %.3f" % opt["sharpe_mensual"])
    print("  Max drawdown mensual:   %.2f%%" % (opt["max_dd_monthly"] * 100))
    print("  " + "=" * 70)

    # Asignacion
    print("\n  ASIGNACION OPTIMA (pesos >= 2%):")
    print("  %-8s %8s %12s" % ("Ticker", "Peso", "Monto USD"))
    print("  " + "-" * 35)
    asignacion = []
    for tk, peso in sorted(zip(opt["tickers"], opt["pesos"]), key=lambda x: -x[1]):
        if peso >= 0.02:
            monto = peso * total_todos
            print("  %-8s %7.1f%% %12.2f" % (tk, peso * 100, monto))
            asignacion.append({"ticker": tk, "peso": peso, "monto_usd": monto})
    print("  " + "-" * 35)
    print("  %-8s %7.1f%%" % ("TOTAL", sum(a["peso"] for a in asignacion) * 100))

    # [5] Escenarios de duplicacion
    print("\n[5/5] ESCENARIOS DE DUPLICACION DE CAPITAL ($%.2f -> $%.2f)" % (
        total_todos, total_todos * 2))
    print("-" * 80)
    df_esc = escenarios_duplicacion(total_todos, opt["ret_mensual"], opt["max_dd_monthly"])
    print("  %-12s %-10s %-10s %-12s %-12s" % (
        "Ret Mensual", "Meses", "Años", "Ganancia", "Pesimista"))
    print("  " + "-" * 70)
    for _, e in df_esc.iterrows():
        marca = " <-- Sharpe optimizado" if abs(e["ret_mensual"] - opt["ret_mensual"]) < 0.001 else ""
        print("  %10.1f%% %8.1f %8.2f $%10.0f %10.1f meses%s" % (
            e["ret_mensual_pct"], e["meses"], e["años"], e["ganancia_usd"],
            e["meses_pesimista"], marca))
    print("  " + "-" * 70)
    print("  Nota: 'Pesimista' = la mitad del rendimiento (50%% de lo esperado)")

    # Resumen final
    print("\n" + "=" * 95)
    print("RESUMEN PARA BERTUCCI")
    print("=" * 95)
    print("  Capital actual:        $%10.2f USD" % total_todos)
    print("  Capital objetivo:      $%10.2f USD (duplicar)" % (total_todos * 2))
    print("  Sharpe anual:          %.3f" % opt["sharpe_anual"])
    print("  Sharpe mensual:        %.3f" % opt["sharpe_mensual"])
    print("  Retorno mensual:       %+.2f%%" % (opt["ret_mensual"] * 100))
    print("  Meses para duplicar:   %.0f meses (~%.1f años)" % (
        np.log(2) / np.log(1 + opt["ret_mensual"]),
        np.log(2) / np.log(1 + opt["ret_mensual"]) / 12))
    print("  Ganancia necesaria:    $%10.2f USD" % total_todos)
    print("")
    print("  Cash disponible:       $%10.2f USD (%.1f%% del total)" % (CASH_USD, CASH_USD / total_todos * 100))
    print("  Para invertir:         $%10.2f USD" % CASH_USD)
    print("")
    print("  CONTEXTO: Fase 2 (Mid Expansion)")
    print("  Sectores favorables: XLI, XLB, XLF, XLE")
    print("  Tech (XLK): no lidera pero no se vende activamente")
    print("=" * 95)


if __name__ == "__main__":
    main()
