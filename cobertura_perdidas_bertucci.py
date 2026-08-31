# -*- coding: utf-8 -*-
"""Optimizacion long-only para cubrir posiciones perdedoras — Bertucci."""
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
# PORTAFOLIO ACTUAL BERTUCCI (snapshot 28/ago/2026)
# ============================================================
TENENCIAS = [
    {"ticker": "PAMP", "cant": 74, "precio_ars": 5215.0, "gan_usd": -9.49, "pct": -3.65, "sector": "Energia"},
    {"ticker": "AAPL", "cant": 2, "precio_ars": 25640.0, "gan_usd": 0, "pct": 0, "sector": "Tecnologia"},
    {"ticker": "ADBE", "cant": 4, "precio_ars": 10670.0, "gan_usd": 0, "pct": 0, "sector": "Software"},
    {"ticker": "AMZN", "cant": 109, "precio_ars": 2950.0, "gan_usd": 12.37, "pct": 6.29, "sector": "Discrecional"},
    {"ticker": "GOOGL", "cant": 61, "precio_ars": 9640.0, "gan_usd": -9.82, "pct": -2.51, "sector": "Comunicacion"},
    {"ticker": "IBM", "cant": 4, "precio_ars": 25420.0, "gan_usd": 0.33, "pct": 0.50, "sector": "Tecnologia"},
    {"ticker": "MU", "cant": 1, "precio_ars": 300550.0, "gan_usd": -7.58, "pct": -3.74, "sector": "Semiconductores"},
    {"ticker": "NU", "cant": 16, "precio_ars": 11510.0, "gan_usd": -9.15, "pct": -7.10, "sector": "Financieras"},
    {"ticker": "NVDA", "cant": 52, "precio_ars": 15080.0, "gan_usd": 46.53, "pct": 10.05, "sector": "Semiconductores"},
    {"ticker": "SMH", "cant": 2, "precio_ars": 18200.0, "gan_usd": -1.30, "pct": -5.22, "sector": "Semiconductores"},
    {"ticker": "SPY", "cant": 331, "precio_ars": 20730.0, "gan_usd": 76.86, "pct": 1.75, "sector": "Benchmark"},
    {"ticker": "TSM", "cant": 1, "precio_ars": 76050.0, "gan_usd": -0.06, "pct": -0.12, "sector": "Semiconductores"},
    {"ticker": "URA", "cant": 3, "precio_ars": 14970.0, "gan_usd": 3.15, "pct": 12.10, "sector": "Energia"},
    {"ticker": "XLE", "cant": 6, "precio_ars": 49940.0, "gan_usd": -1.56, "pct": -0.80, "sector": "Energia"},
]

CASH_USD = 10011.57
CASH_ARS = 503320.88
TC = 368.0  # tipo de cambio oficial aprox

# Tickers para optimizar
TICKERS_OPTIMIZAR = [
    "SPY", "QQQ", "IWM", "XLK", "XLE", "XLI", "XLF", "XLY", "XLP", "XLV",
    "XLC", "XLB", "XLU", "XLRE", "GLD", "TLT", "VTV", "VUG",
    "AMZN", "NVDA", "AAPL", "MSFT", "GOOGL", "META", "TSLA",
    "LMT", "CVS", "PEP", "PFE", "ADBE", "MU", "NVDA", "SMH",
]


def analizar_perdedoras():
    """Identifica posiciones perdedoras y calcula el gap."""
    perdedoras = []
    ganadoras = []
    for t in TENENCIAS:
        valor_ars = t["cant"] * t["precio_ars"]
        valor_usd = valor_ars / TC
        t["valor_ars"] = valor_ars
        t["valor_usd"] = valor_usd
        if t["gan_usd"] < 0:
            perdedoras.append(t)
        elif t["gan_usd"] > 0:
            ganadoras.append(t)

    total_perdida = sum(t["gan_usd"] for t in perdedoras)
    total_ganancia = sum(t["gan_usd"] for t in ganadoras)
    neto = total_ganancia + total_perdida

    return perdedoras, ganadoras, total_perdida, total_ganancia, neto


