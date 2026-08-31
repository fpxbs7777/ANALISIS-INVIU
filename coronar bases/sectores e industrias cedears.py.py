import json
import time
import yfinance as yf
from deep_translator import GoogleTranslator

# Lista COMPLETA de tickers de CEDEARs en pesos (sin sufijos)
TICKERS = [
    "AAP", "AAL", "AEM", "AEG", "ABNB", "ABBV", "ABT", "ABEV", "ABEV3", "ACN",
    "ACWI", "ADBE", "ADGO", "ADI", "ADP", "ADS", "AI", "AIG", "AKO.B", "ALAB",
    "AMAT", "AMD", "AMGN", "AMX", "AMZN", "ANET", "ANF", "ARCO", "ARKK", "ARM",
    "ASR", "ASTS", "ASML", "AVGO", "AVY", "AXIA", "AXP", "AZN", "B", "BA",
    "BA.C", "BABA", "BAK", "BAS", "BAYN", "BB", "BBAS3", "BBD", "BBDC3", "BBV",
    "BCS", "BHP", "BIIB", "BIDU", "BIOX", "BK", "BKNG", "BKR", "BMY", "BMNR",
    "BNG", "BNY", "BP", "BPA11", "BRKB", "BSBR", "BX", "C", "CAAP", "CAH",
    "CAR", "CAT", "CCJ", "CCL", "CDE", "CEG", "CIBR", "CL", "CLS", "COIN",
    "COP", "COPX", "COST", "CRM", "CRWD", "CRWV", "CSCO", "CSNA3", "CVS", "CVX",
    "CX", "DAL", "DD", "DE", "DECK", "DEO", "DHR", "DIA", "DISN", "DJNJ3",
    "DOCU", "DOW", "E", "EA", "EBAY", "ECL", "EEM", "EFA", "EFX", "ELP",
    "ELPC", "EMBJ", "EOAN", "EQNR", "ERIC", "ESGU", "ETHA", "ETSY", "EWJ", "EWY",
    "EWZ", "F", "FCX", "FDX", "FISV", "FMX", "FSLR", "FXI", "GE", "GFI",
    "GGB", "GILD", "GLD", "GLOB", "GLNG", "GLW", "GM", "GOOGL", "GPRK", "GRMN",
    "GS", "GSK", "GT", "GDX", "HAL", "HAPV3", "HD", "HDB", "HIMS", "HL",
    "HMC", "HMY", "HOG", "HON", "HOOD", "HPQ", "HSBC", "HSY", "HUT", "HWM",
    "IBB", "IBM", "IBN", "ICLN", "IEMG", "IEUR", "IFF", "IJH", "ILF", "INF",
    "INFY", "ING", "INTC", "IP", "IREN", "ISRG", "ITA", "ITUB", "ITUB3", "IVE",
    "IVV", "IVW", "IWDA", "IWM", "JCI", "JD", "JMIA", "JNJ", "JOYY", "JPM",
    "KB", "KEEL", "KEP", "KGC", "KMB", "KO", "KOFM", "LAC", "LAR", "LMT",
    "LND", "LREN3", "LRCX", "LVS", "LYG", "MA", "MBG", "MCD", "MDLZ", "MDT",
    "MELI", "META", "MFG", "MGLU3", "MMC", "MMM", "MO", "MOS", "MP", "MRNA",
    "MRK", "MRSH", "MRVL", "MSI", "MSFT", "MSTR", "MU", "MUFG", "MUX", "NATU3",
    "NBIS", "NEE", "NEM", "NFLX", "NG", "NGG", "NIO", "NKE", "NMR", "NOKA",
    "NOW", "NVS", "NVO", "NUE", "NU", "NVDA", "NXE", "O", "OKLO", "ONDS",
    "ORCL", "ORLY", "OXY", "PAAS", "PAC", "PAGS", "PANW", "PATH", "PBI", "PBR",
    "PCAR", "PDD", "PEP", "PETR3", "PFE", "PHG", "PINS", "PKS", "PLTR", "PM",
    "PRIO3", "PSQ", "PSX", "PYPL", "QCOM", "QQQ", "RACE", "RBLX", "RENT3", "RGTI",
    "RIO", "RIOT", "RKLB", "ROKU", "ROST", "RSP", "RTX", "SAN", "SAP", "SATL",
    "SBS", "SBSP3", "SCCO", "SCHW", "SE", "SHEL", "SH", "SHOP", "SID", "SIEGY",
    "SLB", "SLV", "SMH", "SMSN", "SNA", "SNAP", "SNDK", "SNOW", "SONY", "SPCE",
    "SPCX", "SPGI", "SPHQ", "SPOT", "SPXL", "SPY", "STLA", "STNE", "SUZ", "SUZB3",
    "SBUX", "SWKS", "SYY", "T", "TEAM", "TEFO", "TEM", "TEN", "TGT", "TIMB",
    "TIMS3", "TJX", "TM", "TMO", "TMUS", "TQQQ", "TRIP", "TRVV", "TSM", "TTE",
    "TV", "TWLO", "TXN", "TXR", "UAL", "UBER", "UGP", "UL", "UNH", "UNP",
    "UPST", "URA", "URBN", "USB", "USO", "V", "VALE", "VALE3", "VEA", "VIG",
    "VIST", "VIV", "VIVT3", "VOD", "VRSN", "VRTX", "VST", "VXX", "VZ", "WBO",
    "WEGE3", "WFC", "WMT", "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP",
    "XLRE", "XLU", "XLV", "XLY", "XME", "XOM", "XP", "XPEV", "XROX", "XYZ",
    "YELP", "YZCA", "ZM"
]

