# -*- coding: utf-8 -*-
"""Noticias para el scanner: Google News RSS + lexico ES/EN (+ Finnhub opcional).

Reciclado de noticias_portfolio.py (raiz del repo).
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
HEADERS = {"User-Agent": "Mozilla/5.0 (intermarket-scanner)"}

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
    "vender", "deuda", "quiebra", "recesion", "despido", "recorte", "sancion",
    "multa", "demanda", "investigacion", "riesgo", "incertidumbre", "inflacion",
    "estanflacion", "preocupacion", "alerta", "problema", "problemas", "retraso",
}


def load_env():
    for path in (os.path.join(REPO, ".env"), os.path.join(BASE, ".env")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k.strip() and v.strip():
                        os.environ.setdefault(k.strip(), v.strip())
            break


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def score(text):
    if not text:
        return 0
    tokens = set(re.findall(r"[a-záéíóúñ]+", text.lower()))
    pos = len(tokens & POSITIVAS)
    neg = len(tokens & NEGATIVAS)
    return 1 if pos > neg else (-1 if neg > pos else 0)


def gnews(query, days=2):
    q = urllib.parse.quote_plus("%s when:%dd" % (query, max(1, days)))
    url = ("https://news.google.com/rss/search?q=%s&hl=es-419&gl=AR&ceid=AR:es-419" % q)
    try:
        root = ET.fromstring(_get(url))
    except Exception:
        return []
    out = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days) + 0.2)
    for it in root.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        pub = it.findtext("pubDate")
        try:
            dt = parsedate(pub)
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        out.append({"titulo": titulo, "fecha": dt.isoformat() if dt else "",
                    "sent": score(titulo)})
        if len(out) >= 25:
            break
    return out


def parsedate(s):
    from email.utils import parsedate_to_datetime
    dt = parsedate_to_datetime(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def sentimiento_global(queries, days=2, workers=4):
    def work(item):
        items = gnews(item["q"], days)
        neto = sum(i["sent"] for i in items)
        return {"cluster": item["cluster"], "q": item["q"], "n": len(items),
                "neto": neto,
                "titulares": [{"t": i["titulo"][:110], "s": i["sent"]}
                              for i in items if i["sent"] != 0][:4]}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(work, queries))
    return res


def finnhub_market_news(max_items=6):
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key:
        return []
    try:
        url = ("https://finnhub.io/api/v1/news?category=general&token="
               + urllib.parse.quote(key))
        data = json.loads(_get(url, timeout=10).decode("utf-8", "replace"))
        time.sleep(0.3)
        return [{"t": n.get("headline", "")[:110],
                 "s": score(n.get("headline", "")),
                 "src": n.get("source", "")}
                for n in (data or [])[:max_items]]
    except Exception:
        return []


if __name__ == "__main__":
    load_env()
    demo = sentimiento_global([{"q": "\"S&P 500\"", "cluster": "equity"}], 1)
    print(json.dumps(demo, ensure_ascii=False, indent=2))
