import yfinance as yf
import json
import os
import time
from datetime import datetime

CACHE_FILE = "sectores_industrias_cache.json"
RATE_LIMIT = 1.0

TICKERS_CEDEAR = [
    "AAP", "AAL", "AEM", "AEG", "ABNB", "ABBV", "ABT",
    "ABEV", "ABEV3", "ACN", "ACWI",
    "ADBE", "ADGO", "ADI", "ADP", "ADS", "AI", "AIG",
    "AKO.B", "ALAB", "AMAT", "AMD",
    "AMGN", "AMX", "AMZN", "ANET", "ANF", "ARCO", "ARKK",
    "ARM", "ASR", "ASTS",
    "ASML", "AVGO", "AVY", "AXIA", "AXP", "AZN",
    "B", "BA", "BA.C", "BABA", "BAK", "BAS",
    "BAYN", "BB", "BBAS3", "BBD", "BBDC3", "BBV", "BCS",
    "BHP", "BIIB", "BIDU",
    "BIOX", "BK", "BKNG", "BKR", "BMY",
    "BP", "BRKB",
    "BSBR", "BX",
    "C", "CAAP", "CAH", "CAR", "CAT", "CCJ", "CCL",
    "CDE", "CEG",
    "CIBR", "CL", "CLS", "COIN", "COP", "COPX", "COST",
    "CRM", "CRWD", "CRWV", "CSCO", "CSNA3", "CVS", "CVX",
    "CX",
    "DAL", "DD", "DE", "DECK", "DEO", "DHR", "DIA",
    "DISN", "DJNJ3",
    "DOCU", "DOW",
    "E", "EA", "EBAY", "ECL", "EEM", "EFA", "EFX",
    "ELP", "ELPC",
    "EMBJ", "EOAN", "EQNR", "ERIC", "ESGU",
    "ETHA", "ETSY", "EWJ", "EWY", "EWZ",
    "F", "FCX", "FDX", "FISV", "FMX", "FSLR", "FXI",
    "GE", "GFI", "GGB",
    "GILD", "GLD", "GLOB", "GLNG", "GLW", "GM", "GOOGL",
    "GPRK", "GRMN", "GS",
    "GSK", "GT", "GDX",
    "HAL", "HAPV3", "HD", "HDB", "HIMS", "HL", "HMC",
    "HMY", "HOG",
    "HON", "HOOD", "HPQ", "HSBC", "HSY", "HUT", "HWM",
    "IBB", "IBM", "IBN",
    "ICLN", "IEMG", "IEUR", "IFF", "IJH", "ILF",
    "INF", "INFY", "ING", "INTC",
    "IP", "IREN", "ISRG", "ITA", "ITUB", "ITUB3",
    "IVE", "IVV", "IVW", "IWDA", "IWM",
    "JCI", "JD", "JMIA", "JNJ", "JOYY", "JPM",
    "KB", "KEEL", "KEP", "KGC",
    "KMB", "KO", "KOFM",
    "LAC", "LAR", "LMT", "LND", "LREN3", "LRCX", "LVS", "LYG",
    "MA", "MBG", "MCD", "MDLZ", "MDT", "MELI", "META",
    "MFG", "MGLU3", "MMC", "MMM", "MO",
    "MOS", "MP", "MRNA", "MRK", "MRSH", "MRVL", "MSI", "MSFT",
    "MSTR", "MU", "MUFG",
    "MUX",
    "NATU3", "NBIS", "NEE", "NEM", "NFLX", "NG", "NGG",
    "NIO", "NKE", "NMR",
    "NOKA", "NOW", "NVS", "NVO", "NUE", "NU", "NVDA", "NXE",
    "O", "OKLO", "ONDS",
    "ORCL", "ORLY", "OXY",
    "PAAS", "PAC", "PAGS", "PANW", "PATH", "PBI", "PBR",
    "PCAR", "PDD", "PEP", "PETR3", "PFE", "PHG", "PINS",
    "PKS", "PLTR", "PM", "PRIO3", "PSQ", "PSX",
    "PYPL",
    "QCOM", "QQQ",
    "RACE", "RBLX", "RENT3", "RGTI", "RIO", "RIOT", "RKLB",
    "ROKU", "ROST", "RSP", "RTX",
    "SAN", "SAP", "SATL", "SBS", "SBSP3", "SCCO", "SCHW",
    "SE", "SHEL", "SH", "SHOP", "SID", "SIEGY", "SLB",
    "SLV", "SMH", "SMSN",
    "SNA", "SNAP", "SNDK", "SNOW", "SONY", "SPCE",
    "SPCX", "SPGI", "SPHQ", "SPOT", "SPXL", "SPY",
    "STLA", "STNE", "SUZ", "SUZB3",
    "SBUX", "SWKS", "SYY",
    "T", "TEAM", "TEFO", "TEM", "TEN",
    "TGT", "TIMB", "TIMS3", "TJX", "TM", "TMO", "TMUS",
    "TQQQ", "TRIP", "TRVV", "TSM", "TTE",
    "TV", "TWLO", "TXN", "TXR",
    "UAL", "UBER", "UGP", "UL", "UNH", "UNP", "UPST",
    "URA", "URBN", "USB", "USO",
    "V", "VALE", "VALE3", "VEA", "VIG", "VIST", "VIV",
    "VIVT3", "VOD", "VRSN", "VRTX", "VST", "VXX", "VZ",
    "WBO", "WEGE3", "WFC", "WMT",
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP",
    "XLRE", "XLU", "XLV", "XLY",
    "XME", "XOM", "XP", "XPEV", "XROX", "XYZ",
    "YELP", "YZCA",
    "ZM"
]

