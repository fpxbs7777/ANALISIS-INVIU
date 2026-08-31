"""
Configuración de tickers por sector y factores de diversificación.
Este módulo proporciona funciones para obtener tickers organizados por sectores.
"""

# ============================================================================
# CONFIGURACIONES COMPLETAS DE TICKERS POR SECTOR
# ============================================================================

# TECNOLOGÍA (Technology)
TECH_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'AVGO', 'ORCL', 'ADBE', 'CSCO',
    'CRM', 'ACN', 'TXN', 'IBM', 'QCOM', 'INTC', 'AMD', 'NOW', 'INTU', 'AMAT',
    'UBER', 'SHOP', 'NET', 'SNOW', 'CRWD', 'PANW', 'FTNT', 'ZS', 'OKTA', 'TEAM',
    'DDOG', 'MDB', 'PLTR', 'U', 'TWLO', 'DOCU', 'RBLX', 'SQ', 'PYPL', 'COIN'
]

# SERVICIOS FINANCIEROS (Financial Services)
FINANCIAL_TICKERS = [
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'SCHW', 'BLK', 'C', 'AXP', 'V',
    'MA', 'PYPL', 'SPGI', 'MCO', 'ICE', 'CME', 'BX', 'KKR', 'APO', 'ARES',
    'TROW', 'AMP', 'BEN', 'IVZ', 'NTRS', 'STT', 'BK', 'DFS', 'SYF', 'COF'
]

# SALUD (Healthcare)
HEALTHCARE_TICKERS = [
    'JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'LLY', 'MRK', 'DHR', 'ABBV', 'AMGN',
    'GILD', 'BMY', 'CVS', 'ELV', 'CI', 'HUM', 'VRTX', 'REGN', 'BIIB', 'ISRG',
    'SYK', 'BDX', 'ZTS', 'EW', 'IDXX', 'DXCM', 'MRNA', 'BNTX', 'VEEV', 'HCA'
]

# CONSUMO DISCRECIONAL (Consumer Cyclical)
CONSUMER_CYCLICAL_TICKERS = [
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'TGT', 'BKNG',
    'MAR', 'YUM', 'CMG', 'ORLY', 'AZO', 'F', 'GM', 'RIVN', 'LCID', 'NIO',
    'DPZ', 'DRI', 'LVS', 'WYNN', 'MGM', 'RCL', 'NCLH', 'CCL', 'EXPE', 'ABNB'
]

# SERVICIOS DE COMUNICACIÓN (Communication Services)
COMMUNICATION_TICKERS = [
    'GOOGL', 'META', 'NFLX', 'DIS', 'T', 'VZ', 'CMCSA', 'CHTR', 'TMUS', 'EA',
    'ATVI', 'TTWO', 'SPOT', 'LYV', 'LGF-A', 'NWSA', 'FOX', 'FOXA', 'IPG', 'OMC'
]

# CONSUMO BÁSICO (Consumer Defensive)
CONSUMER_DEFENSIVE_TICKERS = [
    'PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'KMB', 'MO', 'PM', 'MDLZ',
    'KHC', 'SYY', 'KR', 'TGT', 'DG', 'DLTR', 'CLX', 'HSY', 'CAG', 'GIS',
    'K', 'MKC', 'SJM', 'TAP', 'STZ', 'BF-B', 'MNST', 'EL', 'UL', 'NSRGY'
]

# ENERGÍA (Energy)
ENERGY_TICKERS = [
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PSX', 'MPC', 'VLO', 'OXY', 'PXD',
    'HES', 'DVN', 'FANG', 'MRO', 'APA', 'BKR', 'HAL', 'WMB', 'OKE', 'LNG',
    'KMI', 'TRP', 'ENB', 'EQT', 'CTRA', 'RRC', 'OVV', 'MTDR', 'CHK', 'EQNR'
]

# INDUSTRIALES (Industrials)
INDUSTRIAL_TICKERS = [
    'RTX', 'HON', 'UPS', 'CAT', 'GE', 'BA', 'LMT', 'NOC', 'GD', 'DE',
    'EMR', 'ITW', 'WM', 'FDX', 'CSX', 'UNP', 'NSC', 'CP', 'CNI', 'MMM',
    'ETN', 'CARR', 'IR', 'DOV', 'FAST', 'GWW', 'NDAQ', 'CMI', 'PH', 'TT'
]

