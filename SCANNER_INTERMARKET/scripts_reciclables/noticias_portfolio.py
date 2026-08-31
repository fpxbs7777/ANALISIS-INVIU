# -*- coding: utf-8 -*-
"""Noticias del portafolio: Google News RSS + Yahoo Finance local (Flask) +
Finnhub (+ Marketaux / NewsAPI.org si hay keys en .env).

Uso:
    python noticias_portfolio.py             # ultimas 24 horas
    python noticias_portfolio.py --days 3    # ultimos 3 dias
"""
import argparse
import csv
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = os.path.dirname(os.path.abspath(__file__))
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-news-checker)"}
MAX_WORKERS = 6

TICKERS = [
    ("PAMP", "PAM", "Pampa Energia", '"Pampa Energia" OR "Pampa Energ\u00eda"'),
    ("AMZN", "AMZN", "Amazon", "Amazon"),
    ("GOOGL", "GOOGL", "Google", "Google"),
    ("IBM", "IBM", "IBM", "IBM"),
    ("MU", "MU", "Micron", '"Micron Technology"'),
    ("NU", "NU", "Nubank", '"Nu Holdings" OR Nubank'),
    ("NVDA", "NVDA", "Nvidia", "Nvidia"),
    ("SMH", "SMH", "VanEck Semiconductor", '"VanEck Semiconductor" OR "semiconductor ETF"'),
    ("SPY", "SPY", "S&P 500", '"S&P 500"'),
    ("TSM", "TSM", "Taiwan Semiconductor", '"Taiwan Semiconductor" OR TSMC'),
    ("URA", "URA", "Uranium ETF", '"Global X Uranium" OR "uranium ETF" OR uranio'),
    ("XLE", "XLE", "Energy ETF", '"Energy Select Sector" OR "energy sector ETF" OR XLE'),
]

SOURCE_ORDER = ("GNews-RSS", "Finnhub", "Yahoo-Flask", "Marketaux", "NewsAPI")

POSITIVAS = {
    "beat", "beats", "profit", "profits", "growth", "strong", "surge", "rally", "gain",
    "gains", "outperform", "upgrade", "upgraded", "buy", "bullish", "optimistic",
    "record", "soar", "jump", "rise", "rises", "positive", "expansion", "breakthrough",
    "momentum", "recovery", "supera", "superan", "ganancia", "ganancias", "crecimiento",
    "fuerte", "alza", "sube", "suben", "compra", "alcista", "optimista", "recuperacion",
    "impulso", "expansion", "positivo", "positiva", "aumento", "beneficio", "dividendo",
    "dividendos", "acuerdo", "contrato", "adquisicion", "fusion", "aprobacion",
    "lanzamiento", "innovacion", "liderazgo", "rentable", "eficiencia", "mejora",
    "mejoran",
}

NEGATIVAS = {
    "miss", "misses", "loss", "losses", "weak", "decline", "drop", "drops", "fall",
    "falls", "plunge", "crash", "bearish", "sell", "downgrade", "downgraded", "cut",
    "cuts", "layoff", "layoffs", "recession", "debt", "default", "bankruptcy",
    "investigation", "lawsuit", "penalty", "warning", "risk", "risks", "volatile",
    "inflation", "stagflation", "fracasa", "falla", "perdida", "perdidas", "debil",
    "caida", "cae", "caen", "baja", "bajan", "bajista", "vender", "deuda", "quiebra",
    "recesion", "despido", "despidos", "recorte", "sancion", "multa", "demanda",
    "investigacion", "riesgo", "riesgos", "incertidumbre", "inflacion", "estanflacion",
    "preocupacion", "alerta", "problema", "problemas", "retraso",
}


class NoKey(Exception):
    pass


class SourceDown(Exception):
    pass


_lock = threading.Lock()
SRC_STATS = {}


def load_env():
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


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url, timeout=15):
    return json.loads(_get(url, timeout).decode("utf-8", "replace"))


