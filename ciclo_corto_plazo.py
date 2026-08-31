# -*- coding: utf-8 -*-
"""Ciclo de corto plazo: rango normalizado min->max + fase intermarket.

Pipeline:
  [1] Detecta fase del ciclo (Murphy) via SCANNER_INTERMARKET o JSON.
  [2] Descarga precios de ETFs sectoriales + activos del portafolio.
  [3] Calcula rango normalizado (min->max) en 3 ventanas: 1M, 3M, 6M.
  [4] Estima ganancia/pérdida aprox si el activo vuelve al max o min del rango.
  [5] Score compuesto: fase + rango + momentum + regla de oro.
  [6] Salida: Markdown + CSV ordenado por score.

Uso:
    python ciclo_corto_plazo.py
    python ciclo_corto_plazo.py --ventanas 21,63,126
    python ciclo_corto_plazo.py --json contexto_actual.json
    python ciclo_corto_plazo.py --portafolio portafolios_inviu.json
"""
import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data import load, load_many
from core.ratio import analyze_pair
from core.senales import regla_oro, accion

# ETFs sectoriales Murphy
ETF_SECTOR = [
    "XLE", "XLK", "XLI", "XLP", "XLF", "XLY", "XLV", "XLC", "XLB", "XLRE", "XLU",
]
# ETFs macro
ETF_MACRO = ["GLD", "TLT", "QQQ", "IWM"]
# Benchmark
BENCH = "SPY"

# Mapeo ETF -> nombre legible
ETF_NOMBRE = {
    "XLE": "Energia", "XLK": "Tecnologia", "XLI": "Industriales",
    "XLP": "Defensiva Consumidor", "XLF": "Financieros", "XLY": "Consumo Ciclico",
    "XLV": "Salud", "XLC": "Comunicacion", "XLB": "Materiales",
    "XLRE": "Bienes Raices", "XLU": "Utilidades", "GLD": "Oro",
    "TLT": "Bonos Largos", "QQQ": "Nasdaq100", "IWM": "Small Caps",
}

# Fase -> ETFs que deberian liderar (de lib_mercado.SECTOR_ROTATION)
FASE_LIDERES = {
    0: ["XLU", "XLP", "XLV", "GLD", "TLT"],
    1: ["XLK", "XLY", "IWM", "XLF", "QQQ"],
    2: ["XLI", "XLB", "XLF", "XLE"],
    3: ["XLE", "GLD", "XLV", "XLU"],
    4: ["XLV", "XLP", "XLU", "GLD", "TLT"],
    5: ["TLT", "GLD"],
}

VENTANAS_DEF = [21, 63, 126]  # 1M, 3M, 6M en dias de trading


def cargar_fase(json_path=None):
    """Detecta la fase del ciclo intermarket."""
    fase_num = None
    etapa_pring = None
    lideres = []
    fuente = None

    # Intentar via SCANNER_INTERMARKET
    try:
        sys.path.insert(0, os.path.join(ROOT, "SCANNER_INTERMARKET"))
        from lib_mercado import detectar_fase, SECTOR_ROTATION
        import yfinance as yf

        close_raw = yf.download(
            ["TLT", "SPY", "GSG", "XLY", "XLP", "IWM", "QQQ"],
            period="2y", progress=False, auto_adjust=True,
        )
        if isinstance(close_raw.columns, pd.MultiIndex):
            close = close_raw["Close"]
        else:
            close = close_raw[["Close"]]
        close.columns = [str(c).strip() for c in close.columns]

        # Tendencias de bonos, stocks, commodities
        def _trend(col, umbral=2.0):
            s = close[col].dropna() if col in close.columns else None
            if s is None or len(s) < 60:
                return None
            s = s.tail(252)
            chg = (s.iloc[-1] / s.iloc[0] - 1) * 100
            slope = np.polyfit(np.arange(len(s)), s.values, 1)[0]
            if slope > 0 and chg > umbral:
                return 1
            if slope < 0 and chg < -umbral:
                return -1
            return 0

        b = _trend("TLT")
        s = _trend("SPY")
        c = _trend("GSG")

        # Extras
        extras = {}
        for k, num, den in [("xly_xlp", "XLY", "XLP"), ("iwm_spy", "IWM", "SPY"), ("qqq_spy", "QQQ", "SPY")]:
            if num in close.columns and den in close.columns:
                ratio = (close[num] / close[den]).dropna().tail(252)
                if len(ratio) > 30:
                    chg = (ratio.iloc[-1] / ratio.iloc[0] - 1) * 100
                    slope = np.polyfit(np.arange(len(ratio)), ratio.values, 1)[0]
                    extras[k] = 1 if slope > 0 and chg > 2 else (-1 if slope < 0 and chg < -2 else 0)

        fase = detectar_fase(b, s, c, extras)
        if fase:
            fase_num = fase["num"]
            rot = SECTOR_ROTATION.get(fase_num, {})
            lideres = rot.get("comprar", [])
            fuente = "SCANNER_INTERMARKET (fase %d: %s, conf %s)" % (fase_num, fase["name"], fase["conf"])
    except Exception as e:
        pass

    # Fallback: contexto JSON
    if fase_num is None and json_path and os.path.exists(json_path):
        try:
            with open(json_path, encoding="utf-8") as f:
                ctx = json.load(f)
            cap12 = ctx.get("cap12", {}).get("resultados", {})
            etapa_pring = cap12.get("etapa_pring")
            cap13 = ctx.get("cap13", {}).get("resultados", {})
            ranking = cap13.get("liderazgo_sectorial_200d", {})
            if ranking:
                from analisis.portafolio.constructor import ETF_A_SECTOR
                lideres = [ETF_A_SECTOR.get(etf, etf) for etf in list(ranking.keys())[:3]]
            fuente = "JSON: %s" % json_path
        except Exception:
            pass

    return fase_num, etapa_pring, lideres, fuente


