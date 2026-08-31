import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

print("=" * 60)
print("EMPRESAS QUE REPORTAN EPS ESTE Y EL PRÓXIMO MES")
print("=" * 60)

OUTPUT_CSV = r"c:\Users\boosa\Desktop\clientes\yfinance analisis\earnings_proximos_meses.csv"

# Calcular rango de fechas: este mes y el próximo mes
hoy = datetime.now()
primer_dia_este_mes = hoy.replace(day=1)
if hoy.month == 12:
    primer_dia_proximo_mes = hoy.replace(year=hoy.year + 1, month=1, day=1)
else:
    primer_dia_proximo_mes = hoy.replace(month=hoy.month + 1, day=1)

ultimo_dia_proximo_mes = (primer_dia_proximo_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

print(f"\nRango de fechas:")
print(f"  Desde: {primer_dia_este_mes.strftime('%Y-%m-%d')}")
print(f"  Hasta: {ultimo_dia_proximo_mes.strftime('%Y-%m-%d')}")

# Tickers principales de mercados globales (SP500, NASDAQ, BCBA)
TICKERS = [
    # SP500 - Principales
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA", "BAC", "ABBV", "PFE", "KO", "PEP",
    "WMT", "MRK", "CSCO", "ADBE", "NFLX", "CRM", "ACN", "ABT", "BMY", "TMO",
    "AVGO", "TXN", "QCOM", "COST", "DIS", "VZ", "NKE", "DHR", "PM", "NEE",
    "AMGN", "LIN", "MDT", "HON", "UPS", "RTX", "CVX", "XOM", "LLY", "WFC",
    "SBUX", "IBM", "INTC", "AMD", "INTU", "GS", "BLK", "C", "MS", "GE",
    "CAT", "DE", "BA", "LMT", "NOC", "SPGI", "PLD", "EQIX", "PSA", "O",
    "CCI", "AMT", "ZTS", "GILD", "REGN", "VRTX", "ISRG", "SYK", "BDX", "EW",
    "ICE", "CME", "MCO", "SPGI", "FIS", "FISV", "PYPL", "SQ", "UBER", "LYFT",
    "ZM", "DOCU", "SNOW", "CRWD", "OKTA", "DDOG", "NET", "FSLY", "TWLO", "SHOP",
    # NASDAQ adicionales
    "ROKU", "PTON", "LCID", "RIVN", "PLTR", "ASML", "TSM", "SONY", "TM", "SAP",
    "SHOP", "SE", "MELI", "BABA", "JD", "PDD", "NTES", "TCOM", "LI", "XPEV",
    "NIO", "DIDI", "TCEHY", "BIDU", "WB", "ZH", "BEKE", "VIPS", "FUTU", "BGNE",
    # BCBA - Argentina
    "GGAL", "YPF", "PAM", "CRESY", "BMA", "SUPV", "BBAR", "LOMA", "CEPU", "EDN",
    "TGS", "TX", "IRCP", "AGRO", "SAMI", "VALO", "CAAP", "TECO2.BA", "YPFD.BA",
    # ETFs populares
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "BND", "AGG",
    "XLF", "XLK", "XLE", "XLU", "XLI", "XLP", "XLB", "XRT", "ARKK", "ARKQ"
]

# Seleccionar rango de tickers a consultar
print(f"\nTotal de tickers disponibles: {len(TICKERS)}")
print("¿Cuántos tickers consultar? (Enter para todos, o número)")
respuesta = input("Cantidad: ").strip()
if respuesta and respuesta.isdigit():
    cantidad = int(respuesta)
    tickers_a_consultar = TICKERS[:cantidad]
else:
    tickers_a_consultar = TICKERS

print(f"✓ Se consultarán {len(tickers_a_consultar)} tickers")

# Crear DataFrame de tickers
df_tickers = pd.DataFrame({'symbol': tickers_a_consultar})

# Obtener earnings dates para cada ticker
earnings_en_rango = []
errores = []

print(f"\nObteniendo earnings dates para {len(df_tickers)} tickers...")
print("Esto puede tardar varios minutos...\n")

for i, row in df_tickers.iterrows():
    symbol = row['symbol']
    try:
        ticker = yf.Ticker(symbol)

        # Obtener nombre de la empresa
        company_name = ""
        try:
            info = ticker.info
            company_name = info.get('shortName', '') or info.get('longName', '')
        except:
            pass

        earnings_dates = ticker.get_earnings_dates(limit=12)
        
        if earnings_dates is not None and not earnings_dates.empty:
            # earnings_dates tiene columnas como 'Earnings Date', 'EPS Estimate', 'Reported EPS', 'Surprise(%)'
            for _, earning_row in earnings_dates.iterrows():
                earning_date = earning_row.get('Earnings Date')
                if pd.notna(earning_date):
                    # Convertir a datetime si es string
                    if isinstance(earning_date, str):
                        try:
                            earning_date = pd.to_datetime(earning_date)
                        except:
                            continue
                    
                    # Verificar si está en el rango
                    if primer_dia_este_mes <= earning_date <= ultimo_dia_proximo_mes:
                        info = {
                            'symbol': symbol,
                            'company_name': company_name,
                            'earnings_date': earning_date.strftime('%Y-%m-%d'),
                            'eps_estimate': earning_row.get('EPS Estimate', ''),
                            'reported_eps': earning_row.get('Reported EPS', ''),
                            'surprise_pct': earning_row.get('Surprise(%)', '')
                        }
                        earnings_en_rango.append(info)
                        print(f"  ✓ {symbol} ({company_name[:20]}): {earning_date.strftime('%Y-%m-%d')}")
        
        time.sleep(0.2)  # evitar rate limit
        
    except Exception as e:
        errores.append((symbol, str(e)))
        if i < 5:  # mostrar primeros errores
            print(f"  ✗ {symbol}: {e}")
    
    if (i + 1) % 50 == 0:
        print(f"  Progreso: {i + 1}/{len(df_tickers)} tickers procesados")

# Guardar resultados
if earnings_en_rango:
    df_result = pd.DataFrame(earnings_en_rango)
    df_result = df_result.sort_values('earnings_date')
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(df_result)} empresas reportan EPS en el rango")
    print(f"{'='*60}")
    
    df_result.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n✓ Guardado en: {OUTPUT_CSV}")
    
    print("\nResumen por fecha:")
    print(df_result['earnings_date'].value_counts().sort_index())
    
    print("\nPrimeros 10 resultados:")
    print(df_result.head(10).to_string(index=False))
else:
    print("\n✗ No se encontraron earnings en el rango de fechas")

if errores:
    print(f"\nErrores ({len(errores)}):")
    for symbol, error in errores[:10]:  # mostrar primeros 10
        print(f"  - {symbol}: {error}")
