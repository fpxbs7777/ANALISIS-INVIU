# -*- coding: utf-8 -*-
"""motor.02_validacion_r2: valida el universo de tickers de un sector/industria
contra su ETF o indice asociado.

Paso 2 del analisis diario. Para cada sector/industria favorecida (según el
contexto Murphy o una lista manual):
    1. Obtiene de `unificado_completo - copia.json` el ETF/indice asociado
       (del campo `etfs` del sector, o del catalogo `etfs.porCategoria`,
       o del mapeo SPDR de sectores).
    2. Arma la lista universo completa de tickers de ese sector/industria
       (normalizando .BA / sufijos D a su subyacente en yfinance).
    3. Descarga 1 año de cierres del benchmark y de cada ticker, y calcula
       el R² de los retornos diarios contra el benchmark.
    4. Clasifica: R² alto = el ticker "valida" la tesis sectorial; R² bajo
       = no acompaña al sector (puede estar desalineado).

Uso:
    python motor/02_validacion_r2.py
    python motor/02_validacion_r2.py --sectores Energía,Tecnología --industrias Semiconductores
    python motor/02_validacion_r2.py --contexto contexto_murphy_2026-08-16.json --top 3
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.data import load, pd_clean
from analisis.portafolio.constructor import ETF_A_SECTOR, SECTOR_A_ETF, descargar_precios

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cache")

# Mapeo industria (por palabra clave, sin acentos/minusculas) -> ETF/indice
# Solo sub-industrias con ETF especifico bien definido; si no matchea,
# el benchmark cae al ETF del sector (fallback correcto en la mayoria).
INDUSTRIA_A_ETF = [
    (["semiconductor"], "SMH"),
    (["software"], "IGV"),
    (["internet content", "internet"], "XLC"),
    (["hardware", "equipo de comunicacion", "communication equipment",
      "electronic component", "componentes electronicos", "electronica de consumo",
      "consumer electronics", "hardware de computadora"], "XLK"),
    (["telecomunication", "telecomunicacion", "telecom services"], "XLC"),
    (["entretenimiento", "entertainment", "juegos", "gaming"], "XLC"),
    (["bancos", "bank"], "KBE"),
    (["seguros", "insurance"], "KIE"),
    (["biotecnologia", "biotech", "biotechnology"], "XBI"),
    (["farmac", "drug manufacturers", "pharma", "medicamentos"], "XLV"),
    (["dispositivos medicos", "medical devices"], "XLV"),
    (["salud", "healthcare", "health care", "salud"], "XLV"),
    (["petroleo", "petr", "oil"], "XLE"),
    (["uranio", "uranium"], "URA"),
    (["oro", "gold"], "GDX"),
    (["plata", "silver"], "SLV"),
    (["cobre", "copper"], "COPX"),
    (["acero", "steel"], "SLX"),
    (["aluminio", "aluminum"], "XLB"),
    (["quimic", "chemical"], "XLB"),
    (["mineria", "mining", "metal"], "XLB"),
    (["material"], "XLB"),
    (["inmobiliar", "real estate", "reit"], "XLRE"),
    (["transporte", "transport", "logistica", "logistic"], "IYT"),
    (["ferrocarril", "rail"], "IYT"),
    (["aerolinea", "airline"], "JETS"),
    (["aerospaci", "aeroespaci", "defensa", "defense"], "ITA"),
    (["electrical", "electrico", "electricos", "repuestos electricos"], "XLI"),
    (["util", "utility", "electricid"], "XLU"),
    (["solar"], "TAN"),
    (["industrial", "maquinaria", "machinery", "equipo", "equipment"], "XLI"),
    (["construccion", "construction", "homebuild", "viviend"], "XHB"),
]

# Umbrales de R2 por defecto
R2_ALTO = 0.6
R2_MEDIO = 0.4


def cargar_unificado(path="unificado_completo - copia.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalizar(texto):
    """Minusculas y sin acentos para matchear nombres."""
    if not texto:
        return ""
    t = texto.lower()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n")]:
        t = t.replace(a, b)
    return t


def etf_sector(unificado, sector):
    """ETF asociado a un sector: primero del campo `etfs` del JSON, luego catalogo SPDR."""
    data = unificado.get("sectores", {}).get(sector, {})
    etfs = data.get("etfs") or []
    if etfs:
        return etfs[0] if isinstance(etfs[0], str) else etfs[0].get("ticker")
    return SECTOR_A_ETF.get(sector)


def etf_industria(nombre_industria, etf_sector_default):
    """ETF asociado a una industria por palabra clave; fallback al ETF del sector."""
    n = normalizar(nombre_industria)
    for keywords, etf in INDUSTRIA_A_ETF:
        if any(k in n for k in keywords):
            return etf
    return etf_sector_default


def ticker_yf(activo):
    """Normaliza el ticker del JSON a un simbolo descargable en yfinance.

    - "AAPL.BA" (cedear) -> "AAPL" (subyacente USD)
    - "AAPLD" (cedear USD) -> "AAPL"
    - "PAMP.BA" (accion local Argentina) -> "PAMP.BA"
    """
    t = (activo.get("ticker") or "").strip()
    if not t:
        return None
    tipo = (activo.get("tipo") or "").lower()
    moneda = (activo.get("moneda") or "").upper()
    if t.endswith(".BA"):
        base = t[:-3]
        if tipo == "accion":
            return t  # accion local de BCBA (PAMP.BA)
        return base  # cedear de BCBA -> subyacente USD
    if moneda == "USD" and tipo == "cedear" and len(t) > 1 and t.endswith("D"):
        return t[:-1]
    return t


def universo_tickers(unificado, sector, industria=None):
    """Lista de activos (dicts) de un sector, opcionalmente filtrando por industria."""
    industrias = unificado.get("sectores", {}).get(sector, {}).get("industrias", {})
    if industria:
        if industria in industrias:
            return industrias[industria]
        n = normalizar(industria)
        for ind, activos in industrias.items():
            if n in normalizar(ind):
                return activos
        return []
    out = []
    for activos in industrias.values():
        out.extend(activos)
    return out


def r2_vs_benchmark(serie_tk, serie_bench, min_n=30):
    """R2 = corr^2 de los retornos diarios de ticker vs benchmark."""
    if serie_tk is None or serie_bench is None:
        return None
    a = pd_clean(serie_tk).rename("a")
    b = pd_clean(serie_bench).rename("b")
    df = pd.concat([a, b], axis=1, sort=False).dropna()
    if len(df) < min_n:
        return None
    ret = df.pct_change().dropna()
    if len(ret) < min_n:
        return None
    corr = ret["a"].corr(ret["b"])
    if corr != corr:
        return None
    r2 = corr ** 2
    beta = ret["a"].cov(ret["b"]) / ret["b"].var()
    return {"r2": r2, "corr": corr, "beta": beta, "n": len(ret)}


def clasificar(r2):
    if r2 >= R2_ALTO:
        return "VALIDA"
    if r2 >= R2_MEDIO:
        return "PARCIAL"
    return "NO VALIDA"


def sectores_favorecidos(contexto, top=3, unificado=None):
    """Sectores favorecidos segun el contexto (cap13, lideres 200d)."""
    cap13 = contexto.get("cap13", {}).get("resultados", {})
    ranking = cap13.get("liderazgo_sectorial_200d", {})
    etfs_lideres = list(ranking.keys())[:top]
    sectores = [ETF_A_SECTOR.get(etf) for etf in etfs_lideres if ETF_A_SECTOR.get(etf)]
    return sectores


def _series(tk, periodo):
    """Serie de cierre para yfinance con cache+reintentos; None si falla."""
    try:
        return load(tk, period=periodo, use_cache=True)
    except Exception:
        return None


def _cache_path(tk, periodo):
    return os.path.join(_CACHE_DIR, "%s_%s.csv" % (tk.replace("^", "_"), periodo))


def _cache_descargar(tickers, periodo="1y", chunk=40, verbose=False):
    """Descarga en lotes y escribe al cache de core.data (evita rate-limit de Yahoo).

    Luego load(tk) lee del cache, evitando descargas una a una (lentas).
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    faltantes = [t for t in tickers if not (t and os.path.exists(_cache_path(t, periodo)))]
    for i in range(0, len(faltantes), chunk):
        grupo = faltantes[i:i + chunk]
        if verbose:
            print("    lote %d-%d/%d..." % (i + 1, i + len(grupo), len(faltantes)))
        prices = descargar_precios(grupo, period=periodo, verbose=False)
        for t, s in prices.items():
            try:
                s = pd_clean(s)
                pd.DataFrame({"Close": s}).to_csv(_cache_path(t, periodo))
            except Exception:
                pass
    return len(faltantes)


