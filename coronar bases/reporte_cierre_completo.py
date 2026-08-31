import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

# ============================================
# CONFIGURACIÓN (desde variables de entorno)
# ============================================

# API BCRA Configuration
BCRA_API_TOKEN = os.environ.get("BCRA_API_TOKEN", "")
BCRA_API_HEADER = f"BEARER {BCRA_API_TOKEN}"
BCRA_API_BASE_URL = "https://api.estadisticasbcra.com"

# API IOL Configuration
IOL_USERNAME = os.environ.get("IOL_USERNAME", "")
IOL_PASSWORD = os.environ.get("IOL_PASSWORD", "")
IOL_API_TOKEN = None  # Se obtiene automáticamente
IOL_API_BASE_URL = "https://api.invertironline.com"

# Lista de endpoints BCRA
BCRA_ENDPOINTS = {
    "usd": "Cotización del USD",
    "usd_of": "Cotización del USD Oficial",
    "reservas": "Reservas internacionales",
    "base": "Base monetaria",
    "cer": "CER",
    "merval": "MERVAL",
    "inflacion_mensual_oficial": "Inflación mensual oficial",
    "inflacion_interanual_oficial": "Inflación interanual oficial"
}

# Tickers YFinance para datos internacionales
YFINANCE_TICKERS = {
    # Índices US
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
    
    # Acciones destacadas
    "NEE": "NextEra Energy",
    "SO": "Southern Company",
    "PLTR": "Palantir",
    "ORCL": "Oracle",
    
    # Sectores ETFs
    "XLU": "Utilities Sector",
    "XLK": "Technology Sector",
    
    # Tasas e índices
    "^TNX": "Treasury 10Y",
    "DX-Y.NYB": "DXY",
    "^VIX": "VIX",
    
    # Commodities
    "GLD": "Oro",
    "SLV": "Plata",
    "BZ=F": "Petróleo Brent",
    "ZS=F": "Soja",
    "BTC-USD": "Bitcoin"
}

# Tickers YFinance para mercados globales
GLOBAL_MARKETS = {
    "^FCHI": "Francia CAC 40",
    "^GDAXI": "Alemania DAX",
    "^MXX": "México IPC",
    "^KS11": "Corea KOSPI"
}

# ============================================
# FUNCIONES YFINANCE (DATOS INTERNACIONALES)
# ============================================