def cargar_tickers_portafolio(path):
    """Extrae tickers USD unicos del portafolios_inviu.json."""
    tickers = set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for cuenta in data.get("cuentas", []):
            for ten in cuenta.get("tenencias", []):
                tk = ten.get("ticker", "")
                tipo = ten.get("tipo", "")
                if tipo == "bono":
                    continue
                # Normalizar a ticker USD (sin .BA)
                tk = tk.upper().replace(".BA", "")
                if tk and tk not in ("SPY",):  # SPY lo agregamos aparte
                    tickers.add(tk)
    except Exception:
        pass
    return sorted(tickers)


def calcular_rango_normalizado(series, ventana):
    """Calcula metricas de rango normalizado para una ventana dada.

    Returns dict con:
      - pct_dentro: donde esta el precio actual dentro del rango [0..100]
      - ganancia_max_pct: cuanto subiria si vuelve al max
      - perdida_min_pct: cuanto bajar si cae al min
      - max_ventana, min_ventana, precio_actual
    """
    if series is None or len(series) < ventana:
        return None
    s = series.iloc[-ventana:]
    precio = float(s.iloc[-1])
    mn = float(s.min())
    mx = float(s.max())
    rango = mx - mn
    if rango <= 0:
        return None
    pct_dentro = (precio - mn) / rango * 100
    gan_max = (mx - precio) / precio * 100 if precio > 0 else 0
    per_min = (precio - mn) / precio * 100 if precio > 0 else 0
    return {
        "pct_dentro": round(pct_dentro, 1),
        "ganancia_max_pct": round(gan_max, 2),
        "perdida_min_pct": round(per_min, 2),
        "max_ventana": round(mx, 2),
        "min_ventana": round(mn, 2),
        "precio_actual": round(precio, 2),
    }


def momentum_vs_spy(precio_series, spy_series, ventana=126):
    """Retorno excesivo vs SPY en la ventana dada."""
    if precio_series is None or spy_series is None:
        return None
    idx = precio_series.index.intersection(spy_series.index)
    if len(idx) < ventana:
        return None
    p = precio_series.loc[idx]
    s = spy_series.loc[idx]
    ret_tk = float(p.iloc[-1] / p.iloc[-ventana] - 1) * 100
    ret_spy = float(s.iloc[-1] / s.iloc[-ventana] - 1) * 100
    return round(ret_tk - ret_spy, 2)