# MATERIALES BÁSICOS (Basic Materials)
MATERIALS_TICKERS = [
    'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'DD', 'PPG', 'ALB', 'VMC',
    'MLM', 'NUE', 'STLD', 'CF', 'MOS', 'FMC', 'IFF', 'AVY', 'BALL', 'PKG',
    'WRK', 'IP', 'WLK', 'CE', 'EMN', 'LYB', 'DOW', 'CTVA', 'NTR', 'SMG'
]

# BIENES RAÍCES (Real Estate)
REAL_ESTATE_TICKERS = [
    'AMT', 'PLD', 'EQIX', 'PSA', 'CCI', 'SBAC', 'DLR', 'WELL', 'AVB', 'EQR',
    'O', 'SPG', 'VTR', 'EXR', 'MAA', 'UDR', 'ESS', 'ARE', 'BXP',
    'KIM', 'REG', 'FRT', 'SLG', 'HIW', 'CPT', 'AIV'
]

# SERVICIOS PÚBLICOS (Utilities)
UTILITIES_TICKERS = [
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'WEC', 'PEG',
    'ED', 'ES', 'EIX', 'FE', 'AES', 'AWK', 'CNP', 'LNT', 'DTE', 'CMS',
    'ATO', 'NRG', 'PPL', 'WTRG', 'NI', 'SWX', 'OGS', 'ALE', 'OTTR', 'MGEE'
]

# DICCIONARIOS POR SECTOR (inglés)
SECTOR_TICKERS_EN = {
    'Technology': TECH_TICKERS,
    'Financial Services': FINANCIAL_TICKERS,
    'Healthcare': HEALTHCARE_TICKERS,
    'Consumer Cyclical': CONSUMER_CYCLICAL_TICKERS,
    'Communication Services': COMMUNICATION_TICKERS,
    'Consumer Defensive': CONSUMER_DEFENSIVE_TICKERS,
    'Energy': ENERGY_TICKERS,
    'Industrials': INDUSTRIAL_TICKERS,
    'Basic Materials': MATERIALS_TICKERS,
    'Real Estate': REAL_ESTATE_TICKERS,
    'Utilities': UTILITIES_TICKERS
}

# Mapeo en español
SECTOR_TICKERS_ES = {
    'Tecnología': TECH_TICKERS,
    'Technology': TECH_TICKERS,
    'Financiero': FINANCIAL_TICKERS,
    'Financial Services': FINANCIAL_TICKERS,
    'Salud': HEALTHCARE_TICKERS,
    'Healthcare': HEALTHCARE_TICKERS,
    'Consumo Discrecional': CONSUMER_CYCLICAL_TICKERS,
    'Consumer Cyclical': CONSUMER_CYCLICAL_TICKERS,
    'Consumo': CONSUMER_CYCLICAL_TICKERS,
    'Servicios de Comunicación': COMMUNICATION_TICKERS,
    'Communication Services': COMMUNICATION_TICKERS,
    'Consumo Básico': CONSUMER_DEFENSIVE_TICKERS,
    'Consumer Defensive': CONSUMER_DEFENSIVE_TICKERS,
    'Energía': ENERGY_TICKERS,
    'Energy': ENERGY_TICKERS,
    'Industriales': INDUSTRIAL_TICKERS,
    'Industrials': INDUSTRIAL_TICKERS,
    'Industrial': INDUSTRIAL_TICKERS,
    'Materiales Básicos': MATERIALS_TICKERS,
    'Basic Materials': MATERIALS_TICKERS,
    'Materials': MATERIALS_TICKERS,
    'Bienes Raíces': REAL_ESTATE_TICKERS,
    'Real Estate': REAL_ESTATE_TICKERS,
    'Servicios Públicos': UTILITIES_TICKERS,
    'Utilities': UTILITIES_TICKERS
}


# ============================================================================
# FUNCIONES PARA OBTENER TICKERS
# ============================================================================

