# -*- coding: utf-8 -*-
"""Análisis de noticias recientes vía yfinance + scoring de sentimiento simple.

No requiere API key externa. Usa yfinance.Ticker(ticker).news y un léxico
keywords en inglés/español para clasificar cada noticia en bullish/bearish/neutral.

Uso:
    python -m analisis.portafolio.noticias --tickers AAPL,MSFT,XOM --out noticias.md
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


POSITIVAS = {
    "beat", "beats", "profit", "profits", "growth", "strong", "surge", "rally", "gain", "gains",
    "outperform", "upgrade", "upgraded", "buy", "bullish", "optimistic", "record", "soar",
    "jump", "rise", "rises", "positive", "expansion", "breakthrough", "momentum", "recovery",
    "beat", "supera", "superan", "ganancia", "ganancias", "crecimiento", "fuerte", "alza",
    "sube", "suben", "compra", "alcista", "optimista", "réccord", "recuperación", "impulso",
    "expansión", "positivo", "positiva", "aumento", "beneficio", "dividendo", "dividendos",
    "acuerdo", "contrato", "adquisición", "fusion", "fusión", "aprobación", "lanzamiento",
    "innovación", "liderazgo", "rentable", "eficiencia", "mejora", "mejoran",
}

NEGATIVAS = {
    "miss", "misses", "loss", "losses", "weak", "decline", "drop", "drops", "fall", "falls",
    "plunge", "crash", "bearish", "sell", "downgrade", "downgraded", "cut", "cuts", "layoff",
    "layoffs", "recession", "debt", "default", "bankruptcy", "investigation", "lawsuit",
    "penalty", "fine", "warning", "risk", "risks", "volatile", "inflation", "stagflation",
    "fracasa", "falla", "pérdida", "pérdidas", "débil", "caída", "cae", "caen", "baja", "bajan",
    "bajista", "vender", "deuda", "quiebra", "recesión", "despido", "despidos", "recorte",
    "sanción", "multa", "demanda", "investigación", "riesgo", "riesgos", "incertidumbre",
    "inflación", "estanflación", "preocupación", "alerta", "problema", "problemas", "retraso",
}


def score_sentiment(text):
    """Devuelve +1/-1/0 según palabras clave encontradas en el texto."""
    if not text:
        return 0
    tokens = set(text.lower().split())
    pos = len(tokens.intersection(POSITIVAS))
    neg = len(tokens.intersection(NEGATIVAS))
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def fetch_news(ticker, max_items=10):
    """Devuelve lista de noticias normalizadas para un ticker."""
    try:
        raw = yf.Ticker(ticker).news or []
        news = []
        for n in raw:
            # yfinance a veces envuelve la noticia en 'content'
            if isinstance(n, dict) and "content" in n and isinstance(n["content"], dict):
                n = n["content"]
            if n.get("title") or n.get("summary") or n.get("description"):
                news.append({
                    "title": n.get("title", ""),
                    "summary": n.get("summary") or n.get("description", ""),
                    "published": n.get("pubDate") or n.get("published"),
                    "publisher": n.get("provider", {}).get("displayName") if isinstance(n.get("provider"), dict) else n.get("publisher", ""),
                })
        return news[:max_items]
    except Exception:
        return []


def analizar_noticias(tickers, max_items=10, verbose=False):
    """Analiza noticias para una lista de tickers y devuelve DataFrame agregado."""
    filas = []
    for t in tickers:
        if verbose:
            print("[+] Noticias %s..." % t)
        news = fetch_news(t, max_items=max_items)
        if not news:
            continue
        scores = []
        for item in news:
            title = item.get("title", "")
            summary = item.get("summary", "")
            text = title + " " + summary
            s = score_sentiment(text)
            scores.append(s)
            filas.append({
                "ticker": t,
                "fecha": item.get("published"),
                "titulo": title,
                "resumen": summary,
                "fuente": item.get("publisher", ""),
                "sentimiento": s,
            })
        if verbose and scores:
            print("  %d noticias, score neto=%d" % (len(scores), sum(scores)))
    return pd.DataFrame(filas)


def agregar_score_noticias(df, max_items=10, verbose=False):
    """Toma un DataFrame con columna 'ticker' y agrega columnas de noticias."""
    if df is None or df.empty or "ticker" not in df.columns:
        return df
    tickers = df["ticker"].dropna().unique().tolist()
    news_df = analizar_noticias(tickers, max_items=max_items, verbose=verbose)
    if news_df.empty:
        df["news_score"] = 0
        df["news_count"] = 0
        return df
    agg = news_df.groupby("ticker").agg(
        news_score=("sentimiento", "sum"),
        news_count=("sentimiento", "count"),
        news_bullish=("sentimiento", lambda x: int((x == 1).sum())),
        news_bearish=("sentimiento", lambda x: int((x == -1).sum())),
    ).reset_index()
    df = df.merge(agg, on="ticker", how="left")
    df["news_score"] = df["news_score"].fillna(0).astype(int)
    df["news_count"] = df["news_count"].fillna(0).astype(int)
    df["news_bullish"] = df["news_bullish"].fillna(0).astype(int)
    df["news_bearish"] = df["news_bearish"].fillna(0).astype(int)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", type=str, required=True,
                        help="Tickers separados por coma")
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--out", type=str, default="NOTICIAS_PORTAFOLIO.md")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    df = analizar_noticias(tickers, max_items=args.max_items, verbose=args.verbose)

    if df.empty:
        texto = "# Noticias de portafolio\n\n*No se encontraron noticias para los tickers solicitados.*"
    else:
        agg = df.groupby("ticker").agg(
            noticias=("sentimiento", "count"),
            score_neto=("sentimiento", "sum"),
            bullish=("sentimiento", lambda x: int((x == 1).sum())),
            bearish=("sentimiento", lambda x: int((x == -1).sum())),
            ultima_fecha=("fecha", "max"),
        ).reset_index().sort_values("score_neto", ascending=False)

        md = ["# Noticias de portafolio", "**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d"), ""]
        md.append("## Resumen por ticker")
        md.append(agg.to_markdown(index=False))
        md.append("")
        md.append("## Detalle de noticias")
        md.append(df.sort_values(["ticker", "fecha"], ascending=[True, False]).to_markdown(index=False))
        texto = "\n".join(md)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(texto)
    print(texto)
    print("\nGuardado en %s" % args.out)


if __name__ == "__main__":
    main()