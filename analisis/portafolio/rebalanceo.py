# -*- coding: utf-8 -*-
"""Sugiere operaciones de rebalanceo para las cuentas Inviu.

Uso:
    python -m analisis.portafolio.rebalanceo --in portafolios_inviu.json --out REBALANCEO_PORTAFOLIOS.md

Lee `portafolios_inviu.json`, calcula allocaciones actuales y objetivo según perfil y
señales Murphy, y emite sugerencias de compra/venta en cantidades aproximadas.
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.portafolio.analizador import analizar_cuenta, buscar_senal, cargar_senales


# Targets por perfil: % del patrimonio total en cada categoría
TARGETS = {
    "Moderado": {
        "cash": 0.18,
        "Benchmark": 0.35,
        "Tecnologia": 0.15,
        "Energia": 0.12,
        "Industrial": 0.05,
        "Staples": 0.05,
        "Salud": 0.05,
        "Bonos": 0.03,
        "Otros": 0.02,
    },
    "Arriesgado": {
        "cash": 0.08,
        "Benchmark": 0.10,
        "Tecnologia": 0.25,
        "Energia": 0.20,
        "Industrial": 0.10,
        "Financieras": 0.08,
        "Staples": 0.05,
        "Salud": 0.05,
        "Metales": 0.04,
        "Bonos": 0.03,
        "Otros": 0.02,
    },
}


def categoria(sector):
    return sector if sector in TARGETS.get("Moderado", {}) or sector in TARGETS.get("Arriesgado", {}) else "Otros"


def analisis_rebalanceo(cuenta, senales, contexto, tolerancia=0.02):
    res = analizar_cuenta(cuenta, senales, contexto)
    perfil = res["perfil"]
    targets = TARGETS.get(perfil, TARGETS["Moderado"])
    patrimonio = res["patrimonio_usd"]

    # Agrupar por sector (usando categoría) en USD sobre patrimonio total
    sectores = {}
    for f in res["filas"]:
        cat = categoria(f["sector"])
        sectores.setdefault(cat, {"actual_usd": 0.0, "filas": []})
        sectores[cat]["actual_usd"] += f["monto_usd"]
        sectores[cat]["filas"].append(f)

    cash_usd = res["cash_usd"]
    sectores["cash"] = {"actual_usd": cash_usd, "filas": []}

    # Calcular brechas
    filas_out = []
    for cat, target in targets.items():
        actual = sectores.get(cat, {"actual_usd": 0})["actual_usd"]
        actual_pct = actual / patrimonio if patrimonio else 0
        target_usd = patrimonio * target
        diff_usd = target_usd - actual
        diff_pct = diff_usd / patrimonio if patrimonio else 0
        filas_out.append({
            "categoria": cat,
            "target": target,
            "actual_pct": actual_pct,
            "diff_pct": diff_pct,
            "diff_usd": diff_usd,
        })

    # Operaciones sugeridas por activo
    operaciones = []
    for f in res["filas"]:
        ticker = f["ticker"]
        cat = categoria(f["sector"])
        target_cat = targets.get(cat, 0)
        cat_actual_pct = sectores.get(cat, {"actual_usd": 0})["actual_usd"] / patrimonio if patrimonio else 0
        if cat_actual_pct > target_cat + tolerancia:
            # reducir proporcionalmente dentro de la categoría
            reducir_usd = f["monto_usd"] * (cat_actual_pct - target_cat) / cat_actual_pct if cat_actual_pct else 0
            reducir_cant = int(round((reducir_usd / f["monto_usd"]) * f["cantidad"])) if f["monto_usd"] else 0
            if reducir_cant > 0 and f["recomendacion"] in ("SALIR/REDUCIR", "NO AGREGAR/REDUCIR", "RECORTAR PÉRDIDA"):
                operaciones.append({"ticker": ticker, "accion": "VENDER", "cantidad": reducir_cant,
                                    "usd_aprox": reducir_usd, "motivo": "sobre-peso en %s + señal débil" % cat})
        elif cat_actual_pct < target_cat - tolerancia and f["recomendacion"] == "MANTENER/ACUMULAR":
            aumentar_usd = (target_cat - cat_actual_pct) * patrimonio * (f["pct_total"] / 100) / (cat_actual_pct if cat_actual_pct else 1)
            aumentar_cant = int(round(aumentar_usd / (f["monto_usd"] / f["cantidad"]))) if f["cantidad"] else 0
            if aumentar_cant > 0:
                operaciones.append({"ticker": ticker, "accion": "COMPRAR", "cantidad": aumentar_cant,
                                    "usd_aprox": aumentar_usd, "motivo": "bajo-peso en %s + señal fuerte" % cat})

    # Cash explícito
    cash_target_usd = patrimonio * targets.get("cash", 0.18)
    if cash_usd > cash_target_usd + (tolerancia * patrimonio):
        operaciones.append({"ticker": "CASH", "accion": "INVERTIR EXCEDENTE", "cantidad": 0,
                            "usd_aprox": cash_usd - cash_target_usd, "motivo": "cash por encima del target"})
    elif cash_usd < cash_target_usd - (tolerancia * patrimonio):
        operaciones.append({"ticker": "CASH", "accion": "RESERVAR", "cantidad": 0,
                            "usd_aprox": cash_target_usd - cash_usd, "motivo": "cash por debajo del target"})

    return {
        "nombre": res["nombre"],
        "perfil": perfil,
        "patrimonio_usd": patrimonio,
        "cash_usd": cash_usd,
        "sectores": filas_out,
        "operaciones": operaciones,
    }


def generar_informe_rebalanceo(archivo_in, archivo_out, contexto=None):
    with open(archivo_in, encoding="utf-8") as f:
        data = json.load(f)

    senales = cargar_senales()
    if contexto is None:
        from analisis.ejecutivo.diario import MurphyDaily
        daily = MurphyDaily(periodo="6y", verbose=False)
        contexto = daily.run(nombres=["12", "13"])

    resultados = [analisis_rebalanceo(c, senales, contexto) for c in data["cuentas"]]

    md = []
    md.append("# Plan de Rebalanceo — Portafolios Inviu")
    md.append("**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d"))
    md.append("")
    md.append("> Este informe sugiere operaciones mecánicas para acercar cada cuenta a una allocación objetivo basada en su perfil y en las señales Murphy. No es una recomendación de inversión personalizada; ajustar según liquidez, horizonte y costos fiscales.")
    md.append("")

    for r in resultados:
        md.append("## %s" % r["nombre"])
        md.append("Perfil: **%s**  |  Patrimonio: USD %.2f  |  Cash actual: USD %.2f (%.1f%%)" %
                  (r["perfil"], r["patrimonio_usd"], r["cash_usd"], r["cash_usd"] / r["patrimonio_usd"] * 100))
        md.append("")
        md.append("### Allocación actual vs objetivo")
        md.append("| Categoría | Objetivo | Actual | Diferencia (%%) | Diferencia (USD) |")
        md.append("|---|---|---|---|---|")
        for s in r["sectores"]:
            md.append("| %s | %.0f%% | %.1f%% | %+.1f%% | %+.0f |" %
                      (s["categoria"], s["target"] * 100, s["actual_pct"] * 100, s["diff_pct"] * 100, s["diff_usd"]))
        md.append("")
        if r["operaciones"]:
            md.append("### Operaciones sugeridas")
            md.append("| Ticker | Acción | Cantidad | USD aprox. | Motivo |")
            md.append("|---|---|---|---|---|")
            for op in r["operaciones"]:
                md.append("| %s | %s | %s | %.0f | %s |" %
                          (op["ticker"], op["accion"], op["cantidad"] if op["cantidad"] else "—", op["usd_aprox"], op["motivo"]))
        else:
            md.append("*Sin operaciones sugeridas: la cuenta está dentro de la tolerancia.*")
        md.append("")

    texto = "\n".join(md)
    with open(archivo_out, "w", encoding="utf-8") as f:
        f.write(texto)
    return texto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="portafolios_inviu.json")
    parser.add_argument("--out", default="REBALANCEO_PORTAFOLIOS.md")
    args = parser.parse_args()
    texto = generar_informe_rebalanceo(args.input, args.out)
    print(texto)
    print("\nGuardado en %s" % args.out)


if __name__ == "__main__":
    main()