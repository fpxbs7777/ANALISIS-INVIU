# -*- coding: utf-8 -*-
"""Noticias del ciclo intermarket: lectura + verificacion del regimen.

Descarga noticias recientes (yfinance Ticker.news, sin API key) para los
drivers del ciclo (tasas, dolar, commodities/energia, oro, riesgo/acciones),
las clasifica por tema (macroeconomico) y sentimiento, y las cruza contra el
contexto Murphy pre-generado para verificar si el analisis del motor se
justifica por la narrativa noticiosa.

Uso (lo invoca run_all.py tras diario):
    python -m analisis.ejecutivo.noticias_ciclo
    python -m analisis.ejecutivo.noticias_ciclo --contexto contexto_murphy_2026-08-16.json
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.data import load
from analisis.portafolio.noticias import fetch_news, score_sentiment

# Drivers del ciclo: a cada uno le pedimos noticias y precio 6m.
# invert=True -> el sentimiento esperado es opuesto al retorno (VIX, TNX).
DRIVERS = [
    {"nombre": "Bonos / Tasas (TNX 10Y)", "ticker": "^TNX", "dimension": "tasas", "invert": True},
    {"nombre": "Bonos largos (TLT)",      "ticker": "TLT",  "dimension": "tasas"},
    {"nombre": "Dolar (DXY)",             "ticker": "DX-Y.NYB", "dimension": "dolar"},
    {"nombre": "Acciones (SPY)",          "ticker": "SPY",  "dimension": "riesgo"},
    {"nombre": "Volatilidad (VIX)",       "ticker": "^VIX", "dimension": "riesgo", "invert": True},
    {"nombre": "Oro (GLD)",               "ticker": "GLD",  "dimension": "oro"},
    {"nombre": "Mineras de oro (GDX)",    "ticker": "GDX",  "dimension": "oro"},
    {"nombre": "Energia (XLE)",           "ticker": "XLE",  "dimension": "energia"},
    {"nombre": "Petroleo (USO)",          "ticker": "USO",  "dimension": "energia"},
    {"nombre": "Tech (XLK)",              "ticker": "XLK",  "dimension": "riesgo"},
    {"nombre": "Corea (EWY)",             "ticker": "EWY",  "dimension": "geopolitica"},
    {"nombre": "China (FXI)",             "ticker": "FXI",  "dimension": "geopolitica"},
]

# Temas macroeconomicos: frases (subcadena) en titulo+resumen en minusculas.
TEMAS = {
    "tasas": ["yields", "treasury", "treasuries", "10-year", "10y", "bond market", "rate cut",
              "rate hikes", "rate hike", "interest rate", "federal reserve", "fed", "hawkish",
              "dovish", "taper", "policy", "yield"],
    "inflacion": ["inflation", "consumer price", "cpi", "price pressure", "price pressures",
                  "deflation", "stagflation", "cost of living", "prices rose", "prices"],
    "energia": ["oil", "crude", "brent", "wti", "opec", "energy", "gas", "gasoline",
                "refinery", "petroleum", "pipeline", "drilling"],
    "oro": ["gold", "silver", "bullion", "precious metal", "precious metals"],
    "dolar": ["dollar", "greenback", "dollar index", "currency", "currencies", "fx",
              "usd", "foreign exchange", "dxy"],
    "geopolitica": ["iran", "war", "conflict", "sanction", "sanctions", "invasion", "israel",
                    "russia", "houthi", "missile", "geopolitical", "tariff", "tariffs",
                    "trade war", "strait", "hormuz", "attack", "strike"],
    "empleo": ["jobs", "jobless", "employment", "labor", "unemployment", "payroll",
               "nonfarm", "non-farm", "hiring", "labour"],
    "recesion": ["recession", "slowdown", "contraction", "slump", "downturn",
                 "stagflation", "layoffs", "layoff", "crisis"],
    "crecimiento": ["growth", "expansion", "gdp", "earnings", "corporate", "consumer spending",
                    "retail sales", "demand", "sales", "pmi"],
    "riesgo_mdo": ["selloff", "sell-off", "correction", "crash", "volatility", "jitters",
                   "risk", "risk-off", "banking", "credit", "default", "liquidity"],
}

# Reclamaciones del regimen que el motor puede afirmar; cada una espera ciertos temas.
CLAIMS = [
    {"claim": "Shock de tasas (Cap.3, alerta_1994): TNX sube y bonos caen",
     "clave": "alerta_1994", "esperado": ["tasas", "inflacion"], "opuesto": ["dolar"]},
    {"claim": "Commodities / energia lideran (CRB al alza; Stage 4)",
     "clave": "commodities", "esperado": ["energia"], "opuesto": ["recesion"]},
    {"claim": "Riesgo geopolitico sobre suministro (Hormuz/Irán) presiona energia",
     "clave": "geopolitica", "esperado": ["geopolitica", "energia"], "opuesto": []},
    {"claim": "Dolar firme (DXY al alza en 6m)",
     "clave": "dolar", "esperado": ["dolar"], "opuesto": ["oro"]},
    {"claim": "Inflacion aun elevada / presion de costos",
     "clave": "inflacion", "esperado": ["inflacion"], "opuesto": []},
    {"claim": "Consumidor debil (XLY/XLP negativo, defensivas resistiendo)",
     "clave": "consumidor", "esperado": ["recesion", "empleo", "crecimiento"], "opuesto": []},
    {"claim": "Volatilidad contenida (VIX bajo): complacencia tipica de late-cycle",
     "clave": "vix", "esperado": [], "opuesto": ["riesgo_mdo"]},
]

_LAST_CACHED = {}


def pct_6m(ticker):
    """Retorno % a 6 meses (~126 barras) desde el ultimo cierre."""
    if ticker in _LAST_CACHED:
        return _LAST_CACHED[ticker]
    out = None
    try:
        s = load(ticker, period="1y", use_cache=True)
        if len(s) >= 126:
            out = float((s.iloc[-1] / s.iloc[-126] - 1.0) * 100.0)
    except Exception:
        out = None
    _LAST_CACHED[ticker] = out
    return out


def temas_detectados(text):
    """Devuelve lista de temas macro encontrados por subcadena."""
    t = (text or "").lower()
    encontrados = []
    for tema, frases in TEMAS.items():
        if any(f in t for f in frases):
            encontrados.append(tema)
    return encontrados


def normalizar_fecha(pub):
    if not pub:
        return ""
    try:
        dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(pub)[:16]


def analizar_drivers(max_items=10):
    """Descarga noticias por driver y devuelve DataFrame con temas y sentimiento."""
    filas = []
    for drv in DRIVERS:
        tk = drv["ticker"]
        news = fetch_news(tk, max_items=max_items)
        for item in news:
            title = item.get("title", "")
            summary = item.get("summary", "")
            text = title + " " + summary
            filas.append({
                "ticker": tk,
                "dimension": drv["dimension"],
                "fecha": normalizar_fecha(item.get("published")),
                "titulo": title,
                "resumen": summary[:500],
                "fuente": item.get("publisher", ""),
                "sentimiento": score_sentiment(text),
                "temas": ",".join(temas_detectados(text)),
            })
    return pd.DataFrame(filas)


def _claim_estado(clave, contexto):
    """True/False/None segun la clave de la reclamacion en el contexto."""
    cap3 = contexto.get("cap3", {}).get("resultados", {}) if contexto else {}
    cap1 = contexto.get("cap1", {}).get("resultados", {}) if contexto else {}
    cap2 = contexto.get("cap2", {}).get("resultados", {}) if contexto else {}
    cap12 = contexto.get("cap12", {}).get("resultados", {}) if contexto else {}
    cap13 = contexto.get("cap13", {}).get("resultados", {}) if contexto else {}
    if clave == "alerta_1994":
        return cap3.get("shock_tasas", {}).get("alerta_1994")
    if clave == "commodities":
        crb = cap12.get("crb_6m") or cap1.get("filtro_riesgo", {}).get("crb_6m")
        return isinstance(crb, (int, float)) and crb > 0
    if clave == "geopolitica":
        # proxy: energia sube fuerte junto con riesgo de suministro
        uso = cap2.get("xle_wtic", {}).get("uso_6m") if contexto and "cap2" in contexto else None
        return uso is not None and uso > 20
    if clave == "dolar":
        return (cap3.get("riesgo", {}).get("dxy_6m") or 0) > 0
    if clave == "inflacion":
        crb = cap12.get("crb_6m") or cap1.get("filtro_riesgo", {}).get("crb_6m")
        return isinstance(crb, (int, float)) and crb > 5
    if clave == "consumidor":
        return cap13.get("ciclicos_vs_staples", {}).get("xly_xlp_slope200") is not None
    if clave == "vix":
        return (cap3.get("riesgo", {}).get("vix") or 99) < 20
    return None


def _temas_de(df, tickers):
    sub = df[df["ticker"].isin(tickers)]
    temas_tot = []
    for v in sub["temas"]:
        temas_tot.extend((v or "").split(",") if v else [])
    return pd.Series(temas_tot).value_counts().to_dict() if temas_tot else {}


def verificar_regimen(df, contexto):
    """Cruza las reclamaciones del regimen contra los temas noticiosos."""
    rows = []
    for c in CLAIMS:
        estado = _claim_estado(c["clave"], contexto)
        if estado is None:
            rows.append({"claim": c["claim"], "activo": "n/a", "veredicto": "sin dato de regimen",
                         "temas_observados": ""})
            continue
        # tickers de la dimension relacionada o todos
        dims = set()
        for t in c["esperado"]:
            dims.update([d["ticker"] for d in DRIVERS if d["dimension"] == t])
        temas_obs = _temas_de(df, list(dims) if dims else df["ticker"].unique().tolist())
        tiene_esperados = any(temas_obs.get(t, 0) > 0 for t in c["esperado"])
        tiene_opuestos = any(temas_obs.get(t, 0) > 0 for t in c["opuesto"])
        if not estado:
            veredicto = "regimen NO activo (sin tension)"
        elif tiene_esperados and not tiene_opuestos:
            veredicto = "CONFIRMA el analisis"
        elif tiene_esperados and tiene_opuestos:
            veredicto = "mixto (hay temas de apoyo y de oposicion)"
        else:
            veredicto = "sin evidencia noticiosa directa"
        rows.append({
            "claim": c["claim"],
            "activo": "SI" if estado else "NO",
            "veredicto": veredicto,
            "temas_observados": ", ".join(sorted(temas_obs, key=lambda k: -temas_obs[k])[:4]),
        })
    return pd.DataFrame(rows)


def interpretar_ciclo(df, contexto):
    """Lineas de interpretacion que conectan noticias con el regimen de Murphy."""
    lines = []
    temas_tot = {}
    for v in df["temas"]:
        for t in (v or "").split(","):
            if t:
                temas_tot[t] = temas_tot.get(t, 0) + 1
    dominantes = sorted(temas_tot, key=lambda k: -temas_tot[k])[:4]
    if dominantes:
        lines.append("Narrativa dominante: %s." % ", ".join(dominantes))
    cap12 = contexto.get("cap12", {}).get("resultados", {}) if contexto else {}
    etapa = cap12.get("etapa_pring", "n/a")
    if etapa and "Stage 4" in str(etapa):
        lines.append("El motor marca **%s**: bonos caen mientras acciones y commodities suben. "
                     "Las noticias de energia (%s) y tasas (%s) son las que sostienen esa lectura reflacionaria."
                     % (etapa, temas_tot.get("energia", 0), temas_tot.get("tasas", 0)))
    if temas_tot.get("geopolitica", 0):
        lines.append("Temas geopoliticos (%d noticias) dan contexto al alza de energia/oro: el shock es de "
                     "oferta (stagflation), no un boom de demanda clasico." % temas_tot["geopolitica"])
    if temas_tot.get("oro", 0):
        dxy = pct_6m("DX-Y.NYB")
        lines.append("El oro aparece %d veces; con DXY %s%% y oro subiendo por miedo, la relacion "
                     "dolar->oro del motor (correlacion negativa) queda en tension." % (temas_tot["oro"],
                                                                                       ("%+.1f" % dxy) if dxy is not None else "n/a"))
    return lines


def generar_reporte(df, contexto, md_path="NOTICIAS_CICLO.md", json_path=None):
    fecha = datetime.now().strftime("%Y-%m-%d")

    coh = verificar_regimen(df, contexto)
    interp = interpretar_ciclo(df, contexto)

    if df.empty:
        md = ["# Noticias del ciclo intermarket",
              "**Fecha:** %s  |  *No se encontraron noticias (o fallo la descarga).*" % fecha,
              "", "> El paso de noticias no aporto informacion. Posibles causas: rate-limiting de Yahoo u offline."]
        texto = "\n".join(md)
        if json_path:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"fecha": fecha, "drivers": [], "coherencia": [], "interpretacion": []},
                          f, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(texto)
        return texto

    agg = []
    for drv in DRIVERS:
        tk = drv["ticker"]
        sub = df[df["ticker"] == tk]
        precio = pct_6m(tk)
        agg.append({
            "ticker": tk,
            "nombre": drv["nombre"],
            "dimension": drv["dimension"],
            "precio_6m": precio,
            "noticias": len(sub),
            "score_neto": int(sub["sentimiento"].sum()) if len(sub) else 0,
            "temas": sorted(_temas_de(df, [tk]), key=lambda k: -_temas_de(df, [tk])[k])[:3],
        })
    agg_df = pd.DataFrame(agg)

    md = ["# Noticias del ciclo intermarket — verificacion", "**Fecha:** %s  |  **Fuente:** yfinance Ticker.news" % fecha, ""]
    md.append("## 1. Drivers del ciclo (%d noticias)" % len(df))
    tabla = agg_df.rename(columns={"ticker": "ticker", "nombre": "driver", "dimension": "dim",
                                   "precio_6m": "precio_6m%", "noticias": "n", "score_neto": "score"})
    for c in tabla.columns:
        if c == "precio_6m%":
            tabla[c] = tabla[c].map(lambda v: ("%+.1f" % v) if isinstance(v, (int, float)) else "n/a")
    md.append(tabla.to_markdown(index=False))
    md.append("")
    md.append("Legenda: `precio_6m%` retorno a 6m del driver; `score` suma de sentimiento (+1/=1); `temas` principales.")
    md.append("")
    md.append("## 2. Coherencia noticias vs regimen del motor")
    md.append(coh.to_markdown(index=False))
    md.append("")
    md.append("## 3. Interpretacion")
    if interp:
        md.append("\n".join("> %s" % l for l in interp))
    else:
        md.append("> Sin interpretacion automatica disponible.")
    md.append("")
    md.append("## 4. Titulares recientes")
    top = df.sort_values("fecha", ascending=False).head(25)
    for _, r in top.iterrows():
        md.append("- **[%s]** %s (%s) — %s" % (r["ticker"], r["titulo"], r["fecha"] or "?", r["fuente"] or "?"))
        if r["resumen"]:
            md.append("    %s" % r["resumen"][:220])

    texto = "\n".join(md)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(texto)

    if json_path:
        payload = {
            "fecha": fecha,
            "fuente": "yfinance Ticker.news",
            "drivers": agg_df.to_dict("records"),
            "coherencia": coh.to_dict("records"),
            "interpretacion": interp,
            "titulares": df[["ticker", "fecha", "titulo", "resumen", "fuente", "sentimiento", "temas"]]
                .sort_values("fecha", ascending=False).head(50).to_dict("records"),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return texto


def main():
    parser = argparse.ArgumentParser(description="Noticias del ciclo intermarket")
    parser.add_argument("--contexto", type=str, default=None,
                        help="JSON de contexto Murphy para verificar el regimen")
    parser.add_argument("--max-items", type=int, default=10,
                        help="Maximo de noticias por ticker")
    parser.add_argument("--out", type=str, default="NOTICIAS_CICLO.md")
    parser.add_argument("--json", type=str, default="noticias_ciclo.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    contexto = None
    if args.contexto and os.path.exists(args.contexto):
        with open(args.contexto, encoding="utf-8") as f:
            contexto = json.load(f)

    if args.verbose:
        for drv in DRIVERS:
            print("[+] Noticias %-10s ..." % drv["ticker"])
    df = analizar_drivers(max_items=args.max_items)

    texto = generar_reporte(df, contexto, md_path=args.out, json_path=args.json)
    print(texto)
    print("\nGuardado en %s y %s" % (args.out, args.json))


if __name__ == "__main__":
    main()