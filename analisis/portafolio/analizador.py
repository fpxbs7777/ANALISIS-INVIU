# -*- coding: utf-8 -*-
"""Analizador automatico de portafolios Inviu cruzado con señales Murphy.

Uso:
    python -m analisis.portafolio.analizador --in portafolios_inviu.json --out RECOMENDACIONES_PORTAFOLIOS.md

El JSON debe tener la estructura de portafolios_inviu.json (ejemplo incluido).
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


MAPEO_TICKER_SENAL = {
    "SPY": "AA1",
    "AMZN": "A4",
    "GOOGL": "A5",
    "NVDA": "A1",
    "TSM": "A2",
    "SMH": "I1",
    "MP": "A3",
    "URA": "I3",
    "PAMP": "LOC1",
    "XLE": "S1",
}

SECTOR_A_ETF = {
    "Benchmark": "SPY",
    "Tecnologia": "XLK",
    "Discrecional": "XLY",
    "Comunicacion": "XLC",
    "Energia": "XLE",
    "Materiales": "XLB",
    "Staples": "XLP",
    "Industrial": "XLI",
    "Financieras": "XLF",
    "Salud": "XLV",
    "Utilities": "XLU",
    "Metales": "GLD",
    "Bonos": "TLT",
}


def cargar_senales(path="senales_auditoria.csv"):
    df = pd.read_csv(path)
    df["accion"] = df["accion"].fillna("VIGILAR")
    df["regla_oro"] = df["regla_oro"].fillna("NEUTRO")
    return df.set_index("id").to_dict("index")


def buscar_senal(ticker, senales):
    sid = MAPEO_TICKER_SENAL.get(ticker)
    if sid and sid in senales:
        return senales[sid]
    return None


def recomendacion_activo(ticker, senal, sector, contexto, rendimiento=None):
    cap13 = contexto.get("cap13", {}).get("resultados", {})
    ranking = cap13.get("liderazgo_sectorial_200d", {})
    sectores_ordenados = list(ranking.keys())
    lideres = sectores_ordenados[:3]
    rezagados = sectores_ordenados[-3:]
    etf_sector = SECTOR_A_ETF.get(sector)

    # Notas especiales por ticker/sector
    if ticker == "CRCEO" and rendimiento is not None and rendimiento < -0.4:
        return "RECORTAR PÉRDIDA", "pérdida -50%+, recuperación improbable"
    if ticker in ["SLV", "GLD"]:
        return "VIGILAR/REDUCIR", "metales preciosos sufren con dólar fuerte y oro en corrección"
    if ticker in ["PEP", "KO"]:
        return "NO AGREGAR/REDUCIR", "staples (XLP) rezagado en fase expansiva"
    if ticker in ["CVS", "PFE", "JNJ"]:
        return "MANTENER, NO AGREGAR", "salud (XLV) rezagado pero defensivo"
    if ticker in ["NU", "MELI"]:
        return "MANTENER", "emergentes/fintech latina; contexto global risk-on"
    if sector == "Bonos" and ticker != "CRCEO":
        return "MANTENER", "carry trade argentino; vigilar contexto local"

    if senal:
        regla = str(senal.get("regla_oro", "NEUTRO"))
        if "ALCISTA" in regla:
            return "MANTENER/ACUMULAR", "señal alcista confirmada"
        if "BAJISTA" in regla:
            return "SALIR/REDUCIR", "señal bajista confirmada"
        if "CAMBIO" in regla:
            return "VIGILAR", "cambio de régimen en curso"
        return "MANTENER", "señal neutra"

    if etf_sector in lideres:
        return "MANTENER/ACUMULAR", "sector %s líder en contexto Murphy" % etf_sector
    if etf_sector in rezagados:
        return "NO AGREGAR/REDUCIR", "sector %s rezagado en contexto Murphy" % etf_sector
    return "MANTENER", "sin señal directa ni sector extremo"


def analizar_cuenta(cuenta, senales, contexto):
    tenencias = cuenta.get("tenencias", [])
    patrimonio_usd = cuenta.get("patrimonio_usd", 0)
    cash_usd_total = cuenta.get("cash", {}).get("USD", 0) + cuenta.get("cash", {}).get("USD_C", 0)

    total_ars = sum(t.get("monto_ars", 0) for t in tenencias)
    cash_ars = cuenta.get("cash", {}).get("ARS", 0)
    # tipo de cambio implícito: parte no-USD del patrimonio sobre activos+cash en ARS
    no_usd_patrimonio = patrimonio_usd - cash_usd_total
    tc_impl = (total_ars + cash_ars) / no_usd_patrimonio if no_usd_patrimonio > 0 else 0
    # recalcular cash incluyendo ARS al TC implicito
    cash_usd_total = cash_usd_total + cash_ars / tc_impl if tc_impl else cash_usd_total
    cash_pct = (cash_usd_total / patrimonio_usd) * 100 if patrimonio_usd else 0

    filas = []
    for t in tenencias:
        monto = t.get("monto_ars", 0)
        monto_usd = monto / tc_impl if tc_impl else 0
        pct_total = (monto_usd / patrimonio_usd) * 100 if patrimonio_usd else 0
        rend = None
        if t.get("pp") and t.get("ultimo"):
            rend = (t["ultimo"] / t["pp"] - 1)
        senal = buscar_senal(t["ticker"], senales)
        rec, motivo = recomendacion_activo(t["ticker"], senal, t.get("sector"), contexto, rendimiento=rend)
        filas.append({
            "ticker": t["ticker"],
            "tipo": t.get("tipo", ""),
            "cantidad": t.get("cantidad", 0),
            "monto_ars": monto,
            "monto_usd": monto_usd,
            "pct_total": pct_total,
            "rendimiento": rend,
            "sector": t.get("sector", ""),
            "senal": senal["regla_oro"] if senal else "n/a",
            "recomendacion": rec,
            "motivo": motivo,
        })

    return {
        "nombre": cuenta["nombre"],
        "perfil": cuenta.get("perfil", ""),
        "patrimonio_usd": patrimonio_usd,
        "cash_usd": cash_usd_total,
        "cash_pct": cash_pct,
        "cash": cuenta.get("cash", {}),
        "total_ars_activos": total_ars,
        "tc_implicito": tc_impl,
        "filas": filas,
    }


def generar_informe(archivo_in, archivo_out, contexto=None):
    with open(archivo_in, encoding="utf-8") as f:
        data = json.load(f)

    senales = cargar_senales()
    if contexto is None:
        print("[+] Calculando contexto Murphy (capitulos 12 y 13)...")
        # import local para evitar circular
        from analisis.ejecutivo.diario import MurphyDaily
        daily = MurphyDaily(periodo="6y", verbose=False)
        contexto = daily.run(nombres=["12", "13"])

    cuentas = [analizar_cuenta(c, senales, contexto) for c in data["cuentas"]]

    md = []
    md.append("# Recomendaciones de Portafolio — Análisis Murphy Automático")
    md.append("**Fecha:** %s" % datetime.now().strftime("%Y-%m-%d"))
    md.append("")
    md.append("## Contexto macro rápido")
    cap12 = contexto.get("cap12", {}).get("resultados", {})
    cap13 = contexto.get("cap13", {}).get("resultados", {})
    md.append("- Etapa Pring: **%s**" % cap12.get("etapa_pring", "n/a"))
    md.append("- Sectores líderes (200d): %s" % ", ".join(list(cap13.get("liderazgo_sectorial_200d", {}).keys())[:3]))
    md.append("- Sectores rezagados (200d): %s" % ", ".join(list(cap13.get("liderazgo_sectorial_200d", {}).keys())[-3:]))
    md.append("")

    for c in cuentas:
        md.append("## %s" % c["nombre"])
        md.append("Perfil: %s  |  Patrimonio: USD %.2f  |  Cash: %.1f%%" % (c["perfil"], c["patrimonio_usd"], c["cash_pct"]))
        md.append("")
        md.append("| Ticker | Tipo | Sector | % Total | Rend. | Señal Murphy | Recomendación | Motivo |")
        md.append("|---|---|---|---|---|---|---|---|")
        for f in sorted(c["filas"], key=lambda x: -x["pct_total"]):
            rend_str = "%.1f%%" % (f["rendimiento"] * 100) if f["rendimiento"] is not None else "n/a"
            md.append("| %s | %s | %s | %.2f%% | %s | %s | %s | %s |" %
                      (f["ticker"], f["tipo"], f["sector"], f["pct_total"], rend_str, f["senal"], f["recomendacion"], f["motivo"]))

        # recomendaciones de allocación
        md.append("")
        md.append("### Recomendaciones de allocación")
        if c["cash_pct"] > 40:
            md.append("- **Cash muy alto (%.1f%%):** reducir al 15-20%% y destinar a SPY/QQQ/XLE dado el contexto risk-on." % c["cash_pct"])
        elif c["cash_pct"] < 3:
            md.append("- **Cash muy bajo (%.1f%%):** subir reserva al 5-10%% vendiendo parcial de ganadores." % c["cash_pct"])
        else:
            md.append("- Cash en rango razonable (%.1f%%)." % c["cash_pct"])

        bajistas = [f for f in c["filas"] if f["recomendacion"] == "SALIR/REDUCIR"]
        if bajistas:
            md.append("- **Salir/reducir:** %s" % ", ".join(["%s (%.1f%%)" % (f["ticker"], f["pct_total"]) for f in bajistas]))
        alcistas = [f for f in c["filas"] if f["recomendacion"] == "MANTENER/ACUMULAR"]
        if alcistas:
            md.append("- **Potenciar:** %s" % ", ".join(["%s (%.1f%%)" % (f["ticker"], f["pct_total"]) for f in alcistas]))
        reducir = [f for f in c["filas"] if "REDUCIR" in f["recomendacion"] and f["recomendacion"] != "SALIR/REDUCIR"]
        if reducir:
            md.append("- **No agregar / reducir:** %s" % ", ".join(["%s (%.1f%%)" % (f["ticker"], f["pct_total"]) for f in reducir]))
        cambio = [f for f in c["filas"] if f["recomendacion"] == "VIGILAR"]
        if cambio:
            md.append("- **Vigilar (cambio de régimen):** %s" % ", ".join([f["ticker"] for f in cambio]))

        # concentración
        concentrados = [f for f in c["filas"] if f["pct_total"] >= 20]
        if concentrados:
            md.append("- **Concentración:** %s superan 20%% cada uno; no agregar más, solo rebalancear." % ", ".join([f["ticker"] for f in concentrados]))

        # moneda
        ars_cash = c.get("cash", {}).get("ARS", 0)
        if ars_cash > 0:
            md.append("- **Riesgo ARS:** parte del cash está en pesos; considerar pasivo a USD/dolarizar reservas.")
        md.append("")

    md.append("## Triggers globales a monitorear")
    md.append("- IRX supera TNX (inversión de curva) → alerta de Stage 5/tope de ciclo.")
    md.append("- XLP/SPY y VNQ/SPY giran al alza → defensivas tomando liderazgo.")
    md.append("- DXY cae + oro sube en 6m → se activa flight-to-gold; revisar SLV/GLD.")

    texto = "\n".join(md)
    with open(archivo_out, "w", encoding="utf-8") as f:
        f.write(texto)
    return texto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="portafolios_inviu.json")
    parser.add_argument("--out", default="RECOMENDACIONES_PORTAFOLIOS.md")
    args = parser.parse_args()
    texto = generar_informe(args.input, args.out)
    print(texto)
    print("\nGuardado en %s" % args.out)


if __name__ == "__main__":
    main()