# Inicializamos el traductor de inglés a español
traductor = GoogleTranslator(source='en', target='es')

# Diccionario de caché para no traducir la misma palabra muchas veces
cache_traducciones = {}

def traducir_texto(texto):
    """Traduce un texto al español utilizando caché para optimizar velocidad."""
    if not texto:
        return "No disponible"
    
    # Si ya lo tradujimos antes, lo tomamos del caché
    if texto in cache_traducciones:
        return cache_traducciones[texto]
    
    # Si es nuevo, lo traducimos y guardamos en caché
    try:
        traduccion = traductor.translate(texto)
        cache_traducciones[texto] = traduccion
        return traduccion
    except Exception as e:
        # En caso de error de conexión, devolvemos el texto original temporalmente
        print(f" (Aviso: Error al traducir '{texto}': {e})")
        return texto

def clasificar_cedears_dinamico(lista_tickers):
    datos_agrupados = {}
    total = len(lista_tickers)

    print(f"Iniciando el procesamiento dinámico de {total} tickers...\n")

    for index, simbolo in enumerate(lista_tickers, start=1):
        try:
            ticker = yf.Ticker(simbolo)
            info = ticker.info

            nombre = info.get("longName") or info.get("shortName", "Nombre no encontrado")
            sector_en = info.get("sector")
            industria_en = info.get("industry")
            tipo_activo = info.get("quoteType", "")

            # Identificación de ETFs o Fondos
            if tipo_activo == "ETF" or (not sector_en and not industria_en):
                categoria_en = info.get("category", "General ETF")
                sector_es = "Fondos y ETFs"
                industria_es = traducir_texto(categoria_en)
            else:
                # Traducción 100% automática obtenida desde yfinance en tiempo de ejecución
                sector_es = traducir_texto(sector_en)
                industria_es = traducir_texto(industria_en)

            # Agrupar en la estructura JSON
            if sector_es not in datos_agrupados:
                datos_agrupados[sector_es] = {}

            if industria_es not in datos_agrupados[sector_es]:
                datos_agrupados[sector_es][industria_es] = []

            datos_agrupados[sector_es][industria_es].append({
                "ticker": simbolo,
                "nombre": nombre
            })

            print(f"[{index}/{total}] OK -> {simbolo}: {sector_es} | {industria_es}")

        except Exception as e:
            print(f"[{index}/{total}] ERROR con {simbolo}: {e}")
            sector_err = "No Disponible / Error"
            if sector_err not in datos_agrupados:
                datos_agrupados[sector_err] = {"Desconocido": []}
            datos_agrupados[sector_err]["Desconocido"].append({
                "ticker": simbolo, 
                "nombre": "Error al descargar datos"
            })

        # Pausa preventiva de cortesía para evitar bloqueos por parte de Yahoo / Google
        time.sleep(0.2)

    return datos_agrupados

if __name__ == "__main__":
    # 1. Obtener y agrupar con traducción dinámica
    resultado = clasificar_cedears_dinamico(TICKERS)

    # 2. Guardar en JSON con el nombre solicitado
    nombre_archivo = "TICKERS_SECTORES_INDUSTRIA.json"
    with open(nombre_archivo, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, indent=4, ensure_ascii=False)

    print("\n" + "=" * 50)
    print(f"¡Proceso completado! Archivo generado: '{nombre_archivo}'")
    print(f"Sectores e industrias traducidos automáticamente de forma dinámica.")
    print("=" * 50)