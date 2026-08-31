# -*- coding: utf-8 -*-
"""PARTE 5 PASO 3 - Cascada por activo: sector/mercado -> industria/sector -> activo/industria.

Antes: intermarket_parte5.py (refactorizado para usar core).
Uso: python -m analisis.portafolio.cascada_activos   (desde la raiz del proyecto)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.data import load
from core.ratio import ratio_stats

# Activos del portafolio: sector ETF / industria-factor ETF / flags locales
PORTAFOLIO = {
    "AMZN":  {"sector": "XLY", "industria": "XLY", "nota": "R2 se saltea (AMZN es peso central del sector)"},
    "GOOGL": {"sector": "XLC", "industria": "XLC", "nota": "R2 se saltea (XLC concentrado en META/GOOGL)"},
    "MP":    {"sector": "XLB", "industria": "LIT"},
    "NVDA":  {"sector": "XLK", "industria": "SMH"},
    "TSM":   {"sector": "XLK", "industria": "SMH"},
    "URA":   {"sector": "XLE", "industria": "URA", "nota": "R3 no aplica (URA es el ETF)"},
    "SMH":   {"sector": "XLK", "industria": "SMH", "nota": "SMH es el nivel industria, R3 no aplica"},
    "PAMP.BA": {"sector": "^MERV", "industria": "XLE", "local": True,
                "nota": "R1 = PAMP vs MERV local; contexto sectorial global XLE/SPY"},
    "ARGT":  {"sector": "EEM", "industria": "ARGT", "nota": "R1 = ARGT vs EEM (pais)"},
}


def main():
    tks = set(["SPY"])
    for activo, cfg in PORTAFOLIO.items():
        tks.add(cfg["sector"]); tks.add(cfg["industria"])
        if activo != cfg["industria"]:
            tks.add(activo)
    print("Descargando (3y, diario)...")
    data = {}
    for tk in sorted(tks):
        try:
            data[tk] = load(tk, period="3y")
        except Exception as e:
            print("  [!] fallo %s: %s" % (tk, e))

    print("\n" + "=" * 130)
    print(" PARTE 5 PASO 3 - CASCADA POR ACTIVO (ventana 200 + SMA50/200)")
    print("=" * 130)

    for activo, cfg in PORTAFOLIO.items():
        print("\n" + "-" * 130)
        print(" ACTIVO: %s  %s" % (activo, cfg.get("nota", "")))
        print("   R1 Sector/Mercado  : %s / SPY" % cfg["sector"])
        print("-" * 130)
        print("   %-22s %-10s %-10s %-10s %8s %7s %7s" %
              ("Ratio", "Ultimo", "SMA50", "SMA200", "Pend%200", "Z", "Pct%"))
        results = []

        if not cfg.get("local"):
            st = ratio_stats(data.get(cfg["sector"]), data.get("SPY"))
            if st:
                results.append(("R1 %s/SPY" % cfg["sector"], st))
                print("   R1 %-15s %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                      (cfg["sector"] + "/SPY", st["last"], st["m50"], st["m200"], st["slope"], st["z"], st["pct"], st["signo"]))
            # R2 industria vs sector
            if cfg["industria"] != cfg["sector"]:
                st2 = ratio_stats(data.get(cfg["industria"]), data.get(cfg["sector"]))
                if st2:
                    results.append(("R2 %s/%s" % (cfg["industria"], cfg["sector"]), st2))
                    print("   R2 %-15s %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                          ("%s/%s" % (cfg["industria"], cfg["sector"]), st2["last"], st2["m50"], st2["m200"], st2["slope"], st2["z"], st2["pct"], st2["signo"]))
            # R3 activo vs industria
            if activo != cfg["industria"]:
                st3 = ratio_stats(data.get(activo), data.get(cfg["industria"]))
                if st3:
                    results.append(("R3 %s/%s" % (activo, cfg["industria"]), st3))
                    print("   R3 %-15s %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                          ("%s/%s" % (activo, cfg["industria"]), st3["last"], st3["m50"], st3["m200"], st3["slope"], st3["z"], st3["pct"], st3["signo"]))
        else:
            # PAMP local
            st = ratio_stats(data.get(activo), data.get(cfg["sector"]))
            if st:
                results.append(("R1 %s/%s" % (activo, cfg["sector"]), st))
                print("   R1 local %-11s %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                      ("%s/%s" % (activo, cfg["sector"]), st["last"], st["m50"], st["m200"], st["slope"], st["z"], st["pct"], st["signo"]))
            stx = ratio_stats(data.get("XLE"), data.get("SPY"))
            if stx:
                results.append(("R1b XLE/SPY", stx))
                print("   R1b XLE/SPY     %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                      (stx["last"], stx["m50"], stx["m200"], stx["slope"], stx["z"], stx["pct"], stx["signo"]))
            # PAMP: R2 XLE/^MERV (sector energia vs mercado local) para PAMP
            st2 = ratio_stats(data.get("XLE"), data.get("^MERV"))
            if st2:
                results.append(("R2 XLE/MERV", st2))
                print("   R2 XLE/MERV     %-10.4f %-10.4f %-10.4f %+8.2f %+7.2f %6.1f  [%s]" %
                      (st2["last"], st2["m50"], st2["m200"], st2["slope"], st2["z"], st2["pct"], st2["signo"]))

        up = sum(1 for _, s in results if s["signo"] == "SUBENDO")
        tot = len(results)
        if tot == 0:
            v = "sin ratios para evaluar"
        elif tot == 1 and up == 1:
            v = "ratio unico SUBENDO -> depende de la pata de industria (check R2/R3)"
        elif up == tot:
            v = "CASCADA COMPLETA (%d/%d ratios SUBENDO) -> viento a favor" % (up, tot)
        elif up >= tot * 0.66:
            v = "Cascada mayormente alcista (%d/%d suben)" % (up, tot)
        elif up <= tot * 0.33:
            v = "Cascada rota (%d/%d suben) -> perder contra nivel superior" % (up, tot)
        else:
            v = "Cascada mixta (%d/%d suben) -> sin confirmacion" % (up, tot)
        print("   => %s" % v)


if __name__ == "__main__":
    main()