import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import warnings
import json

warnings.filterwarnings('ignore')

# Lista de tickers a procesar
TICKERS = [
    "MU", "MSFT", "NVDA", "META", "IBM", "SPY", "MELI", "IBIT", "VIST", "INTC", 
    "AMD", "ORCL", "RGTI", "GLOB", "PLTR", "MSTR", "TSLA", "NU", "AAPL", "CRWV", 
    "SATL", "CRM", "SPCE", "GOOGL", "QQQ", "AVGO", "GPRK", "EWZ", "ADBE", "AMZN", 
    "NOKA", "ASTS", "NIO", "QCOM", "PBR", "HUT", "KO", "UBER", "KEEL", "GLD", 
    "TSM", "RIOT", "SLV", "OKLO", "IREN", "LAC", "MCD", "BRKB", "ETHA", "RKLB", 
    "SMH", "XLE", "ARM", "COPX", "COIN", "MRVL", "WMT", "ASML", "V", "HMY", 
    "CEG", "BBD", "SNOW", "JD", "BABA", "ACN", "LAR", "JPM", "PG", "VALE", 
    "NKE", "B", "URA", "NFLX", "PATH", "SAP", "VST", "EEM", "AI", "BIOX", 
    "PFE", "LLY", "HL", "DIA", "CAT", "HPQ", "SPOT", "PEP", "HOOD", "CVX", 
    "UNH", "MUX", "FXI", "XLV", "ALAB", "UPST", "PAGS", "XLP", "AMAT", "TXN", 
    "RBLX", "XLF", "STNE", "SPXL", "JMIA", "XLU", "XROX", "VEA", "COST", "MA", 
    "PAAS", "FSLR", "IWM", "TQQQ", "JNJ", "AXP", "AAL", "F", "TEAM", "RIO", 
    "EMBJ", "MO", "PYPL", "PANW", "LMT", "ARCO", "EA", "SE", "SCCO", "ADGO", 
    "LVS", "VZ", "ACWI", "BA", "XOM", "PDD", "SDA", "ANF", "LRCX", "DE", "T", 
    "DISN", "C", "DOCU", "SID", "BIDU", "VXX", "SHOP", "BMY", "TXR", "XP", 
    "VIG", "ISRG", "TM", "PINS", "GLW", "OXY", "IEUR", "GE", "TEN", "MRNA", 
    "SWKS", "FCX", "HSY", "NEM", "CSCO", "ARKK", "BB", "ZM", "XYZ", "YELP", 
    "HON", "TCOM", "RACE", "CAR", "UAL", "BA.C", "CDE", "PSQ", "STLA", "MMM", 
    "GS", "BP", "IVW", "SPGI", "ABNB", "IVE", "HD", "TWLO", "ADI", "BAK", 
    "EBAY", "SH", "GFI", "UL", "ABT", "TGT", "GGB", "MOS", "BKNG", "SAN", 
    "ITUB", "BNG", "AIG", "AEM", "SBUX", "AMGN", "MDT", "RTX", "HAL", "HWM", 
    "PM", "GM", "DEO", "FDX", "SNAP", "DOW", "TRIP", "GILD", "SONY", "KMB", 
    "MRK", "MGLU3", "ADP", "HOG", "ABBV", "SHEL", "BHP", "AAP", "AVY", "CL", 
    "XLRE", "NVS", "EWJ", "TMUS", "KGC", "BBV", "WFC", "BIIB", "ABEV", "CX", 
    "DAL", "NUE", "TMO", "NG", "SLB", "PETR3", "ROKU", "ETSY", "HSBC", "MDLZ", 
    "CAAP", "AZN", "MRSH", "BSBR", "HDB", "MSI", "XLB", "BNY", "DD", "CCL", 
    "INFY", "NGG", "URBN", "EQNR", "XLC", "ORLY", "JOYY", "VRSN", "NXE", "CVS", 
    "GT", "ERIC", "PRIO3", "HMC", "GSK"
]

