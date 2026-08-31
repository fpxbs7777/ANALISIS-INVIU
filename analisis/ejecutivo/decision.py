# -*- coding: utf-8 -*-
"""Genera el informe de decision de inversion ejecutivo.

Uso:
    python -m analisis.ejecutivo.decision
    python -m analisis.ejecutivo.decision --out DECISION_INVERSION.md
"""
import argparse
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.ejecutivo.diario import MurphyDaily


def _fmt(v):
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "SI" if v else "NO"
    if isinstance(v, float):
        if abs(v) < 10:
            return "%+.2f" % v
        return "%+.1f" % v
    return str(v)


def cargar_senales(path="senales_auditoria.csv"):
    df = pd.read_csv(path)
    df["accion"] = df["accion"].fillna("VIGILAR")
    df["regla_oro"] = df["regla_oro"].fillna("NEUTRO")
    return df


def interpretar_regimen(contexto):
    """Devuelve parrafos de regimen macro a partir de los resultados."""
    cap12 = contexto.get("cap12", {}).get("resultados", {})
    cap15 = contexto.get("cap15", {}).get("resultados", {})
    cap9 = contexto.get("cap9", {}).get("resultados", {})
    cap13 = contexto.get("cap13", {}).get("resultados", {})

    etapa = cap12.get("etapa_pring", "n/a")
    lines = []
    lines.append("- **Etapa del ciclo (Pring):** %s" % etapa)
    lines.append("- **Contexto global:** bull global activo (SPY-ACWI corr %s); emergentes (%s) suben con commodities a pesar del dolar fuerte."
                 % (_fmt(cap15.get("global", {}).get("spy_acwi")),
                    _fmt(cap15.get("emergentes", {}).get("eem_6m"))))
    lines.append("- **Deflacion:** %s — correlacion SPY-TLT %s, Japon vs tasas %s, commodities y tasas %s."
                 % (
                     "NO activa" if not cap9.get("deflacion_stocks_tasas", {}).get("ambos_cae") else "alerta",
                     _fmt(cap15.get("decoupling", {}).get("spy_tlt")),
                     _fmt(cap15.get("japon", {}).get("corr")),
                     _fmt(cap9.get("bonos_comm", {}).get("corr")),
                 ))
    lideres = list(cap13.get("liderazgo_sectorial_200d", {}).keys())[:3]
    lines.append("- **Liderazgo sectorial (200d):** %s" % ", ".join(lideres))
    return "\n".join(lines)


def recomendaciones(df):
    """Agrupa senales por accion y genera recomendaciones."""
    out = []
    # Alcistas confirmadas
    alc = df[df["regla_oro"].str.contains("ALCISTA")]
    if not alc.empty:
        out.append("### Mantener / Acumular")
        for _, r in alc.iterrows():
            out.append("- **%s** (%s): %s — %s" % (r["id"], r["ratio"], r["regla_oro"], r["accion"]))
    # Bajistas confirmadas
    baj = df[df["regla_oro"].str.contains("BAJISTA")]
    if not baj.empty:
        out.append("\n### Rotar / No comprar")
        for _, r in baj.iterrows():
            out.append("- **%s** (%s): %s — %s" % (r["id"], r["ratio"], r["regla_oro"], r["accion"]))
    # Cambio de regimen
    cam = df[df["regla_oro"].str.contains("CAMBIO")]
    if not cam.empty:
        out.append("\n### Cambio de regimen (vigilar confirmacion)")
        for _, r in cam.iterrows():
            out.append("- **%s** (%s): %s — %s" % (r["id"], r["ratio"], r["regla_oro"], r["accion"]))
    # Neutros relevantes
    neut = df[(df["regla_oro"] == "NEUTRO") & (df["nivel"].str.contains("M1|M2"))]
    if not neut.empty:
        out.append("\n### Macro neutra (contexto sin disparador)")
        for _, r in neut.iterrows():
            out.append("- **%s** (%s): %s" % (r["id"], r["ratio"], r["regla_oro"]))
    return "\n".join(out)


