# -*- coding: utf-8 -*-
"""Wrapper de las 28 señales A/B (analisis.ejecutivo.senales) + detección de cambios."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analisis.ejecutivo.senales import generar_tabla, TABLA


def obtener_senales(periodo="4y", verbose=False):
    return generar_tabla(periodo=periodo)


def detectar_cambios(df_actual, df_previo):
    """Compara dos DataFrames de señales por columna 'regla_oro'/'accion'."""
    if df_previo is None or df_previo.empty:
        return [(r["id"], None, r["regla_oro"]) for _, r in df_actual.iterrows()]
    prev = df_previo.set_index("id")[["regla_oro", "accion"]].to_dict("index")
    cambios = []
    for _, r in df_actual.iterrows():
        p = prev.get(r["id"])
        if p is None or p["regla_oro"] != r["regla_oro"] or p["accion"] != r["accion"]:
            cambios.append((r["id"], p["regla_oro"] if p else None, r["regla_oro"]))
    return cambios


def formatear_senal(row):
    return "%s %s (%s/%s) → %s | %s" % (
        row["id"], row["ratio"], row["A"], row["B"],
        row["regla_oro"], row["accion"]
    )
