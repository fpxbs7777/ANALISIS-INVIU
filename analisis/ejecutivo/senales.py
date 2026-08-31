# -*- coding: utf-8 -*-
"""Senales de auditoria para el runner diario (migrado de generar_senales.py).

Genera senales_auditoria.csv / senales_auditoria.json en la raiz usando
exclusivamente core + core.ratio + core.senales (sin codigo residual).

Uso normal (lo invoca run_all.py):
    python -m analisis.ejecutivo.senales
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd

from core.data import load
from core.ratio import absolute_stats, analyze_pair, WINS
from core.senales import regla_oro, accion

# (id, nombre, A, B, nivel). B=None -> nivel absoluto (DXY, TNX, VIX)
TABLA = [
    ("MAC1", "DXY (DOP)",          "DX-Y.NYB", None,       "M1 motor"),
    ("MAC2", "TNX 10Y",            "^TNX",     None,       "M1 costo dinero"),
    ("MAC3", "Curva IRX/TNX",      "^IRX",     "^TNX",     "M1 fase ciclo"),
    ("MAC4", "VIX",                "^VIX",     None,       "M1 miedo"),
    ("MAC5", "CRB/TLT inflacion",  "^SPGSCI",  "TLT",      "M1 inflacion"),
    ("MAC6", "GLD/DXY",            "GLD",      "DX-Y.NYB", "M1 confirma dolar"),
    ("AA1",  "SPY/TLT",            "SPY",      "TLT",      "M2 asset allocation"),
    ("AA2",  "SPY/GLD",            "SPY",      "GLD",      "M2 risk on/off"),
    ("S1",   "XLE/SPY",            "XLE",      "SPY",      "S3 Energia"),
    ("S2",   "XLY/SPY",            "XLY",      "SPY",      "S3 Discrecional"),
    ("S3",   "XLC/SPY",            "XLC",      "SPY",      "S3 Comunicacion"),
    ("S4",   "XLB/SPY",            "XLB",      "SPY",      "S3 Materiales"),
    ("S5",   "XLK/SPY",            "XLK",      "SPY",      "S3 Tecnologia"),
    ("I1",   "SMH/XLK",            "SMH",      "XLK",      "I4 Semis"),
    ("I2",   "LIT/XLB",            "LIT",      "XLB",      "I4 Litio"),
    ("I3",   "URA/XLE",            "URA",      "XLE",      "I4 Uranio"),
    ("I4",   "URA/XLU",            "URA",      "XLU",      "I4 Uranio-util"),
    ("A1",   "NVDA/SMH",           "NVDA",     "SMH",      "A5 Activo"),
    ("A2",   "TSM/SMH",            "TSM",      "SMH",      "A5 Activo"),
    ("A3",   "MP/LIT",             "MP",       "LIT",      "A5 Activo"),
    ("A4",   "AMZN/XLY",           "AMZN",     "XLY",      "A5 Activo"),
    ("A5",   "GOOGL/XLC",          "GOOGL",    "XLC",      "A5 Activo"),
    ("LOC1", "PAMP/MERV",          "PAMP.BA",  "^MERV",    "A5 Local"),
    ("LOC2", "ARGT/EEM",           "ARGT",     "EEM",      "S3 Pais"),
    ("LOC3", "MERV/EEM",           "^MERV",    "EEM",      "S3 Pais ctx"),
    ("EXT1", "USO/XLE",            "USO",      "XLE",      "P6 PAMP petroleo"),
    ("EXT2", "FXI/SPY",            "FXI",      "SPY",      "P6 geopolitica"),
    ("EXT3", "EWY/SPY",            "EWY",      "SPY",      "P6 Asia TSM"),
    ("EXT4", "N225/SPY",           "^N225",    "SPY",      "P6 Asia TSM"),
]


def generar_tabla(periodo="4y"):
    """Descarga, calcula y devuelve el DataFrame completo de senales."""
    tks = set()
    for _, _, a, b, _ in TABLA:
        tks.add(a)
        if b:
            tks.add(b)
    print("Descargando %d tickers (%s)..." % (len(tks), periodo))
    data = {}
    for tk in sorted(tks):
        try:
            data[tk] = load(tk, period=periodo)
        except Exception as e:
            print("fallo", tk, e)

    rows = []
    for tid, name, a, b, nivel in TABLA:
        pa, pb = data.get(a), data.get(b)
        if pa is None or (b and pb is None):
            rows.append(dict(id=tid, ratio=name, nivel=nivel, A=a, B=b or "-",
                             ok=False, regla_oro="SIN DATOS", accion="-"))
            continue
        if b is None:
            st = absolute_stats(pa)
            base = dict(id=tid, ratio=name, nivel=nivel, A=a, B="-", ok=True, last=float(pa.iloc[-1]))
        else:
            _, st = analyze_pair(pa, pb)
            base = dict(id=tid, ratio=name, nivel=nivel, A=a, B=b, ok=True, last=st.get(120, {}).get("last"))
        for w in WINS:
            s = st.get(w)
            if s:
                base["z%d" % w] = round(s["z"], 2)
                base["pct%d" % w] = round(s["pct"], 1)
                base["pend%d" % w] = round(s["slope"], 1)
                base["corr%d" % w] = s.get("corr", float("nan"))
                base["beta%d" % w] = s.get("beta", float("nan"))
        ro = regla_oro(st)
        base["regla_oro"] = ro
        base["accion"] = accion(ro, st)
        rows.append(base)

    df = pd.DataFrame(rows).fillna("")
    return df


def guardar(df):
    df.to_csv("senales_auditoria.csv", index=False)
    df.to_json("senales_auditoria.json", orient="records", indent=2)


def imprimir(df):
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 280)
    cols = ["id", "ratio", "nivel", "last", "corr120", "corr365", "beta120",
            "z120", "z365", "pct120", "pct365", "pend50", "pend120", "pend200", "pend365",
            "regla_oro", "accion"]
    print(df[cols].to_string(index=False))


def main():
    df = generar_tabla()
    guardar(df)
    imprimir(df)
    print("\nArchivos: senales_auditoria.csv / senales_auditoria.json")


if __name__ == "__main__":
    main()