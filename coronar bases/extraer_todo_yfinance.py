#!/usr/bin/env python3
"""
Extractor masivo de Yahoo Finance — BCBA + NYSE
  - Lee tickers de sectores.json
  - Guarda FUNDAMENTALES en JSON (1 archivo por sector, agrupado por industria)
  - Guarda HISTÓRICO en CSV (1 archivo por ticker, en historical/)
  - Checkpoint cada chunk para reanudar
"""

import json, os, time, shutil, gc, warnings, csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import yfinance as yf
import pandas as pd

# ─── Config ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
SECTORES_PATH = BASE_DIR / "src" / "lib" / "sectores.json"
OUTPUT_DIR = BASE_DIR / "coronar bases" / "datos_yfinance"
HISTORICAL_DIR = OUTPUT_DIR / "historical"
PROGRESS_PATH = OUTPUT_DIR / "_progress.json"

WORKERS = 4
CHUNK_SIZE = 50
PAUSE_SECS = 5
MAX_RETRIES = 2
TIMEOUT = 90

# ─── Serialización ───────────────────────────────────────────────────────

def _serialize(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {str(k) if not isinstance(k, (str, int, float, bool, type(None))) else k: _serialize(v)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "item"):
        return obj.item()
    return obj

def _df_to_dict(df):
    if df is None or df.empty:
        return None
    try:
        return _serialize(df.reset_index().to_dict(orient="records"))
    except Exception:
        return None

def _df_to_records(df):
    if df is None or df.empty:
        return None
    try:
        return _serialize(df.reset_index().to_dict(orient="records"))
    except Exception:
        return None

# ─── Carga de tickers ────────────────────────────────────────────────────

def cargar_tickers():
    with open(SECTORES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for sector, industrias in data.items():
        for industria, tickers in industrias.items():
            for t in tickers:
                ticker = t.get("ticker", "").strip()
                nombre = t.get("nombre", "")
                if ticker:
                    items.append({
                        "sector": sector,
                        "industria": industria,
                        "ticker": ticker,
                        "nombre": nombre,
                    })
    return items

# ─── Extracción de un ticker (SOLO fundamentales, histórico va a CSV) ────

def extraer_ticker(ticker_str, intento=1):
    """Extrae fundamentales + histórico. Retorna (fundamentals_dict, historical_df_or_None)."""
    fund = {
        "error": None, "info": {}, "financials": None,
        "analysis": None, "holdings": None, "calendar_data": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    hist_df = None
    try:
        t = yf.Ticker(ticker_str)
        # Info
        try:
            info = t.info if t.info else {}
            fund["info"] = _serialize(info)
        except Exception:
            fund["info"] = {}
        # Historical
        try:
            hist_df = t.history(period="max")
        except Exception:
            hist_df = None
        # Financials
        try:
            fund["financials"] = {
                "income_stmt": _df_to_dict(t.income_stmt),
                "quarterly_income_stmt": _df_to_dict(t.quarterly_income_stmt),
                "balance_sheet": _df_to_dict(t.balance_sheet),
                "quarterly_balance_sheet": _df_to_dict(t.quarterly_balance_sheet),
                "cashflow": _df_to_dict(t.cashflow),
                "quarterly_cashflow": _df_to_dict(t.quarterly_cashflow),
                "earnings": _df_to_dict(t.earnings),
                "quarterly_earnings": _df_to_dict(t.quarterly_earnings),
            }
        except Exception:
            fund["financials"] = None
        # Analysis
        try:
            fund["analysis"] = {
                "recommendations": _df_to_records(t.recommendations),
                "recommendations_summary": _df_to_records(t.recommendations_summary),
                "upgrades_downgrades": _df_to_records(t.upgrades_downgrades),
                "earnings_dates": _df_to_records(t.earnings_dates),
                "earnings_history": _df_to_dict(t.earnings_history),
                "earnings_estimate": _df_to_dict(t.earnings_estimate),
                "revenue_estimate": _df_to_dict(t.revenue_estimate),
                "eps_trend": _df_to_dict(t.eps_trend),
                "eps_revisions": _df_to_dict(t.eps_revisions),
                "growth_estimates": _df_to_dict(t.growth_estimates),
                "analyst_price_targets": _serialize(t.analyst_price_targets),
                "sustainability": _df_to_dict(t.sustainability),
            }
        except Exception:
            fund["analysis"] = None
        # Holdings
        try:
            fund["holdings"] = {
                "major_holders": _df_to_records(t.major_holders),
                "institutional_holders": _df_to_records(t.institutional_holders),
                "mutualfund_holders": _df_to_records(t.mutualfund_holders),
                "insider_transactions": _df_to_records(t.insider_transactions),
                "insider_purchases": _df_to_records(t.insider_purchases),
                "insider_roster_holders": _df_to_records(t.insider_roster_holders),
            }
        except Exception:
            fund["holdings"] = None
        # Calendar
        try:
            fund["calendar_data"] = {
                "calendar": _serialize(t.calendar),
                "dividends": _serialize(t.dividends.to_dict()) if hasattr(t.dividends, 'to_dict') else None,
                "splits": _serialize(t.splits.to_dict()) if hasattr(t.splits, 'to_dict') else None,
                "actions": _serialize(t.actions.to_dict()) if hasattr(t.actions, 'to_dict') else None,
                "sec_filings": _serialize(t.sec_filings),
            }
        except Exception:
            fund["calendar_data"] = None
    except Exception as e:
        if intento <= MAX_RETRIES:
            time.sleep(2)
            return extraer_ticker(ticker_str, intento + 1)
        fund["error"] = f"{type(e).__name__}: {e}"
    return fund, hist_df

# ─── I/O ──────────────────────────────────────────────────────────────────

def _sanitize(name):
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip().replace(" ", "_")

def sector_path(sector):
    return OUTPUT_DIR / f"{_sanitize(sector)}.json"

def hist_path(ticker):
    return HISTORICAL_DIR / f"{_sanitize(ticker)}.csv"

def cargar_sector(sector):
    fp = sector_path(sector)
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_sector(sector, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fp = sector_path(sector)
    tmp = fp.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    shutil.move(str(tmp), str(fp))

def guardar_historico(ticker, df):
    """Guarda DataFrame histórico como CSV. Retorna dict con stats."""
    stats = {"rows": 0, "columns": 0, "file": None}
    if df is None or df.empty:
        return stats
    try:
        HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
        fp = hist_path(ticker)
        df.to_csv(fp)
        stats = {"rows": len(df), "columns": len(df.columns), "file": str(fp.relative_to(OUTPUT_DIR))}
    except Exception:
        pass
    return stats

def cargar_progreso():
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"ultimo_indice": 0, "procesados": 0}

def guardar_progreso(indice, procesados):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PROGRESS_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ultimo_indice": indice, "procesados": procesados,
                    "timestamp": datetime.now(timezone.utc).isoformat()}, f)
    shutil.move(str(tmp), str(PROGRESS_PATH))

# ─── Procesamiento ───────────────────────────────────────────────────────

def procesar():
    print("=" * 70)
    print("  EXTRACTOR YFINANCE — BCBA + NYSE")
    print(f"  Output: {OUTPUT_DIR}/")
    print("=" * 70)

    items = cargar_tickers()
    print(f"\n📂 {len(items)} tickers en {len(set(i['sector'] for i in items))} sectores")

    progreso = cargar_progreso()
    inicio = progreso.get("ultimo_indice", 0)
    procesados_previos = progreso.get("procesados", 0)
    if inicio > 0:
        print(f"   🔄 Reanudando desde índice {inicio} ({procesados_previos} procesados)")

    restantes = items[inicio:]
    total = len(restantes)
    procesados = procesados_previos
    errores = 0
    t0 = time.time()

    print(f"\n🚀 {total} restantes ({WORKERS} workers, chunks de {CHUNK_SIZE})\n")

    for cs in range(0, total, CHUNK_SIZE):
        ce = min(cs + CHUNK_SIZE, total)
        chunk = restantes[cs:ce]

        # Procesar chunk
        results = []
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            fut_map = {ex.submit(extraer_ticker, item["ticker"]): item for item in chunk}
            for fut in as_completed(fut_map):
                item = fut_map[fut]
                try:
                    fund, hist = fut.result(timeout=TIMEOUT)
                except Exception as e:
                    fund = {"error": f"Timeout: {e}", "info": {}, "financials": None,
                            "analysis": None, "holdings": None, "calendar_data": None,
                            "timestamp": datetime.now(timezone.utc).isoformat()}
                    hist = None
                if fund.get("error"):
                    errores += 1
                results.append((item, fund, hist))

        # Guardar: fundamentales por sector, histórico por ticker
        sector_buf = {}
        for item, fund, hist in results:
            sec = item["sector"]
            ind = item["industria"]
            if sec not in sector_buf:
                sector_buf[sec] = cargar_sector(sec)
            if ind not in sector_buf[sec]:
                sector_buf[sec][ind] = []

            # Guardar histórico como CSV
            hist_stats = guardar_historico(item["ticker"], hist)

            # En fundamentals, incluir referencia al archivo histórico
            fund["historical_file"] = hist_stats.get("file")
            fund["historical_rows"] = hist_stats.get("rows", 0)

            sector_buf[sec][ind].append({
                "ticker": item["ticker"],
                "nombre": item["nombre"],
                "datos": fund,
            })
            procesados += 1

        for sec, data in sector_buf.items():
            guardar_sector(sec, data)

        # Stats
        pct = (procesados - procesados_previos) / total * 100
        elapsed = time.time() - t0
        rate = (procesados - procesados_previos) / elapsed if elapsed > 0 else 0
        eta = (total - (procesados - procesados_previos)) / rate if rate > 0 else 0
        sizes = " ".join(f"{_sanitize(s)[:12]}:{sector_path(s).stat().st_size/1024/1024:.0f}MB"
                         for s in sector_buf if sector_path(s).exists())
        print(f"  📊 Chunk {cs//CHUNK_SIZE+1}/{(total-1)//CHUNK_SIZE+1}: "
              f"{len(chunk)} ticks | {procesados}/{procesados_previos+total} "
              f"({pct:.1f}%) {rate:.2f}t/s ETA:{eta:.0f}s | {sizes}")

        guardar_progreso(inicio + ce, procesados)
        if ce < total:
            time.sleep(PAUSE_SECS)
        del sector_buf, results
        gc.collect()

    # ─── Final ───────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  ✅ COMPLETADO: {procesados} tickers | ❌ {errores} errores")
    elapsed = time.time() - t0

    total_size = 0
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        mb = f.stat().st_size / (1024 * 1024)
        total_size += mb
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            print(f"  📁 {f.stem}: {len(data)} industrias, {sum(len(t) for t in data.values())} tickers, {mb:.1f} MB")
        except Exception:
            print(f"  📁 {f.stem}: {mb:.1f} MB")

    # Contar históricos
    if HISTORICAL_DIR.exists():
        n_csv = len(list(HISTORICAL_DIR.glob("*.csv")))
        csv_size = sum(f.stat().st_size for f in HISTORICAL_DIR.glob("*.csv")) / (1024 * 1024)
        print(f"  📁 historical/: {n_csv} archivos CSV, {csv_size:.0f} MB")

    print(f"\n📊 TOTAL JSON: {total_size:.0f} MB")
    print(f"   Tiempo: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    guardar_progreso(0, 0)

if __name__ == "__main__":
    procesar()