def hallazgos_capitulos(contexto):
    out = []
    for k in sorted(contexto.keys()):
        if not k.startswith("cap"):
            continue
        v = contexto[k]
        titulo = v.get("titulo", k)
        res = v.get("resultados", {})
        # Extraer 1-2 metricas clave
        bullets = []
        if "etapa_pring" in res:
            bullets.append("Etapa Pring: %s" % res["etapa_pring"])
        if "liderazgo_sectorial_200d" in res:
            top = list(res["liderazgo_sectorial_200d"].keys())[:2]
            bullets.append("Lideres: %s" % ", ".join(top))
        if "oro_dolar" in res:
            bullets.append("Oro/DXY corr %s" % _fmt(res["oro_dolar"].get("corr")))
        if "divergencia_bonos_comm" in res:
            bullets.append("Bonos/Comm alerta: %s" % _fmt(res["divergencia_bonos_comm"].get("alerta")))
        if "comm_vs_bonos" in res:
            bullets.append("Comm/Bonos slope200 %s%%" % _fmt(res["comm_vs_bonos"].get("crb_tlt_slope200")))
        if "reits_spy" in res:
            bullets.append("REITs/SPY slope200 %s%%" % _fmt(res["reits_spy"].get("vnq_spy_slope200")))
        if "global" in res:
            bullets.append("SPY-ACWI corr %s" % _fmt(res["global"].get("spy_acwi")))
        if "sector_rotation" in res:
            bullets.append("Tech %s%% vs Energy %s%%" % (_fmt(res["sector_rotation"].get("xlk_6m")), _fmt(res["sector_rotation"].get("xle_6m"))))
        if "comm_tasas_juntas" in res:
            bullets.append("Comm+Tasas suben juntas: %s" % _fmt(res["comm_tasas_juntas"].get("reflacion")))
        if "vinculos_madre" in res:
            vm = res["vinculos_madre"]
            bullets.append("Vinculos DXY-CRB %s, TLT-CRB %s" % (_fmt(vm.get("dxy_crb")), _fmt(vm.get("tlt_crb"))))
        if "dolar_comm" in res:
            bullets.append("DXY-CRB %s" % _fmt(res["dolar_comm"].get("corr")))
        if "bonos_comm" in res:
            bullets.append("TNX-CRB %s" % _fmt(res["bonos_comm"].get("corr")))
        if "shock_tasas" in res:
            st = res["shock_tasas"]
            bullets.append("Shock 1994: TNX %s%% vs TLT %s%% (alerta %s)"
                           % (_fmt(st.get("tnx_6m")), _fmt(st.get("tlt_6m")), _fmt(st.get("alerta_1994"))))
        if "boom_definacional" in res:
            bd = res["boom_definacional"]
            bullets.append("Boom 1995-99: DXY %s%%, CRB %s%%, TNX %s%% (condiciones %s)"
                           % (_fmt(bd.get("dxy_6m")), _fmt(bd.get("crb_6m")), _fmt(bd.get("tnx_6m")),
                              _fmt(bd.get("condiciones_1995"))))
        if bullets:
            out.append("- **%s**: %s" % (titulo, "; ".join(bullets)))
    return "\n".join(out)


def seccion_noticias(path="noticias_ciclo.json"):
    """Devuelve bloque markdown con noticias del ciclo si existe el JSON."""
    if not os.path.exists(path):
        return ""
    try:
        import json
        with open(path, encoding="utf-8") as f:
            news = json.load(f)
    except Exception:
        return ""
    md = ["## 7. Noticias del ciclo (verificacion)"]
    drivers = news.get("drivers") or []
    if not drivers:
        md.append("- *No se obtuvieron noticias (pass de noticias sin datos).*")
        return "\n".join(md)
    filas = []
    for d in drivers:
        precio = d.get("precio_6m")
        filas.append({
            "driver": d.get("nombre", d.get("ticker")),
            "precio_6m%": ("%+.1f" % precio) if isinstance(precio, (int, float)) else "n/a",
            "n": d.get("noticias", 0),
            "score": d.get("score_neto", 0),
        })
    import pandas as pd
    md.append(pd.DataFrame(filas).to_markdown(index=False))
    coh = news.get("coherencia") or []
    if coh:
        md.append("")
        md.append("**Coherencia vs regimen:**")
        for c in coh:
            md.append("- %s — *%s* (%s)" % (c.get("claim", ""), c.get("veredicto", ""), c.get("activo", "")))
    interp = news.get("interpretacion") or []
    if interp:
        md.append("")
        md.append("**Interpretacion:**")
        for l in interp:
            md.append("> %s" % l)
    return "\n".join(md)