def obtener_todos_tickers_sectores():
    """
    Obtiene todos los tickers de todos los sectores (sin duplicados).
    
    Returns:
        set: Conjunto de todos los tickers únicos
    """
    todos_tickers = set()
    for tickers in SECTOR_TICKERS_EN.values():
        todos_tickers.update(tickers)
    return todos_tickers


def obtener_tickers_sector(sector, usar_series_json=True, ruta_json='series_historicas.json'):
    """
    Obtiene la lista de tickers para un sector dado.
    
    Args:
        sector (str): Nombre del sector (en inglés o español)
        usar_series_json (bool): Si True, intenta cargar desde series_historicas.json primero
        ruta_json (str): Ruta al archivo series_historicas.json
    
    Returns:
        list: Lista de tickers del sector, o lista vacía si no se encuentra
    """
    from pathlib import Path
    import json
    
    # Intentar cargar desde series_historicas.json primero
    if usar_series_json:
        try:
            rutas_posibles = [
                Path(ruta_json),
                Path.cwd() / ruta_json,
            ]
            
            datos_json = None
            for ruta in rutas_posibles:
                if ruta.exists():
                    with open(ruta, 'r', encoding='utf-8') as f:
                        datos_json = json.load(f)
                    break
            
            if datos_json and 'sectores' in datos_json:
                sectores_json = datos_json['sectores']
                
                # Buscar el sector en español
                if sector in SECTOR_TICKERS_ES:
                    nombres_sector = [sector]
                    # Agregar alias en inglés si existe
                    for es, en_list in SECTOR_TICKERS_ES.items():
                        if es == sector and en_list == SECTOR_TICKERS_ES.get(sector):
                            for en_name, en_tickers in SECTOR_TICKERS_EN.items():
                                if en_tickers == en_list and en_name not in nombres_sector:
                                    nombres_sector.append(en_name)
                                    break
                            break
                    
                    for nombre in nombres_sector:
                        if nombre in sectores_json:
                            tickers_disponibles = sectores_json[nombre]
                            if tickers_disponibles:
                                return tickers_disponibles
                
                # Buscar directamente en el JSON
                if sector in sectores_json:
                    tickers_disponibles = sectores_json[sector]
                    if tickers_disponibles:
                        return tickers_disponibles
        except Exception:
            pass
    
    # Método normal: buscar en mapeo
    if sector in SECTOR_TICKERS_ES:
        return SECTOR_TICKERS_ES[sector]
    if sector in SECTOR_TICKERS_EN:
        return SECTOR_TICKERS_EN[sector]
    
    return []


def obtener_tickers_por_lotes(tickers, tamano_lote=50):
    """
    Divide una lista de tickers en lotes de tamaño especificado.
    
    Args:
        tickers (list): Lista de tickers a dividir
        tamano_lote (int): Tamaño de cada lote (default: 50)
    
    Returns:
        generator: Generador que produce listas de tickers en lotes
    """
    for i in range(0, len(tickers), tamano_lote):
        yield tickers[i:i + tamano_lote]


def obtener_todos_los_tickers():
    """
    Obtiene todos los tickers disponibles incluyendo ETFs principales.
    
    Returns:
        list: Lista completa de tickers únicos
    """
    tickers_base = list(obtener_todos_tickers_sectores())
    
    # Agregar ETFs principales si no están incluidos
    etfs_principales = ['SPY', 'QQQ', 'IWM', 'VTI', 'VXUS', 'BND', 'GLD', 'SLV']
    todos = set(tickers_base)
    todos.update(etfs_principales)
    
    return sorted(list(todos))


# ============================================================================
# ETFs SECTORIALES
# ============================================================================

SECTOR_ETF_MAPPING = {
    'Technology': 'XLK',
    'Financial Services': 'XLF',
    'Healthcare': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Communication Services': 'XLC',
    'Consumer Defensive': 'XLP',
    'Energy': 'XLE',
    'Industrials': 'XLI',
    'Basic Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
}


def obtener_etf_sectorial(sector):
    """
    Obtiene el ETF sectorial principal para un sector dado.
    
    Args:
        sector (str): Nombre del sector
    
    Returns:
        str: Símbolo del ETF sectorial o None
    """
    return SECTOR_ETF_MAPPING.get(sector)
