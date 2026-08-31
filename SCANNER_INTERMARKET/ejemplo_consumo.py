# -*- coding: utf-8 -*-
"""Ejemplos de integracion del kit en otra aplicacion.

A) Consumo via HTTP (api_server.py corriendo)
B) Consumo directo como paquete Python
C) Lectura plana del snapshot JSON
"""
import json
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))


def via_http():
    req = urllib.request.Request("http://localhost:5010/estado")
    with urllib.request.urlopen(req, timeout=10) as r:
        estado = json.load(r)
    print("[HTTP] fase:", (estado.get("fase") or {}).get("name"))
    for s in estado.get("senales_activas", []):
        print("  [%s] %s: %s" % (s["nivel"], s["tipo"], s["texto"]))


def como_paquete():
    sys.path.insert(0, os.path.dirname(BASE))
    from SCANNER_INTERMARKET import cargar_cfg, load_env, run_scan
    load_env()
    estado = run_scan(cargar_cfg(), quiet=True)
    print("[PKG ] fase:", (estado["fase"] or {}).get("name"),
          "| senales activas:", len(estado["senales_activas"]))
    return estado


def lectura_plana():
    with open(os.path.join(BASE, "estado_actual.json"), encoding="utf-8") as f:
        estado = json.load(f)
    print("[FILE] ratios con cruce nuevo:",
          [r["id"] for r in estado["ratios"] if r["nuevo_cruce"]])


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "plana"
    {"http": via_http, "paquete": como_paquete, "plana": lectura_plana}[modo]()