def calcular_score(fase_num, rango_1m, rango_3m, rango_6m, momentum_ex, es_lider_fase, regla):
    """Score compuesto 0-100 para oportunidad de corto plazo."""
    score = 0.0

    # 1. Fase del ciclo (0-25 pts): si el activo esta en los sectores beneficiados
    if es_lider_fase:
        score += 25
    elif fase_num is not None:
        score += 5  # bonus minimo por estar en el universo

    # 2. Rango normalizado - preferimos activos cerca del min (0-30 pts)
    #    Si esta en el percentil bajo del rango, hay mas upside
    if rango_1m:
        # 0% = en el min (ideal), 100% = en el max (evitar)
        upside_1m = max(0, 100 - rango_1m["pct_dentro"])
        score += upside_1m * 0.10  # max 10 pts
    if rango_3m:
        upside_3m = max(0, 100 - rango_3m["pct_dentro"])
        score += upside_3m * 0.10  # max 10 pts
    if rango_6m:
        upside_6m = max(0, 100 - rango_6m["pct_dentro"])
        score += upside_6m * 0.10  # max 10 pts

    # 3. Momentum excesivo vs SPY (-10 a +15 pts)
    if momentum_ex is not None:
        if momentum_ex > 10:
            score += 15  # fuerte liderazgo
        elif momentum_ex > 0:
            score += momentum_ex * 0.75  # proporcional
        elif momentum_ex > -5:
            score += momentum_ex * 0.3  # penalizacion leve
        else:
            score -= 5  # fuerte debilidad

    # 4. Regla de oro (0-15 pts)
    if regla == "ALCISTA CONFIRMADA":
        score += 15
    elif regla == "CAMBIO DE REGIMEN":
        score += 8
    elif regla == "BAJISTA CONFIRMADA":
        score -= 5

    # 5. Bonus: si esta sobrevendido (rango 1M < 20%) -> reversal potencial
    if rango_1m and rango_1m["pct_dentro"] < 20:
        score += 10

    return round(max(0, min(100, score)), 1)


def recomendar(score, rango_1m, fase_num, es_lider):
    """Recomendacion textual basada en score y contexto."""
    if score >= 70:
        return "FUERTE OPORTUNIDAD"
    if score >= 50:
        return "OPORTUNIDAD MODERADA"
    if score >= 35:
        return "VIGILAR"
    return "NO RECOMENDADO"