def generar_informe_decision(contexto=None, df_senales=None, out_path="DECISION_INVERSION.md"):
    if df_senales is None:
        df_senales = cargar_senales()
    if contexto is None:
        daily = MurphyDaily(periodo="6y", verbose=False)
        contexto = daily.run()

    fecha = contexto.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    periodo = contexto.get("periodo", "6y")

    md = []
    md.append("# Informe de Decision de Inversion — Contexto Murphy")
    md.append("**Fecha:** %s  |  **Ventana:** %s" % (fecha, periodo))
    md.append("")
    md.append("## 1. Resumen Ejecutivo")
    md.append("")
    # resumen dinamico
    etapa = contexto.get("cap12", {}).get("resultados", {}).get("etapa_pring", "n/a")
    n_alc = len(df_senales[df_senales["regla_oro"].str.contains("ALCISTA")])
    n_baj = len(df_senales[df_senales["regla_oro"].str.contains("BAJISTA")])
    n_cam = len(df_senales[df_senales["regla_oro"].str.contains("CAMBIO")])
    md.append("El regimen actual es **%s**. Hay %d senales alcistas confirmadas, %d bajistas confirmadas y %d en cambio de regimen. "
              "El contexto global es alcista (correlaciones altas), sin signos de deflacion y con commodities liderando a bonos. "
              "La postura base es **mantener Tech/AMZN/SPY, evitar discrecional/comunicaciones/litio, y no incrementar apalancamiento**." %
              (etapa, n_alc, n_baj, n_cam))
    md.append("")
    md.append("## 2. Regimen Macro")
    md.append(interpretar_regimen(contexto))
    md.append("")
    md.append("## 3. Recomendaciones por Senal")
    md.append(recomendaciones(df_senales))
    md.append("")
    md.append("## 4. Portafolios Reales")
    if os.path.exists("RECOMENDACIONES_PORTAFOLIOS.md"):
        md.append("- Informe automático cruzando tenencias con señales Murphy: **RECOMENDACIONES_PORTAFOLIOS.md**.")
    else:
        md.append("- No se encontró RECOMENDACIONES_PORTAFOLIOS.md. Ejecutar `python -m analisis.ejecutivo.diario --portfolio`.")
    if os.path.exists("REBALANCEO_PORTAFOLIOS.md"):
        md.append("- Plan mecánico de rebalanceo sugerido: **REBALANCEO_PORTAFOLIOS.md**.")
    else:
        md.append("- No se encontró REBALANCEO_PORTAFOLIOS.md. Ejecutar `python -m analisis.ejecutivo.diario --rebalanceo`.")
    if os.path.exists("CONSTRUCTOR_PORTAFOLIO.md"):
        md.append("- Constructor por sectores beneficiados (candidatos + optimización Markowitz): **CONSTRUCTOR_PORTAFOLIO.md**.")
    else:
        md.append("- No se encontró CONSTRUCTOR_PORTAFOLIO.md. Ejecutar `python -m analisis.ejecutivo.diario --constructor`.")
    md.append("")
    md.append("## 5. Riesgos y Triggers")
    yc = contexto.get("cap13", {}).get("resultados", {}).get("yield_curve", {})
    md.append("- **Riesgo 1 — inversion de curva:** IRX %s%% vs TNX %s%% (spread %s p.b.). Si IRX supera a TNX, re-evaluar todo el marco expansivo."
              % (_fmt(yc.get("irx")), _fmt(yc.get("tnx")), _fmt(yc.get("spread"))))
    md.append("- **Riesgo 2 — defensivas toman el liderazgo:** XLP/SPY y VNQ/SPY girando al alza + VTV/VUG > 0 serian alerta de Late Expansion/Stage 5.")
    md.append("- **Riesgo 3 — dolar se debilita:** si DXY cae en 6m con oro/commodities subiendo, se activa el escenario flight-to-gold de los Cap.8-10.")
    md.append("- **Oportunidad — pata commodities:** correlacion commodities-bonos negativa (-0.16) sugiere que XLE/CRB mejora diversificacion vs un portafolio 100% Tech.")
    md.append("")
    md.append("## 6. Hallazgos por Capitulo")
    md.append(hallazgos_capitulos(contexto))
    md.append("")
    seccion = seccion_noticias()
    if seccion:
        md.append(seccion)
        md.append("")
    num = "8" if seccion else "7"
    md.append("## %s. Conclusion" % num)
    md.append("**Postura recomendada:** mantener lo que tiene viento a favor (SPY, AMZN, Tech), no perseguir maximos (SPY/TLT pct 98), "
              "evitar nuevas entradas en XLY/XLC/MP-LIT, y vigilar IRX>TNX + defensivas para detectar el paso a Stage 5. "
              "Considerar una pata diversificadora en commodities (XLE) dada su baja correlacion con bonos.")

    texto = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(texto)
    return texto


def main():
    parser = argparse.ArgumentParser(description="Generar informe de decision de inversion")
    parser.add_argument("--out", type=str, default="DECISION_INVERSION.md",
                        help="Ruta de salida del informe")
    parser.add_argument("--contexto", type=str, default=None,
                        help="JSON con contexto pre-generado (opcional)")
    args = parser.parse_args()

    ctx = None
    if args.contexto:
        import json
        with open(args.contexto, encoding="utf-8") as f:
            ctx = json.load(f)

    texto = generar_informe_decision(contexto=ctx, out_path=args.out)
    print(texto)
    print("\nGuardado en %s" % args.out)


if __name__ == "__main__":
    main()