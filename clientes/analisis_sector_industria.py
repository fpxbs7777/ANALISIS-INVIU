import yfinance as yf
import pandas as pd
import numpy as np
import scipy.stats as st
from datetime import datetime, timedelta
import time
import warnings
import glob
import os
import json
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import partial
import signal

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN DE CACHE
# ============================================================================

CACHE_DIR = 'cache'
SECTORES_CACHE_FILE = os.path.join(CACHE_DIR, 'sectores_industrias_cache.pkl')
SERIES_CACHE_FILE = os.path.join(CACHE_DIR, 'series_historicas_cache.pkl')
BATCH_SIZE = 10  # Tamaño del lote para procesamiento (reducido para evitar bloqueos)
TEST_MODE = True  # Modo prueba: solo procesa primeros 10 tickers
TEST_TICKERS_COUNT = 10  # Cantidad de tickers en modo prueba
MAX_WORKERS = 5  # Máximo de workers paralelos (reducido para evitar bloqueos)
TIMEOUT_SECONDS = 10  # Timeout para cada petición yfinance

# Crear directorio de cache si no existe
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================================
# SISTEMA DE CACHE
# ============================================================================

def load_cache(cache_file):
    """Carga cache desde archivo"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"  ⚠ Error cargando cache: {e}")
            return {}
    return {}

def save_cache(cache_file, data):
    """Guarda cache en archivo"""
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        print(f"  ⚠ Error guardando cache: {e}")
        return False

def obtener_info_ticker_single(ticker):
    """
    Obtiene información de un solo ticker (para procesamiento paralelo) con timeout
    """
    def _get_info():
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        sector = info.get('sector', 'No disponible')
        industria = info.get('industry', 'No disponible')
        
        data = {
            'ticker': ticker,
            'sector': sector,
            'industria': industria,
            'timestamp': datetime.now()
        }
        
        if sector not in ['Error', 'No disponible']:
            return data, None
        else:
            return None, 'No disponible'
    
    try:
        # Ejecutar con timeout usando ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_get_info)
            return future.result(timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        return None, 'timeout'
    except Exception as e:
        return None, str(e)

def obtener_info_ticker_batch(tickers):
    """
    Obtiene información de sector e industria en lotes con procesamiento paralelo
    """
    print(f"📂 Obteniendo sector e industria para {len(tickers)} tickers en lotes de {BATCH_SIZE}...", flush=True)
    sys.stdout.flush()
    
    # Cargar cache existente
    cache = load_cache(SECTORES_CACHE_FILE)
    print(f"  ✓ Cache cargado", flush=True)
    
    resultados = []
    tickers_a_descargar = []
    
    # Separar tickers que ya están en cache
    for ticker in tickers:
        if ticker in cache and cache[ticker].get('sector') not in ['Error', 'No disponible']:
            resultados.append(cache[ticker])
        else:
            tickers_a_descargar.append(ticker)
    
    print(f"  ✓ {len(resultados)} tickers en cache", flush=True)
    print(f"  📥 {len(tickers_a_descargar)} tickers a descargar...", flush=True)
    
    if not tickers_a_descargar:
        print(f"✓ Completado: {len(resultados)} tickers procesados", flush=True)
        return resultados
    
    # Procesar en lotes con paralelismo
    for i in range(0, len(tickers_a_descargar), BATCH_SIZE):
        batch = tickers_a_descargar[i:i+BATCH_SIZE]
        print(f"  Procesando lote {i//BATCH_SIZE + 1}/{(len(tickers_a_descargar)-1)//BATCH_SIZE + 1} ({len(batch)} tickers) en paralelo...", flush=True)
        
        # Usar ThreadPoolExecutor para procesamiento paralelo (con workers limitados)
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batch))) as executor:
            futures = {executor.submit(obtener_info_ticker_single, ticker): ticker for ticker in batch}
            
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    data, error = future.result()
                    if data:
                        resultados.append(data)
                        cache[ticker] = data
                        print(f"    ✓ {ticker}: {data['sector'][:20]}", flush=True)
                    else:
                        cache[ticker] = {
                            'ticker': ticker,
                            'sector': 'Error',
                            'industria': error,
                            'timestamp': datetime.now()
                        }
                        print(f"    ✗ {ticker}: {error[:20]}", flush=True)
                except Exception as e:
                    cache[ticker] = {
                        'ticker': ticker,
                        'sector': 'Error',
                        'industria': str(e),
                        'timestamp': datetime.now()
                    }
                    print(f"    ✗ {ticker}: Error en ejecución", flush=True)
        
        # Guardar cache después de cada lote
        print(f"  Guardando cache del lote...", flush=True)
        save_cache(SECTORES_CACHE_FILE, cache)
    
    print(f"✓ Completado: {len(resultados)} tickers procesados", flush=True)
    return resultados

def load_timeseries_yf_cached(ticker, period='5y', timeout=30):
    """
    Carga serie temporal desde yfinance con cache incremental
    """
    # Cargar cache de series
    cache = load_cache(SERIES_CACHE_FILE)
    
    # Verificar si existe en cache
    if ticker in cache:
        cached_data = cache[ticker]
        last_date = cached_data.get('last_date')
        
        if last_date:
            last_date = pd.to_datetime(last_date)
            today = pd.Timestamp.now().normalize()
            
            # Si el cache es de hoy, usar cache
            if last_date >= today - timedelta(days=1):
                return cached_data['data']
            
            # Si el cache es antiguo, actualizar incrementalmente
            try:
                start_date = last_date + timedelta(days=1)
                new_data = yf.download(ticker, start=start_date, end=today, progress=False, timeout=timeout)
                
                if new_data is not None and len(new_data) > 0:
                    # Combinar datos antiguos con nuevos
                    old_df = cached_data['data']
                    
                    t = pd.DataFrame()
                    t['date'] = new_data.index
                    t['close'] = new_data['Close'].values
                    t = t.sort_values(by='date').reset_index(drop=True)
                    t['close_previous'] = t['close'].shift(1)
                    t['return_close'] = t['close'] / t['close_previous'] - 1
                    t = t.dropna().reset_index(drop=True)
                    
                    # Concatenar
                    combined = pd.concat([old_df, t], ignore_index=True)
                    combined = combined.drop_duplicates(subset=['date'], keep='last')
                    combined = combined.sort_values(by='date').reset_index(drop=True)
                    
                    # Actualizar cache
                    cache[ticker] = {
                        'data': combined,
                        'last_date': combined['date'].iloc[-1],
                        'timestamp': datetime.now()
                    }
                    save_cache(SERIES_CACHE_FILE, cache)
                    
                    return combined
            except Exception:
                return cached_data['data']
    
    # Si no está en cache o falló actualización, descargar completo
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True, timeout=timeout)
        
        if data is None or len(data) == 0:
            return pd.DataFrame()
        
        t = pd.DataFrame()
        t['date'] = data.index
        t['close'] = data['Close'].values
        t = t.sort_values(by='date').reset_index(drop=True)
        t['close_previous'] = t['close'].shift(1)
        t['return_close'] = t['close'] / t['close_previous'] - 1
        t = t.dropna().reset_index(drop=True)
        
        # Guardar en cache
        cache[ticker] = {
            'data': t,
            'last_date': t['date'].iloc[-1],
            'timestamp': datetime.now()
        }
        save_cache(SERIES_CACHE_FILE, cache)
        
        return t
    except Exception as e:
        return pd.DataFrame()

def load_timeseries_batch(tickers, period='5y', timeout=30):
    """
    Carga series temporales para múltiples tickers en una sola llamada (más rápido)
    """
    cache = load_cache(SERIES_CACHE_FILE)
    results = {}
    tickers_to_download = []
    
    # Verificar cache y separar tickers a descargar
    today = pd.Timestamp.now().normalize()
    for ticker in tickers:
        if ticker in cache:
            cached_data = cache[ticker]
            last_date = cached_data.get('last_date')
            if last_date:
                last_date = pd.to_datetime(last_date)
                if last_date >= today - timedelta(days=1):
                    results[ticker] = cached_data['data']
                    continue
        tickers_to_download.append(ticker)
    
    if not tickers_to_download:
        return results
    
    # Descargar en lote con yfinance
    try:
        data = yf.download(tickers_to_download, period=period, progress=False, auto_adjust=True, timeout=timeout, group_by='ticker')
        
        if data is not None:
            for ticker in tickers_to_download:
                try:
                    if len(tickers_to_download) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[ticker] if ticker in data.columns else None
                    
                    if ticker_data is not None and len(ticker_data) > 0:
                        t = pd.DataFrame()
                        t['date'] = ticker_data.index
                        t['close'] = ticker_data['Close'].values
                        t = t.sort_values(by='date').reset_index(drop=True)
                        t['close_previous'] = t['close'].shift(1)
                        t['return_close'] = t['close'] / t['close_previous'] - 1
                        t = t.dropna().reset_index(drop=True)
                        
                        cache[ticker] = {
                            'data': t,
                            'last_date': t['date'].iloc[-1],
                            'timestamp': datetime.now()
                        }
                        results[ticker] = t
                except Exception:
                    pass
        
        save_cache(SERIES_CACHE_FILE, cache)
    except Exception:
        # Si falla la descarga en lote, descargar individualmente
        for ticker in tickers_to_download:
            results[ticker] = load_timeseries_yf_cached(ticker, period, timeout)
    
    return results

# ============================================================================
# LISTA DE TICKERS (de obtener_sectores_industrias.py)
# ============================================================================

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

# ============================================================================
# CLASES Y FUNCIONES RECICLADAS DE MARKET_DATA.TXT Y CAPM.TXT
# ============================================================================

def synchronise_timeseries(ticker1, ticker2, period='5y'):
    """
    Sincroniza series temporales de dos tickers (de MARKET_DATA.txt) - usa cache
    """
    timeseries_x = load_timeseries_yf_cached(ticker1, period)
    timeseries_y = load_timeseries_yf_cached(ticker2, period)
    
    if timeseries_x.empty or timeseries_y.empty:
        return pd.DataFrame()
    
    # Obtener fechas comunes
    common_dates = pd.to_datetime(timeseries_x['date']).isin(pd.to_datetime(timeseries_y['date']))
    timeseries_x = timeseries_x[common_dates].sort_values(by='date').reset_index(drop=True)
    timeseries_y = timeseries_y[timeseries_y['date'].isin(timeseries_x['date'])].sort_values(by='date').reset_index(drop=True)
    
    timeseries = pd.DataFrame()
    timeseries['date'] = timeseries_x['date']
    timeseries['close_x'] = timeseries_x['close']
    timeseries['close_y'] = timeseries_y['close']
    timeseries['return_x'] = timeseries_x['return_close']
    timeseries['return_y'] = timeseries_y['return_close']
    
    return timeseries

def compute_correlation(ticker1, ticker2, period='5y'):
    """
    Calcula correlación entre dos tickers (de capm.txt)
    """
    timeseries = synchronise_timeseries(ticker1, ticker2, period)
    if timeseries.empty:
        return np.nan
    
    x = timeseries['return_x'].values
    y = timeseries['return_y'].values
    
    if len(x) == 0 or len(y) == 0:
        return np.nan
    
    correlation = np.corrcoef(x, y)[0, 1]
    return correlation

class AssetAnalyzer:
    """
    Clase para análisis de activos financieros (basada en Distribution de MARKET_DATA.txt)
    """
    def __init__(self, ticker, period='5y', decimals=5, factor=252):
        self.ticker = ticker
        self.period = period
        self.decimals = decimals
        self.factor = factor
        self.timeseries = None
        self.vector = None
        self.mean_annual = None
        self.volatility_annual = None
        self.sharpe_ratio = None
        self.var_95 = None
        self.skewness = None
        self.kurtosis = None
        self.current_price = None
        self.min_price = None
        self.max_price = None
        self.normalized_range = None
        self.pe_ratio = None
        self.market_cap = None
        
    def load_timeseries(self):
        """Carga serie temporal desde yfinance con cache"""
        self.timeseries = load_timeseries_yf_cached(self.ticker, self.period)
        if not self.timeseries.empty:
            self.vector = self.timeseries['return_close'].values
            self.current_price = self.timeseries['close'].iloc[-1]
            self.min_price = self.timeseries['close'].min()
            self.max_price = self.timeseries['close'].max()
            
            # Calcular recorrido normalizado (0 = en mínimo, 1 = en máximo)
            if self.max_price != self.min_price:
                self.normalized_range = (self.current_price - self.min_price) / (self.max_price - self.min_price)
            else:
                self.normalized_range = 0.5
    
    def load_fundamentals(self):
        """Carga datos fundamentales desde yfinance"""
        try:
            ticker_obj = yf.Ticker(self.ticker)
            info = ticker_obj.info
            
            # P/E ratio
            self.pe_ratio = info.get('trailingPE', np.nan)
            
            # Market cap
            self.market_cap = info.get('marketCap', np.nan)
            
        except Exception as e:
            self.pe_ratio = np.nan
            self.market_cap = np.nan
    
    def compute_stats(self):
        """Calcula estadísticas de riesgo"""
        if self.vector is None or len(self.vector) == 0:
            return
        
        self.mean_annual = np.mean(self.vector) * self.factor
        self.volatility_annual = np.std(self.vector) * np.sqrt(self.factor)
        self.sharpe_ratio = self.mean_annual / self.volatility_annual if self.volatility_annual > 0 else 0.0
        self.var_95 = np.percentile(self.vector, 5)
        self.skewness = st.skew(self.vector)
        self.kurtosis = st.kurtosis(self.vector)
    
    def get_summary(self):
        """Retorna resumen de métricas"""
        return {
            'ticker': self.ticker,
            'precio_actual': self.current_price,
            'precio_min_historico': self.min_price,
            'precio_max_historico': self.max_price,
            'recorrido_normalizado': self.normalized_range,
            'pe_ratio': self.pe_ratio,
            'market_cap': self.market_cap,
            'retorno_anualizado': self.mean_annual,
            'volatilidad_anualizada': self.volatility_annual,
            'sharpe_ratio': self.sharpe_ratio,
            'var_95': self.var_95,
            'skewness': self.skewness,
            'kurtosis': self.kurtosis
        }

# ============================================================================
# FUNCIONES DE ANÁLISIS POR SECTOR E INDUSTRIA
# ============================================================================

def cargar_datos_sectores_industrias(tickers=None):
    """
    Carga datos de sectores e industrias usando cache y lotes
    """
    if tickers is not None:
        # Usar procesamiento por lotes con cache
        resultados = obtener_info_ticker_batch(tickers)
        df = pd.DataFrame(resultados)
        print(f"✓ {len(df)} tickers con sector disponible")
        return df
    
    # Si no se pasan tickers, usar la lista global
    return cargar_datos_sectores_industrias(TICKERS)

def analizar_ticker(ticker, period='5y'):
    """
    Analiza un ticker individual
    """
    analyzer = AssetAnalyzer(ticker, period=period)
    analyzer.load_timeseries()
    analyzer.load_fundamentals()
    analyzer.compute_stats()
    return analyzer

def calcular_matriz_correlaciones(tickers, period='5y'):
    """
    Calcula matriz de correlaciones entre tickers del mismo sector/industria
    """
    n = len(tickers)
    if n < 2:
        return None
    
    matriz = pd.DataFrame(index=tickers, columns=tickers)
    
    for i, ticker1 in enumerate(tickers):
        for j, ticker2 in enumerate(tickers):
            if i == j:
                matriz.loc[ticker1, ticker2] = 1.0
            elif i < j:
                corr = compute_correlation(ticker1, ticker2, period)
                matriz.loc[ticker1, ticker2] = corr
                matriz.loc[ticker2, ticker1] = corr
    
    return matriz

def analizar_ticker_single(ticker, period='5y'):
    """
    Analiza un ticker individual (para procesamiento paralelo) con timeout
    """
    def _analyze():
        analyzer = AssetAnalyzer(ticker, period=period)
        analyzer.load_timeseries()
        analyzer.load_fundamentals()
        analyzer.compute_stats()
        
        if analyzer.timeseries is not None and not analyzer.timeseries.empty:
            return analyzer.get_summary(), None
        else:
            return None, 'sin datos'
    
    try:
        # Ejecutar con timeout usando ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_analyze)
            return future.result(timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        return None, 'timeout'
    except Exception as e:
        return None, str(e)

def analizar_grupo_sector_industria(df_sector, period='5y'):
    """
    Analiza un grupo de tickers del mismo sector/industria en lotes con paralelismo
    """
    tickers = df_sector['ticker'].tolist()
    resultados = []
    
    print(f"  Analizando {len(tickers)} tickers en lotes de {BATCH_SIZE} con paralelismo...")
    
    # Analizar en lotes con paralelismo
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        print(f"    Lote {i//BATCH_SIZE + 1}/{(len(tickers)-1)//BATCH_SIZE + 1} ({len(batch)} tickers)...")
        
        # Usar ThreadPoolExecutor para procesamiento paralelo (con workers limitados)
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batch))) as executor:
            futures = {executor.submit(analizar_ticker_single, ticker, period): ticker for ticker in batch}
            
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    summary, error = future.result()
                    if summary:
                        resultados.append(summary)
                        print(f"      ✓ {ticker}", flush=True)
                    else:
                        print(f"      ✗ {ticker}: {error[:20]}", flush=True)
                except Exception as e:
                    print(f"      ✗ {ticker}: Error en ejecución", flush=True)
    
    # Crear DataFrame con resultados
    if not resultados:
        print(f"  ⚠ No se obtuvieron resultados para este grupo")
        return pd.DataFrame()
    
    df_resultados = pd.DataFrame(resultados)
    
    # Calcular matriz de correlaciones usando pandas (más rápido)
    if 2 <= len(tickers) <= 10:
        print(f"  Calculando matriz de correlaciones ({len(tickers)}x{len(tickers)})...")
        try:
            # Descargar todas las series en lote
            series_dict = load_timeseries_batch(tickers, period)
            
            if series_dict and len(series_dict) >= 2:
                # Crear DataFrame con retornos
                returns_df = pd.DataFrame()
                for ticker, data in series_dict.items():
                    if not data.empty:
                        returns_df[ticker] = data['return_close'].values
                
                if not returns_df.empty and len(returns_df.columns) >= 2:
                    # Calcular matriz de correlaciones con pandas
                    matriz_corr = returns_df.corr()
                    
                    # Calcular correlación promedio para cada ticker
                    correlaciones_promedio = []
                    for ticker in tickers:
                        if ticker in matriz_corr.columns:
                            corrs = matriz_corr[ticker].drop(ticker, errors='ignore')
                            if len(corrs) > 0:
                                correlaciones_promedio.append(corrs.mean())
                            else:
                                correlaciones_promedio.append(np.nan)
                        else:
                            correlaciones_promedio.append(np.nan)
                    
                    if len(correlaciones_promedio) == len(df_resultados):
                        df_resultados['correlacion_promedio_sector'] = correlaciones_promedio
        except Exception as e:
            print(f"  ⚠ Error calculando correlaciones: {str(e)[:50]}")
    else:
        print(f"  ⚠ Omitiendo matriz de correlaciones (grupo muy grande: {len(tickers)})")
    
    return df_resultados

def generar_dataframe_completo(df_sectores, period='5y'):
    """
    Genera dataframe completo con análisis por sector e industria
    """
    print("="*70)
    print("ANALIZANDO ACTIVOS POR SECTOR E INDUSTRIA")
    print("="*70)
    
    resultados_completos = []
    
    # Agrupar por sector e industria
    agrupado = df_sectores.groupby(['sector', 'industria'])
    
    for (sector, industria), grupo in agrupado:
        print(f"\n📁 Sector: {sector}")
        print(f"🏭 Industria: {industria}")
        print(f"   Tickers: {', '.join(grupo['ticker'].tolist())}")
        
        # Analizar grupo
        df_grupo = analizar_grupo_sector_industria(grupo, period)
        
        if not df_grupo.empty:
            # Agregar información de sector e industria
            df_grupo['sector'] = sector
            df_grupo['industria'] = industria
            resultados_completos.append(df_grupo)
    
    # Concatenar todos los resultados
    if resultados_completos:
        df_final = pd.concat(resultados_completos, ignore_index=True)
        return df_final
    else:
        return pd.DataFrame()

def guardar_resultados(df, filename=None):
    """
    Guarda resultados en CSV
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analisis_sector_industria_{timestamp}.csv"
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n✓ Resultados guardados: {filename}")
    return filename

