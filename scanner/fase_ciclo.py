# -*- coding: utf-8 -*-
"""Fase Pring (cap12) + liderazgo sectorial 200d (cap13) — ejecución liviana (solo 2 caps)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CONTEXTO_FALLBACK = os.path.join(ROOT, "contexto_actual.json")


def obtener_fase(usar_json=False, periodo="6y", verbose=True):
    if not usar_json:
        try:
            from analisis.ejecutivo.diario import MurphyDaily
            if verbose:
                print("  MurphyDaily cap12+cap13...")
            ctx = MurphyDaily(periodo=periodo, verbose=False).run(nombres=["12", "13"])
            lid = ctx["cap13"]["resultados"]["liderazgo_sectorial_200d"]
            etapa = ctx.get("cap12", {}).get("resultados", {}).get("etapa_pring", "N/D")
            return dict(lid), etapa, "MurphyDaily %s" % ctx.get("fecha"), ctx
        except Exception as e:
            if verbose:
                print("  ! MurphyDaily fallo (%s); fallback JSON" % e)
    with open(CONTEXTO_FALLBACK, encoding="utf-8") as f:
        ctx = json.load(f)
    lid = ctx["cap13"]["resultados"]["liderazgo_sectorial_200d"]
    etapa = ctx.get("cap12", {}).get("resultados", {}).get("etapa_pring", "N/D")
    return dict(lid), etapa, "contexto_actual.json %s" % ctx.get("fecha"), ctx


def formatear_fase(liderazgo, etapa):
    orden = sorted(liderazgo.items(), key=lambda kv: kv[1], reverse=True)
    lineas = ["*Fase:* %s" % etapa]
    for etf, slope in orden[:5]:
        lineas.append("`%s` %+5.1f" % (etf, slope))
    return "\n".join(lineas)
