# -*- coding: utf-8 -*-
"""motor.01_intermarket: determina la fase del ciclo intermarket (Murphy).

Paso 1 del analisis diario. Descarga las series de los 15 capitulos,
corre las senales de auditoria (senales_auditoria.csv/json) y genera:
    - contexto_murphy_<fecha>.json  (15 capitulos)
    - FASE_INTERMARKET.md           (resumen de la fase del ciclo)

Uso:
    python motor/01_intermarket.py
    python motor/01_intermarket.py --periodo 6y --json contexto_murphy_2026-08-16.json
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from analisis.ejecutivo import senales
from analisis.ejecutivo.diario import MurphyDaily
from analisis.portafolio.constructor import ETF_A_SECTOR


def resumir_fase(contexto, df_senales):
    """Devuelve dict con el resumen de la fase del ciclo."""
    cap12 = contexto.get("cap12", {}).get("resultados", {})
    cap1 = contexto.get("cap1", {}).get("resultados", {})
    cap3 = contexto.get("cap3", {}).get("resultados", {})
    cap4 = contexto.get("cap4", {}).get("resultados", {})
    cap13 = contexto.get("cap13", {}).get("resultados", {})

    ranking = cap13.get("liderazgo_sectorial_200d", {})
    lideres = [ETF_A_SECTOR.get(etf, etf) for etf in list(ranking.keys())[:3]]

    n_alc = int((df_senales["regla_oro"].astype(str).str.contains("ALCISTA")).sum())
    n_baj = int((df_senales["regla_oro"].astype(str).str.contains("BAJISTA")).sum())
    n_cam = int((df_senales["regla_oro"].astype(str).str.contains("CAMBIO")).sum())

    riesgo = cap1.get("filtro_riesgo", {})
    shock = cap3.get("shock_tasas", {})
    boom = cap4.get("boom_definacional", {})

    return {
        "fecha": contexto.get("fecha", datetime.now().strftime("%Y-%m-%d")),
        "etapa_pring": cap12.get("etapa_pring", "n/a"),
        "filtro_riesgo": {
            "dxy_6m": riesgo.get("dxy_6m"),
            "crb_6m": riesgo.get("crb_6m"),
            "tnx_6m": riesgo.get("tnx_6m"),
            "vix": riesgo.get("vix_nivel"),
        },
        "alerta_1994": shock.get("alerta_1994", False),
        "condiciones_1995": boom.get("condiciones_1995", False),
        "lideres_sectoriales": lideres,
        "ranking_200d": ranking,
        "xly_xlp_slope200": cap13.get("ciclicos_vs_staples", {}).get("xly_xlp_slope200"),
        "senales": {"alcistas": n_alc, "bajistas": n_baj, "cambio": n_cam},
    }


def generar_informe_fase(resumen):
    md = ["# Fase del Ciclo Intermarket (Murphy)", "**Fecha:** %s" % resumen["fecha"], ""]
    md.append("## 1. Etapa del ciclo")
    md.append("- **Pring:** %s" % resumen["etapa_pring"])
    md.append("")
    md.append("## 2. Filtro de riesgo (Cap.1)")
    f = resumen["filtro_riesgo"]
    md.append("- DXY 6m: %+.1f%% | CRB 6m: %+.1f%% | TNX 6m: %+.1f%% | VIX: %.1f"
              % (f["dxy_6m"], f["crb_6m"], f["tnx_6m"], f["vix"]))
    md.append("")
    md.append("## 3. Regimen de tasas (Cap.3 y Cap.4)")
    md.append("- Alerta shock de tasas 1994 (TNX sube + bonos caen): **%s**" % ("ACTIVA" if resumen["alerta_1994"] else "no"))
    md.append("- Condiciones boom desinflacionario 1995-99: **%s**" % ("SI" if resumen["condiciones_1995"] else "NO"))
    md.append("")
    md.append("## 4. Liderazgo sectorial (Cap.13, 200d)")
    md.append("- Lideres: %s" % ", ".join(resumen["lideres_sectoriales"]))
    if resumen["xly_xlp_slope200"] is not None:
        md.append("- Ciclicos vs Staples (XLY/XLP slope200): %+.1f"
                  % resumen["xly_xlp_slope200"])
    md.append("")
    md.append("## 5. Senales de auditoria")
    s = resumen["senales"]
    md.append("- Alcistas: %d | Bajistas: %d | Cambio de regimen: %d" % (s["alcistas"], s["bajistas"], s["cambio"]))
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Paso 1: fase del ciclo intermarket (Murphy)")
    parser.add_argument("--periodo", default="6y", help="Ventana de datos (1y,2y,5y,6y,10y)")
    parser.add_argument("--json", default="contexto_murphy_%s.json" % datetime.now().strftime("%Y-%m-%d"),
                        help="Archivo JSON de contexto Murphy de salida")
    parser.add_argument("--out", default="FASE_INTERMARKET.md",
                        help="Archivo markdown de resumen de fase")
    parser.add_argument("--no-senales", action="store_true", help="No regenerar senales_auditoria")
    parser.add_argument("--silencio", action="store_true", help="No imprimir detalle por pantalla")
    args = parser.parse_args()

    if not args.no_senales:
        if not args.silencio:
            print("[+] Generando senales de auditoria...")
        df_senales = senales.generar_tabla()
        senales.guardar(df_senales)
    else:
        try:
            df_senales = pd.read_csv("senales_auditoria.csv")
        except Exception:
            print("[!] No existe senales_auditoria.csv; ejecutando sin senales...")
            df_senales = pd.DataFrame(columns=["regla_oro"])

    if not args.silencio:
        print("[+] Corriendo 15 capitulos (periodo %s)..." % args.periodo)
    daily = MurphyDaily(periodo=args.periodo, verbose=not args.silencio)
    contexto = daily.run()

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(contexto, f, indent=2, ensure_ascii=False)

    resumen = resumir_fase(contexto, df_senales)
    texto = generar_informe_fase(resumen)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(texto)

    print(texto)
    print("\nGuardado en %s y %s" % (args.out, args.json))


if __name__ == "__main__":
    main()