def mostrar_resumen(df):
    """
    Muestra resumen estadístico del análisis
    """
    print("\n" + "="*70)
    print("RESUMEN DEL ANÁLISIS")
    print("="*70)
    
    print(f"\n📊 Total de activos analizados: {len(df)}")
    print(f"📁 Sectores: {df['sector'].nunique()}")
    print(f"🏭 Industrias: {df['industria'].nunique()}")
    
    print("\n" + "-"*70)
    print("DISTRIBUCIÓN POR SECTOR:")
    print("-"*70)
    print(df['sector'].value_counts().to_string())
    
    print("\n" + "-"*70)
    print("MÉTRICAS PROMEDIO:")
    print("-"*70)
    
    metricas = ['retorno_anualizado', 'volatilidad_anualizada', 'sharpe_ratio', 
                 'var_95', 'recorrido_normalizado', 'pe_ratio']
    
    for metrica in metricas:
        if metrica in df.columns:
            valor_promedio = df[metrica].mean()
            valor_mediano = df[metrica].median()
            print(f"  {metrica:25s} - Promedio: {valor_promedio:8.4f} | Mediana: {valor_mediano:8.4f}")
    
    if 'correlacion_promedio_sector' in df.columns:
        print(f"\n  correlacion_promedio_sector - Promedio: {df['correlacion_promedio_sector'].mean():8.4f}")
    
    print("\n" + "-"*70)
    print("TOP 10 ACTIVOS POR SHARPE RATIO:")
    print("-"*70)
    top_sharpe = df.nlargest(10, 'sharpe_ratio')[['ticker', 'sector', 'industria', 'sharpe_ratio', 'retorno_anualizado', 'volatilidad_anualizada']]
    print(top_sharpe.to_string(index=False))
    
    print("\n" + "-"*70)
    print("TOP 10 ACTIVOS MÁS CERCANOS A MÁXIMO HISTÓRICO:")
    print("-"*70)
    top_max = df.nlargest(10, 'recorrido_normalizado')[['ticker', 'sector', 'industria', 'recorrido_normalizado', 'precio_actual', 'precio_max_historico']]
    print(top_max.to_string(index=False))
    
    print("\n" + "-"*70)
    print("TOP 10 ACTIVOS MÁS CERCANOS A MÍNIMO HISTÓRICO:")
    print("-"*70)
    top_min = df.nsmallest(10, 'recorrido_normalizado')[['ticker', 'sector', 'industria', 'recorrido_normalizado', 'precio_actual', 'precio_min_historico']]
    print(top_min.to_string(index=False))
    
    print("="*70)

