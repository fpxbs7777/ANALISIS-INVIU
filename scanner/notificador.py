# -*- coding: utf-8 -*-
"""Envío a Telegram con dedup por hash (estado/ultimo_envio.json)."""
import argparse
import hashlib
import json
import os
import urllib.request
import urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ESTADO_PATH = os.path.join(os.path.dirname(__file__), "estado", "ultimo_envio.json")


def cargar_config():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def enviar_telegram(texto, parse_mode="Markdown", token=None, chat_id=None):
    cfg = cargar_config()
    tok = token or cfg["telegram"]["token"]
    cid = chat_id or cfg["telegram"]["chat_id"]
    pm = parse_mode if parse_mode is not None else cfg["telegram"].get("parse_mode", "Markdown")
    url = "https://api.telegram.org/bot%s/sendMessage" % tok
    # Telegram impone 4096 chars
    if len(texto) > 4000:
        texto = texto[:4000] + "\n…(truncado)"
    def _post(pm_val):
        payload = {"chat_id": cid, "text": texto, "disable_web_page_preview": cfg["telegram"].get("disable_web_page_preview", True)}
        if pm_val:
            payload["parse_mode"] = pm_val
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read().decode())
        if not body.get("ok"):
            raise RuntimeError("Telegram error: %s" % body)
        return body
    try:
        return _post(pm)
    except urllib.error.HTTPError as e:
        if pm and e.code == 400:
            return _post(None)
        raise


def enviar_si_cambia(clave, texto, force=False):
    """Solo envía si el hash cambió desde la última vez (dedup)."""
    h = _hash(texto)
    estado = {}
    if os.path.exists(ESTADO_PATH):
        try:
            with open(ESTADO_PATH, encoding="utf-8") as f:
                estado = json.load(f)
        except Exception:
            estado = {}
    if not force and estado.get(clave) == h:
        return False, "sin cambios (%s)" % clave
    enviar_telegram(texto)
    estado[clave] = h
    os.makedirs(os.path.dirname(ESTADO_PATH), exist_ok=True)
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)
    return True, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="mensaje de prueba")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--texto", type=str, default=None)
    args = ap.parse_args()
    if args.test:
        txt = (
            "*Scanner intermarket — test* ✅\n"
            "Bot `@fpxbs777_bot` conectado correctamente.\n"
            "`%s` · chat `8179198652`" % __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M ART")
        )
        ok, info = enviar_si_cambia("test", txt, force=True)
        print("test enviado:", ok, info)
        return
    if args.texto:
        enviar_telegram(args.texto)
        print("enviado")
        return
    print("usar --test o --texto '...'")
