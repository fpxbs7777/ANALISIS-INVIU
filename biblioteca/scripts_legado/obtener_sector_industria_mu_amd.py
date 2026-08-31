import yfinance as yf

# Obtener información de MU y AMD
tickers = ['MU', 'AMD']

for ticker in tickers:
    stock = yf.Ticker(ticker)
    info = stock.info
    
    sector = info.get('sector', 'No disponible')
    industry = info.get('industry', 'No disponible')
    
    print(f"{ticker}:")
    print(f"  Sector: {sector}")
    print(f"  Industria: {industry}")
    print()