BRAZILIAN_SUFFIXES = {"3", "4", "5", "6", "7", "8", "9", "11"}
ETF_TICKERS = {"ACWI", "ARKK", "CIBR", "COPX", "DIA", "EEM", "EFA", "ESGU",
               "ETHA", "EWJ", "EWY", "EWZ", "FXI", "GDX", "GLD", "IBB",
               "ICLN", "IEMG", "IEUR", "IJH", "ILF", "ITA", "IVE", "IVV",
               "IVW", "IWM", "PSQ", "QQQ", "RSP", "SLV", "SMH", "SPHQ",
               "SPY", "TQQQ", "URA", "USO", "VEA", "VIG", "VXX", "XLB",
               "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU",
               "XLV", "XLY", "XME", "SPCX"}


SIMBOLO_MAP = {
    "BRKB": "BRK-B",
    "AKO.B": "AKO-B",
    "BA.C": "BA",
    "IWDA": "IWDA.AS",
    "NOKA": "NOK",
    "DISN": "DIS",
    "KOFM": "KOF",
    "MRSH": "MMC",
    "TEFO": "TEF",
    "XROX": "XRX",
    "ADGO": "ADGO",
    "BMNR": "BMNR",
    "BNG": "BNG",
    "BNY": "BNY",
    "CRWV": "CRWV",
    "ELPC": "ELP",
    "EMBJ": "EMB",
    "INF": "INF",
    "KEEL": "KEEL",
    "PKS": "PKS",
    "TXR": "TXR",
    "WBO": "WBO",
    "YZCA": "YZCA",
    "TRVV": "TRVV",
    "SNDK": "SNDK",
    "SPCX": "SPCX",
}


def _limpiar_simbolo(s):
    s = s.strip()
    if s in SIMBOLO_MAP:
        return SIMBOLO_MAP[s]

    if s.endswith("11") or s[-1:] in BRAZILIAN_SUFFIXES:
        return f"{s}.SA"
    return s


def cargar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def obtener_info_ticker(simbolo_original, cache):
    simbolo_clean = _limpiar_simbolo(simbolo_original)

    if simbolo_clean in cache:
        entry = cache[simbolo_clean]
        if entry.get("sector") != "No disponible":
            return entry

    try:
        ticker = yf.Ticker(simbolo_clean)
        info = ticker.info
        if not info:
            info = {}
    except Exception:
        info = {}

    resultado = {
        "simbolo_original": simbolo_original,
        "simbolo_yfinance": simbolo_clean,
        "nombre": info.get("longName") or info.get("shortName") or "No disponible",
        "sector": info.get("sector", "No disponible"),
        "industria": info.get("industry", "No disponible"),
        "pais": info.get("country", "No disponible"),
        "timestamp": datetime.now().isoformat(),
        "error": None
    }

    if resultado["sector"] == "No disponible" and resultado["nombre"] == "No disponible":
        mkt_cap = info.get("marketCap")
        if mkt_cap is not None:
            resultado["error"] = "info_limitada"
        else:
            resultado["error"] = "no_encontrado"

    cache[simbolo_clean] = resultado
    return resultado


def procesar_lista(tickers, resume=True):
    cache = cargar_cache()
    pendientes = [t for t in tickers if _limpiar_simbolo(t) not in cache or
                  cache[_limpiar_simbolo(t)].get("sector") == "No disponible"] if resume else tickers

    print(f"Total tickers: {len(tickers)}")
    print(f"Pendientes de scrapear: {len(pendientes)}")
    if pendientes:
        print()

    for i, ticker in enumerate(pendientes):
        resultado = obtener_info_ticker(ticker, cache)
        estado = "OK" if resultado["error"] is None else resultado["error"]
        print(f"[{i+1}/{len(pendientes)}] {ticker:>8s} -> {resultado['sector']:35s} | {resultado['industria']:45s} [{estado}]")
        guardar_cache(cache)
        time.sleep(RATE_LIMIT)

    print(f"\nProcesados {len(pendientes)} tickers nuevos.")
    print(f"Total en cache: {len(cache)}")
    print(f"Guardado en: {CACHE_FILE}")


if __name__ == "__main__":
    procesar_lista(TICKERS_CEDEAR)