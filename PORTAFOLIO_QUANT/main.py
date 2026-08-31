# -*- coding: utf-8 -*-
"""Main del sistema cuantitativo unificado.

Comandos:
    python main.py universo          -> valida universo Tier A+B
    python main.py salud             -> scoring hibrido
    python main.py factores          -> R2 multifactor
    python main.py carteras          -> pool + optimizaciones del momento
    python main.py backtest          -> walk-forward 2018+ con win-rate y MFE/MAE
    python main.py full              -> pipeline completo + informe MD
"""
import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
for p in (BASE, REPO, os.path.join(REPO, "SCANNER_INTERMARKET")):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import universo as U
import datos as D
import salud as S
import factores as F
import ciclo as C
import regimen as R
import optimizador as O
import backtest as B

import informe as INF


def cmd_universo(args):
    u = U.cargar_universo(tier="AB", max_cedear=args.max_cedear)
    print("Universo %s: ARG %d + CEDEAR %d = %d" % (
        args.tier, u["stats"]["n_arg"], u["stats"]["n_cedear"], u["stats"]["n_total"]))
    print("ARG sample:", [x["ticker_yf"] for x in u["arg"][:10]])
    print("CEDEAR sample:", [x["ticker_yf"] for x in u["cedear"][:10]])
    return u


def _construir_pool_y_datos(args):
    u = U.cargar_universo(tier=args.tier, max_cedear=args.max_cedear)
    cfg = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
    tickers_yf = ([x["ticker_yf"] for x in u["arg"]] +
                  [x["ticker_yf"] for x in u["cedear"]] +
                  cfg["factores"]["lista"] +
                  ["GSG", "HYG", "LQD", "^VIX", "DX-Y.NYB"])
    tickers_yf = sorted(set(t for t in tickers_yf if t))
    print("[datos] descargando %d tickers periodo %s ..." % (len(tickers_yf), cfg["datos"]["periodo"]))
    close = D.descargar_panel(tickers_yf, periodo=cfg["datos"]["periodo"])
    print("[datos] panel: %s filas x %s cols" % close.shape)
    # filtrar columnas con historia suficiente
    min_dias = cfg["universo"]["min_hist_dias"]
    keep = [c for c in close.columns if close[c].dropna().shape[0] >= min_dias]
    print("[datos] tickers con >=%d dias: %d/%d" % (min_dias, len(keep), len(close.columns)))
    close = close[keep]
    return u, close, cfg


def cmd_full(args):
    u, close, cfg = _construir_pool_y_datos(args)

    # salud
    print("[salud] scoring hibrido (fundamental 50/50; esto puede tardar por yfinance.info)...")
    df_salud = S.scoring(close[[c for c in close.columns
                                if c in [x["ticker_yf"] for x in (u["arg"] + u["cedear"])]]],
                         peso_fund=cfg["salud"]["peso_fundamental"],
                         peso_cuant=cfg["salud"]["peso_cuant"])
    print(df_salud.head(10).to_string(index=False))
    # factores
    print("[factores] regresiones R2...")
    df_r2, det = F.factores(close, cfg["factores"]["lista"],
                            r2_umbral=cfg["factores"]["r2_umbral"],
                            ventana=cfg["factores"]["ventana_dias"])
    if not df_r2.empty:
        print(df_r2.head(10).to_string(index=False))
    else:
        print("  (ningun ticker supero R2 umbral; se usara solo ranking de salud)")

    # ciclo
    print("[ciclo] fase intermarket...")
    est_ciclo = C.estado_ciclo()
    print("  fase:", est_ciclo.get("fase"), est_ciclo.get("conf"))

    # pool final
    top_salud = set(df_salud.head(40)["ticker"].tolist())
    top_r2 = set(df_r2["ticker"].tolist()) if not df_r2.empty else top_salud
    pool = sorted(top_salud & top_r2) if top_r2 else sorted(top_salud)
    # si el ciclo favorece sectores, no filtramos duro por ahora; anotamos
    if not pool:
        pool = sorted(top_salud)[:20]
    pool = pool[:cfg["optimizador"]["top_n_pool"]]
    print("[pool] final %d tickers: %s" % (len(pool), pool[:15]))
    close_pool = close[[c for c in pool if c in close.columns]]

    # optimizador
    print("[optimizador] construyendo carteras sobre pool...")
    carteras, _ = O.construir_carteras(close_pool,
                                       tipos=cfg["optimizador"]["tipos"],
                                       max_peso=cfg["optimizador"]["max_peso"],
                                       top_n=cfg["optimizador"]["top_n_pool"])
    for k, v in carteras.items():
        print("  %-18s ret %+.2f%% vol %.2f%% sharpe %.2f" % (k, v["ret"] * 100, v["vol"] * 100, v["sharpe"]))

    # regimen
    print("[regimen] construyendo vector y buscando analogos...")
    reg, norm = R.construir_regimen(close)
    hoy = close.index[-1]
    analog = R.analogos(norm, hoy, n=cfg["regimen"]["n_analogos"],
                        dist_umbral=cfg["regimen"]["dist_umbral"])
    eval_reg = R.evaluar_analogos(close, analog, tuple(cfg["regimen"]["horizontes_dias"]))
    print("  analogos:", len(analog), "evaluacion:", eval_reg)

    # backtest
    print("[backtest] walk-forward %s rebalanceo %s ..." % (
        cfg["backtest"]["inicio"], cfg["backtest"]["rebalanceo"]))
    bt = B.walk_forward(close_pool,
                        lambda hist: O.construir_carteras(
                            hist, tipos=["long-only"], max_peso=cfg["optimizador"]["max_peso"]),
                        inicio=cfg["backtest"]["inicio"],
                        rebalanceo=cfg["backtest"]["rebalanceo"],
                        costo_bps=cfg["backtest"]["costo_bps"])
    print("  win-rate: %.0f%%  n_trades: %s" % (bt.get("win_rate", 0) * 100, bt.get("n_trades", 0)))

    resultado = {"universo": {"tier": args.tier, **u["stats"]},
                 "ciclo": est_ciclo,
                 "salud": df_salud, "factores": df_r2,
                 "pool": pool, "carteras": carteras,
                 "regimen": {"analogos_n": len(analog),
                             "dist_umbral": cfg["regimen"]["dist_umbral"],
                             "evaluacion": eval_reg},
                 "backtest": bt}
    path_md, path_json, txt = INF.escribir(resultado, nombre="portafolio_quant")
    print("\n[OK] Informe:", path_md)
    print("[OK] JSON  :", path_json)
    return resultado


def main():
    ap = argparse.ArgumentParser(description="Portafolio cuantitativo unificado")
    ap.add_argument("cmd", nargs="?", default="full",
                    choices=["universo", "carteras", "backtest", "full"])
    ap.add_argument("--tier", default="AB")
    ap.add_argument("--max-cedear", type=int, default=80,
                    help="limite de CEDEARs (0=todos, 80 rapido)")
    args = ap.parse_args()
    if args.cmd == "universo":
        cmd_universo(args)
    elif args.cmd == "full":
        cmd_full(args)
    else:
        cmd_full(args)


if __name__ == "__main__":
    main()
