import json
import time
import yfinance as yf
from deep_translator import GoogleTranslator

# Lista COMPLETA de ACCIONES de BCBA (Panel General, con sufijo .BA para Yahoo Finance)
TICKERS = [
    "A3.BA", "AGRO.BA", "ALUA.BA", "AUSO.BA", "BBAR.BA", "BHIP.BA",
    "BMA.BA", "BOLT.BA", "BPAT.BA", "BRIO.BA", "BROU.BA", "BYMA.BA",
    "CADO.BA", "CAPX.BA", "CARC.BA", "CECO2.BA", "CELU.BA", "CEPU.BA",
    "CGPA2.BA", "COME.BA", "CONC.BA", "CRES.BA", "CTIO.BA", "CVH.BA",
    "DGCU2.BA", "DOMA.BA", "DOME.BA", "EDN.BA", "FERR.BA", "FIPL.BA",
    "GAMI.BA", "GARO.BA", "GBAN.BA", "GCDI.BA", "GCLA.BA", "GCM.BA",
    "GGAL.BA", "GRIM.BA", "HARG.BA", "HAVA.BA", "IEB.BA", "INAG.BA",
    "INTR.BA", "INVJ.BA", "IRCP.BA", "IRSA.BA", "LEDE.BA", "LOMA.BA",
    "LONG.BA", "MERA.BA", "METR.BA", "MIRG.BA", "MOLA.BA", "MOLI.BA",
    "MORI.BA", "MTR.BA", "OEST.BA", "PAMP.BA", "PATA.BA", "POLL.BA",
    "RICH.BA", "RIGO.BA", "ROSE.BA", "SAMI.BA", "SEMI.BA", "SUPV.BA",
    "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TOMB.BA", "TRAN.BA", "TXAR.BA",
    "VALO.BA", "YPFD.BA",
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

    # 2. Guardar como BCBA (con .BA) separado de USA
    output_dir = "clarity-dashboard-main6/src/lib"
    bcba_file = f"{output_dir}/sectores-bcba.json"
    with open(bcba_file, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, indent=2, ensure_ascii=False)

    # 3. También guardar copia local para debug
    with open("TICKERS_SECTORES_INDUSTRIA.json", "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, indent=2, ensure_ascii=False)

    print("\n" + "=" * 50)
    print(f"Proceso completado!")
    print(f"  - BCBA: '{bcba_file}' ({len(TICKERS)} tickers)")
    print(f"  - Debug: 'TICKERS_SECTORES_INDUSTRIA.json'")
    print(f"Sectores e industrias traducidos automaticamente desde Yahoo Finance.")
    print("=" * 50)