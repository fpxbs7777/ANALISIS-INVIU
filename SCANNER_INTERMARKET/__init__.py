# -*- coding: utf-8 -*-
"""Paquete SCANNER_INTERMARKET: senales intermarket continuas, portable.

Uso desde otra app:
    import sys
    sys.path.insert(0, r"<ruta>/ANALISIS INVIU")
    from SCANNER_INTERMARKET import run_scan, cargar_cfg

    estado = run_scan(cargar_cfg(), quiet=True)
    print(estado["fase"]["name"], estado["senales_activas"])
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scanner import run_scan, cargar_cfg  # noqa: E402,F401
from lib_noticias import load_env  # noqa: E402,F401
import lib_mercado  # noqa: E402,F401
import lib_noticias  # noqa: E402,F401
import lib_eventos  # noqa: E402,F401

__all__ = ["run_scan", "cargar_cfg", "load_env", "lib_mercado",
           "lib_noticias", "lib_eventos"]
