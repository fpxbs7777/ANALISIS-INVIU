# -*- coding: utf-8 -*-
"""Constructor de portafolio por sector beneficiado (Murphy + fundamentos + técnico + Markowitz).

Combina:
- Contexto Murphy (sectores líderes) para elegir sectores.
- `unificado_completo - copia.json` para descubrir tickers de esos sectores/industrias.
- Descarga de precios vía yfinance.
- Métricas cuantitativas (rendimiento esperado, volatilidad, Sharpe, VaR, skew, kurtosis).
- Fundamentos básicos (P/E, P/B, ROE, crecimiento, upside de analistas).
- Optimización Markowitz max-Sharpe long-only.
- Salida: DataFrame y Markdown con asignación sugerida para el saldo disponible en ARS y USD.

Uso:
    python -m analisis.portafolio.constructor --portafolio portafolios_inviu.json --out sugerencias.md

El script necesita:
    - unificado_completo - copia.json  (mapeo sectores/industrias/tickers)
    - contexto_murphy_YYYY-MM-DD.json (opcional, se regenera si falta cap12/cap13)
"""
import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.portafolio.noticias import agregar_score_noticias, analizar_noticias


# Mapeo ETF Murphy -> sector en el JSON unificado
ETF_A_SECTOR = {
    "XLE": "Energía",
    "XLK": "Tecnología",
    "XLI": "Acciones Industriales",
    "XLP": "Defensiva del Consumidor",
    "XLF": "Servicios Financieros",
    "XLY": "Consumo Cíclico",
    "XLV": "Cuidado de la Salud",
    "XLC": "Servicios de Comunicación",
    "XLB": "Materiales Básicos",
    "XLRE": "Bienes Raíces",
    "XLU": "Utilidades",
}

SECTOR_A_ETF = {v: k for k, v in ETF_A_SECTOR.items()}

# Módulos de fundamentos que pedimos a yfinance
FUNDAMENTOS_KEYS = [
    "sector", "industry", "trailingPE", "forwardPE", "priceToBook",
    "returnOnEquity", "revenueGrowth", "earningsGrowth", "debtToEquity",
    "freeCashflow", "marketCap", "recommendationMean", "numberOfAnalystOpinions",
    "targetMeanPrice", "currentPrice",
]


