# -*- coding: utf-8 -*-
"""Backtest walk-forward del constructor de portafolio.

Optimiza en una ventana de entrenamiento y evalúa en el periodo siguiente,
comparando contra un benchmark. Reutiliza la lógica de Markowitz del constructor.

Uso:
    python -m analisis.portafolio.backtest_constructor --out BACKTEST_CONSTRUCTOR.md
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.portafolio.constructor import (
    ETF_A_SECTOR,
    cargar_unificado,
    extraer_candidatos,
    sectores_beneficiados,
)
from analisis.portafolio.visualizaciones import (
    plot_cumulative_and_drawdown,
    plot_efficient_frontier,
    plot_weights,
)


def descargar_precios(tickers, start, end, min_dias=30):
    """Descarga precios de cierre para un rango de fechas, ticker por ticker."""
    if not tickers:
        return pd.DataFrame()
    prices = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(start=start, end=end)
            if not hist.empty and len(hist["Close"].dropna()) >= min_dias:
                prices[t] = hist["Close"].dropna()
        except Exception:
            pass
    return pd.DataFrame(prices)


def optimizar_max_sharpe(returns_df, risk_free_annual=0.04):
    """Optimización Markowitz long-only max Sharpe."""
    if returns_df.empty:
        return None
    # eliminar tickers con muchos NaN
    min_obs = int(len(returns_df) * 0.9)
    returns_df = returns_df.dropna(axis=1, thresh=min_obs).fillna(0)
    if returns_df.shape[1] < 2 or len(returns_df) < 30:
        return None
    mu = returns_df.mean() * 252
    sigma = returns_df.cov() * 252
    n = len(mu)

    def neg_sharpe(w):
        rp = np.dot(w, mu.values)
        vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
        return -(rp - risk_free_annual) / vp if vp > 0 else 0

    x0 = np.array([1 / n] * n)
    bounds = [(0, 1)] * n
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    opt = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 1000})
    if not opt.success:
        return None
    w = opt.x / opt.x.sum()
    return dict(zip(returns_df.columns, w))


def backtest_portafolio(tickers, start_train, end_train, start_test, end_test,
                        benchmark_ticker="SPY", risk_free=0.04, verbose=False):
    """Backtest walk-forward: optimiza en train, aplica en test."""
    prices_train = descargar_precios(tickers, start_train, end_train)
    prices_test = descargar_precios(tickers, start_test, end_test)

    if prices_train.empty or prices_test.empty or len(prices_train.columns) < 2:
        return None

    rets_train = prices_train.pct_change().dropna()
    rets_test = prices_test.pct_change().dropna()

    pesos = optimizar_max_sharpe(rets_train, risk_free_annual=risk_free)
    if not pesos:
        return None

    # filtrar solo activos con peso > 0.5%
    pesos = {t: w for t, w in pesos.items() if w > 0.005}
    total = sum(pesos.values())
    pesos = {t: w / total for t, w in pesos.items()}

    # retornos del portafolio
    common = [t for t in pesos if t in rets_test.columns]
    if not common:
        return None
    w_array = np.array([pesos[t] for t in common])
    pf_rets = rets_test[common].dot(w_array)

    # benchmark
    bm_prices = descargar_precios([benchmark_ticker], start_test, end_test)
    if not bm_prices.empty and benchmark_ticker in bm_prices.columns:
        bm_rets = bm_prices[benchmark_ticker].pct_change().dropna()
    else:
        # fallback: igual ponderado de los candidatos en test
        bm_rets = rets_test.mean(axis=1)

    # alinear
    idx = pf_rets.index.intersection(bm_rets.index)
    pf_rets = pf_rets.loc[idx]
    bm_rets = bm_rets.loc[idx]

    # métricas
    pf_cum = (1 + pf_rets).cumprod()
    bm_cum = (1 + bm_rets).cumprod()

    ret_total = pf_cum.iloc[-1] - 1
    vol_ann = pf_rets.std() * np.sqrt(252)
    years = len(pf_rets) / 252
    sharpe = ((ret_total / years) - risk_free) / vol_ann if vol_ann > 0 else 0

    cum_max = pf_cum.cummax()
    max_dd = ((pf_cum - cum_max) / cum_max).min()

    bm_ret = bm_cum.iloc[-1] - 1

    return {
        "pesos": pesos,
        "ret_total": ret_total,
        "vol_ann": vol_ann,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "bm_ret": bm_ret,
        "diferencia": ret_total - bm_ret,
        "n_dias": len(pf_rets),
        "pf_rets": pf_rets,
        "bm_rets": bm_rets,
        "benchmark": benchmark_ticker if not bm_prices.empty else "igual_ponderado",
    }


def _limitar_candidatos(candidatos, max_cands):
    """Limita candidatos distribuyendo cupo por sector."""
    por_sector = {}
    for c in candidatos:
        por_sector.setdefault(c.get("sector_json", "Otros"), []).append(c)
    n_sec = len(por_sector)
    lim = max(1, max_cands // n_sec) if n_sec else max_cands
    seleccionados = []
    for sec, lst in por_sector.items():
        seleccionados.extend(lst[:lim])
    return seleccionados


def _render_resultado(result, label, bm_label):
    lines = []
    if result is None:
        lines.append("*No fue posible realizar el backtest %s por falta de datos suficientes.*" % label)
        return lines
    lines.append("## Resultados %s (out-of-sample)" % label)
    lines.append("| Métrica | Portafolio | %s |" % bm_label)
    lines.append("|---|---|---|")
    lines.append("| Retorno total | %.2f%% | %.2f%% |" % (result["ret_total"] * 100, result["bm_ret"] * 100))
    lines.append("| Volatilidad anualizada | %.2f%% | — |" % (result["vol_ann"] * 100))
    lines.append("| Sharpe | %.3f | — |" % result["sharpe"])
    lines.append("| Max Drawdown | %.2f%% | — |" % (result["max_dd"] * 100))
    lines.append("| Diferencia vs benchmark | %.2f%% | — |" % (result["diferencia"] * 100))
    lines.append("| Días evaluados | %d | %d |" % (result["n_dias"], result["n_dias"]))
    lines.append("")
    lines.append("## Pesos óptimos %s" % label)
    pesos_df = pd.DataFrame(sorted(result["pesos"].items(), key=lambda x: -x[1]),
                            columns=["ticker", "peso"])
    pesos_df["peso_pct"] = pesos_df["peso"] * 100
    lines.append(pesos_df[["ticker", "peso_pct"]].to_markdown(index=False))
    lines.append("")
    if result["ret_total"] > result["bm_ret"]:
        lines.append("**Conclusión:** el portafolio optimizado superó al benchmark %s en el periodo forward." % bm_label)
    else:
        lines.append("**Conclusión:** el portafolio optimizado NO superó al benchmark %s en el periodo forward." % bm_label)
    lines.append("")
    return lines


def generar_backtest(contexto, unificado_path, out_path, train_months=12, test_months=3,
                     max_cands=60, charts_dir="charts", no_charts=False, verbose=False):
    end_date = datetime.now()
    start_test = (end_date - pd.DateOffset(months=test_months)).strftime("%Y-%m-%d")
    end_train = start_test
    start_train = (pd.to_datetime(end_train) - pd.DateOffset(months=train_months)).strftime("%Y-%m-%d")

    sectores = sectores_beneficiados(contexto, top_n=3)
    unificado = cargar_unificado(unificado_path)
    candidatos = extraer_candidatos(unificado, sectores)

    # candidatos ARS y USD
    ars_cands = []
    usd_cands = []
    for sector, buckets in candidatos.items():
        for c in buckets["ars"]:
            ars_cands.append(c)
        for c in buckets["usd"]:
            usd_cands.append(c)

    ars_cands = _limitar_candidatos(ars_cands, max_cands)
    usd_cands = _limitar_candidatos(usd_cands, max_cands)

    tickers_ars = [c["ticker_ars"] for c in ars_cands]
    tickers_usd = [c["ticker_usd"] for c in usd_cands]

    if verbose:
        print("Backtest train: %s -> %s | test: %s -> %s" % (start_train, end_train, start_test, end_date.strftime("%Y-%m-%d")))
        print("Candidatos ARS:", len(tickers_ars))
        print("Candidatos USD:", len(tickers_usd))

    res_usd = backtest_portafolio(tickers_usd, start_train, end_train,
                                  start_test, end_date.strftime("%Y-%m-%d"),
                                  benchmark_ticker="SPY", verbose=verbose)
    res_ars = backtest_portafolio(tickers_ars, start_train, end_train,
                                  start_test, end_date.strftime("%Y-%m-%d"),
                                  benchmark_ticker="GGAL.BA", verbose=verbose)

    os.makedirs(charts_dir, exist_ok=True)
    if not no_charts:
        # descargar precios train para graficar frontera
        try:
            prices_train_usd = descargar_precios(tickers_usd, start_train, end_train)
            rets_train_usd = prices_train_usd.pct_change().dropna()
            plot_efficient_frontier(rets_train_usd, res_usd["pesos"] if res_usd else None,
                                    os.path.join(charts_dir, "frontier_usd.png"))
        except Exception as e:
            if verbose:
                print("  No se pudo graficar frontera USD:", e)
        try:
            prices_train_ars = descargar_precios(tickers_ars, start_train, end_train)
            rets_train_ars = prices_train_ars.pct_change().dropna()
            plot_efficient_frontier(rets_train_ars, res_ars["pesos"] if res_ars else None,
                                    os.path.join(charts_dir, "frontier_ars.png"))
        except Exception as e:
            if verbose:
                print("  No se pudo graficar frontera ARS:", e)
        if res_usd:
            try:
                plot_weights(res_usd["pesos"], os.path.join(charts_dir, "weights_usd.png"),
                             titulo="Pesos óptimos USD")
                plot_cumulative_and_drawdown(res_usd["pf_rets"], res_usd["bm_rets"],
                                             os.path.join(charts_dir, "backtest_usd.png"),
                                             label_pf="Portafolio USD", label_bm="SPY")
            except Exception as e:
                if verbose:
                    print("  No se pudo graficar backtest USD:", e)
        if res_ars:
            try:
                plot_weights(res_ars["pesos"], os.path.join(charts_dir, "weights_ars.png"),
                             titulo="Pesos óptimos ARS")
                plot_cumulative_and_drawdown(res_ars["pf_rets"], res_ars["bm_rets"],
                                             os.path.join(charts_dir, "backtest_ars.png"),
                                             label_pf="Portafolio ARS", label_bm=res_ars["benchmark"])
            except Exception as e:
                if verbose:
                    print("  No se pudo graficar backtest ARS:", e)

    md = []
    md.append("# Backtest Walk-Forward del Constructor")
    md.append("**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d"))
    md.append("")
    md.append("- **Ventana de entrenamiento:** %s a %s" % (start_train, end_train))
    md.append("- **Ventana de test (forward):** %s a %s" % (start_test, end_date.strftime("%Y-%m-%d")))
    md.append("- **Sectores beneficiados:** %s" % ", ".join(sectores))
    md.append("")

    md.extend(_render_resultado(res_usd, "USD", "SPY"))
    md.append("")
    bm_ars = res_ars["benchmark"] if res_ars else "GGAL.BA"
    md.extend(_render_resultado(res_ars, "ARS", bm_ars))

    if not no_charts and os.path.isdir(charts_dir) and any(f.endswith(".png") for f in os.listdir(charts_dir)):
        md.append("## Visualizaciones")
        md.append("Los gráficos se guardaron en `%s/`" % charts_dir)
        for f in sorted(os.listdir(charts_dir)):
            if f.endswith(".png"):
                md.append("- ![%s](%s)" % (f, os.path.join(charts_dir, f).replace("\\", "/")))
        md.append("")

    md.append("> Nota: este backtest usa los pesos calculados en entrenamiento y los mantiene fijos en test. No incluye rebalanceo, comisiones ni slippage.")

    texto = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(texto)
    if verbose:
        print("Guardado en %s" % out_path)
    return {"usd": res_usd, "ars": res_ars}, texto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contexto", default="contexto_murphy_2026-08-13.json")
    parser.add_argument("--unificado", default="unificado_completo - copia.json")
    parser.add_argument("--out", default="BACKTEST_CONSTRUCTOR.md")
    parser.add_argument("--max-cands", type=int, default=60)
    parser.add_argument("--charts-dir", default="charts")
    parser.add_argument("--no-charts", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    ctx = None
    if args.contexto and os.path.exists(args.contexto):
        with open(args.contexto, encoding="utf-8") as f:
            ctx = json.load(f)
    if ctx is None:
        from analisis.ejecutivo.diario import MurphyDaily
        daily = MurphyDaily(periodo="6y", verbose=args.verbose)
        ctx = daily.run(nombres=["12", "13"])

    generar_backtest(ctx, args.unificado, args.out, max_cands=args.max_cands,
                     charts_dir=args.charts_dir, no_charts=args.no_charts, verbose=args.verbose)


if __name__ == "__main__":
    main()
