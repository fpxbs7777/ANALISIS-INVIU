"""
Análisis comparativo de portafolios SPY/QQQ y portafolios alternativos
usando métricas históricas y simulaciones de Markowitz.

Reutiliza:
- Sistema de descarga/caché de precios: descargar_series_activos_factores.descargar_series_tickers
- Métricas de regresión (alpha, beta, correlación, R²): calcular_metricas_tickers_factores.calcular_metricas_regresion
- Factores de diversificación históricos para SPY/QQQ: config_tickers_factores.*

Portafolios analizados:
- Portafolio 1: SPY + QQQ
- Portafolio 2: Portafolio de alta correlación y alto R² (índices/ETFs muy similares)
- Portafolio 3: Portafolio de baja correlación y bajo R² (factores de diversificación)

Para cada portafolio:
- Calcula retorno y volatilidad esperados (anualizados)
- Simula 1500 combinaciones de pesos (Markowitz) y obtiene:
  - Portafolio de máxima Sharpe
  - Portafolio de mínima volatilidad
- Muestra la ganancia/pérdida esperada para un monto de inversión dado
- Muestra métricas comparativas por activo dentro de cada portafolio
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import random
from scipy.optimize import minimize
from scipy.stats import skew, kurtosis
import matplotlib.pyplot as plt

# ============================================================================
# CONFIGURACIÓN INDEPENDIENTE - TODOS LOS DATOS Y FUNCIONES INCLUIDAS
# ============================================================================

# Importaciones estándar necesarias
import json
import yfinance as yf
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIONES COMPLETAS DE TICKERS Y FACTORES (INTEGRADAS)
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

# BOLSA DE BUENOS AIRES (BCBA) - Tickers Argentinos
BCBA_TICKERS = [
    # Financial Services
    'GGAL.BA', 'BMA.BA', 'BBAR.BA', 'BYMA.BA', 'SUPV.BA', 'BHIP.BA',
    # Energy
    'YPFD.BA', 'PAMP.BA', 'TGNO4.BA', 'TGSU2.BA', 'CAPX.BA',
    # Utilities
    'CEPU.BA', 'TRAN.BA', 'METR.BA', 'DGCU2.BA',
    # Basic Materials
    'ALUA.BA', 'TXAR.BA', 'LOMA.BA', 'HARG.BA', 'CARC.BA',
    # Industrials
    'AGRO.BA', 'AUSO.BA', 'CADO.BA', 'CRES.BA', 'OEST.BA', 'POLL.BA', 'GARO.BA', 'COME.BA',
    # Consumer Cyclical
    'PATA.BA', 'LONG.BA', 'FIPL.BA', 'HAVA.BA',
    # Consumer Defensive
    'MOLI.BA', 'SAMI.BA', 'SEMI.BA',
    # Communication Services
    'TECO2.BA', 'CVH.BA', 'GCLA.BA',
    # Healthcare
    'RICH.BA',
    # Technology
    'BOLT.BA',
    # Real Estate
    'IRCP.BA',
]

# DICCIONARIOS POR SECTOR (para compatibilidad con código existente)
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

# Mapeo en español (para compatibilidad con código existente)
SECTOR_TICKERS_ES = {
    'Tecnología': TECH_TICKERS,
    'Technology': TECH_TICKERS,  # Alias
    'Financiero': FINANCIAL_TICKERS,
    'Financial Services': FINANCIAL_TICKERS,  # Alias
    'Salud': HEALTHCARE_TICKERS,
    'Healthcare': HEALTHCARE_TICKERS,  # Alias
    'Consumo Discrecional': CONSUMER_CYCLICAL_TICKERS,
    'Consumer Cyclical': CONSUMER_CYCLICAL_TICKERS,  # Alias
    'Consumo': CONSUMER_CYCLICAL_TICKERS,  # Alias común
    'Servicios de Comunicación': COMMUNICATION_TICKERS,
    'Communication Services': COMMUNICATION_TICKERS,  # Alias
    'Consumo Básico': CONSUMER_DEFENSIVE_TICKERS,
    'Consumer Defensive': CONSUMER_DEFENSIVE_TICKERS,  # Alias
    'Energía': ENERGY_TICKERS,
    'Energy': ENERGY_TICKERS,  # Alias
    'Industriales': INDUSTRIAL_TICKERS,
    'Industrials': INDUSTRIAL_TICKERS,  # Alias
    'Industrial': INDUSTRIAL_TICKERS,  # Alias
    'Materiales Básicos': MATERIALS_TICKERS,
    'Basic Materials': MATERIALS_TICKERS,  # Alias
    'Materials': MATERIALS_TICKERS,  # Alias
    'Bienes Raíces': REAL_ESTATE_TICKERS,
    'Real Estate': REAL_ESTATE_TICKERS,  # Alias
    'Servicios Públicos': UTILITIES_TICKERS,
    'Utilities': UTILITIES_TICKERS  # Alias
}

# Función helper para obtener tickers por sector (soporta inglés y español)
def obtener_tickers_sector(sector, usar_series_json=True, ruta_json='series_historicas.json'):
    """
    Obtiene la lista de tickers para un sector dado.
    
    Prioriza cargar desde series_historicas.json (más rápido) si está disponible,
    de lo contrario usa las configuraciones internas.
    
    Args:
        sector (str): Nombre del sector (en inglés o español)
        usar_series_json (bool): Si True, intenta cargar desde series_historicas.json primero
        ruta_json (str): Ruta al archivo series_historicas.json
    
    Returns:
        list: Lista de tickers del sector, o lista vacía si no se encuentra
    """
    # Intentar cargar desde series_historicas.json primero (más rápido)
    if usar_series_json:
        try:
            # Buscar el archivo en varias ubicaciones posibles
            rutas_posibles = [
                Path(ruta_json),
                Path(__file__).parent / ruta_json if '__file__' in globals() else Path(ruta_json),
                Path.cwd() / ruta_json,
            ]
            
            datos_json = None
            for ruta in rutas_posibles:
                if ruta.exists():
                    with open(ruta, 'r', encoding='utf-8') as f:
                        datos_json = json.load(f)
                    break
            
            if datos_json and 'sectores' in datos_json:
                # Buscar el sector en el JSON (soporta múltiples nombres)
                sectores_json = datos_json['sectores']
                
                # Intentar encontrar el sector con diferentes nombres
                nombres_sector = [
                    sector,
                    sector.replace(' ', ''),
                    sector.upper(),
                    sector.lower(),
                    sector.title(),
                ]
                
                # También buscar en los mapeos para encontrar el nombre correcto
                if sector in SECTOR_TICKERS_ES:
                    # Si el sector está en el mapeo, buscar todos sus posibles nombres
                    for nombre_sector in SECTOR_TICKERS_ES.keys():
                        if nombre_sector in sectores_json:
                            tickers_disponibles = sectores_json[nombre_sector]
                            if tickers_disponibles:
                                return tickers_disponibles
                
                # Buscar directamente en el JSON
                for nombre in nombres_sector:
                    if nombre in sectores_json:
                        tickers_disponibles = sectores_json[nombre]
                        if tickers_disponibles:
                            return tickers_disponibles
                
                # Si no se encontró en sectores, buscar en la lista completa de activos
                # y filtrar por los tickers del sector desde config
                if 'activos' in datos_json and 'lista' in datos_json['activos']:
                    tickers_config = obtener_tickers_sector(sector, usar_series_json=False)
                    if tickers_config:
                        activos_disponibles = set(datos_json['activos']['lista'])
                        tickers_filtrados = [t for t in tickers_config if t in activos_disponibles]
                        if tickers_filtrados:
                            return tickers_filtrados
        except Exception as e:
            # Si hay error cargando JSON, continuar con método normal
            pass
    
    # Método normal: buscar en mapeo en español primero
    if sector in SECTOR_TICKERS_ES:
        return SECTOR_TICKERS_ES[sector]
    # Buscar en mapeo en inglés
    if sector in SECTOR_TICKERS_EN:
        return SECTOR_TICKERS_EN[sector]
    # Retornar lista vacía si no se encuentra
    return []

# Función para obtener todos los tickers de sectores
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

# ETFs POR SECTOR PARA COMPARACIÓN
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
    # Aliases en español
    'Tecnología': 'XLK',
    'Financiero': 'XLF',
    'Salud': 'XLV',
    'Consumo Discrecional': 'XLY',
    'Consumo': 'XLY',  # Alias común
    'Servicios de Comunicación': 'XLC',
    'Consumo Básico': 'XLP',
    'Energía': 'XLE',
    'Industriales': 'XLI',
    'Industrial': 'XLI',  # Alias
    'Materiales Básicos': 'XLB',
    'Materials': 'XLB',  # Alias
    'Bienes Raíces': 'XLRE',
    'Real Estate': 'XLRE',
    'Servicios Públicos': 'XLU'
}

# Factores de diversificación para análisis
FACTORES_DIVERSIFICACION = {
    # ETFs de factores (baja correlación con índices amplios)
    'MTUM': 'Factor Momentum',
    'QUAL': 'Factor Calidad',
    'VLUE': 'Factor Valor',
    'USMV': 'Factor Mínima Volatilidad',
    'SIZE': 'Factor Tamaño Pequeño',
    # ETFs sectoriales defensivos (baja correlación con tech)
    'XLP': 'Sector Consumo Básico',
    'XLV': 'Sector Salud',
    'XLU': 'Sector Servicios Públicos',
    'XLRE': 'Sector Inmobiliario',
    # ETFs sectoriales cíclicos (diversificación sectorial)
    'XLE': 'Sector Energía',
    'XLB': 'Sector Materiales',
    'XLI': 'Sector Industrial',
    'XLF': 'Sector Financiero',
}

# Funciones placeholder para factores óptimos
def obtener_factores_optimos_spy(periodo='5y', top_n=10):
    """Retorna factores básicos de diversificación"""
    return list(FACTORES_DIVERSIFICACION.keys())[:top_n]

def obtener_factores_optimos_qqq(periodo='5y', top_n=10):
    """Retorna factores básicos de diversificación"""
    return list(FACTORES_DIVERSIFICACION.keys())[:top_n]

# ============================================================================
# FUNCIONES DE CACHÉ DE MONEDAS (INTEGRADAS)
# ============================================================================

def cargar_monedas_cache(directorio_cache='datos_series', archivo_json='series_historicas.json'):
    """
    Carga las monedas detectadas desde el caché (JSON).
    
    Args:
        directorio_cache (str): Directorio donde buscar el caché
        archivo_json (str): Nombre del archivo JSON con las series
    
    Returns:
        dict: Diccionario {ticker: moneda} o {} si no existe
    """
    cache_dir = Path(directorio_cache)
    json_file = cache_dir / archivo_json
    
    if not json_file.exists():
        return {}
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        # Buscar monedas en el JSON
        monedas = datos.get('monedas', {})
        return monedas
    except Exception as e:
        # Silencioso, retornar diccionario vacío
        return {}

def guardar_monedas_cache(monedas_tickers, directorio_cache='datos_series', 
                          archivo_cache='monedas_cache.json'):
    """
    Guarda las monedas detectadas en un archivo de caché separado.
    
    Args:
        monedas_tickers (dict): Diccionario {ticker: moneda}
        directorio_cache (str): Directorio donde guardar el caché
        archivo_cache (str): Nombre del archivo de caché
    """
    cache_dir = Path(directorio_cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / archivo_cache
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(monedas_tickers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Silencioso, no imprimir error
        pass

# ============================================================================
# FUNCIONES DE SECTOR E INDUSTRIA (INTEGRADAS)
# ============================================================================

def obtener_sector_industria_ticker(ticker: str) -> dict:
    """
    Obtiene el sector e industria de un ticker desde yfinance API.
    
    Args:
        ticker (str): Ticker a consultar
    
    Returns:
        dict: {'sector': str o None, 'industry': str o None}
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        sector = info.get('sector')
        industry = info.get('industry')
        
        # Normalizar valores None o vacíos
        sector = sector if sector and str(sector).strip() else None
        industry = industry if industry and str(industry).strip() else None
        
        return {
            'sector': sector,
            'industry': industry
        }
    except Exception as e:
        # Si hay error, retornar None para ambos
        return {
            'sector': None,
            'industry': None
        }

def cargar_sectores_industrias_cache(directorio_cache='datos_series', archivo_json='series_historicas.json'):
    """
    Carga los sectores e industrias detectados desde el caché (JSON).
    
    Args:
        directorio_cache (str): Directorio donde buscar el caché
        archivo_json (str): Nombre del archivo JSON con las series
    
    Returns:
        dict: Diccionario {ticker: {'sector': str, 'industry': str}} o {} si no existe
    """
    cache_dir = Path(directorio_cache)
    json_file = cache_dir / archivo_json
    
    if not json_file.exists():
        return {}
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        # Buscar sectores_industrias en el JSON
        sectores_industrias = datos.get('sectores_industrias', {})
        return sectores_industrias
    except Exception as e:
        # Silencioso, retornar diccionario vacío
        return {}

def guardar_sectores_industrias_cache(sectores_industrias_tickers, directorio_cache='datos_series', 
                                       archivo_cache='sectores_industrias_cache.json'):
    """
    Guarda los sectores e industrias detectados en un archivo de caché separado.
    
    Args:
        sectores_industrias_tickers (dict): Diccionario {ticker: {'sector': str, 'industry': str}}
        directorio_cache (str): Directorio donde guardar el caché
        archivo_cache (str): Nombre del archivo de caché
    """
    cache_dir = Path(directorio_cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / archivo_cache
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(sectores_industrias_tickers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Silencioso, no imprimir error
        pass

def obtener_sectores_industrias_batch(tickers: List[str], usar_cache: bool = True, 
                                      ruta_json: str = 'series_historicas.json') -> dict:
    """
    Obtiene sectores e industrias para múltiples tickers, usando caché cuando es posible.
    
    Args:
        tickers (List[str]): Lista de tickers a consultar
        usar_cache (bool): Si True, carga desde caché y solo consulta los faltantes
        ruta_json (str): Ruta al archivo JSON principal
    
    Returns:
        dict: {ticker: {'sector': str, 'industry': str}}
    """
    resultado = {}
    
    # Cargar desde caché si está habilitado
    if usar_cache:
        json_path = Path(ruta_json)
        directorio_json = json_path.parent if json_path.exists() else Path('.')
        
        # Intentar cargar desde JSON principal
        resultado = cargar_sectores_industrias_cache(str(directorio_json), json_path.name)
        
        # Si no está en JSON principal, intentar archivo de caché separado
        if not resultado:
            resultado = cargar_sectores_industrias_cache(str(directorio_json), 'sectores_industrias_cache.json')
    
    # Identificar tickers faltantes
    tickers_faltantes = [t for t in tickers if t not in resultado or 
                        resultado.get(t, {}).get('sector') is None and resultado.get(t, {}).get('industry') is None]
    
    if tickers_faltantes:
        print(f"   🔍 Obteniendo sector e industria para {len(tickers_faltantes)} tickers desde API...")
        
        for i, ticker in enumerate(tickers_faltantes, 1):
            if i % 10 == 0:
                print(f"      Procesando {i}/{len(tickers_faltantes)}...")
            
            datos = obtener_sector_industria_ticker(ticker)
            resultado[ticker] = datos
            
            # Pequeño delay para evitar rate limiting
            if i < len(tickers_faltantes):
                time.sleep(0.1)
        
        # Guardar en caché
        if usar_cache:
            json_path = Path(ruta_json)
            directorio_json = json_path.parent if json_path.exists() else Path('.')
            guardar_sectores_industrias_cache(resultado, str(directorio_json), 'sectores_industrias_cache.json')
            print(f"   ✅ Sectores e industrias guardados en caché")
    
    return resultado

def filtrar_tickers_por_sector(tickers: List[str], sector: str, 
                               ruta_json: str = 'series_historicas.json') -> List[str]:
    """
    Filtra tickers por sector específico.
    
    Args:
        tickers (List[str]): Lista de tickers a filtrar
        sector (str): Nombre del sector (case-insensitive)
        ruta_json (str): Ruta al archivo JSON con datos
    
    Returns:
        List[str]: Lista de tickers que pertenecen al sector
    """
    sectores_industrias = obtener_sectores_industrias_batch(tickers, usar_cache=True, ruta_json=ruta_json)
    
    sector_lower = sector.lower().strip()
    tickers_filtrados = []
    
    for ticker in tickers:
        datos = sectores_industrias.get(ticker, {})
        sector_ticker = datos.get('sector', '')
        
        if sector_ticker and sector_ticker.lower().strip() == sector_lower:
            tickers_filtrados.append(ticker)
    
    return tickers_filtrados

def filtrar_tickers_por_industria(tickers: List[str], industry: str, 
                                  ruta_json: str = 'series_historicas.json') -> List[str]:
    """
    Filtra tickers por industria específica.
    
    Args:
        tickers (List[str]): Lista de tickers a filtrar
        industry (str): Nombre de la industria (case-insensitive, puede ser parcial)
        ruta_json (str): Ruta al archivo JSON con datos
    
    Returns:
        List[str]: Lista de tickers que pertenecen a la industria
    """
    sectores_industrias = obtener_sectores_industrias_batch(tickers, usar_cache=True, ruta_json=ruta_json)
    
    industry_lower = industry.lower().strip()
    tickers_filtrados = []
    
    for ticker in tickers:
        datos = sectores_industrias.get(ticker, {})
        industry_ticker = datos.get('industry', '')
        
        if industry_ticker and industry_lower in industry_ticker.lower():
            tickers_filtrados.append(ticker)
    
    return tickers_filtrados

def obtener_sectores_disponibles(tickers: List[str] = None, 
                                 ruta_json: str = 'series_historicas.json') -> List[str]:
    """
    Obtiene lista de todos los sectores únicos disponibles.
    
    Args:
        tickers (List[str], optional): Lista de tickers a analizar. Si None, usa todos del JSON
        ruta_json (str): Ruta al archivo JSON con datos
    
    Returns:
        List[str]: Lista de sectores únicos (ordenados)
    """
    if tickers is None:
        # Cargar todos los tickers desde JSON
        try:
            json_path = Path(ruta_json)
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                if 'activos' in datos and 'lista' in datos['activos']:
                    tickers = datos['activos']['lista']
                else:
                    return []
            else:
                return []
        except:
            return []
    
    sectores_industrias = obtener_sectores_industrias_batch(tickers, usar_cache=True, ruta_json=ruta_json)
    
    sectores = set()
    for datos in sectores_industrias.values():
        sector = datos.get('sector')
        if sector:
            sectores.add(sector)
    
    return sorted(list(sectores))

def obtener_industrias_disponibles(tickers: List[str] = None, 
                                   ruta_json: str = 'series_historicas.json') -> List[str]:
    """
    Obtiene lista de todas las industrias únicas disponibles.
    
    Args:
        tickers (List[str], optional): Lista de tickers a analizar. Si None, usa todos del JSON
        ruta_json (str): Ruta al archivo JSON con datos
    
    Returns:
        List[str]: Lista de industrias únicas (ordenadas)
    """
    if tickers is None:
        # Cargar todos los tickers desde JSON
        try:
            json_path = Path(ruta_json)
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                if 'activos' in datos and 'lista' in datos['activos']:
                    tickers = datos['activos']['lista']
                else:
                    return []
            else:
                return []
        except:
            return []
    
    sectores_industrias = obtener_sectores_industrias_batch(tickers, usar_cache=True, ruta_json=ruta_json)
    
    industrias = set()
    for datos in sectores_industrias.values():
        industry = datos.get('industry')
        if industry:
            industrias.add(industry)
    
    return sorted(list(industrias))

# Función simplificada para calcular métricas de regresión (placeholder básico)
def calcular_metricas_regresion(ticker, benchmark_ticker, returns_df):
    """Versión simplificada de cálculo de métricas de regresión"""
    if ticker not in returns_df.columns or benchmark_ticker not in returns_df.columns:
        return None
    
    ticker_returns = returns_df[ticker].dropna()
    benchmark_returns = returns_df[benchmark_ticker].dropna()
    
    # Alinear series
    common_idx = ticker_returns.index.intersection(benchmark_returns.index)
    if len(common_idx) < 10:
        return None
    
    ticker_aligned = ticker_returns.loc[common_idx]
    benchmark_aligned = benchmark_returns.loc[common_idx]
    
    # Calcular correlación básica
    correlation = ticker_aligned.corr(benchmark_aligned)
    
    return {
        'correlacion': correlation if not pd.isna(correlation) else 0.0,
        'beta': correlation,  # Simplificado
        'alpha': 0.0,  # Simplificado
        'r_cuadrado': correlation ** 2 if not pd.isna(correlation) else 0.0,
    }

# Cantidad objetivo de activos por portafolio para poder compararlos de forma homogénea
NUM_ACTIVOS_PORTAFOLIO = 30  # Versión con 30 activos
NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO = 60  # Versión extendida con 60 activos

# Mínimo de activos que debe tener un portafolio "especial" (alta correlación / correlación negativa)
MIN_ACTIVOS_CORRELACION = 5


@dataclass
class PortfolioSummary:
    nombre: str
    tickers: List[str]
    returns_df: pd.DataFrame  # retornos diarios
    mean_return_annual: float
    volatility_annual: float
    sharpe_ratio: float
    weights: Dict[str, float]
    skewness: float = 0.0  # Sesgo del portafolio (opcional)
    kurtosis: float = 0.0  # Curtosis del portafolio (opcional)


def simular_retorno_futuro(mean_return_annual, vol_annual, dias=252):
    """
    Simula un retorno futuro usando random walk lognormal.
    
    Args:
        mean_return_annual: Retorno promedio anual
        vol_annual: Volatilidad anual
        dias: Número de días de trading (default 252)
    
    Returns:
        Retorno acumulado simulado (ej: 0.15 = 15%)
    """
    dt = 1 / dias
    drift = (mean_return_annual - (vol_annual**2)/2) * dt
    shock = vol_annual * np.sqrt(dt) * np.random.normal(size=dias)
    return np.exp(drift + shock).prod() - 1


def calcular_retornos_portafolio_historico(summary):
    """
    Calcula los retornos históricos reales del portafolio usando los pesos y retornos diarios.
    
    Args:
        summary: PortfolioSummary con returns_df y weights
    
    Returns:
        pd.Series: Retornos diarios históricos del portafolio
    """
    if summary.returns_df.empty:
        return pd.Series(dtype=float)
    
    # Obtener pesos como array en el mismo orden que las columnas
    weights_array = np.array([summary.weights.get(ticker, 0.0) 
                              for ticker in summary.returns_df.columns 
                              if ticker in summary.weights])
    
    # Filtrar columnas que están en los pesos
    tickers_validos = [t for t in summary.returns_df.columns if t in summary.weights]
    if not tickers_validos:
        return pd.Series(dtype=float)
    
    sub_returns = summary.returns_df[tickers_validos]
    weights_array = np.array([summary.weights[t] for t in tickers_validos])
    
    # Normalizar pesos por si acaso
    weights_array = weights_array / weights_array.sum()
    
    # Calcular retorno diario del portafolio
    port_daily = (sub_returns * weights_array).sum(axis=1)
    
    return port_daily.dropna()


def simular_retorno_futuro_empirico(retornos_historicos, dias=252):
    """
    Simula un retorno futuro usando bootstrapping de retornos históricos reales.
    
    Args:
        retornos_historicos: pd.Series con retornos diarios históricos del portafolio
        dias: Número de días de trading a simular (default 252 = 1 año)
    
    Returns:
        Retorno acumulado simulado (ej: 0.15 = 15%)
    """
    if len(retornos_historicos) == 0:
        return 0.0
    
    # Bootstrapping: muestrear días aleatoriamente con reemplazo
    indices_muestra = np.random.choice(len(retornos_historicos), size=dias, replace=True)
    retornos_muestra = retornos_historicos.iloc[indices_muestra]
    
    # Calcular retorno acumulado: (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
    retorno_acumulado = (1 + retornos_muestra).prod() - 1
    
    return retorno_acumulado


def simular_ganancias_portafolio_combinado(summary, returns_df, capital=10000, n=5000, optimizar_pesos=True, metodo='empirico'):
    """
    Simula ganancias del portafolio combinando:
    1. Simulación de pesos optimizados (variaciones de Markowitz)
    2. Trayectorias empíricas de retornos (bootstrapping)
    
    En cada simulación:
    - Genera pesos optimizados (o variaciones de pesos)
    - Simula trayectorias empíricas de retornos
    - Combina ambos para calcular ganancias finales
    
    Args:
        summary: PortfolioSummary con mean_return_annual, volatility_annual, returns_df y weights
        returns_df: DataFrame con retornos históricos de todos los activos
        capital: Capital inicial a invertir
        n: Número de simulaciones
        optimizar_pesos: Si True, varía los pesos en cada simulación. Si False, usa pesos fijos.
        metodo: 'empirico' (bootstrapping) o 'parametrico' (random walk)
    
    Returns:
        Array de ganancias simuladas
    """
    if returns_df.empty or summary.returns_df.empty:
        # Fallback a método simple si no hay datos
        mean_r = summary.mean_return_annual
        vol_r = summary.volatility_annual
        retornos = [simular_retorno_futuro(mean_r, vol_r) for _ in range(n)]
        return capital * np.array(retornos)
    
    # Obtener tickers válidos
    tickers_validos = [t for t in summary.tickers if t in returns_df.columns]
    if len(tickers_validos) < 2:
        # Fallback si no hay suficientes tickers
        mean_r = summary.mean_return_annual
        vol_r = summary.volatility_annual
        retornos = [simular_retorno_futuro(mean_r, vol_r) for _ in range(n)]
        return capital * np.array(retornos)
    
    # Retornos históricos de los activos individuales
    returns_subset = returns_df[tickers_validos].dropna()
    
    if len(returns_subset) < 20:
        # Fallback si no hay suficientes datos
        mean_r = summary.mean_return_annual
        vol_r = summary.volatility_annual
        retornos = [simular_retorno_futuro(mean_r, vol_r) for _ in range(n)]
        return capital * np.array(retornos)
    
    ganancias = []
    np.random.seed(42)  # Para reproducibilidad
    
    for i in range(n):
        # 1. SIMULACIÓN DE PESOS (si optimizar_pesos=True)
        if optimizar_pesos:
            # Generar pesos aleatorios normalizados (simulando variaciones de optimización)
            weights_sim = np.random.random(len(tickers_validos))
            weights_sim = weights_sim / weights_sim.sum()
        else:
            # Usar pesos fijos del summary
            weights_sim = np.array([summary.weights.get(t, 0.0) for t in tickers_validos])
            if weights_sim.sum() > 0:
                weights_sim = weights_sim / weights_sim.sum()
            else:
                weights_sim = np.array([1.0 / len(tickers_validos)] * len(tickers_validos))
        
        # 2. SIMULACIÓN DE TRAYECTORIAS EMPÍRICAS
        if metodo == 'empirico':
            # Bootstrapping: muestrear días aleatoriamente con reemplazo
            dias = 252  # 1 año
            indices_muestra = np.random.choice(len(returns_subset), size=dias, replace=True)
            retornos_muestra = returns_subset.iloc[indices_muestra]
            
            # Calcular retorno del portafolio para cada día usando los pesos simulados
            retornos_portafolio_diarios = (retornos_muestra * weights_sim).sum(axis=1)
            
            # Calcular retorno acumulado: (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
            retorno_acumulado = (1 + retornos_portafolio_diarios).prod() - 1
            
        else:  # metodo == 'parametrico'
            # Calcular retorno y volatilidad del portafolio con pesos simulados
            mean_returns_annual = returns_subset.mean() * 252
            cov_matrix_annual = returns_subset.cov() * 252
            
            port_return_annual = np.sum(mean_returns_annual * weights_sim)
            port_vol_annual = np.sqrt(np.dot(weights_sim.T, np.dot(cov_matrix_annual, weights_sim)))
            
            # Simular retorno futuro usando random walk
            retorno_acumulado = simular_retorno_futuro(port_return_annual, port_vol_annual)
        
        # 3. CALCULAR GANANCIA
        ganancia = capital * retorno_acumulado
        ganancias.append(ganancia)
    
    return np.array(ganancias)


def simular_ganancias_portafolio(summary, capital=10000, n=5000, metodo='empirico'):
    """
    Simula ganancias del portafolio usando Monte Carlo.
    NOTA: Esta función usa pesos fijos. Para combinar optimización de pesos + trayectorias,
    usar simular_ganancias_portafolio_combinado().
    
    Args:
        summary: PortfolioSummary con mean_return_annual, volatility_annual, returns_df y weights
        capital: Capital inicial a invertir
        n: Número de simulaciones
        metodo: 'empirico' (bootstrapping de retornos históricos) o 'parametrico' (random walk lognormal)
    
    Returns:
        Array de ganancias simuladas
    """
    if metodo == 'empirico':
        # Método empírico: usar retornos históricos reales del portafolio
        retornos_historicos = calcular_retornos_portafolio_historico(summary)
        
        if len(retornos_historicos) < 20:
            # Si no hay suficientes datos históricos, usar método paramétrico
            print(f"   Advertencia: pocos datos históricos ({len(retornos_historicos)}), usando método paramétrico")
            metodo = 'parametrico'
        else:
            retornos = [simular_retorno_futuro_empirico(retornos_historicos) for _ in range(n)]
            ganancias = capital * np.array(retornos)
            return ganancias
    
    # Método paramétrico: random walk lognormal
    if metodo == 'parametrico':
        mean_r = summary.mean_return_annual
        vol_r = summary.volatility_annual
        
        retornos = [simular_retorno_futuro(mean_r, vol_r) for _ in range(n)]
        ganancias = capital * np.array(retornos)
        return ganancias
    
    else:
        raise ValueError(f"Método '{metodo}' no válido. Use 'empirico' o 'parametrico'")


def obtener_metricas_ganancia_real(summary, capital=10000, n=5000, metodo='empirico', returns_df=None, usar_combinado=True):
    """
    Obtiene métricas de ganancia real usando simulación Monte Carlo.
    
    Calcula:
    - Ganancia media (esperada)
    - Ganancia mediana (típica)
    - Ganancia moda (más probable)
    - Probabilidad de ganar/perder
    - Intervalo de confianza 95%
    - Percentiles (5%, 25%, 75%, 95%)
    - VaR y CVaR (Value at Risk y Conditional Value at Risk)
    
    Args:
        summary: PortfolioSummary con mean_return_annual, volatility_annual, returns_df y weights
        capital: Capital inicial a invertir
        n: Número de simulaciones
        metodo: 'empirico' (bootstrapping de retornos históricos) o 'parametrico' (random walk lognormal)
                Por defecto usa 'empirico' para capturar la distribución real del portafolio
        returns_df: DataFrame con retornos históricos de todos los activos (requerido si usar_combinado=True)
        usar_combinado: Si True, combina simulación de pesos + trayectorias empíricas. Si False, usa pesos fijos.
    
    Returns:
        Dict con métricas de ganancia
    """
    if usar_combinado and returns_df is not None:
        # Usar simulación combinada: pesos optimizados + trayectorias empíricas
        g = simular_ganancias_portafolio_combinado(summary, returns_df, capital, n, optimizar_pesos=True, metodo=metodo)
    else:
        # Usar simulación tradicional: pesos fijos + trayectorias
        g = simular_ganancias_portafolio(summary, capital, n, metodo=metodo)
    
    media = g.mean()
    mediana = np.median(g)
    std = g.std()
    
    # Calcular moda usando histograma
    hist, bins = np.histogram(g, bins=50)
    idx_moda = np.argmax(hist)
    moda = 0.5 * (bins[idx_moda] + bins[idx_moda+1])
    
    p_ganar = (g > 0).mean()
    p_perder = (g < 0).mean()
    
    # Intervalo de confianza 95% (similar al código de opciones)
    intervalo_confianza_95 = media + np.array([-1.0, 1.0]) * 1.96 * std / np.sqrt(n)
    
    # Percentiles para análisis de riesgo (sobre P&L)
    percentil_1 = np.percentile(g, 1)
    percentil_5 = np.percentile(g, 5)
    percentil_10 = np.percentile(g, 10)
    percentil_25 = np.percentile(g, 25)
    percentil_75 = np.percentile(g, 75)
    percentil_90 = np.percentile(g, 90)
    percentil_95 = np.percentile(g, 95)
    
    # VaR y CVaR (Value at Risk / Conditional VaR) para distintos niveles
    var_1 = percentil_1
    var_5 = percentil_5
    var_10 = percentil_10
    
    cvar_1 = g[g <= var_1].mean() if len(g[g <= var_1]) > 0 else var_1
    cvar_5 = g[g <= var_5].mean() if len(g[g <= var_5]) > 0 else var_5
    cvar_10 = g[g <= var_10].mean() if len(g[g <= var_10]) > 0 else var_10
    
    # Probabilidad de "ruina" (pérdida mayor o igual a -50% del capital)
    umbral_ruina = -0.5 * capital
    prob_ruina = (g <= umbral_ruina).mean()
    
    # Sortino Ratio simulado (usando retornos simulados a partir de P&L)
    retornos_sim = g / capital
    retornos_neg = retornos_sim[retornos_sim < 0]
    if len(retornos_neg) > 0:
        downside_dev = np.sqrt((retornos_neg**2).mean())
        sortino_sim = retornos_sim.mean() / downside_dev if downside_dev > 0 else 0.0
    else:
        sortino_sim = 0.0
    
    return {
        "ganancia_media": media,
        "ganancia_mediana": mediana,
        "ganancia_moda": moda,
        "ganancia_std": std,
        "prob_ganar": p_ganar,
        "prob_perder": p_perder,
        "intervalo_confianza_95": intervalo_confianza_95,
        "percentil_1": percentil_1,
        "percentil_5": percentil_5,
        "percentil_10": percentil_10,
        "percentil_25": percentil_25,
        "percentil_75": percentil_75,
        "percentil_90": percentil_90,
        "percentil_95": percentil_95,
        "var_1": var_1,
        "var_5": var_5,    # Value at Risk al 5%
        "var_10": var_10,
        "cvar_1": cvar_1,
        "cvar_5": cvar_5,  # Conditional VaR al 5%
        "cvar_10": cvar_10,
        "prob_ruina": prob_ruina,
        "sortino_sim": sortino_sim,
        "ganancias_simuladas": g,  # Para análisis adicional si se necesita
        "metodo_usado": metodo  # Indica qué método se usó
    }


def plot_histograma_ganancias(metricas_ganancia, nombre_portafolio="Portafolio", capital=10000, bins=100):
    """
    Plotea histograma de ganancias simuladas (similar al código de opciones).
    
    Args:
        metricas_ganancia: Dict retornado por obtener_metricas_ganancia_real
        nombre_portafolio: Nombre del portafolio para el título
        capital: Capital inicial (para mostrar en el título)
        bins: Número de bins para el histograma
    """
    g = metricas_ganancia["ganancias_simuladas"]
    
    plt.figure(figsize=(10, 6))
    plt.hist(g, bins=bins, edgecolor='black', alpha=0.7)
    plt.axvline(metricas_ganancia["ganancia_media"], color='red', linestyle='--', 
                linewidth=2, label=f'Media: USD {metricas_ganancia["ganancia_media"]:,.0f}')
    plt.axvline(metricas_ganancia["ganancia_mediana"], color='green', linestyle='--', 
                linewidth=2, label=f'Mediana: USD {metricas_ganancia["ganancia_mediana"]:,.0f}')
    plt.axvline(metricas_ganancia["ganancia_moda"], color='orange', linestyle='--', 
                linewidth=2, label=f'Moda: USD {metricas_ganancia["ganancia_moda"]:,.0f}')
    plt.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5, label='Cero ganancia')
    
    # Mostrar intervalo de confianza
    ic = metricas_ganancia["intervalo_confianza_95"]
    plt.axvspan(ic[0], ic[1], alpha=0.2, color='blue', label='IC 95%')
    
    plt.xlabel('Ganancia/Pérdida (USD)', fontsize=12)
    plt.ylabel('Frecuencia', fontsize=12)
    plt.title(f'Monte Carlo Simulations | {nombre_portafolio} | Capital: USD {capital:,.0f}', fontsize=14)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def descargar_precios_activos(tickers: List[str], periodo: str = "5y") -> pd.DataFrame:
    """
    Descarga precios de cierre ajustados usando yfinance directamente.
    Guarda y actualiza series_historicas.json como único archivo de datos.
    PERÍODO FIJO: Siempre usa 5 años para mejores datos y resultados.
    """
    # Forzar período a 5 años (siempre 5 años para mejores resultados)
    periodo = "5y"
    print(f"\n📥 Descargando precios para {len(tickers)} tickers (período: {periodo})...")
    
    # Archivo único JSON para todas las series
    json_path = Path("series_historicas.json")
    
    # Cargar datos existentes si el archivo existe
    datos_existentes = {}
    fechas_existentes = []
    
    # Función auxiliar para normalizar fechas
    def normalizar_fecha(fecha_str):
        """Normaliza una fecha a formato YYYY-MM-DD"""
        if isinstance(fecha_str, str):
            # Si tiene formato ISO8601 completo, tomar solo la parte de fecha
            if 'T' in fecha_str:
                fecha_str = fecha_str.split('T')[0]
            # Asegurar que tenga formato YYYY-MM-DD
            if len(fecha_str) >= 10:
                return fecha_str[:10]
        return fecha_str
    
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                datos_json = json.load(f)
                if 'activos' in datos_json and 'precios' in datos_json['activos']:
                    datos_existentes = datos_json['activos']['precios']
                    # Convertir listas a diccionarios si es necesario (para compatibilidad)
                    for ticker, datos in datos_existentes.items():
                        if isinstance(datos, list) and 'fechas' in datos_json:
                            fechas = datos_json.get('fechas', [])
                            if len(fechas) == len(datos):
                                # Normalizar fechas antes de crear el diccionario
                                fechas_normalizadas = [normalizar_fecha(f) for f in fechas]
                                datos_existentes[ticker] = dict(zip(fechas_normalizadas, datos))
                        elif isinstance(datos, dict):
                            # Normalizar las claves del diccionario (fechas)
                            datos_existentes[ticker] = {
                                normalizar_fecha(k): v for k, v in datos.items()
                            }
                if 'fechas' in datos_json:
                    fechas_existentes = [normalizar_fecha(f) for f in datos_json['fechas']]
        except Exception as e:
            print(f"   ⚠️  Error cargando JSON existente: {e}")
    
    # Descargar datos faltantes o actualizar existentes
    tickers_unicos = sorted(set(tickers))
    precios_nuevos = {}
    todas_las_fechas = set()
    
    print(f"   Descargando {len(tickers_unicos)} tickers en lotes...")
    
    # Procesar en lotes de 100 tickers para optimizar la descarga
    TAMANO_LOTE = 100
    from config_tickers_factores import obtener_tickers_por_lotes
    
    lotes = list(obtener_tickers_por_lotes(tickers_unicos, TAMANO_LOTE))
    total_lotes = len(lotes)
    
    for num_lote, lote in enumerate(lotes, 1):
        print(f"\n   📦 Lote {num_lote}/{total_lotes} ({len(lote)} tickers)...")
        
        # Descargar lote completo con yfinance (mucho más eficiente)
        try:
            # yfinance puede descargar múltiples tickers en una sola llamada
            lote_str = " ".join(lote)
            datos_lote = yf.download(
                lote_str, 
                period=periodo, 
                interval='1d',
                group_by='ticker',
                auto_adjust=True,  # Usar precios ajustados automáticamente
                progress=False,   # Desactivar progreso interno
                threads=True      # Usar threads para paralelización
            )
            
            # Procesar resultados del lote
            for i, ticker in enumerate(lote, 1):
                print(f"      [{i}/{len(lote)}] {ticker}...", end=' ', flush=True)
                
                try:
                    # Extraer datos del ticker específico
                    if len(lote) == 1:
                        # Si es un solo ticker, la estructura es diferente
                        hist = datos_lote
                    else:
                        hist = datos_lote[ticker] if ticker in datos_lote else None
                    
                    if hist is not None and not hist.empty and 'Close' in hist.columns:
                        # Usar precio de cierre (auto_adjust=True ya ajusta por splits/dividendos)
                        fechas_ticker = [d.strftime('%Y-%m-%d') for d in hist.index]
                        precios_ticker = hist['Close'].dropna().tolist()
                        
                        if precios_ticker:
                            fechas_validas = fechas_ticker[:len(precios_ticker)]
                            precios_nuevos[ticker] = dict(zip(fechas_validas, precios_ticker))
                            todas_las_fechas.update(fechas_validas)
                            print("✅")
                        else:
                            print("❌ (sin datos válidos)")
                    else:
                        print("❌ (sin datos)")
                        
                        # Intentar con datos existentes
                        if ticker in datos_existentes:
                            if isinstance(datos_existentes[ticker], list) and fechas_existentes:
                                precios_nuevos[ticker] = dict(zip(fechas_existentes, datos_existentes[ticker]))
                                todas_las_fechas.update(fechas_existentes)
                            elif isinstance(datos_existentes[ticker], dict):
                                precios_nuevos[ticker] = datos_existentes[ticker]
                                todas_las_fechas.update(datos_existentes[ticker].keys())
                                
                except Exception as e:
                    print(f"❌ (error: {str(e)[:50]})")
                    # Mantener datos existentes si hay error
                    if ticker in datos_existentes:
                        if isinstance(datos_existentes[ticker], list) and fechas_existentes:
                            precios_nuevos[ticker] = dict(zip(fechas_existentes, datos_existentes[ticker]))
                            todas_las_fechas.update(fechas_existentes)
                        elif isinstance(datos_existentes[ticker], dict):
                            precios_nuevos[ticker] = datos_existentes[ticker]
                            todas_las_fechas.update(datos_existentes[ticker].keys())
            
            # Pequeña pausa entre lotes para no sobrecargar la API
            if num_lote < total_lotes:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"   ❌ Error descargando lote {num_lote}: {str(e)[:80]}")
            # Fallback: procesar tickers individualmente
            for ticker in lote:
                print(f"      {ticker}...", end=' ', flush=True)
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period=periodo, interval='1d')
                    
                    if not hist.empty and 'Close' in hist.columns:
                        precio_col = 'Adj Close' if 'Adj Close' in hist.columns else 'Close'
                        fechas_ticker = [d.strftime('%Y-%m-%d') for d in hist.index]
                        precios_ticker = hist[precio_col].tolist()
                        precios_nuevos[ticker] = dict(zip(fechas_ticker, precios_ticker))
                        todas_las_fechas.update(fechas_ticker)
                        print("✅")
                    else:
                        print("❌")
                except Exception as e2:
                    print(f"❌")
                    if ticker in datos_existentes:
                        if isinstance(datos_existentes[ticker], list) and fechas_existentes:
                            precios_nuevos[ticker] = dict(zip(fechas_existentes, datos_existentes[ticker]))
                            todas_las_fechas.update(fechas_existentes)
                        elif isinstance(datos_existentes[ticker], dict):
                            precios_nuevos[ticker] = datos_existentes[ticker]
                            todas_las_fechas.update(datos_existentes[ticker].keys())
                            
    # Si hay datos existentes en formato lista, convertirlos también
    for ticker, datos in datos_existentes.items():
        if ticker not in precios_nuevos and isinstance(datos, list):
            if fechas_existentes:
                precios_nuevos[ticker] = dict(zip(fechas_existentes, datos))
                todas_las_fechas.update(fechas_existentes)
        elif ticker not in precios_nuevos and isinstance(datos, dict):
            precios_nuevos[ticker] = datos
            todas_las_fechas.update(datos.keys())
        elif ticker not in precios_nuevos:
            precios_nuevos[ticker] = datos
    
    # La función normalizar_fecha ya está definida arriba
    
    # Normalizar todas las fechas recopiladas
    todas_las_fechas_normalizadas = {normalizar_fecha(f) for f in todas_las_fechas}
    
    # Ordenar fechas y crear índice común
    fechas_ordenadas = sorted(todas_las_fechas_normalizadas)
    
    # Normalizar también las claves de los diccionarios de precios
    precios_nuevos_normalizados = {}
    for ticker, precios_dict in precios_nuevos.items():
        if isinstance(precios_dict, dict):
            precios_nuevos_normalizados[ticker] = {
                normalizar_fecha(k): v for k, v in precios_dict.items()
            }
        else:
            precios_nuevos_normalizados[ticker] = precios_dict
    
    # Alinear todos los datos al índice común
    datos_alineados = {}
    for ticker, precios_dict in precios_nuevos_normalizados.items():
        if isinstance(precios_dict, dict):
            # Alinear a las fechas comunes, usar NaN donde falte
            datos_alineados[ticker] = [precios_dict.get(fecha, None) for fecha in fechas_ordenadas]
        else:
            # Si no es dict, mantener como está (será manejado después)
            datos_alineados[ticker] = precios_dict
    
    # Obtener sectores e industrias para los tickers descargados
    print(f"   📊 Obteniendo sectores e industrias para {len(datos_alineados)} tickers...")
    sectores_industrias = obtener_sectores_industrias_batch(
        list(datos_alineados.keys()), 
        usar_cache=True, 
        ruta_json=str(json_path)
    )
    
    # Cargar sectores e industrias existentes si el JSON ya existe
    sectores_industrias_existentes = {}
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                datos_existentes_json = json.load(f)
            sectores_industrias_existentes = datos_existentes_json.get('sectores_industrias', {})
        except:
            pass
    
    # Combinar sectores e industrias (nuevos + existentes)
    sectores_industrias_completos = {**sectores_industrias_existentes, **sectores_industrias}
    
    # Guardar en JSON único (sobrescribir) - guardar como listas para compatibilidad
    datos_completos = {
        'fechas': fechas_ordenadas,
        'activos': {
            'lista': list(datos_alineados.keys()),
            'precios': datos_alineados
        },
        'metadata': {
            'periodo': periodo,
            'intervalo': '1d',
            'ultima_actualizacion': datetime.now().isoformat(),
            'total_activos': len(datos_alineados)
        },
        'sectores_industrias': sectores_industrias_completos  # Agregar sectores e industrias
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(datos_completos, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"   ✅ Datos guardados en {json_path}")
    
    # Convertir a DataFrame para retorno - alineado al índice común
    if fechas_ordenadas and datos_alineados:
        # Crear DataFrame con todas las fechas como índice
        # Usar format='mixed' para manejar diferentes formatos de fecha
        try:
            fechas_datetime = pd.to_datetime(fechas_ordenadas, format='mixed', errors='coerce')
        except:
            # Fallback: intentar sin formato específico
            fechas_datetime = pd.to_datetime(fechas_ordenadas, errors='coerce')
        
        # Crear DataFrame
        df = pd.DataFrame(datos_alineados, index=fechas_datetime)
        df = df.sort_index()
        # Eliminar filas donde todos los valores sean NaN
        df = df.dropna(how='all')
        # Eliminar filas con índice NaT (fechas inválidas)
        df = df[df.index.notna()]
        return df
    else:
        raise RuntimeError("No se pudieron descargar datos de precios.")


def calcular_retornos(df_precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula retornos diarios a partir de precios de cierre.
    """
    returns = df_precios.pct_change().dropna(how="all")
    # Eliminar columnas que sean completamente NaN
    returns = returns.dropna(axis=1, how="all")
    return returns


def optimizar_portafolio_max_sharpe(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.08,  # 8% en USD
    annual_trading_days: int = 252,
) -> Tuple[np.ndarray, float, float, float]:
    """
    Optimiza un portafolio para maximizar el ratio de Sharpe usando optimización matemática.
    
    Returns:
        weights: Array de pesos optimizados
        retorno_anual: Retorno anual esperado
        volatilidad_anual: Volatilidad anual
        sharpe_ratio: Ratio de Sharpe
    """
    if returns.shape[1] < 2:
        raise ValueError("Se necesitan al menos 2 activos para optimización.")
    
    # Anualizar retornos: retorno_diario * 252
    mean_returns = returns.mean() * annual_trading_days
    # Anualizar covarianza: cov_diaria * 252 (para que sqrt(cov_anual) = sqrt(cov_diaria) * sqrt(252))
    cov_matrix = returns.cov() * annual_trading_days
    
    num_assets = len(mean_returns)
    
    # Función objetivo: minimizar el negativo del Sharpe (maximizar Sharpe)
    def negative_sharpe(weights):
        port_return = np.sum(mean_returns * weights)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        if port_vol == 0:
            return 1e10  # Penalizar volatilidad cero
        sharpe = (port_return - risk_free_rate) / port_vol
        return -sharpe  # Negativo porque minimizamos
    
    # Restricciones: suma de pesos = 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    
    # Límites: cada peso entre 0 y 1 (sin ventas en corto)
    bounds = tuple((0, 1) for _ in range(num_assets))
    
    # Punto inicial: pesos iguales
    x0 = np.array([1.0 / num_assets] * num_assets)
    
    # Optimizar con múltiples puntos iniciales para evitar mínimos locales
    best_result = None
    best_sharpe = -np.inf
    
    # Probar varios puntos iniciales
    initial_points = [
        x0,  # Pesos iguales
        np.random.random(num_assets),  # Aleatorio 1
        np.random.random(num_assets),  # Aleatorio 2
    ]
    initial_points = [p / np.sum(p) for p in initial_points]  # Normalizar
    
    for x_init in initial_points:
        result = minimize(negative_sharpe, x_init, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter': 1000})
        if result.success:
            test_weights = result.x
            test_return = np.sum(mean_returns * test_weights)
            test_vol = np.sqrt(np.dot(test_weights.T, np.dot(cov_matrix, test_weights)))
            test_sharpe = (test_return - risk_free_rate) / test_vol if test_vol > 0 else -np.inf
            if test_sharpe > best_sharpe:
                best_sharpe = test_sharpe
                best_result = result
    
    if best_result is None or not best_result.success:
        # Si falla, usar pesos iguales como fallback
        weights = x0
    else:
        weights = best_result.x
    
    # Calcular métricas finales
    port_return = np.sum(mean_returns * weights)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0
    
    return weights, port_return, port_vol, sharpe


def optimizar_portafolio_min_var(
    returns: pd.DataFrame,
    annual_trading_days: int = 252,
    risk_free_rate: float = 0.08,  # 8% en USD
) -> Tuple[np.ndarray, float, float, float]:
    """
    Optimiza un portafolio para minimizar la varianza usando optimización matemática.
    
    Returns:
        weights: Array de pesos optimizados
        retorno_anual: Retorno anual esperado
        volatilidad_anual: Volatilidad anual
        sharpe_ratio: Ratio de Sharpe (calculado con risk_free_rate)
    """
    if returns.shape[1] < 2:
        raise ValueError("Se necesitan al menos 2 activos para optimización.")
    
    # Anualizar retornos: retorno_diario * 252
    mean_returns = returns.mean() * annual_trading_days
    # Anualizar covarianza: cov_diaria * 252 (para que sqrt(cov_anual) = sqrt(cov_diaria) * sqrt(252))
    cov_matrix = returns.cov() * annual_trading_days
    
    num_assets = len(mean_returns)
    
    # Función objetivo: minimizar la varianza (volatilidad al cuadrado)
    def portfolio_variance(weights):
        return np.dot(weights.T, np.dot(cov_matrix, weights))
    
    # Restricciones: suma de pesos = 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    
    # Límites: cada peso entre 0 y 1 (sin ventas en corto)
    bounds = tuple((0, 1) for _ in range(num_assets))
    
    # Punto inicial: pesos iguales
    x0 = np.array([1.0 / num_assets] * num_assets)
    
    # Optimizar con múltiples puntos iniciales para evitar mínimos locales
    best_result = None
    best_variance = np.inf
    
    # Probar varios puntos iniciales
    initial_points = [
        x0,  # Pesos iguales
        np.random.random(num_assets),  # Aleatorio 1
        np.random.random(num_assets),  # Aleatorio 2
    ]
    initial_points = [p / np.sum(p) for p in initial_points]  # Normalizar
    
    for x_init in initial_points:
        result = minimize(portfolio_variance, x_init, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter': 1000})
        if result.success:
            test_weights = result.x
            test_variance = np.dot(test_weights.T, np.dot(cov_matrix, test_weights))
            if test_variance < best_variance:
                best_variance = test_variance
                best_result = result
    
    if best_result is None or not best_result.success:
        # Si falla, usar pesos iguales como fallback
        weights = x0
    else:
        weights = best_result.x
    
    # Calcular métricas finales
    port_return = np.sum(mean_returns * weights)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0
    
    return weights, port_return, port_vol, sharpe


def simular_portafolios_markowitz(
    returns: pd.DataFrame,
    num_portfolios: int = 5000,
    risk_free_rate: float = 0.08,  # 8% en USD
    annual_trading_days: int = 252,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Calcula portafolios optimizados usando Markowitz:
    - Máximo Sharpe: optimización matemática
    - Mínima Varianza: optimización matemática
    - También genera simulación de portafolios para visualización
    
    Returns:
        portfolios_df: DataFrame con portafolios simulados (para visualización)
        max_sharpe_pf: Series con portafolio de máximo Sharpe (optimizado)
        min_vol_pf: Series con portafolio de mínima volatilidad (optimizado)
    """
    if returns.shape[1] < 2:
        raise ValueError("Se necesitan al menos 2 activos para un análisis de Markowitz.")

    # Anualizar retornos y covarianza para cálculos consistentes
    mean_returns_annual = returns.mean() * annual_trading_days
    cov_matrix_annual = returns.cov() * annual_trading_days

    # OPTIMIZACIÓN REAL: Máximo Sharpe
    weights_max_sharpe, ret_ms, vol_ms, sharpe_ms = optimizar_portafolio_max_sharpe(
        returns, risk_free_rate, annual_trading_days
    )
    
    # OPTIMIZACIÓN REAL: Mínima Varianza
    weights_min_var, ret_mv, vol_mv, sharpe_mv = optimizar_portafolio_min_var(
        returns, annual_trading_days, risk_free_rate
    )

    # Generar portafolios simulados para visualización (opcional)
    portfolio_returns = []
    portfolio_volatilities = []
    portfolio_sharpes = []
    portfolio_weights = []

    np.random.seed(42)
    for _ in range(num_portfolios):
        weights = np.random.random(len(mean_returns_annual))
        weights /= np.sum(weights)
        weights_array = np.array(weights)

        # Usar retornos y covarianza anualizados
        port_return = np.sum(mean_returns_annual * weights_array)
        port_vol = np.sqrt(
            np.dot(weights_array.T, np.dot(cov_matrix_annual, weights_array))
        )
        sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0

        portfolio_returns.append(port_return)
        portfolio_volatilities.append(port_vol)
        portfolio_sharpes.append(sharpe)
        portfolio_weights.append(weights)

    portfolios_df = pd.DataFrame(
        {
            "Return": portfolio_returns,
            "Volatility": portfolio_volatilities,
            "Sharpe": portfolio_sharpes,
        }
    )
    weight_cols = [f"Weight_{t}" for t in mean_returns_annual.index]
    weights_df = pd.DataFrame(portfolio_weights, columns=weight_cols)
    portfolios_df = pd.concat([portfolios_df, weights_df], axis=1)

    # Crear Series con los portafolios optimizados
    max_sharpe_dict = {"Return": ret_ms, "Volatility": vol_ms, "Sharpe": sharpe_ms}
    for i, ticker in enumerate(mean_returns_annual.index):
        max_sharpe_dict[f"Weight_{ticker}"] = weights_max_sharpe[i]
    max_sharpe_pf = pd.Series(max_sharpe_dict)

    min_vol_dict = {"Return": ret_mv, "Volatility": vol_mv, "Sharpe": sharpe_mv}
    for i, ticker in enumerate(mean_returns_annual.index):
        min_vol_dict[f"Weight_{ticker}"] = weights_min_var[i]
    min_vol_pf = pd.Series(min_vol_dict)

    return portfolios_df, max_sharpe_pf, min_vol_pf


def resumen_portafolio_equally_weighted(
    nombre: str,
    tickers: List[str],
    returns: pd.DataFrame,
    risk_free_rate: float = 0.08,  # 8% en USD
    annual_trading_days: int = 252,
) -> PortfolioSummary:
    """
    Calcula métricas de un portafolio con pesos iguales.
    """
    tickers_validos = [t for t in tickers if t in returns.columns]
    if len(tickers_validos) < 2:
        raise ValueError(f"Portafolio {nombre}: se necesitan al menos 2 activos con datos.")

    sub_returns = returns[tickers_validos]
    weights = np.array([1.0 / len(tickers_validos)] * len(tickers_validos))

    port_daily = (sub_returns * weights).sum(axis=1)
    mean_daily = port_daily.mean()
    std_daily = port_daily.std()

    mean_annual = mean_daily * annual_trading_days
    vol_annual = std_daily * (annual_trading_days ** 0.5)
    sharpe = 0.0 if vol_annual == 0 else (mean_annual - risk_free_rate) / vol_annual
    
    # Calcular sesgo y curtosis del portafolio
    port_skewness = skew(port_daily) if len(port_daily) > 2 else 0.0
    port_kurtosis = kurtosis(port_daily, fisher=True) if len(port_daily) > 2 else 0.0  # fisher=True devuelve exceso de kurtosis

    return PortfolioSummary(
        nombre=nombre,
        tickers=tickers_validos,
        returns_df=sub_returns,
        mean_return_annual=mean_annual,
        volatility_annual=vol_annual,
        sharpe_ratio=sharpe,
        weights={t: 1.0 / len(tickers_validos) for t in tickers_validos},
        skewness=port_skewness,
        kurtosis=port_kurtosis,
    )


def calcular_metricas_spy_qqq(returns: pd.DataFrame, risk_free_rate: float = 0.08) -> Dict[str, Dict]:  # 8% en USD
    """
    Calcula alpha, beta, correlación y R² entre SPY y QQQ en ambas direcciones.
    """
    if "SPY" not in returns.columns or "QQQ" not in returns.columns:
        raise ValueError("Se requieren columnas SPY y QQQ en los retornos.")

    spy_ret = returns["SPY"].dropna()
    qqq_ret = returns["QQQ"].dropna()
    
    # Alinear series a fechas comunes
    common_idx = spy_ret.index.intersection(qqq_ret.index)
    if len(common_idx) < 10:
        return {
            "SPY_vs_QQQ": None,
            "QQQ_vs_SPY": None,
        }
    
    spy_aligned = spy_ret.loc[common_idx]
    qqq_aligned = qqq_ret.loc[common_idx]
    
    # Calcular métricas SPY vs QQQ
    correlation_spy_qqq = spy_aligned.corr(qqq_aligned)
    if pd.isna(correlation_spy_qqq):
        correlation_spy_qqq = 0.0
    
    # Calcular beta usando regresión lineal simple
    cov_spy_qqq = spy_aligned.cov(qqq_aligned)
    var_qqq = qqq_aligned.var()
    beta_spy_qqq = cov_spy_qqq / var_qqq if var_qqq > 0 else 0.0
    
    # Alpha = retorno medio de SPY - beta * retorno medio de QQQ
    mean_spy = spy_aligned.mean()
    mean_qqq = qqq_aligned.mean()
    alpha_spy_qqq_diario = mean_spy - beta_spy_qqq * mean_qqq
    alpha_spy_qqq_anual = alpha_spy_qqq_diario * 252  # Convertir a anual
    
    r_squared_spy_qqq = correlation_spy_qqq ** 2
    
    # Calcular métricas QQQ vs SPY
    correlation_qqq_spy = qqq_aligned.corr(spy_aligned)
    if pd.isna(correlation_qqq_spy):
        correlation_qqq_spy = 0.0
    
    cov_qqq_spy = qqq_aligned.cov(spy_aligned)
    var_spy = spy_aligned.var()
    beta_qqq_spy = cov_qqq_spy / var_spy if var_spy > 0 else 0.0
    
    alpha_qqq_spy_diario = mean_qqq - beta_qqq_spy * mean_spy
    alpha_qqq_spy_anual = alpha_qqq_spy_diario * 252  # Convertir a anual
    r_squared_qqq_spy = correlation_qqq_spy ** 2

    return {
        "SPY_vs_QQQ": {
            'correlacion': correlation_spy_qqq,
            'beta': beta_spy_qqq,
            'alpha_anual': alpha_spy_qqq_anual,
            'r_squared': r_squared_spy_qqq,
        },
        "QQQ_vs_SPY": {
            'correlacion': correlation_qqq_spy,
            'beta': beta_qqq_spy,
            'alpha_anual': alpha_qqq_spy_anual,
            'r_squared': r_squared_qqq_spy,
        },
    }


def obtener_sector_ticker(ticker: str) -> str:
    """
    Obtiene el sector al que pertenece un ticker.
    PRIORIZA series_historicas.json, luego busca en otras fuentes.
    """
    # Mapeo especial para ETFs comunes
    etf_sectores = {
        'SPY': 'S&P 500 ETF',
        'QQQ': 'NASDAQ ETF',
        'DIA': 'Dow Jones ETF',
        'IWM': 'Russell 2000 ETF',
        'VTI': 'Total Stock Market ETF',
        'VOO': 'S&P 500 ETF',
        'IVV': 'S&P 500 ETF',
    }
    
    if ticker in etf_sectores:
        return etf_sectores[ticker]
    
    # PRIORIDAD 1: Buscar en series_historicas.json PRIMERO (detectión automática)
    try:
        import json
        from pathlib import Path
        
        json_path = Path("series_historicas.json")
        if not json_path.exists():
            json_path = Path("datos_series") / "series_historicas.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'sectores' in data:
                    # Buscar en la estructura de sectores del JSON
                    for sector, tickers_sector in data['sectores'].items():
                        if isinstance(tickers_sector, list) and ticker in tickers_sector:
                            return sector
                        elif isinstance(tickers_sector, dict) and ticker in tickers_sector:
                            return sector
    except Exception as e:
        pass
    
    # PRIORIDAD 2: Si es un ETF sectorial, devolver el sector correspondiente
    etf_to_sector = {v: k for k, v in SECTOR_ETF_MAPPING.items()}
    if ticker in etf_to_sector:
        return etf_to_sector[ticker]
    
    # PRIORIDAD 3: Buscar en SECTOR_TICKERS_EN
    for sector, tickers_sector in SECTOR_TICKERS_EN.items():
        if ticker in tickers_sector:
            return sector
    
    # Si no se encuentra, devolver "Desconocido"
    return "Desconocido"


def normalizar_tickers_duplicados(tickers: List[str]) -> List[str]:
    """
    Elimina tickers duplicados de la misma empresa.
    Por ejemplo: GOOG y GOOGL son ambos Alphabet, solo mantener GOOGL.
    BRK.A y BRK.B son ambos Berkshire Hathaway, solo mantener BRK.B.
    """
    # Mapeo de tickers duplicados (mantener el preferido)
    duplicados_map = {
        'GOOG': 'GOOGL',  # Alphabet - preferir GOOGL
        'BRK.A': 'BRK.B',  # Berkshire Hathaway - preferir BRK.B
    }
    
    # Crear un set para tracking y lista resultado
    tickers_normalizados = []
    tickers_vistos = set()
    
    for ticker in tickers:
        # Si es un duplicado conocido, usar el preferido
        if ticker in duplicados_map:
            ticker_normalizado = duplicados_map[ticker]
        else:
            ticker_normalizado = ticker
        
        # Si ya tenemos el ticker normalizado, saltarlo
        if ticker_normalizado in tickers_vistos:
            continue
        
        # Si el ticker original es el preferido de un duplicado, asegurar que no esté el otro
        if ticker_normalizado in duplicados_map.values():
            # Buscar si hay algún duplicado en la lista
            for dup_key, dup_value in duplicados_map.items():
                if dup_value == ticker_normalizado and dup_key in tickers_vistos:
                    # Ya tenemos el duplicado, no agregar este
                    break
            else:
                # Si no encontramos duplicado, agregar el ticker
                tickers_normalizados.append(ticker_normalizado)
                tickers_vistos.add(ticker_normalizado)
        else:
            # Si no es un duplicado conocido, agregarlo directamente
            tickers_normalizados.append(ticker_normalizado)
            tickers_vistos.add(ticker_normalizado)
    
    return tickers_normalizados


def construir_portafolio_alta_correlacion(
    returns: pd.DataFrame = None,
    n_activos: int = NUM_ACTIVOS_PORTAFOLIO,
) -> List[str]:
    """
    Define un portafolio de activos individuales muy correlacionados
    (alta correlación / alto R²) seleccionados aleatoriamente basándose en métricas.
    
    NO incluye SPY y QQQ (solo están en el portafolio base).
    Los tickers se seleccionan aleatoriamente de los que tienen alta correlación entre sí.
    Usa la matriz de correlaciones del JSON si está disponible.
    """
    # NO incluir SPY y QQQ en este portafolio
    portafolio = []
    n_restantes = n_activos
    
    # Cargar matrices de correlación y R² desde JSON
    matriz_corr_json, matriz_r2_json = cargar_matriz_correlaciones_json()
    
    # Obtener TODOS los tickers desde series_historicas.json (solo USD, sin duplicados CEDEARs)
    todos_tickers = obtener_todos_tickers_desde_json(solo_usd=True)
    
    # Si no hay tickers en el JSON, usar fallback
    if not todos_tickers:
        todos_tickers = list(obtener_todos_tickers_sectores())
        print(f"   Advertencia: usando fallback de tickers de sectores ({len(todos_tickers)} tickers)")
    
    todos_tickers = normalizar_tickers_duplicados(todos_tickers)
    
    # Excluir SPY y QQQ de los candidatos (NO deben estar en este portafolio)
    candidatos = [t for t in todos_tickers if t not in portafolio and t not in ["SPY", "QQQ"]]
    
    # Si tenemos returns, filtrar candidatos que estén disponibles en returns
    if returns is not None and not returns.empty:
        candidatos = [t for t in candidatos if t in returns.columns]
        print(f"   📊 Candidatos disponibles en returns: {len(candidatos)}")
    
    if not candidatos:
        # NO HAY FALLBACK: Si no hay candidatos, no se puede construir el portafolio
        print(f"   ❌ No hay candidatos disponibles para construir portafolio de alta correlación")
        return []
    
    # Usar matrices de correlación y R² del JSON si están disponibles
    # PERO también verificar que los candidatos estén en returns si está disponible
    if matriz_corr_json and matriz_r2_json:
        # Filtrar candidatos que tienen correlaciones en el JSON
        candidatos_con_corr = [t for t in candidatos if t in matriz_corr_json]
        
        # Si tenemos returns, filtrar también por disponibilidad en returns
        if returns is not None and not returns.empty:
            candidatos_con_corr = [t for t in candidatos_con_corr if t in returns.columns]
        
        print(f"   🔍 Buscando en {len(candidatos_con_corr)} candidatos con datos de correlación...")
        
        if len(candidatos_con_corr) >= 2:
            # REGLA ESTRICTA: Buscar el clique más grande donde TODAS las correlaciones sean >= 0.70
            umbral_correlacion = 0.70
            
            print(f"   🔍 Construyendo grafo de correlaciones (umbral >= {umbral_correlacion})...")
            
            # Construir grafo de correlaciones: para cada par, verificar si correlación >= 0.70
            # REGLA ESTRICTA: Solo correlación >= 0.70 (no R²)
            grafo_correlaciones = {}
            total_pares = 0
            pares_alta_corr = 0
            
            for i, ticker1 in enumerate(candidatos_con_corr):
                grafo_correlaciones[ticker1] = []
                for ticker2 in candidatos_con_corr[i+1:]:
                    total_pares += 1
                    corr = None
                    
                    # Buscar correlación en ambas direcciones
                    if ticker1 in matriz_corr_json and ticker2 in matriz_corr_json.get(ticker1, {}):
                        corr_val = matriz_corr_json[ticker1].get(ticker2)
                        if corr_val is not None:
                            corr = abs(float(corr_val))
                    elif ticker2 in matriz_corr_json and ticker1 in matriz_corr_json.get(ticker2, {}):
                        corr_val = matriz_corr_json[ticker2].get(ticker1)
                        if corr_val is not None:
                            corr = abs(float(corr_val))
                    
                    # REGLA ESTRICTA: Solo agregar arista si correlación >= 0.70
                    if corr is not None and not np.isnan(corr) and corr >= umbral_correlacion:
                        grafo_correlaciones[ticker1].append(ticker2)
                        pares_alta_corr += 1
            
            nodos_con_conexiones = len([k for k, v in grafo_correlaciones.items() if v])
            print(f"   📊 Grafo construido: {nodos_con_conexiones} nodos con conexiones")
            print(f"      Pares analizados: {total_pares}, Pares con corr >= {umbral_correlacion}: {pares_alta_corr}")
            
            # Algoritmo sistemático para encontrar TODOS los cliques y priorizar los más grandes
            def encontrar_todos_cliques(grafo, min_tamano=2):
                """Encuentra todos los cliques posibles en el grafo, priorizando los más grandes"""
                nodos = list(grafo.keys())
                todos_cliques = []
                
                # Ordenar nodos por grado (número de conexiones) descendente para priorizar los más conectados
                nodos_ordenados = sorted(nodos, key=lambda n: len(grafo.get(n, [])), reverse=True)
                
                # Para cada nodo como semilla, intentar construir el clique máximo
                nodos_procesados = set()
                
                for nodo_inicial in nodos_ordenados:
                    if nodo_inicial in nodos_procesados:
                        continue
                    
                    clique_actual = [nodo_inicial]
                    # Candidatos: solo los que están conectados con el nodo inicial
                    candidatos = [n for n in grafo.get(nodo_inicial, []) if n not in nodos_procesados]
                    
                    # Expandir el clique de forma sistemática
                    while candidatos:
                        # Priorizar candidatos con más conexiones dentro del clique actual
                        candidatos_con_peso = []
                        for candidato in candidatos:
                            conexiones_en_clique = sum(1 for n in clique_actual if candidato in grafo.get(n, []))
                            candidatos_con_peso.append((candidato, conexiones_en_clique))
                        
                        # Ordenar por número de conexiones (mayor a menor)
                        candidatos_con_peso.sort(key=lambda x: x[1], reverse=True)
                        
                        # Buscar el primer candidato que esté conectado con TODOS los del clique
                        candidato_valido = None
                        for candidato, peso in candidatos_con_peso:
                            # Verificar que esté conectado con TODOS los del clique actual
                            conectado_con_todos = True
                            for nodo_clique in clique_actual:
                                if candidato not in grafo.get(nodo_clique, []):
                                    conectado_con_todos = False
                                    break
                            
                            if conectado_con_todos:
                                candidato_valido = candidato
                                break
                        
                        if candidato_valido:
                            clique_actual.append(candidato_valido)
                            candidatos.remove(candidato_valido)
                            # Filtrar candidatos que no están conectados con el nuevo miembro
                            candidatos = [c for c in candidatos if c in grafo.get(candidato_valido, [])]
                        else:
                            break
                    
                    # Guardar el clique si tiene al menos min_tamano nodos
                    if len(clique_actual) >= min_tamano:
                        todos_cliques.append(clique_actual)
                        # Marcar nodos como procesados para evitar duplicados
                        nodos_procesados.update(clique_actual)
                
                # Ordenar cliques por tamaño (mayor a menor)
                todos_cliques.sort(key=len, reverse=True)
                return todos_cliques
            
            # Encontrar todos los cliques posibles
            print(f"   🔍 Buscando grupos de alta correlación (cliques)...")
            todos_cliques = encontrar_todos_cliques(grafo_correlaciones, min_tamano=2)
            
            if todos_cliques:
                print(f"   ✅ Encontrados {len(todos_cliques)} grupos de alta correlación")
                print(f"      Tamaños: {[len(c) for c in todos_cliques[:10]]}...")
                
                # Seleccionar el clique más grande que tenga al menos n_restantes activos
                clique_seleccionado = None
                for clique in todos_cliques:
                    if len(clique) >= n_restantes:
                        clique_seleccionado = clique[:n_restantes]
                        print(f"   ✅ Clique seleccionado: {len(clique_seleccionado)} activos (de {len(clique)} disponibles)")
                        break
                
                # Si no hay clique suficientemente grande, usar el más grande disponible
                if clique_seleccionado is None:
                    if todos_cliques:
                        clique_seleccionado = todos_cliques[0]
                        print(f"   ⚠️  Usando el clique más grande disponible: {len(clique_seleccionado)} activos")
                    else:
                        print(f"   ❌ No se encontraron cliques con correlación >= 0.70")
                        return []
                
                # VERIFICACIÓN PREVIA: Confirmar que el clique seleccionado cumple el criterio estricto
                correlaciones_clique = []
                for i, ticker1 in enumerate(clique_seleccionado):
                    for ticker2 in clique_seleccionado[i+1:]:
                        corr = None
                        if ticker1 in matriz_corr_json and ticker2 in matriz_corr_json.get(ticker1, {}):
                            corr_val = matriz_corr_json[ticker1].get(ticker2)
                            if corr_val is not None:
                                corr = abs(float(corr_val))
                        elif ticker2 in matriz_corr_json and ticker1 in matriz_corr_json.get(ticker2, {}):
                            corr_val = matriz_corr_json[ticker2].get(ticker1)
                            if corr_val is not None:
                                corr = abs(float(corr_val))
                        
                        if corr is not None:
                            correlaciones_clique.append(corr)
                            if corr < 0.70:
                                print(f"   ❌ ERROR EN CLIQUE: {ticker1}-{ticker2} tiene correlación {corr:.3f} (< 0.70)")
                                return []
                
                if correlaciones_clique:
                    min_corr_clique = min(correlaciones_clique)
                    if min_corr_clique < 0.70:
                        print(f"   ❌ El clique seleccionado no cumple el criterio estricto (correlación mínima: {min_corr_clique:.3f})")
                        return []
                    print(f"   ✅ Clique verificado: correlación mínima = {min_corr_clique:.3f} (>= 0.70)")
                
                seleccionados = clique_seleccionado
            else:
                print(f"   ❌ No se encontraron grupos de alta correlación")
                seleccionados = []
                
            # VERIFICACIÓN FINAL ESTRICTA: Confirmar que TODAS las correlaciones entre TODOS los pares sean >= 0.70
            if len(seleccionados) >= 2:
                correlaciones_minimas = []
                correlaciones_todas = []
                pares_problema = []
                
                # Verificar TODAS las correlaciones entre TODOS los pares
                for i, ticker1 in enumerate(seleccionados):
                    for ticker2 in seleccionados[i+1:]:
                        corr = None
                        if ticker1 in matriz_corr_json and ticker2 in matriz_corr_json.get(ticker1, {}):
                            corr_val = matriz_corr_json[ticker1].get(ticker2)
                            if corr_val is not None:
                                corr = abs(float(corr_val))
                        elif ticker2 in matriz_corr_json and ticker1 in matriz_corr_json.get(ticker2, {}):
                            corr_val = matriz_corr_json[ticker2].get(ticker1)
                            if corr_val is not None:
                                corr = abs(float(corr_val))
                        
                        if corr is not None:
                            correlaciones_todas.append((ticker1, ticker2, corr))
                            correlaciones_minimas.append(corr)
                            if corr < 0.70:
                                pares_problema.append((ticker1, ticker2, corr))
                
                if correlaciones_minimas:
                    min_corr = min(correlaciones_minimas)
                    max_corr = max(correlaciones_minimas)
                    avg_corr = np.mean(correlaciones_minimas)
                    
                    # REGLA ESTRICTA: TODAS las correlaciones deben ser >= 0.70
                    if min_corr >= 0.70 and len(pares_problema) == 0:
                        print(f"   ✅ REGLA ESTRICTA CUMPLIDA: Correlación mínima = {min_corr:.3f} (>= 0.70)")
                        print(f"      Correlación máxima = {max_corr:.3f}, Promedio = {avg_corr:.3f}")
                        print(f"      Tickers seleccionados ({len(seleccionados)}): {', '.join(seleccionados)}")
                        return seleccionados[:n_restantes] if len(seleccionados) > n_restantes else seleccionados
                    else:
                        print(f"   ❌ ERROR: Correlación mínima = {min_corr:.3f} (< 0.70) o hay {len(pares_problema)} pares con correlación < 0.70")
                        print(f"      Pares con correlación < 0.70:")
                        for t1, t2, c in pares_problema:
                            print(f"         {t1}-{t2}: {c:.3f}")
                        
                        # Filtrar agresivamente: eliminar activos que tienen correlación < 0.70 con otros
                        # Estrategia: construir un nuevo clique desde cero con solo los que cumplen
                        seleccionados_filtrados = []
                        for ticker in seleccionados:
                            # Verificar que este ticker tiene correlación >= 0.70 con TODOS los ya seleccionados
                            cumple_todos = True
                            for otro in seleccionados_filtrados:
                                corr = None
                                if ticker in matriz_corr_json and otro in matriz_corr_json.get(ticker, {}):
                                    corr = abs(float(matriz_corr_json[ticker].get(otro, 0)))
                                elif otro in matriz_corr_json and ticker in matriz_corr_json.get(otro, {}):
                                    corr = abs(float(matriz_corr_json[otro].get(ticker, 0)))
                                
                                if corr is None or corr < 0.70:
                                    cumple_todos = False
                                    break
                            
                            if cumple_todos:
                                seleccionados_filtrados.append(ticker)
                        
                        # Verificar nuevamente el clique filtrado
                        if len(seleccionados_filtrados) >= 2:
                            correlaciones_filtradas = []
                            for i, ticker1 in enumerate(seleccionados_filtrados):
                                for ticker2 in seleccionados_filtrados[i+1:]:
                                    corr = None
                                    if ticker1 in matriz_corr_json and ticker2 in matriz_corr_json.get(ticker1, {}):
                                        corr = abs(float(matriz_corr_json[ticker1].get(ticker2, 0)))
                                    elif ticker2 in matriz_corr_json and ticker1 in matriz_corr_json.get(ticker2, {}):
                                        corr = abs(float(matriz_corr_json[ticker2].get(ticker1, 0)))
                                    if corr is not None:
                                        correlaciones_filtradas.append(corr)
                            
                            if correlaciones_filtradas and min(correlaciones_filtradas) >= 0.70:
                                seleccionados = seleccionados_filtrados
                                print(f"   ✅ Portafolio filtrado: {len(seleccionados)} activos con TODAS las correlaciones >= 0.70")
                                return seleccionados[:n_restantes] if len(seleccionados) > n_restantes else seleccionados
                            else:
                                print(f"   ❌ El portafolio filtrado aún no cumple el criterio estricto")
                                return []
                        else:
                            print(f"   ❌ No se pudo encontrar un portafolio que cumpla la regla estricta (mínimo 2 activos requeridos)")
                            return []
                else:
                    print(f"   ❌ No se encontraron correlaciones para los tickers seleccionados")
                    return []
            else:
                print(f"   ❌ No se encontraron suficientes activos con correlación >= 0.70 entre todos")
                return []
    
    # Si no hay matrices JSON o no funcionó, usar correlaciones calculadas en tiempo real
    if returns is not None and not returns.empty:
        candidatos_validos = [t for t in candidatos if t in returns.columns]
        
        if len(candidatos_validos) >= n_restantes:
            # FILTRO ESTRICTO: PRIMERO filtrar por correlación >= 0.70, LUEGO seleccionar aleatoriamente
            umbral_correlacion = 0.70
            seleccionados = []
            candidatos_disponibles = candidatos_validos.copy()
            
            import random
            
            # Empezar con el primer candidato (selección aleatoria inicial)
            if candidatos_disponibles:
                random.shuffle(candidatos_disponibles)
                seleccionados.append(candidatos_disponibles.pop(0))
            
            intentos_maximos = len(candidatos_disponibles) * 5
            intentos = 0
            
            while len(seleccionados) < n_restantes and candidatos_disponibles and intentos < intentos_maximos:
                intentos += 1
                
                # PRIMERO: Filtrar candidatos que tienen correlación >= 0.70 con TODOS los ya seleccionados
                candidatos_con_alta_corr = []
                
                for ticker in candidatos_disponibles:
                    todas_alta_corr = True
                    tiene_algunas_altas = False
                    
                    for seleccionado in seleccionados:
                        try:
                            if seleccionado in returns.columns and ticker in returns.columns:
                                corr = abs(returns[ticker].corr(returns[seleccionado]))
                                if not np.isnan(corr) and corr != 0:
                                    if corr < umbral_correlacion:
                                        # Si tiene alguna correlación menor al umbral, no cumple
                                        todas_alta_corr = False
                                        break
                                    elif corr >= umbral_correlacion:
                                        tiene_algunas_altas = True
                                else:
                                    # Si no hay datos de correlación, no cumple
                                    todas_alta_corr = False
                                    break
                        except:
                            todas_alta_corr = False
                            break
                    
                    # Solo incluir si tiene correlación >= 0.70 con TODOS los seleccionados
                    if todas_alta_corr and tiene_algunas_altas:
                        candidatos_con_alta_corr.append(ticker)
                
                # LUEGO: Si hay candidatos filtrados, seleccionar aleatoriamente de ellos
                if candidatos_con_alta_corr:
                    random.shuffle(candidatos_con_alta_corr)
                    ticker_seleccionado = candidatos_con_alta_corr[0]
                    seleccionados.append(ticker_seleccionado)
                    candidatos_disponibles.remove(ticker_seleccionado)
                else:
                    # Si no hay candidatos con correlación alta estricta, salir del loop
                    print(f"   ⚠️  No se encontraron más candidatos con correlación >= {umbral_correlacion} estricta")
                    break
            
            # Calcular scores para los seleccionados
            ticker_scores = []
            for ticker in seleccionados:
                correlaciones = []
                r_squared_list = []
                
                # Comparar con otros seleccionados
                for otro_ticker in seleccionados:
                    if otro_ticker != ticker:
                        try:
                            if otro_ticker in returns.columns and ticker in returns.columns:
                                corr = abs(returns[ticker].corr(returns[otro_ticker]))
                                if not np.isnan(corr) and corr != 0:
                                    r_squared = corr ** 2
                                    # Correlación > 0.70 O R² > 0.55
                                    if corr > umbral_correlacion or r_squared > 0.55:
                                        correlaciones.append(corr)
                                        r_squared_list.append(r_squared)
                        except:
                            pass
                
                if correlaciones:
                    max_corr = np.max(correlaciones)
                    max_r_squared = np.max(r_squared_list)
                else:
                    max_corr = 0.0
                    max_r_squared = 0.0
                
                score = 0.4 * max_corr + 0.6 * max_r_squared
                ticker_scores.append((ticker, score, 0.0, max_corr, max_r_squared))
            
            # VERIFICACIÓN FINAL: Confirmar que TODAS las correlaciones entre los seleccionados sean >= 0.70
            if len(seleccionados) >= 2:
                correlaciones_minimas = []
                for i, ticker1 in enumerate(seleccionados):
                    for ticker2 in seleccionados[i+1:]:
                        try:
                            if ticker1 in returns.columns and ticker2 in returns.columns:
                                corr = abs(returns[ticker1].corr(returns[ticker2]))
                                if not np.isnan(corr):
                                    correlaciones_minimas.append(corr)
                        except:
                            pass
                
                if correlaciones_minimas:
                    min_corr = min(correlaciones_minimas)
                    max_corr = max(correlaciones_minimas)
                    avg_corr = np.mean(correlaciones_minimas)
                    
                    if min_corr >= umbral_correlacion:
                        print(f"   ✅ REGLA ESTRICTA CUMPLIDA: Correlación mínima = {min_corr:.3f} (>= {umbral_correlacion})")
                        print(f"      Correlación máxima = {max_corr:.3f}, Promedio = {avg_corr:.3f}")
                        if len(seleccionados) >= n_restantes:
                            print(f"   📊 Portafolio alta correlación (calculado, correlación >= {umbral_correlacion}):")
                            print(f"      Tickers seleccionados ({len(seleccionados)}): {', '.join(seleccionados)}")
                            return seleccionados[:n_restantes] if len(seleccionados) > n_restantes else seleccionados
                    else:
                        print(f"   ❌ ERROR: Correlación mínima = {min_corr:.3f} (< {umbral_correlacion})")
                        # Filtrar más agresivamente
                        seleccionados_filtrados = []
                        for ticker in seleccionados:
                            cumple_todos = True
                            for otro in seleccionados_filtrados:
                                try:
                                    if ticker in returns.columns and otro in returns.columns:
                                        corr = abs(returns[ticker].corr(returns[otro]))
                                        if corr is None or np.isnan(corr) or corr < umbral_correlacion:
                                            cumple_todos = False
                                            break
                                except:
                                    cumple_todos = False
                                    break
                            
                            if cumple_todos:
                                seleccionados_filtrados.append(ticker)
                        
                        if len(seleccionados_filtrados) >= 2:
                            seleccionados = seleccionados_filtrados
                            print(f"   ✅ Portafolio filtrado: {len(seleccionados)} activos con TODAS las correlaciones >= {umbral_correlacion}")
                            return seleccionados[:n_restantes] if len(seleccionados) > n_restantes else seleccionados
                        else:
                            print(f"   ❌ No se pudo encontrar un portafolio que cumpla la regla estricta")
                            return []
            
            # VERIFICACIÓN FINAL ESTRICTA: Confirmar que TODAS las correlaciones entre TODOS los pares sean >= 0.70
            if len(seleccionados) >= 2:
                correlaciones_minimas = []
                pares_problema = []
                for i, ticker1 in enumerate(seleccionados):
                    for ticker2 in seleccionados[i+1:]:
                        try:
                            if ticker1 in returns.columns and ticker2 in returns.columns:
                                corr = abs(returns[ticker1].corr(returns[ticker2]))
                                if not np.isnan(corr):
                                    correlaciones_minimas.append(corr)
                                    if corr < umbral_correlacion:
                                        pares_problema.append((ticker1, ticker2, corr))
                        except:
                            pass
                
                if correlaciones_minimas:
                    min_corr = min(correlaciones_minimas)
                    if min_corr >= umbral_correlacion:
                        if len(seleccionados) >= n_restantes:
                            print(f"   ✅ REGLA ESTRICTA CUMPLIDA: Correlación mínima = {min_corr:.3f} (>= {umbral_correlacion})")
                            print(f"      Tickers seleccionados ({len(seleccionados)}): {', '.join(seleccionados)}")
                            return seleccionados[:n_restantes] if len(seleccionados) > n_restantes else seleccionados
                        else:
                            print(f"   ⚠️  Solo se encontraron {len(seleccionados)} activos con correlación >= {umbral_correlacion} estricta")
                            print(f"      Correlación mínima = {min_corr:.3f}")
                            if len(seleccionados) >= 2:
                                return seleccionados
                            else:
                                print(f"   ❌ No se puede construir portafolio de alta correlación (mínimo 2 activos requeridos)")
                                return []
                    else:
                        print(f"   ❌ ERROR: Correlación mínima = {min_corr:.3f} (< {umbral_correlacion})")
                        print(f"      Pares con correlación < {umbral_correlacion}:")
                        for t1, t2, c in pares_problema:
                            print(f"         {t1}-{t2}: {c:.3f}")
                        print(f"   ❌ No se puede construir portafolio de alta correlación estricta")
                        return []
                else:
                    print(f"   ❌ No se encontraron correlaciones válidas para los tickers seleccionados")
                    return []
            else:
                print(f"   ❌ No se encontraron suficientes activos con correlación >= {umbral_correlacion} estricta")
                return []
    
    # NO HAY FALLBACK: Si no se puede construir un portafolio con correlación >= 0.70, devolver lista vacía
    print(f"   ❌ No se puede construir portafolio de alta correlación: no hay datos de correlación disponibles")
    return []


def obtener_todos_tickers_desde_json(ruta_json: str = "series_historicas.json", solo_usd: bool = True) -> List[str]:
    """
    Obtiene todos los tickers disponibles desde series_historicas.json.
    Incluye activos, factores, ETFs e índices.
    
    Args:
        ruta_json: Ruta al archivo JSON
        solo_usd: Si True, filtra solo tickers en USD y evita duplicados con CEDEARs
    
    Returns:
        Lista de tickers filtrados
    """
    import json
    from pathlib import Path
    
    # Buscar el archivo en varias ubicaciones posibles
    rutas_posibles = [
        Path(ruta_json),
        Path(__file__).parent / ruta_json,
        Path.cwd() / ruta_json,
        Path("datos_series") / ruta_json,
    ]
    
    datos_json = None
    for ruta in rutas_posibles:
        if ruta.exists():
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos_json = json.load(f)
                print(f"   ✅ Cargado desde: {ruta}")
                break
            except Exception as e:
                print(f"   ⚠️  Error al cargar {ruta}: {e}")
                continue
    
    if not datos_json:
        print(f"   ⚠️  No se encontró {ruta_json}, usando fallback")
        return []
    
    todos_tickers = set()
    
    # Obtener tickers de activos (puede estar en 'activos.lista' o directamente en 'activos')
    if 'activos' in datos_json:
        activos_data = datos_json['activos']
        if isinstance(activos_data, dict):
            # Si tiene 'lista', usar esa lista
            if 'lista' in activos_data and isinstance(activos_data['lista'], list):
                todos_tickers.update(activos_data['lista'])
            # Si tiene 'precios', usar las claves
            elif 'precios' in activos_data and isinstance(activos_data['precios'], dict):
                todos_tickers.update(activos_data['precios'].keys())
            # Si no tiene estructura anidada, usar las claves directamente
            else:
                todos_tickers.update(activos_data.keys())
        elif isinstance(activos_data, list):
            todos_tickers.update(activos_data)
    
    # Obtener tickers de sectores
    if 'sectores' in datos_json:
        for sector, tickers in datos_json['sectores'].items():
            if isinstance(tickers, list):
                todos_tickers.update(tickers)
            elif isinstance(tickers, dict):
                todos_tickers.update(tickers.keys())
    
    # Obtener tickers de factores (puede estar en 'factores.lista' o directamente)
    if 'factores' in datos_json:
        factores_data = datos_json['factores']
        if isinstance(factores_data, dict):
            # Si tiene 'lista', usar esa lista
            if 'lista' in factores_data and isinstance(factores_data['lista'], list):
                todos_tickers.update(factores_data['lista'])
            # Si tiene 'precios', usar las claves
            elif 'precios' in factores_data and isinstance(factores_data['precios'], dict):
                todos_tickers.update(factores_data['precios'].keys())
            # Si no tiene estructura anidada, usar las claves directamente
            else:
                todos_tickers.update(factores_data.keys())
        elif isinstance(factores_data, list):
            todos_tickers.update(factores_data)
    
    # Obtener tickers de índices
    if 'indices' in datos_json:
        if isinstance(datos_json['indices'], dict):
            todos_tickers.update(datos_json['indices'].keys())
        elif isinstance(datos_json['indices'], list):
            todos_tickers.update(datos_json['indices'])
    
    # Si hay datos de series directamente, obtener las claves
    if 'series' in datos_json:
        if isinstance(datos_json['series'], dict):
            todos_tickers.update(datos_json['series'].keys())
    
    # Si hay precios, obtener las claves
    if 'precios' in datos_json:
        if isinstance(datos_json['precios'], dict):
            todos_tickers.update(datos_json['precios'].keys())
    
    print(f"   📊 Total de tickers encontrados en JSON: {len(todos_tickers)}")
    
    # Si solo_usd es True, filtrar por moneda y evitar duplicados
    if solo_usd:
        # Cargar monedas desde el JSON - verificar múltiples ubicaciones posibles
        monedas_tickers = {}
        
        # Intentar cargar desde la clave principal 'monedas'
        if 'monedas' in datos_json:
            monedas_tickers = datos_json.get('monedas', {})
            if isinstance(monedas_tickers, dict) and len(monedas_tickers) > 0:
                print(f"   ✅ Monedas cargadas desde JSON: {len(monedas_tickers)} tickers con moneda detectada")
            else:
                print(f"   ⚠️  Clave 'monedas' existe en JSON pero está vacía o no es un diccionario")
                monedas_tickers = {}
        else:
            # Intentar cargar desde archivo de caché separado
            print(f"   ⚠️  Clave 'monedas' no encontrada en JSON, intentando cargar desde caché...")
            # Intentar cargar desde el mismo directorio del JSON
            json_path = Path(ruta_json)
            if json_path.exists():
                directorio_json = json_path.parent
                monedas_tickers = cargar_monedas_cache(str(directorio_json), 'monedas_cache.json')
                if monedas_tickers:
                    print(f"   ✅ Monedas cargadas desde caché: {len(monedas_tickers)} tickers")
                else:
                    # Intentar desde el archivo JSON principal
                    monedas_tickers = cargar_monedas_cache(str(directorio_json), json_path.name)
                    if monedas_tickers:
                        print(f"   ✅ Monedas cargadas desde JSON principal: {len(monedas_tickers)} tickers")
                    else:
                        print(f"   ⚠️  No se encontraron monedas en caché")
                        monedas_tickers = {}
            else:
                monedas_tickers = {}
        
        # Si no hay monedas en el JSON o faltan algunas, usar reglas simples primero (más rápido)
        tickers_sin_moneda = [t for t in todos_tickers if t not in monedas_tickers]
        if tickers_sin_moneda:
            print(f"   🔍 Asignando monedas para {len(tickers_sin_moneda)} tickers usando reglas simples...")
            # Usar reglas simples primero (mucho más rápido que detectar con API)
            for ticker in tickers_sin_moneda:
                if ticker.endswith('.BA'):
                    # CEDEARs en USD: terminan en D.BA o tienen .D.BA o .C.BA
                    if ticker.endswith('D.BA') or '.D.BA' in ticker or '.C.BA' in ticker or ticker.endswith('C.BA'):
                        monedas_tickers[ticker] = 'USD'
                    else:
                        monedas_tickers[ticker] = 'ARS'
                else:
                    # Por defecto, tickers sin .BA son USD (internacionales)
                    monedas_tickers[ticker] = 'USD'
            print(f"   ✅ Monedas asignadas usando reglas simples para {len(tickers_sin_moneda)} tickers")
            
            # Guardar monedas detectadas en caché para futuras ejecuciones
            json_path = Path(ruta_json)
            if json_path.exists():
                directorio_json = json_path.parent
                guardar_monedas_cache(monedas_tickers, str(directorio_json), 'monedas_cache.json')
                print(f"   💾 Monedas guardadas en caché para futuras ejecuciones")
        
        # Filtrar solo tickers en USD
        tickers_usd = {t for t in todos_tickers if monedas_tickers.get(t, 'USD') == 'USD'}
        print(f"   💵 Tickers en USD: {len(tickers_usd)}")
        
        # Evitar duplicados: si hay MELI (NYSE) y MELID.BA (CEDEAR), mantener solo MELI
        # Mapeo de CEDEARs a acciones originales
        tickers_finales = set()
        tickers_cedear_vistos = set()
        
        for ticker in tickers_usd:
            # Si es un CEDEAR (termina en D.BA o tiene .D.BA)
            if ticker.endswith('D.BA') or '.D.BA' in ticker or (ticker.endswith('.BA') and 'D' in ticker):
                # Extraer el ticker base (ej: MELID.BA -> MELI)
                ticker_base = ticker.replace('D.BA', '').replace('.D.BA', '').replace('.BA', '')
                # Si ya tenemos el ticker base (ej: MELI), no agregar el CEDEAR
                if ticker_base in tickers_usd:
                    tickers_cedear_vistos.add(ticker)
                    continue
                # Si no tenemos el ticker base, agregar el CEDEAR
                tickers_finales.add(ticker)
            else:
                # Es un ticker normal, verificar que no tengamos su CEDEAR
                ticker_cedear = f"{ticker}D.BA"
                if ticker_cedear not in tickers_usd:
                    tickers_finales.add(ticker)
        
        print(f"   🔄 Tickers CEDEARs excluidos (duplicados): {len(tickers_cedear_vistos)}")
        print(f"   ✅ Tickers finales (USD, sin duplicados): {len(tickers_finales)}")
        
        lista_tickers = sorted(list(tickers_finales))
    else:
        # No filtrar, devolver todos
        lista_tickers = sorted(list(todos_tickers))
    
    return lista_tickers


def construir_portafolio_alta_volatilidad_sesgo_positivo(
    returns: pd.DataFrame = None,
    n_activos: int = NUM_ACTIVOS_PORTAFOLIO,
    percentil_volatilidad: float = 0.75,
    sesgo_minimo: float = 0.0,
) -> List[str]:
    """
    Construye un portafolio de activos con alta volatilidad y sesgo positivo
    (distribución con colas a la derecha).
    
    Filtra activos que tienen:
    - Volatilidad por encima del percentil especificado (por defecto 75%)
    - Sesgo positivo (skewness > sesgo_minimo)
    
    NO incluye SPY y QQQ (solo están en el portafolio base).
    """
    # NO incluir SPY y QQQ en este portafolio
    portafolio = []
    n_restantes = n_activos
    
    # Obtener TODOS los tickers desde series_historicas.json (solo USD, sin duplicados CEDEARs)
    todos_tickers = obtener_todos_tickers_desde_json(solo_usd=True)
    
    # Si no hay tickers en el JSON, usar fallback
    if not todos_tickers:
        todos_tickers = list(obtener_todos_tickers_sectores())
        print(f"   ⚠️  Usando fallback de tickers de sectores: {len(todos_tickers)} tickers")
    
    todos_tickers = normalizar_tickers_duplicados(todos_tickers)
    
    # Excluir SPY y QQQ de los candidatos
    candidatos = [t for t in todos_tickers if t not in portafolio and t not in ["SPY", "QQQ"]]
    
    # Si tenemos returns, filtrar candidatos que estén disponibles en returns
    if returns is not None and not returns.empty:
        candidatos = [t for t in candidatos if t in returns.columns]
        print(f"   📊 Candidatos disponibles en returns: {len(candidatos)}")
        
        if len(candidatos) < n_restantes:
            # Fallback mínimo
            fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM", "ADBE", "ORCL", "CSCO", "INTC", "AMD"]
            fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
            fallback = [t for t in fallback if t in returns.columns]
            print(f"   ⚠️  Usando fallback: {fallback[:n_restantes]}")
            return fallback[:n_restantes]
        
        # Calcular métricas para cada candidato
        metricas_candidatos = []
        volatilidades = []
        sesgos = []
        
        for ticker in candidatos:
            try:
                serie_returns = returns[ticker].dropna()
                if len(serie_returns) < 20:  # Mínimo de datos
                    continue
                
                # Calcular volatilidad anual
                vol_diaria = serie_returns.std()
                vol_anual = vol_diaria * np.sqrt(252)
                volatilidades.append(vol_anual)
                
                # Calcular sesgo (skewness)
                sesgo_valor = skew(serie_returns)
                sesgos.append(sesgo_valor)
                
                metricas_candidatos.append({
                    'ticker': ticker,
                    'volatilidad': vol_anual,
                    'sesgo': sesgo_valor,
                    'retorno_medio': serie_returns.mean() * 252,
                })
            except Exception as e:
                continue
        
        if not metricas_candidatos:
            # Fallback si no hay métricas
            fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM"]
            fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
            fallback = [t for t in fallback if t in returns.columns]
            return fallback[:n_restantes]
        
        # Calcular umbral de volatilidad (percentil)
        umbral_volatilidad = np.percentile(volatilidades, percentil_volatilidad * 100)
        
        # Filtrar candidatos: alta volatilidad Y sesgo positivo
        candidatos_filtrados = [
            m for m in metricas_candidatos
            if m['volatilidad'] >= umbral_volatilidad and m['sesgo'] > sesgo_minimo
        ]
        
        print(f"   📊 Candidatos con alta volatilidad (≥{umbral_volatilidad:.2%}) y sesgo positivo (> {sesgo_minimo:.2f}): {len(candidatos_filtrados)}")
        
        if len(candidatos_filtrados) >= n_restantes:
            # Ordenar por score: 60% volatilidad, 40% sesgo
            for m in candidatos_filtrados:
                # Normalizar scores (0-1)
                vol_norm = (m['volatilidad'] - umbral_volatilidad) / (max(volatilidades) - umbral_volatilidad + 1e-10)
                sesgo_norm = max(0, m['sesgo']) / (max(sesgos) + 1e-10) if max(sesgos) > 0 else 0
                m['score'] = 0.6 * vol_norm + 0.4 * sesgo_norm
            
            # Ordenar por score descendente
            candidatos_filtrados.sort(key=lambda x: x['score'], reverse=True)
            
            # Seleccionar top candidatos y mezclar aleatoriamente
            top_n = max(n_restantes, int(len(candidatos_filtrados) * 0.5))
            top_candidatos = [m['ticker'] for m in candidatos_filtrados[:top_n]]
            
            import random
            random.shuffle(top_candidatos)
            seleccionados = top_candidatos[:n_restantes]
            
            print(f"   ✅ Portafolio alta volatilidad y sesgo positivo seleccionado:")
            print(f"      Tickers ({len(seleccionados)}): {', '.join(seleccionados)}")
            if candidatos_filtrados:
                mejor = candidatos_filtrados[0]
                print(f"      Mejor candidato - Vol: {mejor['volatilidad']:.2%}, Sesgo: {mejor['sesgo']:.3f}")
            
            return seleccionados
        else:
            # Si no hay suficientes con ambos criterios, relajar filtro de sesgo
            print(f"   ⚠️  Solo {len(candidatos_filtrados)} candidatos cumplen ambos criterios, relajando filtro de sesgo...")
            candidatos_alta_vol = [
                m for m in metricas_candidatos
                if m['volatilidad'] >= umbral_volatilidad
            ]
            
            if len(candidatos_alta_vol) >= n_restantes:
                # Ordenar por volatilidad y sesgo (priorizar sesgo positivo si existe)
                candidatos_alta_vol.sort(key=lambda x: (x['volatilidad'], max(0, x['sesgo'])), reverse=True)
                seleccionados = [m['ticker'] for m in candidatos_alta_vol[:n_restantes]]
                
                import random
                random.shuffle(seleccionados)
                print(f"   ✅ Portafolio alta volatilidad (relajado): {len(seleccionados)} activos")
                return seleccionados
            else:
                # Último recurso: usar los de mayor volatilidad disponibles
                metricas_candidatos.sort(key=lambda x: x['volatilidad'], reverse=True)
                seleccionados = [m['ticker'] for m in metricas_candidatos[:n_restantes]]
                print(f"   ⚠️  Usando top {len(seleccionados)} activos por volatilidad")
                return seleccionados
    else:
        # Si no hay returns, usar fallback
        fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM"]
        fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
        return fallback[:n_restantes]


def construir_portafolio_colas_gruesas(
    returns: pd.DataFrame = None,
    n_activos: int = NUM_ACTIVOS_PORTAFOLIO,
    percentil_kurtosis: float = 0.75,
    kurtosis_minima: float = 3.0,
) -> List[str]:
    """
    Construye un portafolio de activos con colas gruesas (fat tails).
    
    Filtra activos que tienen:
    - Kurtosis por encima del percentil especificado (por defecto 75%)
    - Kurtosis mínima (por defecto 3.0, que es mayor que la normal que tiene kurtosis=3)
    - Kurtosis alta indica colas gruesas (mayor probabilidad de eventos extremos)
    
    NO incluye SPY y QQQ (solo están en el portafolio base).
    """
    # NO incluir SPY y QQQ en este portafolio
    portafolio = []
    n_restantes = n_activos
    
    # Obtener TODOS los tickers desde series_historicas.json (solo USD, sin duplicados CEDEARs)
    todos_tickers = obtener_todos_tickers_desde_json(solo_usd=True)
    
    # Si no hay tickers en el JSON, usar fallback
    if not todos_tickers:
        todos_tickers = list(obtener_todos_tickers_sectores())
        print(f"   ⚠️  Usando fallback de tickers de sectores: {len(todos_tickers)} tickers")
    
    todos_tickers = normalizar_tickers_duplicados(todos_tickers)
    
    # Excluir SPY y QQQ de los candidatos
    candidatos = [t for t in todos_tickers if t not in portafolio and t not in ["SPY", "QQQ"]]
    
    # Si tenemos returns, filtrar candidatos que estén disponibles en returns
    if returns is not None and not returns.empty:
        candidatos = [t for t in candidatos if t in returns.columns]
        print(f"   📊 Candidatos disponibles en returns: {len(candidatos)}")
        
        if len(candidatos) < n_restantes:
            # Fallback mínimo
            fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM", "ADBE", "ORCL", "CSCO", "INTC", "AMD"]
            fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
            fallback = [t for t in fallback if t in returns.columns]
            print(f"   ⚠️  Usando fallback: {fallback[:n_restantes]}")
            return fallback[:n_restantes]
        
        # Calcular métricas para cada candidato
        metricas_candidatos = []
        kurtosis_values = []
        
        for ticker in candidatos:
            try:
                serie_returns = returns[ticker].dropna()
                if len(serie_returns) < 20:  # Mínimo de datos
                    continue
                
                # Calcular kurtosis (exceso de kurtosis, fisher=True)
                # Kurtosis normal = 3, exceso de kurtosis = kurtosis - 3
                # Valores positivos indican colas gruesas
                kurtosis_valor = kurtosis(serie_returns, fisher=True)  # fisher=True devuelve exceso
                kurtosis_absoluta = kurtosis_valor + 3  # Convertir a kurtosis absoluta
                kurtosis_values.append(kurtosis_absoluta)
                
                # Calcular volatilidad anual para referencia
                vol_diaria = serie_returns.std()
                vol_anual = vol_diaria * np.sqrt(252)
                
                metricas_candidatos.append({
                    'ticker': ticker,
                    'kurtosis': kurtosis_absoluta,
                    'kurtosis_exceso': kurtosis_valor,
                    'volatilidad': vol_anual,
                    'retorno_medio': serie_returns.mean() * 252,
                })
            except Exception as e:
                continue
        
        if not metricas_candidatos:
            # Fallback si no hay métricas
            fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM"]
            fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
            fallback = [t for t in fallback if t in returns.columns]
            return fallback[:n_restantes]
        
        # Calcular umbral de kurtosis (percentil)
        umbral_kurtosis = np.percentile(kurtosis_values, percentil_kurtosis * 100)
        umbral_final = max(umbral_kurtosis, kurtosis_minima)
        
        # Filtrar candidatos: alta kurtosis (colas gruesas)
        candidatos_filtrados = [
            m for m in metricas_candidatos
            if m['kurtosis'] >= umbral_final
        ]
        
        print(f"   📊 Candidatos con colas gruesas (kurtosis ≥{umbral_final:.2f}): {len(candidatos_filtrados)}")
        
        if len(candidatos_filtrados) >= n_restantes:
            # Ordenar por kurtosis descendente
            candidatos_filtrados.sort(key=lambda x: x['kurtosis'], reverse=True)
            
            # Seleccionar top candidatos y mezclar aleatoriamente
            top_n = max(n_restantes, int(len(candidatos_filtrados) * 0.5))
            top_candidatos = [m['ticker'] for m in candidatos_filtrados[:top_n]]
            
            import random
            random.shuffle(top_candidatos)
            seleccionados = top_candidatos[:n_restantes]
            
            print(f"   ✅ Portafolio colas gruesas seleccionado:")
            print(f"      Tickers ({len(seleccionados)}): {', '.join(seleccionados)}")
            if candidatos_filtrados:
                mejor = candidatos_filtrados[0]
                print(f"      Mejor candidato - Kurtosis: {mejor['kurtosis']:.2f}, Vol: {mejor['volatilidad']:.2%}")
            
            return seleccionados
        else:
            # Si no hay suficientes, relajar umbral
            print(f"   ⚠️  Solo {len(candidatos_filtrados)} candidatos cumplen criterio, relajando umbral...")
            # Ordenar todos por kurtosis descendente
            metricas_candidatos.sort(key=lambda x: x['kurtosis'], reverse=True)
            seleccionados = [m['ticker'] for m in metricas_candidatos[:n_restantes]]
            
            import random
            random.shuffle(seleccionados)
            print(f"   ✅ Portafolio colas gruesas (relajado): {len(seleccionados)} activos")
            return seleccionados
    else:
        # Si no hay returns, usar fallback
        fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM"]
        fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
        return fallback[:n_restantes]


def cargar_matriz_correlaciones_json(ruta_json: str = "series_historicas.json") -> tuple:
    """
    Carga las matrices de correlación y R² desde el archivo JSON.
    
    Returns:
        tuple: (matriz_correlacion, matriz_r2) donde cada una es Dict[str, Dict[str, float]]
    """
    import json
    from pathlib import Path
    
    json_path = Path(ruta_json)
    if not json_path.exists():
        # Intentar en datos_series
        json_path = Path("datos_series") / ruta_json
        if not json_path.exists():
            return {}, {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            matrices = data.get('matrices', {})
            matriz_correlacion = matrices.get('correlacion', {})
            matriz_r2 = matrices.get('r2', {})
            return matriz_correlacion, matriz_r2
    except Exception as e:
        print(f"   ⚠️ No se pudo cargar matrices desde {json_path}: {e}")
        return {}, {}


def construir_portafolio_baja_correlacion(
    returns: pd.DataFrame = None,
    n_activos: int = NUM_ACTIVOS_PORTAFOLIO,
) -> List[str]:
    """
    Construye un portafolio de activos individuales de baja correlación
    y bajo R² entre sí, seleccionados aleatoriamente basándose en métricas.
    
    NO incluye SPY y QQQ (solo están en el portafolio base).
    Los tickers se seleccionan aleatoriamente de los que tienen baja correlación entre sí.
    Un activo NO se incluye si tiene correlación > 0.50 con 2 o más activos del portafolio.
    Usa la matriz de correlaciones del JSON si está disponible.
    """
    from config_tickers_factores import obtener_todos_tickers_sectores
    
    # NO incluir SPY y QQQ en este portafolio
    portafolio = []
    n_restantes = n_activos
    
    # Cargar matrices de correlación y R² desde JSON
    matriz_corr_json, matriz_r2_json = cargar_matriz_correlaciones_json()
    
    # Obtener TODOS los tickers desde series_historicas.json (solo USD, sin duplicados CEDEARs)
    todos_tickers = obtener_todos_tickers_desde_json(solo_usd=True)
    
    # Si no hay tickers en el JSON, usar fallback
    if not todos_tickers:
        from config_tickers_factores import obtener_todos_tickers_sectores
        todos_tickers = list(obtener_todos_tickers_sectores())
        print(f"   ⚠️  Usando fallback de config_tickers_factores: {len(todos_tickers)} tickers")
    
    todos_tickers = normalizar_tickers_duplicados(todos_tickers)
    print(f"   📊 Total de tickers disponibles (después de normalizar): {len(todos_tickers)}")
    
    # Excluir SPY y QQQ de los candidatos (NO deben estar en este portafolio)
    candidatos = [t for t in todos_tickers if t not in portafolio and t not in ["SPY", "QQQ"]]
    print(f"   📊 Candidatos después de excluir SPY/QQQ: {len(candidatos)}")
    
    # Si tenemos returns, filtrar candidatos que estén disponibles en returns
    if returns is not None and not returns.empty:
        candidatos = [t for t in candidatos if t in returns.columns]
        print(f"   📊 Candidatos disponibles en returns: {len(candidatos)}")
    
    if not candidatos:
        # Fallback mínimo (sin SPY/QQQ)
        fallback = ["XLE", "XLU", "XLV", "XLP", "XLF", "XLI", "XLB", "XLRE", "AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA"]
        fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
        # Si tenemos returns, filtrar también el fallback
        if returns is not None and not returns.empty:
            fallback = [t for t in fallback if t in returns.columns]
        print(f"   ⚠️  Usando fallback: {fallback[:n_restantes]}")
        return fallback[:n_restantes]
        fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
        return portafolio + fallback[:n_restantes]
    
    # Usar matrices de correlación y R² del JSON si están disponibles
    # PERO también verificar que los candidatos estén en returns si está disponible
    if matriz_corr_json and matriz_r2_json:
        # Filtrar candidatos que tienen correlaciones en el JSON (buscar en ambas direcciones)
        candidatos_con_corr = []
        for t in candidatos:
            # Verificar si el ticker está en el JSON (como clave o como valor en otras claves)
            if t in matriz_corr_json:
                candidatos_con_corr.append(t)
            else:
                # Buscar si aparece como valor en otras claves
                for key, corr_dict in matriz_corr_json.items():
                    if isinstance(corr_dict, dict) and t in corr_dict:
                        candidatos_con_corr.append(t)
                        break
        
        # Si tenemos returns, filtrar también por disponibilidad en returns
        if returns is not None and not returns.empty:
            candidatos_con_corr = [t for t in candidatos_con_corr if t in returns.columns]
        
        if len(candidatos_con_corr) >= n_restantes:
            # PRIMER FILTRO: Solo candidatos con correlación < 0.50 con SPY y QQQ (si están en el JSON)
            umbral_correlacion = 0.50
            candidatos_baja_corr_base = []
            
            print(f"   📊 Filtrando {len(candidatos_con_corr)} candidatos por correlación < 0.50 con SPY/QQQ...")
            
            for ticker in candidatos_con_corr:
                cumple_umbral = True
                max_corr_base = 0.0
                
                # Verificar correlación con SPY y QQQ (solo para referencia, no los incluimos)
                for base_ticker in ["SPY", "QQQ"]:
                    # Buscar correlación en ambas direcciones
                    corr_base = 0.0
                    if ticker in matriz_corr_json and base_ticker in matriz_corr_json.get(ticker, {}):
                        corr_base = abs(matriz_corr_json[ticker].get(base_ticker, 0))
                    elif base_ticker in matriz_corr_json and ticker in matriz_corr_json.get(base_ticker, {}):
                        corr_base = abs(matriz_corr_json[base_ticker].get(ticker, 0))
                    
                    if not np.isnan(corr_base) and corr_base != 0:
                        max_corr_base = max(max_corr_base, corr_base)
                        # Para baja correlación, queremos correlación < 0.50 con SPY/QQQ
                        if corr_base >= umbral_correlacion:
                            cumple_umbral = False
                            break
                
                if cumple_umbral:
                    candidatos_baja_corr_base.append((ticker, max_corr_base))
            
            # NO ordenar - mantener aleatoriedad completa
            # Mezclar aleatoriamente antes de seleccionar
            import random
            random.shuffle(candidatos_baja_corr_base)
            candidatos_filtrados = [t[0] for t in candidatos_baja_corr_base]
            
            if len(candidatos_filtrados) >= n_restantes:
                # SEGUNDO FILTRO ESTRICTO: PRIMERO filtrar por correlación < 0.50, LUEGO seleccionar aleatoriamente
                umbral_correlacion_baja = 0.50
                seleccionados = []
                candidatos_disponibles = candidatos_filtrados.copy()
                
                import random
                
                # Empezar con el primer candidato (selección aleatoria inicial)
                if candidatos_disponibles:
                    random.shuffle(candidatos_disponibles)
                    seleccionados.append(candidatos_disponibles.pop(0))
                
                intentos_maximos = len(candidatos_disponibles) * 5
                intentos = 0
                
                while len(seleccionados) < n_restantes and candidatos_disponibles and intentos < intentos_maximos:
                    intentos += 1
                    
                    # PRIMERO: Filtrar candidatos que tienen correlación < 0.50 con TODOS los ya seleccionados
                    candidatos_con_baja_corr = []
                    
                    for ticker in candidatos_disponibles:
                        todas_baja_corr = True
                        tiene_algunas_bajas = False
                        
                        for seleccionado in seleccionados:
                            corr = None
                            
                            # Buscar correlación en ambas direcciones
                            if ticker in matriz_corr_json and seleccionado in matriz_corr_json.get(ticker, {}):
                                corr_val = matriz_corr_json[ticker].get(seleccionado)
                                if corr_val is not None:
                                    corr = abs(float(corr_val))
                            elif seleccionado in matriz_corr_json and ticker in matriz_corr_json.get(seleccionado, {}):
                                corr_val = matriz_corr_json[seleccionado].get(ticker)
                                if corr_val is not None:
                                    corr = abs(float(corr_val))
                            
                            if corr is not None and not np.isnan(corr):
                                if corr >= umbral_correlacion_baja:
                                    # Si tiene alguna correlación >= 0.50, no cumple
                                    todas_baja_corr = False
                                    break
                                elif corr < umbral_correlacion_baja:
                                    tiene_algunas_bajas = True
                            else:
                                # Si no hay datos de correlación, no cumple
                                todas_baja_corr = False
                                break
                        
                        # Solo incluir si tiene correlación < 0.50 con TODOS los seleccionados
                        if todas_baja_corr and tiene_algunas_bajas:
                            candidatos_con_baja_corr.append(ticker)
                    
                    # LUEGO: Si hay candidatos filtrados, seleccionar aleatoriamente de ellos
                    if candidatos_con_baja_corr:
                        random.shuffle(candidatos_con_baja_corr)
                        ticker_seleccionado = candidatos_con_baja_corr[0]
                        seleccionados.append(ticker_seleccionado)
                        candidatos_disponibles.remove(ticker_seleccionado)
                    else:
                        # Si no hay candidatos con correlación baja estricta, salir del loop
                        print(f"   ⚠️  No se encontraron más candidatos con correlación < {umbral_correlacion_baja} estricta")
                        break
                
                if len(seleccionados) >= 10:
                    print(f"   📊 Portafolio baja correlación (JSON, correlación < 0.70 o R² < 0.50):")
                    print(f"      Tickers seleccionados: {', '.join(seleccionados)}")
                    print(f"      Total candidatos filtrados: {len(candidatos_filtrados)}")
                    return seleccionados
                elif len(seleccionados) >= 2:
                    # Si tenemos al menos 2, pero menos de 5, intentar agregar más relajando el filtro
                    print(f"   ⚠️  Solo se encontraron {len(seleccionados)} activos con baja correlación estricta, relajando filtro...")
                    # Continuar agregando más candidatos sin el filtro estricto de R²
                    candidatos_restantes = [t for t in candidatos_filtrados if t not in seleccionados]
                    random.shuffle(candidatos_restantes)
                    while len(seleccionados) < 5 and candidatos_restantes:
                        ticker = candidatos_restantes.pop(0)
                        # Verificar solo correlación < 0.50 (sin R² estricto)
                        puede_agregar = True
                        correlaciones_altas = 0
                        for seleccionado in seleccionados:
                            corr = None
                            r2 = None
                            
                            if ticker in matriz_corr_json and seleccionado in matriz_corr_json.get(ticker, {}):
                                corr_val = matriz_corr_json[ticker].get(seleccionado)
                                if corr_val is not None:
                                    corr = abs(float(corr_val))
                            elif seleccionado in matriz_corr_json and ticker in matriz_corr_json.get(seleccionado, {}):
                                corr_val = matriz_corr_json[seleccionado].get(ticker)
                                if corr_val is not None:
                                    corr = abs(float(corr_val))
                            
                            if ticker in matriz_r2_json and seleccionado in matriz_r2_json.get(ticker, {}):
                                r2_val = matriz_r2_json[ticker].get(seleccionado)
                                if r2_val is not None:
                                    r2 = float(r2_val)
                            elif seleccionado in matriz_r2_json and ticker in matriz_r2_json.get(seleccionado, {}):
                                r2_val = matriz_r2_json[seleccionado].get(ticker)
                                if r2_val is not None:
                                    r2 = float(r2_val)
                            
                            if corr is not None and r2 is not None and not np.isnan(corr) and not np.isnan(r2):
                                # Para baja correlación: correlación < 0.70 o R² < 0.50
                                if corr >= 0.70 or r2 >= 0.50:
                                    correlaciones_altas += 1
                                    if correlaciones_altas >= 2:
                                        puede_agregar = False
                                        break
                        if puede_agregar:
                            seleccionados.append(ticker)
                    if len(seleccionados) >= 10:
                        return seleccionados[:5]
                    elif len(seleccionados) >= 2:
                        # Si aún no llegamos a 5, usar candidatos filtrados para completar
                        candidatos_para_completar = [t for t in candidatos_filtrados if t not in seleccionados]
                        random.shuffle(candidatos_para_completar)
                        while len(seleccionados) < 5 and candidatos_para_completar:
                            seleccionados.append(candidatos_para_completar.pop(0))
                        return seleccionados[:10] if len(seleccionados) >= 10 else seleccionados
                else:
                    print(f"   ⚠️  No se encontraron suficientes activos con baja correlación estricta ({len(seleccionados)} encontrados)")
                    # Si no hay suficientes, usar los candidatos filtrados por correlación con base
                    if len(candidatos_filtrados) >= 10:
                        return candidatos_filtrados[:5]
                    elif len(candidatos_filtrados) >= 2:
                        # Completar hasta 5 con candidatos adicionales si es posible
                        return candidatos_filtrados
    
    # Si tenemos returns, usar correlaciones calculadas en tiempo real
    if returns is not None and not returns.empty:
        candidatos_validos = [t for t in candidatos if t in returns.columns]
        base_tickers = [t for t in portafolio if t in returns.columns]  # SPY y QQQ
        
        if len(candidatos_validos) >= n_restantes:
            # PRIMER FILTRO: Solo candidatos con correlación < 0.50 con SPY y QQQ
            umbral_correlacion = 0.50
            candidatos_baja_corr_base = []
            
            for ticker in candidatos_validos:
                cumple_umbral = True
                max_corr_base = 0.0
                
                # Verificar correlación con SPY y QQQ (solo para referencia, no los incluimos)
                for base_ticker in ["SPY", "QQQ"]:
                    try:
                        if base_ticker in returns.columns:
                            corr_base = abs(returns[ticker].corr(returns[base_ticker]))
                            if not np.isnan(corr_base) and corr_base != 0:
                                max_corr_base = max(max_corr_base, corr_base)
                                # Para baja correlación, queremos correlación < 0.50 con SPY/QQQ
                                if corr_base >= umbral_correlacion:
                                    cumple_umbral = False
                                    break
                    except:
                        pass
                
                if cumple_umbral:
                    candidatos_baja_corr_base.append((ticker, max_corr_base))
            
            # NO ordenar - mantener aleatoriedad completa
            # Mezclar aleatoriamente antes de seleccionar
            import random
            random.shuffle(candidatos_baja_corr_base)
            candidatos_filtrados = [t[0] for t in candidatos_baja_corr_base]
            
            if len(candidatos_filtrados) >= n_restantes:
                # SEGUNDO FILTRO ESTRICTO: PRIMERO filtrar por correlación < 0.50, LUEGO seleccionar aleatoriamente
                umbral_correlacion_baja = 0.50
                seleccionados = []
                candidatos_disponibles = candidatos_filtrados.copy()
                
                import random
                
                # Empezar con el primer candidato (selección aleatoria inicial)
                if candidatos_disponibles:
                    random.shuffle(candidatos_disponibles)
                    seleccionados.append(candidatos_disponibles.pop(0))
                
                intentos_maximos = len(candidatos_disponibles) * 5
                intentos = 0
                
                while len(seleccionados) < n_restantes and candidatos_disponibles and intentos < intentos_maximos:
                    intentos += 1
                    
                    # PRIMERO: Filtrar candidatos que tienen correlación < 0.50 con TODOS los ya seleccionados
                    candidatos_con_baja_corr = []
                    
                    for ticker in candidatos_disponibles:
                        todas_baja_corr = True
                        tiene_algunas_bajas = False
                        
                        for seleccionado in seleccionados:
                            try:
                                if seleccionado in returns.columns and ticker in returns.columns:
                                    corr = abs(returns[ticker].corr(returns[seleccionado]))
                                    if not np.isnan(corr):
                                        if corr >= umbral_correlacion_baja:
                                            # Si tiene alguna correlación >= 0.50, no cumple
                                            todas_baja_corr = False
                                            break
                                        elif corr < umbral_correlacion_baja:
                                            tiene_algunas_bajas = True
                                    else:
                                        # Si no hay datos de correlación, no cumple
                                        todas_baja_corr = False
                                        break
                            except:
                                todas_baja_corr = False
                                break
                        
                        # Solo incluir si tiene correlación < 0.50 con TODOS los seleccionados
                        if todas_baja_corr and tiene_algunas_bajas:
                            candidatos_con_baja_corr.append(ticker)
                    
                    # LUEGO: Si hay candidatos filtrados, seleccionar aleatoriamente de ellos
                    if candidatos_con_baja_corr:
                        random.shuffle(candidatos_con_baja_corr)
                        ticker_seleccionado = candidatos_con_baja_corr[0]
                        seleccionados.append(ticker_seleccionado)
                        candidatos_disponibles.remove(ticker_seleccionado)
                    else:
                        # Si no hay candidatos con correlación baja estricta, salir del loop
                        print(f"   ⚠️  No se encontraron más candidatos con correlación < {umbral_correlacion_baja} estricta")
                        break
                
                if len(seleccionados) >= 10:
                    print(f"   📊 Portafolio baja correlación (calculado, correlación < {umbral_correlacion:.0%} y R² < 50%):")
                    print(f"      Tickers seleccionados: {', '.join(seleccionados)}")
                    print(f"      Total candidatos filtrados: {len(candidatos_filtrados)}")
                    return seleccionados
                elif len(seleccionados) >= 2:
                    # Si tenemos al menos 2, pero menos de 5, intentar agregar más relajando el filtro
                    print(f"   ⚠️  Solo se encontraron {len(seleccionados)} activos con baja correlación estricta, relajando filtro...")
                    # Continuar agregando más candidatos sin el filtro estricto de R²
                    candidatos_restantes = [t for t in candidatos_filtrados if t not in seleccionados]
                    random.shuffle(candidatos_restantes)
                    while len(seleccionados) < 5 and candidatos_restantes:
                        ticker = candidatos_restantes.pop(0)
                        # Verificar solo correlación < 0.50 (sin R² estricto)
                        puede_agregar = True
                        correlaciones_altas = 0
                        for seleccionado in seleccionados:
                            try:
                                if seleccionado in returns.columns and ticker in returns.columns:
                                    corr = abs(returns[ticker].corr(returns[seleccionado]))
                                    if not np.isnan(corr) and corr >= umbral_correlacion:
                                        correlaciones_altas += 1
                                        if correlaciones_altas >= 2:
                                            puede_agregar = False
                                            break
                            except:
                                pass
                        if puede_agregar:
                            seleccionados.append(ticker)
                    if len(seleccionados) >= 10:
                        return seleccionados[:5]
                    elif len(seleccionados) >= 2:
                        # Si aún no llegamos a 5, usar candidatos filtrados para completar
                        candidatos_para_completar = [t for t in candidatos_filtrados if t not in seleccionados]
                        random.shuffle(candidatos_para_completar)
                        while len(seleccionados) < 5 and candidatos_para_completar:
                            seleccionados.append(candidatos_para_completar.pop(0))
                        return seleccionados[:10] if len(seleccionados) >= 10 else seleccionados
                else:
                    print(f"   ⚠️  No se encontraron suficientes activos con baja correlación estricta ({len(seleccionados)} encontrados)")
                    # Si no hay suficientes, usar los candidatos filtrados por correlación con base
                    if len(candidatos_filtrados) >= 10:
                        return candidatos_filtrados[:5]
                    elif len(candidatos_filtrados) >= 2:
                        # Completar hasta 5 con candidatos adicionales si es posible
                        return candidatos_filtrados
    
    # Fallback: selección aleatoria simple
    np.random.seed()
    seleccionados = np.random.choice(candidatos, size=min(n_restantes, len(candidatos)), replace=False).tolist()
    return portafolio + seleccionados


def construir_portafolio_correlacion_negativa(
    returns: pd.DataFrame = None,
    n_activos: int = NUM_ACTIVOS_PORTAFOLIO,
) -> List[str]:
    """
    Construye un portafolio de activos con correlaciones negativas fuertes entre sí.
    Extrae todos los activos con correlación negativa fuerte (<= -0.70) y selecciona aleatoriamente.
    
    Criterio: correlación <= -0.70 (valor absoluto >= 0.70 y signo negativo)
    
    NO incluye SPY y QQQ (solo están en el portafolio base).
    Garantiza que el portafolio tenga exactamente n_activos activos para ser comparable.
    """
    from config_tickers_factores import obtener_todos_tickers_sectores
    
    # NO incluir SPY y QQQ en este portafolio
    portafolio = []
    n_restantes = n_activos
    umbral_correlacion_negativa = -0.70  # Correlación negativa fuerte
    
    # Cargar matrices de correlación y R² desde JSON
    matriz_corr_json, matriz_r2_json = cargar_matriz_correlaciones_json()
    
    # Obtener TODOS los tickers desde series_historicas.json (solo USD, sin duplicados CEDEARs)
    todos_tickers = obtener_todos_tickers_desde_json(solo_usd=True)
    
    # Si no hay tickers en el JSON, usar fallback
    if not todos_tickers:
        todos_tickers = list(obtener_todos_tickers_sectores())
        print(f"   ⚠️  Usando fallback de config_tickers_factores: {len(todos_tickers)} tickers")
    
    todos_tickers = normalizar_tickers_duplicados(todos_tickers)
    print(f"   📊 Total de tickers disponibles (después de normalizar): {len(todos_tickers)}")
    
    # Excluir SPY y QQQ de los candidatos
    candidatos = [t for t in todos_tickers if t not in portafolio and t not in ["SPY", "QQQ"]]
    print(f"   📊 Candidatos después de excluir SPY/QQQ: {len(candidatos)}")
    
    # Si tenemos returns, filtrar candidatos que estén disponibles en returns
    if returns is not None and not returns.empty:
        candidatos = [t for t in candidatos if t in returns.columns]
        print(f"   📊 Candidatos disponibles en returns: {len(candidatos)}")
        
        if len(candidatos) < n_restantes:
            print(f"   ⚠️  Solo hay {len(candidatos)} candidatos disponibles, menos que los {n_restantes} requeridos")
            # Devolver los candidatos disponibles truncados a n_restantes
            return candidatos[:n_restantes]
        
        # Usar matriz de correlaciones del JSON si está disponible
        if matriz_corr_json:
            print(f"   🔍 Extrayendo activos con correlación negativa fuerte (<= {umbral_correlacion_negativa}) desde matriz JSON...")
            
            # PASO 1: Extraer TODOS los activos que tienen al menos una correlación negativa fuerte (<= -0.70)
            universo_corr_negativa = set()
            
            for ticker1 in matriz_corr_json:
                if ticker1 not in candidatos:
                    continue
                
                correlaciones_negativas_fuertes = []
                if isinstance(matriz_corr_json[ticker1], dict):
                    for ticker2, corr_val in matriz_corr_json[ticker1].items():
                        if ticker2 not in candidatos:
                            continue
                        
                        try:
                            corr = float(corr_val)
                            if not np.isnan(corr) and corr <= umbral_correlacion_negativa:
                                # Correlación negativa fuerte
                                universo_corr_negativa.add(ticker1)
                                universo_corr_negativa.add(ticker2)
                                correlaciones_negativas_fuertes.append((ticker2, corr))
                        except (ValueError, TypeError):
                            continue
                
                # También verificar en la dirección inversa
                for ticker2 in matriz_corr_json:
                    if ticker2 == ticker1 or ticker2 not in candidatos:
                        continue
                    if isinstance(matriz_corr_json.get(ticker2, {}), dict):
                        if ticker1 in matriz_corr_json[ticker2]:
                            try:
                                corr = float(matriz_corr_json[ticker2][ticker1])
                                if not np.isnan(corr) and corr <= umbral_correlacion_negativa:
                                    universo_corr_negativa.add(ticker1)
                                    universo_corr_negativa.add(ticker2)
                            except (ValueError, TypeError):
                                continue
            
            universo_lista = list(universo_corr_negativa)
            print(f"   ✅ Universo de activos con correlación negativa fuerte (<= {umbral_correlacion_negativa}): {len(universo_lista)} activos")
            
            if len(universo_lista) >= n_restantes:
                # PASO 2: Seleccionar aleatoriamente n_restantes activos del universo
                import random
                random.shuffle(universo_lista)
                seleccionados = universo_lista[:n_restantes]
                
                print(f"   📊 Portafolio correlación negativa fuerte (JSON) - {len(seleccionados)} activos seleccionados aleatoriamente:")
                print(f"      Activos: {', '.join(seleccionados)}")
                return seleccionados
            else:
                print(f"   ⚠️  Solo se encontraron {len(universo_lista)} activos con correlación negativa fuerte, menos que los {n_restantes} requeridos")
                if len(universo_lista) > 0:
                    # Devolver los que tenemos
                    return universo_lista
        
        # Si no hay JSON o no funcionó, usar correlaciones calculadas en tiempo real
        print(f"   🔍 Calculando correlaciones en tiempo real para extraer activos con correlación negativa fuerte (<= {umbral_correlacion_negativa})...")
        
        # PASO 1: Extraer TODOS los activos que tienen al menos una correlación negativa fuerte (<= -0.70)
        universo_corr_negativa = set()
        
        for i, ticker1 in enumerate(candidatos):
            if ticker1 not in returns.columns:
                continue
            
            correlaciones_negativas_fuertes = []
            for ticker2 in candidatos:
                if ticker2 == ticker1 or ticker2 not in returns.columns:
                    continue
                
                try:
                    corr = returns[ticker1].corr(returns[ticker2])
                    if not np.isnan(corr) and corr <= umbral_correlacion_negativa:
                        # Correlación negativa fuerte
                        universo_corr_negativa.add(ticker1)
                        universo_corr_negativa.add(ticker2)
                        correlaciones_negativas_fuertes.append((ticker2, corr))
                except Exception:
                    continue
        
        universo_lista = list(universo_corr_negativa)
        print(f"   ✅ Universo de activos con correlación negativa fuerte (<= {umbral_correlacion_negativa}): {len(universo_lista)} activos")
        
        if len(universo_lista) >= n_restantes:
            # PASO 2: Seleccionar aleatoriamente n_restantes activos del universo
            import random
            random.shuffle(universo_lista)
            seleccionados = universo_lista[:n_restantes]
            
            print(f"   📊 Portafolio correlación negativa fuerte (calculado) - {len(seleccionados)} activos seleccionados aleatoriamente:")
            print(f"      Activos: {', '.join(seleccionados)}")
            return seleccionados
        else:
            print(f"   ⚠️  Solo se encontraron {len(universo_lista)} activos con correlación negativa fuerte, menos que los {n_restantes} requeridos")
            if len(universo_lista) > 0:
                # Devolver los que tenemos
                return universo_lista
            else:
                # Si no hay ningún activo con correlación negativa fuerte, usar fallback
                print(f"   ⚠️  No se encontraron activos con correlación negativa fuerte, usando fallback")
                fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM", "ADBE", "ORCL", "CSCO", "INTC", "AMD"]
                fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
                fallback = [t for t in fallback if t in returns.columns]
                return fallback[:n_restantes]
    
    # Si no hay returns, usar fallback
    print(f"   ⚠️  No hay datos de returns disponibles, usando fallback")
    fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM", "ADBE", "ORCL", "CSCO", "INTC", "AMD"]
    fallback = [t for t in fallback if t not in portafolio and t not in ["SPY", "QQQ"]]
    return fallback[:n_restantes]
    
    # Si llegamos aquí, NO se pudo construir un portafolio que respete estrictamente la correlación negativa
    # con al menos MIN_ACTIVOS_CORRELACION activos. Devolvemos lista vacía para que el llamador
    # aplique un fallback (por ejemplo, una lista predefinida de tickers).
    print("   No se pudo construir un portafolio de correlación negativa que cumpla las reglas estrictas con el mínimo de activos requerido.")
    return []


def validar_y_filtrar_activos_por_correlacion(
    tickers: List[str],
    returns: pd.DataFrame,
    tipo_portafolio: str,
    umbral_minimo_activos: int = NUM_ACTIVOS_PORTAFOLIO,
) -> List[str]:
    """
    Valida y filtra activos según el criterio de correlación del portafolio.
    
    Estrategia mejorada:
    - Para "Alta Correlación": mantiene activos que tienen al menos 70% de sus pares con correlación >= 0.70
    - Para "Correlación Negativa": mantiene activos que tienen al menos 70% de sus pares con correlación <= -0.70
    - Prioriza mantener el mínimo requerido de activos para comparabilidad
    
    Args:
        tickers: Lista de tickers a validar
        returns: DataFrame con retornos históricos
        tipo_portafolio: "Alta Correlación" o "Correlación Negativa"
        umbral_minimo_activos: Mínimo de activos requeridos después del filtrado (por defecto NUM_ACTIVOS_PORTAFOLIO)
    
    Returns:
        Lista de tickers que cumplen el criterio de correlación (mínimo umbral_minimo_activos)
    """
    if not tickers or len(tickers) < 2:
        return tickers
    
    # Filtrar tickers que están en returns y tienen datos suficientes
    tickers_validos = []
    for t in tickers:
        if t in returns.columns:
            serie = returns[t].dropna()
            if len(serie) >= 10:  # Mínimo 10 días de datos para calcular correlación
                tickers_validos.append(t)
    
    if len(tickers_validos) < 2:
        print(f"   ⚠️  No hay suficientes tickers válidos en returns para validar correlación")
        return tickers_validos[:umbral_minimo_activos] if len(tickers_validos) > 0 else []
    
    # Determinar criterio según tipo de portafolio
    if "Alta Correlación" in tipo_portafolio:
        umbral_corr = 0.70
        criterio = lambda corr: abs(corr) >= umbral_corr if not np.isnan(corr) else False
        nombre_criterio = f"correlación >= {umbral_corr}"
    elif "Correlación Negativa" in tipo_portafolio:
        umbral_corr = -0.70
        criterio = lambda corr: corr <= umbral_corr if not np.isnan(corr) else False
        nombre_criterio = f"correlación <= {umbral_corr}"
    else:
        # Si no es un portafolio con criterio de correlación, devolver todos hasta el mínimo
        return tickers_validos[:umbral_minimo_activos] if len(tickers_validos) >= umbral_minimo_activos else tickers_validos
    
    # Calcular matriz de correlación
    returns_subset = returns[tickers_validos].dropna()
    if len(returns_subset) < 10:
        print(f"   ⚠️  No hay suficientes datos históricos para validar correlación")
        return tickers_validos[:umbral_minimo_activos] if len(tickers_validos) >= umbral_minimo_activos else tickers_validos
    
    corr_matrix = returns_subset.corr()
    
    # Calcular score para cada activo: porcentaje de pares que cumplen el criterio
    scores_activos = {}
    for ticker in tickers_validos:
        if ticker not in corr_matrix.columns:
            continue
        
        pares_validos = 0
        total_pares = 0
        
        for otro_ticker in tickers_validos:
            if otro_ticker == ticker or otro_ticker not in corr_matrix.columns:
                continue
            
            corr = corr_matrix.loc[ticker, otro_ticker]
            total_pares += 1
            if criterio(corr):
                pares_validos += 1
        
        if total_pares > 0:
            score = pares_validos / total_pares
            scores_activos[ticker] = score
    
    # Ordenar activos por score (mayor a menor)
    activos_ordenados = sorted(scores_activos.items(), key=lambda x: x[1], reverse=True)
    
    # Estrategia: mantener activos con mejor score hasta alcanzar el mínimo requerido
    # Luego, agregar más si cumplen al menos 70% del criterio
    activos_filtrados = []
    umbral_score_minimo = 0.70  # Al menos 70% de los pares deben cumplir el criterio
    
    # Primero: agregar activos que cumplen el umbral de score
    for ticker, score in activos_ordenados:
        if score >= umbral_score_minimo:
            activos_filtrados.append(ticker)
    
    # Si no alcanzamos el mínimo, agregar los mejores aunque no cumplan el 70%
    if len(activos_filtrados) < umbral_minimo_activos:
        print(f"   ⚠️  Solo {len(activos_filtrados)} activos cumplen el criterio estricto (>= {umbral_score_minimo*100:.0f}% de pares válidos)")
        print(f"      Agregando los mejores activos hasta alcanzar el mínimo de {umbral_minimo_activos} activos para comparabilidad")
        
        for ticker, score in activos_ordenados:
            if ticker not in activos_filtrados:
                activos_filtrados.append(ticker)
                if len(activos_filtrados) >= umbral_minimo_activos:
                    break
    
    # Asegurar que tenemos exactamente el mínimo requerido (o todos si hay menos)
    activos_filtrados = activos_filtrados[:umbral_minimo_activos] if len(activos_filtrados) >= umbral_minimo_activos else activos_filtrados
    activos_filtrados = sorted(activos_filtrados)
    
    # Calcular estadísticas finales
    if len(activos_filtrados) > 0:
        scores_finales = [scores_activos.get(t, 0) for t in activos_filtrados]
        score_promedio = np.mean(scores_finales) if scores_finales else 0
        
        print(f"   ✅ Filtrado por {nombre_criterio}: {len(activos_filtrados)} activos seleccionados")
        print(f"      Score promedio de cumplimiento: {score_promedio*100:.1f}%")
        print(f"      Activos seleccionados: {', '.join(activos_filtrados[:10])}{'...' if len(activos_filtrados) > 10 else ''}")
    
    return activos_filtrados


def mostrar_resumen_portafolio(
    resumen: PortfolioSummary,
    monto_inversion: float = 10000.0,
):
    """
    Imprime métricas clave del portafolio (pesos iguales), incluyendo
    escenarios de ganancia/pérdida ajustados por volatilidad (±1 desvío estándar).
    """
    print(f"\n{'='*80}")
    print(f"RESUMEN - {resumen.nombre}")
    print(f"{'='*80}")
    print(f"Activos: {', '.join(resumen.tickers)}")
    print(f"Retorno anual esperado: {resumen.mean_return_annual*100:6.2f}%")
    print(f"Volatilidad anual esperada: {resumen.volatility_annual*100:6.2f}%")
    # Comparar Sharpe bruto (sin tasa libre de riesgo) vs Sharpe ajustado (8% USD)
    if resumen.volatility_annual > 0:
        sharpe_bruto = resumen.mean_return_annual / resumen.volatility_annual
        sharpe_rf8 = (resumen.mean_return_annual - 0.08) / resumen.volatility_annual
    else:
        sharpe_bruto = 0.0
        sharpe_rf8 = 0.0
    print(f"Sharpe (sin RF):     {sharpe_bruto:5.2f}")
    print(f"Sharpe (RF 8% USD):  {sharpe_rf8:5.2f}")

    ganancia_esperada = resumen.mean_return_annual * monto_inversion
    print(f"\nPara una inversión de USD {monto_inversion:,.0f}:")
    if ganancia_esperada >= 0:
        print(f"   Ganancia esperada anual: USD {ganancia_esperada:,.0f}")
    else:
        print(f"   Pérdida esperada anual: USD {ganancia_esperada:,.0f}")

    # Escenarios ±1 desvío (ajustando retorno por volatilidad)
    # NOTA: Esta es una aproximación que asume distribución normal y retorno simple.
    # Para cálculos precisos de valor final, se debería usar capitalización compuesta.
    retorno_up = resumen.mean_return_annual + resumen.volatility_annual
    retorno_down = resumen.mean_return_annual - resumen.volatility_annual
    ganancia_up = retorno_up * monto_inversion
    perdida_down = retorno_down * monto_inversion

    print("\nEscenarios ajustados por volatilidad (±1 desvío):")
    print(
        f"   Escenario optimista (+1σ): Retorno ≈ {retorno_up*100:6.2f}%  "
        f"Ganancia/Pérdida ≈ USD {ganancia_up:,.0f}"
    )
    print(
        f"   Escenario pesimista (-1σ): Retorno ≈ {retorno_down*100:6.2f}% "
        f"Ganancia/Pérdida ≈ USD {perdida_down:,.0f}"
    )

    print("\nPesos utilizados (equally-weighted):")
    for t, w in resumen.weights.items():
        print(f"   {t:6s}: {w*100:5.1f}%")
    
    # Métricas de ganancia real usando simulación Monte Carlo (método empírico por defecto)
    print("\n" + "="*80)
    print("🎲 GANANCIA ESPERADA MÁS PROBABLE (Simulación Monte Carlo - Bootstrapping Empírico)")
    print("="*80)
    print("   Método: Bootstrapping de retornos históricos reales del portafolio")
    metricas_ganancia = obtener_metricas_ganancia_real(resumen, capital=monto_inversion, n=5000, metodo='empirico')
    
    print(f"\nPara una inversión de USD {monto_inversion:,.0f}:")
    print(f"   Ganancia media (esperada):     USD {metricas_ganancia['ganancia_media']:,.0f}")
    print(f"   Ganancia mediana (típica):     USD {metricas_ganancia['ganancia_mediana']:,.0f}")
    print(f"   Ganancia moda (más probable):  USD {metricas_ganancia['ganancia_moda']:,.0f}")
    print(f"   Desviación estándar:           USD {metricas_ganancia['ganancia_std']:,.0f}")
    
    # Intervalo de confianza 95%
    ic = metricas_ganancia['intervalo_confianza_95']
    print(f"\n   Intervalo de confianza 95%:   USD {ic[0]:,.0f} a USD {ic[1]:,.0f}")
    
    # Percentiles
    print(f"\n   Percentiles:")
    print(f"      5% (peor escenario):        USD {metricas_ganancia['percentil_5']:,.0f}")
    print(f"      25%:                         USD {metricas_ganancia['percentil_25']:,.0f}")
    print(f"      75%:                         USD {metricas_ganancia['percentil_75']:,.0f}")
    print(f"      95% (mejor escenario):       USD {metricas_ganancia['percentil_95']:,.0f}")
    
    # VaR y CVaR
    print(f"\n   Métricas de riesgo:")
    print(f"      VaR 5% (pérdida máxima esperada): USD {metricas_ganancia['var_5']:,.0f}")
    print(f"      CVaR 5% (pérdida esperada en cola): USD {metricas_ganancia['cvar_5']:,.0f}")
    
    print(f"\n   Probabilidad de ganar:        {metricas_ganancia['prob_ganar']*100:.1f}%")
    print(f"   Probabilidad de perder:        {metricas_ganancia['prob_perder']*100:.1f}%")


def mostrar_resultados_markowitz(
    nombre: str,
    portfolios_df: pd.DataFrame,
    max_sharpe_pf: pd.Series,
    min_vol_pf: pd.Series,
    returns_subset: pd.DataFrame,
    monto_inversion: float = 10000.0,
):
    """
    Imprime comparación de portafolios optimizados (máximo Sharpe y mínima volatilidad).
    """
    print(f"\n{'-'*80}")
    print(f"🧮 OPTIMIZACIÓN DE MARKOWITZ - {nombre} (1500 simulaciones)")
    print(f"{'-'*80}")
    print(f"Total de portafolios simulados: {len(portfolios_df)}")

    # Máximo Sharpe
    r_ms = max_sharpe_pf["Return"]
    v_ms = max_sharpe_pf["Volatility"]
    s_ms = max_sharpe_pf["Sharpe"]
    g_ms = r_ms * monto_inversion
    # Escenarios ±1σ
    r_ms_up = r_ms + v_ms
    r_ms_down = r_ms - v_ms
    g_ms_up = r_ms_up * monto_inversion
    g_ms_down = r_ms_down * monto_inversion

    print("\n👉 Portafolio de Máximo Sharpe:")
    print(f"   Retorno anual esperado: {r_ms*100:6.2f}%")
    print(f"   Volatilidad anual:      {v_ms*100:6.2f}%")
    print(f"   Sharpe Ratio:           {s_ms:5.2f}")
    print(f"   Ganancia/Pérdida esperada (USD {monto_inversion:,.0f}): {g_ms:,.0f}")
    print(
        f"   Escenario optimista (+1σ): Retorno ≈ {r_ms_up*100:6.2f}%, "
        f"Ganancia/Pérdida ≈ USD {g_ms_up:,.0f}"
    )
    print(
        f"   Escenario pesimista (-1σ): Retorno ≈ {r_ms_down*100:6.2f}%, "
        f"Ganancia/Pérdida ≈ USD {g_ms_down:,.0f}"
    )

    # Mínima volatilidad
    r_mv = min_vol_pf["Return"]
    v_mv = min_vol_pf["Volatility"]
    s_mv = min_vol_pf["Sharpe"]
    g_mv = r_mv * monto_inversion
    # Escenarios ±1σ
    r_mv_up = r_mv + v_mv
    r_mv_down = r_mv - v_mv
    g_mv_up = r_mv_up * monto_inversion
    g_mv_down = r_mv_down * monto_inversion

    print("\n👉 Portafolio de Mínima Volatilidad:")
    print(f"   Retorno anual esperado: {r_mv*100:6.2f}%")
    print(f"   Volatilidad anual:      {v_mv*100:6.2f}%")
    print(f"   Sharpe Ratio:           {s_mv:5.2f}")
    print(f"   Ganancia/Pérdida esperada (USD {monto_inversion:,.0f}): {g_mv:,.0f}")
    print(
        f"   Escenario optimista (+1σ): Retorno ≈ {r_mv_up*100:6.2f}%, "
        f"Ganancia/Pérdida ≈ USD {g_mv_up:,.0f}"
    )
    print(
        f"   Escenario pesimista (-1σ): Retorno ≈ {r_mv_down*100:6.2f}%, "
        f"Ganancia/Pérdida ≈ USD {g_mv_down:,.0f}"
    )

    # Mostrar pesos de cada portafolio (solo columnas Weight_)
    weight_cols = [c for c in portfolios_df.columns if c.startswith("Weight_")]

    def _mostrar_pesos(label: str, serie: pd.Series):
        print(f"\n   Composición - {label}:")
        for col in weight_cols:
            w = serie.get(col, 0.0)
            if w > 0.001:
                ticker = col.replace("Weight_", "")
                print(f"      {ticker:6s}: {w*100:5.1f}%")

    _mostrar_pesos("Máximo Sharpe", max_sharpe_pf)
    _mostrar_pesos("Mínima Volatilidad", min_vol_pf)

    # Métricas de ganancia real usando simulación Monte Carlo (método empírico por defecto)
    print("\n" + "="*80)
    print("🎲 GANANCIA ESPERADA MÁS PROBABLE (Simulación Monte Carlo - Bootstrapping Empírico)")
    print("="*80)
    print("   Método: Bootstrapping de retornos históricos reales del portafolio")
    
    # Crear PortfolioSummary temporales para los portafolios optimizados
    weight_cols = [c for c in portfolios_df.columns if c.startswith("Weight_")]
    tickers_ms = [col.replace("Weight_", "") for col in weight_cols if max_sharpe_pf.get(col, 0.0) > 0.001]
    tickers_mv = [col.replace("Weight_", "") for col in weight_cols if min_vol_pf.get(col, 0.0) > 0.001]
    
    # Filtrar tickers que están disponibles en returns_subset
    tickers_ms_validos = [t for t in tickers_ms if t in returns_subset.columns] if not returns_subset.empty else []
    tickers_mv_validos = [t for t in tickers_mv if t in returns_subset.columns] if not returns_subset.empty else []
    
    # Calcular pesos normalizados solo para tickers válidos
    weights_ms_raw = {col.replace("Weight_", ""): max_sharpe_pf.get(col, 0.0) for col in weight_cols if max_sharpe_pf.get(col, 0.0) > 0.001}
    weights_mv_raw = {col.replace("Weight_", ""): min_vol_pf.get(col, 0.0) for col in weight_cols if min_vol_pf.get(col, 0.0) > 0.001}
    
    # Normalizar pesos para tickers válidos
    if tickers_ms_validos:
        total_weight_ms = sum(weights_ms_raw.get(t, 0.0) for t in tickers_ms_validos)
        weights_ms = {t: weights_ms_raw.get(t, 0.0) / total_weight_ms if total_weight_ms > 0 else 0.0 
                     for t in tickers_ms_validos}
    else:
        weights_ms = {}
    
    if tickers_mv_validos:
        total_weight_mv = sum(weights_mv_raw.get(t, 0.0) for t in tickers_mv_validos)
        weights_mv = {t: weights_mv_raw.get(t, 0.0) / total_weight_mv if total_weight_mv > 0 else 0.0 
                     for t in tickers_mv_validos}
    else:
        weights_mv = {}
    
    # Calcular returns_df para cada portafolio optimizado usando los pesos optimizados
    if tickers_ms_validos and not returns_subset.empty:
        returns_ms = returns_subset[tickers_ms_validos].copy()
    else:
        returns_ms = pd.DataFrame()
    
    if tickers_mv_validos and not returns_subset.empty:
        returns_mv = returns_subset[tickers_mv_validos].copy()
    else:
        returns_mv = pd.DataFrame()
    
    # PortfolioSummary para Máximo Sharpe
    summary_ms = PortfolioSummary(
        nombre=f"{nombre} - Máximo Sharpe",
        tickers=tickers_ms_validos if tickers_ms_validos else tickers_ms,
        returns_df=returns_ms,
        mean_return_annual=r_ms,
        volatility_annual=v_ms,
        sharpe_ratio=s_ms,
        weights=weights_ms if weights_ms else weights_ms_raw
    )
    
    # PortfolioSummary para Mínima Volatilidad
    summary_mv = PortfolioSummary(
        nombre=f"{nombre} - Mínima Volatilidad",
        tickers=tickers_mv_validos if tickers_mv_validos else tickers_mv,
        returns_df=returns_mv,
        mean_return_annual=r_mv,
        volatility_annual=v_mv,
        sharpe_ratio=s_mv,
        weights=weights_mv if weights_mv else weights_mv_raw
    )
    
    # Calcular métricas de ganancia real usando método empírico
    # Verificar que tenemos datos suficientes para simulación empírica
    if not returns_ms.empty and len(tickers_ms_validos) > 0:
        print(f"   📊 Simulando Máximo Sharpe con método empírico ({len(returns_ms)} días históricos)")
        metricas_ms = obtener_metricas_ganancia_real(summary_ms, capital=monto_inversion, n=5000, metodo='empirico')
    else:
        print(f"   ⚠️  Usando método paramétrico para Máximo Sharpe (sin datos históricos suficientes)")
        metricas_ms = obtener_metricas_ganancia_real(summary_ms, capital=monto_inversion, n=5000, metodo='parametrico')
    
    if not returns_mv.empty and len(tickers_mv_validos) > 0:
        print(f"   📊 Simulando Mínima Volatilidad con método empírico ({len(returns_mv)} días históricos)")
        metricas_mv = obtener_metricas_ganancia_real(summary_mv, capital=monto_inversion, n=5000, metodo='empirico')
    else:
        print(f"   ⚠️  Usando método paramétrico para Mínima Volatilidad (sin datos históricos suficientes)")
        metricas_mv = obtener_metricas_ganancia_real(summary_mv, capital=monto_inversion, n=5000, metodo='parametrico')
    
    print(f"\n👉 Portafolio de Máximo Sharpe (USD {monto_inversion:,.0f}):")
    print(f"   Ganancia media (esperada):     USD {metricas_ms['ganancia_media']:,.0f}")
    print(f"   Ganancia mediana (típica):     USD {metricas_ms['ganancia_mediana']:,.0f}")
    print(f"   Ganancia moda (más probable):  USD {metricas_ms['ganancia_moda']:,.0f}")
    print(f"   Desviación estándar:           USD {metricas_ms['ganancia_std']:,.0f}")
    
    # Intervalo de confianza 95%
    ic_ms = metricas_ms['intervalo_confianza_95']
    print(f"   Intervalo de confianza 95%:   USD {ic_ms[0]:,.0f} a USD {ic_ms[1]:,.0f}")
    
    # Percentiles y métricas de riesgo
    print(f"   Percentil 5% (peor):           USD {metricas_ms['percentil_5']:,.0f}")
    print(f"   Percentil 95% (mejor):         USD {metricas_ms['percentil_95']:,.0f}")
    print(f"   VaR 5%:                        USD {metricas_ms['var_5']:,.0f}")
    print(f"   CVaR 5%:                       USD {metricas_ms['cvar_5']:,.0f}")
    print(f"   Probabilidad de ganar:         {metricas_ms['prob_ganar']*100:.1f}%")
    print(f"   Probabilidad de perder:        {metricas_ms['prob_perder']*100:.1f}%")
    
    print(f"\n👉 Portafolio de Mínima Volatilidad (USD {monto_inversion:,.0f}):")
    print(f"   Ganancia media (esperada):     USD {metricas_mv['ganancia_media']:,.0f}")
    print(f"   Ganancia mediana (típica):     USD {metricas_mv['ganancia_mediana']:,.0f}")
    print(f"   Ganancia moda (más probable):  USD {metricas_mv['ganancia_moda']:,.0f}")
    print(f"   Desviación estándar:           USD {metricas_mv['ganancia_std']:,.0f}")
    
    # Intervalo de confianza 95%
    ic_mv = metricas_mv['intervalo_confianza_95']
    print(f"   Intervalo de confianza 95%:   USD {ic_mv[0]:,.0f} a USD {ic_mv[1]:,.0f}")
    
    # Percentiles y métricas de riesgo
    print(f"   Percentil 5% (peor):           USD {metricas_mv['percentil_5']:,.0f}")
    print(f"   Percentil 95% (mejor):         USD {metricas_mv['percentil_95']:,.0f}")
    print(f"   VaR 5%:                        USD {metricas_mv['var_5']:,.0f}")
    print(f"   CVaR 5%:                       USD {metricas_mv['cvar_5']:,.0f}")
    print(f"   Probabilidad de ganar:         {metricas_mv['prob_ganar']*100:.1f}%")
    print(f"   Probabilidad de perder:        {metricas_mv['prob_perder']*100:.1f}%")

    # Métricas por activo dentro del portafolio de mínima varianza
    if not returns_subset.empty and weight_cols:
        print(f"\n📌 Detalle por activo en el Portafolio de Mínima Volatilidad:")
        annual_trading_days = 252
        filas = []
        for col in weight_cols:
            w = min_vol_pf.get(col, 0.0)
            if w <= 0.001:
                continue
            ticker = col.replace("Weight_", "")
            if ticker not in returns_subset.columns:
                continue
            serie = returns_subset[ticker].dropna()
            if len(serie) < 20:
                continue
            mean_daily = serie.mean()
            std_daily = serie.std()
            mean_annual = mean_daily * annual_trading_days
            vol_annual = std_daily * (annual_trading_days ** 0.5)
            filas.append(
                {
                    "ticker": ticker,
                    "peso_%": w * 100,
                    "retorno_anual_%": mean_annual * 100,
                    "volatilidad_anual_%": vol_annual * 100,
                }
            )
        if filas:
            df_detalle = pd.DataFrame(filas).round(2)
            print(df_detalle.to_string(index=False))


def mostrar_metricas_individuales(
    nombre: str,
    returns: pd.DataFrame,
):
    """
    Muestra métricas individuales de cada activo dentro del portafolio:
    - Retorno anual esperado
    - Volatilidad anual
    - Correlación entre activos
    """
    annual_trading_days = 252
    print(f"\n{'-'*80}")
    print(f"📌 MÉTRICAS INDIVIDUALES - {nombre}")
    print(f"{'-'*80}")

    resumen_rows = []
    for t in returns.columns:
        serie = returns[t].dropna()
        if len(serie) < 20:
            continue
        mean_daily = serie.mean()
        std_daily = serie.std()
        mean_annual = mean_daily * annual_trading_days
        vol_annual = std_daily * (annual_trading_days ** 0.5)
        resumen_rows.append(
            {
                "ticker": t,
                "retorno_anual": mean_annual,
                "volatilidad_anual": vol_annual,
            }
        )

    if resumen_rows:
        df_resumen = pd.DataFrame(resumen_rows)
        df_resumen["retorno_anual_%"] = df_resumen["retorno_anual"] * 100
        df_resumen["volatilidad_anual_%"] = df_resumen["volatilidad_anual"] * 100
        print("\nMétricas por activo (anualizadas):")
        print(
            df_resumen[
                ["ticker", "retorno_anual_%", "volatilidad_anual_%"]
            ].round(2).to_string(index=False)
        )

    if returns.shape[1] >= 2:
        print("\nMatriz de correlaciones entre activos:")
        print(returns.corr().round(2).to_string())


def main():
    # Parámetros globales - PERÍODO FIJO DE 5 AÑOS
    periodo_precios = "5y"  # Siempre 5 años para mejores datos y resultados
    periodo_metricas_div = "5y"  # Siempre 5 años
    risk_free_rate = 0.08  # 8% en USD
    monto_inversion = 10000.0

    # 0) Actualizar series históricas hasta hoy para backtesting consistente
    # Nota: La función descargar_precios_activos ahora gestiona el JSON único automáticamente
    print("\n=== ACTUALIZANDO SERIES HISTÓRICAS ===")
    print("📥 Las series se descargarán/actualizarán automáticamente cuando se necesiten...")
    print("   Archivo único: series_historicas.json (período: 5 años)")

    # 1) Definir portafolios
    # Portafolio "sin diversificación": solo SPY y QQQ a partes iguales
    port_spy_qqq = ["SPY", "QQQ"]

    # Portafolio de alta correlación - se construirá después de tener returns
    # Por ahora solo definimos que necesitamos NUM_ACTIVOS_PORTAFOLIO
    n_activos_objetivo = NUM_ACTIVOS_PORTAFOLIO

    # 2) Descargar precios primero para poder calcular correlaciones reales
    print("\n=== DESCARGANDO UNIVERSO COMPLETO ===")
    print("📥 Obteniendo todos los tickers de todos los sectores...")
    
    # Obtener todos los tickers de todos los sectores (prioriza series_historicas.json)
    todos_tickers_universo = set()
    sectores_disponibles = list(SECTOR_TICKERS_EN.keys())
    
    for sector in sectores_disponibles:
        tickers_sector = obtener_tickers_sector(sector, usar_series_json=True)
        if tickers_sector:
            todos_tickers_universo.update(tickers_sector)
            print(f"   ✅ {sector}: {len(tickers_sector)} tickers")
    
    # Agregar SPY y QQQ si no están
    todos_tickers_universo.add("SPY")
    todos_tickers_universo.add("QQQ")
    
    # Agregar factores de diversificación
    todos_tickers_universo.update(FACTORES_DIVERSIFICACION.keys())
    
    universo_completo = sorted(list(todos_tickers_universo))
    print(f"\n📊 UNIVERSO COMPLETO: {len(universo_completo)} tickers únicos")
    print(f"   Ejemplos: {', '.join(universo_completo[:10])}...")
    
    # Descargar precios para TODO el universo
    print(f"\n📥 Descargando precios para el universo completo...")
    df_precios = descargar_precios_activos(universo_completo, periodo=periodo_precios)

    if df_precios.empty:
        print("❌ No hay datos de precios descargados.")
        return

    returns = calcular_retornos(df_precios)

    # Asegurar que SPY y QQQ estén presentes
    if "SPY" not in returns.columns or "QQQ" not in returns.columns:
        print("❌ Los retornos no contienen columnas SPY y QQQ. Revisa la descarga de datos.")
        return

    # Construir portafolios después de tener returns (selección aleatoria basada en correlaciones)
    print("\n📊 Construyendo portafolios con selección aleatoria basada en correlaciones y R²...")
    
    # Portafolio de alta correlación (5 activos)
    port_alta_corr = construir_portafolio_alta_correlacion(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO,
    )
    
    # Portafolio de alta correlación extendido (10 activos)
    port_alta_corr_ext = construir_portafolio_alta_correlacion(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO,
    )
    
    # Portafolio de baja correlación (5 activos)
    port_baja_corr = construir_portafolio_baja_correlacion(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO,
    )
    
    # Portafolio de baja correlación extendido (10 activos)
    port_baja_corr_ext = construir_portafolio_baja_correlacion(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO,
    )
    
    # Portafolio de alta volatilidad y sesgo positivo (colas a la derecha)
    port_alta_vol_sesgo = construir_portafolio_alta_volatilidad_sesgo_positivo(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO,
        percentil_volatilidad=0.75,  # Top 25% de volatilidad
        sesgo_minimo=0.0,  # Sesgo positivo
    )

    print("\n=== DEFINICIÓN DE PORTAFOLIOS ===")
    print(f"Portafolio 1 - Sin diversificación (SPY/QQQ): {', '.join(port_spy_qqq)}")
    print(f"Portafolio 2 - Alta correlación ({NUM_ACTIVOS_PORTAFOLIO} activos): {', '.join(port_alta_corr)} (Total: {len(port_alta_corr)} tickers)")
    print(f"Portafolio 2b - Alta correlación extendido ({NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO} activos): {', '.join(port_alta_corr_ext)} (Total: {len(port_alta_corr_ext)} tickers)")
    print(f"Portafolio 3 - Baja correlación ({NUM_ACTIVOS_PORTAFOLIO} activos): {', '.join(port_baja_corr)} (Total: {len(port_baja_corr)} tickers)")
    print(f"Portafolio 3b - Baja correlación extendido ({NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO} activos): {', '.join(port_baja_corr_ext)} (Total: {len(port_baja_corr_ext)} tickers)")
    print(f"Portafolio 4 - Alta volatilidad y sesgo positivo ({NUM_ACTIVOS_PORTAFOLIO} activos): {', '.join(port_alta_vol_sesgo)} (Total: {len(port_alta_vol_sesgo)} tickers)")
    
    # Validar que los tickers estén en returns
    port_alta_corr_en_returns = [t for t in port_alta_corr if t in returns.columns]
    port_baja_corr_en_returns = [t for t in port_baja_corr if t in returns.columns]
    
    if len(port_alta_corr_en_returns) != len(port_alta_corr):
        print(f"⚠️  ADVERTENCIA: Portafolio alta correlación tiene {len(port_alta_corr) - len(port_alta_corr_en_returns)} tickers no disponibles en returns")
        print(f"   Tickers no disponibles: {[t for t in port_alta_corr if t not in returns.columns]}")
        port_alta_corr = port_alta_corr_en_returns
    
    if len(port_baja_corr_en_returns) != len(port_baja_corr):
        print(f"⚠️  ADVERTENCIA: Portafolio baja correlación tiene {len(port_baja_corr) - len(port_baja_corr_en_returns)} tickers no disponibles en returns")
        print(f"   Tickers no disponibles: {[t for t in port_baja_corr if t not in returns.columns]}")
        port_baja_corr = port_baja_corr_en_returns
    
    # Validar también las versiones extendidas
    port_alta_corr_ext_en_returns = [t for t in port_alta_corr_ext if t in returns.columns]
    port_baja_corr_ext_en_returns = [t for t in port_baja_corr_ext if t in returns.columns]
    
    if len(port_alta_corr_ext_en_returns) != len(port_alta_corr_ext):
        print(f"⚠️  ADVERTENCIA: Portafolio alta correlación extendido tiene {len(port_alta_corr_ext) - len(port_alta_corr_ext_en_returns)} tickers no disponibles en returns")
        port_alta_corr_ext = port_alta_corr_ext_en_returns
    
    if len(port_baja_corr_ext_en_returns) != len(port_baja_corr_ext):
        print(f"⚠️  ADVERTENCIA: Portafolio baja correlación extendido tiene {len(port_baja_corr_ext) - len(port_baja_corr_ext_en_returns)} tickers no disponibles en returns")
        port_baja_corr_ext = port_baja_corr_ext_en_returns
    
    # Validar portafolio de alta volatilidad y sesgo positivo
    port_alta_vol_sesgo_en_returns = [t for t in port_alta_vol_sesgo if t in returns.columns]
    if len(port_alta_vol_sesgo_en_returns) != len(port_alta_vol_sesgo):
        print(f"⚠️  ADVERTENCIA: Portafolio alta volatilidad y sesgo positivo tiene {len(port_alta_vol_sesgo) - len(port_alta_vol_sesgo_en_returns)} tickers no disponibles en returns")
        port_alta_vol_sesgo = port_alta_vol_sesgo_en_returns
    
    if len(port_alta_vol_sesgo) < 30:
        print(f"⚠️  ADVERTENCIA: Portafolio alta volatilidad y sesgo positivo tiene solo {len(port_alta_vol_sesgo)} activos, se requiere mínimo 30")
    
    # NO agregar SPY y QQQ a los otros portafolios (solo están en el base)
    # Asegurar que tengan mínimo 30 activos
    if len(port_alta_corr) < 30:
        print(f"⚠️  ADVERTENCIA: Portafolio alta correlación tiene solo {len(port_alta_corr)} activos, se requiere mínimo 30")
    if len(port_baja_corr) < 30:
        print(f"⚠️  ADVERTENCIA: Portafolio baja correlación tiene solo {len(port_baja_corr)} activos, se requiere mínimo 30")
    if len(port_alta_corr_ext) < 60:
        print(f"⚠️  ADVERTENCIA: Portafolio alta correlación extendido tiene solo {len(port_alta_corr_ext)} activos, se requiere 60")
    if len(port_baja_corr_ext) < 60:
        print(f"⚠️  ADVERTENCIA: Portafolio baja correlación extendido tiene solo {len(port_baja_corr_ext)} activos, se requiere 60")
    
    print(f"\n✅ Portafolios validados (SIN SPY/QQQ):")
    print(f"   Alta correlación (30): {', '.join(port_alta_corr)} ({len(port_alta_corr)} tickers)")
    print(f"   Alta correlación (60): {', '.join(port_alta_corr_ext)} ({len(port_alta_corr_ext)} tickers)")
    print(f"   Baja correlación (30): {', '.join(port_baja_corr)} ({len(port_baja_corr)} tickers)")
    print(f"   Baja correlación (60): {', '.join(port_baja_corr_ext)} ({len(port_baja_corr_ext)} tickers)")
    print(f"   Alta volatilidad y sesgo positivo (30): {', '.join(port_alta_vol_sesgo)} ({len(port_alta_vol_sesgo)} tickers)")

    # 3) Métricas SPY vs QQQ
    metricas_spy_qqq = calcular_metricas_spy_qqq(returns, risk_free_rate=risk_free_rate)
    print("\n=== MÉTRICAS SPY vs QQQ (regresión CAPM diaria) ===")
    for etiqueta, m in metricas_spy_qqq.items():
        if not m:
            continue
        print(f"\n{etiqueta}:")
        print(f"   Correlación: {m.get('correlacion', 0.0):.3f}")
        print(f"   Beta:        {m.get('beta', 0.0):.3f}")
        alpha_anual = m.get('alpha_anual', 0.0)
        print(f"   Alpha anual: {alpha_anual*100:6.2f}%")
        print(f"   R²:          {m.get('r_squared', 0.0):.3f}")

    # 4) Portafolio SPY/QQQ - PRIMERO SIN OPTIMIZACIÓN (pesos iguales)
    print("\n" + "="*80)
    print("📊 PASO 1: PORTAFOLIO SPY+QQQ (Composición Global)")
    print("="*80)
    resumen_spy_qqq = resumen_portafolio_equally_weighted(
        nombre="SPY + QQQ",
        tickers=port_spy_qqq,
        returns=returns,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resumen_portafolio(resumen_spy_qqq, monto_inversion=monto_inversion)
    mostrar_metricas_individuales("Portafolio SPY+QQQ", returns[resumen_spy_qqq.tickers])
    
    # 5) Portafolio SPY/QQQ - LUEGO OPTIMIZADO (Markowitz)
    print("\n" + "="*80)
    print("📊 PASO 2: PORTAFOLIO SPY+QQQ OPTIMIZADO (Markowitz)")
    print("="*80)

    pf_spy_qqq_df, pf_spy_qqq_ms, pf_spy_qqq_mv = simular_portafolios_markowitz(
        returns[resumen_spy_qqq.tickers],
        num_portfolios=5000,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resultados_markowitz(
        "Portafolio SPY+QQQ",
        pf_spy_qqq_df,
        pf_spy_qqq_ms,
        pf_spy_qqq_mv,
        returns[resumen_spy_qqq.tickers],
        monto_inversion=monto_inversion,
    )

    # 6) Portafolio alta correlación - COMPARACIÓN
    print("\n" + "="*80)
    print("📊 PASO 3: COMPARACIÓN CON PORTAFOLIO ALTA CORRELACIÓN")
    print("="*80)
    # Filtrar tickers que realmente están en returns
    port_alta_corr_validos = [t for t in port_alta_corr if t in returns.columns]
    if len(port_alta_corr_validos) != len(port_alta_corr):
        print(f"⚠️  Advertencia: {len(port_alta_corr) - len(port_alta_corr_validos)} tickers de alta correlación no están en returns")
        print(f"   Tickers originales: {port_alta_corr}")
        print(f"   Tickers válidos: {port_alta_corr_validos}")
    
    # VALIDAR Y FILTRAR activos por criterio de correlación ANTES de optimizar
    print(f"\n   🔍 Validando activos por criterio de correlación alta (>= 0.70)...")
    port_alta_corr_validos = validar_y_filtrar_activos_por_correlacion(
        tickers=port_alta_corr_validos,
        returns=returns,
        tipo_portafolio="Alta Correlación",
        umbral_minimo_activos=NUM_ACTIVOS_PORTAFOLIO,
    )
    
    if len(port_alta_corr_validos) < NUM_ACTIVOS_PORTAFOLIO:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_alta_corr_validos)} activos válidos para alta correlación")
        print(f"   Se requieren {NUM_ACTIVOS_PORTAFOLIO} activos para comparabilidad. Completando con los mejores disponibles...")
        # Completar con los mejores activos disponibles que no estén ya en el portafolio
        todos_disponibles = [t for t in returns.columns if t not in ["SPY", "QQQ"] and t not in port_alta_corr_validos]
        if len(todos_disponibles) > 0:
            necesarios = NUM_ACTIVOS_PORTAFOLIO - len(port_alta_corr_validos)
            port_alta_corr_validos.extend(todos_disponibles[:necesarios])
    
    # Asegurar exactamente NUM_ACTIVOS_PORTAFOLIO activos
    port_alta_corr_validos = port_alta_corr_validos[:NUM_ACTIVOS_PORTAFOLIO]
    
    if len(port_alta_corr_validos) < 2:
        print(f"❌ Error: No se pueden construir portafolios de alta correlación con los datos disponibles")
        return
    
    resumen_high = resumen_portafolio_equally_weighted(
        nombre="Alta Correlación",
        tickers=port_alta_corr_validos,
        returns=returns,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resumen_portafolio(resumen_high, monto_inversion=monto_inversion)

    pf_high_df, pf_high_ms, pf_high_mv = simular_portafolios_markowitz(
        returns[resumen_high.tickers],
        num_portfolios=5000,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resultados_markowitz(
        "Alta Correlación (Optimizado)",
        pf_high_df,
        pf_high_ms,
        pf_high_mv,
        returns[resumen_high.tickers],
        monto_inversion=monto_inversion,
    )
    mostrar_metricas_individuales(
        "Alta Correlación", returns[resumen_high.tickers]
    )

    # 7) Portafolio baja correlación - COMPARACIÓN
    print("\n" + "="*80)
    print("📊 PASO 4: COMPARACIÓN CON PORTAFOLIO BAJA CORRELACIÓN (Diversificado)")
    print("="*80)
    # Filtrar tickers que realmente están en returns
    port_baja_corr_validos = [t for t in port_baja_corr if t in returns.columns]
    if len(port_baja_corr_validos) != len(port_baja_corr):
        print(f"⚠️  Advertencia: {len(port_baja_corr) - len(port_baja_corr_validos)} tickers de baja correlación no están en returns")
        print(f"   Tickers originales: {port_baja_corr}")
        print(f"   Tickers válidos: {port_baja_corr_validos}")
    
    # Asegurar que tenga exactamente NUM_ACTIVOS_PORTAFOLIO activos para comparabilidad
    if len(port_baja_corr_validos) < NUM_ACTIVOS_PORTAFOLIO:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_baja_corr_validos)} activos válidos, completando hasta {NUM_ACTIVOS_PORTAFOLIO}...")
        fallback = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX", "AVGO", "CRM",
                    "ADBE", "ORCL", "CSCO", "INTC", "AMD", "NKE", "DIS", "V", "MA", "JPM",
                    "WMT", "HD", "MCD", "VZ", "T", "XOM", "CVX", "BAC", "C", "GS"]
        extras = [t for t in fallback if t in returns.columns and t not in ["SPY", "QQQ"] and t not in port_baja_corr_validos]
        necesarios = NUM_ACTIVOS_PORTAFOLIO - len(port_baja_corr_validos)
        port_baja_corr_validos.extend(extras[:necesarios])
    
    # Asegurar exactamente NUM_ACTIVOS_PORTAFOLIO activos (truncar si hay más)
    port_baja_corr_validos = port_baja_corr_validos[:NUM_ACTIVOS_PORTAFOLIO]
    
    if len(port_baja_corr_validos) != NUM_ACTIVOS_PORTAFOLIO:
        print(f"⚠️  Advertencia: Portafolio baja correlación tiene {len(port_baja_corr_validos)} activos en lugar de {NUM_ACTIVOS_PORTAFOLIO}")
    
    resumen_low = resumen_portafolio_equally_weighted(
        nombre="Baja Correlación",
        tickers=port_baja_corr_validos,
        returns=returns,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resumen_portafolio(resumen_low, monto_inversion=monto_inversion)

    pf_low_df, pf_low_ms, pf_low_mv = simular_portafolios_markowitz(
        returns[resumen_low.tickers],
        num_portfolios=5000,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resultados_markowitz(
        "Baja Correlación (Optimizado)",
        pf_low_df,
        pf_low_ms,
        pf_low_mv,
        returns[resumen_low.tickers],
        monto_inversion=monto_inversion,
    )
    mostrar_metricas_individuales(
        "Baja Correlación", returns[resumen_low.tickers]
    )

    # 8) Portafolio alta correlación EXTENDIDO (10 activos) - COMPARACIÓN
    print("\n" + "="*80)
    print("📊 PASO 5: COMPARACIÓN CON PORTAFOLIO ALTA CORRELACIÓN EXTENDIDO (10 activos)")
    print("="*80)
    port_alta_corr_ext_validos = [t for t in port_alta_corr_ext if t in returns.columns]
    if len(port_alta_corr_ext_validos) != len(port_alta_corr_ext):
        print(f"⚠️  Advertencia: {len(port_alta_corr_ext) - len(port_alta_corr_ext_validos)} tickers de alta correlación extendido no están en returns")
        port_alta_corr_ext = port_alta_corr_ext_validos
    
    # VALIDAR Y FILTRAR activos por criterio de correlación alta ANTES de optimizar
    print(f"\n   🔍 Validando activos extendidos por criterio de correlación alta (>= 0.70)...")
    port_alta_corr_ext = validar_y_filtrar_activos_por_correlacion(
        tickers=port_alta_corr_ext,
        returns=returns,
        tipo_portafolio="Alta Correlación",
        umbral_minimo_activos=NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO,
    )
    
    # Asegurar exactamente NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO activos
    if len(port_alta_corr_ext) < NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_alta_corr_ext)} activos válidos para alta correlación extendido")
        print(f"   Completando hasta {NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO} activos para comparabilidad...")
        todos_disponibles = [t for t in returns.columns if t not in ["SPY", "QQQ"] and t not in port_alta_corr_ext]
        if len(todos_disponibles) > 0:
            necesarios = NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO - len(port_alta_corr_ext)
            port_alta_corr_ext.extend(todos_disponibles[:necesarios])
    
    port_alta_corr_ext = port_alta_corr_ext[:NUM_ACTIVOS_PORTAFOLIO_EXTENDIDO]
    
    # Validar que haya suficientes activos antes de crear el resumen
    if len(port_alta_corr_ext) < 2:
        print(f"❌ Error: Solo se encontraron {len(port_alta_corr_ext)} activos válidos para el portafolio de alta correlación extendido")
        print(f"   Saltando este análisis.")
        resumen_high_ext = None
        pf_high_ext_df = None
        pf_high_ext_ms = None
        pf_high_ext_mv = None
    else:
        resumen_high_ext = resumen_portafolio_equally_weighted(
            nombre="Alta Correlación",
            tickers=port_alta_corr_ext,
            returns=returns,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resumen_portafolio(resumen_high_ext, monto_inversion=monto_inversion)

        pf_high_ext_df, pf_high_ext_ms, pf_high_ext_mv = simular_portafolios_markowitz(
            returns[resumen_high_ext.tickers],
            num_portfolios=5000,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resultados_markowitz(
            "Alta Correlación Extendido (Optimizado)",
            pf_high_ext_df,
            pf_high_ext_ms,
            pf_high_ext_mv,
            returns[resumen_high_ext.tickers],
            monto_inversion=monto_inversion,
        )

    # 9) Portafolio baja correlación EXTENDIDO (10 activos) - COMPARACIÓN
    print("\n" + "="*80)
    print("📊 PASO 6: COMPARACIÓN CON PORTAFOLIO BAJA CORRELACIÓN EXTENDIDO (10 activos)")
    print("="*80)
    port_baja_corr_ext_validos = [t for t in port_baja_corr_ext if t in returns.columns]
    if len(port_baja_corr_ext_validos) != len(port_baja_corr_ext):
        print(f"⚠️  Advertencia: {len(port_baja_corr_ext) - len(port_baja_corr_ext_validos)} tickers de baja correlación extendido no están en returns")
        port_baja_corr_ext = port_baja_corr_ext_validos
    
    # Validar que haya suficientes activos antes de crear el resumen
    if len(port_baja_corr_ext) < 2:
        print(f"❌ Error: Solo se encontraron {len(port_baja_corr_ext)} activos válidos para el portafolio de baja correlación extendido")
        print(f"   Se requiere mínimo 2 activos. Saltando este análisis.")
        resumen_low_ext = None
        pf_low_ext_df = None
        pf_low_ext_ms = None
        pf_low_ext_mv = None
    else:
        resumen_low_ext = resumen_portafolio_equally_weighted(
            nombre="Baja Correlación",
            tickers=port_baja_corr_ext,
            returns=returns,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resumen_portafolio(resumen_low_ext, monto_inversion=monto_inversion)

        pf_low_ext_df, pf_low_ext_ms, pf_low_ext_mv = simular_portafolios_markowitz(
            returns[resumen_low_ext.tickers],
            num_portfolios=5000,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resultados_markowitz(
            "Baja Correlación Extendido (Optimizado)",
            pf_low_ext_df,
            pf_low_ext_ms,
            pf_low_ext_mv,
            returns[resumen_low_ext.tickers],
            monto_inversion=monto_inversion,
        )

    # 6.5) Portafolio alta volatilidad y sesgo positivo
    print("\n" + "="*80)
    print("📊 PASO 6.5: PORTAFOLIO ALTA VOLATILIDAD Y SESGO POSITIVO")
    print("="*80)
    
    # Validar tickers
    port_alta_vol_sesgo_validos = [t for t in port_alta_vol_sesgo if t in returns.columns]
    
    # Asegurar exactamente NUM_ACTIVOS_PORTAFOLIO activos para comparabilidad
    if len(port_alta_vol_sesgo_validos) < NUM_ACTIVOS_PORTAFOLIO:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_alta_vol_sesgo_validos)} activos válidos para alta volatilidad y sesgo positivo")
        print(f"   Completando hasta {NUM_ACTIVOS_PORTAFOLIO} activos para comparabilidad...")
        todos_disponibles = [t for t in returns.columns if t not in ["SPY", "QQQ"] and t not in port_alta_vol_sesgo_validos]
        if len(todos_disponibles) > 0:
            necesarios = NUM_ACTIVOS_PORTAFOLIO - len(port_alta_vol_sesgo_validos)
            port_alta_vol_sesgo_validos.extend(todos_disponibles[:necesarios])
    
    port_alta_vol_sesgo_validos = port_alta_vol_sesgo_validos[:NUM_ACTIVOS_PORTAFOLIO]
    
    if len(port_alta_vol_sesgo_validos) < 2:
        print(f"❌ Error: No se pueden construir portafolios de alta volatilidad y sesgo positivo con los datos disponibles")
        return
    
    resumen_skew = resumen_portafolio_equally_weighted(
        nombre="Alta Volatilidad y Sesgo Positivo",
        tickers=port_alta_vol_sesgo_validos,
        returns=returns,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resumen_portafolio(resumen_skew, monto_inversion=monto_inversion)
    
    pf_skew_df, pf_skew_ms, pf_skew_mv = simular_portafolios_markowitz(
        returns[resumen_skew.tickers],
        num_portfolios=5000,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resultados_markowitz(
        "Alta Volatilidad y Sesgo Positivo (Optimizado)",
        pf_skew_df,
        pf_skew_ms,
        pf_skew_mv,
        returns[resumen_skew.tickers],
        monto_inversion=monto_inversion,
    )

    # 6.6) Portafolio correlación negativa
    print("\n" + "="*80)
    print("📊 PASO 6.6: PORTAFOLIO CORRELACIÓN NEGATIVA")
    print("="*80)
    
    port_corr_neg = construir_portafolio_correlacion_negativa(
        returns=returns,
        n_activos=NUM_ACTIVOS_PORTAFOLIO,
    )
    print(f"Portafolio 5 - Correlación Negativa ({NUM_ACTIVOS_PORTAFOLIO} activos objetivo): {', '.join(port_corr_neg)} (Total: {len(port_corr_neg)} tickers)")
    
    # Validar tickers que están en returns
    port_corr_neg_validos = [t for t in port_corr_neg if t in returns.columns]
    
    # VALIDAR Y FILTRAR activos por criterio de correlación negativa ANTES de optimizar
    print(f"\n   🔍 Validando activos por criterio de correlación negativa (<= -0.70)...")
    port_corr_neg_validos = validar_y_filtrar_activos_por_correlacion(
        tickers=port_corr_neg_validos,
        returns=returns,
        tipo_portafolio="Correlación Negativa",
        umbral_minimo_activos=NUM_ACTIVOS_PORTAFOLIO,
    )
    
    if len(port_corr_neg_validos) < NUM_ACTIVOS_PORTAFOLIO:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_corr_neg_validos)} activos válidos para correlación negativa")
        print(f"   Se requieren {NUM_ACTIVOS_PORTAFOLIO} activos para comparabilidad. Completando con los mejores disponibles...")
        # Completar con los mejores activos disponibles que no estén ya en el portafolio
        todos_disponibles = [t for t in returns.columns if t not in ["SPY", "QQQ"] and t not in port_corr_neg_validos]
        if len(todos_disponibles) > 0:
            necesarios = NUM_ACTIVOS_PORTAFOLIO - len(port_corr_neg_validos)
            port_corr_neg_validos.extend(todos_disponibles[:necesarios])
    
    # Asegurar exactamente NUM_ACTIVOS_PORTAFOLIO activos
    port_corr_neg_validos = port_corr_neg_validos[:NUM_ACTIVOS_PORTAFOLIO]
    
    if len(port_corr_neg_validos) < 2:
        print(f"❌ Error: No se pueden construir portafolios de correlación negativa con los datos disponibles")
        return
    
    resumen_neg = resumen_portafolio_equally_weighted(
        nombre="Correlación Negativa",
        tickers=port_corr_neg_validos,
        returns=returns,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resumen_portafolio(resumen_neg, monto_inversion=monto_inversion)
    
    pf_neg_df, pf_neg_ms, pf_neg_mv = simular_portafolios_markowitz(
        returns[resumen_neg.tickers],
        num_portfolios=5000,
        risk_free_rate=risk_free_rate,
    )
    mostrar_resultados_markowitz(
        "Correlación Negativa (Optimizado)",
        pf_neg_df,
        pf_neg_ms,
        pf_neg_mv,
        returns[resumen_neg.tickers],
        monto_inversion=monto_inversion,
    )

    # 7) Portafolio BCBA (Bolsa de Buenos Aires)
    print("\n" + "="*80)
    print("📊 PASO 7: PORTAFOLIO BCBA - BOLSA DE BUENOS AIRES")
    print("="*80)
    
    # Filtrar tickers BCBA que estén en returns
    port_bcba_validos = [t for t in BCBA_TICKERS if t in returns.columns]
    print(f"Portafolio BCBA: {len(port_bcba_validos)} tickers válidos de {len(BCBA_TICKERS)} totales")
    print(f"Tickers: {', '.join(port_bcba_validos)}")
    
    if len(port_bcba_validos) < 2:
        print(f"⚠️  Advertencia: Solo se encontraron {len(port_bcba_validos)} tickers BCBA válidos. Se requieren al menos 2.")
        resumen_bcba = None
        pf_bcba_df = None
        pf_bcba_ms = None
        pf_bcba_mv = None
    else:
        resumen_bcba = resumen_portafolio_equally_weighted(
            nombre="BCBA (Buenos Aires)",
            tickers=port_bcba_validos,
            returns=returns,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resumen_portafolio(resumen_bcba, monto_inversion=monto_inversion)
        mostrar_metricas_individuales("Portafolio BCBA", returns[resumen_bcba.tickers])
        
        pf_bcba_df, pf_bcba_ms, pf_bcba_mv = simular_portafolios_markowitz(
            returns[resumen_bcba.tickers],
            num_portfolios=5000,
            risk_free_rate=risk_free_rate,
        )
        mostrar_resultados_markowitz(
            "BCBA (Buenos Aires)",
            pf_bcba_df,
            pf_bcba_ms,
            pf_bcba_mv,
            returns[resumen_bcba.tickers],
            monto_inversion=monto_inversion,
        )

    # 8) Tabla comparativa mejorada con todos los portafolios y optimizaciones
    print("\n" + "=" * 100)
    print("📊 TABLA COMPARATIVA COMPLETA: TODOS LOS PORTAFOLIOS Y OPTIMIZACIONES")
    print("=" * 100)

    filas_tabla = []

    # 1. SPY+QQQ sin optimización (pesos iguales)
    filas_tabla.append(
        {
            "Portafolio": "SPY + QQQ",
            "Tipo": "Pesos Iguales",
            "Retorno_anual": resumen_spy_qqq.mean_return_annual,
            "Volatilidad_anual": resumen_spy_qqq.volatility_annual,
            "Sharpe_Ratio": resumen_spy_qqq.sharpe_ratio,
            "Ganancia_esperada_USD": resumen_spy_qqq.mean_return_annual * monto_inversion,
            "Ganancia_+1σ_USD": (resumen_spy_qqq.mean_return_annual + resumen_spy_qqq.volatility_annual)
            * monto_inversion,
            "Perdida_-1σ_USD": (resumen_spy_qqq.mean_return_annual - resumen_spy_qqq.volatility_annual)
            * monto_inversion,
        }
    )

    # 2. SPY+QQQ optimizado - Máximo Sharpe
    filas_tabla.append(
        {
            "Portafolio": "SPY + QQQ",
            "Tipo": "Máximo Sharpe",
            "Retorno_anual": pf_spy_qqq_ms["Return"],
            "Volatilidad_anual": pf_spy_qqq_ms["Volatility"],
            "Sharpe_Ratio": pf_spy_qqq_ms["Sharpe"],
            "Ganancia_esperada_USD": pf_spy_qqq_ms["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_spy_qqq_ms["Return"] + pf_spy_qqq_ms["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_spy_qqq_ms["Return"] - pf_spy_qqq_ms["Volatility"]) * monto_inversion,
        }
    )

    # 3. SPY+QQQ optimizado - Mínima Volatilidad
    filas_tabla.append(
        {
            "Portafolio": "SPY + QQQ",
            "Tipo": "Mínima Volatilidad",
            "Retorno_anual": pf_spy_qqq_mv["Return"],
            "Volatilidad_anual": pf_spy_qqq_mv["Volatility"],
            "Sharpe_Ratio": pf_spy_qqq_mv["Sharpe"],
            "Ganancia_esperada_USD": pf_spy_qqq_mv["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_spy_qqq_mv["Return"] + pf_spy_qqq_mv["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_spy_qqq_mv["Return"] - pf_spy_qqq_mv["Volatility"]) * monto_inversion,
        }
    )

    # 4. Alta correlación sin optimización
    filas_tabla.append(
        {
            "Portafolio": "Alta Correlación",
            "Tipo": "Pesos Iguales",
            "Retorno_anual": resumen_high.mean_return_annual,
            "Volatilidad_anual": resumen_high.volatility_annual,
            "Sharpe_Ratio": resumen_high.sharpe_ratio,
            "Ganancia_esperada_USD": resumen_high.mean_return_annual * monto_inversion,
            "Ganancia_+1σ_USD": (resumen_high.mean_return_annual + resumen_high.volatility_annual)
            * monto_inversion,
            "Perdida_-1σ_USD": (resumen_high.mean_return_annual - resumen_high.volatility_annual)
            * monto_inversion,
        }
    )

    # 5. Alta correlación optimizado - Máximo Sharpe
    filas_tabla.append(
        {
            "Portafolio": "Alta Correlación",
            "Tipo": "Máximo Sharpe",
            "Retorno_anual": pf_high_ms["Return"],
            "Volatilidad_anual": pf_high_ms["Volatility"],
            "Sharpe_Ratio": pf_high_ms["Sharpe"],
            "Ganancia_esperada_USD": pf_high_ms["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_high_ms["Return"] + pf_high_ms["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_high_ms["Return"] - pf_high_ms["Volatility"]) * monto_inversion,
        }
    )

    # 6. Alta correlación optimizado - Mínima Volatilidad
    filas_tabla.append(
        {
            "Portafolio": "Alta Correlación",
            "Tipo": "Mínima Volatilidad",
            "Retorno_anual": pf_high_mv["Return"],
            "Volatilidad_anual": pf_high_mv["Volatility"],
            "Sharpe_Ratio": pf_high_mv["Sharpe"],
            "Ganancia_esperada_USD": pf_high_mv["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_high_mv["Return"] + pf_high_mv["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_high_mv["Return"] - pf_high_mv["Volatility"]) * monto_inversion,
        }
    )

    # 7. Baja correlación sin optimización
    filas_tabla.append(
        {
            "Portafolio": "Baja Correlación",
            "Tipo": "Pesos Iguales",
            "Retorno_anual": resumen_low.mean_return_annual,
            "Volatilidad_anual": resumen_low.volatility_annual,
            "Sharpe_Ratio": resumen_low.sharpe_ratio,
            "Ganancia_esperada_USD": resumen_low.mean_return_annual * monto_inversion,
            "Ganancia_+1σ_USD": (resumen_low.mean_return_annual + resumen_low.volatility_annual)
            * monto_inversion,
            "Perdida_-1σ_USD": (resumen_low.mean_return_annual - resumen_low.volatility_annual)
            * monto_inversion,
        }
    )

    # 8. Baja correlación optimizado - Máximo Sharpe
    filas_tabla.append(
        {
            "Portafolio": "Baja Correlación",
            "Tipo": "Máximo Sharpe",
            "Retorno_anual": pf_low_ms["Return"],
            "Volatilidad_anual": pf_low_ms["Volatility"],
            "Sharpe_Ratio": pf_low_ms["Sharpe"],
            "Ganancia_esperada_USD": pf_low_ms["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_low_ms["Return"] + pf_low_ms["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_low_ms["Return"] - pf_low_ms["Volatility"]) * monto_inversion,
        }
    )

    # 9. Baja correlación optimizado - Mínima Volatilidad
    filas_tabla.append(
        {
            "Portafolio": "Baja Correlación",
            "Tipo": "Mínima Volatilidad",
            "Retorno_anual": pf_low_mv["Return"],
            "Volatilidad_anual": pf_low_mv["Volatility"],
            "Sharpe_Ratio": pf_low_mv["Sharpe"],
            "Ganancia_esperada_USD": pf_low_mv["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_low_mv["Return"] + pf_low_mv["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_low_mv["Return"] - pf_low_mv["Volatility"]) * monto_inversion,
        }
    )
    
    # 10. Alta volatilidad y sesgo positivo sin optimización
    filas_tabla.append(
        {
            "Portafolio": "Alta Volatilidad y Sesgo Positivo",
            "Tipo": "Pesos Iguales",
            "Retorno_anual": resumen_skew.mean_return_annual,
            "Volatilidad_anual": resumen_skew.volatility_annual,
            "Sharpe_Ratio": resumen_skew.sharpe_ratio,
            "Ganancia_esperada_USD": resumen_skew.mean_return_annual * monto_inversion,
            "Ganancia_+1σ_USD": (resumen_skew.mean_return_annual + resumen_skew.volatility_annual) * monto_inversion,
            "Perdida_-1σ_USD": (resumen_skew.mean_return_annual - resumen_skew.volatility_annual) * monto_inversion,
        }
    )
    
    # 11. Alta volatilidad y sesgo positivo optimizado - Máximo Sharpe
    filas_tabla.append(
        {
            "Portafolio": "Alta Volatilidad y Sesgo Positivo",
            "Tipo": "Máximo Sharpe",
            "Retorno_anual": pf_skew_ms["Return"],
            "Volatilidad_anual": pf_skew_ms["Volatility"],
            "Sharpe_Ratio": pf_skew_ms["Sharpe"],
            "Ganancia_esperada_USD": pf_skew_ms["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_skew_ms["Return"] + pf_skew_ms["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_skew_ms["Return"] - pf_skew_ms["Volatility"]) * monto_inversion,
        }
    )
    
    # 12. Alta volatilidad y sesgo positivo optimizado - Mínima Volatilidad
    filas_tabla.append(
        {
            "Portafolio": "Alta Volatilidad y Sesgo Positivo",
            "Tipo": "Mínima Volatilidad",
            "Retorno_anual": pf_skew_mv["Return"],
            "Volatilidad_anual": pf_skew_mv["Volatility"],
            "Sharpe_Ratio": pf_skew_mv["Sharpe"],
            "Ganancia_esperada_USD": pf_skew_mv["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_skew_mv["Return"] + pf_skew_mv["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_skew_mv["Return"] - pf_skew_mv["Volatility"]) * monto_inversion,
        }
    )
    
    # 13. Correlación Negativa sin optimización (pesos iguales)
    filas_tabla.append(
        {
            "Portafolio": "Correlación Negativa",
            "Tipo": "Pesos Iguales",
            "Retorno_anual": resumen_neg.mean_return_annual,
            "Volatilidad_anual": resumen_neg.volatility_annual,
            "Sharpe_Ratio": resumen_neg.sharpe_ratio,
            "Ganancia_esperada_USD": resumen_neg.mean_return_annual * monto_inversion,
            "Ganancia_+1σ_USD": (resumen_neg.mean_return_annual + resumen_neg.volatility_annual) * monto_inversion,
            "Perdida_-1σ_USD": (resumen_neg.mean_return_annual - resumen_neg.volatility_annual) * monto_inversion,
        }
    )
    
    # 14. Correlación Negativa optimizado - Máximo Sharpe
    filas_tabla.append(
        {
            "Portafolio": "Correlación Negativa",
            "Tipo": "Máximo Sharpe",
            "Retorno_anual": pf_neg_ms["Return"],
            "Volatilidad_anual": pf_neg_ms["Volatility"],
            "Sharpe_Ratio": pf_neg_ms["Sharpe"],
            "Ganancia_esperada_USD": pf_neg_ms["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_neg_ms["Return"] + pf_neg_ms["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_neg_ms["Return"] - pf_neg_ms["Volatility"]) * monto_inversion,
        }
    )
    
    # 15. Correlación Negativa optimizado - Mínima Volatilidad
    filas_tabla.append(
        {
            "Portafolio": "Correlación Negativa",
            "Tipo": "Mínima Volatilidad",
            "Retorno_anual": pf_neg_mv["Return"],
            "Volatilidad_anual": pf_neg_mv["Volatility"],
            "Sharpe_Ratio": pf_neg_mv["Sharpe"],
            "Ganancia_esperada_USD": pf_neg_mv["Return"] * monto_inversion,
            "Ganancia_+1σ_USD": (pf_neg_mv["Return"] + pf_neg_mv["Volatility"]) * monto_inversion,
            "Perdida_-1σ_USD": (pf_neg_mv["Return"] - pf_neg_mv["Volatility"]) * monto_inversion,
        }
    )
    
    # 16-18. BCBA (Bolsa de Buenos Aires) - solo si hay datos válidos
    if resumen_bcba is not None:
        # BCBA sin optimización (pesos iguales)
        filas_tabla.append(
            {
                "Portafolio": "BCBA (Buenos Aires)",
                "Tipo": "Pesos Iguales",
                "Retorno_anual": resumen_bcba.mean_return_annual,
                "Volatilidad_anual": resumen_bcba.volatility_annual,
                "Sharpe_Ratio": resumen_bcba.sharpe_ratio,
                "Ganancia_esperada_USD": resumen_bcba.mean_return_annual * monto_inversion,
                "Ganancia_+1σ_USD": (resumen_bcba.mean_return_annual + resumen_bcba.volatility_annual) * monto_inversion,
                "Perdida_-1σ_USD": (resumen_bcba.mean_return_annual - resumen_bcba.volatility_annual) * monto_inversion,
            }
        )
        
        # BCBA optimizado - Máximo Sharpe
        filas_tabla.append(
            {
                "Portafolio": "BCBA (Buenos Aires)",
                "Tipo": "Máximo Sharpe",
                "Retorno_anual": pf_bcba_ms["Return"],
                "Volatilidad_anual": pf_bcba_ms["Volatility"],
                "Sharpe_Ratio": pf_bcba_ms["Sharpe"],
                "Ganancia_esperada_USD": pf_bcba_ms["Return"] * monto_inversion,
                "Ganancia_+1σ_USD": (pf_bcba_ms["Return"] + pf_bcba_ms["Volatility"]) * monto_inversion,
                "Perdida_-1σ_USD": (pf_bcba_ms["Return"] - pf_bcba_ms["Volatility"]) * monto_inversion,
            }
        )
        
        # BCBA optimizado - Mínima Volatilidad
        filas_tabla.append(
            {
                "Portafolio": "BCBA (Buenos Aires)",
                "Tipo": "Mínima Volatilidad",
                "Retorno_anual": pf_bcba_mv["Return"],
                "Volatilidad_anual": pf_bcba_mv["Volatility"],
                "Sharpe_Ratio": pf_bcba_mv["Sharpe"],
                "Ganancia_esperada_USD": pf_bcba_mv["Return"] * monto_inversion,
                "Ganancia_+1σ_USD": (pf_bcba_mv["Return"] + pf_bcba_mv["Volatility"]) * monto_inversion,
                "Perdida_-1σ_USD": (pf_bcba_mv["Return"] - pf_bcba_mv["Volatility"]) * monto_inversion,
            }
        )
    
    # Crear DataFrame y formatear
    df_tabla = pd.DataFrame(filas_tabla)
    df_tabla["Retorno_anual_%"] = df_tabla["Retorno_anual"] * 100
    df_tabla["Volatilidad_anual_%"] = df_tabla["Volatilidad_anual"] * 100
    df_tabla["Ganancia_esperada_USD"] = df_tabla["Ganancia_esperada_USD"].round(0)
    df_tabla["Ganancia_+1σ_USD"] = df_tabla["Ganancia_+1σ_USD"].round(0)
    df_tabla["Perdida_-1σ_USD"] = df_tabla["Perdida_-1σ_USD"].round(0)
    df_tabla["Sharpe_Ratio"] = df_tabla["Sharpe_Ratio"].round(3)
    df_tabla["Retorno_anual_%"] = df_tabla["Retorno_anual_%"].round(2)
    df_tabla["Volatilidad_anual_%"] = df_tabla["Volatilidad_anual_%"].round(2)

    # Mostrar tabla completa
    print("\n📈 RESUMEN COMPARATIVO (Monto de Inversión: USD ${:,.0f})".format(monto_inversion))
    print("-" * 100)
    print(
        df_tabla[
            [
                "Portafolio",
                "Tipo",
                "Retorno_anual_%",
                "Volatilidad_anual_%",
                "Sharpe_Ratio",
                "Ganancia_esperada_USD",
                "Ganancia_+1σ_USD",
                "Perdida_-1σ_USD",
            ]
        ].to_string(index=False)
    )
    
    # Mostrar mejores portafolios
    print("\n" + "=" * 100)
    print("🏆 MEJORES PORTAFOLIOS POR MÉTRICA")
    print("=" * 100)
    
    mejor_sharpe = df_tabla.loc[df_tabla["Sharpe_Ratio"].idxmax()]
    mejor_retorno = df_tabla.loc[df_tabla["Retorno_anual"].idxmax()]
    menor_volatilidad = df_tabla.loc[df_tabla["Volatilidad_anual"].idxmin()]
    
    print(f"\n🥇 Mayor Sharpe Ratio: {mejor_sharpe['Portafolio']} - {mejor_sharpe['Tipo']}")
    print(f"   Sharpe: {mejor_sharpe['Sharpe_Ratio']:.3f} | Retorno: {mejor_sharpe['Retorno_anual_%']:.2f}% | Vol: {mejor_sharpe['Volatilidad_anual_%']:.2f}%")
    
    print(f"\n📈 Mayor Retorno Esperado: {mejor_retorno['Portafolio']} - {mejor_retorno['Tipo']}")
    print(f"   Retorno: {mejor_retorno['Retorno_anual_%']:.2f}% | Sharpe: {mejor_retorno['Sharpe_Ratio']:.3f} | Vol: {mejor_retorno['Volatilidad_anual_%']:.2f}%")
    
    print(f"\n🛡️ Menor Volatilidad: {menor_volatilidad['Portafolio']} - {menor_volatilidad['Tipo']}")
    print(f"   Vol: {menor_volatilidad['Volatilidad_anual_%']:.2f}% | Retorno: {menor_volatilidad['Retorno_anual_%']:.2f}% | Sharpe: {menor_volatilidad['Sharpe_Ratio']:.3f}")

    print("\n\n✅ Análisis completado.")
    
    # 8) Generar HTML con las optimizaciones
    print("\n📄 Generando HTML con optimizaciones...")
    generar_html_optimizaciones(
        resumen_spy_qqq=resumen_spy_qqq,
        pf_spy_qqq_df=pf_spy_qqq_df,
        pf_spy_qqq_ms=pf_spy_qqq_ms,
        pf_spy_qqq_mv=pf_spy_qqq_mv,
        resumen_high=resumen_high,
        pf_high_df=pf_high_df,
        pf_high_ms=pf_high_ms,
        pf_high_mv=pf_high_mv,
        resumen_low=resumen_low,
        pf_low_df=pf_low_df,
        pf_low_ms=pf_low_ms,
        pf_low_mv=pf_low_mv,
        resumen_high_ext=resumen_high_ext,
        pf_high_ext_df=pf_high_ext_df,
        pf_high_ext_ms=pf_high_ext_ms,
        pf_high_ext_mv=pf_high_ext_mv,
        resumen_low_ext=resumen_low_ext,
        pf_low_ext_df=pf_low_ext_df,
        pf_low_ext_ms=pf_low_ext_ms,
        pf_low_ext_mv=pf_low_ext_mv,
        resumen_skew=resumen_skew,
        pf_skew_df=pf_skew_df,
        pf_skew_ms=pf_skew_ms,
        pf_skew_mv=pf_skew_mv,
        resumen_neg=resumen_neg,
        pf_neg_df=pf_neg_df,
        pf_neg_ms=pf_neg_ms,
        pf_neg_mv=pf_neg_mv,
        resumen_bcba=resumen_bcba,
        pf_bcba_df=pf_bcba_df,
        pf_bcba_ms=pf_bcba_ms,
        pf_bcba_mv=pf_bcba_mv,
        metricas_spy_qqq=metricas_spy_qqq,
        monto_inversion=monto_inversion,
        returns=returns,
        df_precios=df_precios,  # Agregar precios para calcular cantidades
        risk_free_rate=risk_free_rate,
    )
    print("✅ HTML generado exitosamente.")


def _generar_html_completo_con_carruseles() -> str:
    """
    Genera el template HTML completo con carruseles, gráficos y funcionalidad de descarga.
    """
    # Leer el HTML completo desde un archivo o generarlo inline
    # Por ahora, generamos una versión completa inline
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Portfolio Optimizer & Visualizer - Análisis de Optimizaciones</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/downloadjs@1.4.7/download.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700&family=JetBrains+Mono:wght@400;500;600;700&family=Roboto+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" crossorigin="anonymous">
    <style>
    /* Plantillas profesionales minimalistas dark financieras formales */
    :root {
      --template: 'minimal-dark';
    }
    
    body { 
      font-family: 'Inter', sans-serif; 
      background-color: #0f172a; 
      color: #f8fafc;
      overflow-x: hidden;
      overflow-y: auto;
      transition: all 0.3s ease;
      margin: 0 !important;
      padding: 0 !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    
    html {
      margin: 0 !important;
      padding: 0 !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    
    /* Plantilla: Minimal Dark (por defecto) */
    body[data-template="minimal-dark"] {
      background-color: #0a0e1a;
      color: #e2e8f0;
    }
    body[data-template="minimal-dark"] .card {
      background: #1a1f2e;
      border: 1px solid #2d3748;
      border-radius: 8px;
    }
    body[data-template="minimal-dark"] .header {
      background: #0f1419;
      border-bottom: 1px solid #1e293b;
    }
    
    /* Plantilla: Executive Dark */
    body[data-template="executive-dark"] {
      background: linear-gradient(135deg, #0a0f1c 0%, #1a1f2e 100%);
      color: #f1f5f9;
    }
    body[data-template="executive-dark"] .card {
      background: #111827;
      border: 1px solid #374151;
      border-left: 3px solid #d4af37;
      border-radius: 4px;
    }
    body[data-template="executive-dark"] .header {
      background: #0d1117;
      border-bottom: 2px solid #d4af37;
    }
    body[data-template="executive-dark"] h1, body[data-template="executive-dark"] h2 {
      font-family: 'Playfair Display', serif;
      color: #d4af37;
    }
    
    /* Plantilla: Bloomberg Terminal */
    body[data-template="bloomberg"] {
      background: #1a1a1a;
      color: #ffa500;
      font-family: 'JetBrains Mono', monospace;
    }
    body[data-template="bloomberg"] .card {
      background: #2a2a2a;
      border-left: 4px solid #ffa500;
      border-radius: 0;
    }
    body[data-template="bloomberg"] .header {
      background: #1a1a1a;
      border-bottom: 2px solid #ffa500;
    }
    body[data-template="bloomberg"] table {
      border-collapse: collapse;
    }
    body[data-template="bloomberg"] th {
      background: #1a1a1a;
      border-bottom: 2px solid #ffa500;
    }
    
    /* Plantilla: Institutional */
    body[data-template="institutional"] {
      background: #0d1117;
      color: #c9d1d9;
    }
    body[data-template="institutional"] .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 6px;
    }
    body[data-template="institutional"] .header {
      background: #0d1117;
      border-bottom: 1px solid #21262d;
    }
    
    /* Plantilla: Financial Report */
    body[data-template="financial-report"] {
      background: #ffffff;
      color: #1e293b;
    }
    body[data-template="financial-report"] .card {
      background: #f8fafc;
      border: 2px solid #e2e8f0;
      border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    body[data-template="financial-report"] .header {
      background: #1e293b;
      color: #ffffff;
      border-bottom: 3px solid #3b82f6;
    }
    
    /* Plantilla: Quant Dark */
    body[data-template="quant-dark"] {
      background: #000000;
      color: #00ff88;
      font-family: 'JetBrains Mono', monospace;
    }
    body[data-template="quant-dark"] .card {
      background: #0a0a0a;
      border: 1px solid #00ff88;
      border-radius: 0;
      box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
    }
    body[data-template="quant-dark"] .header {
      background: #000000;
      border-bottom: 2px solid #00ff88;
    }
    
    /* Estilos comunes */
    #root {
      overflow: visible;
      min-height: 100vh;
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    .slide {
      display: none;
      /* min-height: 100vh; ELIMINADO para quitar espacio estructural */
      padding: 0 !important;
      margin: 0 !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
      width: 100%;
      box-sizing: border-box;
    }
    .slide.active {
      display: block;
    }
    /* Asegurar que los slides tengan todo su contenido visible para descarga */
    .slide * {
      max-width: 100%;
      box-sizing: border-box;
    }
    /* Eliminar TODOS los espacios vacíos en TODOS los slides */
    .slide > div {
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    .slide > div > .card:first-child {
      margin-top: 0 !important;
      padding-top: 1.5rem !important;
    }
    #slide-container {
      overflow: visible !important;
      max-height: none !important;
      height: auto !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    main {
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    .header {
      padding-top: 0.25rem !important;
      padding-bottom: 0.25rem !important;
      margin: 0 !important;
    }
    body > #root > main {
      padding-top: 0 !important;
      margin-top: 0 !important;
    }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
    .font-playfair { font-family: 'Playfair Display', serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
    @keyframes slide-in-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
    .animate-slide-in-right { animation: slide-in-right 0.3s ease-out; }
    canvas { 
      max-width: 100%; 
      height: auto; 
      display: block;
    }
    /* Contenedor para gráficos de barras - ajustado al ancho */
    .chart-container {
      width: 100%;
      overflow: visible;
      padding: 1rem 0;
    }
    .chart-container canvas {
      display: block;
      margin: 0 auto;
      max-width: 100%;
      height: auto;
    }
    
    /* Selector de plantillas - versión discreta (inline en el header) */
    .template-selector {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-left: 1rem;
      background: transparent;
      border: none;
      padding: 0;
    }
    .template-selector label {
      font-size: 0.7rem;
      color: #64748b;
    }
    .template-selector select {
      padding: 0.25rem 0.5rem;
      background: #1e293b;
      border: 1px solid #475569;
      border-radius: 9999px; /* pill */
      color: #f8fafc;
      font-size: 0.75rem;
    }
    
    /* Tabs de navegación */
    .nav-tabs {
      display: flex;
      gap: 0.5rem;
      border-bottom: 2px solid #334155;
      margin-bottom: 1rem;
      padding: 0 1rem;
    }
    .nav-tab {
      padding: 0.75rem 1.5rem;
      background: transparent;
      border: none;
      border-bottom: 3px solid transparent;
      color: #94a3b8;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 500;
      transition: all 0.2s;
    }
    .nav-tab:hover {
      color: #f1f5f9;
      background: rgba(255, 255, 255, 0.05);
    }
    .nav-tab.active {
      color: #3b82f6;
      border-bottom-color: #3b82f6;
      background: rgba(59, 130, 246, 0.1);
    }
    .tab-content {
      display: none;
    }
    .tab-content.active {
      display: block;
    }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module">
        // Datos de optimizaciones embebidos
        let OPTIMIZATION_DATA = {datos_json};
        
        // Estado de la aplicación
        let currentSlideIndex = 0;
        let slides = [];
        let currentTemplate = 'minimal-dark';
        let currentTab = 'optimizaciones';
        let historicalSeriesData = null;
        
        // Plantillas disponibles
        const TEMPLATES = {
            'minimal-dark': { name: 'Minimal Dark', class: 'minimal-dark' },
            'executive-dark': { name: 'Executive Dark', class: 'executive-dark' },
            'bloomberg': { name: 'Bloomberg Terminal', class: 'bloomberg' },
            'institutional': { name: 'Institutional', class: 'institutional' },
            'financial-report': { name: 'Financial Report', class: 'financial-report' },
            'quant-dark': { name: 'Quant Dark', class: 'quant-dark' }
        };
        
        // Función para cambiar plantilla
        function changeTemplate(templateId) {
            currentTemplate = templateId;
            document.body.setAttribute('data-template', templateId);
            // Re-renderizar gráficos con nuevos colores si es necesario
            setTimeout(() => renderAllCharts(), 100);
        }
        
        // Funciones de utilidad
        function formatCurrency(value) {
            const absValue = Math.abs(value);
            const sign = value < 0 ? '-' : '';
            const wholePart = Math.floor(absValue);
            const decimalPart = Math.round((absValue - wholePart) * 100);
            const formatted = wholePart.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
            return `${sign}$${formatted}${decimalPart > 0 ? '.' + decimalPart.toString().padStart(2, '0') : ''}`;
        }
        
        // Función para crear gráfico de pastel (PROFESIONAL MEJORADO)
        function createPieChart(canvasId, data, title) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            // Usar el ancho completo del contenedor para mejor visualización
            const container = canvas.parentElement;
            let canvasWidth = 1000;
            let canvasHeight = 700;
            
            if (container) {
                const containerWidth = container.clientWidth || 1000;
                canvasWidth = Math.max(900, containerWidth - 96); // Usar casi todo el ancho disponible
                canvasHeight = 700; // Altura aumentada
            }
            
            // Establecer tamaño del canvas con alta resolución
            const dpr = window.devicePixelRatio || 1;
            canvas.width = canvasWidth * dpr;
            canvas.height = canvasHeight * dpr;
            canvas.style.width = canvasWidth + 'px';
            canvas.style.height = canvasHeight + 'px';
            
            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            
            // Calcular dimensiones del gráfico
            const legendWidth = 280; // Ancho fijo para la leyenda
            const chartAreaWidth = canvasWidth - legendWidth - 40; // Área del gráfico
            const centerX = chartAreaWidth / 2;
            const centerY = canvasHeight / 2;
            const maxRadius = Math.min(chartAreaWidth, canvasHeight) / 2 - 40;
            const radius = maxRadius;
            
            let currentAngle = -Math.PI / 2;
            const total = data.reduce((sum, item) => sum + (item.value || 0), 0);
            
            // Colores profesionales mejorados
            const colors = [
                '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
                '#a855f7', '#06b6d4', '#f97316', '#ec4899',
                '#14b8a6', '#6366f1', '#f43f5e', '#8b5cf6'
            ];
            
            // Limpiar canvas
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            
            // Fondo profesional
            const bgGradient = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight);
            bgGradient.addColorStop(0, 'rgba(15, 23, 42, 0.95)');
            bgGradient.addColorStop(1, 'rgba(30, 41, 59, 0.95)');
            ctx.fillStyle = bgGradient;
            ctx.fillRect(0, 0, canvasWidth, canvasHeight);
            
            // Dibujar gráfico de pastel
            data.forEach((item, idx) => {
                const sliceAngle = ((item.value || 0) / total) * 2 * Math.PI;
                
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
                ctx.closePath();
                ctx.fillStyle = colors[idx % colors.length];
                ctx.fill();
                
                // Borde profesional
                ctx.strokeStyle = 'rgba(15, 23, 42, 0.9)';
                ctx.lineWidth = 3;
                ctx.stroke();
                
                // Separación entre segmentos
                if (sliceAngle > 0.05) {
                    ctx.strokeStyle = 'rgba(15, 23, 42, 0.6)';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(centerX, centerY);
                    ctx.lineTo(
                        centerX + Math.cos(currentAngle) * radius,
                        centerY + Math.sin(currentAngle) * radius
                    );
                    ctx.stroke();
                }
                
                currentAngle += sliceAngle;
            });
            
            // Leyenda profesional a la derecha con mejor espaciado
            const legendStartX = chartAreaWidth + 30;
            const legendStartY = 50;
            let yOffset = legendStartY;
            const lineHeight = 28; // Aumentado de 20 para mejor espaciado
            const colorBoxSize = 18; // Aumentado de 14
            const colorBoxSpacing = 8;
            
            data.forEach((item, idx) => {
                const value = (item.value || 0);
                const percentage = value.toFixed(2);
                const allocation = formatCurrency(item.allocation || 0);
                
                // Cuadro de color
                ctx.fillStyle = colors[idx % colors.length];
                ctx.fillRect(legendStartX, yOffset, colorBoxSize, colorBoxSize);
                
                // Borde del cuadro
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
                ctx.lineWidth = 1;
                ctx.strokeRect(legendStartX, yOffset, colorBoxSize, colorBoxSize);
                
                // Nombre del ticker (primera línea)
                ctx.fillStyle = '#f1f5f9';
                ctx.font = '600 13px "Inter", sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                ctx.fillText(item.name, legendStartX + colorBoxSize + colorBoxSpacing, yOffset);
                
                // Porcentaje y asignación (segunda línea)
                ctx.fillStyle = '#94a3b8';
                ctx.font = '500 11px "Roboto Mono", monospace';
                ctx.fillText(
                    `${percentage}% • ${allocation}`, 
                    legendStartX + colorBoxSize + colorBoxSpacing, 
                    yOffset + 16
                );
                
                yOffset += lineHeight;
            });
            
            // Título del gráfico (opcional, si se pasa)
            if (title) {
                ctx.fillStyle = '#f8fafc';
                ctx.font = '700 18px "Inter", sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillText(title, centerX, 20);
            }
        }
        
        // Función para crear gráfico de barras de percentiles (PROFESIONAL MEJORADO)
        function createBarChart(canvasId, percentiles, title) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            // Verificar que los percentiles existan
            if (!percentiles || Object.keys(percentiles).length === 0) {
                console.error('Percentiles incompletos:', percentiles);
                return;
            }
            
            // Tamaño ajustado al contenedor (sin barras de desplazamiento)
            const container = canvas.parentElement;
            let canvasWidth = 800;
            let canvasHeight = 500;
            
            if (container) {
                // Usar el ancho completo del contenedor menos padding
                const containerWidth = container.clientWidth || 800;
                canvasWidth = Math.max(600, containerWidth - 96); // 48px padding a cada lado
                canvasHeight = 500; // Altura fija razonable
            }
            
            // Establecer tamaño del canvas con alta resolución
            const dpr = window.devicePixelRatio || 1;
            canvas.width = canvasWidth * dpr;
            canvas.height = canvasHeight * dpr;
            canvas.style.width = canvasWidth + 'px';
            canvas.style.height = canvasHeight + 'px';
            
            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            
            // Padding aumentado para mejor espaciado profesional
            const padding = { top: 80, right: 60, bottom: 140, left: 120 };
            const chartWidth = canvasWidth - padding.left - padding.right;
            const chartHeight = canvasHeight - padding.top - padding.bottom;
            
            // Convertir percentiles a lista ordenada
            const percentilesList = Object.entries(percentiles)
                .filter(([p, perc]) => {
                    // Filtrar percentiles inválidos (NaN, null, undefined)
                    const prob = parseInt(p);
                    if (isNaN(prob) || !perc || perc === null || perc === undefined) {
                        return false;
                    }
                    // Filtrar también si el PNL es NaN o si es un string "NaN"
                    const pnl = perc.pnl;
                    if (pnl === null || pnl === undefined || isNaN(pnl) || (typeof pnl === 'string' && pnl.toLowerCase() === 'nan')) {
                        return false;
                    }
                    return true;
                })
                .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
                .map(([p, perc]) => {
                    const prob = parseInt(p);
                    const pnl = perc.pnl || 0;
                    const colors = {
                        5: { color: '#dc2626', colorLight: '#fca5a5', name: 'P5', subtitle: 'Muy Pesimista' },
                        10: { color: '#f59e0b', colorLight: '#fcd34d', name: 'P10', subtitle: 'Pesimista' },
                        25: { color: '#f97316', colorLight: '#fb923c', name: 'P25', subtitle: 'Bajo' },
                        50: { color: '#3b82f6', colorLight: '#93c5fd', name: 'P50', subtitle: 'Mediana' },
                        75: { color: '#10b981', colorLight: '#6ee7b7', name: 'P75', subtitle: 'Alto' },
                        90: { color: '#059669', colorLight: '#34d399', name: 'P90', subtitle: 'Optimista' },
                        95: { color: '#047857', colorLight: '#6ee7b7', name: 'P95', subtitle: 'Muy Optimista' }
                    };
                    const style = colors[prob] || { color: '#64748b', colorLight: '#94a3b8', name: `P${prob}`, subtitle: '' };
                    return {
                        name: style.name,
                        subtitle: style.subtitle,
                        value: pnl,
                        color: style.color,
                        colorLight: style.colorLight
                    };
                });
            
            // Calcular min y max con margen para mejor visualización
            const rawMinValue = Math.min(...percentilesList.map(s => s.value));
            const rawMaxValue = Math.max(...percentilesList.map(s => s.value));
            const rawRange = rawMaxValue - rawMinValue;
            
            // Agregar margen del 10% arriba y abajo para mejor visualización
            const margin = Math.max(Math.abs(rawRange) * 0.1, Math.abs(rawMinValue) * 0.1, Math.abs(rawMaxValue) * 0.1);
            const minValue = rawMinValue - margin;
            const maxValue = rawMaxValue + margin;
            const range = maxValue - minValue || 1;
            
            // Calcular posición de cero en el eje Y
            const zeroY = padding.top + chartHeight - ((0 - minValue) / range) * chartHeight;
            
            // Limpiar canvas
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            
            // Fondo profesional con gradiente sutil
            const bgGradient = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight);
            bgGradient.addColorStop(0, 'rgba(15, 23, 42, 0.95)');
            bgGradient.addColorStop(1, 'rgba(30, 41, 59, 0.95)');
            ctx.fillStyle = bgGradient;
            ctx.fillRect(0, 0, canvasWidth, canvasHeight);
            
            // Borde sutil
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.2)';
            ctx.lineWidth = 1;
            ctx.strokeRect(0, 0, canvasWidth, canvasHeight);
            
            // Línea de cero más visible
            ctx.strokeStyle = '#64748b';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(padding.left, zeroY);
            ctx.lineTo(canvas.width - padding.right, zeroY);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // Ejes más visibles
            ctx.strokeStyle = '#475569';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(padding.left, padding.top);
            ctx.lineTo(padding.left, canvas.height - padding.bottom);
            ctx.lineTo(canvas.width - padding.right, canvas.height - padding.bottom);
            ctx.stroke();
            
            // Etiquetas del eje Y (valores)
            const numYTicks = 8;
            const yStep = range / numYTicks;
            for (let i = 0; i <= numYTicks; i++) {
                const value = minValue + (i * yStep);
                const y = padding.top + chartHeight - ((value - minValue) / range) * chartHeight;
                
                // Línea de guía
                ctx.strokeStyle = '#334155';
                ctx.lineWidth = 0.5;
                ctx.setLineDash([2, 2]);
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(canvas.width - padding.right, y);
                ctx.stroke();
                ctx.setLineDash([]);
                
                // Etiqueta del valor con fuente profesional
                ctx.fillStyle = '#cbd5e1';
                ctx.font = '500 12px "Roboto Mono", monospace';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';
                ctx.fillText(formatCurrency(value), padding.left - 15, y);
            }
            
            // Barras con mejor espaciado (más espacio entre barras)
            const barWidth = (chartWidth / percentilesList.length) * 0.65; // 65% del espacio para barras
            const barSpacing = (chartWidth / percentilesList.length) * 0.35; // 35% para espaciado (aumentado)
            percentilesList.forEach((scenario, idx) => {
                const x = padding.left + idx * (barWidth + barSpacing) + (barSpacing / 2);
                
                // Calcular altura de la barra correctamente basada en la posición del valor en la escala
                // La altura debe ser la distancia desde cero hasta el valor
                const valueY = padding.top + chartHeight - ((scenario.value - minValue) / range) * chartHeight;
                const barHeight = Math.abs(zeroY - valueY);
                
                // Calcular posición Y: si el valor es positivo, la barra va desde zeroY hacia arriba
                // Si es negativo, la barra va desde zeroY hacia abajo
                const y = scenario.value >= 0 ? valueY : zeroY;
                
                // Sombra de la barra
                ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                ctx.fillRect(x + 3, y + 3, barWidth, barHeight);
                
                // Barra principal
                ctx.fillStyle = scenario.color;
                ctx.fillRect(x, y, barWidth, barHeight);
                
                // Borde de la barra
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
                ctx.lineWidth = 1;
                ctx.strokeRect(x, y, barWidth, barHeight);
                
                // Etiqueta del escenario (debajo de la barra) - Formato profesional
                const labelY = canvasHeight - padding.bottom + 35;
                const labelY2 = labelY + 18;
                
                // Nombre principal
                ctx.fillStyle = '#f1f5f9';
                ctx.font = '600 14px "Inter", sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillText(scenario.name, x + barWidth / 2, labelY);
                
                // Subtítulo si existe
                if (scenario.subtitle) {
                    ctx.fillStyle = '#94a3b8';
                    ctx.font = '500 11px "Inter", sans-serif';
                    ctx.fillText(scenario.subtitle, x + barWidth / 2, labelY2);
                }
                
                // Valor P&L con formato profesional mejorado
                const valueText = formatCurrency(scenario.value);
                const valueColor = scenario.value >= 0 ? '#10b981' : '#ef4444';
                
                // Calcular posición del texto para evitar superposición - mejorado
                let textValueY;
                const minTextDistance = 35; // Aumentado para mejor espaciado
                const textOffset = 18; // Offset desde la barra
                
                if (scenario.value >= 0) {
                    // Valor positivo: arriba de la barra
                    textValueY = y - textOffset;
                    // Si está muy cerca del borde superior, ponerlo dentro de la barra
                    if (textValueY < padding.top + minTextDistance) {
                        if (barHeight > 60) {
                            textValueY = y + barHeight / 2;
                        } else {
                            textValueY = y + barHeight + textOffset + 5;
                        }
                    }
                } else {
                    // Valor negativo: abajo de la barra
                    textValueY = y + barHeight + textOffset;
                    // Si está muy cerca del borde inferior, ponerlo dentro de la barra
                    if (textValueY > canvasHeight - padding.bottom - minTextDistance) {
                        if (barHeight > 60) {
                            textValueY = y + barHeight / 2;
                        } else {
                            textValueY = y - textOffset;
                        }
                    }
                }
                
                // Asegurar que el texto no se salga de los límites
                textValueY = Math.max(padding.top + minTextDistance, Math.min(textValueY, canvasHeight - padding.bottom - minTextDistance));
                
                // Fondo profesional para el texto con sombra
                const textMetrics = ctx.measureText(valueText);
                const textWidth = textMetrics.width;
                const textHeight = 22;
                const textPadding = 10;
                const textX = x + barWidth / 2 - textWidth / 2 - textPadding;
                const textY = textValueY - textHeight / 2;
                
                // Sombra del fondo
                ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                ctx.fillRect(textX + 2, textY + 2, textWidth + textPadding * 2, textHeight);
                
                // Fondo del texto
                ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
                ctx.fillRect(textX, textY, textWidth + textPadding * 2, textHeight);
                
                // Borde del fondo del texto
                ctx.strokeStyle = valueColor;
                ctx.lineWidth = 2;
                ctx.strokeRect(textX, textY, textWidth + textPadding * 2, textHeight);
                
                // Dibujar el texto del valor con fuente profesional
                ctx.fillStyle = valueColor;
                ctx.font = '700 15px "Roboto Mono", monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(valueText, x + barWidth / 2, textValueY);
            });
            
            // Título profesional más grande y centrado
            ctx.fillStyle = '#f8fafc';
            ctx.font = '700 22px "Inter", sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(title, canvasWidth / 2, 25);
            
            // Subtítulo con información adicional
            ctx.fillStyle = '#94a3b8';
            ctx.font = '500 13px "Inter", sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Ganancia/Pérdida Esperada por Escenario (P&L)', canvasWidth / 2, 55);
        }
        
        // Función para crear gráfico de frontera eficiente
        function createEfficientFrontierChart(canvasId, frontierData, portfolioPoints, title) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            // Tamaño del canvas
            const container = canvas.parentElement;
            let canvasWidth = 800;
            let canvasHeight = 600;
            
            if (container) {
                const containerWidth = container.clientWidth || 800;
                canvasWidth = Math.max(600, containerWidth - 96); // Ajustar al ancho disponible
                canvasHeight = 500; // Altura razonable
            }
            
            const dpr = window.devicePixelRatio || 1;
            canvas.width = canvasWidth * dpr;
            canvas.height = canvasHeight * dpr;
            canvas.style.width = canvasWidth + 'px';
            canvas.style.height = canvasHeight + 'px';
            
            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            
            const padding = { top: 60, right: 50, bottom: 80, left: 100 };
            const chartWidth = canvasWidth - padding.left - padding.right;
            const chartHeight = canvasHeight - padding.top - padding.bottom;
            
            // Limpiar canvas
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            
            // Fondo profesional
            const bgGradient = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight);
            bgGradient.addColorStop(0, 'rgba(15, 23, 42, 0.95)');
            bgGradient.addColorStop(1, 'rgba(30, 41, 59, 0.95)');
            ctx.fillStyle = bgGradient;
            ctx.fillRect(0, 0, canvasWidth, canvasHeight);
            
            if (!frontierData || frontierData.length === 0) {
                ctx.fillStyle = '#94a3b8';
                ctx.font = '14px Inter';
                ctx.textAlign = 'center';
                ctx.fillText('No hay datos de frontera eficiente', canvasWidth / 2, canvasHeight / 2);
                return;
            }
            
            // Calcular rangos: mostrar solo la MITAD SUPERIOR de las simulaciones (mejor retorno/riesgo)
            // Ordenar por Sharpe ratio o por retorno/volatilidad para obtener la mejor mitad
            const frontierDataWithSharpe = frontierData.map(p => ({
                ...p,
                sharpe_ratio: p.retorno / p.volatilidad || 0  // Aproximación de Sharpe
            }));
            
            // Ordenar por Sharpe descendente y tomar la mejor mitad
            frontierDataWithSharpe.sort((a, b) => b.sharpe_ratio - a.sharpe_ratio);
            const mejorMitad = frontierDataWithSharpe.slice(0, Math.ceil(frontierDataWithSharpe.length / 2));
            
            // Calcular rangos solo de la mejor mitad
            const volatilities = mejorMitad.map(p => p.volatilidad);
            const returns = mejorMitad.map(p => p.retorno);
            
            // Si hay puntos de portafolios optimizados, incluirlos en el rango
            let focusVol = null, focusRet = null;
            if (portfolioPoints && Object.keys(portfolioPoints).length > 0) {
                const points = Object.values(portfolioPoints).filter(p => p && p.volatilidad !== undefined && p.retorno !== undefined);
                if (points.length > 0) {
                    focusVol = points.map(p => p.volatilidad);
                    focusRet = points.map(p => p.retorno);
                    // Incluir los puntos optimizados en los rangos
                    volatilities.push(...focusVol);
                    returns.push(...focusRet);
                }
            }
            
            // Calcular rangos con margen para visualización
            const minVol = Math.min(...volatilities);
            const maxVol = Math.max(...volatilities);
            const minRet = Math.min(...returns);
            const maxRet = Math.max(...returns);
            
            // Agregar margen del 10% para mejor visualización
            const volRange = maxVol - minVol;
            const retRange = maxRet - minRet;
            const minVol_final = Math.max(0, minVol - volRange * 0.1);
            const maxVol_final = maxVol + volRange * 0.1;
            const minRet_final = minRet - retRange * 0.1;
            const maxRet_final = maxRet + retRange * 0.1;
            
            const volRange_final = maxVol_final - minVol_final || 1;
            const retRange_final = maxRet_final - minRet_final || 1;
            
            // Escalar coordenadas usando los rangos finales
            const scaleX = (vol) => padding.left + ((vol - minVol_final) / volRange_final) * chartWidth;
            const scaleY = (ret) => padding.top + chartHeight - ((ret - minRet_final) / retRange_final) * chartHeight;
            
            // Filtrar puntos que están dentro del rango visible (solo la mejor mitad)
            const visiblePoints = mejorMitad.filter(p => 
                p.volatilidad >= minVol_final && p.volatilidad <= maxVol_final &&
                p.retorno >= minRet_final && p.retorno <= maxRet_final
            );
            
            // Dibujar nube de portafolios simulados como dispersión
            ctx.fillStyle = 'rgba(59, 130, 246, 0.15)'; // Más transparente
            visiblePoints.forEach(point => {
                const x = scaleX(point.volatilidad);
                const y = scaleY(point.retorno);
                ctx.beginPath();
                ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
                ctx.fill();
            });
            
            // Dibujar puntos de portafolios específicos
            if (portfolioPoints) {
                const pointColors = {
                    'composicion_global': '#f59e0b',  // Naranja
                    'maximo_sharpe': '#10b981',       // Verde
                    'minima_volatilidad': '#3b82f6'    // Azul
                };
                
                const pointLabels = {
                    'composicion_global': 'Pesos Iguales',
                    'maximo_sharpe': 'Máx Sharpe',
                    'minima_volatilidad': 'Mín Vol'
                };
                
                Object.entries(portfolioPoints).forEach(([key, point]) => {
                    if (!point || point.volatilidad === undefined || point.retorno === undefined) return;
                    
                    // Verificar que el punto esté en el rango visible
                    if (point.volatilidad < minVol_final || point.volatilidad > maxVol_final ||
                        point.retorno < minRet_final || point.retorno > maxRet_final) {
                        return; // Saltar puntos fuera del rango
                    }
                    
                    const x = scaleX(point.volatilidad);
                    const y = scaleY(point.retorno);
                    const color = pointColors[key] || '#ef4444';
                    
                    // Sombra del punto
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                    ctx.beginPath();
                    ctx.arc(x + 3, y + 3, 12, 0, 2 * Math.PI);
                    ctx.fill();
                    
                    // Círculo exterior más grande y visible
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(x, y, 12, 0, 2 * Math.PI);
                    ctx.fill();
                    
                    // Borde blanco grueso
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                    
                    // Círculo interior blanco
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(x, y, 6, 0, 2 * Math.PI);
                    ctx.fill();
                    
                    // Fondo para etiqueta con información detallada
                    const label = pointLabels[key] || key;
                    const labelText = `${label} (${(point.retorno * 100).toFixed(2)}%, ${(point.volatilidad * 100).toFixed(2)}%)`;
                    ctx.font = '700 13px Inter';
                    const textMetrics = ctx.measureText(labelText);
                    const textWidth = textMetrics.width;
                    const textHeight = 18;
                    const textX = x + 18;
                    const textY = y - 10;
                    
                    // Fondo semitransparente con sombra
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                    ctx.fillRect(textX - 2, textY + 2, textWidth + 10, textHeight);
                    
                    ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
                    ctx.fillRect(textX - 4, textY, textWidth + 10, textHeight);
                    
                    // Borde del fondo
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.strokeRect(textX - 4, textY, textWidth + 10, textHeight);
                    
                    // Etiqueta con información
                    ctx.fillStyle = '#f1f5f9';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(labelText, textX, textY + textHeight / 2);
                });
            }
            
            // Ejes
            ctx.strokeStyle = '#475569';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(padding.left, padding.top);
            ctx.lineTo(padding.left, canvasHeight - padding.bottom);
            ctx.lineTo(canvasWidth - padding.right, canvasHeight - padding.bottom);
            ctx.stroke();
            
            // Etiquetas de ejes
            ctx.fillStyle = '#cbd5e1';
            ctx.font = '500 13px Inter';
            ctx.textAlign = 'center';
            ctx.fillText('Volatilidad (Riesgo)', canvasWidth / 2, canvasHeight - 20);
            
            ctx.save();
            ctx.translate(20, canvasHeight / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText('Retorno Esperado', 0, 0);
            ctx.restore();
            
            // Etiquetas de valores en ejes
            ctx.fillStyle = '#94a3b8';
            ctx.font = '500 11px Roboto Mono';
            ctx.textAlign = 'right';
            
            // Eje Y (retornos)
            const numYTicks = 6;
            for (let i = 0; i <= numYTicks; i++) {
                const value = minRet_final + (i * retRange_final / numYTicks);
                const y = scaleY(value);
                ctx.fillText((value * 100).toFixed(1) + '%', padding.left - 10, y + 4);
            }
            
            // Eje X (volatilidades)
            ctx.textAlign = 'center';
            const numXTicks = 6;
            for (let i = 0; i <= numXTicks; i++) {
                const value = minVol_final + (i * volRange_final / numXTicks);
                const x = scaleX(value);
                ctx.fillText((value * 100).toFixed(1) + '%', x, canvasHeight - padding.bottom + 20);
            }
            
            // Título
            ctx.fillStyle = '#f8fafc';
            ctx.font = '700 18px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(title || 'Frontera Eficiente', canvasWidth / 2, 30);
        }
        
        // Función para renderizar slide de portafolio
        function renderPortfolioSlide(portfolioKey, portfolioData, portfolioIndex, slideIndexOffset) {
            const portfolioTypes = ['composicion_global', 'maximo_sharpe', 'minima_volatilidad'];
            const typeLabels = {
                'composicion_global': 'Pesos Iguales',
                'maximo_sharpe': 'Optimización: Máximo Sharpe',
                'minima_volatilidad': 'Optimización: Mínima Volatilidad'
            };
            
            return portfolioTypes.map((type, typeIdx) => {
                const data = portfolioData[type];
                
                // Validar que data existe y tiene los campos mínimos requeridos
                if (!data || data === null || data === undefined) {
                    console.warn(`⚠️  Portafolio ${portfolioKey} - ${type} tiene datos null/undefined`);
                    return '';
                }
                
                // Validar que tiene los campos esenciales
                if (data.retorno_anual === undefined || data.volatilidad_anual === undefined || 
                    data.sharpe_ratio === undefined || !data.asignacion || !Array.isArray(data.asignacion)) {
                    console.warn(`⚠️  Portafolio ${portfolioKey} - ${type} tiene datos incompletos:`, data);
                    return '';
                }
                
                const slideIndex = slideIndexOffset + (portfolioIndex * 3) + typeIdx;
                const slideId = `slide-${portfolioKey}-${type}-${portfolioIndex}`;
                const chartId = `chart-${portfolioKey}-${type}-${portfolioIndex}`;
                const barChartId = `barchart-${portfolioKey}-${type}-${portfolioIndex}`;
                
                const metricasMC = data.metricas_montecarlo || {};
                const probGanar = (metricasMC.prob_ganar || 0) * 100;
                const probPerder = (metricasMC.prob_perder || 0) * 100;
                
                // Calcular Sharpe bruto (sin tasa libre de riesgo) y Sharpe ajustado (8% USD)
                const sharpeBruto = data.volatilidad_anual > 0 ? (data.retorno_anual / data.volatilidad_anual) : 0;
                const sharpeRf = (typeof data.sharpe_ratio === 'number') ? data.sharpe_ratio : sharpeBruto;
                
                const nActivos = portfolioData.n_activos || (data.asignacion ? data.asignacion.length : 0);
                // Limpiar el nombre del portafolio para quitar redundancias como "(10 activos)" o "(30 activos)"
                const nombreLimpio = portfolioData.nombre.replace(/\\s*\\(\\d+\\s*activos?\\)/gi, '').trim();
        return `
                    <div id="${slideId}" class="slide ${slideIndex === 0 ? 'active' : ''}" data-slide-index="${slideIndex}" style="margin: 0 !important; padding: 0 !important;">
                        <div class="max-w-7xl mx-auto px-8" style="margin: 0 !important; padding: 0 !important;">
                            <!-- Banner de ancho completo con métricas -->
                            <div class="card p-8 mb-6 bg-gradient-to-r from-slate-800 to-slate-900 border border-slate-700" style="margin-top: 0 !important; padding-top: 1.5rem !important;">
                                <div class="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
                                    <div>
                                        <h2 class="text-4xl font-bold mb-2 text-slate-100">${nombreLimpio}</h2>
                                        <h3 class="text-2xl text-slate-300 font-semibold">${typeLabels[type]} • ${nActivos} activos</h3>
                                        <button onclick="downloadPortfolioJSON('${portfolioKey}', '${type}')" class="mt-4 px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors text-white font-semibold">
                                            Comprar Portafolio
                                        </button>
                                    </div>
                                    <div class="mt-4 md:mt-0">
                                        <div class="grid grid-cols-4 gap-4 text-center">
                                            <div>
                                                <div class="text-xs text-slate-400 mb-1">Retorno Anual</div>
                                                <div class="text-xl font-bold ${data.retorno_anual >= 0 ? 'text-green-400' : 'text-red-400'}">${(data.retorno_anual * 100).toFixed(2)}%</div>
                                            </div>
                                            <div>
                                                <div class="text-xs text-slate-400 mb-1">Riesgo (Volatilidad)</div>
                                                <div class="text-xl font-bold text-slate-300">${(data.volatilidad_anual * 100).toFixed(2)}%</div>
                                            </div>
                                            <div>
                                                <div class="text-xs text-slate-400 mb-1">Sharpe (bruto / 8% RF)</div>
                                                <div class="text-sm font-mono text-slate-300">
                                                    <span class="${sharpeBruto >= 1 ? 'text-green-400' : sharpeBruto >= 0.5 ? 'text-yellow-400' : 'text-red-400'} mr-1">${sharpeBruto.toFixed(2)}</span>
                                                    <span class="text-slate-500">/</span>
                                                    <span class="${sharpeRf >= 1 ? 'text-green-400' : sharpeRf >= 0.5 ? 'text-yellow-400' : 'text-red-400'} ml-1">${sharpeRf.toFixed(2)}</span>
                                                </div>
                                            </div>
                                            <div>
                                                <div class="text-xs text-slate-400 mb-1">Prob. Ganar / Perder</div>
                                                <div class="text-sm font-mono text-slate-300">
                                                    <span class="${probGanar >= 70 ? 'text-green-400' : probGanar >= 50 ? 'text-yellow-400' : 'text-red-400'} mr-1">${probGanar.toFixed(1)}%</span>
                                                    <span class="text-slate-500">/</span>
                                                    <span class="${probPerder <= 20 ? 'text-green-400' : probPerder <= 40 ? 'text-yellow-400' : 'text-red-400'} ml-1">${probPerder.toFixed(1)}%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Retornos Proyectados a Distintos Horizontes - MINI TAB -->
                                <div class="mb-6">
                                    <button onclick="toggleRetornosProyectados('${slideId}')" class="flex items-center justify-between w-full text-left mb-2 p-2 hover:bg-slate-700/30 rounded transition-colors">
                                        <h5 class="text-xs font-semibold text-slate-400">Retornos Proyectados a Distintos Horizontes</h5>
                                        <svg id="icon-retornos-${slideId}" class="w-4 h-4 text-slate-400 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </button>
                                    <div id="retornos-proyectados-${slideId}" class="hidden">
                                        ${(() => {
                                            const retorno_anual = data.retorno_anual || 0;
                                            const monto = OPTIMIZATION_DATA.monto_inversion || 10000;
                                            const horizontes = [
                                                { nombre: '1 Mes', dias: 21 },
                                                { nombre: '3 Meses', dias: 63 },
                                                { nombre: '6 Meses', dias: 126 },
                                                { nombre: '1 Año', dias: 252 },
                                                { nombre: '2 Años', dias: 504 },
                                                { nombre: '3 Años', dias: 756 }
                                            ];
                                            var tablaProyecciones = '<table class="w-full text-xs border-collapse">' +
                                                '<thead>' +
                                                '<tr class="border-b border-slate-600">' +
                                                '<th class="text-left py-2 px-3 text-slate-300 font-semibold">Horizonte</th>' +
                                                '<th class="text-right py-2 px-3 text-slate-300 font-semibold">Retorno Proyectado</th>' +
                                                '<th class="text-right py-2 px-3 text-slate-300 font-semibold">Valor Proyectado</th>' +
                                                '<th class="text-right py-2 px-3 text-slate-300 font-semibold">Ganancia/Pérdida</th>' +
                                                '</tr>' +
                                                '</thead>' +
                                                '<tbody>';
                                            horizontes.forEach(function(h) {
                                                const retorno_proyectado = Math.pow(1 + retorno_anual, h.dias / 252) - 1;
                                                const valor_proyectado = monto * (1 + retorno_proyectado);
                                                const ganancia_proyectada = valor_proyectado - monto;
                                                const retornoColor = retorno_proyectado >= 0 ? 'text-green-400' : 'text-red-400';
                                                const gananciaColor = ganancia_proyectada >= 0 ? 'text-green-400' : 'text-red-400';
                                                tablaProyecciones += '<tr class="border-b border-slate-700/30">' +
                                                    '<td class="py-2 px-3 text-slate-400">' + h.nombre + '</td>' +
                                                    '<td class="py-2 px-3 text-right font-mono ' + retornoColor + '">' + (retorno_proyectado * 100).toFixed(2) + '%</td>' +
                                                    '<td class="py-2 px-3 text-right font-mono text-slate-300">' + formatCurrency(valor_proyectado) + '</td>' +
                                                    '<td class="py-2 px-3 text-right font-mono ' + gananciaColor + '">' + formatCurrency(ganancia_proyectada) + '</td>' +
                                                    '</tr>';
                                            });
                                            tablaProyecciones += '</tbody></table>';
                                            return tablaProyecciones;
                                        })()}
                                    </div>
                                </div>
                                
                                <!-- Mini DataFrame Comparativo: Solo Ganancias y Pérdidas - COLAPSABLE -->
                                <div class="mb-6">
                                    <button onclick="toggleComparativo('${slideId}')" class="flex items-center justify-between w-full text-left mb-2 p-2 hover:bg-slate-700/30 rounded transition-colors">
                                        <h5 class="text-xs font-semibold text-slate-400">Comparativo de Ganancias y Pérdidas</h5>
                                        <svg id="icon-${slideId}" class="w-4 h-4 text-slate-400 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </button>
                                    <div id="comparativo-${slideId}" class="hidden overflow-x-auto">
                                        <table class="w-full text-xs border-collapse">
                                            <thead>
                                                <tr class="border-b border-slate-600">
                                                    <th class="text-left py-1 px-2 text-slate-300 font-semibold text-xs">Escenario</th>
                                                    <th class="text-right py-1 px-2 text-slate-300 font-semibold text-xs bg-slate-800/50">Optimización (Pesos)</th>
                                                    <th class="text-right py-1 px-2 text-slate-300 font-semibold text-xs bg-blue-900/30">Monte Carlo (5000)</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr class="border-b border-slate-700/30">
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. 50% (Mediana)</td>
                                                    <td class="py-1 px-2 text-right font-bold text-blue-400 bg-slate-800/30 text-xs">${(data.percentiles && data.percentiles[50] && data.percentiles[50].pnl !== undefined && data.percentiles[50].pnl !== null && data.percentiles[50].pnl !== 0) ? formatCurrency(data.percentiles[50].pnl) : formatCurrency(data.ganancia_esperada)}</td>
                                                    <td class="py-1 px-2 text-right font-bold text-blue-400 bg-blue-900/20 text-xs">${formatCurrency(metricasMC.ganancia_mediana || 0)}</td>
                                                </tr>
                                                <tr class="border-b border-slate-700/30">
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. 25% (Escenario Bajo)</td>
                                                    <td class="py-1 px-2 text-right font-bold text-red-400 bg-slate-800/30 text-xs">${(data.percentiles && data.percentiles[25] && data.percentiles[25].pnl !== undefined && data.percentiles[25].pnl !== null && data.percentiles[25].pnl !== 0) ? formatCurrency(data.percentiles[25].pnl) : '-'}</td>
                                                    <td class="py-1 px-2 text-right font-bold text-red-400 bg-blue-900/20 text-xs">${formatCurrency(metricasMC.percentil_25 || 0)}</td>
                                                </tr>
                                                <tr class="border-b border-slate-700/30">
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. 75% (Escenario Alto)</td>
                                                    <td class="py-1 px-2 text-right font-bold text-orange-400 bg-slate-800/30 text-xs">${(data.percentiles && data.percentiles[75] && data.percentiles[75].pnl !== undefined && data.percentiles[75].pnl !== null && data.percentiles[75].pnl !== 0) ? formatCurrency(data.percentiles[75].pnl) : '-'}</td>
                                                    <td class="py-1 px-2 text-right font-bold text-orange-400 bg-blue-900/20 text-xs">${formatCurrency(metricasMC.percentil_75 || 0)}</td>
                                                </tr>
                                                <tr class="border-b border-slate-700/30">
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. 5% (Escenario Pesimista)</td>
                                                    <td class="py-1 px-2 text-right font-bold text-red-400 bg-slate-800/30 text-xs">${(data.percentiles && data.percentiles[5] && data.percentiles[5].pnl !== undefined && data.percentiles[5].pnl !== null && data.percentiles[5].pnl !== 0) ? formatCurrency(data.percentiles[5].pnl) : '-'}</td>
                                                    <td class="py-1 px-2 text-right font-bold text-red-400 bg-blue-900/20 text-xs">${formatCurrency(metricasMC.percentil_5 || 0)}</td>
                                                </tr>
                                                <tr class="border-b border-slate-700/30">
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. 95% (Escenario Optimista)</td>
                                                    <td class="py-1 px-2 text-right font-bold text-green-400 bg-slate-800/30 text-xs">${(data.percentiles && data.percentiles[95] && data.percentiles[95].pnl !== undefined && data.percentiles[95].pnl !== null && data.percentiles[95].pnl !== 0) ? formatCurrency(data.percentiles[95].pnl) : '-'}</td>
                                                    <td class="py-1 px-2 text-right font-bold text-green-400 bg-blue-900/20 text-xs">${formatCurrency(metricasMC.percentil_95 || 0)}</td>
                                                </tr>
                                                <tr>
                                                    <td class="py-1 px-2 text-slate-400 text-xs">Prob. Ganar / Perder</td>
                                                    <td class="py-1 px-2 text-right font-bold bg-slate-800/30 text-xs">
                                                        <span class="text-green-400">${((data.probabilidades && data.probabilidades.prob_ganancia) ? data.probabilidades.prob_ganancia.toFixed(1) : 0)}%</span> / 
                                                        <span class="text-red-400">${((data.probabilidades && data.probabilidades.prob_perdida) ? data.probabilidades.prob_perdida.toFixed(1) : 0)}%</span>
                                                    </td>
                                                    <td class="py-1 px-2 text-right font-bold bg-blue-900/20 text-xs">
                                                        <span class="text-green-400">${((metricasMC.prob_ganar || 0) * 100).toFixed(1)}%</span> / 
                                                        <span class="text-red-400">${((metricasMC.prob_perder || 0) * 100).toFixed(1)}%</span>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Gráfico de Frontera Eficiente - PRIMERO -->
                                <div class="card p-6 mb-6">
                                    <h4 class="text-xl font-bold mb-6 text-slate-100">Frontera Eficiente (Monte Carlo - 5000 simulaciones)</h4>
                                    <div class="w-full flex justify-center items-center" style="min-height: 500px;">
                                        <canvas id="frontier-${portfolioKey}-${type}-${portfolioIndex}" width="1400" height="700" style="max-width: 100%; height: auto; width: 100%;"></canvas>
                                    </div>
                                </div>
                            
                            <!-- Gráfico de Composición del Portafolio - Ancho completo -->
                                <div class="card p-6 mb-6">
                                    <h4 class="text-xl font-bold mb-6 text-slate-100">Composición del Portafolio</h4>
                                    <div class="w-full flex justify-center items-center" style="min-height: 500px;">
                                        <canvas id="${chartId}" width="1000" height="700" style="max-width: 100%; height: auto; width: 100%;"></canvas>
                                    </div>
                                </div>
                                
                                <!-- Gráfico de Escenarios de P&L - Ancho completo -->
                                <div class="card p-6 mb-6">
                                    <h4 class="text-xl font-bold mb-6 text-slate-100">Escenarios de P&L</h4>
                                    <div class="w-full flex justify-center items-center" style="min-height: 500px;">
                                        <canvas id="${barChartId}" width="1400" height="700" style="max-width: 100%; height: auto; width: 100%;"></canvas>
                                    </div>
                                </div>
                                
                                <div class="card p-6">
                                    <h4 class="text-lg font-semibold mb-4">Asignación Detallada</h4>
                                    <div class="overflow-x-auto">
                                        <table class="w-full text-sm">
                                            <thead>
                                                <tr class="border-b border-slate-700">
                                                    <th class="text-left py-2">Ticker</th>
                                                    <th class="text-left py-2">Sector</th>
                                                    <th class="text-right py-2">Peso (%)</th>
                                                    <th class="text-right py-2">Asignación ($)</th>
                                                    <th class="text-right py-2">Precio Actual</th>
                                                    <th class="text-right py-2">Cantidad</th>
                                                    <th class="text-right py-2">Retorno Anual (%)</th>
                                                    <th class="text-right py-2">Volatilidad Anual (%)</th>
                                                    <th class="text-right py-2">Sharpe Ratio</th>
                                                    <th class="text-right py-2">Sesgo</th>
                                                    <th class="text-right py-2">Ganancia Esperada</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${(function() {
                                                    var tablaAsignacion = '';
                                                    data.asignacion.forEach(function(item) {
                                                        // Obtener sector y métricas individuales del ticker
                                                        const metricas = (portfolioData.metricas_activos || []).find(function(m) { return m.ticker === item.ticker; });
                                                        const sector = item.sector || (metricas && metricas.sector) || 'Desconocido';
                                                        const retorno_anual = (metricas && metricas.retorno_anual) || 0;
                                                        const volatilidad_anual = (metricas && metricas.volatilidad_anual) || 0;
                                                        const sharpe_ratio = (metricas && metricas.sharpe_ratio) || 0;
                                                        const skewness_valor = (metricas && metricas.skewness) || 0;
                                                        const skewness_color = skewness_valor > 0.5 ? 'text-green-400' : skewness_valor < -0.5 ? 'text-red-400' : 'text-slate-400';
                                                        const retornoColor = retorno_anual >= 0 ? 'text-green-400' : 'text-red-400';
                                                        const sharpeColor = sharpe_ratio >= 1 ? 'text-green-400' : sharpe_ratio >= 0.5 ? 'text-yellow-400' : 'text-red-400';
                                                        const gananciaColor = item.ganancia_esperada >= 0 ? 'text-green-400' : 'text-red-400';
                                                        tablaAsignacion += '<tr class="border-b border-slate-800">' +
                                                            '<td class="py-2 font-medium">' + item.ticker + '</td>' +
                                                            '<td class="py-2 text-slate-400">' + sector + '</td>' +
                                                            '<td class="text-right py-2">' + item.peso_porcentaje.toFixed(2) + '%</td>' +
                                                            '<td class="text-right py-2">' + formatCurrency(item.asignacion_dinero) + '</td>' +
                                                            '<td class="text-right py-2">' + formatCurrency(item.precio_actual) + '</td>' +
                                                            '<td class="text-right py-2">' + Math.round(item.cantidad) + '</td>' +
                                                            '<td class="text-right py-2 ' + retornoColor + '">' + (retorno_anual * 100).toFixed(2) + '%</td>' +
                                                            '<td class="text-right py-2">' + (volatilidad_anual * 100).toFixed(2) + '%</td>' +
                                                            '<td class="text-right py-2 ' + sharpeColor + '">' + sharpe_ratio.toFixed(2) + '</td>' +
                                                            '<td class="text-right py-2 ' + skewness_color + '">' + skewness_valor.toFixed(3) + '</td>' +
                                                            '<td class="text-right py-2 ' + gananciaColor + '">' + formatCurrency(item.ganancia_esperada) + '</td>' +
                                                            '</tr>';
                                                    });
                                                    return tablaAsignacion;
                                                })()}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                                
                                <div class="card p-6 mt-6">
                                    <h4 class="text-lg font-semibold mb-4">Métricas entre Activos (Correlación, R², Beta, Alpha)</h4>
                                    <div class="overflow-x-auto">
                                        ${(function() {
                                            // Usar métricas específicas de esta optimización si están disponibles
                                            // Si no, usar las métricas globales (legacy)
                                            const metricas_especificas = data.metricas_pares_activos || portfolioData.metricas_pares_activos || [];
                                            
                                            if (!metricas_especificas || metricas_especificas.length === 0) {
                                                return '<div class="text-slate-400 text-sm py-4 text-center">No hay datos de métricas entre activos disponibles. Verifique que el portafolio tenga al menos 2 activos con datos históricos.</div>';
                                            }
                                            
                                            // Las métricas específicas ya están filtradas para esta optimización
                                            // Solo necesitamos aplicar el filtro de alta correlación si es necesario
                                            const pesos_actuales = data.pesos || {};
                                            
                                            // Crear conjunto de activos con peso > 0 para validación adicional
                                            const activos_con_peso = new Set();
                                            for (const [ticker, peso] of Object.entries(pesos_actuales)) {
                                                const pesoNum = typeof peso === 'number' ? peso : parseFloat(peso) || 0;
                                                if (pesoNum > 0.0001) {
                                                    activos_con_peso.add(ticker);
                                                }
                                            }
                                            
                                            // Validación: asegurar que los pares solo incluyen activos con peso > 0
                                            const pares_filtrados = metricas_especificas.filter(pair => {
                                                const activo1_en_portafolio = activos_con_peso.has(pair.activo1);
                                                const activo2_en_portafolio = activos_con_peso.has(pair.activo2);
                                                return activo1_en_portafolio && activo2_en_portafolio;
                                            });
                                            
                                            // Para portafolios especiales, aplicar filtros adicionales
                                            const nombre_portafolio = portfolioData.nombre || '';
                                            let pares_finales = pares_filtrados;
                                            
                                            // Filtro para portafolio "Alta Correlación": solo mostrar pares con |correlación| >= 0.70
                                            if (nombre_portafolio.includes('Alta Correlación')) {
                                                const UMBRAL_CORR_ALTA = 0.70;
                                                pares_finales = pares_filtrados.filter(pair => {
                                                    const corr = typeof pair.correlacion === 'number' ? pair.correlacion : parseFloat(pair.correlacion) || 0;
                                                    return Math.abs(corr) >= UMBRAL_CORR_ALTA;
                                                });
                                                // Ordenar por correlación absoluta descendente
                                                pares_finales.sort((a, b) => {
                                                    const corrA = Math.abs(typeof a.correlacion === 'number' ? a.correlacion : parseFloat(a.correlacion) || 0);
                                                    const corrB = Math.abs(typeof b.correlacion === 'number' ? b.correlacion : parseFloat(b.correlacion) || 0);
                                                    return corrB - corrA;
                                                });
                                            }
                                            
                                            // Filtro para portafolio "Correlación Negativa": solo mostrar pares con correlación < 0
                                            if (nombre_portafolio.includes('Correlación Negativa')) {
                                                pares_finales = pares_filtrados.filter(pair => {
                                                    const corr = typeof pair.correlacion === 'number' ? pair.correlacion : parseFloat(pair.correlacion) || 0;
                                                    return corr < 0.0;
                                                });
                                            }
                                            
                                            // Debug: mostrar cantidad de pares filtrados
                                            // console.log('Pares después de filtrar:', pares_finales.length);
                                            
                                            // Mensajes específicos según el tipo de portafolio y cantidad de pares
                                            if (pares_finales.length === 0) {
                                                let mensaje = '';
                                                if (nombre_portafolio.includes('Alta Correlación')) {
                                                    mensaje = '<div class="text-yellow-400 text-sm py-4 text-center border border-yellow-600 rounded p-4 bg-yellow-900/20">' +
                                                        '<p class="font-semibold mb-2">⚠️ No se encontraron pares con alta correlación (≥ 0.70)</p>' +
                                                        '<p class="text-xs text-slate-400">El portafolio optimizado no contiene suficientes pares de activos con correlación alta entre sí. ' +
                                                        'Esto puede indicar que la optimización seleccionó activos con baja correlación, lo cual es beneficioso para la diversificación pero no cumple con el criterio de "Alta Correlación".</p>' +
                                                        '<p class="text-xs text-slate-400 mt-2">Total de pares calculados: ' + pares_filtrados.length + '</p>' +
                                                        '</div>';
                                                } else if (nombre_portafolio.includes('Correlación Negativa')) {
                                                    mensaje = '<div class="text-yellow-400 text-sm py-4 text-center border border-yellow-600 rounded p-4 bg-yellow-900/20">' +
                                                        '<p class="font-semibold mb-2">⚠️ No se encontraron pares con correlación negativa</p>' +
                                                        '<p class="text-xs text-slate-400">El portafolio optimizado no contiene pares de activos con correlación negativa entre sí.</p>' +
                                                        '</div>';
                                                } else {
                                                    mensaje = '<div class="text-slate-400 text-sm py-4 text-center">No hay pares de activos con métricas disponibles para esta optimización. Verifique que el portafolio tenga al menos 2 activos con peso > 0.</div>';
                                                }
                                                return mensaje;
                                            } else if (pares_finales.length === 1 && nombre_portafolio.includes('Alta Correlación')) {
                                                // Mostrar advertencia cuando solo hay un par con alta correlación
                                                const par_unico = pares_finales[0];
                                                const corr = typeof par_unico.correlacion === 'number' ? par_unico.correlacion : parseFloat(par_unico.correlacion) || 0;
                                                return '<div class="mb-4">' +
                                                    '<div class="text-yellow-400 text-xs py-2 px-3 border border-yellow-600 rounded mb-3 bg-yellow-900/20">' +
                                                    '<p class="font-semibold">⚠️ Solo se encontró 1 par con alta correlación (≥ 0.70)</p>' +
                                                    '<p class="text-slate-400 text-xs mt-1">El portafolio optimizado tiene muy pocos activos con alta correlación entre sí. Esto puede indicar que la optimización priorizó la diversificación sobre la alta correlación.</p>' +
                                                    '</div>' +
                                                    '<table class="w-full text-sm">' +
                                                    '<thead>' +
                                                    '<tr class="border-b border-slate-700">' +
                                                    '<th class="text-left py-2">Activo 1</th>' +
                                                    '<th class="text-left py-2">Activo 2</th>' +
                                                    '<th class="text-right py-2">Correlación</th>' +
                                                    '<th class="text-right py-2">R²</th>' +
                                                    '<th class="text-right py-2">Beta</th>' +
                                                    '<th class="text-right py-2">Alpha Anual (%)</th>' +
                                                    '</tr>' +
                                                    '</thead>' +
                                                    '<tbody>' +
                                                    '<tr class="border-b border-slate-800">' +
                                                    '<td class="py-2 font-medium">' + par_unico.activo1 + '</td>' +
                                                    '<td class="py-2 font-medium">' + par_unico.activo2 + '</td>' +
                                                    '<td class="text-right py-2 text-orange-400">' + corr.toFixed(3) + '</td>' +
                                                    '<td class="text-right py-2">' + (typeof par_unico.r_squared === 'number' ? par_unico.r_squared.toFixed(3) : parseFloat(par_unico.r_squared || 0).toFixed(3)) + '</td>' +
                                                    '<td class="text-right py-2">' + (typeof par_unico.beta === 'number' ? par_unico.beta.toFixed(3) : parseFloat(par_unico.beta || 0).toFixed(3)) + '</td>' +
                                                    '<td class="text-right py-2">' + ((typeof par_unico.alpha_anual === 'number' ? par_unico.alpha_anual : parseFloat(par_unico.alpha_anual || 0)) * 100).toFixed(4) + '%</td>' +
                                                    '</tr>' +
                                                    '</tbody>' +
                                                    '</table>' +
                                                    '</div>';
                                            } else if (pares_finales.length < 5 && nombre_portafolio.includes('Alta Correlación')) {
                                                // Mostrar advertencia cuando hay pocos pares con alta correlación
                                                var tablaHTML_pocos = '<div class="mb-4">' +
                                                    '<div class="text-yellow-400 text-xs py-2 px-3 border border-yellow-600 rounded mb-3 bg-yellow-900/20">' +
                                                    '<p class="font-semibold">⚠️ Se encontraron solo ' + pares_finales.length + ' pares con alta correlación (≥ 0.70)</p>' +
                                                    '<p class="text-slate-400 text-xs mt-1">El portafolio optimizado tiene limitada diversificación por alta correlación. Esto puede indicar que la optimización priorizó la diversificación sobre la alta correlación.</p>' +
                                                    '</div>' +
                                                    '<table class="w-full text-sm">' +
                                                    '<thead>' +
                                                    '<tr class="border-b border-slate-700">' +
                                                    '<th class="text-left py-2">Activo 1</th>' +
                                                    '<th class="text-left py-2">Activo 2</th>' +
                                                    '<th class="text-right py-2">Correlación</th>' +
                                                    '<th class="text-right py-2">R²</th>' +
                                                    '<th class="text-right py-2">Beta</th>' +
                                                    '<th class="text-right py-2">Alpha Anual (%)</th>' +
                                                    '</tr>' +
                                                    '</thead>' +
                                                    '<tbody>';
                                                pares_finales.forEach(function(pair) {
                                                    var corr = typeof pair.correlacion === "number" ? pair.correlacion : parseFloat(pair.correlacion) || 0;
                                                    var r2 = typeof pair.r_squared === "number" ? pair.r_squared : parseFloat(pair.r_squared || 0);
                                                    var beta = typeof pair.beta === "number" ? pair.beta : parseFloat(pair.beta || 0);
                                                    var alpha = typeof pair.alpha_anual === "number" ? pair.alpha_anual : parseFloat(pair.alpha_anual || 0);
                                                    tablaHTML_pocos += '<tr class="border-b border-slate-800">' +
                                                        '<td class="py-2 font-medium">' + pair.activo1 + '</td>' +
                                                        '<td class="py-2 font-medium">' + pair.activo2 + '</td>' +
                                                        '<td class="text-right py-2 text-orange-400">' + corr.toFixed(3) + '</td>' +
                                                        '<td class="text-right py-2">' + r2.toFixed(3) + '</td>' +
                                                        '<td class="text-right py-2">' + beta.toFixed(3) + '</td>' +
                                                        '<td class="text-right py-2">' + (alpha * 100).toFixed(4) + '%</td>' +
                                                        '</tr>';
                                                });
                                                tablaHTML_pocos += '</tbody></table></div>';
                                                return tablaHTML_pocos;
                                            }
                                            
                                            // Tabla normal cuando hay múltiples pares - construir HTML usando concatenación
                                            var tablaHTML = '<table class="w-full text-sm">' +
                                                '<thead>' +
                                                '<tr class="border-b border-slate-700">' +
                                                '<th class="text-left py-2">Activo 1</th>' +
                                                '<th class="text-left py-2">Activo 2</th>' +
                                                '<th class="text-right py-2">Correlación</th>' +
                                                '<th class="text-right py-2">R²</th>' +
                                                '<th class="text-right py-2">Beta</th>' +
                                                '<th class="text-right py-2">Alpha Anual (%)</th>' +
                                                '</tr>' +
                                                '</thead>' +
                                                '<tbody>';
                                            pares_finales.forEach(function(pair) {
                                                var corr = typeof pair.correlacion === "number" ? pair.correlacion : parseFloat(pair.correlacion) || 0;
                                                var r2 = typeof pair.r_squared === "number" ? pair.r_squared : parseFloat(pair.r_squared || 0);
                                                var beta = typeof pair.beta === "number" ? pair.beta : parseFloat(pair.beta || 0);
                                                var alpha = typeof pair.alpha_anual === "number" ? pair.alpha_anual : parseFloat(pair.alpha_anual || 0);
                                                var corrColor = Math.abs(corr) > 0.7 ? "text-orange-400" : Math.abs(corr) < 0.3 ? "text-green-400" : "text-slate-300";
                                                var betaColor = Math.abs(beta - 1) < 0.2 ? "text-blue-400" : beta > 1 ? "text-orange-400" : "text-slate-300";
                                                var alphaColor = alpha >= 0 ? "text-green-400" : "text-red-400";
                                                tablaHTML += '<tr class="border-b border-slate-800">' +
                                                    '<td class="py-2 font-medium">' + pair.activo1 + '</td>' +
                                                    '<td class="py-2 font-medium">' + pair.activo2 + '</td>' +
                                                    '<td class="text-right py-2 ' + corrColor + '">' + corr.toFixed(3) + '</td>' +
                                                    '<td class="text-right py-2">' + r2.toFixed(3) + '</td>' +
                                                    '<td class="text-right py-2 ' + betaColor + '">' + beta.toFixed(3) + '</td>' +
                                                    '<td class="text-right py-2 ' + alphaColor + '">' + (alpha * 100).toFixed(4) + '%</td>' +
                                                    '</tr>';
                                            });
                                            tablaHTML += '</tbody></table>';
                                            return tablaHTML;
                                        })()}
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Inicializar aplicación
        document.addEventListener('DOMContentLoaded', () => {
            const root = document.getElementById('root');
            if (!root) return;
            
            // Crear estructura con tabs
            let htmlContent = `
                <div class="">
                    <header class="header w-full p-1 backdrop-blur-sm z-50" style="margin:0 !important; padding-top:0 !important; position: relative;">
                        <div class="max-w-7xl mx-auto flex justify-between items-center">
                            <div class="flex items-center gap-4">
                                <h1 class="text-xl font-bold">Análisis de Optimizaciones de Portafolios</h1>
                                <div class="template-selector">
                                    <label for="template-select">Plantilla</label>
                                    <select id="template-select" onchange="changeTemplate(this.value)">
                                        ${Object.entries(TEMPLATES).map(([id, t]) => 
                                            `<option value="${id}" ${id === currentTemplate ? 'selected' : ''}>${t.name}</option>`
                                        ).join('')}
                                    </select>
                                </div>
                            </div>
                            <div class="flex items-center gap-4">
                                <button id="prev-slide" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors" style="display: none;">← Anterior</button>
                                <span id="slide-counter" class="text-sm text-slate-400" style="display: none;">1 / 1</span>
                                <button id="next-slide" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors" style="display: none;">Siguiente →</button>
                                <button id="download-all" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors" style="display: none;">Descargar Todos</button>
                                <button id="download-current" class="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg transition-colors" style="display: none;">Descargar Actual</button>
                            </div>
                        </div>
                        <div class="nav-tabs">
                            <button class="nav-tab active" data-tab="optimizaciones" onclick="switchTab('optimizaciones')">Optimizaciones</button>
                            <button class="nav-tab" data-tab="backtesting" onclick="switchTab('backtesting')">Backtesting</button>
                            <button class="nav-tab" data-tab="simulacion" onclick="switchTab('simulacion')">Simulación</button>
                        </div>
                    </header>
                    
                    <main style="padding-top: 0 !important; margin-top: 0 !important;">
                        <!-- Tab: Optimizaciones -->
                        <div id="tab-optimizaciones" class="tab-content active">
                            <div id="slide-container" style="padding-top: 0 !important; margin-top: 0 !important;">
            `;
            
            // Generar slides para cada portafolio
            let slideIndexCounter = 0;
            Object.entries(OPTIMIZATION_DATA.portafolios || {}).forEach(([key, portfolio], idx) => {
                // Validar que el portafolio existe y tiene datos
                if (!portfolio || portfolio === null || portfolio === undefined) {
                    console.warn(`⚠️  Portafolio ${key} es null/undefined, saltando...`);
                    return;
                }
                // Validar que tiene al menos uno de los tipos requeridos
                if (!portfolio.composicion_global && !portfolio.maximo_sharpe && !portfolio.minima_volatilidad) {
                    console.warn(`⚠️  Portafolio ${key} no tiene datos de composición, saltando...`);
                    return;
                }
                htmlContent += renderPortfolioSlide(key, portfolio, idx, slideIndexCounter);
                slideIndexCounter += 3; // 3 tipos por portafolio
            });
            
            // Slide de comparación completa con todas las métricas
            // Construir lista plana de portafolios (nombre + tipo) y luego ordenarla de forma lógica
            let comparacionPortafolios = Object.entries(OPTIMIZATION_DATA.portafolios).flatMap(([key, portfolio]) => {
                const nombreLimpio = portfolio.nombre.replace(/\\s*\\(\\d+\\s*activos?\\)/gi, '').trim();
                return [
                    { 
                        key,
                        nombre: nombreLimpio, 
                        tipo: 'Pesos Iguales',
                        n_activos: portfolio.n_activos || 0,
                        data: portfolio.composicion_global 
                    },
                    { 
                        key,
                        nombre: nombreLimpio, 
                        tipo: 'Máximo Sharpe',
                        n_activos: portfolio.n_activos || 0,
                        data: portfolio.maximo_sharpe 
                    },
                    { 
                        key,
                        nombre: nombreLimpio, 
                        tipo: 'Mínima Volatilidad',
                        n_activos: portfolio.n_activos || 0,
                        data: portfolio.minima_volatilidad 
                    },
                ];
            }).filter(item => item.data && item.data.retorno_anual !== undefined);

            // Orden deseado de portafolios para la tabla comparativa
            const ordenPortafolios = [
                'spy_qqq',                    // SPY + QQQ
                'alta_correlacion',           // Alta correlación (30)
                'baja_correlacion',           // Baja correlación (30)
                'alta_correlacion_ext',       // Alta correlación (60)
                'baja_correlacion_ext',       // Baja correlación (60)
                'alta_volatilidad_sesgo_positivo', // Skew positivo
                'correlacion_negativa'        // Correlación negativa
            ];

            // Orden deseado de tipos dentro de cada portafolio
            const ordenTipos = ['Pesos Iguales', 'Máximo Sharpe', 'Mínima Volatilidad'];

            // Ordenar la lista plana según portafolio y tipo
            comparacionPortafolios = comparacionPortafolios.sort((a, b) => {
                const idxA = ordenPortafolios.indexOf(a.key);
                const idxB = ordenPortafolios.indexOf(b.key);
                const ordA = idxA === -1 ? 999 : idxA;
                const ordB = idxB === -1 ? 999 : idxB;
                if (ordA !== ordB) return ordA - ordB;

                const tA = ordenTipos.indexOf(a.tipo);
                const tB = ordenTipos.indexOf(b.tipo);
                const tipoA = tA === -1 ? 999 : tA;
                const tipoB = tB === -1 ? 999 : tB;
                if (tipoA !== tipoB) return tipoA - tipoB;

                return (a.nombre || '').localeCompare(b.nombre || '');
            });
            
            // Función para generar interpretación detallada con probabilidades y percentiles
            const generarInterpretacion = (portfolio) => {
                const mc = portfolio.data.metricas_montecarlo || {};
                const probGanar = (mc.prob_ganar || 0) * 100;
                const probPerder = (mc.prob_perder || 0) * 100;
                const sharpe = portfolio.data.sharpe_ratio || 0;
                const gananciaEsperada = portfolio.data.ganancia_esperada || 0;
                const gananciaMediana = mc.ganancia_mediana || 0;
                const var5 = mc.var_5 || 0;
                const p5 = mc.percentil_5 || 0;
                const p25 = mc.percentil_25 || 0;
                const p75 = mc.percentil_75 || 0;
                const p95 = mc.percentil_95 || 0;
                
                let interpretacion = [];
                
                // Interpretación de Sharpe
                if (sharpe > 1.5) {
                    interpretacion.push('🌟 Excelente relación riesgo-retorno (Sharpe > 1.5)');
                } else if (sharpe > 1.0) {
                    interpretacion.push('✅ Buena relación riesgo-retorno (Sharpe > 1.0)');
                } else if (sharpe > 0.5) {
                    interpretacion.push('⚠️ Sharpe moderado (0.5-1.0), retorno compensa riesgo');
                } else if (sharpe > 0) {
                    interpretacion.push('⚠️ Sharpe bajo (< 0.5), retorno apenas compensa riesgo');
                } else {
                    interpretacion.push('❌ Sharpe negativo, retorno no compensa el riesgo');
                }
                
                // Interpretación de probabilidades básicas
                if (probGanar > 70) {
                    interpretacion.push(`📈 Alta probabilidad de ganancia (${probGanar.toFixed(1)}%)`);
                } else if (probGanar > 50) {
                    interpretacion.push(`📊 Probabilidad moderada de ganancia (${probGanar.toFixed(1)}%)`);
                } else {
                    interpretacion.push(`⚠️ Baja probabilidad de ganancia (${probGanar.toFixed(1)}%)`);
                }
                
                // Interpretación de VaR (equivalente a P5 en pérdidas)
                if (var5 < -500) {
                    interpretacion.push(`⚠️ Pérdida máxima esperada (VaR 5%) significativa: ${formatCurrency(var5)}`);
                } else if (var5 < -200) {
                    interpretacion.push(`📉 Pérdida máxima esperada (VaR 5%) moderada: ${formatCurrency(var5)}`);
                } else {
                    interpretacion.push(`✅ Pérdida máxima esperada (VaR 5%) controlada: ${formatCurrency(var5)}`);
                }
                
                // Comparación ganancia esperada vs mediana
                if (Math.abs(gananciaEsperada - gananciaMediana) > 100) {
                    const diferencia = gananciaMediana - gananciaEsperada;
                    if (diferencia > 0) {
                        interpretacion.push(`📊 Mediana (${formatCurrency(gananciaMediana)}) supera esperada, distribución sesgada positivamente`);
                    } else {
                        interpretacion.push(`📊 Mediana (${formatCurrency(gananciaMediana)}) menor a esperada, distribución sesgada negativamente`);
                    }
                }

                // Interpretación de percentiles como probabilidades
                // P25: 25% de probabilidad de estar peor que ese P&L (escenario bajo)
                interpretacion.push(`📉 P25: 25% de probabilidad de terminar por debajo de ${formatCurrency(p25)} (escenario bajo).`);

                // P75: 75% de probabilidad de estar por debajo de ese P&L (escenario alto)
                interpretacion.push(`📈 P75: 75% de probabilidad de terminar por debajo de ${formatCurrency(p75)} (escenario alto), 25% de ir mejor.`);

                // P5: 5% de probabilidad de un resultado peor que ese P&L (cola pesimista)
                interpretacion.push(`⚠️ P5: solo en el 5% de los peores casos la pérdida superaría ${formatCurrency(p5)} (cola pesimista).`);

                // P95: 5% de probabilidad de superar ese P&L (cola optimista)
                interpretacion.push(`🌈 P95: solo en el 5% de los mejores escenarios la ganancia superaría ${formatCurrency(p95)} (cola optimista).`);
                
                return interpretacion.join(' • ');
            };
            
            htmlContent += `
                        <div id="slide-comparison" class="slide" data-slide-index="${slideIndexCounter}" style="margin-top: 0 !important; padding-top: 0 !important;">
                            <div class="max-w-7xl mx-auto px-8" style="padding-top: 0 !important; margin-top: 0 !important; padding-bottom: 2rem;">
                                <div class="card p-8 mb-6">
                                    <h2 class="text-3xl font-bold mb-6 text-slate-100">Comparación Completa de Portafolios</h2>
                                    <p class="text-slate-400 mb-6">Comparación lado a lado: Métricas de Optimización (Pesos) vs Simulación Monte Carlo (5000 escenarios)</p>
                                    
                                    <!-- Tabla Comparativa Unificada -->
                                    <div class="mb-8">
                                        <div class="overflow-x-auto">
                                            <table class="w-full text-xs border-collapse">
                                                <thead>
                                                    <tr class="border-b-2 border-slate-600 bg-slate-800/70">
                                                        <th rowspan="2" class="text-left py-3 px-3 text-slate-300 font-semibold border-r border-slate-700">Portafolio</th>
                                                        <th rowspan="2" class="text-right py-3 px-3 text-slate-300 font-semibold border-r border-slate-700">Activos</th>
                                                        <th colspan="4" class="text-center py-2 px-2 text-slate-300 font-semibold bg-slate-800/50 border-r border-slate-700">Optimización (Pesos)</th>
                                                        <th colspan="8" class="text-center py-2 px-2 text-slate-300 font-semibold bg-blue-900/30">Monte Carlo (5000 escenarios)</th>
                                                    </tr>
                                                    <tr class="border-b border-slate-700 bg-slate-800/50">
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-slate-800/30 border-r border-slate-700">Retorno (%)</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-slate-800/30 border-r border-slate-700">Volatilidad (%)</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-slate-800/30 border-r border-slate-700">Sharpe</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-slate-800/30 border-r border-slate-700">Ganancia Esperada</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Ganancia Media</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. 50%</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. 25%</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. 75%</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. 5%</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. 95%</th>
                                                        <th class="text-right py-2 px-2 text-slate-300 font-semibold bg-blue-900/20">Prob. Ganar</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${comparacionPortafolios.map((item, idx) => {
                                                        const sharpe = item.data.sharpe_ratio || 0;
                                                        const sharpeColor = sharpe > 1.0 ? 'text-green-400' : sharpe > 0.5 ? 'text-yellow-400' : 'text-red-400';
                                                        const mc = item.data.metricas_montecarlo || {};
                                                        const tipoLabel = item.tipo === 'Pesos Iguales' ? 'Pesos Iguales' : item.tipo === 'Máximo Sharpe' ? 'Máx Sharpe' : 'Mín Vol';
                                                        return `
                                                        <tr class="border-b border-slate-800 ${idx % 2 === 0 ? 'bg-slate-800/20' : ''}">
                                                            <td class="py-3 px-3 font-medium text-slate-200 border-r border-slate-700">${item.nombre} - ${tipoLabel}</td>
                                                            <td class="text-right py-3 px-3 text-slate-400 border-r border-slate-700">${item.n_activos}</td>
                                                            <td class="text-right py-3 px-2 ${item.data.retorno_anual >= 0 ? 'text-green-400' : 'text-red-400'} bg-slate-800/20 border-r border-slate-700">${(item.data.retorno_anual * 100).toFixed(2)}%</td>
                                                            <td class="text-right py-3 px-2 text-slate-300 bg-slate-800/20 border-r border-slate-700">${(item.data.volatilidad_anual * 100).toFixed(2)}%</td>
                                                            <td class="text-right py-3 px-2 font-bold ${sharpeColor} bg-slate-800/20 border-r border-slate-700">${sharpe.toFixed(2)}</td>
                                                            <td class="text-right py-3 px-2 font-bold text-green-400 bg-slate-800/20 border-r border-slate-700">${formatCurrency(item.data.ganancia_esperada)}</td>
                                                            <td class="text-right py-3 px-2 font-bold text-green-400 bg-blue-900/20">${formatCurrency(mc.ganancia_media || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-blue-400 bg-blue-900/20">${formatCurrency(mc.ganancia_mediana || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-red-400 bg-blue-900/20">${formatCurrency(mc.percentil_25 || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-orange-400 bg-blue-900/20">${formatCurrency(mc.percentil_75 || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-red-400 bg-blue-900/20">${formatCurrency(mc.percentil_5 || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-green-400 bg-blue-900/20">${formatCurrency(mc.percentil_95 || 0)}</td>
                                                            <td class="text-right py-3 px-2 text-green-400 bg-blue-900/20">${((mc.prob_ganar || 0) * 100).toFixed(1)}%</td>
                                                        </tr>
                                                    `;
                                                    }).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                    
                                    <!-- Interpretaciones -->
                                    <div class="mb-6">
                                        <h3 class="text-xl font-semibold mb-4 text-slate-200">Interpretación de Resultados</h3>
                                        <div class="space-y-4">
                                            ${comparacionPortafolios.map((item) => {
                                                const interpretacion = generarInterpretacion(item);
                                                const tipoLabel = item.tipo === 'Pesos Iguales' ? 'Pesos Iguales' : item.tipo === 'Máximo Sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad';
                                                return `
                                                <div class="bg-slate-800/30 border border-slate-700 rounded-lg p-4">
                                                    <h4 class="text-lg font-semibold mb-2 text-slate-100">${item.nombre} - ${tipoLabel} (${item.n_activos} activos)</h4>
                                                    <p class="text-sm text-slate-300 leading-relaxed">${interpretacion || 'Sin interpretación disponible'}</p>
                                                </div>
                                            `;
                                            }).join('')}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                        </div>
                        
                        <!-- Tab: Backtesting -->
                        <div id="tab-backtesting" class="tab-content">
                            <div class="max-w-7xl mx-auto px-8 py-8">
                                <div class="card p-8">
                                    <h2 class="text-3xl font-bold mb-6 text-slate-100">Backtesting de Portafolios</h2>
                                    <p class="text-slate-400 mb-6">Cargue un portafolio comprado para realizar backtesting histórico desde la fecha de compra</p>
                                    
                                    <div class="mb-6">
                                        <label class="block text-slate-300 mb-2">Seleccionar Portafolio para Backtesting:</label>
                                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4" id="backtesting-portfolios-list">
                                        </div>
                                        <div id="backtesting-status" class="mt-4 text-slate-400"></div>
                                    </div>
                                    
                                    <div id="backtesting-results" class="hidden">
                                        <h3 class="text-2xl font-semibold mb-4 text-slate-200">Resultados del Backtesting</h3>
                                        <div id="backtesting-metrics" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6"></div>
                                        <div id="backtesting-chart-container" class="mb-6">
                                            <canvas id="backtesting-chart" width="800" height="400"></canvas>
                                        </div>
                                        <div id="backtesting-table-container" class="overflow-x-auto"></div>
                                    </div>
                                    
                                    <div class="mt-6 p-4 bg-slate-800/50 rounded-lg">
                                        <h4 class="text-lg font-semibold mb-2 text-slate-200">Cómo usar Backtesting:</h4>
                                        <ol class="list-decimal list-inside text-slate-300 space-y-1 text-sm">
                                            <li>Seleccione un portafolio desde la sección "Optimizaciones"</li>
                                            <li>Haga clic en el botón "Comprar Portafolio" para descargar el JSON con las posiciones</li>
                                            <li>Cargue el archivo JSON descargado aquí</li>
                                            <li>El sistema calculará el rendimiento histórico desde la fecha de compra hasta hoy</li>
                                        </ol>
                                    </div>
                                    
                                    <div class="mt-6">
                                        <label class="block text-slate-300 mb-2">Cargar JSON de Portafolio Comprado:</label>
                                        <input type="file" id="load-portfolio-json" accept=".json" class="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500" />
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Tab: Simulación -->
                        <div id="tab-simulacion" class="tab-content">
                            <div class="max-w-7xl mx-auto px-8 py-8">
                                <div class="card p-8">
                                    <h2 class="text-3xl font-bold mb-6 text-slate-100">Simulación de Portafolios</h2>
                                    <p class="text-slate-400 mb-6">Simule un portafolio desde una fecha pasada y compare los resultados esperados vs los reales</p>
                                    
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                                        <div>
                                            <label class="block text-slate-300 mb-2">Seleccionar Portafolio:</label>
                                            <select id="sim-portfolio-select" class="w-full px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200">
                                                <option value="">-- Seleccionar --</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-slate-300 mb-2">Fecha de Simulación (como si fuera hoy):</label>
                                            <input type="date" id="sim-date" class="w-full px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200" />
                                        </div>
                                    </div>
                                    
                                    <div class="mb-6">
                                        <label class="block text-slate-300 mb-2">Horizontes de Análisis:</label>
                                        <div class="flex gap-4 flex-wrap">
                                            <label class="flex items-center text-slate-300">
                                                <input type="checkbox" class="mr-2" value="1m" checked /> 1 Mes
                                            </label>
                                            <label class="flex items-center text-slate-300">
                                                <input type="checkbox" class="mr-2" value="3m" checked /> 3 Meses
                                            </label>
                                            <label class="flex items-center text-slate-300">
                                                <input type="checkbox" class="mr-2" value="6m" /> 6 Meses
                                            </label>
                                            <label class="flex items-center text-slate-300">
                                                <input type="checkbox" class="mr-2" value="1y" checked /> 1 Año
                                            </label>
                                        </div>
                                    </div>
                                    
                                    <button id="run-simulation" class="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors text-white font-semibold mb-6">
                                        Ejecutar Simulación
                                    </button>
                                    
                                    <div id="simulation-results" class="hidden">
                                        <h3 class="text-2xl font-semibold mb-4 text-slate-200">Resultados de la Simulación</h3>
                                        <div id="simulation-comparison" class="space-y-6"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </main>
                </div>
            `;
            
            root.innerHTML = htmlContent;
            
            // Inicializar slides
            slides = Array.from(document.querySelectorAll('.slide'));
            updateSlideCounter();
            
            // Event listeners
            document.getElementById('prev-slide').addEventListener('click', () => {
                if (currentSlideIndex > 0) {
                    currentSlideIndex--;
                    showSlide(currentSlideIndex);
                }
            });
            
            document.getElementById('next-slide').addEventListener('click', () => {
                if (currentSlideIndex < slides.length - 1) {
                    currentSlideIndex++;
                    showSlide(currentSlideIndex);
                }
            });
            
            document.getElementById('download-current').addEventListener('click', async () => {
                await downloadSlide(currentSlideIndex);
            });
            
            document.getElementById('download-all').addEventListener('click', async () => {
                for (let i = 0; i < slides.length; i++) {
                    showSlide(i);
                    await new Promise(resolve => setTimeout(resolve, 500));
                    await downloadSlide(i);
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            });
            
            // Selector de plantillas
            document.getElementById('template-select').addEventListener('change', (e) => {
                changeTemplate(e.target.value);
            });
            
            // Inicializar plantilla por defecto
            document.body.setAttribute('data-template', currentTemplate);
            
            // Renderizar gráficos después de un delay
            setTimeout(() => {
                renderAllCharts();
            }, 500);
            
            // Inicializar tabs de backtesting y simulación
            initializeBacktestingTab();
            initializeSimulationTab();
            
            // Cargar series históricas
            loadHistoricalSeries();
        });
        
        // Función para cambiar entre tabs
        function switchTab(tabName) {
            currentTab = tabName;
            
            // Ocultar todos los tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Mostrar el tab seleccionado
            document.getElementById(`tab-${tabName}`).classList.add('active');
            
            // Actualizar botones de tabs
            document.querySelectorAll('.nav-tab').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabName);
            });
            
            // Mostrar/ocultar controles de slides según el tab
            const slideControls = ['prev-slide', 'next-slide', 'download-all', 'download-current', 'slide-counter'];
            const shouldShow = tabName === 'optimizaciones';
            slideControls.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = shouldShow ? '' : 'none';
            });
            
            // Si es el tab de optimizaciones, renderizar gráficos
            if (tabName === 'optimizaciones') {
                setTimeout(() => renderAllCharts(), 100);
            }
        }
        
        // Función para descargar JSON del portafolio
        function downloadPortfolioJSON(portfolioKey, type) {
            const portfolio = OPTIMIZATION_DATA.portafolios[portfolioKey];
            if (!portfolio) return;
            
            const data = portfolio[type];
            if (!data || !data.asignacion) return;
            
            const fechaHoy = new Date().toISOString().split('T')[0];
            
            const portfolioJSON = {
                fecha_compra: fechaHoy,
                nombre_portafolio: portfolio.nombre,
                tipo_optimizacion: type === 'composicion_global' ? 'Pesos Iguales' : type === 'maximo_sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad',
                monto_total: data.asignacion.reduce((sum, item) => sum + (item.asignacion_dinero || 0), 0),
                posiciones: data.asignacion.map(item => ({
                    ticker: item.ticker,
                    cantidad: item.cantidad,
                    precio_compra: item.precio_actual,
                    asignacion_dinero: item.asignacion_dinero,
                    peso_porcentaje: item.peso_porcentaje,
                    sector: item.sector
                })),
                metricas_iniciales: {
                    retorno_anual_esperado: data.retorno_anual,
                    volatilidad_anual: data.volatilidad_anual,
                    sharpe_ratio: data.sharpe_ratio
                }
            };
            
            const jsonStr = JSON.stringify(portfolioJSON, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `portafolio_${portfolioKey}_${type}_${fechaHoy}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // Función para cargar series históricas
        async function loadHistoricalSeries() {
            try {
                const response = await fetch('series_historicas.json');
                if (response.ok) {
                    historicalSeriesData = await response.json();
                    console.log('Series históricas cargadas');
                } else {
                    console.warn('No se pudieron cargar las series históricas');
                }
            } catch (error) {
                console.warn('Error cargando series históricas:', error);
            }
        }
        
        // Inicializar tab de backtesting
        function initializeBacktestingTab() {
            // Llenar lista de portafolios
            const listContainer = document.getElementById('backtesting-portfolios-list');
            if (!listContainer) return;
            
            listContainer.innerHTML = '';
            Object.entries(OPTIMIZATION_DATA.portafolios || {}).forEach(([key, portfolio]) => {
                const nombreLimpio = portfolio.nombre.replace(/\\s*\\(\\d+\\s*activos?\\)/gi, '').trim();
                ['composicion_global', 'maximo_sharpe', 'minima_volatilidad'].forEach(type => {
                    const data = portfolio[type];
                    if (!data) return;
                    
                    const typeLabel = type === 'composicion_global' ? 'Pesos Iguales' : type === 'maximo_sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad';
                    const card = document.createElement('div');
                    card.className = 'card p-4 cursor-pointer hover:bg-slate-700/50 transition-colors';
                    card.innerHTML = `
                        <h4 class="font-semibold text-slate-200">${nombreLimpio}</h4>
                        <p class="text-sm text-slate-400">${typeLabel}</p>
                        <p class="text-xs text-slate-500 mt-2">Retorno: ${(data.retorno_anual * 100).toFixed(2)}%</p>
                    `;
                    card.onclick = () => selectPortfolioForBacktesting(key, type);
                    listContainer.appendChild(card);
                });
            });
            
            // Manejar carga de archivo JSON
            const fileInput = document.getElementById('load-portfolio-json');
            if (fileInput) {
                fileInput.addEventListener('change', (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        try {
                            const portfolioData = JSON.parse(event.target.result);
                            performBacktesting(portfolioData);
                        } catch (error) {
                            alert('Error al leer el archivo JSON: ' + error.message);
                        }
                    };
                    reader.readAsText(file);
                });
            }
        }
        
        function selectPortfolioForBacktesting(portfolioKey, type) {
            const portfolio = OPTIMIZATION_DATA.portafolios[portfolioKey];
            if (!portfolio) return;
            
            const data = portfolio[type];
            if (!data) return;
            
            const fechaHoy = new Date().toISOString().split('T')[0];
            const portfolioJSON = {
                fecha_compra: fechaHoy,
                nombre_portafolio: portfolio.nombre,
                tipo_optimizacion: type === 'composicion_global' ? 'Pesos Iguales' : type === 'maximo_sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad',
                monto_total: data.asignacion.reduce((sum, item) => sum + (item.asignacion_dinero || 0), 0),
                posiciones: data.asignacion.map(item => ({
                    ticker: item.ticker,
                    cantidad: item.cantidad,
                    precio_compra: item.precio_actual,
                    asignacion_dinero: item.asignacion_dinero
                }))
            };
            
            performBacktesting(portfolioJSON);
        }
        
        async function performBacktesting(portfolioData) {
            if (!historicalSeriesData) {
                await loadHistoricalSeries();
                if (!historicalSeriesData) {
                    alert('Error: No se pudieron cargar las series históricas. Asegúrese de que el archivo series_historicas.json existe.');
                    return;
                }
            }
            
            const fechaCompra = new Date(portfolioData.fecha_compra);
            const fechas = historicalSeriesData.fechas || [];
            const precios = historicalSeriesData.activos?.precios || {};
            
            // Encontrar índice de fecha de compra
            let fechaCompraIdx = fechas.findIndex(f => new Date(f) >= fechaCompra);
            if (fechaCompraIdx === -1) {
                alert('La fecha de compra es muy reciente o no hay datos históricos suficientes');
                return;
            }
            
            // Calcular valor del portafolio día por día
            const resultados = [];
            let valorInicial = 0;
            
            portfolioData.posiciones.forEach(pos => {
                valorInicial += pos.asignacion_dinero;
            });
            
            for (let i = fechaCompraIdx; i < fechas.length; i++) {
                const fecha = fechas[i];
                let valorPortafolio = 0;
                
                portfolioData.posiciones.forEach(pos => {
                    const ticker = pos.ticker;
                    if (precios[ticker] && precios[ticker][i] !== undefined) {
                        const precioActual = precios[ticker][i];
                        const valorPosicion = pos.cantidad * precioActual;
                        valorPortafolio += valorPosicion;
                    }
                });
                
                const retorno = (valorPortafolio - valorInicial) / valorInicial;
                
                resultados.push({
                    fecha,
                    valor: valorPortafolio,
                    retorno,
                    ganancia_perdida: valorPortafolio - valorInicial
                });
            }
            
            // Mostrar resultados
            displayBacktestingResults(portfolioData, resultados, valorInicial);
        }
        
        function displayBacktestingResults(portfolioData, resultados, valorInicial) {
            const resultsDiv = document.getElementById('backtesting-results');
            const metricsDiv = document.getElementById('backtesting-metrics');
            const chartContainer = document.getElementById('backtesting-chart-container');
            const tableContainer = document.getElementById('backtesting-table-container');
            
            if (!resultsDiv || resultados.length === 0) return;
            
            resultsDiv.classList.remove('hidden');
            
            // Calcular métricas
            const ultimoResultado = resultados[resultados.length - 1];
            const retornoTotal = ultimoResultado.retorno;
            const gananciaTotal = ultimoResultado.ganancia_perdida;
            const diasTranscurridos = resultados.length;
            
            // Calcular retorno anualizado
            const retornoAnualizado = diasTranscurridos > 0 ? Math.pow(1 + retornoTotal, 252 / diasTranscurridos) - 1 : 0;
            
            // Calcular volatilidad (desviación estándar de retornos diarios)
            const retornosDiarios = [];
            for (let i = 1; i < resultados.length; i++) {
                const retDia = (resultados[i].valor - resultados[i-1].valor) / resultados[i-1].valor;
                retornosDiarios.push(retDia);
            }
            const volatilidad = retornosDiarios.length > 0 ? 
                Math.sqrt(retornosDiarios.reduce((sum, r) => sum + Math.pow(r - (retornoTotal / diasTranscurridos), 2), 0) / retornosDiarios.length) * Math.sqrt(252) : 0;
            
            metricsDiv.innerHTML = `
                <div class="card p-4">
                    <div class="text-sm text-slate-400 mb-1">Retorno Total</div>
                    <div class="text-2xl font-bold ${retornoTotal >= 0 ? 'text-green-400' : 'text-red-400'}">${(retornoTotal * 100).toFixed(2)}%</div>
                </div>
                <div class="card p-4">
                    <div class="text-sm text-slate-400 mb-1">Ganancia/Pérdida</div>
                    <div class="text-2xl font-bold ${gananciaTotal >= 0 ? 'text-green-400' : 'text-red-400'}">${formatCurrency(gananciaTotal)}</div>
                </div>
                <div class="card p-4">
                    <div class="text-sm text-slate-400 mb-1">Retorno Anualizado</div>
                    <div class="text-2xl font-bold ${retornoAnualizado >= 0 ? 'text-green-400' : 'text-red-400'}">${(retornoAnualizado * 100).toFixed(2)}%</div>
                </div>
            `;
            
            // Dibujar gráfico simple (puedes mejorar esto con Chart.js si prefieres)
            const canvas = document.getElementById('backtesting-chart');
            if (canvas) {
                drawBacktestingChart(canvas, resultados, valorInicial);
            }
            
            // Mostrar tabla de resultados
            const ultimos30 = resultados.slice(-30);
            tableContainer.innerHTML = `
                <table class="w-full text-sm border-collapse">
                    <thead>
                        <tr class="border-b border-slate-600">
                            <th class="text-left py-2 px-3 text-slate-300">Fecha</th>
                            <th class="text-right py-2 px-3 text-slate-300">Valor</th>
                            <th class="text-right py-2 px-3 text-slate-300">Retorno</th>
                            <th class="text-right py-2 px-3 text-slate-300">Ganancia/Pérdida</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${ultimos30.map(r => `
                            <tr class="border-b border-slate-700">
                                <td class="py-2 px-3 text-slate-400">${r.fecha.split('T')[0]}</td>
                                <td class="py-2 px-3 text-right text-slate-300">${formatCurrency(r.valor)}</td>
                                <td class="py-2 px-3 text-right ${r.retorno >= 0 ? 'text-green-400' : 'text-red-400'}">${(r.retorno * 100).toFixed(2)}%</td>
                                <td class="py-2 px-3 text-right ${r.ganancia_perdida >= 0 ? 'text-green-400' : 'text-red-400'}">${formatCurrency(r.ganancia_perdida)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        function drawBacktestingChart(canvas, resultados, valorInicial) {
            const ctx = canvas.getContext('2d');
            const width = canvas.width = 800;
            const height = canvas.height = 400;
            
            ctx.clearRect(0, 0, width, height);
            
            // Dibujar gráfico simple de línea
            const padding = { top: 20, right: 20, bottom: 40, left: 80 };
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;
            
            const valores = resultados.map(r => r.valor);
            const minValor = Math.min(...valores, valorInicial);
            const maxValor = Math.max(...valores, valorInicial);
            const range = maxValor - minValor || 1;
            
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            resultados.forEach((r, i) => {
                const x = padding.left + (i / (resultados.length - 1)) * chartWidth;
                const y = padding.top + chartHeight - ((r.valor - minValor) / range) * chartHeight;
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
            
            // Línea de valor inicial
            ctx.strokeStyle = '#94a3b8';
            ctx.setLineDash([5, 5]);
            const yInicial = padding.top + chartHeight - ((valorInicial - minValor) / range) * chartHeight;
            ctx.beginPath();
            ctx.moveTo(padding.left, yInicial);
            ctx.lineTo(padding.left + chartWidth, yInicial);
            ctx.stroke();
            ctx.setLineDash([]);
        }
        
        // Inicializar tab de simulación
        function initializeSimulationTab() {
            // Llenar selector de portafolios
            const select = document.getElementById('sim-portfolio-select');
            if (!select) return;
            
            Object.entries(OPTIMIZATION_DATA.portafolios || {}).forEach(([key, portfolio]) => {
                const nombreLimpio = portfolio.nombre.replace(/\\s*\\(\\d+\\s*activos?\\)/gi, '').trim();
                ['composicion_global', 'maximo_sharpe', 'minima_volatilidad'].forEach(type => {
                    const data = portfolio[type];
                    if (!data) return;
                    
                    const typeLabel = type === 'composicion_global' ? 'Pesos Iguales' : type === 'maximo_sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad';
                    const option = document.createElement('option');
                    option.value = `${key}|${type}`;
                    option.textContent = `${nombreLimpio} - ${typeLabel}`;
                    select.appendChild(option);
                });
            });
            
            // Establecer fecha por defecto (3 meses atrás)
            const dateInput = document.getElementById('sim-date');
            if (dateInput) {
                const fecha = new Date();
                fecha.setMonth(fecha.getMonth() - 3);
                dateInput.value = fecha.toISOString().split('T')[0];
            }
            
            // Botón de ejecutar simulación
            const btn = document.getElementById('run-simulation');
            if (btn) {
                btn.addEventListener('click', runSimulation);
            }
        }
        
        async function runSimulation() {
            if (!historicalSeriesData) {
                await loadHistoricalSeries();
                if (!historicalSeriesData) {
                    alert('Error: No se pudieron cargar las series históricas');
                    return;
                }
            }
            
            const portfolioSelect = document.getElementById('sim-portfolio-select');
            const fechaSelect = document.getElementById('sim-date');
            const checkboxes = document.querySelectorAll('#tab-simulacion input[type="checkbox"]:checked');
            
            if (!portfolioSelect || !fechaSelect || checkboxes.length === 0) {
                alert('Por favor complete todos los campos');
                return;
            }
            
            const [portfolioKey, type] = portfolioSelect.value.split('|');
            const fechaSimulacion = new Date(fechaSelect.value);
            const horizontes = Array.from(checkboxes).map(cb => cb.value);
            
            const portfolio = OPTIMIZATION_DATA.portafolios[portfolioKey];
            if (!portfolio) return;
            
            const data = portfolio[type];
            if (!data) return;
            
            // Realizar simulación
            const resultados = performSimulation(portfolio, data, fechaSimulacion, horizontes);
            
            // Mostrar resultados
            displaySimulationResults(resultados, portfolio.nombre, type);
        }
        
        function calcularPercentil(valor, percentiles) {
            // Calcular en qué percentil está el valor basado en los percentiles de Monte Carlo
            if (!percentiles || valor === null || valor === undefined) return null;
            
            const p5 = percentiles.percentil_5;
            const p25 = percentiles.percentil_25;
            const p75 = percentiles.percentil_75;
            const p95 = percentiles.percentil_95;
            const mediana = percentiles.ganancia_mediana;
            
            // Validar que los percentiles sean números válidos
            if (p5 === null || p5 === undefined || isNaN(p5) ||
                p25 === null || p25 === undefined || isNaN(p25) ||
                mediana === null || mediana === undefined || isNaN(mediana) ||
                p75 === null || p75 === undefined || isNaN(p75) ||
                p95 === null || p95 === undefined || isNaN(p95)) {
                return null;
            }
            
            // Ordenar percentiles para comparación correcta
            if (valor <= p5) return { percentil: 5, label: 'P5 (Muy Bajo)' };
            if (valor <= p25) return { percentil: 25, label: 'P25 (Bajo)' };
            if (valor <= mediana) return { percentil: 50, label: 'P50 (Mediana)' };
            if (valor <= p75) return { percentil: 75, label: 'P75 (Alto)' };
            if (valor <= p95) return { percentil: 95, label: 'P95 (Muy Alto)' };
            return { percentil: 99, label: '>P95 (Extremo)' };
        }
        
        /**
         * Analiza si el retorno observado se explica por mean + k·σ
         * Basado en la metodología empírica usando percentiles de Monte Carlo
         */
        function analizarObservadoVsSigma(retornoEsperado, retornoObservado, volatilidadAnual, diasHorizonte, percentilesEscalados, valorInicial) {
            if (!percentilesEscalados || valorInicial <= 0) {
                return null;
            }
            
            // Escalar volatilidad al horizonte
            // σ_h = σ_anual * sqrt(dias / 252)
            const sigmaHorizonte = volatilidadAnual * Math.sqrt(diasHorizonte / 252);
            
            // Calcular z-score
            const diferencia = retornoObservado - retornoEsperado;
            const zScore = sigmaHorizonte > 0 ? diferencia / sigmaHorizonte : null;
            
            // Calcular valores de sigma
            const mu = retornoEsperado;
            const sigma = sigmaHorizonte;
            const muPlus1Sigma = mu + 1.0 * sigma;
            const muMinus1Sigma = mu - 1.0 * sigma;
            const muPlus2Sigma = mu + 2.0 * sigma;
            const muMinus2Sigma = mu - 2.0 * sigma;
            
            // Calcular P&L observado para comparar con percentiles
            const pnlObservado = valorInicial * retornoObservado;
            
            // Estimar percentil empírico usando los percentiles de Monte Carlo
            // Los percentiles escalados están en términos de P&L (ganancia/pérdida), no retorno
            // Comparar directamente el P&L observado con los percentiles de P&L
            let percentilEmpirico = null;
            const pnlP5 = percentilesEscalados.percentil_5 !== null ? percentilesEscalados.percentil_5 * valorInicial : null;
            const pnlP25 = percentilesEscalados.percentil_25 !== null ? percentilesEscalados.percentil_25 * valorInicial : null;
            const pnlMediana = percentilesEscalados.ganancia_mediana !== null ? percentilesEscalados.ganancia_mediana * valorInicial : null;
            const pnlP75 = percentilesEscalados.percentil_75 !== null ? percentilesEscalados.percentil_75 * valorInicial : null;
            const pnlP95 = percentilesEscalados.percentil_95 !== null ? percentilesEscalados.percentil_95 * valorInicial : null;
            
            if (pnlP5 !== null && pnlP25 !== null && pnlMediana !== null && pnlP75 !== null && pnlP95 !== null) {
                // Comparar P&L observado directamente con percentiles de P&L
                if (pnlObservado <= pnlP5) {
                    percentilEmpirico = 5; // Por debajo del percentil 5
                } else if (pnlObservado <= pnlP25) {
                    // Interpolar entre P5 y P25
                    percentilEmpirico = 5 + ((pnlObservado - pnlP5) / (pnlP25 - pnlP5)) * 20;
                } else if (pnlObservado <= pnlMediana) {
                    // Interpolar entre P25 y mediana (P50)
                    percentilEmpirico = 25 + ((pnlObservado - pnlP25) / (pnlMediana - pnlP25)) * 25;
                } else if (pnlObservado <= pnlP75) {
                    // Interpolar entre mediana y P75
                    percentilEmpirico = 50 + ((pnlObservado - pnlMediana) / (pnlP75 - pnlMediana)) * 25;
                } else if (pnlObservado <= pnlP95) {
                    // Interpolar entre P75 y P95
                    percentilEmpirico = 75 + ((pnlObservado - pnlP75) / (pnlP95 - pnlP75)) * 20;
                } else {
                    percentilEmpirico = 95 + ((pnlObservado - pnlP95) / Math.abs(pnlP95)) * 5; // Extrapolación conservadora
                }
            }
            
            // Calcular probabilidad de obtener >= retorno observado (aproximación usando z-score)
            let probGe = null;
            if (zScore !== null) {
                // Usar aproximación normal: P(Z >= z) = 1 - Φ(z)
                // Aproximación simple usando erf
                probGe = 0.5 * (1 - erf(zScore / Math.sqrt(2)));
            }
            
            // Determinar interpretación del z-score
            let interpretacionSigma = null;
            let explicacion = null;
            if (zScore !== null) {
                const absZ = Math.abs(zScore);
                if (absZ <= 0.5) {
                    interpretacionSigma = "≈ 0σ";
                    explicacion = "Dentro del rango esperado";
                } else if (absZ <= 1.0) {
                    interpretacionSigma = zScore > 0 ? "≈ +1σ" : "≈ -1σ";
                    explicacion = zScore > 0 ? "Explicado por +1σ" : "Explicado por -1σ";
                } else if (absZ <= 1.5) {
                    interpretacionSigma = zScore > 0 ? "≈ +1.5σ" : "≈ -1.5σ";
                    explicacion = "Ligeramente superior/inferior a 1σ";
                } else if (absZ <= 2.0) {
                    interpretacionSigma = zScore > 0 ? "≈ +2σ" : "≈ -2σ";
                    explicacion = "Evento poco probable (>95% en distribución normal)";
                } else {
                    interpretacionSigma = zScore > 0 ? `>+2σ (${zScore.toFixed(2)}σ)` : `<-2σ (${zScore.toFixed(2)}σ)`;
                    explicacion = "Evento muy raro (outlier)";
                }
            }
            
            return {
                mu: mu,
                sigma: sigma,
                retornoObservado: retornoObservado,
                diferencia: diferencia,
                zScore: zScore,
                percentilEmpirico: percentilEmpirico,
                probGe: probGe,
                muPlus1Sigma: muPlus1Sigma,
                muMinus1Sigma: muMinus1Sigma,
                muPlus2Sigma: muPlus2Sigma,
                muMinus2Sigma: muMinus2Sigma,
                interpretacionSigma: interpretacionSigma,
                explicacion: explicacion
            };
        }
        
        // Función auxiliar para calcular la función de error (erf) aproximada
        function erf(x) {
            // Aproximación de Abramowitz y Stegun
            const a1 =  0.254829592;
            const a2 = -0.284496736;
            const a3 =  1.421413741;
            const a4 = -1.453152027;
            const a5 =  1.061405429;
            const p  =  0.3275911;
            
            const sign = x < 0 ? -1 : 1;
            x = Math.abs(x);
            
            const t = 1.0 / (1.0 + p * x);
            const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
            
            return sign * y;
        }
        
        function performSimulation(portfolio, data, fechaSimulacion, horizontes) {
            const fechas = historicalSeriesData.fechas || [];
            const precios = historicalSeriesData.activos?.precios || {};
            
            // Encontrar índice de fecha de simulación
            let fechaSimIdx = fechas.findIndex(f => new Date(f) >= fechaSimulacion);
            if (fechaSimIdx === -1) fechaSimIdx = fechas.length - 1;
            
            const fechaHoy = new Date();
            const fechaHoyIdx = fechas.length - 1;
            
            // Calcular días transcurridos desde fecha de simulación hasta hoy
            const fechaSimDate = new Date(fechaSimulacion);
            const diasTranscurridos = Math.floor((fechaHoy - fechaSimDate) / (1000 * 60 * 60 * 24));
            
            // BACKTEST DE PROYECCIÓN CORRECTO:
            // 1. Filtrar horizontes válidos: solo los que "entran" en el tramo desde fecha_simulacion hasta hoy
            // Un horizonte es válido si: dias_horizonte <= dias_transcurridos
            
            const horizontesDiasMap = {
                '1m': 21,
                '3m': 63,
                '6m': 126,
                '1y': 252
            };
            
            // Filtrar horizontes válidos (solo los que ya pasaron o están en el rango hasta hoy)
            const horizontesValidos = horizontes.filter(h => {
                const diasHorizonte = horizontesDiasMap[h] || 0;
                // Solo incluir horizontes donde el horizonte es menor o igual a los días transcurridos
                return diasHorizonte > 0 && diasHorizonte <= diasTranscurridos;
            });
            
            // Calcular valor inicial del portafolio
            // PRIORIDAD: Usar asignacion_dinero si está disponible (más confiable)
            // Si no, calcular usando cantidades y precios de la fecha de simulación
            let valorInicial = 0;
            const asignacionDineroTotal = data.asignacion.reduce((sum, item) => sum + (item.asignacion_dinero || 0), 0);
            
            if (asignacionDineroTotal > 0) {
                // Usar asignacion_dinero como base (más confiable)
                valorInicial = asignacionDineroTotal;
                
                // Recalcular cantidades basadas en precios de la fecha de simulación para consistencia
                data.asignacion.forEach(pos => {
                    const ticker = pos.ticker;
                    if (precios[ticker] && precios[ticker][fechaSimIdx] !== undefined && precios[ticker][fechaSimIdx] !== null) {
                        const precioInicial = precios[ticker][fechaSimIdx];
                        // Recalcular cantidad basada en asignacion_dinero y precio inicial
                        if (pos.asignacion_dinero && precioInicial > 0) {
                            pos.cantidad_recalculada = pos.asignacion_dinero / precioInicial;
                        }
                    }
                });
            } else {
                // Fallback: calcular usando cantidades y precios
                // IMPORTANTE: Usar cantidad_recalculada si está disponible para consistencia
                data.asignacion.forEach(pos => {
                    const ticker = pos.ticker;
                    const cantidadUsar = pos.cantidad_recalculada !== undefined ? pos.cantidad_recalculada : pos.cantidad;
                    
                    if (precios[ticker] && precios[ticker][fechaSimIdx] !== undefined && precios[ticker][fechaSimIdx] !== null) {
                        const precioInicial = precios[ticker][fechaSimIdx];
                        valorInicial += cantidadUsar * precioInicial;
                    } else if (pos.precio_actual) {
                        valorInicial += cantidadUsar * pos.precio_actual;
                    }
                });
            }
            
            // Validación: asegurar que valorInicial > 0
            if (valorInicial <= 0) {
                console.warn('⚠️ Valor inicial <= 0, usando fallback');
                valorInicial = asignacionDineroTotal || 10000; // Fallback seguro
            }
            
            // Obtener métricas de Monte Carlo para cálculo de percentiles
            const metricasMC = data.metricas_montecarlo || {};
            const percentilesMC = {
                percentil_5: metricasMC.percentil_5,
                percentil_25: metricasMC.percentil_25,
                percentil_75: metricasMC.percentil_75,
                percentil_95: metricasMC.percentil_95,
                ganancia_mediana: metricasMC.ganancia_mediana
            };
            
            // Mapear horizontes a días
            const horizontesDias = {
                '1m': 21,
                '3m': 63,
                '6m': 126,
                '1y': 252,
                'hoy': diasTranscurridos
            };
            
            const resultados = [];
            
            // Calcular valor actual una sola vez (precio de hoy)
            // IMPORTANTE: Usar la misma lógica de cantidad que se usó para valorInicial
            let valorActualHoy = 0;
            let tieneValorActualHoy = false;
            data.asignacion.forEach(pos => {
                const ticker = pos.ticker;
                // Usar cantidad_recalculada si está disponible, sino usar cantidad original
                const cantidadUsar = pos.cantidad_recalculada !== undefined ? pos.cantidad_recalculada : pos.cantidad;
                
                if (precios[ticker] && precios[ticker][fechaHoyIdx] !== undefined && precios[ticker][fechaHoyIdx] !== null) {
                    valorActualHoy += cantidadUsar * precios[ticker][fechaHoyIdx];
                    tieneValorActualHoy = true;
                }
            });
            
            // Debug: verificar consistencia de cantidades (solo en desarrollo)
            if (valorInicial > 0 && tieneValorActualHoy && typeof console !== 'undefined') {
                const retornoDebug = (valorActualHoy - valorInicial) / valorInicial;
                if (Math.abs(retornoDebug) > 0.5) {
                    console.warn(`⚠️ Retorno inicial extremo detectado: ${(retornoDebug * 100).toFixed(2)}%`);
                    console.warn(`   Valor inicial: ${valorInicial.toFixed(2)}, Valor actual hoy: ${valorActualHoy.toFixed(2)}`);
                }
            }
            
            // BACKTEST DE PROYECCIÓN CORRECTO - CALCULOS COMUNES
            
            // 1. Calcular retorno esperado HOY (común para todos los horizontes)
            // Retorno esperado hoy = (1 + retorno_anual)^(dias_transcurridos/252) - 1
            const retornoEsperadoHoy = diasTranscurridos > 0 
                ? Math.pow(1 + data.retorno_anual, diasTranscurridos / 252) - 1 
                : 0;
            
            // 2. Calcular retorno real HOY (común para todos los horizontes)
            const retornoRealHoy = tieneValorActualHoy && valorInicial > 0 
                ? (valorActualHoy - valorInicial) / valorInicial 
                : null;
            
            // 3. Calcular diferencia correcta: ret_real_hoy - ret_esperado_hoy
            const diferenciaHoy = retornoRealHoy !== null 
                ? retornoRealHoy - retornoEsperadoHoy 
                : null;
            
            // 4. Escalar percentiles para evaluación "hoy" (usando días transcurridos)
            const factorEscalaHoy = diasTranscurridos / 252;
            const percentilesEscaladosHoy = {
                percentil_5: percentilesMC.percentil_5 !== undefined ? percentilesMC.percentil_5 * factorEscalaHoy : null,
                percentil_25: percentilesMC.percentil_25 !== undefined ? percentilesMC.percentil_25 * factorEscalaHoy : null,
                percentil_75: percentilesMC.percentil_75 !== undefined ? percentilesMC.percentil_75 * factorEscalaHoy : null,
                percentil_95: percentilesMC.percentil_95 !== undefined ? percentilesMC.percentil_95 * factorEscalaHoy : null,
                ganancia_mediana: percentilesMC.ganancia_mediana !== undefined ? percentilesMC.ganancia_mediana * factorEscalaHoy : null
            };
            
            // 5. Calcular P&L actual para percentiles
            const pnlHoy = tieneValorActualHoy ? valorActualHoy - valorInicial : null;
            const percentilHoy = pnlHoy !== null ? calcularPercentil(pnlHoy, percentilesEscaladosHoy) : null;
            
            // 5.1. Análisis de sigma para "hoy"
            const analisisSigmaHoy = retornoRealHoy !== null && diasTranscurridos > 0
                ? analizarObservadoVsSigma(
                    retornoEsperadoHoy,
                    retornoRealHoy,
                    data.volatilidad_anual,
                    diasTranscurridos,
                    percentilesEscaladosHoy,
                    valorInicial
                )
                : null;
            
            // 6. Calcular probabilidad de ganar condicionada al resultado observado hasta hoy
            let probGanarCondicionada = null;
            if (retornoRealHoy !== null && diasTranscurridos > 0) {
                const probGanarBase = metricasMC.prob_ganar || 0.5;
                const factorTiempoHoy = Math.min(diasTranscurridos / 252, 1.0);
                
                // Probabilidad base ajustada por tiempo
                let probBaseAjustada = probGanarBase * (0.7 + 0.3 * factorTiempoHoy);
                
                // Condicionar según el resultado observado hasta hoy
                // Si el resultado actual está muy por debajo del esperado, reducir probabilidad
                // Si está por encima, aumentar probabilidad
                if (diferenciaHoy !== null) {
                    // Ajuste más conservador: si la diferencia es negativa grande, reducir más
                    const ajuste = diferenciaHoy * 2.0; // Factor de sensibilidad
                    probGanarCondicionada = Math.max(0.05, Math.min(0.95, probBaseAjustada + ajuste));
                } else {
                    probGanarCondicionada = probBaseAjustada;
                }
            }
            
            // 7. Procesar cada horizonte válido
            horizontesValidos.forEach(horizonte => {
                const diasHorizonte = horizontesDiasMap[horizonte];
                
                // Calcular fecha objetivo del horizonte
                const fechaFuturo = new Date(fechaSimulacion);
                fechaFuturo.setDate(fechaFuturo.getDate() + diasHorizonte);
                
                // Buscar índice de fecha objetivo del horizonte
                let fechaFuturoIdx = fechas.findIndex(f => {
                    const fechaF = new Date(f);
                    return fechaF >= fechaFuturo;
                });
                if (fechaFuturoIdx === -1) fechaFuturoIdx = fechaHoyIdx;
                fechaFuturoIdx = Math.min(fechaFuturoIdx, fechaHoyIdx);
                
                // A. Calcular retorno esperado del horizonte
                const retornoEsperadoHorizonte = Math.pow(1 + data.retorno_anual, diasHorizonte / 252) - 1;
                const valorEsperadoHorizonte = valorInicial * (1 + retornoEsperadoHorizonte);
                
                // B. Calcular retorno REAL del horizonte (en su fecha objetivo)
                let valorRealHorizonte = 0;
                data.asignacion.forEach(pos => {
                    const ticker = pos.ticker;
                    const cantidadUsar = pos.cantidad_recalculada !== undefined ? pos.cantidad_recalculada : pos.cantidad;
                    
                    if (precios[ticker] && precios[ticker][fechaFuturoIdx] !== undefined && precios[ticker][fechaFuturoIdx] !== null) {
                        const precioReal = precios[ticker][fechaFuturoIdx];
                        valorRealHorizonte += cantidadUsar * precioReal;
                    } else {
                        // Fallback: usar precio inicial
                        const precioInicial = precios[ticker] && precios[ticker][fechaSimIdx] !== undefined ? 
                            precios[ticker][fechaSimIdx] : (pos.precio_actual || 0);
                        valorRealHorizonte += cantidadUsar * precioInicial;
                    }
                });
                
                const retornoRealHorizonte = valorInicial > 0 
                    ? (valorRealHorizonte - valorInicial) / valorInicial 
                    : 0;
                
                // C. Escalar percentiles para evaluación del horizonte (usando días del horizonte)
                const factorEscalaHorizonte = diasHorizonte / 252;
                const percentilesEscaladosHorizonte = {
                    percentil_5: percentilesMC.percentil_5 !== undefined ? percentilesMC.percentil_5 * factorEscalaHorizonte : null,
                    percentil_25: percentilesMC.percentil_25 !== undefined ? percentilesMC.percentil_25 * factorEscalaHorizonte : null,
                    percentil_75: percentilesMC.percentil_75 !== undefined ? percentilesMC.percentil_75 * factorEscalaHorizonte : null,
                    percentil_95: percentilesMC.percentil_95 !== undefined ? percentilesMC.percentil_95 * factorEscalaHorizonte : null,
                    ganancia_mediana: percentilesMC.ganancia_mediana !== undefined ? percentilesMC.ganancia_mediana * factorEscalaHorizonte : null
                };
                
                // D. Calcular percentil del horizonte
                const pnlRealHorizonte = valorRealHorizonte - valorInicial;
                const percentilHorizonte = calcularPercentil(pnlRealHorizonte, percentilesEscaladosHorizonte);
                
                // D.1. Análisis de sigma para el horizonte
                const analisisSigmaHorizonte = analizarObservadoVsSigma(
                    retornoEsperadoHorizonte,
                    retornoRealHorizonte,
                    data.volatilidad_anual,
                    diasHorizonte,
                    percentilesEscaladosHorizonte,
                    valorInicial
                );
                
                // E. Probabilidad de ganar del horizonte (sin condicionar)
                const probGanarBase = metricasMC.prob_ganar || 0.5;
                const factorTiempoHorizonte = Math.min(diasHorizonte / 252, 1.0);
                const probGanarHorizonte = probGanarBase * (0.7 + 0.3 * factorTiempoHorizonte);
                
                // F. Guardar resultado (separando claramente horizonte vs hoy)
                resultados.push({
                    horizonte: horizonte.toUpperCase(),
                    diasHorizonte,
                    diasTranscurridos, // Para referencia
                    fechaFuturo: fechaFuturo.toISOString().split('T')[0],
                    fechaHoy: fechaHoy.toISOString().split('T')[0],
                    
                    // Valores del horizonte
                    valorInicial,
                    valorEsperadoHorizonte,
                    valorRealHorizonte,
                    retornoEsperadoHorizonte,
                    retornoRealHorizonte,
                    diferenciaHorizonte: retornoRealHorizonte - retornoEsperadoHorizonte,
                    pnlRealHorizonte,
                    percentilHorizonte,
                    probGanarHorizonte,
                    analisisSigmaHorizonte,
                    
                    // Valores hasta HOY (comunes para todos los horizontes)
                    valorRealHoy: tieneValorActualHoy ? valorActualHoy : null,
                    retornoEsperadoHoy,
                    retornoRealHoy,
                    diferenciaHoy,
                    pnlHoy,
                    percentilHoy,
                    probGanarCondicionada,
                    analisisSigmaHoy
                });
            });
            
            return resultados;
        }
        
        function displaySimulationResults(resultados, nombrePortafolio, tipo) {
            const resultsDiv = document.getElementById('simulation-results');
            const comparisonDiv = document.getElementById('simulation-comparison');
            
            if (!resultsDiv || !comparisonDiv) return;
            
            resultsDiv.classList.remove('hidden');
            
            const tipoLabel = tipo === 'composicion_global' ? 'Pesos Iguales' : tipo === 'maximo_sharpe' ? 'Máximo Sharpe' : 'Mínima Volatilidad';
            
            // Obtener retorno esperado hoy (común para todos) - del primer resultado
            const retornoEsperadoHoyComun = resultados.length > 0 ? resultados[0].retornoEsperadoHoy : null;
            const retornoRealHoyComun = resultados.length > 0 ? resultados[0].retornoRealHoy : null;
            const diferenciaHoyComun = resultados.length > 0 ? resultados[0].diferenciaHoy : null;
            const percentilHoyComun = resultados.length > 0 ? resultados[0].percentilHoy : null;
            const probGanarCondicionadaComun = resultados.length > 0 ? resultados[0].probGanarCondicionada : null;
            const analisisSigmaHoyComun = resultados.length > 0 ? resultados[0].analisisSigmaHoy : null;
            const diasTranscurridosComun = resultados.length > 0 ? resultados[0].diasTranscurridos : 0;
            
            comparisonDiv.innerHTML = `
                <div class="card p-6 mb-4">
                    <h4 class="text-xl font-semibold mb-4 text-slate-200">${nombrePortafolio} - ${tipoLabel}</h4>
                    
                    ${retornoEsperadoHoyComun !== null && retornoRealHoyComun !== null ? `
                    <div class="mb-4 p-4 bg-slate-800 rounded-lg border border-slate-700">
                        <h5 class="text-lg font-semibold mb-2 text-slate-300">Proyección hasta HOY (${diasTranscurridosComun} días transcurridos)</h5>
                        <div class="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm">
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Retorno Esperado HOY</div>
                                <div class="${retornoEsperadoHoyComun >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold">
                                    ${(retornoEsperadoHoyComun * 100).toFixed(2)}%
                                </div>
                            </div>
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Retorno Real HOY</div>
                                <div class="${retornoRealHoyComun >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold">
                                    ${(retornoRealHoyComun * 100).toFixed(2)}%
                                </div>
                            </div>
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Diferencia HOY</div>
                                <div class="${diferenciaHoyComun !== null ? (diferenciaHoyComun >= 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-500'} font-semibold">
                                    ${diferenciaHoyComun !== null ? ((diferenciaHoyComun * 100).toFixed(2) + '%') : 'N/A'}
                                </div>
                            </div>
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Análisis Sigma HOY</div>
                                <div class="text-xs">
                                    ${analisisSigmaHoyComun ? `
                                        <div class="font-semibold ${Math.abs(analisisSigmaHoyComun.zScore || 0) <= 1 ? 'text-yellow-400' : Math.abs(analisisSigmaHoyComun.zScore || 0) <= 2 ? 'text-orange-400' : 'text-red-400'}">
                                            ${analisisSigmaHoyComun.interpretacionSigma || 'N/A'}
                                        </div>
                                        <div class="text-slate-500 text-xs mt-1">
                                            Z: ${analisisSigmaHoyComun.zScore !== null ? analisisSigmaHoyComun.zScore.toFixed(2) : 'N/A'}
                                        </div>
                                        ${analisisSigmaHoyComun.percentilEmpirico !== null ? `
                                        <div class="text-slate-500 text-xs">
                                            Percentil: ${analisisSigmaHoyComun.percentilEmpirico.toFixed(1)}%
                                        </div>
                                        ` : ''}
                                    ` : 'N/A'}
                                </div>
                            </div>
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Percentil HOY</div>
                                <div class="text-xs">
                                    ${percentilHoyComun ? `<span class="${percentilHoyComun.percentil <= 25 ? 'text-red-400' : percentilHoyComun.percentil <= 50 ? 'text-yellow-400' : percentilHoyComun.percentil <= 75 ? 'text-green-400' : 'text-emerald-400'}">${percentilHoyComun.label}</span>` : 'N/A'}
                                </div>
                            </div>
                            <div>
                                <div class="text-slate-400 text-xs mb-1">Prob. Ganar (Cond.)</div>
                                <div class="text-xs">
                                    ${probGanarCondicionadaComun !== null ? `<span class="${probGanarCondicionadaComun >= 0.7 ? 'text-green-400' : probGanarCondicionadaComun >= 0.5 ? 'text-yellow-400' : 'text-red-400'}">${(probGanarCondicionadaComun * 100).toFixed(1)}%</span>` : 'N/A'}
                                </div>
                            </div>
                        </div>
                        ${analisisSigmaHoyComun && analisisSigmaHoyComun.explicacion ? `
                        <div class="mt-3 pt-3 border-t border-slate-700">
                            <div class="text-xs text-slate-400">
                                <strong>Interpretación:</strong> ${analisisSigmaHoyComun.explicacion}
                                ${analisisSigmaHoyComun.muPlus1Sigma !== null ? ` | μ+1σ: ${(analisisSigmaHoyComun.muPlus1Sigma * 100).toFixed(2)}%` : ''}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}
                    
                    <table class="w-full text-sm border-collapse">
                        <thead>
                            <tr class="border-b border-slate-600">
                                <th class="text-left py-2 px-3 text-slate-300" rowspan="2">Horizonte</th>
                                <th class="text-center py-2 px-3 text-slate-300 border-b border-slate-600" colspan="5">Evaluación del Horizonte</th>
                                <th class="text-center py-2 px-3 text-slate-300 border-b border-slate-600" colspan="2">Comparación HOY</th>
                                <th class="text-right py-2 px-3 text-slate-300" rowspan="2">Prob. Ganar</th>
                            </tr>
                            <tr class="border-b border-slate-600">
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Ret. Esperado</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Ret. Real</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Diferencia</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Percentil</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Análisis σ</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Ret. Esperado HOY</th>
                                <th class="text-right py-2 px-3 text-slate-300 text-xs">Ret. Real HOY</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${resultados.map((r, idx) => {
                                const horizonteLabel = `${r.horizonte} (${r.diasHorizonte} días)`;
                                
                                const percentilHorizonteLabel = r.percentilHorizonte 
                                    ? `<span class="${r.percentilHorizonte.percentil <= 25 ? 'text-red-400' : r.percentilHorizonte.percentil <= 50 ? 'text-yellow-400' : r.percentilHorizonte.percentil <= 75 ? 'text-green-400' : 'text-emerald-400'}">${r.percentilHorizonte.label}</span>`
                                    : 'N/A';
                                
                                const probGanarHorizonteLabel = r.probGanarHorizonte !== undefined 
                                    ? `<span class="${r.probGanarHorizonte >= 0.7 ? 'text-green-400' : r.probGanarHorizonte >= 0.5 ? 'text-yellow-400' : 'text-red-400'}">${(r.probGanarHorizonte * 100).toFixed(1)}%</span>`
                                    : 'N/A';
                                
                                // Retorno esperado hoy (común, solo mostrar en primera fila)
                                const retornoEsperadoHoyCell = idx === 0 
                                    ? `<td class="py-2 px-3 text-right ${r.retornoEsperadoHoy >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold" rowspan="${resultados.length}">${(r.retornoEsperadoHoy * 100).toFixed(2)}%</td>`
                                    : '';
                                
                                const retornoRealHoyCell = idx === 0 
                                    ? `<td class="py-2 px-3 text-right ${r.retornoRealHoy !== null ? (r.retornoRealHoy >= 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-500'} font-semibold" rowspan="${resultados.length}">${r.retornoRealHoy !== null ? ((r.retornoRealHoy * 100).toFixed(2) + '%') : 'N/A'}</td>`
                                    : '';
                                
                                return `
                                <tr class="border-b border-slate-700">
                                    <td class="py-2 px-3 text-slate-400">${horizonteLabel}</td>
                                    <td class="py-2 px-3 text-right ${r.retornoEsperadoHorizonte >= 0 ? 'text-green-400' : 'text-red-400'}">${(r.retornoEsperadoHorizonte * 100).toFixed(2)}%</td>
                                    <td class="py-2 px-3 text-right ${r.retornoRealHorizonte >= 0 ? 'text-green-400' : 'text-red-400'}">${(r.retornoRealHorizonte * 100).toFixed(2)}%</td>
                                    <td class="py-2 px-3 text-right ${r.diferenciaHorizonte >= 0 ? 'text-green-400' : 'text-red-400'}">${(r.diferenciaHorizonte * 100).toFixed(2)}%</td>
                                    <td class="py-2 px-3 text-right text-xs">${percentilHorizonteLabel}</td>
                                    <td class="py-2 px-3 text-right text-xs">
                                        ${r.analisisSigmaHorizonte ? `
                                            <div class="font-semibold ${Math.abs(r.analisisSigmaHorizonte.zScore || 0) <= 1 ? 'text-yellow-400' : Math.abs(r.analisisSigmaHorizonte.zScore || 0) <= 2 ? 'text-orange-400' : 'text-red-400'}">
                                                ${r.analisisSigmaHorizonte.interpretacionSigma || 'N/A'}
                                            </div>
                                            <div class="text-slate-500 text-xs">
                                                Z: ${r.analisisSigmaHorizonte.zScore !== null ? r.analisisSigmaHorizonte.zScore.toFixed(2) : 'N/A'}
                                            </div>
                                        ` : 'N/A'}
                                    </td>
                                    ${retornoEsperadoHoyCell}
                                    ${retornoRealHoyCell}
                                    <td class="py-2 px-3 text-right text-xs">${probGanarHorizonteLabel}</td>
                                </tr>
                            `;
                            }).join('')}
                        </tbody>
                    </table>
                    <div class="mt-4 text-xs text-slate-400 space-y-2">
                        <p><strong>Explicación de Métricas:</strong></p>
                        <ul class="list-disc list-inside space-y-1 ml-2">
                            <li><strong>Evaluación del Horizonte:</strong> Muestra cómo fue la predicción del modelo para cada horizonte temporal específico (ej: 1M, 3M). El "Retorno Real" es el observado en la fecha objetivo de ese horizonte.</li>
                            <li><strong>Comparación HOY:</strong> Muestra la proyección y el resultado real hasta la fecha actual. El "Retorno Esperado HOY" es único (calculado desde fecha de simulación hasta hoy) y se compara con el "Retorno Real HOY" (también único).</li>
                            <li><strong>Diferencia (Horizonte):</strong> Retorno Real del Horizonte - Retorno Esperado del Horizonte. Mide qué tan precisa fue la predicción para ese horizonte específico.</li>
                            <li><strong>Diferencia HOY:</strong> Se muestra en el panel superior. Retorno Real HOY - Retorno Esperado HOY. Mide el desempeño real vs lo proyectado hasta hoy.</li>
                        </ul>
                        <p><strong>Percentiles:</strong> Se calculan comparando el P&L con la distribución de Monte Carlo escalada al horizonte correspondiente. Cada evaluación usa su propia escala temporal (horizonte del horizonte, días transcurridos para HOY).</p>
                        <p><strong>Análisis σ (Sigma):</strong> Determina si el retorno observado se explica por μ + k·σ (donde μ = retorno esperado, σ = volatilidad escalada al horizonte). El z-score indica cuántas desviaciones estándar se desvía el resultado observado del esperado. |z| ≤ 1 = dentro de ±1σ, 1 < |z| ≤ 2 = evento poco probable, |z| > 2 = evento muy raro.</p>
                        <p><strong>Probabilidades:</strong> La probabilidad del horizonte es teórica (basada en Monte Carlo). La probabilidad condicionada (en el panel superior) está ajustada según el resultado observado hasta hoy.</p>
                    </div>
                </div>
            `;
        }
        
        // Exponer funciones globalmente
        window.switchTab = switchTab;
        window.downloadPortfolioJSON = downloadPortfolioJSON;
        
        function toggleDistribution(slideId) {
            const distributionDiv = document.getElementById(`distribution-${slideId}`);
            const icon = document.getElementById(`icon-${slideId}`);
            
            if (distributionDiv && icon) {
                const isHidden = distributionDiv.classList.contains('hidden');
                if (isHidden) {
                    distributionDiv.classList.remove('hidden');
                    icon.classList.add('rotate-180');
                } else {
                    distributionDiv.classList.add('hidden');
                    icon.classList.remove('rotate-180');
                }
            }
        }
        
        function toggleComparativo(slideId) {
            const comparativoDiv = document.getElementById(`comparativo-${slideId}`);
            const icon = document.getElementById(`icon-${slideId}`);
            
            if (comparativoDiv && icon) {
                const isHidden = comparativoDiv.classList.contains('hidden');
                if (isHidden) {
                    comparativoDiv.classList.remove('hidden');
                    icon.classList.add('rotate-180');
                } else {
                    comparativoDiv.classList.add('hidden');
                    icon.classList.remove('rotate-180');
                }
            }
        }
        
        function toggleRetornosProyectados(slideId) {
            const retornosDiv = document.getElementById(`retornos-proyectados-${slideId}`);
            const icon = document.getElementById(`icon-retornos-${slideId}`);
            
            if (retornosDiv && icon) {
                const isHidden = retornosDiv.classList.contains('hidden');
                if (isHidden) {
                    retornosDiv.classList.remove('hidden');
                    icon.classList.add('rotate-180');
                } else {
                    retornosDiv.classList.add('hidden');
                    icon.classList.remove('rotate-180');
                }
            }
        }

        // Exponer funciones al ámbito global para que los onclick inline puedan usarlas
        window.toggleComparativo = toggleComparativo;
        window.toggleDistribution = toggleDistribution;
        
        function showSlide(index) {
            slides.forEach((slide, idx) => {
                slide.classList.toggle('active', idx === index);
            });
            currentSlideIndex = index;
            updateSlideCounter();
            renderAllCharts();
        }
        
        function updateSlideCounter() {
            const counter = document.getElementById('slide-counter');
            if (counter) {
                counter.textContent = `${currentSlideIndex + 1} / ${slides.length}`;
            }
        }
        
        function renderAllCharts() {
            Object.entries(OPTIMIZATION_DATA.portafolios).forEach(([key, portfolio], portfolioIdx) => {
                const types = ['composicion_global', 'maximo_sharpe', 'minima_volatilidad'];
                types.forEach((type, typeIdx) => {
                    const data = portfolio[type];
                    const chartId = `chart-${key}-${type}-${portfolioIdx}`;
                    const barChartId = `barchart-${key}-${type}-${portfolioIdx}`;
                    const frontierChartId = `frontier-${key}-${type}-${portfolioIdx}`;
                    
                    // Gráfico de pastel - incluir TODOS los activos con peso > 0
                    // Mostrar TODOS los activos del portafolio en la tabla, pero solo graficar los que tienen peso > 0
                    const pieData = data.asignacion
                        .filter(item => item.peso_porcentaje > 0)  // Solo activos con peso > 0 para el gráfico
                        .map(item => ({
                            name: item.ticker,
                            value: item.peso_porcentaje,
                            allocation: item.asignacion_dinero
                        }));
                    createPieChart(chartId, pieData, 'Composición');
                    
                    // Gráfico de barras (usar percentiles)
                    createBarChart(barChartId, data.percentiles || {}, 'Distribución de Retornos (Percentiles)');
                    
                    // Gráfico de frontera eficiente
                    const frontierData = portfolio.frontera_eficiente || [];
                    const portfolioPoints = {};
                    // Solo mostrar el punto correspondiente al tipo actual
                    if (data && data.volatilidad_anual !== undefined && data.retorno_anual !== undefined) {
                        portfolioPoints[type] = {
                            volatilidad: data.volatilidad_anual,
                            retorno: data.retorno_anual
                        };
                    }
                    createEfficientFrontierChart(frontierChartId, frontierData, portfolioPoints, `Frontera Eficiente - ${portfolio.nombre}`);
                });
            });
        }
        
        async function downloadSlide(index) {
            const slide = slides[index];
            if (!slide) return;
            
            try {
                // Mostrar el slide si no está visible
                const wasActive = slide.classList.contains('active');
                if (!wasActive) {
                    slide.classList.add('active');
                    slide.style.display = 'block';
                    slide.style.visibility = 'visible';
                    slide.style.position = 'relative';
                    slide.style.height = 'auto';
                    slide.style.overflow = 'visible';
                }
                
                // Esperar a que se rendericen los gráficos
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Re-renderizar gráficos para asegurar que estén listos
                renderAllCharts();
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Forzar recálculo de dimensiones
                slide.style.height = 'auto';
                slide.style.maxHeight = 'none';
                slide.style.overflow = 'visible';
                
                // Obtener dimensiones completas del contenido
                // Usar scrollHeight/scrollWidth para obtener todo el contenido
                const rect = slide.getBoundingClientRect();
                const scrollHeight = slide.scrollHeight || slide.offsetHeight || rect.height;
                const scrollWidth = slide.scrollWidth || slide.offsetWidth || rect.width;
                
                // Asegurar que tenemos dimensiones válidas
                const fullHeight = Math.max(scrollHeight, 1000);
                const fullWidth = Math.max(scrollWidth, 1200);
                
                // Obtener color de fondo según la plantilla actual
                const bgColors = {
                    'minimal-dark': '#0a0e1a',
                    'executive-dark': '#0a0f1c',
                    'bloomberg': '#1a1a1a',
                    'institutional': '#0d1117',
                    'financial-report': '#ffffff',
                    'quant-dark': '#000000'
                };
                const bgColor = bgColors[currentTemplate] || '#0f172a';
                
                // Capturar el slide completo usando las dimensiones reales
                const dataUrl = await htmlToImage.toPng(slide, {
                    quality: 1.0,
                    pixelRatio: 2, // Alta resolución
                    backgroundColor: bgColor,
                    useCORS: true,
                    allowTaint: true,
                    width: fullWidth,
                    height: fullHeight,
                    cacheBust: true,
                    scrollX: 0,
                    scrollY: 0,
                    // Asegurar que capture todo el contenido
                    filter: (node) => {
                        // Incluir todos los elementos del slide y excluir controles de navegación
                        if (node.classList && (
                            node.classList.contains('header') ||
                            node.classList.contains('template-selector') ||
                            node.id === 'prev-slide' ||
                            node.id === 'next-slide' ||
                            node.id === 'download-current' ||
                            node.id === 'download-all' ||
                            node.id === 'slide-counter'
                        )) {
                            return false;
                        }
                        return true;
                    }
                });
                
                // Restaurar estado original si no estaba activo
                if (!wasActive) {
                    slide.classList.remove('active');
                    slide.style.display = '';
                    slide.style.visibility = '';
                    slide.style.position = '';
                    slide.style.height = '';
                    slide.style.maxHeight = '';
                    slide.style.overflow = '';
                }
                
                const portfolioName = slide.id.replace('slide-', '').replace(/-/g, '_');
                download(dataUrl, `portfolio_${portfolioName}_${index + 1}.png`);
            } catch (error) {
                console.error('Error descargando slide:', error);
                alert('Error al descargar el slide. Verifica la consola para más detalles.');
            }
        }
    </script>
</body>
</html>"""


def generar_html_optimizaciones(
    resumen_spy_qqq: PortfolioSummary,
    pf_spy_qqq_df: pd.DataFrame,
    pf_spy_qqq_ms: pd.Series,
    pf_spy_qqq_mv: pd.Series,
    resumen_high: PortfolioSummary,
    pf_high_df: pd.DataFrame,
    pf_high_ms: pd.Series,
    pf_high_mv: pd.Series,
    resumen_low: PortfolioSummary,
    pf_low_df: pd.DataFrame,
    pf_low_ms: pd.Series,
    pf_low_mv: pd.Series,
    resumen_high_ext: PortfolioSummary,
    pf_high_ext_df: pd.DataFrame,
    pf_high_ext_ms: pd.Series,
    pf_high_ext_mv: pd.Series,
    resumen_low_ext: PortfolioSummary,
    pf_low_ext_df: pd.DataFrame,
    pf_low_ext_ms: pd.Series,
    pf_low_ext_mv: pd.Series,
    resumen_skew: PortfolioSummary,
    pf_skew_df: pd.DataFrame,
    pf_skew_ms: pd.Series,
    pf_skew_mv: pd.Series,
    resumen_neg: PortfolioSummary,
    pf_neg_df: pd.DataFrame,
    pf_neg_ms: pd.Series,
    pf_neg_mv: pd.Series,
    resumen_bcba: PortfolioSummary,
    pf_bcba_df: pd.DataFrame,
    pf_bcba_ms: pd.Series,
    pf_bcba_mv: pd.Series,
    metricas_spy_qqq: Dict[str, Dict],
    monto_inversion: float,
    returns: pd.DataFrame,
    df_precios: pd.DataFrame,
    risk_free_rate: float = 0.08,  # 8% en USD
) -> None:
    """
    Genera un archivo HTML con las optimizaciones realizadas en el formato
    especificado para hacer publicidad de los portafolios sugeridos.
    """
    import json
    from datetime import datetime
    
    # Preparar datos para el HTML
    # Convertir DataFrames y Series a estructuras JSON serializables
    def preparar_datos_portafolio(resumen, pf_df, pf_ms, pf_mv, returns_subset, monto_inversion_override=None):
        """Prepara los datos de un portafolio para el HTML"""
        # Usar monto_inversion_override si se proporciona, sino usar el global
        monto_inversion_local = monto_inversion_override if monto_inversion_override is not None else monto_inversion
        # Preparar datos de la frontera eficiente (Monte Carlo)
        # Muestrear portafolios para no sobrecargar el JSON (máximo 500 puntos)
        if len(pf_df) > 500:
            # Muestrear aleatoriamente
            np.random.seed(42)
            indices_muestra = np.random.choice(len(pf_df), size=500, replace=False)
            pf_df_muestra = pf_df.iloc[indices_muestra]
        else:
            pf_df_muestra = pf_df
        
        # Convertir a lista de diccionarios para JSON
        frontera_eficiente = []
        for _, row in pf_df_muestra.iterrows():
            frontera_eficiente.append({
                "retorno": float(row["Return"]),
                "volatilidad": float(row["Volatility"]),
                "sharpe": float(row["Sharpe"])
            })
        # Obtener precios actuales (último precio disponible)
        precios_actuales = {}
        for ticker in resumen.tickers:
            if ticker in df_precios.columns:
                precio_serie = df_precios[ticker].dropna()
                if len(precio_serie) > 0:
                    precios_actuales[ticker] = float(precio_serie.iloc[-1])
        
        # Obtener pesos del máximo Sharpe - INCLUIR TODOS LOS TICKERS DEL PORTAFOLIO
        weight_cols_ms = [c for c in pf_df.columns if c.startswith("Weight_")]
        pesos_ms = {}
        # Primero, inicializar todos los tickers del portafolio con peso 0
        for ticker in resumen.tickers:
            pesos_ms[ticker] = 0.0
        # Luego, asignar los pesos reales de la optimización
        for col in weight_cols_ms:
            w = pf_ms.get(col, 0.0)
            ticker = col.replace("Weight_", "")
            if ticker in resumen.tickers:  # Solo incluir si está en el portafolio
                pesos_ms[ticker] = float(w)
        
        # Obtener pesos de mínima volatilidad - INCLUIR TODOS LOS TICKERS DEL PORTAFOLIO
        pesos_mv = {}
        # Primero, inicializar todos los tickers del portafolio con peso 0
        for ticker in resumen.tickers:
            pesos_mv[ticker] = 0.0
        # Luego, asignar los pesos reales de la optimización
        for col in weight_cols_ms:
            w = pf_mv.get(col, 0.0)
            ticker = col.replace("Weight_", "")
            if ticker in resumen.tickers:  # Solo incluir si está en el portafolio
                pesos_mv[ticker] = float(w)
        
        # Obtener pesos para composición global (pesos iguales) - INCLUIR TODOS LOS TICKERS DEL PORTAFOLIO
        pesos_global_calculo = {t: 1.0 / len(resumen.tickers) for t in resumen.tickers}
        
        # Calcular métricas básicas
        retorno_anual = float(resumen.mean_return_annual)
        volatilidad_anual = float(resumen.volatility_annual)
        sharpe = float(resumen.sharpe_ratio)
        
        # Escenarios para máximo Sharpe
        ret_ms = float(pf_ms["Return"])
        vol_ms = float(pf_ms["Volatility"])
        sharpe_ms = float(pf_ms["Sharpe"])
        
        # Escenarios para mínima volatilidad
        ret_mv = float(pf_mv["Return"])
        vol_mv = float(pf_mv["Volatility"])
        sharpe_mv = float(pf_mv["Sharpe"])
        
        # Calcular sectores de todos los tickers del portafolio ANTES de usarlos
        sectores_tickers = {}  # Mapeo ticker -> sector
        for ticker in resumen.tickers:
            sector = obtener_sector_ticker(ticker)
            sectores_tickers[ticker] = sector
        
        # Función auxiliar para calcular asignación y cantidades
        def calcular_asignacion(pesos_dict, tipo="composicion_global"):
            asignacion = []
            
            # Para composicion_global (pesos iguales), usar 1 unidad de cada activo
            if tipo == "composicion_global":
                # Calcular el monto total real necesario para comprar 1 unidad de cada activo
                monto_total_real = 0.0
                cantidades_reales = {}
                for ticker in pesos_dict.keys():
                    precio_actual = precios_actuales.get(ticker, 0)
                    if precio_actual > 0:
                        cantidades_reales[ticker] = 1.0  # Exactamente 1 unidad
                        monto_total_real += precio_actual
                    else:
                        cantidades_reales[ticker] = 0.0
                
                # Calcular asignación con 1 unidad de cada activo
                for ticker in pesos_dict.keys():
                    precio_actual = precios_actuales.get(ticker, 0)
                    cantidad = cantidades_reales.get(ticker, 0.0)
                    asignacion_dinero_real = cantidad * precio_actual
                    
                    # Obtener sector del ticker
                    sector = sectores_tickers.get(ticker, "Desconocido")
                    
                    # Calcular peso real basado en el monto total real
                    peso_real = asignacion_dinero_real / monto_total_real if monto_total_real > 0 else 0.0
                    
                    # Calcular ganancia esperada basada en la asignación real
                    ganancia_esperada = asignacion_dinero_real * retorno_anual
                    
                    asignacion.append({
                        "ticker": ticker,
                        "sector": sector,
                        "peso_porcentaje": peso_real * 100,  # Peso real basado en monto total real
                        "asignacion_dinero": float(asignacion_dinero_real),  # Asignación real = 1 unidad * precio
                        "precio_actual": float(precio_actual),
                        "cantidad": float(cantidad),  # Siempre 1 unidad
                        "ganancia_esperada": float(ganancia_esperada),
                    })
            else:
                # Para máximo Sharpe y mínima volatilidad, usar los pesos óptimos tal cual
                # sin forzar redondeo de cantidades. Esto garantiza que todas las
                # optimizaciones utilicen la MISMA cantidad de activos (los mismos tickers)
                # y que no se "caigan" activos por redondeo a 0 unidades.
                for ticker, peso in pesos_dict.items():
                    asignacion_dinero_ideal = peso * monto_inversion_local
                    precio_actual = precios_actuales.get(ticker, 0)
                    
                    # Obtener sector del ticker
                    sector = sectores_tickers.get(ticker, "Desconocido")
                    
                    # Permitir cantidades fraccionales para respetar exactamente los pesos
                    if precio_actual > 0 and asignacion_dinero_ideal > 0:
                        cantidad = asignacion_dinero_ideal / precio_actual  # puede ser fraccional
                        asignacion_dinero_real = asignacion_dinero_ideal   # respetar el peso ideal
                    else:
                        cantidad = 0.0
                        asignacion_dinero_real = 0.0
                    
                    # Calcular ganancia esperada basada en la asignación ideal
                    if tipo == "maximo_sharpe":
                        ganancia_esperada = asignacion_dinero_real * ret_ms
                    else:
                        ganancia_esperada = asignacion_dinero_real * ret_mv
                    
                    # Peso real coincide con el peso del portafolio optimizado
                    peso_real = peso
                    
                    asignacion.append({
                        "ticker": ticker,
                        "sector": sector,
                        "peso_porcentaje": peso_real * 100,
                        "asignacion_dinero": float(asignacion_dinero_real),
                        "precio_actual": float(precio_actual),
                        "cantidad": float(cantidad),
                        "ganancia_esperada": float(ganancia_esperada),
                    })
            return asignacion
        
        # Matriz de correlación - IMPORTANTE: Calcular métricas POR CADA optimización específica
        # Esto asegura que las métricas entre activos solo incluyan activos realmente en cada optimización
        
        # Función auxiliar para calcular métricas entre activos para una optimización específica
        def calcular_metricas_para_optimizacion(pesos_dict, nombre_optimizacion):
            """Calcula métricas entre activos solo para los activos con peso > 0 en esta optimización"""
            # Obtener solo los activos con peso > 0 en esta optimización específica
            activos_con_peso_opt = [ticker for ticker, peso in pesos_dict.items() if peso > 0.0001]
            
            if len(activos_con_peso_opt) < 2:
                print(f"   ⚠️  {nombre_optimizacion}: Solo {len(activos_con_peso_opt)} activo(s) con peso > 0, no se pueden calcular métricas entre pares")
                return []
            
            # Filtrar solo los tickers que están disponibles en returns_subset
            tickers_validos_opt = [t for t in activos_con_peso_opt if t in returns_subset.columns]
            
            if len(tickers_validos_opt) < 2:
                print(f"   ⚠️  {nombre_optimizacion}: Solo {len(tickers_validos_opt)} activo(s) disponible(s) en returns, no se pueden calcular métricas entre pares")
                return []
            
            print(f"   📊 {nombre_optimizacion}: Calculando métricas entre {len(tickers_validos_opt)} activos con peso > 0")
            
            # Calcular matriz de correlación solo para estos activos
            returns_para_corr_opt = returns_subset[tickers_validos_opt]
            corr_matrix_opt = returns_para_corr_opt.corr().round(6).to_dict()
            
            metricas_pares_opt = []
            pares_calculados_opt = set()
            
            # Calcular TODOS los pares entre estos activos
            for i, ticker1 in enumerate(tickers_validos_opt):
                for ticker2 in tickers_validos_opt[i+1:]:
                    par_key = (ticker1, ticker2)
                    if par_key in pares_calculados_opt:
                        continue
                    
                    try:
                        # Obtener correlación de la matriz
                        correlacion = None
                        if ticker1 in corr_matrix_opt and ticker2 in corr_matrix_opt[ticker1]:
                            correlacion = corr_matrix_opt[ticker1][ticker2]
                        elif ticker2 in corr_matrix_opt and ticker1 in corr_matrix_opt[ticker2]:
                            correlacion = corr_matrix_opt[ticker2][ticker1]
                        
                        if correlacion is None or np.isnan(correlacion):
                            continue
                        
                        correlacion = float(correlacion)
                        r_squared = correlacion ** 2
                        
                        # Calcular beta y alpha
                        beta = 0.0
                        alpha_anual = 0.0
                        
                        if ticker1 in returns_subset.columns and ticker2 in returns_subset.columns:
                            serie1 = returns_subset[ticker1].dropna()
                            serie2 = returns_subset[ticker2].dropna()
                            
                            # Alinear series por fecha
                            serie1_aligned, serie2_aligned = serie1.align(serie2, join='inner')
                            
                            if len(serie1_aligned) >= 20:
                                # Calcular beta: cov(X,Y) / var(X)
                                cov = np.cov(serie1_aligned, serie2_aligned)[0, 1]
                                var = np.var(serie1_aligned)
                                if var > 0:
                                    beta = cov / var
                                    
                                    # Calcular alpha anual: (mean(Y) - beta * mean(X)) * 252
                                    mean1 = serie1_aligned.mean()
                                    mean2 = serie2_aligned.mean()
                                    alpha_diario = mean2 - beta * mean1
                                    alpha_anual = alpha_diario * 252
                        
                        metricas_pares_opt.append({
                            "activo1": ticker1,
                            "activo2": ticker2,
                            "correlacion": correlacion,
                            "r_squared": r_squared,
                            "beta": beta,
                            "alpha_anual": alpha_anual,
                        })
                        
                        pares_calculados_opt.add(par_key)
                    except Exception as e:
                        continue
            
            total_pares_posibles_opt = len(tickers_validos_opt) * (len(tickers_validos_opt) - 1) // 2
            print(f"      {len(tickers_validos_opt)} activos, {total_pares_posibles_opt} pares posibles, {len(metricas_pares_opt)} pares calculados")
            
            # Aplicar filtro de alta correlación si es un portafolio de alta correlación
            if "Alta Correlación" in resumen.nombre:
                UMBRAL_CORR_ALTA = 0.70
                metricas_pares_opt = [
                    m for m in metricas_pares_opt
                    if abs(m.get("correlacion", 0.0)) >= UMBRAL_CORR_ALTA
                ]
                metricas_pares_opt = sorted(
                    metricas_pares_opt,
                    key=lambda m: abs(m.get("correlacion", 0.0)),
                    reverse=True,
                )
                if len(metricas_pares_opt) > 0:
                    print(f"      ✅ Filtrado aplicado: {len(metricas_pares_opt)} pares con correlación >= {UMBRAL_CORR_ALTA}")
                else:
                    print(f"      ⚠️  No se encontraron pares con correlación >= {UMBRAL_CORR_ALTA} en esta optimización")
            
            # Aplicar filtro de correlación negativa si es un portafolio de correlación negativa
            if "Correlación Negativa" in resumen.nombre:
                metricas_pares_opt = [
                    m for m in metricas_pares_opt
                    if m.get("correlacion", 0.0) < 0.0
                ]
                if len(metricas_pares_opt) > 0:
                    print(f"      ✅ Filtrado aplicado: {len(metricas_pares_opt)} pares con correlación negativa")
                else:
                    print(f"      ⚠️  No se encontraron pares con correlación negativa en esta optimización")
            
            return metricas_pares_opt
        
        # Calcular métricas para cada optimización por separado
        metricas_pares_ms = calcular_metricas_para_optimizacion(pesos_ms, "Máximo Sharpe")
        metricas_pares_mv = calcular_metricas_para_optimizacion(pesos_mv, "Mínima Volatilidad")
        metricas_pares_global = calcular_metricas_para_optimizacion(pesos_global_calculo, "Pesos Iguales")
        
        # Para compatibilidad con el código existente, usar las métricas de "Pesos Iguales" como base
        # (ya que incluye todos los activos del portafolio)
        metricas_pares_activos = metricas_pares_global
        
        # Obtener todos los activos que tienen peso > 0 en alguna optimización (para uso general)
        activos_con_peso = set()
        for ticker, peso in pesos_ms.items():
            if peso > 0.0001:
                activos_con_peso.add(ticker)
        for ticker, peso in pesos_mv.items():
            if peso > 0.0001:
                activos_con_peso.add(ticker)
        for ticker, peso in pesos_global_calculo.items():
            if peso > 0.0001:
                activos_con_peso.add(ticker)
        
        # Si no hay activos con peso (caso raro), usar todos los del portafolio original
        if not activos_con_peso:
            tickers_portafolio = sorted(resumen.tickers)
            print(f"   ⚠️  Advertencia: No se encontraron activos con peso > 0, usando todos los activos del portafolio original")
        else:
            # Usar solo los activos que tienen peso > 0 en alguna optimización
            tickers_portafolio = sorted(activos_con_peso)
            print(f"   ✅ Usando {len(tickers_portafolio)} activos con peso > 0 en alguna optimización (de {len(resumen.tickers)} activos originales)")
        
        # Filtrar solo los tickers del portafolio que están disponibles en returns_subset
        # Esto asegura que solo se calculen correlaciones entre activos del portafolio
        tickers_disponibles_en_returns = [t for t in tickers_portafolio if t in returns_subset.columns]
        
        # Validación: asegurar que estamos usando solo los activos del portafolio
        if len(tickers_disponibles_en_returns) < len(tickers_portafolio):
            faltantes = [t for t in tickers_portafolio if t not in returns_subset.columns]
            print(f"   ⚠️  Advertencia: {len(faltantes)} ticker(s) del portafolio no están en returns_subset: {faltantes[:5]}...")
        
        # Debug: para portafolio "Correlación Negativa", mostrar los activos que se usarán
        if "Correlación Negativa" in resumen.nombre:
            print(f"   📊 Portafolio 'Correlación Negativa': {len(tickers_portafolio)} activos con peso > 0")
            print(f"      Activos disponibles en returns: {len(tickers_disponibles_en_returns)}")
            print(f"      Activos del portafolio optimizado: {', '.join(tickers_portafolio[:10])}{'...' if len(tickers_portafolio) > 10 else ''}")
        
        # Calcular matriz de correlación SOLO con los tickers del portafolio
        # Esto es crítico para mantener coherencia: solo correlaciones entre activos del portafolio
        returns_para_corr = returns_subset[tickers_disponibles_en_returns] if tickers_disponibles_en_returns else returns_subset
        corr_matrix = returns_para_corr.corr().round(6).to_dict()
        
        # Las métricas entre activos ahora se calculan por optimización específica arriba
        # Usar las métricas de "Pesos Iguales" como fallback para compatibilidad
        metricas_pares_activos = metricas_pares_global
        
        if "Correlación Negativa" in resumen.nombre:
            pares_negativos = [p for p in metricas_pares_activos if p.get("correlacion", 0.0) < 0.0]
            print(f"   📊 Portafolio 'Correlación Negativa': {len(pares_negativos)} pares con correlación negativa de {len(metricas_pares_activos)} pares totales")
            if len(pares_negativos) < len(metricas_pares_activos):
                print(f"      ⚠️  Hay {len(metricas_pares_activos) - len(pares_negativos)} pares con correlación positiva/cero que serán filtrados")
            # Mostrar algunos ejemplos de pares negativos para verificación
            if pares_negativos:
                ejemplos = pares_negativos[:5]
                ejemplos_str = ', '.join([f"{p['activo1']}-{p['activo2']} ({p['correlacion']:.3f})" for p in ejemplos])
                print(f"      Ejemplos de pares con correlación negativa: {ejemplos_str}")
        
        # Ajustes de consistencia para portafolios especiales:
        # 1) Alta Correlación: mostrar SOLO los pares con |correlación| alta (umbral definido),
        #    respetando estrictamente el filtro del portafolio.
        # 2) Correlación Negativa: mostrar SOLO los pares con correlación < 0 (sin excepciones),
        #    respetando estrictamente su filtro.
        #
        # IMPORTANTE: Para estos portafolios, es preferible que la tabla quede vacía
        # antes que mostrar pares que no cumplen el criterio del filtro.
        if metricas_pares_activos:
            metricas_filtradas = metricas_pares_activos
            
            if "Alta Correlación" in resumen.nombre:
                # Umbral de alta correlación (absoluta)
                UMBRAL_CORR_ALTA = 0.70
                candidatas = [
                    m for m in metricas_pares_activos
                    if abs(m.get("correlacion", 0.0)) >= UMBRAL_CORR_ALTA
                ]
                # Aplicar SIEMPRE el filtro, aunque deje pocos pares (o ninguno):
                # el portafolio debe respetar estrictamente su criterio.
                metricas_filtradas = sorted(
                    candidatas,
                    key=lambda m: abs(m.get("correlacion", 0.0)),
                    reverse=True,
                )
                # Mensajes informativos según la cantidad de pares encontrados
                if len(candidatas) == 0:
                    print(f"   ⚠️  Advertencia: No se encontraron pares con correlación >= {UMBRAL_CORR_ALTA} en el portafolio 'Alta Correlación'")
                    print(f"      Total de pares calculados: {len(metricas_pares_activos)}")
                    print(f"      Activos del portafolio: {len(tickers_portafolio)}")
                    print(f"      Esto indica que el portafolio optimizado no tiene suficientes pares con alta correlación")
                    print(f"      Posibles causas: la optimización seleccionó activos con baja correlación entre sí")
                elif len(candidatas) == 1:
                    par_unico = candidatas[0]
                    print(f"   ⚠️  Advertencia: Solo se encontró 1 par con correlación >= {UMBRAL_CORR_ALTA} en el portafolio 'Alta Correlación'")
                    print(f"      Par encontrado: {par_unico.get('activo1')}-{par_unico.get('activo2')} (correlación: {par_unico.get('correlacion', 0.0):.3f})")
                    print(f"      Total de pares calculados: {len(metricas_pares_activos)}")
                    print(f"      Esto indica que el portafolio optimizado tiene muy pocos activos con alta correlación entre sí")
                elif len(candidatas) < 5:
                    print(f"   ⚠️  Advertencia: Solo se encontraron {len(candidatas)} pares con correlación >= {UMBRAL_CORR_ALTA} en el portafolio 'Alta Correlación'")
                    print(f"      Total de pares calculados: {len(metricas_pares_activos)}")
                    print(f"      Esto puede indicar que el portafolio optimizado tiene limitada diversificación por alta correlación")
                else:
                    print(f"   ✅ Filtrado aplicado: {len(candidatas)} pares con correlación >= {UMBRAL_CORR_ALTA} de {len(metricas_pares_activos)} pares totales")
            
            if "Correlación Negativa" in resumen.nombre:
                # Para correlación negativa, mostrar SOLO los pares con correlación < 0
                # SIN EXCEPCIONES. No mostrar pares con correlación positiva o cero.
                # Validación adicional: asegurar que ambos activos estén en el portafolio
                candidatas = [
                    m for m in metricas_pares_activos
                    if (m.get("correlacion", 0.0) < 0.0 and 
                        m.get("activo1") in tickers_portafolio and 
                        m.get("activo2") in tickers_portafolio)
                ]
                # SIEMPRE aplicar el filtro, incluso si deja la tabla vacía
                # (es mejor mostrar vacía que mostrar datos incorrectos)
                metricas_filtradas = candidatas
                if len(candidatas) == 0:
                    print(f"   ⚠️  Advertencia: No se encontraron pares con correlación negativa en el portafolio 'Correlación Negativa'")
                    print(f"      Total de pares calculados: {len(metricas_pares_activos)}")
                    print(f"      Activos del portafolio: {len(tickers_portafolio)}")
                    print(f"      Esto puede indicar que el portafolio no tiene suficientes pares con correlación negativa")
                else:
                    print(f"   ✅ Filtrado aplicado: {len(candidatas)} pares con correlación negativa de {len(metricas_pares_activos)} pares totales")
                    # Verificación final: mostrar que todos los activos en los pares están en el portafolio
                    activos_en_pares = set()
                    for par in candidatas:
                        activos_en_pares.add(par.get("activo1"))
                        activos_en_pares.add(par.get("activo2"))
                    activos_fuera = activos_en_pares - set(tickers_portafolio)
                    if activos_fuera:
                        print(f"      ⚠️  ERROR: Hay activos en los pares que no están en el portafolio: {activos_fuera}")
                    else:
                        print(f"      ✅ Verificación: Todos los activos en los pares están en el portafolio ({len(activos_en_pares)} activos únicos)")
            
            metricas_pares_activos = metricas_filtradas
        
        # Calcular matriz de correlación general para compatibilidad (usando todos los activos del portafolio)
        tickers_disponibles_en_returns = [t for t in tickers_portafolio if t in returns_subset.columns]
        if tickers_disponibles_en_returns:
            returns_para_corr = returns_subset[tickers_disponibles_en_returns]
            corr_matrix = returns_para_corr.corr().round(6).to_dict()
        else:
            corr_matrix = {}
        
        # Métricas individuales de activos con sectores
        # (sectores_tickers ya fue definido arriba, antes de calcular_asignacion)
        annual_trading_days = 252
        metricas_activos = []
        for ticker in resumen.tickers:
            sector = sectores_tickers.get(ticker, "Desconocido")
            if ticker in returns_subset.columns:
                serie = returns_subset[ticker].dropna()
                if len(serie) >= 20:
                    mean_daily = float(serie.mean())
                    std_daily = float(serie.std())
                    mean_annual = mean_daily * annual_trading_days
                    vol_annual = std_daily * (annual_trading_days ** 0.5)
                    sharpe_individual = (mean_annual - risk_free_rate) / vol_annual if vol_annual > 0 else 0
                    # Calcular sesgo (skewness)
                    skewness_valor = float(skew(serie)) if len(serie) > 2 else 0.0
                    
                    metricas_activos.append({
                        "ticker": ticker,
                        "sector": sector,
                        "retorno_anual": float(mean_annual),
                        "volatilidad_anual": float(vol_annual),
                        "sharpe_ratio": float(sharpe_individual),
                        "skewness": float(skewness_valor),
                    })
        
        # Calcular monto total real para composicion_global (1 unidad de cada activo)
        monto_total_real_global = 0.0
        for ticker in resumen.tickers:
            precio_actual = precios_actuales.get(ticker, 0)
            if precio_actual > 0:
                monto_total_real_global += precio_actual
        
        # Calcular distribución de retornos del portafolio para percentiles
        def calcular_percentiles_portafolio(pesos_dict, tipo="composicion_global", monto_usar=None):
            """
            Calcula percentiles basados en la distribución empírica real de retornos del portafolio.
            También calcula escenarios basados en percentiles reales y probabilidades de pérdidas/ganancias.
            """
            # Usar monto_usar si se proporciona, sino usar monto_inversion_local
            monto_calculo = monto_usar if monto_usar is not None else monto_inversion_local
            
            # Calcular retornos diarios del portafolio con los pesos dados
            port_returns_daily = None
            for ticker, peso in pesos_dict.items():
                if ticker in returns_subset.columns and peso > 0:
                    serie = returns_subset[ticker].dropna() * peso
                    if port_returns_daily is None:
                        port_returns_daily = serie
                    else:
                        port_returns_daily = port_returns_daily.add(serie, fill_value=0)
            
            # Usar SIEMPRE distribución empírica basada en los datos reales
            port_returns_clean = port_returns_daily.dropna() if port_returns_daily is not None else pd.Series()
            
            if len(port_returns_clean) > 0:
                # CORRECCIÓN: Calcular retornos anuales acumulados correctamente usando ventanas móviles
                # En lugar de multiplicar retornos diarios por 252 (incorrecto), calculamos retornos anuales
                # usando capitalización compuesta sobre ventanas de 252 días
                annual_trading_days = 252
                port_returns_annual = []
                
                # Si tenemos suficientes datos, calcular retornos anuales usando ventanas móviles
                if len(port_returns_clean) >= annual_trading_days:
                    # Calcular retornos anuales acumulados usando ventanas de 252 días
                    for i in range(len(port_returns_clean) - annual_trading_days + 1):
                        window_returns = port_returns_clean.iloc[i:i+annual_trading_days]
                        # Retorno anual acumulado: (1 + r1) * (1 + r2) * ... * (1 + r252) - 1
                        annual_return = (1 + window_returns).prod() - 1
                        port_returns_annual.append(annual_return)
                    port_returns_annual = pd.Series(port_returns_annual)
                else:
                    # Si no hay suficientes datos, usar aproximación basada en estadísticas
                    # Calcular media y volatilidad anualizadas correctamente
                    mean_daily = port_returns_clean.mean()
                    std_daily = port_returns_clean.std()
                    mean_annual = mean_daily * annual_trading_days
                    vol_annual = std_daily * np.sqrt(annual_trading_days)
                    
                    # Para percentiles, usar aproximación basada en distribución normal
                    # pero solo si tenemos al menos algunos datos
                    if len(port_returns_clean) >= 20:
                        # Usar los retornos diarios existentes y proyectarlos a anuales
                        # usando bootstrapping: muestrear bloques de días y calcular retornos anuales
                        np.random.seed(42)  # Para reproducibilidad
                        num_simulations = min(500, len(port_returns_clean) * 5)
                        simulated_annual_returns = []
                        for _ in range(num_simulations):
                            # Muestrear días aleatoriamente con reemplazo
                            sampled_days = np.random.choice(len(port_returns_clean), size=annual_trading_days, replace=True)
                            sampled_returns = port_returns_clean.iloc[sampled_days]
                            # Calcular retorno anual acumulado
                            annual_return = (1 + sampled_returns).prod() - 1
                            simulated_annual_returns.append(annual_return)
                        port_returns_annual = pd.Series(simulated_annual_returns)
                    else:
                        # Si hay muy pocos datos, usar aproximación simple pero correcta
                        # Calcular retorno acumulado de los datos disponibles y escalar
                        total_return = (1 + port_returns_clean).prod() - 1
                        # Escalar a anual (aproximación)
                        days_available = len(port_returns_clean)
                        if days_available > 0:
                            annual_return_approx = (1 + total_return) ** (annual_trading_days / days_available) - 1
                            # Crear distribución alrededor de este valor
                            port_returns_annual = pd.Series([annual_return_approx] * max(100, days_available))
                        else:
                            port_returns_annual = pd.Series([mean_annual] * 100)
                
                # Calcular la MODA (intervalo modal del histograma - el pico de la distribución)
                # En datos financieros casi nunca hay valores repetidos exactos, así que usamos el intervalo con mayor frecuencia
                moda_retorno = None
                moda_intervalo = None
                moda_frecuencia = 0
                try:
                    # Crear histograma para encontrar el intervalo modal
                    # Usar regla de Sturges para determinar número de bins: k = 1 + log2(n)
                    n = len(port_returns_annual)
                    if n > 0:
                        num_bins = max(10, int(1 + np.log2(n)))  # Mínimo 10 bins para buena resolución
                        counts, bin_edges = np.histogram(port_returns_annual, bins=num_bins)
                        
                        # Encontrar el bin con mayor frecuencia (el pico)
                        indice_max = np.argmax(counts)
                        moda_frecuencia = int(counts[indice_max])
                        
                        # El intervalo modal es el centro del bin con mayor frecuencia
                        moda_retorno = float((bin_edges[indice_max] + bin_edges[indice_max + 1]) / 2)
                        moda_intervalo = (float(bin_edges[indice_max]), float(bin_edges[indice_max + 1]))
                except Exception as e:
                    print(f"   ⚠️  Error calculando moda: {e}")
                    moda_retorno = None
                    moda_intervalo = None
                    moda_frecuencia = 0
                
                # Calcular percentiles de retornos anuales basados ÚNICAMENTE en la distribución empírica real
                # Solo percentiles estándar, sin mezclar con aproximaciones de sigma
                percentiles_retornos = {}
                percentiles_valores = {}
                percentiles_pnl = {}
                
                # Percentiles estándar para la tabla única
                for p in [5, 10, 25, 40, 50, 60, 75, 90, 95]:
                    retorno_percentil = float(np.percentile(port_returns_annual, p))
                    # CORRECCIÓN: El retorno_percentil ya es un retorno anual acumulado correcto
                    # Usar capitalización compuesta: valor_final = capital * (1 + retorno_anual)
                    valor_final = monto_calculo * (1 + retorno_percentil)
                    percentiles_retornos[p] = retorno_percentil
                    percentiles_valores[p] = float(valor_final)
                    percentiles_pnl[p] = float(valor_final - monto_calculo)
                
                # Calcular el rango más probable (P40 a P60) - donde suele estar el pico de probabilidad
                rango_mas_probable = None
                if 40 in percentiles_retornos and 60 in percentiles_retornos:
                    pnl_p40 = percentiles_pnl[40]
                    pnl_p60 = percentiles_pnl[60]
                    retorno_p40 = percentiles_retornos[40]
                    retorno_p60 = percentiles_retornos[60]
                    rango_mas_probable = {
                        "pnl_min": float(pnl_p40),
                        "pnl_max": float(pnl_p60),
                        "retorno_min": float(retorno_p40),
                        "retorno_max": float(retorno_p60),
                        "valor_final_min": float(percentiles_valores[40]),
                        "valor_final_max": float(percentiles_valores[60])
                    }
                
                # Agregar la moda como un "percentil" especial (usando clave "moda")
                if moda_retorno is not None:
                    # CORRECCIÓN: El moda_retorno ya es un retorno anual acumulado correcto
                    valor_final_moda = monto_calculo * (1 + moda_retorno)
                    percentiles_retornos["moda"] = moda_retorno
                    percentiles_valores["moda"] = float(valor_final_moda)
                    percentiles_pnl["moda"] = float(valor_final_moda - monto_calculo)
                
                # Calcular probabilidades basadas en la distribución empírica real
                n_total = len(port_returns_annual)
                
                if n_total > 0:
                    # Probabilidades básicas
                    prob_perdida = (len(port_returns_annual[port_returns_annual < 0]) / n_total) * 100
                    prob_ganancia = (len(port_returns_annual[port_returns_annual > 0]) / n_total) * 100
                    prob_neutro = (len(port_returns_annual[port_returns_annual == 0]) / n_total) * 100
                    
                    # Probabilidades por rangos de pérdidas (basadas en distribución empírica)
                    prob_perdida_50 = (len(port_returns_annual[port_returns_annual < -0.50]) / n_total) * 100
                    prob_perdida_30 = (len(port_returns_annual[(port_returns_annual < -0.30) & (port_returns_annual >= -0.50)]) / n_total) * 100
                    prob_perdida_20 = (len(port_returns_annual[(port_returns_annual < -0.20) & (port_returns_annual >= -0.30)]) / n_total) * 100
                    prob_perdida_10 = (len(port_returns_annual[(port_returns_annual < -0.10) & (port_returns_annual >= -0.20)]) / n_total) * 100
                    prob_perdida_5 = (len(port_returns_annual[(port_returns_annual < -0.05) & (port_returns_annual >= -0.10)]) / n_total) * 100
                    prob_perdida_menor_5 = (len(port_returns_annual[(port_returns_annual < 0) & (port_returns_annual >= -0.05)]) / n_total) * 100
                    
                    # Probabilidades por rangos de ganancias (basadas en distribución empírica)
                    prob_ganancia_menor_5 = (len(port_returns_annual[(port_returns_annual > 0) & (port_returns_annual <= 0.05)]) / n_total) * 100
                    prob_ganancia_5 = (len(port_returns_annual[(port_returns_annual > 0.05) & (port_returns_annual <= 0.10)]) / n_total) * 100
                    prob_ganancia_10 = (len(port_returns_annual[(port_returns_annual > 0.10) & (port_returns_annual <= 0.20)]) / n_total) * 100
                    prob_ganancia_20 = (len(port_returns_annual[(port_returns_annual > 0.20) & (port_returns_annual <= 0.30)]) / n_total) * 100
                    prob_ganancia_30 = (len(port_returns_annual[(port_returns_annual > 0.30) & (port_returns_annual <= 0.50)]) / n_total) * 100
                    prob_ganancia_50 = (len(port_returns_annual[port_returns_annual > 0.50]) / n_total) * 100
                    
                    # Calcular probabilidades basadas en los MISMOS percentiles calculados
                    # Usar los valores de los percentiles para calcular probabilidades acumuladas
                    prob_perdida_p5 = (len(port_returns_annual[port_returns_annual <= percentiles_retornos[5]]) / n_total) * 100
                    prob_perdida_p10 = (len(port_returns_annual[port_returns_annual <= percentiles_retornos[10]]) / n_total) * 100
                    prob_perdida_p25 = (len(port_returns_annual[port_returns_annual <= percentiles_retornos[25]]) / n_total) * 100
                    prob_ganancia_p75 = (len(port_returns_annual[port_returns_annual > percentiles_retornos[75]]) / n_total) * 100
                    prob_ganancia_p90 = (len(port_returns_annual[port_returns_annual > percentiles_retornos[90]]) / n_total) * 100
                    prob_ganancia_p95 = (len(port_returns_annual[port_returns_annual > percentiles_retornos[95]]) / n_total) * 100
                    
                    probabilidades = {
                        # Básicas (basadas en distribución empírica)
                        "prob_perdida": float(prob_perdida),
                        "prob_ganancia": float(prob_ganancia),
                        "prob_neutro": float(prob_neutro),
                        # Probabilidades basadas en los percentiles calculados
                        "prob_perdida_p5": float(prob_perdida_p5),
                        "prob_perdida_p10": float(prob_perdida_p10),
                        "prob_perdida_p25": float(prob_perdida_p25),
                        "prob_ganancia_p75": float(prob_ganancia_p75),
                        "prob_ganancia_p90": float(prob_ganancia_p90),
                        "prob_ganancia_p95": float(prob_ganancia_p95),
                        # Para compatibilidad con código existente
                        "prob_perdida_10pct": float(prob_perdida_p10),
                        "prob_perdida_20pct": float(prob_perdida_p25),
                        "prob_ganancia_10pct": float(prob_ganancia_p75),
                        "prob_ganancia_20pct": float(prob_ganancia_p90),
                        "prob_ganancia_50pct": float(prob_ganancia_p95)
                    }
                else:
                    probabilidades = {}
            else:
                probabilidades = {}
            
            # Construir diccionario de percentiles incluyendo la moda
            percentiles_dict = {
                p: {
                    "probabilidad": p,
                    "retorno": percentiles_retornos.get(p, 0.0),
                    "valor_final": percentiles_valores.get(p, 0.0),
                    "pnl": percentiles_pnl.get(p, 0.0),
                }
                for p in [5, 10, 25, 40, 50, 60, 75, 90, 95]
            }
            
            # Agregar la moda si está disponible
            if "moda" in percentiles_retornos:
                percentiles_dict["moda"] = {
                    "probabilidad": "moda",
                    "retorno": percentiles_retornos["moda"],
                    "valor_final": percentiles_valores["moda"],
                    "pnl": percentiles_pnl["moda"],
                    "intervalo": moda_intervalo,
                    "frecuencia": moda_frecuencia,
                }
            
            return {
                "percentiles": percentiles_dict,
                "probabilidades": probabilidades,
                "rango_mas_probable": rango_mas_probable  # Rango P40-P60 donde suele estar el pico
            }
        
        # Calcular métricas de Monte Carlo para cada tipo de portafolio
        def calcular_metricas_montecarlo(pesos_dict, tipo="composicion_global", monto_usar=None):
            """Calcula métricas de simulación Monte Carlo para el portafolio"""
            monto_calculo = monto_usar if monto_usar is not None else monto_inversion_local
            
            # Crear PortfolioSummary temporal para la simulación
            tickers_validos = [t for t in pesos_dict.keys() if t in returns_subset.columns and pesos_dict[t] > 0.0001]
            if not tickers_validos:
                return {}
            
            # Normalizar pesos
            total_peso = sum(pesos_dict.get(t, 0) for t in tickers_validos)
            if total_peso == 0:
                return {}
            
            pesos_normalizados = {t: pesos_dict.get(t, 0) / total_peso for t in tickers_validos}
            
            # Calcular retornos históricos del portafolio
            returns_portfolio = None
            for ticker, peso in pesos_normalizados.items():
                if ticker in returns_subset.columns:
                    serie = returns_subset[ticker].dropna() * peso
                    if returns_portfolio is None:
                        returns_portfolio = serie
                    else:
                        returns_portfolio = returns_portfolio.add(serie, fill_value=0)
            
            if returns_portfolio is None or len(returns_portfolio.dropna()) < 20:
                return {}
            
            # Calcular métricas anuales del portafolio
            returns_clean = returns_portfolio.dropna()
            mean_daily = float(returns_clean.mean())
            std_daily = float(returns_clean.std())
            mean_annual = mean_daily * 252
            vol_annual = std_daily * (252 ** 0.5)
            sharpe_temp = (mean_annual - risk_free_rate) / vol_annual if vol_annual > 0 else 0
            
            # Crear PortfolioSummary temporal
            summary_temp = PortfolioSummary(
                nombre=f"Temp {tipo}",
                tickers=tickers_validos,
                returns_df=returns_subset[tickers_validos] if not returns_subset.empty else pd.DataFrame(),
                mean_return_annual=mean_annual,
                volatility_annual=vol_annual,
                sharpe_ratio=sharpe_temp,
                weights=pesos_normalizados
            )
            
            # Calcular métricas de Monte Carlo usando pesos FIJOS (optimizados) + trayectorias simuladas
            try:
                # CORRECCIÓN: Usar pesos FIJOS (ya optimizados) y solo simular trayectorias
                # Esto hace que los portafolios sean comparables y coherentes
                # No volver a simular pesos distintos, solo simular trayectorias con los pesos optimizados
                metricas_mc = obtener_metricas_ganancia_real(
                    summary_temp, 
                    capital=monto_calculo, 
                    n=5000, 
                    metodo='empirico',
                    returns_df=returns_subset,
                    usar_combinado=False  # Usar pesos FIJOS (optimizados), solo simular trayectorias
                )
                return {
                    "ganancia_media": float(metricas_mc.get('ganancia_media', 0)),
                    "ganancia_mediana": float(metricas_mc.get('ganancia_mediana', 0)),
                    "ganancia_moda": float(metricas_mc.get('ganancia_moda', 0)),
                    "ganancia_std": float(metricas_mc.get('ganancia_std', 0)),
                    "percentil_5": float(metricas_mc.get('percentil_5', 0)),  # Pérdida en escenario pesimista
                    "percentil_25": float(metricas_mc.get('percentil_25', 0)),  # Pérdida en escenario probable
                    "percentil_75": float(metricas_mc.get('percentil_75', 0)),  # Ganancia en escenario probable
                    "percentil_95": float(metricas_mc.get('percentil_95', 0)),  # Ganancia en escenario optimista
                    "var_5": float(metricas_mc.get('var_5', 0)),  # Value at Risk
                    "cvar_5": float(metricas_mc.get('cvar_5', 0)),  # Conditional VaR
                    "prob_ganar": float(metricas_mc.get('prob_ganar', 0)),
                    "prob_perder": float(metricas_mc.get('prob_perder', 0)),
                }
            except Exception as e:
                print(f"   ⚠️  Error calculando métricas Monte Carlo para {tipo}: {e}")
                return {}
        
        # Calcular percentiles para cada tipo de portafolio
        # Para composicion_global, usar el monto total real (1 unidad de cada activo)
        # (pesos_global_calculo ya está definido arriba)
        percentiles_global = calcular_percentiles_portafolio(pesos_global_calculo, "composicion_global", monto_total_real_global)
        percentiles_ms = calcular_percentiles_portafolio(pesos_ms, "maximo_sharpe", monto_inversion_local)
        percentiles_mv = calcular_percentiles_portafolio(pesos_mv, "minima_volatilidad", monto_inversion_local)
        
        # Calcular métricas de Monte Carlo para cada tipo
        metricas_mc_global = calcular_metricas_montecarlo(pesos_global_calculo, "composicion_global", monto_total_real_global)
        metricas_mc_ms = calcular_metricas_montecarlo(pesos_ms, "maximo_sharpe", monto_inversion_local)
        metricas_mc_mv = calcular_metricas_montecarlo(pesos_mv, "minima_volatilidad", monto_inversion_local)
        
        # Calcular asignaciones para cada tipo de portafolio
        # Para composicion_global, usar pesos iguales porcentuales para cálculos de retornos
        # pero la asignación real será 1 unidad de cada activo
        asignacion_global = calcular_asignacion(pesos_global_calculo, "composicion_global")
        asignacion_ms = calcular_asignacion(pesos_ms, "maximo_sharpe")
        asignacion_mv = calcular_asignacion(pesos_mv, "minima_volatilidad")
        
        # Calcular pesos reales basados en 1 unidad de cada activo
        # (los pesos reales se calculan desde la asignación)
        monto_total_real = sum(item["asignacion_dinero"] for item in asignacion_global)
        pesos_global_reales = {}
        for item in asignacion_global:
            if monto_total_real > 0:
                pesos_global_reales[item["ticker"]] = item["asignacion_dinero"] / monto_total_real
            else:
                pesos_global_reales[item["ticker"]] = 0.0
        
        return {
            "nombre": resumen.nombre,
            "tickers": resumen.tickers,
            "n_activos": len(resumen.tickers),  # Cantidad de activos en el portafolio
            "skewness": float(resumen.skewness) if hasattr(resumen, 'skewness') else 0.0,
            "kurtosis": float(resumen.kurtosis) if hasattr(resumen, 'kurtosis') else 0.0,
            "composicion_global": {
                "retorno_anual": retorno_anual,
                "volatilidad_anual": volatilidad_anual,
                "sharpe_ratio": sharpe,
                "pesos": pesos_global_reales,
                "asignacion": asignacion_global,
                "ganancia_esperada": float(retorno_anual * monto_total_real),
                "percentiles": percentiles_global["percentiles"],
                "probabilidades": percentiles_global["probabilidades"],
                "metricas_montecarlo": metricas_mc_global,  # Métricas de simulación Monte Carlo
                "metricas_pares_activos": metricas_pares_global,  # Métricas específicas de esta optimización
            },
            "maximo_sharpe": {
                "retorno_anual": ret_ms,
                "volatilidad_anual": vol_ms,
                "sharpe_ratio": sharpe_ms,
                "pesos": pesos_ms,
                "asignacion": asignacion_ms,
                "ganancia_esperada": float(ret_ms * monto_inversion_local),
                "percentiles": percentiles_ms["percentiles"],
                "probabilidades": percentiles_ms["probabilidades"],
                "metricas_montecarlo": metricas_mc_ms,  # Métricas de simulación Monte Carlo
                "metricas_pares_activos": metricas_pares_ms,  # Métricas específicas de esta optimización
            },
            "minima_volatilidad": {
                "retorno_anual": ret_mv,
                "volatilidad_anual": vol_mv,
                "sharpe_ratio": sharpe_mv,
                "pesos": pesos_mv,
                "asignacion": asignacion_mv,
                "ganancia_esperada": float(ret_mv * monto_inversion_local),
                "percentiles": percentiles_mv["percentiles"],
                "probabilidades": percentiles_mv["probabilidades"],
                "metricas_montecarlo": metricas_mc_mv,  # Métricas de simulación Monte Carlo
                "metricas_pares_activos": metricas_pares_mv,  # Métricas específicas de esta optimización
            },
            "matriz_correlacion": corr_matrix,
            "metricas_activos": metricas_activos,
            "metricas_pares_activos": metricas_pares_activos,  # Correlaciones, R², beta, alpha entre pares (legacy, usar las específicas)
            "frontera_eficiente": frontera_eficiente,  # Datos de Monte Carlo para gráfico
        }
    
    # Preparar datos de los tres portafolios
    datos_spy_qqq = preparar_datos_portafolio(
        resumen_spy_qqq,
        pf_spy_qqq_df,
        pf_spy_qqq_ms,
        pf_spy_qqq_mv,
        returns[resumen_spy_qqq.tickers],
    )
    
    datos_alta_corr = preparar_datos_portafolio(
        resumen_high,
        pf_high_df,
        pf_high_ms,
        pf_high_mv,
        returns[resumen_high.tickers],
    )
    
    datos_baja_corr = preparar_datos_portafolio(
        resumen_low,
        pf_low_df,
        pf_low_ms,
        pf_low_mv,
        returns[resumen_low.tickers],
    )
    
    # Preparar datos de las versiones extendidas (10 activos)
    datos_alta_corr_ext = None
    if resumen_high_ext is not None:
        datos_alta_corr_ext = preparar_datos_portafolio(
            resumen_high_ext,
            pf_high_ext_df,
            pf_high_ext_ms,
            pf_high_ext_mv,
            returns[resumen_high_ext.tickers],
        )
    
    datos_baja_corr_ext = None
    if resumen_low_ext is not None:
        datos_baja_corr_ext = preparar_datos_portafolio(
            resumen_low_ext,
            pf_low_ext_df,
            pf_low_ext_ms,
            pf_low_ext_mv,
            returns[resumen_low_ext.tickers],
        )
    
    datos_skew = preparar_datos_portafolio(
        resumen_skew,
        pf_skew_df,
        pf_skew_ms,
        pf_skew_mv,
        returns[resumen_skew.tickers],
    )
    
    datos_neg = preparar_datos_portafolio(
        resumen_neg,
        pf_neg_df,
        pf_neg_ms,
        pf_neg_mv,
        returns[resumen_neg.tickers],
    )
    
    # Preparar datos BCBA (si existen)
    datos_bcba = None
    if resumen_bcba is not None:
        datos_bcba = preparar_datos_portafolio(
            resumen_bcba,
            pf_bcba_df,
            pf_bcba_ms,
            pf_bcba_mv,
            returns[resumen_bcba.tickers],
        )
    
    # Preparar métricas SPY vs QQQ
    metricas_spy_qqq_serializable = {}
    for key, m in metricas_spy_qqq.items():
        if m:
            metricas_spy_qqq_serializable[key] = {
                "correlacion": float(m.get("correlacion", 0)),
                "beta": float(m.get("beta", 0)),
                "alpha_anual": float(m.get("alpha_anual", 0)),
                "r_squared": float(m.get("r_squared", 0)),
            }
    
    # Crear estructura de datos completa
    # Filtrar portafolios None antes de agregarlos
    portafolios_dict = {}
    if datos_spy_qqq:
        portafolios_dict["spy_qqq"] = datos_spy_qqq
    if datos_alta_corr:
        portafolios_dict["alta_correlacion"] = datos_alta_corr
    if datos_baja_corr:
        portafolios_dict["baja_correlacion"] = datos_baja_corr
    if datos_skew:
        portafolios_dict["alta_volatilidad_sesgo_positivo"] = datos_skew
    if datos_neg:
        portafolios_dict["correlacion_negativa"] = datos_neg
    if datos_alta_corr_ext:
        portafolios_dict["alta_correlacion_ext"] = datos_alta_corr_ext
    if datos_baja_corr_ext:
        portafolios_dict["baja_correlacion_ext"] = datos_baja_corr_ext
    if datos_bcba:
        portafolios_dict["bcba"] = datos_bcba
    
    datos_completos = {
        "fecha_generacion": datetime.now().isoformat(),
        "monto_inversion": float(monto_inversion),
        "risk_free_rate": 0.08,  # 8% en USD
        "metricas_spy_qqq": metricas_spy_qqq_serializable,
        "portafolios": portafolios_dict,
    }
    
    # Debug: verificar que los datos se están generando correctamente
    print(f"\n   📊 Verificando datos generados:")
    print(f"      Portafolios en datos_completos: {list(datos_completos['portafolios'].keys())}")
    for key, portfolio in datos_completos['portafolios'].items():
        if portfolio:
            has_global = portfolio.get('composicion_global') is not None
            has_sharpe = portfolio.get('maximo_sharpe') is not None
            has_vol = portfolio.get('minima_volatilidad') is not None
            print(f"      {key}: composicion_global={has_global}, maximo_sharpe={has_sharpe}, minima_volatilidad={has_vol}")
        else:
            print(f"      {key}: NULL")
    
    # Generar el HTML completo con carruseles y funcionalidad de descarga
    # El HTML será generado con los datos de optimizaciones embebidos
    html_template = _generar_html_completo_con_carruseles()
    
    # Reemplazar el placeholder con los datos JSON
    # Escapar correctamente para JavaScript
    datos_json_str = json.dumps(datos_completos, indent=2, ensure_ascii=False)
    # Reemplazar el placeholder
    html_final = html_template.replace("{datos_json}", datos_json_str)
    
    # Guardar el HTML
    output_path = Path("optimizaciones_portafolios.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_final)
    
    print(f"   ✅ HTML guardado en: {output_path}")
    print(f"   📊 El HTML incluye optimizaciones de {len(datos_completos['portafolios'])} portafolios")
    print(f"   💰 Monto de inversión: ${monto_inversion:,.0f}")


if __name__ == "__main__":
    main()