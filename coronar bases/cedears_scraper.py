```python
import yfinance as yf
import json

def obtener_info_ticker(simbolo):
    try:
        ticker = yf.Ticker(simbolo)
        info = ticker.info
        sector = info.get('sector', 'No disponible')
        industria = info.get('industry', 'No disponible')
        nombre = info.get('longName', 'Nombre no encontrado')
        return {
            'ticker': simbolo,
            'nombre': nombre,
            'sector': sector,
            'industria': industria
        }
    except Exception as e:
        print(f