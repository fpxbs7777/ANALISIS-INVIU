# -*- coding: utf-8 -*-
"""Alertas macro extraídas del contexto Murphy (caps 2,3,7)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def evaluar_alertas(ctx):
    """Devuelve dict {clave: (activo:bool, detalle:str)}."""
    out = {}
    try:
        out["curva_invertida"] = (
            bool(ctx.get("cap7", {}).get("resultados", {}).get("curva_invertida", {}).get("invertida", False)),
            "cap7.curva_invertida"
        )
    except Exception:
        out["curva_invertida"] = (False, "—")
    try:
        out["shock_1994"] = (
            bool(ctx.get("cap3", {}).get("resultados", {}).get("shock_tasas", {}).get("alerta_1994", False)),
            "cap3.shock_tasas.alerta_1994"
        )
    except Exception:
        out["shock_1994"] = (False, "—")
    try:
        out["divergencia_bonos_comm"] = (
            bool(ctx.get("cap2", {}).get("resultados", {}).get("divergencia_bonos_comm", {}).get("alerta", False)),
            "cap2.divergencia_bonos_comm"
        )
    except Exception:
        out["divergencia_bonos_comm"] = (False, "—")
    try:
        c2 = ctx.get("cap2", {}).get("resultados", {})
        out["clima_deflacionario"] = (bool(c2.get("clima_deflacionario", {}).get("activo", False)), "cap8/9 clima")
    except Exception:
        out["clima_deflacionario"] = (False, "—")
    return out


def formatear_alertas(alertas):
    lineas = []
    for k, (activo, det) in alertas.items():
        lineas.append("%s %s (%s)" % ("🔴" if activo else "🟢", k, det))
    return "\n".join(lineas)
