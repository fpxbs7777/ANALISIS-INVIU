# -*- coding: utf-8 -*-
"""Orquestador del scanner: intermarket + earnings + EPS + screener (loop intraday)."""
import argparse
import json
import os
import sys
import time
from datetime import datetime

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scanner.fase_ciclo import obtener_fase
from scanner.alertas_macro import evaluar_alertas
from scanner.senales_nucleo import obtener_senales, detectar_cambios
from scanner.notificador import enviar_telegram, enviar_si_cambia

CFG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
ESTADO_DIR = os.path.join(os.path.dirname(__file__), "estado")
SINALES_PREV = os.path.join(ESTADO_DIR, "senales_previo.csv")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def cargar_config():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def dentro_horario(cfg):
    import datetime as dt
    h = cfg.get("horario_us", {})
    ini = h.get("inicio", "13:30")
    fin = h.get("fin", "22:00")
    dias = set(h.get("dias", [0, 1, 2, 3, 4]))
    ahora = datetime.now()
    if ahora.weekday() not in dias:
        return False
    def hm(s):
        hh, mm = map(int, s.split(":"))
        return hh * 60 + mm
    cur = ahora.hour * 60 + ahora.minute
    return hm(ini) <= cur <= hm(fin)


def ciclo_once(force=False):
    cfg = cargar_config()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M ART")
    # --- fase + señales ---
    liderazgo, etapa, fuente, ctx = obtener_fase(usar_json=False, periodo=cfg.get("fase_ciclo", {}).get("periodo", "6y"))
    alertas = evaluar_alertas(ctx)
    df_sen = obtener_senales(periodo=cfg.get("senal", {}).get("periodo", "4y"))
    # comparar con previo
    df_prev = pd.read_csv(SINALES_PREV) if os.path.exists(SINALES_PREV) else None
    cambios = detectar_cambios(df_sen, df_prev)
    # persistir
    os.makedirs(ESTADO_DIR, exist_ok=True)
    df_sen.to_csv(SINALES_PREV, index=False, encoding="utf-8-sig")
    historico = os.path.join(ESTADO_DIR, "senales_historico.csv")
    df_sen.assign(fecha=fecha).to_csv(historico, mode="a", header=not os.path.exists(historico), index=False, encoding="utf-8-sig")

    # --- mensaje intermarket ---
    orden = sorted(liderazgo.items(), key=lambda kv: kv[1], reverse=True)
    top3 = ", ".join("%s %+0.1f" % (k, v) for k, v in orden[:3])
    msg_inter = (
        "*SCANNER INTERMARKET* — %s\n"
        "*Fase:* %s  _(fuente: %s)_\n"
        "*Liderazgo 200d:* %s\n"
        "*Alertas:* %s\n"
        "*Cambios:* %s\n"
        % (fecha, etapa, fuente, top3,
           ", ".join("%s %s" % ("🔴" if a else "🟢", k) for k, (a, _) in alertas.items()) or "—",
           ", ".join("%s %s→%s" % (cid, prev or "—", cur) for cid, prev, cur in cambios[:8]) if cambios else "sin cambios"))
    fila_sen = df_sen[df_sen["accion"].str.contains("CAMBIO|MANTENER|ROTAR", na=False)].head(10)
    if not fila_sen.empty:
        msg_inter += "\n" + "\n".join("`%s` %s %s" % (r["id"], r["regla_oro"], r["accion"]) for _, r in fila_sen.iterrows())

    # enviar con dedup
    sent = []
    ok, _ = enviar_si_cambia("intermarket", msg_inter, force=force)
    sent.append(("intermarket", ok))

    # --- screener (solo primera del día o force) ---
    hoy = datetime.now().date().isoformat()
    flag_screener = os.path.join(ESTADO_DIR, "screener_%s.done" % hoy)
    if force or not os.path.exists(flag_screener):
        try:
            from scanner.screener_dia import ejecutar as screener_ejecutar
            df_scr, finals = screener_ejecutar(liderazgo, verbose=False)
            out = os.path.join(ESTADO_DIR, "resumen_empresas_%s.csv" % hoy)
            df_scr.to_csv(out, index=False, encoding="utf-8-sig")
            msg_scr = "*SCREENER ROTACIÓN* %s\nTop por industria:\n" % hoy
            for (etf, ind), tks in list(finals.items())[:12]:
                msg_scr += "`%s|%s` %s\n" % (etf, ind[:24], ", ".join(tks))
            enviar_si_cambia("screener_%s" % hoy, msg_scr, force=force)
            sent.append(("screener", True))
            open(flag_screener, "w").close()
        except Exception as e:
            msg = "*SCREENER* error: %s" % str(e)[:400]
            enviar_telegram(msg)
            sent.append(("screener_error", True))

    # --- earnings ---
    try:
        from scanner.earnings import ejecutar as earn_ej, formatear as earn_fmt
        filas = earn_ej()
        msg_earn = earn_fmt(filas)
        enviar_si_cambia("earnings_%s" % hoy, msg_earn, force=force)
        sent.append(("earnings", True))
    except Exception as e:
        print("earnings error:", e)

    # --- EPS (solo con screener) ---
    try:
        if not os.path.exists(flag_screener) or force:
            from scanner.analisis_eps import ejecutar as eps_ej, formatear as eps_fmt
            uni = []
            for v in (finals if "finals" in locals() else {}).values():
                uni.extend(v)
            lista = eps_ej(uni[:20])
            msg_eps = eps_fmt(lista)
            enviar_si_cambia("eps_%s" % hoy, msg_eps, force=force)
            sent.append(("eps", True))
    except Exception as e:
        print("eps error:", e)

    # log
    os.makedirs(LOG_DIR, exist_ok=True)
    logf = os.path.join(LOG_DIR, "scanner_%s.log" % datetime.now().strftime("%Y%m%d"))
    with open(logf, "a", encoding="utf-8") as f:
        f.write("[%s] sent=%s cambios=%d\n" % (fecha, sent, len(cambios)))
    print("ciclo %s | sent=%s | cambios=%d" % (fecha, sent, len(cambios)))
    return {"cambios": cambios, "sent": sent}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="una corrida y salir")
    ap.add_argument("--json", action="store_true", help="usar contexto_actual.json")
    ap.add_argument("--force", action="store_true", help="forzar envío aunque no haya cambios")
    args = ap.parse_args()
    if args.once:
        ciclo_once(force=args.force)
        return
    cfg = cargar_config()
    freq = int(cfg.get("frecuencia_min", 30))
    print("Scanner loop cada %d min. Ctrl+C para salir." % freq)
    while True:
        if dentro_horario(cfg):
            try:
                ciclo_once()
            except Exception as e:
                print("ciclo error:", e)
                try:
                    enviar_telegram("*SCANNER ERROR* `%s`" % str(e)[:400])
                except Exception:
                    pass
        else:
            print(datetime.now().strftime("%H:%M"), "fuera de horario, duerme 30 min")
        time.sleep(freq * 60)
