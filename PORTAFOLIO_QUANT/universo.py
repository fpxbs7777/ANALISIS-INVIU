# -*- coding: utf-8 -*-
"""Universo: parsea unificado_completo.json -> Tier A+B liquido.

Normaliza tickers, dedupplica y clasifica segun reglas documentadas
en README del kit. Reutiliza ideas de motor/02_validacion_r2.py
para mapear a simbolos yfinance.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)


def _underlying_cedear(ticker, moneda):
    base = ticker.split(".")[0].upper().strip()
    if moneda == "USD" and base.endswith("C") and len(base) > 2:
        return base[:-1]
    if moneda == "USD" and base.endswith("D") and len(base) > 2:
        return base[:-1]
    return base


def cargar_universo(json_path=None, tier="AB", max_arg=0, max_cedear=120):
    if json_path is None:
        json_path = os.path.join(REPO, "unificado_completo - copia.json")
    if not os.path.isabs(json_path) and not os.path.exists(json_path):
        alt = os.path.join(REPO, json_path)
        if os.path.exists(alt):
            json_path = alt
    data = json.load(open(json_path, encoding="utf-8"))
    sectores = data.get("sectores", {})

    args = {}
    for sec, payload in sectores.items():
        for ind, arr in payload.get("industrias", {}).items():
            if ind == "etfs":
                continue
            for t in arr:
                if t.get("tipo") != "accion" or t.get("pais") != "Argentina":
                    continue
                if t.get("mercado") != "BCBA":
                    continue
                raw = t.get("ticker", "").strip()
                if not raw:
                    continue
                moneda = t.get("moneda", "ARS")
                base = raw.split(".")[0].upper()
                if moneda == "USD" and base.endswith("D") and len(base) > 2:
                    base = base[:-1]
                yf = base + ".BA"
                if yf not in args:
                    args[yf] = {"ticker_yf": yf, "sector": sec, "industria": ind,
                                "nombre": t.get("nombre", ""), "base": base}

    ceds = {}
    for sec, payload in sectores.items():
        for ind, arr in payload.get("industrias", {}).items():
            if ind == "etfs":
                continue
            for t in arr:
                if t.get("tipo") != "cedear":
                    continue
                raw = t.get("ticker", "").strip()
                if not raw:
                    continue
                moneda = t.get("moneda", "ARS")
                base = _underlying_cedear(raw, moneda)
                if base not in ceds:
                    ceds[base] = {"ticker_yf": base, "sector": sec, "industria": ind,
                                  "nombre": t.get("nombre", ""), "base": base,
                                  "moneda_origen": moneda}

    lista_arg = sorted(args.values(), key=lambda x: x["base"])
    # ranking CEDEAR por frecuencia de aparicion (proxy liquidez)
    from collections import Counter
    freq = Counter()
    for sec, payload in sectores.items():
        for arr in payload.get("industrias", {}).values():
            if isinstance(arr, list):
                for t in arr:
                    if t.get("tipo") == "cedear":
                        freq[_underlying_cedear(t.get("ticker",""), t.get("moneda",""))] += 1
    lista_ced = sorted(ceds.values(), key=lambda x: (-freq.get(x["base"], 0), x["base"]))

    if max_arg and max_arg > 0:
        lista_arg = lista_arg[:max_arg]
    if max_cedear and max_cedear > 0:
        lista_ced = lista_ced[:max_cedear]

    etfs = []
    return {"arg": lista_arg, "cedear": lista_ced, "etfs": etfs,
            "stats": {"n_arg": len(lista_arg), "n_cedear": len(lista_ced),
                      "n_total": len(lista_arg) + len(lista_ced)}}


if __name__ == "__main__":
    u = cargar_universo(tier="AB", max_cedear=120)
    print("ARG:", len(u["arg"]), [x["ticker_yf"] for x in u["arg"][:12]])
    print("CEDEAR top 12:", [x["ticker_yf"] for x in u["cedear"][:12]])
    print("Stats:", u["stats"])