def optimizar_cobertura(retornos_df, cash_usd, gap_perdida, risk_free=0.05):
    """Optimiza un portafolio long-only para maximizar Sharpe con restriccion de retorno minimo.

    La restriccion: el retorno mensual del portafolio nuevo debe cubrir la perdida
    existente en un plazo razonable.
    """
    retornos_df = retornos_df.dropna(how="any", axis=1).dropna(how="any", axis=0)
    if retornos_df.shape[1] < 2 or len(retornos_df) < 60:
        return None

    mu = retornos_df.mean() * 252
    sigma = retornos_df.cov() * 252
    n = len(mu)

    # Retorno minimo necesario para cubrir gap en 12 meses
    ret_anual_necesario = abs(gap_perdida) / cash_usd if cash_usd > 0 else 0.30

    def neg_sharpe(w):
        rp = np.dot(w, mu.values)
        vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
        return -(rp - risk_free) / vp if vp > 0 else 0

    x0 = np.array([1 / n] * n)
    bounds = [(0, 1)] * n
    constraints = [
        {"type": "eq", "fun": lambda x: np.sum(x) - 1},
        {"type": "ineq", "fun": lambda x: np.dot(x, mu.values) - ret_anual_necesario},
    ]
    opt = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 2000})
    if not opt.success:
        # Fallback sin restriccion de retorno minimo
        opt = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds,
                       constraints=[{"type": "eq", "fun": lambda x: np.sum(x) - 1}],
                       options={"maxiter": 2000})
        if not opt.success:
            return None

    w = opt.x / opt.x.sum()
    rp = np.dot(w, mu.values)
    vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
    sharpe = (rp - risk_free) / vp

    # Metricas mensuales
    returns_monthly = retornos_df.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    port_monthly = (returns_monthly * w).sum(axis=1)
    ret_mensual = port_monthly.mean()
    vol_mensual = port_monthly.std()
    sharpe_mensual = ret_mensual / vol_mensual * np.sqrt(12) if vol_mensual > 0 else 0
    max_dd = (port_monthly.cumsum() - port_monthly.cumsum().cummax()).min()

    return {
        "tickers": list(retornos_df.columns),
        "pesos": w,
        "retorno_anual": rp,
        "volatilidad_anual": vp,
        "sharpe_anual": sharpe,
        "ret_mensual": ret_mensual,
        "vol_mensual": vol_mensual,
        "sharpe_mensual": sharpe_mensual,
        "max_dd_monthly": max_dd,
        "returns_monthly": port_monthly,
    }