def obtener_info_ticker(simbolo):
    """Obtiene información de sector e industria de un ticker"""
    try:
        ticker = yf.Ticker(simbolo)
        info = ticker.info
        
        nombre = info.get('longName', 'No disponible')
        sector = info.get('sector', 'No disponible')
        industria = info.get('industry', 'No disponible')
        
        return {
            'ticker': simbolo,
            'nombre': nombre,
            'sector': sector,
            'industria': industria
        }
    except Exception as e:
        print(f"  ✗ Error obteniendo {simbolo}: {e}")
        return {
            'ticker': simbolo,
            'nombre': 'Error',
            'sector': 'Error',
            'industria': str(e)
        }

def procesar_tickers(tickers):
    """Procesa lista de tickers y obtiene su información"""
    print("="*70)
    print("OBTENIENDO SECTOR E INDUSTRIA DE TICKERS")
    print("="*70)
    print(f"Total de tickers a procesar: {len(tickers)}")
    print()
    
    resultados = []
    errores = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Procesando {ticker}...", end=" ")
        
        info = obtener_info_ticker(ticker)
        
        if info['sector'] == 'Error':
            errores.append(info)
            print("❌")
        else:
            resultados.append(info)
            print(f"✓ {info['sector'][:30]}")
        
        # Pequeña pausa para no saturar la API
        if i % 10 == 0:
            time.sleep(1)
    
    return resultados, errores

def agrupar_por_sector_industria(resultados):
    """Agrupa tickers por sector e industria"""
    print("\n" + "="*70)
    print("AGRUPANDO POR SECTOR E INDUSTRIA")
    print("="*70)
    
    agrupado = {}
    
    for item in resultados:
        sector = item['sector']
        industria = item['industria']
        
        if sector == 'Error':
            continue
        
        if sector not in agrupado:
            agrupado[sector] = {}
        
        if industria not in agrupado[sector]:
            agrupado[sector][industria] = []
        
        agrupado[sector][industria].append({
            'ticker': item['ticker'],
            'nombre': item['nombre']
        })
    
    # Mostrar resumen de agrupación
    print(f"\nSectores encontrados: {len(agrupado)}")
    for sector, industrias in agrupado.items():
        total_tickers = sum(len(tickers) for tickers in industrias.values())
        print(f"  - {sector}: {len(industrias)} industrias, {total_tickers} tickers")
    
    return agrupado

def descargar_series_historicas(agrupado):
    """Descarga series históricas de 10 años para todos los tickers en lotes"""
    print("\n" + "="*70)
    print("DESCARGANDO SERIES HISTÓRICAS DE 10 AÑOS (EN LOTES)")
    print("="*70)
    
    periodo = "10y"
    datos_completos = {}
    
    # Recolectar todos los tickers
    all_tickers = []
    for sector, industrias in agrupado.items():
        for industria, tickers in industrias.items():
            for ticker_info in tickers:
                all_tickers.append({
                    'ticker': ticker_info['ticker'],
                    'nombre': ticker_info['nombre'],
                    'sector': sector,
                    'industria': industria
                })
    
    total_tickers = len(all_tickers)
    print(f"Total de tickers a descargar: {total_tickers}")
    print(f"Período: {periodo}")
    print(f"Descargando en lotes de 50 tickers...")
    print()
    
    # Descargar en lotes de 50
    batch_size = 50
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i+batch_size]
        batch_tickers = [t['ticker'] for t in batch]
        
        print(f"Lote {i//batch_size + 1}/{(len(all_tickers)-1)//batch_size + 1} ({len(batch_tickers)} tickers)...")
        
        try:
            # Descargar lote completo
            data = yf.download(batch_tickers, period=periodo, progress=False)
            
            if data is not None and len(data) > 0:
                # Obtener columna de cierre
                if isinstance(data.columns, pd.MultiIndex):
                    close_data = data['Close']
                else:
                    close_data = data
                
                # Procesar cada ticker del lote
                for ticker_info in batch:
                    ticker = ticker_info['ticker']
                    sector = ticker_info['sector']
                    industria = ticker_info['industria']
                    nombre = ticker_info['nombre']
                    
                    if sector not in datos_completos:
                        datos_completos[sector] = {}
                    if industria not in datos_completos[sector]:
                        datos_completos[sector][industria] = {}
                    
                    if ticker in close_data.columns:
                        ticker_data = close_data[ticker].dropna()
                        
                        if len(ticker_data) > 0:
                            # Convertir a formato JSON serializable
                            series_dict = {}
                            for fecha, valor in ticker_data.items():
                                series_dict[fecha.strftime('%Y-%m-%d')] = float(valor)
                            
                            datos_completos[sector][industria][ticker] = {
                                'nombre': nombre,
                                'datos': series_dict,
                                'fecha_inicio': ticker_data.index[0].strftime('%Y-%m-%d'),
                                'fecha_fin': ticker_data.index[-1].strftime('%Y-%m-%d'),
                                'registros': len(ticker_data)
                            }
                            print(f"  ✓ {ticker} - {len(ticker_data)} registros")
                        else:
                            datos_completos[sector][industria][ticker] = {
                                'error': 'No hay datos válidos'
                            }
                            print(f"  ✗ {ticker} - No hay datos válidos")
                    else:
                        datos_completos[sector][industria][ticker] = {
                            'error': 'No disponible en datos'
                        }
                        print(f"  ✗ {ticker} - No disponible en datos")
            else:
                print(f"  ✗ Error descargando lote: No hay datos")
                for ticker_info in batch:
                    sector = ticker_info['sector']
                    industria = ticker_info['industria']
                    ticker = ticker_info['ticker']
                    if sector not in datos_completos:
                        datos_completos[sector] = {}
                    if industria not in datos_completos[sector]:
                        datos_completos[sector][industria] = {}
                    datos_completos[sector][industria][ticker] = {
                        'error': 'Error en descarga de lote'
                    }
        
        except Exception as e:
            print(f"  ✗ Error en lote: {str(e)[:50]}")
            for ticker_info in batch:
                sector = ticker_info['sector']
                industria = ticker_info['industria']
                ticker = ticker_info['ticker']
                if sector not in datos_completos:
                    datos_completos[sector] = {}
                if industria not in datos_completos[sector]:
                    datos_completos[sector][industria] = {}
                datos_completos[sector][industria][ticker] = {
                    'error': str(e)
                }
    
    return datos_completos