def parse_dt(v):
    if v in (None, "", 0):
        return None
    if isinstance(v, (int, float)):
        try:
            ts = float(v)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    s = str(v).strip()
    if re.fullmatch(r"\d{9,13}", s):
        return parse_dt(int(s))
    for fn in (
        lambda x: parsedate_to_datetime(x),
        lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")),
    ):
        try:
            dt = fn(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def norm_title(t):
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return t[:90]


def domain(url):
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def lex_score(text):
    if not text:
        return 0
    tokens = set(re.findall(r"[a-záéíóúñ]+", text.lower()))
    pos = len(tokens & POSITIVAS)
    neg = len(tokens & NEGATIVAS)
    return 1 if pos > neg else (-1 if neg > pos else 0)


def _pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


def fetch_gnews(rss_q, days, cutoff):
    q = urllib.parse.quote_plus("%s when:%dd" % (rss_q, max(1, days)))
    url = "https://news.google.com/rss/search?q=%s&hl=es-419&gl=AR&ceid=AR:es-419" % q
    try:
        root = ET.fromstring(_get(url, timeout=30))
    except Exception as e:
        raise SourceDown(str(e)[:60])
    items = []
    for it in root.iter("item"):
        pub = parse_dt(it.findtext("pubDate"))
        if pub and pub < cutoff:
            continue
        src = it.find("source")
        items.append({
            "titulo": (it.findtext("title") or "").strip(),
            "url": (it.findtext("link") or "").strip(),
            "fuente": (src.text or "").strip() if src is not None else "",
            "fecha": pub,
            "origen": "GNews-RSS",
            "sent": None,
        })
    return items


def fetch_finnhub(sym_us, days):
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key:
        raise NoKey("FINNHUB_API_KEY vacia")
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    to = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    url = ("https://finnhub.io/api/v1/company-news?symbol=%s&from=%s&to=%s&token=%s"
           % (sym_us, frm, to, urllib.parse.quote(key)))
    data = get_json(url, timeout=15)
    time.sleep(0.2)
    items = []
    for n in data or []:
        items.append({
            "titulo": n.get("headline") or "",
            "url": n.get("url") or "",
            "fuente": n.get("source") or "",
            "fecha": parse_dt(n.get("datetime")),
            "origen": "Finnhub",
            "sent": None,
        })
    return items


def fetch_yf_local(sym_us, cutoff):
    base = os.environ.get("NEWS_API_URL", "http://localhost:5000/api/news").strip()
    sep = "&" if "?" in base else "?"
    url = "%s%sticker=%s" % (base, sep, urllib.parse.quote(sym_us))
    try:
        data = get_json(url, timeout=4)
    except (urllib.error.URLError, OSError) as e:
        raise SourceDown("sin respuesta en %s (%s)" % (base, getattr(e, "reason", e)))
    except Exception as e:
        raise SourceDown(str(e)[:60])
    if isinstance(data, dict):
        for k in ("news", "articles", "data", "items", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        raise SourceDown("formato JSON no reconocido")
    items = []
    for n in data:
        if not isinstance(n, dict):
            continue
        prov = n.get("provider") or n.get("source") or n.get("publisher") or ""
        if isinstance(prov, dict):
            prov = prov.get("displayName") or prov.get("name") or ""
        fecha = parse_dt(_pick(n, "published", "pubDate", "datetime", "published_at",
                               "datetime_utc", "date"))
        if fecha and fecha < cutoff:
            continue
        items.append({
            "titulo": str(_pick(n, "title", "headline", "titulo")),
            "url": str(_pick(n, "link", "url")),
            "fuente": str(prov),
            "fecha": fecha,
            "origen": "Yahoo-Flask",
            "sent": None,
        })
    return items


def fetch_marketaux(sym_us, days):
    key = os.environ.get("MARKETAUX_API_KEY", "").strip()
    if not key:
        raise NoKey("MARKETAUX_API_KEY vacia")
    iso_from = (datetime.now(timezone.utc) - timedelta(days=min(days, 5))).strftime("%Y-%m-%d")
    url = ("https://api.marketaux.com/v1/news/all?symbols=%s&filter_entities=true"
           "&language=en,es&published_after=%s&api_token=%s"
           % (sym_us, iso_from, urllib.parse.quote(key)))
    data = get_json(url, timeout=15)
    items = []
    for n in (data or {}).get("data") or []:
        sent = None
        for ent in n.get("entities") or []:
            if ent.get("symbol") == sym_us and ent.get("sentiment_score") is not None:
                sent = float(ent["sentiment_score"])
                break
        src = n.get("source")
        fuente = src.get("name") if isinstance(src, dict) else src
        items.append({
            "titulo": n.get("title") or "",
            "url": n.get("url") or "",
            "fuente": fuente or "",
            "fecha": parse_dt(n.get("published_at")),
            "origen": "Marketaux",
            "sent": sent,
        })
    return items


def fetch_newsapi(empresa, days):
    key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not key:
        raise NoKey("NEWSAPI_KEY vacia")
    iso_from = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = urllib.parse.quote('"%s"' % empresa)
    url = ("https://newsapi.org/v2/everything?q=%s&from=%s&sortBy=publishedAt&pageSize=20"
           "&apiKey=%s" % (q, iso_from, urllib.parse.quote(key)))
    data = get_json(url, timeout=15)
    if str(data.get("status")) != "ok":
        raise SourceDown(str(data.get("message"))[:60])
    items = []
    for a in data.get("articles") or []:
        src = a.get("source")
        items.append({
            "titulo": a.get("title") or "",
            "url": a.get("url") or "",
            "fuente": (src.get("name") if isinstance(src, dict) else "") or "",
            "fecha": parse_dt(a.get("publishedAt")),
            "origen": "NewsAPI",
            "sent": None,
        })
    return items


def dedup(items):
    seen = {}
    out = []
    for it in items:
        key = (norm_title(it["titulo"]), domain(it["url"]))
        if key in seen:
            prev = seen[key]
            if it["origen"] not in prev["origen"]:
                prev["origen"] += "+" + it["origen"]
            continue
        seen[key] = it
        out.append(it)
    return out


def sent_str(it):
    s = it["sent"]
    if isinstance(s, (int, float)):
        return "%+.2f" % s
    return {1: "[+]", -1: "[-]", 0: "[ ]"}[lex_score(it["titulo"])]


def _stat(name, ok=None, n=None, err=None):
    with _lock:
        st = SRC_STATS.setdefault(name, {"ok": 0, "n": 0, "err": ""})
        if ok:
            st["ok"] += 1
        if n:
            st["n"] += n
        if err:
            st["err"] = err
        return st


def safe(name, fn, *args):
    try:
        items = fn(*args)
        _stat(name, ok=True, n=len(items))
        return items
    except NoKey as e:
        _stat(name, err="omitida (%s)" % e)
    except SourceDown as e:
        _stat(name, err="NO DISPONIBLE - %s" % e)
    except Exception as e:
        _stat(name, err="ERROR - %s" % str(e)[:60])
    return []


def process_ticker(args_tuple, days, cutoff):
    cedear, sym_us, empresa, rss_q = args_tuple
    raw = []
    raw += safe("GNews-RSS", fetch_gnews, rss_q, days, cutoff)
    raw += safe("Finnhub", fetch_finnhub, sym_us, days)
    raw += safe("Yahoo-Flask", fetch_yf_local, sym_us, cutoff)
    raw += safe("Marketaux", fetch_marketaux, sym_us, days)
    raw += safe("NewsAPI", fetch_newsapi, empresa, days)

    items = dedup(raw)
    items.sort(key=lambda x: x["fecha"] or datetime(1970, 1, 1, tzinfo=timezone.utc),
               reverse=True)
    rows = [{
        "ticker_cedear": cedear,
        "simbolo_us": sym_us,
        "empresa": empresa,
        "fecha_utc": it["fecha"].strftime("%Y-%m-%d %H:%M:%S") if it["fecha"] else "",
        "origen": it["origen"],
        "fuente": it["fuente"],
        "sentimiento": it["sent"] if it["sent"] is not None else lex_score(it["titulo"]),
        "titulo": it["titulo"],
        "url": it["url"],
    } for it in items]
    return (cedear, sym_us, empresa, items, rows)


def main():
    ap = argparse.ArgumentParser(description="Noticias del portafolio (multi-fuente)")
    ap.add_argument("--days", type=int, default=1, help="ventana de dias (default 1)")
    ap.add_argument("--tickers", type=str, default="",
                    help="lista CEDEARs separada por coma (ej: PAMP,NVDA)")
    ap.add_argument("--limit", type=int, default=12, help="max noticias por ticker")
    args = ap.parse_args()

    load_env()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    want = {x.strip().upper() for x in args.tickers.split(",") if x.strip()}
    sel = [t for t in TICKERS if not want or t[0] in want]

    print("=" * 110)
    print("NOTICIAS DEL PORTAFOLIO | %s | ventana: ultimas %dh | %d tickers"
          % (datetime.now().strftime("%d/%m/%Y %H:%M"), args.days * 24, len(sel)))
    print("=" * 110, flush=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(process_ticker, t, args.days, cutoff) for t in sel]
        results = [f.result() for f in futures]

    all_rows = []
    for cedear, sym_us, empresa, items, rows in results:
        print("\n%s  %s  [%s]" % (cedear, empresa, sym_us))
        if not items:
            print("   (sin noticias en la ventana)")
        for it in items[:args.limit]:
            fh = it["fecha"].astimezone().strftime("%d/%m %H:%M") if it["fecha"] else "--/-- --:--"
            print("   %s | %-14s | %-18s | %s | %s" % (
                fh, (it["fuente"] or "-")[:14], "[%s]" % it["origen"], sent_str(it),
                it["titulo"][:100]))
        all_rows.extend(rows)

    total_sel = len(sel)
    print("\n" + "-" * 110)
    print("ESTADO DE FUENTES:")
    for name in SOURCE_ORDER:
        st = SRC_STATS.get(name)
        if not st:
            print("   %-12s sin uso" % name)
        elif st["ok"]:
            msg = "OK en %d/%d tickers (%d noticias)" % (st["ok"], total_sel, st["n"])
            if st["err"]:
                msg += " | fallos parciales: %s" % st["err"]
            print("   %-12s %s" % (name, msg))
        else:
            print("   %-12s %s" % (name, st["err"]))
    print("-" * 110)

    if all_rows:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_csv = os.path.join(REPO, "noticias_%s.csv" % stamp)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print("TOTAL: %d noticias | CSV: %s" % (len(all_rows), out_csv))
    else:
        print("TOTAL: 0 noticias")


if __name__ == "__main__":
    main()
