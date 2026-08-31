# -*- coding: utf-8 -*-
"""Ciclo: envuelve SCANNER_INTERMARKET para obtener fase, rotacion y sentimiento por sector."""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
KIT = os.path.join(REPO, "SCANNER_INTERMARKET")
for p in (KIT, REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from SCANNER_INTERMARKET import cargar_cfg as kit_cfg, load_env as kit_env
    from SCANNER_INTERMARKET.lib_mercado import detectar_fase as _det_fase
    _KIT_OK = True
except Exception:
    _KIT_OK = False


def estado_ciclo():
    if not _KIT_OK:
        return {"fase": None, "fase_num": None, "conf": None}
    cfg = kit_cfg()
    kit_env()
    # usa el ultimo estado ya computado si existe (mas rapido)
    est_path = os.path.join(KIT, "estado_actual.json")
    if os.path.exists(est_path):
        try:
            est = json.load(open(est_path, encoding="utf-8"))
            fase = est.get("fase")
            if fase:
                return {"fase": fase["name"], "fase_num": fase["num"],
                        "conf": fase.get("conf"), "raw": est}
        except Exception:
            pass
    # fallback: corre un scan rapido quiet
    try:
        from SCANNER_INTERMARKET import run_scan
        est = run_scan(cfg, quiet=True)
        fase = est.get("fase", {}) if isinstance(est, dict) else {}
        return {"fase": fase.get("name"), "fase_num": fase.get("num"),
                "conf": fase.get("conf"), "raw": est}
    except Exception as e:
        return {"fase": None, "error": str(e)}


SECTORES_POR_FASE = {
    0: ["XLU", "XLP", "XLV", "GLD", "TLT"],
    1: ["XLK", "XLY", "IWM", "XLF", "QQQ"],
    2: ["XLI", "XLB", "XLF", "XLE", "COPX"],
    3: ["XLE", "GLD", "DBA", "XLV", "XLU"],
    4: ["XLV", "XLP", "XLU", "GLD", "TLT"],
    5: ["TLT", "GLD", "BIL"],
}
