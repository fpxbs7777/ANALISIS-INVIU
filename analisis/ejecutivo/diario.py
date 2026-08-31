# -*- coding: utf-8 -*-
"""Runner diario unificado para el contexto Murphy.

Uso:
    python -m analisis.ejecutivo.diario
    python -m analisis.ejecutivo.diario --caps 8,9,10
    python -m analisis.ejecutivo.diario --json contexto_2026-08-13.json
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analisis.portafolio.analizador import generar_informe
from analisis.portafolio.rebalanceo import generar_informe_rebalanceo
from analisis.portafolio.constructor import generar_informe_constructor
from analisis.libro import (
    Capitulo1, Capitulo2, Capitulo3, Capitulo4, Capitulo5, Capitulo6, Capitulo7,
    Capitulo8, Capitulo9, Capitulo10, Capitulo11, Capitulo12,
    Capitulo13, Capitulo14, Capitulo15,
)

CAPITULOS = {
    "1": Capitulo1, "2": Capitulo2, "3": Capitulo3, "4": Capitulo4,
    "5": Capitulo5, "6": Capitulo6, "7": Capitulo7, "8": Capitulo8,
    "9": Capitulo9, "10": Capitulo10, "11": Capitulo11, "12": Capitulo12,
    "13": Capitulo13, "14": Capitulo14, "15": Capitulo15,
}


class MurphyDaily:
    """Ejecuta los capitulos seleccionados y devuelve un dict consolidado."""

    def __init__(self, periodo="6y", verbose=True):
        self.periodo = periodo
        self.verbose = verbose

    def run(self, nombres=None):
        """nombres: lista de strings con numeros de capitulo. None = todos."""
        seleccion = list(CAPITULOS.keys()) if nombres is None else [str(x) for x in nombres]
        out = {"fecha": datetime.now().strftime("%Y-%m-%d"), "periodo": self.periodo}
        for n in seleccion:
            cls = CAPITULOS.get(n)
            if cls is None:
                continue
            if self.verbose:
                print("[+] %s ..." % cls.TITULO)
            cap = cls(periodo=self.periodo, verbose=False)
            out["cap%s" % n] = {
                "titulo": cls.TITULO,
                "resultados": cap.run(),
            }
        return out

    def run_texto(self, nombres=None):
        out = self.run(nombres=nombres)
        for k, v in out.items():
            if not k.startswith("cap"):
                continue
            cls = CAPITULOS[k.replace("cap", "")]
            cap = cls(periodo=self.periodo, verbose=False)
            cap.datos = {}  # no re-usamos datos; imprimira resultados
            cap.resultados = v["resultados"]
            cap.texto()
        return out


def main():
    parser = argparse.ArgumentParser(description="Contexto Murphy diario")
    parser.add_argument("--caps", type=str, default=None,
                        help="Capitulos a correr separados por coma (ej: 8,9,10). Por defecto todos.")
    parser.add_argument("--json", type=str, default=None,
                        help="Guardar resultados en archivo JSON")
    parser.add_argument("--periodo", type=str, default="6y",
                        help="Ventana de datos (1y,2y,5y,6y,10y)")
    parser.add_argument("--silencio", action="store_true",
                        help="No imprimir por pantalla")
    parser.add_argument("--portfolio", action="store_true",
                        help="Si existe portafolios_inviu.json, generar RECOMENDACIONES_PORTAFOLIOS.md")
    parser.add_argument("--rebalanceo", action="store_true",
                        help="Si existe portafolios_inviu.json, generar REBALANCEO_PORTAFOLIOS.md")
    parser.add_argument("--constructor", action="store_true",
                        help="Si existe portafolios_inviu.json, generar CONSTRUCTOR_PORTAFOLIO.md")
    parser.add_argument("--matutino", action="store_true",
                        help="Modo resumen: solo contexto Murphy (sin portafolio)")
    parser.add_argument("--max-cands", type=int, default=60,
                        help="Máximo de candidatos por bucket para el constructor")
    parser.add_argument("--no-liquidez", action="store_true",
                        help="No aplicar filtro de liquidez en el constructor")
    parser.add_argument("--min-monto-usd", type=float, default=5_000_000,
                        help="Monto diario mínimo USD para considerar líquido")
    parser.add_argument("--min-monto-ars", type=float, default=1_000_000,
                        help="Monto diario mínimo ARS para considerar líquido")
    parser.add_argument("--min-precio-usd", type=float, default=5.0,
                        help="Precio mínimo USD para considerar líquido")
    parser.add_argument("--min-precio-ars", type=float, default=100.0,
                        help="Precio mínimo ARS para considerar líquido")
    args = parser.parse_args()

    caps = args.caps.split(",") if args.caps else None
    daily = MurphyDaily(periodo=args.periodo, verbose=not args.silencio)
    out = daily.run_texto(nombres=caps) if not args.silencio else daily.run(nombres=caps)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        if not args.silencio:
            print("\nGuardado en %s" % args.json)

    if (args.portfolio or args.rebalanceo) and os.path.exists("portafolios_inviu.json"):
        if "cap12" not in out or "cap13" not in out:
            ctx = MurphyDaily(periodo=args.periodo, verbose=False).run(nombres=["12", "13"])
            out.update(ctx)
        if args.portfolio:
            if not args.silencio:
                print("\n[+] Generando análisis de portafolio...")
            generar_informe("portafolios_inviu.json", "RECOMENDACIONES_PORTAFOLIOS.md", contexto=out)
            if not args.silencio:
                print("Guardado en RECOMENDACIONES_PORTAFOLIOS.md")
        if args.rebalanceo:
            if not args.silencio:
                print("\n[+] Generando plan de rebalanceo...")
            generar_informe_rebalanceo("portafolios_inviu.json", "REBALANCEO_PORTAFOLIOS.md", contexto=out)
            if not args.silencio:
                print("Guardado en REBALANCEO_PORTAFOLIOS.md")
        if args.constructor:
            if not args.silencio:
                print("\n[+] Generando constructor de portafolio por sectores...")
            generar_informe_constructor("portafolios_inviu.json", out, "unificado_completo - copia.json",
                                        "CONSTRUCTOR_PORTAFOLIO.md", verbose=not args.silencio,
                                        max_cands=args.max_cands, aplicar_liquidez=not args.no_liquidez,
                                        min_monto_usd=args.min_monto_usd, min_monto_ars=args.min_monto_ars,
                                        min_precio_usd=args.min_precio_usd, min_precio_ars=args.min_precio_ars)
            if not args.silencio:
                print("Guardado en CONSTRUCTOR_PORTAFOLIO.md")


if __name__ == "__main__":
    main()