def main():
    print("=" * 95)
    print("OPTIMIZACION LONG-ONLY PARA CUBRIR POSICIONES PERDEDRAS — BERTUCCI")
    print("=" * 95)

    # [1] Analisis de perdedoras
    print("\n[1/4] ANALISIS DE POSICIONES PERDEDRAS")
    print("-" * 90)
    perdedoras, ganadoras, total_perdida, total_ganancia, neto = analizar_perdedoras()

    print("\n  POSICIONES PERDEDRAS:")
    print("  %-8s %6s %12s %12s %8s %s" % ("Ticker", "Cant", "Inv USD", "Perdida USD", "Pct", "Sector"))
    print("  " + "-" * 80)
    for t in sorted(perdedoras, key=lambda x: x["gan_usd"]):
        print("  %-8s %6d %12.2f %12.2f %+7.2f%% %s" % (
            t["ticker"], t["cant"], t["valor_usd"], t["gan_usd"], t["pct"], t["sector"]))
    print("  " + "-" * 80)
    print("  %-8s %6s %12s %12.2f" % ("TOTAL", "", "", total_perdida))

    print("\n  POSICIONES GANADORAS:")
    print("  %-8s %6s %12s %12s %8s %s" % ("Ticker", "Cant", "Inv USD", "Ganancia USD", "Pct", "Sector"))
    print("  " + "-" * 80)
    for t in sorted(ganadoras, key=lambda x: -x["gan_usd"]):
        print("  %-8s %6d %12.2f %+12.2f %+7.2f%% %s" % (
            t["ticker"], t["cant"], t["valor_usd"], t["gan_usd"], t["pct"], t["sector"]))
    print("  " + "-" * 80)
    print("  %-8s %6s %12s %+12.2f" % ("TOTAL", "", "", total_ganancia))

    print("\n  RESUMEN PORTAFOLIO:")
    print("    Total ganadoras:  %+12.2f USD" % total_ganancia)
    print("    Total perdedoras: %+12.2f USD" % total_perdida)
    print("    NETO:             %+12.2f USD" % neto)
    print("    Cash disponible:  %12.2f USD" % CASH_USD)
    print("    Gap a cubrir:     %12.2f USD (perdida total)" % abs(total_perdida))

    # [2] Cuanto necesito ganar
    print("\n[2/4] CUANTO NECESITO GANAR PARA CUBRIR")
    print("-" * 90)
    meses_objetivo = [3, 6, 9, 12]
    print("  Para cubrir $%.2f de perdidas con $%.2f de cash:" % (abs(total_perdida), CASH_USD))
    print("  %-12s %-15s %-15s %-15s" % ("Plazo", "Ret Mensual", "Ret Anual", "Sharpe Req"))
    print("  " + "-" * 60)
    for m in meses_objetivo:
        # (1+r)^m = 1 + gap/cash => r = (1 + gap/cash)^(1/m) - 1
        ret_total = abs(total_perdida) / CASH_USD
        r_mensual = (1 + ret_total) ** (1 / m) - 1
        r_anual = (1 + r_mensual) ** 12 - 1
        # Sharpe minimo asumiendo vol 15%
        sharpe_req = r_anual / 0.15
        print("  %10d M %14.2f%% %14.2f%% %14.2f" % (m, r_mensual * 100, r_anual * 100, sharpe_req))
    print("  " + "-" * 60)

    # [3] Descarga y optimizacion
    print("\n[3/4] DESCARGANDO PRECIOS Y OPTIMIZANDO (2y)...")
    data = load_many(TICKERS_OPTIMIZAR, period="2y")
    print("  Descargados: %d / %d" % (len(data), len(TICKERS_OPTIMIZAR)))

    precios = pd.DataFrame({tk: s for tk, s in data.items() if s is not None and len(s) > 100})
    retornos = precios.pct_change().dropna()
    print("  Activos para optimizar: %d" % len(precios.columns))

    print("\n  Optimizando Max Sharpe con restriccion de retorno minimo...")
    opt = optimizar_cobertura(retornos, CASH_USD, total_perdida, risk_free=0.05)
    if opt is None:
        print("  ERROR: no se pudo optimizar")
        return

    print("\n  RESULTADOS DEL PORTAFOLIO OPTIMIZADO:")
    print("  " + "=" * 70)
    print("  Retorno anualizado:     %+.2f%%" % (opt["retorno_anual"] * 100))
    print("  Volatilidad anualizada: %.2f%%" % (opt["volatilidad_anual"] * 100))
    print("  Sharpe anual:           %.3f" % opt["sharpe_anual"])
    print("  Retorno mensual:        %+.2f%%" % (opt["ret_mensual"] * 100))
    print("  Volatilidad mensual:    %.2f%%" % (opt["vol_mensual"] * 100))
    print("  Sharpe mensual:         %.3f" % opt["sharpe_mensual"])
    print("  Max DD mensual:         %.2f%%" % (opt["max_dd_monthly"] * 100))
    print("  " + "=" * 70)

    # [4] Asignacion concreta
    print("\n[4/4] ASIGNACION CONCRETA CON $%.2f USD" % CASH_USD)
    print("-" * 75)
    print("  %-8s %8s %12s %12s %s" % ("Ticker", "Peso", "Monto USD", "Monto ARS", "Accion"))
    print("  " + "-" * 75)

    compras = []
    for tk, peso in sorted(zip(opt["tickers"], opt["pesos"]), key=lambda x: -x[1]):
        if peso >= 0.01:
            monto_usd = peso * CASH_USD
            monto_ars = monto_usd * TC
            accion = "COMPRAR" if monto_usd >= 50 else "Posicion chica"
            compras.append({"ticker": tk, "peso": peso, "monto_usd": monto_usd, "monto_ars": monto_ars})
            print("  %-8s %7.1f%% %12.2f %12.0f  %s" % (tk, peso * 100, monto_usd, monto_ars, accion))

    print("  " + "-" * 75)
    print("  %-8s %7.1f%% %12.2f" % ("TOTAL", 100.0, CASH_USD))

    # Cubrimiento de perdidas
    meses_cubrimiento = np.log(1 + abs(total_perdida) / CASH_USD) / np.log(1 + opt["ret_mensual"]) if opt["ret_mensual"] > 0 else 999
    ganancia_mensual = CASH_USD * opt["ret_mensual"]

    print("\n" + "=" * 95)
    print("COBERTURA DE PERDIDAS")
    print("=" * 95)
    print("  Perdida a cubrir:      $%10.2f USD" % abs(total_perdida))
    print("  Cash invertido:        $%10.2f USD" % CASH_USD)
    print("  Retorno mensual:       %+.2f%%" % (opt["ret_mensual"] * 100))
    print("  Ganancia mensual:      $%10.2f USD" % ganancia_mensual)
    print("  Meses para cubrir:     %.0f meses (~%.1f años)" % (meses_cubrimiento, meses_cubrimiento / 12))
    print("")
    print("  Escenarios de cobertura:")
    print("  %-12s %-15s %-15s" % ("Meses", "GanAcum USD", "vs Perdida"))
    print("  " + "-" * 45)
    for m in [1, 3, 6, 9, 12, 18, 24]:
        gan_acum = CASH_USD * ((1 + opt["ret_mensual"]) ** m - 1)
        pct_cobertura = gan_acum / abs(total_perdida) * 100
        marca = " <-- CUBIERTA" if pct_cobertura >= 100 else ""
        print("  %10d M  %12.2f  %+10.1f%%%s" % (m, gan_acum, pct_cobertura, marca))
    print("  " + "-" * 45)

    # Posiciones sugeridas a mantener/vender
    print("\n" + "=" * 95)
    print("RECOMENDACIONES SOBRE POSICIONES EXISTENTES")
    print("=" * 95)
    print("  MANTENER (ganadoras con momentum):")
    for t in ganadoras:
        if t["pct"] > 2:
            print("    %-6s %+7.2f%% — mantener, tiene viento a favor" % (t["ticker"], t["pct"]))
    print("")
    print("  MONITOREAR (perdedoras leves, <3%):")
    for t in perdedoras:
        if abs(t["pct"]) < 3:
            print("    %-6s %+7.2f%% — no vender, esperar recovery" % (t["ticker"], t["pct"]))
    print("")
    print("  CUIDADO (perdedoras fuertes, >5%):")
    for t in perdedoras:
        if abs(t["pct"]) >= 5:
            print("    %-6s %+7.2f%% — evaluar si la tesis se rompio" % (t["ticker"], t["pct"]))
    print("=" * 95)


if __name__ == "__main__":
    main()
