# -*- coding: utf-8 -*-
"""Informe MD + JSON por corrida."""
import json
import os
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))


def escribir(resultado, nombre="informe"):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    path_md = os.path.join(BASE, "informes", "%s_%s.md" % (nombre, ts))
    path_json = os.path.join(BASE, "resultados", "backtests", "%s_%s.json" % (nombre, ts))
    os.makedirs(os.path.dirname(path_md), exist_ok=True)
    os.makedirs(os.path.dirname(path_json), exist_ok=True)

    md = []
    md.append("# Informe Portafolio Cuantitativo — %s" % ts)
    md.append("Generado: %s" % datetime.now().strftime("%d/%m/%Y %H:%M"))
    md.append("")
    if "universo" in resultado:
        u = resultado["universo"]
        md.append("## Universo Tier %s: ARG %d + CEDEAR %d = %d tickers" % (
            u.get("tier", "?"), u.get("n_arg", 0), u.get("n_cedear", 0), u.get("n_total", 0)))
    if "ciclo" in resultado:
        c = resultado["ciclo"]
        md.append("## Ciclo intermarket: %s (conf %s)" % (c.get("fase"), c.get("conf")))
        if c.get("raw") and c["raw"].get("fase"):
            md.append("> %s" % c["raw"]["fase"].get("desc", ""))
    if "salud" in resultado and resultado["salud"] is not None:
        df = resultado["salud"]
        try:
            md.append("## Top sanas (hibrido 50/50)")
            md.append(df.head(12).to_string(index=False))
        except Exception:
            pass
    if "factores" in resultado and resultado["factores"] is not None:
        df = resultado["factores"]
        if not df.empty:
            md.append("## Alta R2 por factor (predictibles)")
            md.append(df.head(15).to_string(index=False))
    if "regimen" in resultado:
        r = resultado["regimen"]
        md.append("## Motor de analogos (periodos donde las condiciones se repitieron)")
        for h, met in r.get("evaluacion", {}).items():
            md.append("- Horizonte %sd: win-rate %.0f%% (n=%d, ret medio %+.2f%%)" % (
                h, met["win_rate"] * 100, met["n"], met["ret_medio"] * 100))
        if r.get("analogos_n"):
            md.append("- Analogos encontrados: %d (dist umbral %.1f)" % (r["analogos_n"], r.get("dist_umbral", 0)))
    if "backtest" in resultado:
        bt = resultado["backtest"]
        md.append("## Backtest walk-forward 2018+")
        md.append("- Win-rate por entrada: %.0f%% (n=%d)" % (
            (bt.get("win_rate", 0) * 100) if bt.get("win_rate") is not None else 0,
            bt.get("n_trades", 0)))
        if bt.get("equity") is not None and hasattr(bt["equity"], "empty") and not bt["equity"].empty:
            eq = bt["equity"]
            cagr = (eq["equity"].iloc[-1] ** (252 / len(eq)) - 1) if len(eq) > 0 else 0
            md.append("- CAGR aprox: %+.1f%%" % (cagr * 100))
    md.append("")
    md.append("> Sistema cuantitativo unificado — informativo, no recomendacion.")
    texto = "\n".join(md)
    open(path_md, "w", encoding="utf-8").write(texto)
    json.dump({k: (v.to_dict() if hasattr(v, "to_dict") else str(v)[:500])
               for k, v in resultado.items()},
              open(path_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path_md, path_json, texto
