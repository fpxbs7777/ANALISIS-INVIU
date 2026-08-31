# -*- coding: utf-8 -*-
"""SCANNER INTERMARKET — señales continuas (Murphy/Pring/Stovall + credito + noticias + eventos).

Uso:
    python scanner.py                 # un scan y sale
    python scanner.py --loop          # corre continuo cada intervalo_min
    python scanner.py --loop -i 30    # loop con intervalo propio (min)
    python scanner.py --quiet         # sin banner, solo senales nuevas

Salidas:
    estado_actual.json   -> snapshot completo para consumo externo (bots/dashboards)
    senales/senales_YYYYMMDD.csv -> log append de senales nuevas (dedup vs estado previo)
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import lib_mercado as mk
import lib_noticias as nt
import lib_eventos as ev

BASE = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(BASE, "estado_actual.json")
DIR_SENALES = os.path.join(BASE, "señales")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def cargar_cfg():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def cargar_estado_previo():
    if os.path.exists(ESTADO):
        try:
            return json.load(open(ESTADO, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def key_senal(s):
    return "%s|%s|%s" % (s["tipo"], s["id"], s.get("sentido", ""))


def run_scan(cfg, quiet=False):
    nt.load_env()
    ts = datetime.now(timezone.utc)
    previo = cargar_estado_previo()
    keys_previas = {key_senal(x) for x in previo.get("senales_activas", [])}

    tickers_ratio = [t for r in cfg["ratios"] for t in (r["num"], r["den"])]
    fase_inputs = {"b": ("TLT", None), "s": ("SPY", None), "c": ("GSG", None)}
    extra_t = list(dict.fromkeys(
        [t for _, (t, _) in fase_inputs.items()] +
        ["TLT", "SPY", "GSG"] + cfg["macro_extra"]))
    todos = sorted(set(tickers_ratio) | set(extra_t))

    errores = []
    try:
        close_main = mk.descargar(todos, period=cfg["main_period"])
    except Exception as e:
        close_main = None
        errores.append("descarga principal: %s" % e)
    try:
        close_credit = mk.descargar(["HYG", "LQD", "IEF"], start=cfg["credit_start"])
    except Exception as e:
        close_credit = None
        errores.append("descarga credito: %s" % e)

    ratios = []
    if close_main is not None:
        ratios = mk.evaluar_ratios(close_main, cfg["ratios"], cfg["roc_umbral_pct"],
                                   cfg["fast_ma"], cfg["slow_ma"])

    extras = {}
    for r in ratios:
        if r.get("fase_key"):
            extras[r["fase_key"]] = r["tend"]
    b_t, _ = mk.trend_num(close_main["TLT"], cfg["roc_umbral_pct"]) if close_main is not None and "TLT" in close_main.columns else (None, None)
    s_t, _ = mk.trend_num(close_main["SPY"], cfg["roc_umbral_pct"]) if close_main is not None and "SPY" in close_main.columns else (None, None)
    c_t, _ = mk.trend_num(close_main["GSG"], cfg["roc_umbral_pct"]) if close_main is not None and "GSG" in close_main.columns else (None, None)
    fase = mk.detectar_fase(b_t, s_t, c_t, extras) if close_main is not None else None

    credit = mk.credito(close_credit, cfg["credit_warning_pct"],
                        cfg["credit_critical_pct"], cfg["credit_stress_pct"]) if close_credit is not None else {"IG": None, "HY": None}
    vix = mk.vix_regime(close_main, cfg["vix_warn"], cfg["vix_alert"]) if close_main is not None else None

    try:
        noticias = nt.sentimiento_global(cfg["noticias_queries"], cfg["noticias_dias"])
    except Exception as e:
        noticias = []
        errores.append("noticias: %s" % e)

    try:
        eventos = ev.proximos_eventos(cfg["watchlist_portafolio"], cfg["eventos_dias"])
    except Exception as e:
        eventos = []
        errores.append("eventos: %s" % e)

    # ---------------- generacion de senales ----------------
    senales = []
    for r in ratios:
        if r["nuevo_cruce"]:
            sentido = "alcista" if r["ma"] == "alcista" else "bajista"
            senales.append({"nivel": "ALERTA" if r.get("fase_key") else "INFO",
                            "tipo": "RATIO_CRUCE", "id": r["id"], "sentido": sentido,
                            "texto": "%s (%s): cruce %s nuevo | ROC63 %+d%%" % (
                                r["id"], r["desc"], sentido, r["roc63"] or 0)})
    prev_fase = (previo.get("fase") or {}).get("num")
    if fase and prev_fase is not None and fase["num"] != prev_fase:
        rot = mk.SECTOR_ROTATION.get(fase["num"], {})
        senales.append({
            "nivel": "ALERTA", "tipo": "FASE_CICLO", "id": "fase",
            "sentido": fase["name"],
            "texto": "CAMBIO DE FASE: %s -> %s (conf %s). COMPRAR: %s | VENDER: %s" % (
                previo["fase"]["name"], fase["name"], fase["conf"],
                ", ".join(rot.get("comprar", [])) or "-", ", ".join(rot.get("vender", [])) or "-")})
    for k, d in (("IG", credit.get("IG")), ("HY", credit.get("HY"))):
        if not d:
            continue
        if d["nivel"].startswith("ALERTA"):
            senales.append({"nivel": "ALERTA", "tipo": "CREDITO", "id": k,
                            "sentido": d["nivel"],
                            "texto": "Credito %s en percentil %.0f%% (%s)" % (k, d["pct"], d["nivel"])})
        elif d["nivel"].startswith("WARN"):
            senales.append({"nivel": "WARN", "tipo": "CREDITO", "id": k,
                            "sentido": d["nivel"],
                            "texto": "Credito %s percentil %.0f%% elevado" % (k, d["pct"])})
    if vix and vix["nivel"] != "OK":
        senales.append({"nivel": "ALERTA" if "ALERTA" in vix["nivel"] else "WARN",
                        "tipo": "VIX", "id": "VIX", "sentido": vix["nivel"],
                        "texto": "VIX %.1f (z %.2f) %s" % (vix["valor"], vix["z252"], vix["nivel"])})
    neto_total = sum(n["neto"] for n in noticias)
    if noticias and neto_total <= -4:
        peores = min(noticias, key=lambda n: n["neto"])
        senales.append({"nivel": "WARN", "tipo": "SENTIMIENTO", "id": "news",
                        "sentido": "negativo",
                        "texto": "Sentimiento noticias neto %+d; cluster peor: %s (%+d)" % (
                            neto_total, peores["cluster"], peores["neto"])})
    for e in eventos[:5]:
        senales.append({"nivel": "INFO", "tipo": "EVENTO", "id": "%s_%s" % (e["ticker"], e["fecha"]),
                        "sentido": "catalizador",
                        "texto": "Earnings %s en %dd (%s) EPS est %s | beat 8Q %s" % (
                            e["ticker"], e["faltan_dias"], e["fecha"],
                            e["eps_est"], e["beat_rate_8q"])})

    nuevas = [s for s in senales if key_senal(s) not in keys_previas]

    estado = {
        "timestamp_utc": ts.isoformat(),
        "fase": fase,
        "ratios": [{k: r[k] for k in ("id", "desc", "tend", "roc63", "ma", "nuevo_cruce")} for r in ratios],
        "credito": credit,
        "vix": vix,
        "noticias": [{"cluster": n["cluster"], "n": n["n"], "neto": n["neto"]} for n in noticias],
        "noticias_neto_total": neto_total,
        "eventos": eventos,
        "senales_activas": senales,
        "errores": errores,
    }
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)

    if nuevas:
        os.makedirs(DIR_SENALES, exist_ok=True)
        path_csv = os.path.join(DIR_SENALES, "senales_%s.csv" % ts.strftime("%Y%m%d"))
        nuevo_archivo = not os.path.exists(path_csv)
        with open(path_csv, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if nuevo_archivo:
                w.writerow(["timestamp_utc", "nivel", "tipo", "id", "sentido", "texto"])
            for s in nuevas:
                w.writerow([ts.isoformat(), s["nivel"], s["tipo"], s["id"],
                            s.get("sentido", ""), s["texto"]])

    # ---------------- salida consola ----------------
    if not quiet:
        print("=" * 96)
        print("SCAN %s | FASE: %s (conf %s, match %s%%)" % (
            ts.strftime("%d/%m %H:%M"),
            fase["name"] if fase else "S/D",
            fase["conf"] if fase else "-",
            fase["match_pct"] if fase else "-"))
        if fase:
            print("   %s | sectores clave: %s" % (fase["desc"], fase["clave"]))
        print("-" * 96)
        for r in ratios:
            flecha = {1: "^", -1: "v", 0: "=", None: "?"}[r["tend"]]
            marca = " <<CRUCE NUEVO" if r["nuevo_cruce"] else ""
            print("   %-9s %-34s %s ROC63 %+6s%% | MA %s%s" % (
                r["id"], r["desc"][:34], flecha, r["roc63"], r["ma"], marca))
        ig, hy = credit.get("IG"), credit.get("HY")
        print("-" * 96)
        print("   Credito IG pctl %s%% [%s] | HY pctl %s%% [%s] | VIX %s" % (
            ig["pct"] if ig else "-", ig["nivel"] if ig else "-",
            hy["pct"] if hy else "-", hy["nivel"] if hy else "-",
            "%.1f z%+.1f [%s]" % (vix["valor"], vix["z252"], vix["nivel"]) if vix else "S/D"))
        print("   Noticias neto: %+d (%s)" % (
            neto_total, ", ".join("%s:%+d" % (n["cluster"], n["neto"]) for n in noticias)))
        if eventos:
            print("   Eventos <=%dd: %s" % (cfg["eventos_dias"], "; ".join(
                "%s(%dd)" % (e["ticker"], e["faltan_dias"]) for e in eventos[:6])))
        print("-" * 96)
        print("   SENALES NUEVAS: %d de %d activas%s" % (
            len(nuevas), len(senales), "" if nuevas else " (sin cambios)"))
        for s in nuevas:
            print("   [%s] %s/%s: %s" % (s["nivel"], s["tipo"], s["id"], s["texto"]))
        for err in errores:
            print("   [ERROR] %s" % err)
        print("=" * 96)
    return estado


def main():
    ap = argparse.ArgumentParser(description="Scanner intermarket continuo")
    ap.add_argument("--loop", action="store_true", help="correr indefinidamente")
    ap.add_argument("-i", "--intervalo", type=int, default=None,
                    help="minutos entre scans (override config)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    cfg = cargar_cfg()
    intervalo = args.intervalo or cfg.get("intervalo_min", 15)

    if not args.loop:
        run_scan(cfg, args.quiet)
        return

    print("[SCANNER] modo continuo cada %d min. Ctrl+C para salir." % intervalo)
    while True:
        inicio = time.time()
        try:
            run_scan(cfg, args.quiet)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("[SCANNER ERROR] %s" % e)
        espera = max(30, intervalo * 60 - (time.time() - inicio))
        time.sleep(espera)


if __name__ == "__main__":
    main()