def validar_sectores(unificado, sectores, industrias_filtro=None, periodo="1y", verbose=False):
    """Valida el universo de cada sector/industria contra su benchmark. Devuelve DataFrame filas + resumen."""
    filas = []
    for sector in sectores:
        bench_default = etf_sector(unificado, sector)
        if not bench_default:
            if verbose:
                print("  [sin benchmark] %s" % sector)
            continue
        industrias = unificado.get("sectores", {}).get(sector, {}).get("industrias", {})
        industrias_a_validar = []
        if industrias_filtro:
            for f in industrias_filtro:
                n = normalizar(f)
                for ind in industrias:
                    if n in normalizar(ind):
                        industrias_a_validar.append(ind)
        else:
            industrias_a_validar = list(industrias.keys())

        if not industrias_a_validar:
            continue

        # pre-cargar en lotes todo el universo del sector (una vez, cacheado)
        tickers_sector = set()
        for ind in industrias_a_validar:
            for a in universo_tickers(unificado, sector, ind):
                t = ticker_yf(a)
                if t:
                    tickers_sector.add(t)
        for ind in industrias_a_validar:
            tickers_sector.add(etf_industria(ind, bench_default))
        if verbose:
            print("[+] Pre-descargando %d tickers de %s (%s)..." % (len(tickers_sector), sector, periodo))
        _cache_descargar(list(tickers_sector), periodo=periodo, verbose=verbose)

        for ind in industrias_a_validar:
            # benchmark por industria: ETF especifico si matchea, si no el del sector
            bench = etf_industria(ind, bench_default)
            if verbose:
                print("[+] %s / %s contra %s..." % (sector, ind, bench))
            bench_serie = _series(bench, periodo)
            if bench_serie is None:
                if verbose:
                    print("  [sin datos benchmark %s]" % bench)
                continue
            for a in universo_tickers(unificado, sector, ind):
                t = ticker_yf(a)
                if not t:
                    continue
                serie = _series(t, periodo)
                res = r2_vs_benchmark(serie, bench_serie)
                if res is None:
                    filas.append({
                        "sector": sector, "industria": ind, "benchmark": bench,
                        "ticker": a.get("ticker"), "nombre": a.get("nombre", ""),
                        "yf": t, "r2": None, "corr": None, "beta": None, "n": 0,
                        "veredicto": "SIN DATOS",
                    })
                    continue
                filas.append({
                    "sector": sector, "industria": ind, "benchmark": bench,
                    "ticker": a.get("ticker"), "nombre": a.get("nombre", ""),
                    "yf": t, "r2": round(res["r2"], 3), "corr": round(res["corr"], 3),
                    "beta": round(res["beta"], 3), "n": res["n"],
                    "veredicto": clasificar(res["r2"]),
                })

    df = pd.DataFrame(filas)
    if df.empty:
        return df, pd.DataFrame()

    # dedup: mismo simbolo yfinance dentro del mismo sector/industria
    df = df.sort_values(["sector", "industria", "yf", "r2"], ascending=[True, True, True, False])
    df = df.drop_duplicates(subset=["sector", "industria", "yf"], keep="first")

    resumen = []
    for (sector, ind, bench), g in df.groupby(["sector", "industria", "benchmark"]):
        g_validos = g[g["r2"].notna()]
        if g_validos.empty:
            continue
        n_tot = len(g_validos)
        n_valida = int((g_validos["veredicto"] == "VALIDA").sum())
        n_parcial = int((g_validos["veredicto"] == "PARCIAL").sum())
        n_no = n_tot - n_valida - n_parcial
        resumen.append({
            "sector": sector, "industria": ind, "benchmark": bench,
            "n_universo": n_tot, "n_valida": n_valida, "n_parcial": n_parcial,
            "n_no": n_no, "pct_valida": round(100 * n_valida / n_tot, 1),
            "r2_mediana": round(float(g_validos["r2"].median()), 3),
        })
    res = pd.DataFrame(resumen)
    return df, res


