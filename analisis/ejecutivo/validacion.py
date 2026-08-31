# -*- coding: utf-8 -*-
"""Validacion del ciclo intermarket contra noticias (yfinance, sin API key).

Cruza el contexto tecnico del motor Murphy (etapa de Pring, shock de tasas,
liderazgo sectorial) contra el flujo real de noticias de cada cluster de
mercado (tasas, dolar, commodities, oro, acciones, riesgo, emergentes, tech).

Para cada cluster compara el signo de la tendencia de 6m que detecto el motor
con el sentimiento neto de las noticias: si coinciden, el analisis se confirma
(la narrativa y el precio van en la misma direccion); si divergen, el precio
puede haber ido por delante de la historia y el ciclo aparece agotado o en
riesgo de revertir.

Salida: VALIDACION_INTERMARKET.md
Uso (lo invoca run_all.py):
    python -m analisis.ejecutivo.validacion --contexto contexto_murphy_<fecha>.json
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.portafolio.noticias import score_sentiment, fetch_news

# Cada cluster tiene un ticker representativo (para la tendencia tecnica) y
# tickers de los que se traen noticias.
CLUSTERS = {
    "Tasas/Bonos": {
        "proxi": "TLT",
        "tickers": ["TLT", "^TNX", "^IRX"],
    },
    "Dolar": {
        "proxi": "DX-Y.NYB",
        "tickers": ["DX-Y.NYB", "FXE", "FXY"],
    },
    "Commodities": {
        "proxi": "^SPGSCI",
        "tickers": ["^SPGSCI", "XLE", "DBA", "USO"],
    },
    "Oro": {
        "proxi": "GC=F",
        "tickers": ["GC=F", "GLD", "GDX"],
    },
    "Acciones USA": {
        "proxi": "SPY",
        "tickers": ["SPY", "QQQ", "IWM"],
    },
    "Riesgo/VIX": {
        "proxi": "^VIX",
        "tickers": ["^VIX"],
    },
    "Emergentes": {
        "proxi": "EEM",
        "tickers": ["EEM", "ARGT"],
    },
}

# El shock de tasas del Cap.3 usa TNX como proxy (sube = bonds caen).
# Para el signo esperado de sentimiento de noticias usamos el movimiento del
# propio ticker: suele seguir al precio.


def v6_from_series(serie):
    """Variacion de ultimo vs hace 126 barras sobre una serie del contexto."""
    if serie is None or len(serie) < 127:
        return None
    return (serie.iloc[-1] / serie.iloc[-126] - 1) * 100.0


def tendencia_tecnica_cluster(contexto, cluster):
    """Signo esperado de la narrativa de noticias segun el contexto tecnico.

    Usa las senales del motor (que estan en <contexto>/cap<X>) para inferir si
    el cluster debe aparecer bullish (+1), bearish (-1) o plano (0).
    """
    if cluster == "Tasas/Bonos":
        cap3 = contexto.get("cap3", {}).get("resultados", {})
        st = cap3.get("shock_tasas", {})
        vidx = st.get("tnx_6m")
        if vidx is not None:
            # tasas suben => bonos/tlT caen => narrativa bearish de bonos
            return -1 if vidx > 0 else (1 if vidx < 0 else 0)
        return 0
    if cluster == "Dolar":
        for cap in ["cap1", "cap9", "cap4"]:
            r = contexto.get(cap, {}).get("resultados", {})
            for k in ["filtro_riesgo", "dolar_comm", "boom_definacional"]:
                grp = r.get(k, {})
                if "dxy_6m" in grp:
                    v = grp.get("dxy_6m")
                    if v is not None:
                        return 1 if v > 0 else (-1 if v < 0 else 0)
        return 0
    if cluster == "Commodities":
        cap1 = contexto.get("cap1", {}).get("resultados", {}).get("filtro_riesgo", {})
        v = cap1.get("crb_6m")
        if v is not None:
            return 1 if v > 0 else (-1 if v < 0 else 0)
        return 0
    if cluster == "Oro":
        cap8 = contexto.get("cap8", {}).get("resultados", {}).get("oro_dolar", {})
        v = cap8.get("gold_6m")
        if v is not None:
            return 1 if v > 0 else (-1 if v < 0 else 0)
        return 0
    if cluster == "Acciones USA":
        cap12 = contexto.get("cap12", {}).get("resultados", {})
        v = cap12.get("spy_6m")
        if v is not None:
            return 1 if v > 0 else (-1 if v < 0 else 0)
        return 0
    if cluster == "Riesgo/VIX":
        # VIX \u2193 = sentimiento calmo/greed: el motor reporta direccion del nivel.
        cap1 = contexto.get("cap1", {}).get("resultados", {}).get("filtro_riesgo", {})
        v = cap1.get("vix_nivel")
        # no tenemos 6m del vix en contexto; usamos las senales de la auditoria
        return 0
    if cluster == "Emergentes":
        cap15 = contexto.get("cap15", {}).get("resultados", {}).get("emergentes", {})
        v = cap15.get("eem_6m")
        if v is not None:
            return 1 if v > 0 else (-1 if v < 0 else 0)
        return 0
    return 0


def sentimiento_noticias(cluster, max_items=5):
    """Sentimiento neto (suma de score por noticia) del cluster."""
    ticks = [t for t in CLUSTERS[cluster]["tickers"]]
    total = 0
    n = 0
    detalle = []
    for t in ticks:
        for item in fetch_news(t, max_items=max_items):
            texto = "%s %s" % (item.get("title", ""), item.get("summary", ""))
            s = score_sentiment(texto)
            total += s
            n += 1
            detalle.append({"ticker": t, "titulo": item.get("title", "")[:90], "s": s})
    return total, n, detalle


def veredicto(tec, sent):
    """Compara signo tecnico esperado vs sentimiento de noticias."""
    if tec == 0 or sent == 0:
        return "INDEFINIDO", 0.0
    if (tec > 0) == (sent > 0):
        return "CONFIRMA", 1.0
    return "CONTRADICE", 0.0


def generar_informe(contexto_path, out_path="VALIDACION_INTERMARKET.md", max_items=5):
    with open(contexto_path, encoding="utf-8") as f:
        contexto = json.load(f)

    fecha = contexto.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    cap12 = contexto.get("cap12", {}).get("resultados", {})
    cap3 = contexto.get("cap3", {}).get("resultados", {})
    cap13 = contexto.get("cap13", {}).get("resultados", {})

    etapa = cap12.get("etapa_pring", "n/a")
    shock = cap3.get("shock_tasas", {})
    lideres = list(cap13.get("liderazgo_sectorial_200d", {}).keys())[:3]

    md = []
    md.append("# Validacion del Ciclo Intermarket contra Noticias")
    md.append("**Fecha:** %s" % fecha)
    md.append("")
    md.append("## 1. Lectura tecnica del motor")
    md.append("- **Etapa del ciclo (Pring):** %s" % etapa)
    md.append("- **Shock de tasas (Cap.3):** TNX 6m %s%% vs TLT 6m %s%% (alerta %s)"
             % (fmt(shock.get("tnx_6m")), fmt(shock.get("tlt_6m")),
                "SI" if shock.get("alerta_1994") else "NO"))
    md.append("- **Liderazgo sectorial 200d:** %s" % ", ".join(lideres))
    md.append("")

    md.append("## 2. Sentimiento de noticias por cluster (yfinance)")
    filas = []
    total_confirmadas = 0.0
    total_clusters = 0.0
    for cluster in CLUSTERS:
        tec = tendencia_tecnica_cluster(contexto, cluster)
        sent, n, detalle = sentimiento_noticias(cluster, max_items=max_items)
        verdict, peso = veredicto(tec, sent)
        etiqueta_tec = {1: "alcista", -1: "bajista", 0: "plana"}.get(tec, "plana")
        filas.append({
            "cluster": cluster,
            "tendencia_tecnica": etiqueta_tec,
            "noticias": n,
            "score_neto": sent,
            "veredicto": verdict,
        })
        md.append("- **%s:** tendencia tecnica %s | %d noticias | score neto %+d | **%s**"
                  % (cluster, etiqueta_tec, n, sent, verdict))
        if verdict in ("CONFIRMA",):
            total_confirmadas += 1.0
        total_clusters += 1.0
    md.append("")

    tasa_conf = total_confirmadas / total_clusters if total_clusters else 0.0

    md.append("## 3. Veredicto")
    if tasa_conf >= 0.6:
        veredicto_final = ("**ANALISIS VALIDADO:** %d de %d clusters confirman la lectura tecnica. "
                           "La narrativa de mercado (inflacion, Fed, dolar, commodities) respalda el "
                           "ciclo detectado por el motor." % (int(total_confirmadas), int(total_clusters)))
    elif tasa_conf >= 0.33:
        veredicto_final = ("**ANALISIS PARCIAL:** %d de %d clusters confirman. Existen tensiones entre "
                           "precio y narrativa que sugieren vigilancia (posible agotamiento o reversal)."
                           % (int(total_confirmadas), int(total_clusters)))
    else:
        veredicto_final = ("**ANALISIS EN RIESGO:** solo %d de %d clusters confirman. El precio se "
                           "adelanto a la noticia o el ciclo esta agotandose; revisar triggers de riesgo."
                           % (int(total_confirmadas), int(total_clusters)))
    md.append(veredicto_final)
    md.append("")
    md.append("## 4. Detalle por noticia relevante")
    md.append(df_detalle(contexto, max_items=max_items))

    texto = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(texto)
    return texto


def df_detalle(contexto, max_items=5):
    filas = []
    for cluster in CLUSTERS:
        tec = tendencia_tecnica_cluster(contexto, cluster)
        sent, n, detalle = sentimiento_noticias(cluster, max_items=max_items)
        stand = "CONFIRMA" if tec and sent and (tec > 0) == (sent > 0) else "MIRA"
        for d in detalle:
            filas.append({
                "cluster": cluster,
                "ticker": d["ticker"],
                "titulo": d["titulo"],
                "s": d["s"],
            })
    df = pd.DataFrame(filas)
    if df.empty:
        return "*Sin noticias disponibles.*"
    return df.to_markdown(index=False)


def fmt(v):
    if v is None:
        return "n/a"
    return "%+.1f" % v


def main():
    parser = argparse.ArgumentParser(description="Validar ciclo intermarket con noticias")
    parser.add_argument("--contexto", type=str, required=True,
                        help="JSON de contexto Murphy generado por el diario")
    parser.add_argument("--out", type=str, default="VALIDACION_INTERMARKET.md")
    parser.add_argument("--max-items", type=int, default=5)
    args = parser.parse_args()

    texto = generar_informe(args.contexto, out_path=args.out, max_items=args.max_items)
    print(texto)
    print("\nGuardado en %s" % args.out)


if __name__ == "__main__":
    main()