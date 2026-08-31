import yfinance as yf
import pandas as pd
import time

# Principales tickers de la Bolsa de Buenos Aires (BCBA) con sus sectores conocidos
# Se consultan directamente ya que el screener de Yahoo Finance no retorna resultados para BUE

TICKERS_BCBA = {
    # Financial Services
    'GGAL.BA': 'Grupo Financiero Galicia',
    'BMA.BA': 'Banco Macro',
    'BBAR.BA': 'BBVA Argentina',
    'BYMA.BA': 'Bolsas y Mercados Argentinos',
    'SUPV.BA': 'Supervielle',
    'BHIP.BA': 'Banco Hipotecario',
    'SAMI.BA': 'Sancor Seguros',
    'CAPX.BA': 'Capex',
    
    # Energy
    'YPFD.BA': 'YPF',
    'PAMP.BA': 'Pampa Energía',
    'CEPU.BA': 'Central Puerto',
    'TGNO4.BA': 'Transportadora de Gas del Norte',
    'TGSU2.BA': 'TGS',
    'TRAN.BA': 'Transener',
    
    # Utilities
    'EDHD.BA': 'Edenor',
    'MESA.BA': 'Metrogas',
    'BASA.BA': 'BBVA Seguros',
    
    # Basic Materials
    'ALUA.BA': 'Aluar',
    'LOMA.BA': 'Loma Negra',
    'TXAR.BA': 'Ternium Argentina',
    
    # Consumer Defensive
    'CARC.BA': 'Carrefour Argentina',
    'MOLI.BA': 'Molinos Río de la Plata',
    'PATA.BA': 'Grupo La Anónima',
    'WATT.BA': 'Watt’s',
    
    # Consumer Cyclical
    'GARO.BA': 'Garbarino',
    'LONG.BA': 'Longvie',
    'RICH.BA': 'Richards',
    'COME.BA': 'Sociedad Comercial del Plata',
    'DYCA.BA': 'Dycasa',
    
    # Industrials
    'AGRO.BA': 'Agrometal',
    'AUSO.BA': 'Autopistas del Sol',
    'CADO.BA': 'Carboclor',
    'CRES.BA': 'Cresud',
    'FIPL.BA': 'Fiplasto',
    'GCLA.BA': 'Grupo Clarín',
    'HARG.BA': 'Holcim Argentina',
    'HAVA.BA': 'Havanna',
    'LEDESMA.BA': 'Ledesma',
    'METR.BA': 'Metrogas',
    'OEST.BA': 'Grupo Concesionario del Oeste',
    'POLL.BA': 'Polledo',
    'SEMI.BA': 'Semino',
    
    # Technology
    'BOLT.BA': 'Boldt',
    'CVH.BA': 'Cablevisión Holding',
    'DGCU2.BA': 'DGCU2',
    'TECO2.BA': 'Telecom Argentina',
    
    # Real Estate
    'APBR.BA': 'Alto Palermo',
    'IRCP.BA': 'IRSA Propiedades Comerciales',
    'IRSAD.BA': 'IRSA Inversiones y Representaciones',
}

def obtener_info_ticker(ticker_symbol, nombre):
    """Obtiene información de sector e industria de un ticker."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        market_cap = info.get('marketCap', None)
        currency = info.get('currency', 'ARS')
        exchange = info.get('exchange', 'BCBA')
        
        return {
            'symbol': ticker_symbol,
            'nombre': nombre,
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
            'currency': currency,
            'exchange': exchange
        }
    except Exception as e:
        print(f"  ✗ Error con {ticker_symbol}: {e}")
        return {
            'symbol': ticker_symbol,
            'nombre': nombre,
            'sector': 'ERROR',
            'industry': 'ERROR',
            'market_cap': None,
            'currency': 'ARS',
            'exchange': 'BCBA'
        }

print("=" * 60)
print("OBTENIENDO TICKERS DE BUENOS AIRES POR SECTOR")
print("=" * 60)

resultados = []
errores = []

for i, (ticker, nombre) in enumerate(TICKERS_BCBA.items(), 1):
    print(f"\n[{i}/{len(TICKERS_BCBA)}] Consultando {ticker} - {nombre}...")
    info = obtener_info_ticker(ticker, nombre)
    resultados.append(info)
    
    if info['sector'] != 'ERROR':
        print(f"  ✓ Sector: {info['sector']} | Industria: {info['industry']}")
    else:
        errores.append(ticker)
    
    time.sleep(0.3)  # evitar rate limit

# Crear DataFrame
df = pd.DataFrame(resultados)

# Guardar CSV
output_csv = r"c:\Users\boosa\Desktop\clientes\yfinance analisis\tickers_buenos_aires_sectores.csv"
df.to_csv(output_csv, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"TOTAL: {len(resultados)} tickers procesados")
print(f"Errores: {len(errores)}")
print("=" * 60)

# Mostrar resumen por sector
if not df.empty and 'sector' in df.columns:
    print("\n📊 RESUMEN POR SECTOR:")
    print(df[df['sector'] != 'ERROR']['sector'].value_counts())
    
    print("\n📋 DETALLE POR SECTOR:")
    for sector in df[df['sector'] != 'ERROR']['sector'].unique():
        print(f"\n{sector}:")
        sector_df = df[df['sector'] == sector][['symbol', 'nombre', 'industry']]
        for _, row in sector_df.iterrows():
            print(f"  - {row['symbol']}: {row['nombre']} ({row['industry']})")

print(f"\n✓ Guardado en: {output_csv}")

if errores:
    print(f"\n⚠ Tickers con error: {', '.join(errores)}")