def main():
    """
    Función principal
    """
    print("="*70)
    print("ANÁLISIS DE ACTIVOS POR SECTOR E INDUSTRIA")
    print("="*70)
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Modo prueba
    if TEST_MODE:
        print(f"⚠ MODO PRUEBA ACTIVADO: Procesando solo los primeros {TEST_TICKERS_COUNT} tickers")
        print(f"   Para procesar todos, cambia TEST_MODE = False en el script")
        print()
        tickers_a_procesar = TICKERS[:TEST_TICKERS_COUNT]
    else:
        tickers_a_procesar = TICKERS
    
    # Parámetros
    PERIODO = '5y'  # 5 años de datos históricos
    
    # Paso 1: Cargar datos de sectores e industrias desde yfinance
    print("📋 Usando lista de tickers definida en el script")
    print(f"   Total de tickers: {len(tickers_a_procesar)}")
    print()
    
    df_sectores = cargar_datos_sectores_industrias(tickers_a_procesar)
    
    if df_sectores is None or df_sectores.empty:
        print("❌ No se pudieron cargar los datos de sectores e industrias")
        return
    
    # Paso 2: Generar dataframe completo con análisis
    print("\n📊 Iniciando análisis de series históricas...")
    df_analisis = generar_dataframe_completo(df_sectores, period=PERIODO)
    
    if df_analisis.empty:
        print("❌ No se pudo generar el análisis")
        return
    
    # Paso 3: Guardar resultados
    filename = guardar_resultados(df_analisis)
    
    # Paso 4: Mostrar resumen
    mostrar_resumen(df_analisis)
    
    print("\n✅ Análisis completado exitosamente")
    print(f"📁 Archivo generado: {filename}")

if __name__ == "__main__":
    main()