def cargar_unificado(path="unificado_completo - copia.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sectores_beneficiados(contexto, top_n=3):
    """Devuelve lista de nombres de sectores del JSON que lideran según Murphy."""
    cap13 = contexto.get("cap13", {}).get("resultados", {})
    ranking = cap13.get("liderazgo_sectorial_200d", {})
    lideres = list(ranking.keys())[:top_n]
    return [ETF_A_SECTOR.get(etf) for etf in lideres if ETF_A_SECTOR.get(etf)]


def extraer_candidatos(unificado, sectores_nombres):
    """Extrae candidatos ARS y USD del JSON para los sectores dados.

    Devuelve dict: {sector: {'ars': [...], 'usd': [...]}}
    Cada candidato es un dict con ticker, tipo, moneda, pais, nombre, y sus
    tickers normalizados para yfinance (ticker_ars, ticker_usd).
    """
    out = {}
    for sector in sectores_nombres:
        data = unificado.get("sectores", {}).get(sector, {})
        ars, usd = [], []
        seen_ars = set()
        seen_usd = set()
        for industria, activos in data.get("industrias", {}).items():
            for activo in activos:
                if not isinstance(activo, dict) or "ticker" not in activo:
                    continue
                ticker = activo["ticker"]
                tipo = (activo.get("tipo") or "").lower()
                moneda = (activo.get("moneda") or "").upper()
                pais = activo.get("pais", "")
                nombre = activo.get("nombre", "")

                # ignorar ETFs y renta fija
                if tipo == "etf" or sector == "Renta Fija":
                    continue

                # ticker ARS: si termina en .BA lo usamos, sino lo agregamos
                ticker_ars = ticker if ticker.endswith(".BA") else ticker + ".BA"
                # ticker USD: removemos .BA o sufijo D de cedear dolarizado
                ticker_usd = ticker
                if ticker_usd.endswith(".BA"):
                    ticker_usd = ticker_usd[:-3]
                elif moneda == "USD" and tipo == "cedear" and ticker_usd.endswith("D"):
                    ticker_usd = ticker_usd[:-1]

                item = {
                    "ticker_original": ticker,
                    "tipo": tipo,
                    "moneda": moneda,
                    "pais": pais,
                    "nombre": nombre,
                    "sector_json": sector,
                    "industria": industria,
                    "ticker_ars": ticker_ars,
                    "ticker_usd": ticker_usd,
                }

                if moneda == "ARS" or ticker.endswith(".BA"):
                    if ticker_ars not in seen_ars:
                        seen_ars.add(ticker_ars)
                        ars.append(item)
                elif moneda == "USD":
                    if ticker_usd not in seen_usd:
                        seen_usd.add(ticker_usd)
                        usd.append(item)
        out[sector] = {"ars": ars, "usd": usd}
    return out


def descargar_precios(tickers, period="1y", verbose=False):
    """Descarga precios de cierre para una lista de tickers. Devuelve dict {ticker: Series}."""
    if not tickers:
        return {}
    prices = {}
    try:
        # descarga batch; yfinance acepta espacio separado por comas
        data = yf.download(" ".join(tickers), period=period, progress=False, threads=True, group_by="ticker")
        if data.empty:
            return prices
        if len(tickers) == 1:
            data = {tickers[0]: data}
        for t in tickers:
            try:
                if len(tickers) == 1:
                    df = data[tickers[0]]
                else:
                    df = data[t]
                if "Close" in df.columns and not df["Close"].dropna().empty and len(df["Close"].dropna()) > 30:
                    prices[t] = df["Close"].dropna()
                    if verbose:
                        print("  OK %s (%d dias)" % (t, len(prices[t])))
                else:
                    if verbose:
                        print("  SIN DATOS %s" % t)
            except Exception as e:
                if verbose:
                    print("  ERROR %s: %s" % (t, e))
    except Exception as e:
        if verbose:
            print("  ERROR batch download: %s" % e)
        # fallback individual
        for t in tickers:
            try:
                hist = yf.Ticker(t).history(period=period)
                if not hist.empty and len(hist) > 30:
                    prices[t] = hist["Close"].dropna()
            except Exception:
                pass
    return prices


def descargar_ohlcv(tickers, period="1y", verbose=False):
    """Descarga OHLCV para una lista de tickers. Devuelve dict {ticker: DataFrame}."""
    if not tickers:
        return {}
    data = {}
    try:
        batch = yf.download(" ".join(tickers), period=period, progress=False, threads=True, group_by="ticker")
        if batch.empty:
            return data
        if len(tickers) == 1:
            batch = {tickers[0]: batch}
        for t in tickers:
            try:
                df = batch[t] if len(tickers) > 1 else batch[tickers[0]]
                if not df.empty and "Close" in df.columns and "Volume" in df.columns:
                    data[t] = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception as e:
                if verbose:
                    print("  ERROR OHLCV %s: %s" % (t, e))
    except Exception as e:
        if verbose:
            print("  ERROR batch OHLCV: %s" % e)
        for t in tickers:
            try:
                hist = yf.Ticker(t).history(period=period)
                if not hist.empty and "Close" in hist.columns and "Volume" in hist.columns:
                    data[t] = hist[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception:
                pass
    return data


def liquidez(ticker, moneda, min_dias=15, period="3mo"):
    """Devuelve dict con métricas de liquidez o None si no hay datos."""
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty or len(hist) < min_dias:
            return None
        hist = hist.dropna()
        if len(hist) < min_dias:
            return None
        avg_price = hist["Close"].mean()
        avg_volume = hist["Volume"].mean()
        med_volume = hist["Volume"].median()
        monto_diario = (hist["Close"] * hist["Volume"]).mean()
        return {
            "ticker": ticker,
            "moneda": moneda,
            "dias": len(hist),
            "precio_promedio": avg_price,
            "volumen_medio": avg_volume,
            "volumen_mediana": med_volume,
            "monto_diario_medio": monto_diario,
        }
    except Exception:
        return None


def filtrar_por_liquidez(candidatos, moneda_label, min_monto_usd=5_000_000, min_monto_ars=1_000_000,
                         min_precio_usd=5.0, min_precio_ars=100.0, verbose=False):
    """Filtra candidatos por liquidez y precio mínimo usando descarga batch."""
    tickers = [c["ticker_ars"] if moneda_label == "ARS" else c["ticker_usd"] for c in candidatos]
    ohlcv = descargar_ohlcv(tickers, period="3mo", verbose=verbose)

    filtrados = []
    rechazados = []
    for c in candidatos:
        tk = c["ticker_ars"] if moneda_label == "ARS" else c["ticker_usd"]
        df = ohlcv.get(tk)
        if df is None or df.empty or len(df) < 15:
            rechazados.append({"ticker": tk, "motivo": "sin_datos"})
            continue
        avg_price = df["Close"].mean()
        monto_diario = (df["Close"] * df["Volume"]).mean()
        c["liq_precio_promedio"] = avg_price
        c["liq_volumen_medio"] = df["Volume"].mean()
        c["liq_monto_diario_medio"] = monto_diario
        c["liq_dias"] = len(df)

        if moneda_label == "USD":
            if monto_diario < min_monto_usd or avg_price < min_precio_usd:
                rechazados.append({
                    "ticker": tk,
                    "motivo": "liquidez_usd",
                    "monto_diario": monto_diario,
                    "precio": avg_price,
                })
                continue
        else:
            if monto_diario < min_monto_ars or avg_price < min_precio_ars:
                rechazados.append({
                    "ticker": tk,
                    "motivo": "liquidez_ars",
                    "monto_diario": monto_diario,
                    "precio": avg_price,
                })
                continue
        filtrados.append(c)
    if verbose:
        print("  Liquidez %s: %d aceptados, %d rechazados" % (moneda_label, len(filtrados), len(rechazados)))
        if rechazados:
            for r in rechazados[:10]:
                print("    - %s: %s" % (r["ticker"], r["motivo"]))
    return filtrados, rechazados


def metricas_riesgo_retorno(serie, risk_free_annual=0.04, factor=252):
    """Calcula métricas cuantitativas de una serie de precios."""
    if serie is None or len(serie) < 30:
        return None
    rets = serie.pct_change().dropna()
    if len(rets) < 20:
        return None
    mean = rets.mean() * factor
    vol = rets.std() * np.sqrt(factor)
    sharpe = (mean - risk_free_annual) / vol if vol > 0 else np.nan
    var_95 = np.percentile(rets, 5)
    skew = rets.skew()
    kurt = rets.kurtosis()
    return {
        "rend_esperado_annual": mean,
        "volatilidad_annual": vol,
        "sharpe": sharpe,
        "var_95": var_95,
        "skewness": skew,
        "kurtosis": kurt,
        "ultimo_precio": serie.iloc[-1],
    }


def fundamentales(ticker):
    """Obtiene fundamentales del ticker USD subyacente."""
    try:
        info = yf.Ticker(ticker).info
        return {k: info.get(k) for k in FUNDAMENTOS_KEYS}
    except Exception:
        return {k: None for k in FUNDAMENTOS_KEYS}


def filtrar_metricos(candidatos, prices, min_dias=60):
    """Calcula métricas para cada candidato según su especie (ARS/USD).

    Devuelve lista de dicts con métricas y fundamentos.
    """
    filas = []
    for c in candidatos:
        # precio según moneda del candidato
        ticker_precio = c.get("ticker_ars") if c.get("moneda") == "ARS" else c.get("ticker_usd")
        serie = prices.get(ticker_precio)
        m = metricas_riesgo_retorno(serie)
        if m is None:
            continue
        # fundamentos: intentamos subyacente USD; si falla, usamos ticker de precio
        fund = fundamentales(c["ticker_usd"])
        if all(v is None for v in fund.values()):
            fund = fundamentales(ticker_precio)
        nombre = c.get("nombre") or ""
        # intentar completar nombre desde fundamentos si falta
        if not nombre and fund.get("sector"):
            try:
                info = yf.Ticker(ticker_precio).info
                nombre = info.get("longName") or info.get("shortName") or ""
            except Exception:
                pass
        fila = {
            "ticker": ticker_precio,
            "ticker_original": c["ticker_original"],
            "sector_json": c.get("sector_json"),
            "industria": c.get("industria"),
            "nombre": nombre,
            "moneda": c.get("moneda"),
            "pais": c.get("pais"),
        }
        fila.update(m)
        fila.update({"fund_" + k: v for k, v in fund.items()})
        filas.append(fila)
    return filas


def optimizar_max_sharpe(returns_df, risk_free_annual=0.04, min_peso=0.005):
    """Optimización Markowitz long-only max Sharpe."""
    returns_df = returns_df.dropna(how="any", axis=1)
    returns_df = returns_df.dropna(how="any", axis=0)
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
    w = opt.x
    w = w / w.sum()
    rp = np.dot(w, mu.values)
    vp = np.sqrt(np.dot(w.T, np.dot(sigma.values, w)))
    sharpe = (rp - risk_free_annual) / vp
    return {
        "tickers": list(returns_df.columns),
        "pesos": w,
        "retorno_esperado": rp,
        "volatilidad": vp,
        "sharpe": sharpe,
    }


def construir_optimizacion(candidatos_moneda, moneda_label, cash, risk_free=0.04, verbose=False,
                            max_cands=60, aplicar_liquidez=True,
                            min_monto_usd=5_000_000, min_monto_ars=1_000_000,
                            min_precio_usd=5.0, min_precio_ars=100.0):
    """Descarga precios, calcula métricas y optimiza para una bucket (ARS/USD)."""
    if not candidatos_moneda:
        return None, None

    # filtro de liquidez
    if aplicar_liquidez:
        candidatos_moneda, rechazados = filtrar_por_liquidez(
            candidatos_moneda, moneda_label,
            min_monto_usd=min_monto_usd, min_monto_ars=min_monto_ars,
            min_precio_usd=min_precio_usd, min_precio_ars=min_precio_ars,
            verbose=verbose,
        )
        if len(candidatos_moneda) < 2:
            if verbose:
                print("  No quedan suficientes candidatos líquidos para %s" % moneda_label)
            return pd.DataFrame(rechazados), None

    # distribuir candidatos entre sectores para no quedar solo en el primero
    por_sector = {}
    for c in candidatos_moneda:
        por_sector.setdefault(c.get("sector_json", "Otros"), []).append(c)
    n_sectores = len(por_sector)
    por_sector_limit = max(1, max_cands // n_sectores) if n_sectores else max_cands
    seleccionados = []
    for sec, lst in por_sector.items():
        seleccionados.extend(lst[:por_sector_limit])
    candidatos_moneda = seleccionados
    if verbose:
        print("  %d candidatos %s seleccionados (%d sectores)" % (len(candidatos_moneda), moneda_label, n_sectores))

    tickers_precio = []
    for c in candidatos_moneda:
        tk = c["ticker_ars"] if moneda_label == "ARS" else c["ticker_usd"]
        if tk and tk not in tickers_precio:
            tickers_precio.append(tk)

    if verbose:
        print("\n[+] Descargando %d precios para bucket %s..." % (len(tickers_precio), moneda_label))
    prices = descargar_precios(tickers_precio, period="1y", verbose=verbose)

    if verbose:
        print("[+] Calculando métricas...")
    filas = filtrar_metricos(candidatos_moneda, prices)

    if len(filas) < 2:
        if verbose:
            print("  No hay suficientes activos con datos.")
        return pd.DataFrame(filas), None

    df = pd.DataFrame(filas)
    df = df.sort_values("sharpe", ascending=False)

    # Para optimizar, tomamos los tickers con datos y usamos sus precios
    tickers_optimizar = df["ticker"].tolist()
    prices_df = pd.DataFrame({t: prices[t] for t in tickers_optimizar if t in prices})
    returns_df = prices_df.pct_change().dropna()

    opt = optimizar_max_sharpe(returns_df, risk_free_annual=risk_free)

    if opt:
        df_opt = pd.DataFrame({
            "ticker": opt["tickers"],
            "peso": opt["pesos"],
            "monto_sugerido": [p * cash for p in opt["pesos"]],
            "cantidad_sugerida": None,  # se completa después con precio
        })
        # unir con métricas
        df_opt = df_opt.merge(df, on="ticker", how="left")
        # cantidad aproximada
        df_opt["cantidad_sugerida"] = (df_opt["monto_sugerido"] / df_opt["ultimo_precio"]).fillna(0).round(0).astype(int)
        # reordenar
        cols = ["ticker", "nombre", "sector_json", "industria", "rend_esperado_annual",
                "volatilidad_annual", "sharpe", "peso", "monto_sugerido",
                "cantidad_sugerida", "ultimo_precio"]
        cols = [c for c in cols if c in df_opt.columns]
        df_opt = df_opt[cols].sort_values("peso", ascending=False)
        return df, opt
    return df, None


def _df_a_markdown(df, titulo, columnas=None):
    """Formatea un DataFrame a markdown, opcionalmente recortando columnas."""
    out = ["## %s" % titulo]
    if df is None or df.empty:
        out.append("*Sin datos suficientes.*")
        out.append("")
        return "\n".join(out)
    if columnas:
        df = df[[c for c in columnas if c in df.columns]]
    out.append(df.to_markdown(index=False))
    out.append("")
    return "\n".join(out)


def generar_informe_constructor(portafolio_path, contexto, unificado_path, out_path, verbose=False,
                                max_cands=60, aplicar_liquidez=True,
                                min_monto_usd=5_000_000, min_monto_ars=1_000_000,
                                min_precio_usd=5.0, min_precio_ars=100.0):
    base, _ = os.path.splitext(out_path)
    # carga portafolio para saber cash ARS/USD disponible
    with open(portafolio_path, encoding="utf-8") as f:
        port = json.load(f)

    # por simplicidad sumamos cash de todas las cuentas
    cash_usd_total = 0.0
    cash_ars_total = 0.0
    for c in port.get("cuentas", []):
        cash = c.get("cash", {})
        cash_usd_total += cash.get("USD", 0) + cash.get("USD_C", 0)
        cash_ars_total += cash.get("ARS", 0)

    sectores = sectores_beneficiados(contexto, top_n=3)
    if verbose:
        print("Sectores beneficiados según Murphy:", sectores)

    unificado = cargar_unificado(unificado_path)
    candidatos = extraer_candidatos(unificado, sectores)

    # Aplanar candidatos por moneda
    ars_cands = []
    usd_cands = []
    for sector, buckets in candidatos.items():
        for c in buckets["ars"]:
            ars_cands.append(c)
        for c in buckets["usd"]:
            usd_cands.append(c)

    df_ars, opt_ars = construir_optimizacion(ars_cands, "ARS", cash_ars_total, verbose=verbose,
                                              max_cands=max_cands, aplicar_liquidez=aplicar_liquidez,
                                              min_monto_usd=min_monto_usd, min_monto_ars=min_monto_ars,
                                              min_precio_usd=min_precio_usd, min_precio_ars=min_precio_ars)
    df_usd, opt_usd = construir_optimizacion(usd_cands, "USD", cash_usd_total, verbose=verbose,
                                              max_cands=max_cands, aplicar_liquidez=aplicar_liquidez,
                                              min_monto_usd=min_monto_usd, min_monto_ars=min_monto_ars,
                                              min_precio_usd=min_precio_usd, min_precio_ars=min_precio_ars)

    # agregar scoring de noticias
    if verbose:
        print("\n[+] Analizando noticias recientes...")
    df_ars = agregar_score_noticias(df_ars, max_items=10, verbose=verbose)
    df_usd = agregar_score_noticias(df_usd, max_items=10, verbose=verbose)

    # detalle de noticias para candidatos con score negativo o alto
    tickers_con_noticias = []
    for df in [df_ars, df_usd]:
        if df is not None and not df.empty and "ticker" in df.columns:
            tickers_con_noticias.extend(df["ticker"].dropna().unique().tolist())
    news_detail = analizar_noticias(list(set(tickers_con_noticias)), max_items=5, verbose=verbose)
    if not news_detail.empty:
        news_detail.to_csv(base + "_noticias.csv", index=False)

    # guardar dataframes a CSV
    if df_ars is not None and not df_ars.empty:
        df_ars.to_csv(base + "_ars_candidatos.csv", index=False)
    if df_usd is not None and not df_usd.empty:
        df_usd.to_csv(base + "_usd_candidatos.csv", index=False)

    # Generar Markdown
    md = []
    md.append("# Constructor de Portafolio — Sectores beneficiados por Murphy")
    md.append("**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d"))
    md.append("")
    md.append("> Pipeline: sectores Murphy → unificado de tickers → métricas de riesgo-retorno → fundamentos → Markowitz max-Sharpe.")
    md.append("")
    md.append("## Contexto Murphy")
    cap13 = contexto.get("cap13", {}).get("resultados", {})
    lideres = list(cap13.get("liderazgo_sectorial_200d", {}).keys())[:3]
    md.append("- Sectores líderes (200d): %s" % ", ".join(lideres))
    md.append("- Sectores del unificado seleccionados: %s" % ", ".join(sectores))
    md.append("")
    md.append("## Cash disponible")
    md.append("- USD: $%.2f" % cash_usd_total)
    md.append("- ARS: $%.2f" % cash_ars_total)
    md.append("")

    # ARS
    cols_riesgo_ars = ["ticker", "nombre", "sector_json", "industria", "rend_esperado_annual",
                       "volatilidad_annual", "sharpe", "var_95", "ultimo_precio",
                       "news_score", "news_count", "news_bullish", "news_bearish"]
    cols_fund_ars = ["ticker", "nombre", "fund_trailingPE", "fund_forwardPE", "fund_priceToBook",
                     "fund_returnOnEquity", "fund_revenueGrowth", "fund_earningsGrowth",
                     "fund_debtToEquity", "fund_recommendationMean", "fund_targetMeanPrice"]
    md.append(_df_a_markdown(df_ars, "Bucket ARS — Métricas cuantitativas de candidatos", cols_riesgo_ars))
    md.append(_df_a_markdown(df_ars, "Bucket ARS — Fundamentos", cols_fund_ars))

    opt_ars_df = None
    if opt_ars:
        opt_ars_df = pd.DataFrame({
            "ticker": opt_ars["tickers"],
            "peso": opt_ars["pesos"],
            "monto_sugerido_ars": [p * cash_ars_total for p in opt_ars["pesos"]],
        }).merge(df_ars[["ticker", "nombre", "ultimo_precio"]], on="ticker", how="left")
        opt_ars_df["cantidad_sugerida"] = (opt_ars_df["monto_sugerido_ars"] / opt_ars_df["ultimo_precio"]).fillna(0).round(0).astype(int)
        opt_ars_df = opt_ars_df[opt_ars_df["peso"] >= 0.005].sort_values("peso", ascending=False)
        opt_ars_df.to_csv(base + "_ars_optimo.csv", index=False)
        md.append(_df_a_markdown(opt_ars_df, "Bucket ARS — Portafolio óptimo Max Sharpe",
                                 ["ticker", "nombre", "peso", "monto_sugerido_ars", "cantidad_sugerida", "ultimo_precio"]))
        md.append("- **Rendimiento esperado:** %.2f%%" % (opt_ars["retorno_esperado"] * 100))
        md.append("- **Volatilidad:** %.2f%%" % (opt_ars["volatilidad"] * 100))
        md.append("- **Sharpe:** %.3f" % opt_ars["sharpe"])
        md.append("")

    # USD
    cols_riesgo_usd = cols_riesgo_ars
    cols_fund_usd = cols_fund_ars
    md.append(_df_a_markdown(df_usd, "Bucket USD — Métricas cuantitativas de candidatos", cols_riesgo_usd))
    md.append(_df_a_markdown(df_usd, "Bucket USD — Fundamentos", cols_fund_usd))

    opt_usd_df = None
    if opt_usd:
        opt_usd_df = pd.DataFrame({
            "ticker": opt_usd["tickers"],
            "peso": opt_usd["pesos"],
            "monto_sugerido_usd": [p * cash_usd_total for p in opt_usd["pesos"]],
        }).merge(df_usd[["ticker", "nombre", "ultimo_precio"]], on="ticker", how="left")
        opt_usd_df["cantidad_sugerida"] = (opt_usd_df["monto_sugerido_usd"] / opt_usd_df["ultimo_precio"]).fillna(0).round(0).astype(int)
        opt_usd_df = opt_usd_df[opt_usd_df["peso"] >= 0.005].sort_values("peso", ascending=False)
        opt_usd_df.to_csv(base + "_usd_optimo.csv", index=False)
        md.append(_df_a_markdown(opt_usd_df, "Bucket USD — Portafolio óptimo Max Sharpe",
                                 ["ticker", "nombre", "peso", "monto_sugerido_usd", "cantidad_sugerida", "ultimo_precio"]))
        md.append("- **Rendimiento esperado:** %.2f%%" % (opt_usd["retorno_esperado"] * 100))
        md.append("- **Volatilidad:** %.2f%%" % (opt_usd["volatilidad"] * 100))
        md.append("- **Sharpe:** %.3f" % opt_usd["sharpe"])
        md.append("")

    # Noticias
    if not news_detail.empty:
        md.append("## Noticias recientes (resumen)")
        agg_news = news_detail.groupby("ticker").agg(
            noticias=("sentimiento", "count"),
            score_neto=("sentimiento", "sum"),
            bullish=("sentimiento", lambda x: int((x == 1).sum())),
            bearish=("sentimiento", lambda x: int((x == -1).sum())),
        ).reset_index().sort_values("score_neto", ascending=False)
        md.append(agg_news.to_markdown(index=False))
        md.append("")
        # alertas bajistas
        bajistas = agg_news[agg_news["score_neto"] < -1]["ticker"].tolist()
        if bajistas:
            md.append("**Alertas bajistas por noticias:** %s" % ", ".join(bajistas))
            md.append("")
        md.append("Detalle completo en `%s_noticias.csv`." % os.path.basename(base))
        md.append("")

    md.append("## Advertencias")
    md.append("- Los retornos esperados se calculan sobre 1 año de historial; en periodos cortos con tendencias fuertes (ej. semiconductores, energía) el Sharpe puede estar inflado.")
    md.append("- La optimización Markowitz asume que correlaciones y volatilidades históricas se mantienen, un supuesto que raramente se cumple en el corto plazo.")
    md.append("- Para cedears ARS se usan los tickers `.BA`; para el bucket USD se usan los ADRs/acciones subyacentes. Los fundamentales provienen del ticker subyacente en USD.")
    md.append("- El sentimiento de noticias es un scoring keyword simple (no NLP avanzado); usarlo como filtro adicional, no como señal única.")
    md.append("- Revisar liquidez, comisiones, impuestos y horizonte antes de ejecutar.")

    texto = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(texto)

    if verbose:
        print("\nGuardado en %s" % out_path)
    return df_ars, df_usd, opt_ars, opt_usd, texto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portafolio", default="portafolios_inviu.json")
    parser.add_argument("--unificado", default="unificado_completo - copia.json")
    parser.add_argument("--contexto", default="contexto_murphy_2026-08-13.json")
    parser.add_argument("--out", default="CONSTRUCTOR_PORTAFOLIO.md")
    parser.add_argument("--max-cands", type=int, default=60, help="Máximo de candidatos por bucket")
    parser.add_argument("--no-liquidez", action="store_true", help="No aplicar filtro de liquidez")
    parser.add_argument("--min-monto-usd", type=float, default=5_000_000, help="Monto diario mínimo USD")
    parser.add_argument("--min-monto-ars", type=float, default=1_000_000, help="Monto diario mínimo ARS")
    parser.add_argument("--min-precio-usd", type=float, default=5.0, help="Precio mínimo USD")
    parser.add_argument("--min-precio-ars", type=float, default=100.0, help="Precio mínimo ARS")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    ctx = None
    if args.contexto and os.path.exists(args.contexto):
        with open(args.contexto, encoding="utf-8") as f:
            ctx = json.load(f)
    if ctx is None or "cap12" not in ctx or "cap13" not in ctx:
        from analisis.ejecutivo.diario import MurphyDaily
        daily = MurphyDaily(periodo="6y", verbose=args.verbose)
        ctx = daily.run(nombres=["12", "13"])

    generar_informe_constructor(args.portafolio, ctx, args.unificado, args.out, verbose=args.verbose,
                                max_cands=args.max_cands, aplicar_liquidez=not args.no_liquidez,
                                min_monto_usd=args.min_monto_usd, min_monto_ars=args.min_monto_ars,
                                min_precio_usd=args.min_precio_usd, min_precio_ars=args.min_precio_ars)


if __name__ == "__main__":
    main()