def get_yfinance_data(ticker_symbol, period="5d"):
    """Obtiene datos históricos de YFinance"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return None
        
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest
        
        cambio = ((latest['Close'] - previous['Close']) / previous['Close'] * 100) if previous['Close'] != 0 else 0
        
        return {
            'symbol': ticker_symbol,
            'ultimo_precio': latest['Close'],
            'precio_anterior': previous['Close'],
            'variacion': cambio,
            'apertura': latest['Open'],
            'maximo': latest['High'],
            'minimo': latest['Low'],
            'volumen': latest['Volume'],
            'fecha': latest.name.strftime('%Y-%m-%d')
        }
    except Exception as e:
        print(f"Error obteniendo datos YFinance para {ticker_symbol}: {str(e)}")
        return None

def get_international_markets():
    """Obtiene datos de mercados internacionales"""
    print("🌍 Obteniendo datos internacionales...")
    
    data = {
        'indices': {},
        'acciones': {},
        'sectores': {},
        'tasas': {},
        'commodities': {},
        'global': {}
    }
    
    # Categorizar y obtener datos
    for symbol, name in YFINANCE_TICKERS.items():
        result = get_yfinance_data(symbol)
        if result:
            result['nombre'] = name
            
            if symbol in ['^GSPC', '^IXIC', '^DJI', '^RUT']:
                data['indices'][symbol] = result
            elif symbol in ['NEE', 'SO', 'PLTR', 'ORCL']:
                data['acciones'][symbol] = result
            elif symbol in ['XLU', 'XLK']:
                data['sectores'][symbol] = result
            elif symbol in ['^TNX', 'DX-Y.NYB', '^VIX']:
                data['tasas'][symbol] = result
            elif symbol in ['GLD', 'SLV', 'BZ=F', 'ZS=F', 'BTC-USD']:
                data['commodities'][symbol] = result
    
    # Mercados globales
    for symbol, name in GLOBAL_MARKETS.items():
        result = get_yfinance_data(symbol)
        if result:
            result['nombre'] = name
            data['global'][symbol] = result
    
    return data

# ============================================
# FUNCIONES API IOL (DATOS LOCALES)
# ============================================

def obtener_iol_token(username, password):
    """Obtiene token de acceso de IOL usando usuario y contraseña"""
    token_url = 'https://api.invertironline.com/token'
    payload = {
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(token_url, data=payload, headers=headers)
        if response.status_code == 200:
            tokens = response.json()
            return tokens['access_token'], tokens['refresh_token']
        else:
            print(f'Error en la solicitud: {response.status_code}')
            print(response.text)
            return None, None
    except Exception as e:
        print(f"Error obteniendo token IOL: {str(e)}")
        return None, None

def get_iol_data(endpoint, headers=None):
    """Obtiene datos del API IOL"""
    if not IOL_API_TOKEN:
        print("⚠️ Token IOL no configurado. Saltando datos locales.")
        return None
    
    if headers is None:
        headers = {
            'Authorization': f'BEARER {IOL_API_TOKEN}',
            'Content-Type': 'application/json'
        }
    
    try:
        url = f"{IOL_API_BASE_URL}{endpoint}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error obteniendo datos IOL de {endpoint}: {str(e)}")
        return None

def get_local_markets():
    """Obtiene datos de mercados locales argentinos"""
    print("🇦🇷 Obteniendo datos locales...")
    
    global IOL_API_TOKEN
    
    # Obtener token automáticamente si no está configurado
    if not IOL_API_TOKEN and IOL_USERNAME and IOL_PASSWORD:
        print("🔐 Autenticando con IOL...")
        IOL_API_TOKEN, refresh_token = obtener_iol_token(IOL_USERNAME, IOL_PASSWORD)
        if IOL_API_TOKEN:
            print("✅ Token IOL obtenido exitosamente")
        else:
            print("❌ Error al obtener token IOL")
    
    data = {
        'merval': None,
        'futuros_usd': None,
        'fx': {}
    }
    
    # Obtener cotizaciones de futuros
    futuros = get_iol_data('/api/v2/cotizaciones-orleans-panel/futuros/argentina/Todos')
    if futuros and 'titulos' in futuros:
        data['futuros_usd'] = futuros['titulos']
    
    # Obtener MEP
    try:
        mep_response = requests.post(
            f"{IOL_API_BASE_URL}/api/v2/Cotizaciones/MEP",
            headers={'Authorization': f'BEARER {IOL_API_TOKEN}', 'Content-Type': 'application/json'},
            json={"simbolo": "AL30", "idPlazoOperatoriaCompra": 2, "idPlazoOperatoriaVenta": 2}
        )
        if mep_response.status_code == 200:
            data['fx']['MEP'] = mep_response.json()
    except:
        pass
    
    return data

# ============================================
# FUNCIONES API BCRA
# ============================================

def get_bcra_api_data(endpoint):
    """Obtiene datos del API de estadísticas BCRA"""
    url = f"{BCRA_API_BASE_URL}/{endpoint}"
    headers = {
        'Authorization': BCRA_API_HEADER
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return None
        
        df = pd.DataFrame(data)
        if 'd' in df.columns:
            df = df.rename(columns={'d': 'fecha'})
        if 'v' in df.columns:
            df = df.rename(columns={'v': 'valor'})
        
        return df
    except Exception as e:
        print(f"Error obteniendo datos BCRA para {endpoint}: {str(e)}")
        return None

def get_bcra_variations():
    """Obtiene variaciones de variables BCRA clave"""
    print("🏛️ Obteniendo datos BCRA...")
    
    data = {}
    
    for endpoint, descripcion in BCRA_ENDPOINTS.items():
        df = get_bcra_api_data(endpoint)
        if df is not None and not df.empty and 'valor' in df.columns:
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            df = df.dropna(subset=['valor'])
            
            if len(df) >= 2:
                values = df['valor'].values
                var_diaria = ((values[-1] - values[-2]) / values[-2] * 100)
                
                data[endpoint] = {
                    'descripcion': descripcion,
                    'valor_actual': values[-1],
                    'valor_anterior': values[-2],
                    'variacion': var_diaria
                }
    
    return data

# ============================================
# GENERACIÓN DE REPORTE
# ============================================

def print_international_report(data):
    """Imprime reporte de mercados internacionales"""
    print("\n" + "="*70)
    print("🇺🇸 CIERRE INTERNACIONAL")
    print("="*70)
    
    # Índices principales
    print("\n📊 Principales Índices:")
    for symbol, info in data['indices'].items():
        emoji = "🟢" if info['variacion'] >= 0 else "🔴"
        print(f"* {emoji} {info['nombre']}: {info['variacion']:+.2f}%")
    
    # Acciones destacadas
    print("\nMovimientos Destacados:")
    for symbol, info in data['acciones'].items():
        emoji = "🟢" if info['variacion'] >= 0 else "🔴"
        print(f"* {emoji} {info['nombre']}: {info['variacion']:+.2f}%")
    
    # Sectores
    print(f"\n🟢 Sector Ganador: {data['sectores']['XLU']['nombre']} {data['sectores']['XLU']['variacion']:+.2f}%")
    print(f"🔴 Sector Perdedor: {data['sectores']['XLK']['nombre']} {data['sectores']['XLK']['variacion']:+.2f}%")
    
    # Tasas e índices
    print("\nTasas e índices:")
    for symbol, info in data['tasas'].items():
        emoji = "📉" if info['variacion'] >= 0 else "📈"
        print(f"- {emoji} {info['nombre']}: {info['ultimo_precio']:.2f} ({info['variacion']:+.2f}%)")
    
    # Mercados globales
    print("\n🌐 Global:")
    for symbol, info in data['global'].items():
        emoji = "📊" 
        print(f"* {emoji} {info['nombre']}: {info['variacion']:+.2f}%")
    
    # Commodities
    print("\nCommodities:")
    for symbol, info in data['commodities'].items():
        emoji = "🟢" if info['variacion'] >= 0 else "🔴"
        print(f"* {emoji} {info['nombre']}: {info['ultimo_precio']:.2f} ({info['variacion']:+.2f}%)")

def print_local_report(iol_data, bcra_data):
    """Imprime reporte de mercados locales"""
    print("\n" + "="*70)
    print("🇦🇷 CIERRE LOCAL")
    print("="*70)
    
    # Datos BCRA
    if 'usd' in bcra_data:
        usd = bcra_data['usd']
        print(f"\nUSD Blue: ${usd['valor_actual']:.2f} ({usd['variacion']:+.2f}%)")
    
    if 'usd_of' in bcra_data:
        usd_of = bcra_data['usd_of']
        print(f"USD Oficial: ${usd_of['valor_actual']:.2f} ({usd_of['variacion']:+.2f}%)")
    
    if 'reservas' in bcra_data:
        reservas = bcra_data['reservas']
        print(f"💰 BCRA: Reservas USD {reservas['valor_actual']:,.0f}")
    
    if 'merval' in bcra_data:
        merval = bcra_data['merval']
        emoji = "🟢" if merval['variacion'] >= 0 else "🔴"
        print(f"\nMerval: {emoji} {merval['variacion']:+.2f}% (USD {merval['valor_actual']:.2f})")
    
    # Datos IOL si están disponibles
    if iol_data and iol_data['futuros_usd']:
        print("\nFuturos USD:")
        for futuro in iol_data['futuros_usd'][:3]:  # Primeros 3 futuros
            if 'simbolo' in futuro and 'ultimoPrecio' in futuro:
                print(f"• {futuro['simbolo']}: ${futuro['ultimoPrecio']:.2f}")
    
    if iol_data and iol_data['fx'].get('MEP'):
        print(f"\nFX: MEP: ${iol_data['fx']['MEP']:.2f}")

def generate_full_report():
    """Genera reporte completo de cierre"""
    print("="*70)
    print("📊 REPORTE DE CIERRE - MERCADOS FINANCIEROS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Obtener datos de todas las fuentes
    international_data = get_international_markets()
    local_data = get_local_markets()
    bcra_data = get_bcra_variations()
    
    # Imprimir reportes
    print_international_report(international_data)
    print_local_report(local_data, bcra_data)
    
    print("\n" + "="*70)
    print("✅ REPORTE COMPLETADO")
    print("="*70)
    
    # Guardar en JSON
    report = {
        'fecha': datetime.now().isoformat(),
        'internacional': international_data,
        'local': local_data,
        'bcra': bcra_data
    }
    
    filename = f"reporte_cierre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📁 Reporte guardado en: {filename}")

# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

if __name__ == "__main__":
    # Configurar token IOL si está disponible
    # IOL_API_TOKEN = "TU_TOKEN_AQUI"
    
    generate_full_report()
