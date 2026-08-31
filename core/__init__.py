# -*- coding: utf-8 -*-
"""core: funciones compartidas de datos, correlacion, ratios y senales.

Extraidas de intermarket_parte1.py, cap1_murphy_aplicado.py,
intermarket_parte2_3.py, intermarket_parte4_6_7.py, intermarket_parte5.py,
intermarket_ratios.py y generar_senales.py (sin duplicacion).
"""
from core.data import load
from core.corr import corr_lag, best_lag
from core.ratio import WINS, ratio_series, window_stats, analyze_pair, ratio_stats
from core.senales import direc, regla_oro, accion, apply_rules

__all__ = [
    "load", "corr_lag", "best_lag",
    "WINS", "ratio_series", "window_stats", "analyze_pair", "ratio_stats",
    "direc", "regla_oro", "accion", "apply_rules",
]