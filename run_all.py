# -*- coding: utf-8 -*-
"""Pipeline diario unico de intermarket (motor Murphy + portafolio + decision).

Orquesta el motor completo del libro de John Murphy:
   1. senales_auditoria.csv/json  (analisis.ejecutivo.senales)
   2. contexto_murphy_<fecha>.json con los 15 capitulos (Cap.3 y Cap.4 incluidos)
   3. RECOMENDACIONES / REBALANCEO / CONSTRUCTOR de portafolios
   4. Backtest walk-forward del constructor
   5. DECISION_INVERSION.md (informe ejecutivo)
   6. Copia historica en historial/

Uso:
    python run_all.py
    python run_all.py --max-cands 40 --no-liquidez
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime

FECHA = datetime.now().strftime("%Y-%m-%d")


def run(cmd):
    print("\n" + "=" * 70)
    print("Ejecutando:", cmd)
    print("=" * 70)
    result = subprocess.run(cmd, shell=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print("[ERROR] comando fallo:", cmd, file=sys.stderr)
        sys.exit(result.returncode)


def guardar_historial(files, fecha):
    """Copia outputs a historial/YYYY-MM-DD/ y actualiza historial/latest/."""
    hist_dir = os.path.join("historial", fecha)
    latest_dir = os.path.join("historial", "latest")
    os.makedirs(hist_dir, exist_ok=True)
    os.makedirs(latest_dir, exist_ok=True)

    for item in os.listdir(latest_dir):
        item_path = os.path.join(latest_dir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception:
            pass

    copiados = []
    for src in files:
        if not os.path.exists(src):
            continue
        dst_hist = os.path.join(hist_dir, os.path.basename(src))
        dst_latest = os.path.join(latest_dir, os.path.basename(src))
        if os.path.isdir(src):
            shutil.copytree(src, dst_hist, dirs_exist_ok=True)
            shutil.copytree(src, dst_latest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst_hist)
            shutil.copy2(src, dst_latest)
        copiados.append(src)

    meta = {
        "fecha": fecha,
        "archivos": [os.path.basename(f) for f in copiados],
    }
    with open(os.path.join(hist_dir, "metadata.json"), "w", encoding="utf-8") as f:
        f.write(str(meta).replace("'", '"'))
    return hist_dir


def main():
    parser = argparse.ArgumentParser(description="Pipeline diario unico de intermarket (Murphy)")
    parser.add_argument("--max-cands", type=int, default=60,
                        help="Maximo de candidatos por bucket para el constructor")
    parser.add_argument("--contexto", default="contexto_murphy_%s.json" % FECHA,
                        help="Archivo JSON de contexto Murphy")
    parser.add_argument("--matutino", action="store_true",
                        help="Modo resumen rapido: solo senales + contexto + decision")
    parser.add_argument("--no-historial", action="store_true",
                        help="No guardar copia historica en historial/")
    parser.add_argument("--no-noticias", action="store_true",
                        help="Omitir el paso de noticias del ciclo (offline rapido)")
    parser.add_argument("--no-liquidez", action="store_true",
                        help="No aplicar filtro de liquidez en el constructor")
    parser.add_argument("--min-monto-usd", type=float, default=5_000_000)
    parser.add_argument("--min-monto-ars", type=float, default=1_000_000)
    parser.add_argument("--min-precio-usd", type=float, default=5.0)
    parser.add_argument("--min-precio-ars", type=float, default=100.0)
    args = parser.parse_args()

    liquidez_flags = ""
    if args.no_liquidez:
        liquidez_flags += " --no-liquidez"
    else:
        liquidez_flags += f" --min-monto-usd {args.min_monto_usd}"
        liquidez_flags += f" --min-monto-ars {args.min_monto_ars}"
        liquidez_flags += f" --min-precio-usd {args.min_precio_usd}"
        liquidez_flags += f" --min-precio-ars {args.min_precio_ars}"

    # 0. Senales de auditoria (senales_auditoria.csv/json)
    run("python -m analisis.ejecutivo.senales")

    # 1. Contexto Murphy (15 capitulos) + informes de portafolio
    flags = " --matutino" if args.matutino else " --portfolio --rebalanceo --constructor"
    run(f"python -m analisis.ejecutivo.diario{flags} "
        f"--max-cands {args.max_cands}{liquidez_flags} --json {args.contexto} --silencio")

    # 1.5 Noticias del ciclo: lee/interpreta/verifica el regimen contra narrativa
    if not args.no_noticias:
        run(f"python -m analisis.ejecutivo.noticias_ciclo --contexto {args.contexto} "
            f"--out NOTICIAS_CICLO.md --json noticias_ciclo.json")

    if args.matutino:
        run(f"python -m analisis.ejecutivo.decision --contexto {args.contexto} --out DECISION_INVERSION.md")
        print("\nModo matutino: omitiendo backtest, constructor y rebalanceo.")

    # 2. Backtest walk-forward del constructor (solo modo completo)
    else:
        run(f"python -m analisis.portafolio.backtest_constructor --contexto {args.contexto} "
            f"--max-cands {args.max_cands} --out BACKTEST_CONSTRUCTOR.md --charts-dir charts")

        # 3. Informe ejecutivo de decision
        run(f"python -m analisis.ejecutivo.decision --contexto {args.contexto} --out DECISION_INVERSION.md")

    outputs = [args.contexto, "DECISION_INVERSION.md", "RECOMENDACIONES_PORTAFOLIOS.md",
               "REBALANCEO_PORTAFOLIOS.md", "CONSTRUCTOR_PORTAFOLIO.md", "BACKTEST_CONSTRUCTOR.md",
               "NOTICIAS_CICLO.md", "noticias_ciclo.json",
               "senales_auditoria.csv", "senales_auditoria.json"]
    for item in os.listdir("."):
        if item.endswith(".csv") and item != "senales_auditoria.csv" or (item == "charts" and os.path.isdir(item)):
            outputs.append(item)

    fecha = datetime.now().strftime("%Y-%m-%d")
    if not args.no_historial:
        hist_dir = guardar_historial(outputs, fecha)
        print("\nHistorial guardado en:", hist_dir)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETADO")
    print("=" * 70)
    print("Archivos generados:")
    for f in outputs:
        if os.path.exists(f):
            print("  -", f)


if __name__ == "__main__":
    main()