def generar_reporte(df, resumen, out_path="VALIDACION_R2.md", json_path="validacion_r2.json"):
    fecha = datetime.now().strftime("%Y-%m-%d")
    md = ["# Validacion R2 de Universo vs Benchmark de Sector", "**Fecha:** %s" % fecha, ""]
    md.append("> R2 de retornos diarios (1y) de cada ticker del universo contra el ETF/indice asociado.")
    md.append("> `VALIDA` >= %.1f | `PARCIAL` >= %.1f | `NO VALIDA` < %.1f." % (R2_ALTO, R2_MEDIO, R2_MEDIO))
    md.append("")
    md.append("## Resumen por sector / industria")
    if resumen.empty:
        md.append("*Sin datos.*")
    else:
        md.append(resumen.to_markdown(index=False))
    md.append("")
    md.append("## Detalle por ticker")
    if df.empty:
        md.append("*Sin datos.*")
    else:
        cols = [c for c in ["sector", "industria", "benchmark", "ticker", "nombre", "yf",
                            "r2", "corr", "beta", "n", "veredicto"] if c in df.columns]
        md.append(df.sort_values(["sector", "veredicto", "r2"], ascending=[True, False, False])[cols].to_markdown(index=False))
    texto = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(texto)
    payload = {
        "fecha": fecha,
        "umbrales": {"alto": R2_ALTO, "medio": R2_MEDIO},
        "resumen": resumen.to_dict("records") if not resumen.empty else [],
        "detalle": df.to_dict("records") if not df.empty else [],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return texto


def main():
    parser = argparse.ArgumentParser(description="Paso 2: validacion R2 del universo vs ETF/indice")
    parser.add_argument("--contexto", default=None, help="JSON de contexto Murphy para derivar sectores")
    parser.add_argument("--unificado", default="unificado_completo - copia.json")
    parser.add_argument("--sectores", default=None, help="Sectores separados por coma (sobreescribe contexto)")
    parser.add_argument("--industrias", default=None, help="Industrias separadas por coma (filtro)")
    parser.add_argument("--top", type=int, default=3, help="Top N sectores lideres del contexto")
    parser.add_argument("--periodo", default="1y", help="Ventana de datos (6mo,1y,2y)")
    parser.add_argument("--out", default="VALIDACION_R2.md")
    parser.add_argument("--json", default="validacion_r2.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    unificado = cargar_unificado(args.unificado)

    sectores = None
    if args.sectores:
        sectores = [s.strip() for s in args.sectores.split(",") if s.strip()]
        # aceptar tickers de ETF (XLE -> Energia)
        sectores = [ETF_A_SECTOR.get(s, s) for s in sectores]
    elif args.contexto and os.path.exists(args.contexto):
        with open(args.contexto, encoding="utf-8") as f:
            contexto = json.load(f)
        sectores = sectores_favorecidos(contexto, top=args.top, unificado=unificado)
        if args.verbose:
            print("Sectores favorecidos del contexto:", sectores)
    if not sectores:
        print("[!] Indica --sectores o --contexto (contexto_murphy_<fecha>.json).")
        print("    Ej: python motor/02_validacion_r2.py --contexto contexto_murphy_%s.json"
              % datetime.now().strftime("%Y-%m-%d"))
        sys.exit(1)

    industrias = None
    if args.industrias:
        industrias = [i.strip() for i in args.industrias.split(",") if i.strip()]

    if args.verbose:
        print("Sectores a validar:", sectores)
    df, resumen = validar_sectores(unificado, sectores, industrias_filtro=industrias,
                                   periodo=args.periodo, verbose=args.verbose)
    texto = generar_reporte(df, resumen, out_path=args.out, json_path=args.json)
    print(texto)
    print("\nGuardado en %s y %s" % (args.out, args.json))


if __name__ == "__main__":
    main()