def generar_markdown(tabla, fase_num, etapa_pring, lideres, fuente, ventanas):
    """Genera informe markdown."""
    md = []
    md.append("# Ciclo de Corto Plazo - Rango Normalizado")
    md.append("**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    md.append("")

    # Fase
    md.append("## 1. Fase del Ciclo Intermarket")
    if etapa_pring:
        md.append("- **Etapa Pring:** %s" % etapa_pring)
    if fase_num is not None:
        nombres_fase = {
            0: "Recession Bottom", 1: "Early Recovery", 2: "Mid Expansion",
            3: "Late Expansion", 4: "Early Contraction", 5: "Full Contraction"
        }
        md.append("- **Fase Murphy:** %d - %s" % (fase_num, nombres_fase.get(fase_num, "?")))
    if lideres:
        md.append("- **Sectores beneficiados:** %s" % ", ".join(lideres[:5]))
    if fuente:
        md.append("- **Fuente:** %s" % fuente)
    md.append("")

    # Metodologia
    ventanas_str = ", ".join("%dD" % v for v in ventanas)
    md.append("## 2. Metodologia")
    md.append("- **Ventanas de rango:** %s (1M, 3M, 6M)" % ventanas_str)
    md.append("- **Rango normalizado:** `(precio - min) / (max - min) * 100`")
    md.append("  - 0%% = precio en el minimo de la ventana (mas upside)")
    md.append("  - 100%% = precio en el maximo de la ventana (menos upside)")
    md.append("- **Ganancia max:** `(max - precio) / precio * 100` (si vuelve al max)")
    md.append("- **Perdida min:** `(precio - min) / precio * 100` (si cae al min)")
    md.append("- **Score:** combina fase + rango + momentum + regla de oro (0-100)")
    md.append("")

    # Ranking
    md.append("## 3. Ranking por Score de Oportunidad")
    md.append("")
    df = pd.DataFrame(tabla)
    if not df.empty:
        cols_show = ["ticker", "nombre", "precio", "score", "recomendacion",
                     "rango_1m_pct", "gan_max_1m", "rango_3m_pct", "gan_max_3m",
                     "rango_6m_pct", "gan_max_6m", "momentum_vs_spy", "regla_oro",
                     "es_lider_fase"]
        cols_show = [c for c in cols_show if c in df.columns]
        md.append(df[cols_show].to_markdown(index=False))
    md.append("")

    # Top 5 oportunidades
    if not df.empty:
        top5 = df.sort_values("score", ascending=False).head(5)
        md.append("## 4. Top 5 Oportunidades de Corto Plazo")
        md.append("")
        for _, row in top5.iterrows():
            md.append("### %s (%s) — Score: %.1f" % (row["ticker"], row.get("nombre", ""), row["score"]))
            md.append("- **Recomendacion:** %s" % row["recomendacion"])
            md.append("- **Precio actual:** $%.2f" % row["precio"])
            if row.get("rango_1m_pct") is not None:
                md.append("- **Rango 1M:** %.1f%% del rango | GanMax: +%.2f%% | PerdMin: -%.2f%%" % (
                    row["rango_1m_pct"], row["gan_max_1m"], row["perd_min_1m"]))
            if row.get("rango_3m_pct") is not None:
                md.append("- **Rango 3M:** %.1f%% del rango | GanMax: +%.2f%% | PerdMin: -%.2f%%" % (
                    row["rango_3m_pct"], row["gan_max_3m"], row["perd_min_3m"]))
            if row.get("rango_6m_pct") is not None:
                md.append("- **Rango 6M:** %.1f%% del rango | GanMax: +%.2f%% | PerdMin: -%.2f%%" % (
                    row["rango_6m_pct"], row["gan_max_6m"], row["perd_min_6m"]))
            if row.get("momentum_vs_spy") is not None:
                md.append("- **Momentum vs SPY (6M):** %+.2f%%" % row["momentum_vs_spy"])
            md.append("- **Regla de oro:** %s" % row.get("regla_oro", "N/D"))
            md.append("- **Lider de fase:** %s" % ("SI" if row.get("es_lider_fase") else "NO"))
            md.append("")

    # Advertencias
    md.append("## 5. Advertencias")
    md.append("- El rango normalizado es una measure de posicion relativa, no garantiza rebote.")
    md.append("- Los sectores beneficiados dependen de la fase detectada; un cambio de fase invalida la tesis.")
    md.append("- Para activos con poca historia (< ventana), el rango puede ser enganioso.")
    md.append("- Combinar con fundamentales y liquidez antes de operar.")
    md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Ciclo de corto plazo: rango normalizado + fase")
    parser.add_argument("--ventanas", default="21,63,126",
                        help="Dias de trading por ventana (default: 21,63,126)")
    parser.add_argument("--json", default="contexto_actual.json",
                        help="JSON de contexto Murphy para fallback de fase")
    parser.add_argument("--portafolio", default="portafolios_inviu.json",
                        help="Portafolio JSON para extraer tickers")
    parser.add_argument("--out", default="CICLO_CORTO_PLAZO.md",
                        help="Archivo markdown de salida")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    ventanas = [int(x.strip()) for x in args.ventanas.split(",")]

    print("=" * 90)
    print("CICLO DE CORTO PLAZO — RANGO NORMALIZADO MIN->MAX")
    print("=" * 90)

    # [1] Fase
    print("\n[1/5] Detectando fase del ciclo intermarket...")
    fase_num, etapa_pring, lideres, fuente = cargar_fase(args.json)
    nombres_fase = {
        0: "Recession Bottom", 1: "Early Recovery", 2: "Mid Expansion",
        3: "Late Expansion", 4: "Early Contraction", 5: "Full Contraction"
    }
    if fase_num is not None:
        print("  Fase: %d - %s" % (fase_num, nombres_fase.get(fase_num, "?")))
    else:
        print("  Fase: no detectada (usando solo metricas de precio)")
    if etapa_pring:
        print("  Etapa Pring: %s" % etapa_pring)
    if lideres:
        print("  Sectores beneficiados: %s" % ", ".join(lideres[:5]))

    # [2] Universo
    print("\n[2/5] Armando universo de activos...")
    etfs = ETF_SECTOR + ETF_MACRO
    tickers_port = cargar_tickers_portafolio(args.portafolio)
    todos_tickers = sorted(set(etfs + tickers_port + [BENCH]))
    print("  ETFs sectoriales: %d" % len(etfs))
    print("  Tickers portafolio: %d (%s)" % (len(tickers_port), ", ".join(tickers_port[:10]) + ("..." if len(tickers_port) > 10 else "")))
    print("  Total a descargar: %d" % len(todos_tickers))

    # [3] Descarga
    print("\n[3/5] Descargando precios (periodo 6M+ para ventanas)...")
    data = load_many(todos_tickers, period="1y")
    print("  Descargados: %d / %d" % (len(data), len(todos_tickers)))
    spy = data.get(BENCH)

    # [4] Calculo
    print("\n[4/5] Calculando rangos normalizados y scores...")
    tabla = []
    for tk in sorted(data.keys()):
        if tk == BENCH:
            continue
        serie = data[tk]
        if serie is None or len(serie) < 20:
            continue

        precio = float(serie.iloc[-1])
        nombre = ETF_NOMBRE.get(tk, tk)

        # Rangos por ventana
        rangos = {}
        for v in ventanas:
            r = calcular_rango_normalizado(serie, v)
            if r:
                rangos[v] = r

        # Momentum vs SPY
        mom = momentum_vs_spy(serie, spy, ventana=min(126, len(serie) - 1))

        # Regla de oro vs SPY
        regla = "N/D"
        try:
            _, stats = analyze_pair(serie, spy)
            regla = regla_oro(stats)
        except Exception:
            pass

        # Es lider de fase?
        es_lider = False
        if fase_num is not None:
            # Buscar si el ticker o su ETF sectorial esta en los lideres
            es_lider = tk in FASE_LIDERES.get(fase_num, [])
            # Para tickers del portafolio, verificar por sector
            if not es_lider:
                # Mapeo basico ticker -> ETF sectorial
                ticker_a_etf = {
                    "AMZN": "XLY", "GOOGL": "XLC", "NVDA": "XLK", "TSM": "XLK",
                    "SMH": "XLK", "MU": "XLK", "IBM": "XLK", "AAPL": "XLK",
                    "PAMP": "XLE", "XLE": "XLE", "URA": "XLE", "CEG": "XLE",
                    "CVS": "XLV", "PEP": "XLP", "PFE": "XLV", "SLV": "GLD",
                    "LMT": "XLI", "NU": "XLF",
                }
                etf_asociado = ticker_a_etf.get(tk)
                if etf_asociado:
                    es_lider = etf_asociado in FASE_LIDERES.get(fase_num, [])

        # Score
        r1m = rangos.get(ventanas[0]) if len(ventanas) > 0 else None
        r3m = rangos.get(ventanas[1]) if len(ventanas) > 1 else None
        r6m = rangos.get(ventanas[2]) if len(ventanas) > 2 else None

        score = calcular_score(fase_num, r1m, r3m, r6m, mom, es_lider, regla)
        rec = recomendar(score, r1m, fase_num, es_lider)

        fila = {
            "ticker": tk,
            "nombre": nombre,
            "precio": precio,
            "score": score,
            "recomendacion": rec,
            "es_lider_fase": es_lider,
            "regla_oro": regla,
            "momentum_vs_spy": mom,
        }

        # Agregar metricas de cada ventana
        for v, label in zip(ventanas, ["1m", "3m", "6m"]):
            r = rangos.get(v)
            if r:
                fila["rango_%s_pct" % label] = r["pct_dentro"]
                fila["gan_max_%s" % label] = r["ganancia_max_pct"]
                fila["perd_min_%s" % label] = r["perdida_min_pct"]
                fila["max_%s" % label] = r["max_ventana"]
                fila["min_%s" % label] = r["min_ventana"]
            else:
                fila["rango_%s_pct" % label] = None
                fila["gan_max_%s" % label] = None
                fila["perd_min_%s" % label] = None
                fila["max_%s" % label] = None
                fila["min_%s" % label] = None

        tabla.append(fila)

        if args.verbose:
            r1m_str = "%.0f%%" % r1m["pct_dentro"] if r1m else "N/D"
            gan_str = "+%.1f%%" % r1m["ganancia_max_pct"] if r1m else "N/D"
            print("  %-8s %8.2f  R1M: %6s  GanMax: %8s  Score: %5.1f  %s" % (
                tk, precio, r1m_str, gan_str, score, rec))

    # [5] Salida
    print("\n[5/5] Generando informe...")
    df = pd.DataFrame(tabla).sort_values("score", ascending=False)

    # CSV
    csv_path = args.out.replace(".md", ".csv")
    if not df.empty:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("  CSV: %s" % csv_path)

    # Markdown
    md_text = generar_markdown(tabla, fase_num, etapa_pring, lideres, fuente, ventanas)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md_text)
    print("  Markdown: %s" % args.out)

    # Resumen por consola
    print("\n" + "=" * 90)
    print("TOP 10 POR SCORE DE OPORTUNIDAD")
    print("=" * 90)
    if not df.empty:
        top = df.head(10)
        print("%-8s %10s %6s  %-20s %12s %12s %12s  %s" % (
            "Ticker", "Precio", "Score", "Recomendacion",
            "GanMax 1M", "GanMax 3M", "GanMax 6M", "Fase"))
        print("-" * 90)
        for _, row in top.iterrows():
            g1 = "+%.1f%%" % row["gan_max_1m"] if row.get("gan_max_1m") is not None else "N/D"
            g3 = "+%.1f%%" % row["gan_max_3m"] if row.get("gan_max_3m") is not None else "N/D"
            g6 = "+%.1f%%" % row["gan_max_6m"] if row.get("gan_max_6m") is not None else "N/D"
            lider = "*" if row.get("es_lider_fase") else " "
            print("%-8s %10.2f %5.1f  %-20s %12s %12s %12s  %s%s" % (
                row["ticker"], row["precio"], row["score"], row["recomendacion"],
                g1, g3, g6, row.get("regla_oro", "")[:20], lider))

    print("\n  * = lider de fase actual")
    print("=" * 90)


if __name__ == "__main__":
    main()