def guardar_json(datos, agrupado):
    """Guarda todos los datos en un archivo JSON"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"series_historicas_sectores_industrias_{timestamp}.json"
    
    output = {
        'metadata': {
            'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'periodo': '10 años',
            'total_sectores': len(datos),
            'total_tickers_procesados': sum(
                len(tickers) for sector in datos.values() 
                for industria in sector.values() 
                for tickers in [industria] if isinstance(tickers, dict)
            )
        },
        'agrupacion': agrupado,
        'series_historicas': datos
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ JSON guardado: {filename}")
    return filename

def mostrar_resumen(datos):
    """Muestra resumen de datos descargados"""
    print("\n" + "="*70)
    print("RESUMEN DE SERIES HISTÓRICAS DESCARGADAS")
    print("="*70)
    
    total_tickers = 0
    total_con_datos = 0
    total_con_errores = 0
    
    for sector, industrias in datos.items():
        for industria, tickers in industrias.items():
            for ticker, info in tickers.items():
                total_tickers += 1
                if 'datos' in info:
                    total_con_datos += 1
                else:
                    total_con_errores += 1
    
    print(f"\n� ESTADÍSTICAS:")
    print("-"*70)
    print(f"  Total de tickers procesados:     {total_tickers}")
    print(f"  Con datos históricos:            {total_con_datos} ({total_con_datos/total_tickers*100:.1f}%)")
    print(f"  Con errores:                     {total_con_errores} ({total_con_errores/total_tickers*100:.1f}%)")
    print(f"  Sectores:                        {len(datos)}")
    print("="*70)

def main():
    # Paso 1: Obtener sector e industria
    resultados, errores = procesar_tickers(TICKERS)
    
    # Paso 2: Agrupar por sector e industria
    agrupado = agrupar_por_sector_industria(resultados)
    
    # Paso 3: Descargar series históricas de 10 años
    datos_completos = descargar_series_historicas(agrupado)
    
    # Paso 4: Guardar en JSON
    filename = guardar_json(datos_completos, agrupado)
    
    # Paso 5: Mostrar resumen
    mostrar_resumen(datos_completos)
    
    print("\n✅ Proceso completado exitosamente")
    print(f"📁 Archivo generado: {filename}")

if __name__ == "__main__":
    main()
