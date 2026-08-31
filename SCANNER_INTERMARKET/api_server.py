# -*- coding: utf-8 -*-
"""API HTTP del scanner — solo stdlib (http.server), cero dependencias extra.

Endpoints:
    GET /health   -> {ok, fase, listo}
    GET /estado   -> estado_actual.json completo (snapshot del ultimo scan)
    GET /senales?dias=1 -> señales nuevas de los ultimos N dias (JSON)
    POST /scan    -> dispara un scan inmediato en background

Uso:
    python api_server.py            # puerto 5010 + scan automatico al arrancar
    python api_server.py --port 8080 --no-autostart
"""
import argparse
import csv
import json
import os
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(BASE, "estado_actual.json")
DIR_SENALES = os.path.join(BASE, "señales")

_lock = threading.Lock()
_scan_thread = None


def disparar_scan():
    def worker():
        with _lock:
            try:
                sys_path_setup()
                from scanner import cargar_cfg, load_env, run_scan
                load_env()
                run_scan(cargar_cfg(), quiet=True)
            except Exception as e:
                print("[API] error en scan: %s" % e)
    global _scan_thread
    if _scan_thread and _scan_thread.is_alive():
        return False
    _scan_thread = threading.Thread(target=worker, daemon=True)
    _scan_thread.start()
    return True


def sys_path_setup():
    parent = os.path.dirname(BASE)
    if parent not in __import__("sys").path:
        __import__("sys").path.insert(0, parent)


def leer_estado():
    if not os.path.exists(ESTADO):
        return {"listo": False, "msg": "aun no hay scans; espera o haz POST /scan"}
    with open(ESTADO, encoding="utf-8") as f:
        return json.load(f)


def leer_senales(dias=1):
    out = []
    hoy = datetime.now()
    for d in range(max(1, dias)):
        dia = (hoy - timedelta(days=d)).strftime("%Y%m%d")
        path = os.path.join(DIR_SENALES, "senales_%s.csv" % dia)
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                out.append(row)
    return out


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        try:
            if url.path == "/health":
                est = leer_estado()
                self._json({"ok": True,
                            "listo": bool(est.get("listo", True)),
                            "fase": (est.get("fase") or {}).get("name"),
                            "timestamp": est.get("timestamp_utc")})
            elif url.path == "/estado":
                self._json(leer_estado())
            elif url.path == "/senales":
                dias = int(qs.get("dias", ["1"])[0])
                self._json({"n": len(s := leer_senales(dias)), "senales": s})
            else:
                self._json({"error": "endpoint desconocido",
                            "rutas": ["/health", "/estado", "/senales?dias=N",
                                      "POST /scan"]}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        if urlparse(self.path).path == "/scan":
            lanzado = disparar_scan()
            self._json({"aceptado": True, "ya_corriendo": not lanzado})
        else:
            self._json({"error": "solo POST /scan"}, 404)

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5010)
    ap.add_argument("--no-autostart", action="store_true")
    args = ap.parse_args()

    if not args.no_autostart:
        disparar_scan()

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("[API] Scanner escuchando en http://localhost:%d" % args.port)
    print("[API] /health /estado /senales?dias=N | POST /scan")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
