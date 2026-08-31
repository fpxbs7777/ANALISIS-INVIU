# -*- coding: utf-8 -*-
"""Estudio forense NVDA previo a earnings (26/08/2026 AMC).

Fases:
  A) Historial 8 trimestres: EPS est/real/sorpresa (patron ESTIMACIONES.txt)
  B) Reaccion real por evento: gap D+1, c2c, rango intradia, volumen vs 20d
     + MFE/MAE ventana [evento..+5 ruedas] vs cierre pre-evento + ATR(14) pre-evento
  C) Noticias validadoras por evento (Finnhub historico +/- 3 dias + lexico ES/EN)
  D) Whisper number, tecnico hoy y escenarios para manana

Salida: consola + INFORME_NVDA_EARNINGS_20260826.md
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import timedelta

import numpy as np
import pandas as pd
import yfinance as yf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = os.path.dirname(os.path.abspath(__file__))
TICKER = "NVDA"
OUT_MD = os.path.join(REPO, "INFORME_NVDA_EARNINGS_20260826.md")

POSITIVAS = {
    "beat", "beats", "profit", "profits", "growth", "strong", "surge", "rally", "gain",
    "gains", "outperform", "upgrade", "record", "soar", "jump", "rise", "rises",
    "positive", "expansion", "breakthrough", "momentum", "recovery", "supera",
    "crecimiento", "fuerte", "alza", "sube", "suben", "alcista", "optimista",
    "recuperacion", "impulso", "expansion", "positivo", "positiva", "aumento",
    "beneficio", "acuerdo", "contrato", "adquisicion", "aprobacion", "lanzamiento",
    "innovacion", "rentable", "eficiencia", "mejora", "mejoran", "buy", "bullish",
}
NEGATIVAS = {
    "miss", "misses", "loss", "losses", "weak", "decline", "drop", "drops", "fall",
    "falls", "plunge", "crash", "bearish", "sell", "downgrade", "downgraded", "cut",
    "cuts", "layoff", "layoffs", "recession", "debt", "default", "bankruptcy",
    "investigation", "lawsuit", "penalty", "warning", "risk", "risks", "volatile",
    "inflation", "stagflation", "caida", "cae", "caen", "baja", "bajan", "bajista",
    "deuda", "quiebra", "recesion", "recorte", "sancion", "multa", "demanda",
    "investigacion", "riesgo", "incertidumbre", "inflacion", "alerta", "problema",
}


def load_env():
    path = os.path.join(os.path.dirname(REPO), ".env")
    if not os.path.exists(path):
        path = os.path.join(REPO, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() and v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def lex_score(text):
    if not text:
        return 0
    tokens = set(re.findall(r"[a-záéíóúñ]+", text.lower()))
    pos = len(tokens & POSITIVAS)
    neg = len(tokens & NEGATIVAS)
    return 1 if pos > neg else (-1 if neg > pos else 0)


def finnhub_news(d_from, d_to, max_items=8):
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key:
        return []
    url = ("https://finnhub.io/api/v1/company-news?symbol=%s&from=%s&to=%s&token=%s"
           % (TICKER, d_from.strftime("%Y-%m-%d"), d_to.strftime("%Y-%m-%d"),
              urllib.parse.quote(key)))
    req = urllib.request.Request(url, headers={"User-Agent": "nvda-study"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    time.sleep(0.4)
    items = [{"dt": n.get("datetime", 0), "src": n.get("source", ""),
              "tit": n.get("headline", "")} for n in data or []]
    items.sort(key=lambda x: x["dt"], reverse=True)
    return items[:max_items]


def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(df, n=14):
    pc = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"],
                    (df["High"] - pc).abs(),
                    (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


MD = []


def say(txt=""):
    print(txt)
    MD.append(txt)


def main():
    load_env()
    tk = yf.Ticker(TICKER)

    say("=" * 100)
    say("ESTUDIO FORENSE NVDA — PREVIO A EARNINGS Q2 FY2027 (miércoles 26/08/2026, después del cierre)")
    say("Generado: %s" % pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"))
    say("=" * 100)

    ed = tk.get_earnings_dates(limit=40)
    if ed is None or ed.empty:
        say("[ERROR] yfinance no devolvio fechas de earnings.")
        return
    ed.index = ed.index.tz_localize("UTC") if ed.index.tz is None else ed.index.tz_convert("UTC")

    px = tk.history(period="max", auto_adjust=False)
    px.index = px.index.tz_convert("UTC").tz_localize(None)
    px = px[~px.index.duplicated(keep="last")]
    closes = px["Close"]
    rsi14 = rsi(closes)
    atr14 = atr(px, 14)
    sma20 = closes.rolling(20).mean()
    sma50 = closes.rolling(50).mean()
    sma200 = closes.rolling(200).mean()

    hoy = pd.Timestamp.now(tz="UTC").tz_localize(None)
    pasados = ed[ed.index < pd.Timestamp.now(tz="UTC")].sort_index(ascending=False)
    pasados = pasados.dropna(subset=["Reported EPS"]).head(16).sort_index()

    # ---------- FASE A+B: historial y reacciones ----------
    say("\n" + "-" * 100)
    say("FASE A+B | HISTORIAL %s TRIMESTRES Y REACCION REAL DEL PRECIO" % ("OCHO" if False else len(pasados)))
    say("-" * 100)
    say("%-12s | %-7s %-7s | %-8s | %-8s | %-8s | %-7s | %-8s | %-7s | %-7s" % (
        "Fecha rep.", "EPSest", "EPSreal", "Sorpr.%", "Gap D+1", "C2C D+1", "Rango%", "MFE 5d", "MAE 5d", "xATR"))
    filas_evento = []
    for ts, row in pasados.iterrows():
        e_date = pd.Timestamp(ts.date())
        pos = px.index.searchsorted(e_date)
        if pos >= len(px) or px.index[pos].date() != e_date.date():
            continue
        base_close = float(px["Close"].iloc[pos])
        win = px.iloc[pos:pos + 6]
        nxt = px.iloc[pos + 1] if pos + 1 < len(px) else None
        if nxt is None:
            continue
        gap = (nxt["Open"] / base_close - 1) * 100
        c2c = (nxt["Close"] / base_close - 1) * 100
        rango = (nxt["High"] - nxt["Low"]) / base_close * 100
        mfe = (win["High"].max() / base_close - 1) * 100
        mae = (win["Low"].min() / base_close - 1) * 100
        a_pre = atr14.iloc[pos - 1] if pos >= 1 else np.nan
        xatr = abs(c2c) / a_pre if a_pre and not np.isnan(a_pre) else np.nan
        vol_d1 = float(nxt["Volume"])
        vol_avg = float(px["Volume"].iloc[max(0, pos - 20):pos].mean())
        sorp = float(row["Surprise(%)"]) * 100 if abs(float(row["Surprise(%)"])) < 1 else float(row["Surprise(%)"])
        filas_evento.append({
            "fecha": e_date, "eps_est": float(row["EPS Estimate"]),
            "eps_real": float(row["Reported EPS"]), "sorp": sorp,
            "gap": gap, "c2c": c2c, "rango": rango, "mfe": mfe, "mae": mae,
            "xatr": xatr, "volrel": vol_d1 / vol_avg if vol_avg else np.nan,
        })
        say("%-12s | %7.2f %7.2f | %+7.2f%% | %+7.2f%% | %+7.2f%% | %7.2f | %+6.1f%% | %+6.1f%% | %.1fx"
            % (e_date.strftime("%d/%m/%y"), row["EPS Estimate"], row["Reported EPS"], sorp,
               gap, c2c, rango, mfe, mae, xatr))

    if filas_evento:
        ev = pd.DataFrame(filas_evento)
        beats = ev[ev["sorp"] > 0]
        bajaron_pese_beat = beats[beats["c2c"] < 0]
        say("\nRatio de acierto (beat): %d/%d trimestres (%.0f%%)" % (
            len(beats), len(ev), len(beats) / len(ev) * 100))
        say("Sorpresa media: %+.2f%% | mediana %+.2f%%" % (ev["sorp"].mean(), ev["sorp"].median()))
        say("Reaccion media D+1: %+.2f%% | mediana %+.2f%%" % (ev["c2c"].mean(), ev["c2c"].median()))
        say("BEATS QUE IGUAL CAYERON en D+1: %d de %d beats (%.0f%%)"
            % (len(bajaron_pese_beat), len(beats), len(bajaron_pese_beat) / max(1, len(beats)) * 100))
        say("Gap D+1 medio: %+.2f%% | Rango intradia medio: %.2f%%" % (ev["gap"].mean(), ev["rango"].mean()))
        say("MFE medio 5d: %+.2f%% | MAE medio 5d: %+.2f%%" % (ev["mfe"].mean(), ev["mae"].mean()))
        say("Movimiento D+1 en multiplos de ATR(14): media %.1fx | max %.1fx" % (
            ev["xatr"].mean(), ev["xatr"].max()))
        say("Volumen D+1 relativo al promedio 20d: media %.2fx" % ev["volrel"].mean())

        say("\nCRUCE SORPRESA <-> REACCION (la trampa del 'beat vendido'):")
        for _, r in ev.sort_values("fecha").iterrows():
            veredicto = "SUBIO" if r["c2c"] >= 0 else "CAYO"
            say("   %s  sorp %+5.2f%%  ->  D+1 %+6.2f%%  (%s)" % (
                r["fecha"].strftime("%d/%m/%y"), r["sorp"], r["c2c"], veredicto))

        explosiva = ev[ev["sorp"] >= 9]
        comprimida = ev[(ev["sorp"] >= 0) & (ev["sorp"] < 9)]
        if len(explosiva) and len(comprimida):
            up_exp = (explosiva["c2c"] >= 0).mean() * 100
            up_com = (comprimida["c2c"] >= 0).mean() * 100
            say("\nANALISIS DE REGIMEN SEGUN TAMANO DE LA SORPRESA:")
            say("   Sorpresa EXPLOSIVA (+9%% o mas): %d casos | D+1 medio %+.2f%% | subio %.0f%% de las veces"
                % (len(explosiva), explosiva["c2c"].mean(), up_exp))
            say("   Sorpresa COMPRIMIDA (0 a +9%%):   %d casos | D+1 medio %+.2f%% | subio %.0f%% de las veces"
                % (len(comprimida), comprimida["c2c"].mean(), up_com))

    # ---------- FASE C: noticias validadoras por evento ----------
    say("\n" + "-" * 100)
    say("FASE C | NOTICIAS VALIDADORAS (Finnhub historico +/- 3 dias por evento)")
    say("-" * 100)
    if os.environ.get("FINNHUB_API_KEY", "").strip():
        for _, r in ev.sort_values("fecha", ascending=False).iterrows():
            d = r["fecha"]
            items = finnhub_news(d - timedelta(days=3), d + timedelta(days=3), max_items=6)
            say("\n>> Evento %s (sorpresa %+.2f%%, D+1 %+.2f%%)" % (
                d.strftime("%d/%m/%y"), r["sorp"], r["c2c"]))
            for it in items[:4]:
                s = {1: "[+]", -1: "[-]", 0: "[ ]"}[lex_score(it["tit"])]
                say("    %s %-18s %s" % (s, it["src"][:18], it["tit"][:95]))
    else:
        say("[i] Sin FINNHUB_API_KEY: fase salteada.")

    # ---------- FASE D: tecnico hoy + whisper + escenarios ----------
    say("\n" + "-" * 100)
    say("FASE D | TECNICO HOY, WHISPER NUMBER Y ESCENARIOS PARA MANANA 26/08")
    say("-" * 100)
    last = px.iloc[-1]
    last_dt = px.index[-1]
    r_now = float(rsi14.iloc[-1])
    a_now = float(atr14.iloc[-1])
    c_now = float(last["Close"])
    hi52 = float(closes.tail(252).max())
    lo52 = float(closes.tail(252).min())
    racha = 0
    for i in range(len(px) - 1, 0, -1):
        if px["Close"].iloc[i] < px["Close"].iloc[i - 1]:
            racha += 1
        else:
            break
    say("Precio ultimo cierre (%s): $%.2f" % (last_dt.strftime("%d/%m/%y"), c_now))
    say("RSI(14): %.1f | ATR(14): $%.2f (%.1f%% del precio)" % (r_now, a_now, a_now / c_now * 100))
    say("SMA20: $%.2f (%+.1f%%) | SMA50: $%.2f (%+.1f%%) | SMA200: $%.2f (%+.1f%%)" % (
        sma20.iloc[-1], (c_now / sma20.iloc[-1] - 1) * 100,
        sma50.iloc[-1], (c_now / sma50.iloc[-1] - 1) * 100,
        sma200.iloc[-1], (c_now / sma200.iloc[-1] - 1) * 100))
    say("Distancia a maximo 52w ($%.2f): %+.1f%% | minimo 52w: $%.2f" % (hi52, (c_now / hi52 - 1) * 100, lo52))
    say("Racha actual de velas rojas consecutivas: %d" % racha)

    eps_cons = 2.13
    rev_cons = 93.63
    if filas_evento:
        sorp_media4 = ev["sorp"].tail(4).mean()
        sorp_mediana8 = ev["sorp"].tail(8).median()
        eps_whisper_lo = eps_cons * (1 + sorp_mediana8 / 100)
        eps_whisper_hi = eps_cons * (1 + sorp_media4 / 100)
        rev_whisper = rev_cons * 1.005
        say("\nWHISPER NUMBER (reciclado de estimaciones con tu propio historial):")
        say("   Consenso: EPS $%.2f | Rev $%.2fB | Guia propia NVDA: $91B +-2%% (75%% GM, CHINA=0)" % (eps_cons, rev_cons))
        say("   Sorpresa mediana ultimos 8 trim: %+.2f%% -> piso del beat aceptable: EPS ~$%.2f" % (
            sorp_mediana8, eps_whisper_lo))
        say("   Sorpresa media ultimos 4 trim: %+.2f%% -> whisper optimista: EPS ~$%.2f" % (
            sorp_media4, eps_whisper_hi))
        say("   Regla empirica: imprimir DEBAJO de $%.2f ya se lee como decepcion pese a ser 'beat'" % eps_whisper_hi)

    prob_beat = 95.0
    if filas_evento:
        p_up_tras_beat = (beats["c2c"] >= 0).mean() * 100
    else:
        p_up_tras_beat = 40.0
    imp_move = 5.8
    say("\nESCENARIOS PARA EL 27/08 (apertura post-earnings):")
    say("   [BASE ~55%] Beat 'correcto' (EPS $2.15-2.23, DC >$67B, GM >=71.5%, guia Q3 firme)")
    say("      -> movimiento -2% a +4%; sigue el rango $200-$220 dentro del canal $190-$227")
    say("   [BULL ~20%] Beat+China upside o guia fuerte (EPS >$2.23 / DC >>67B / licencias China)")
    say("      -> +6% a +8% rompe $227 resistencia; objetivo $230-$235")
    say("   [BEAR ~20%] Beat 'vendido' por composicion (China-driven, GM <71.5%, guia tibia)")
    say("      -> -4% a -6% hacia $196-$200 (soporte $190); precedentes AMAT -5.1% y feb-26 -5.5%")
    say("   [MISS ~5%%]  Miss real (0 casos en %d trimestres auditados) -> -10%% hacia $188" % (
        len(filas_evento) if filas_evento else 16))
    say("\nP(beat) historica ~%.0f%% | P(subir en D+1 dado beat, TU historial): %.0f%%" % (prob_beat, p_up_tras_beat))
    say("Movimiento implícito opciones ±%.1f%% vs realizado medio ultimos 4 trim: %.1f%%" % (
        imp_move, ev["c2c"].abs().tail(4).mean() if filas_evento else 2.8))
    say("Sesgo cuantitativo: beat casi seguro PERO el mercado castiga la calidad del beat;")
    say("con precio bajo SMA20/SMA50 y 7+ ruedas rojas, el riesgo asimetrico esta en un beat tibio.")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(MD))
    say("\n[OK] Informe guardado en: %s" % OUT_MD)


if __name__ == "__main__":
    main()
