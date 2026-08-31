import numpy as np
import pandas as pd
import scipy.stats as st
import yfinance as yf
from datetime import datetime
import sys

# =============================================================================
# CONFIGURACION
# =============================================================================
PERIODO_MUESTRA = "3y"
MIN_OBSERVACIONES = 100
ANUALIZACION = 252

ACCIONES_LOCALES = [
    "ALUA.BA", "AUSO.BA", "BBAR.BA", "BMA.BA", "BOLT.BA", "BYMA.BA", "CAPX.BA", "CARC.BA",
    "CECO2.BA", "CELU.BA", "CEPU.BA", "CGPA2.BA", "COME.BA", "CRES.BA", "CTIO.BA", "DGCU2.BA",
    "EDN.BA", "FERR.BA", "GGAL.BA", "GRIM.BA", "HARG.BA", "INTR.BA", "IRSA.BA",
    "LEDE.BA", "LOMA.BA", "METR.BA", "MIRG.BA", "MOLA.BA", "MORI.BA", "OEST.BA",
    "PAMP.BA", "PATA.BA", "RICH.BA", "RIGO.BA", "SAMI.BA", "SEMI.BA", "SUPV.BA",
    "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"
]

FACTORES = {
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ',
    '^MXX': 'IPC Mexico',
    '^STOXX': 'STOXX Europa 600',
    '^GDAXI': 'DAX',
    '^FCHI': 'CAC 40',
    '^VIX': 'Indice de Volatilidad',
    'XLK': 'Sector Tecnologia',
    'XLF': 'Sector Financiero',
    'XLV': 'Sector Salud',
    'XLE': 'Sector Energia',
    'XLC': 'Sector Servicios de Comunicacion',
    'XLY': 'Sector Consumo Discrecional',
    'XLP': 'Sector Consumo Basico',
    'XLI': 'Sector Industrial',
    'XLB': 'Sector Materiales',
    'XLRE': 'Sector Inmobiliario',
    'XLU': 'Sector Servicios Publicos',
    'SPY': 'ETF S&P 500',
    'EWW': 'ETF MSCI Mexico',
    'IVW': 'ETF S&P 500 Crecimiento',
    'IVE': 'ETF S&P 500 Valor',
    'IWM': 'Russell 2000',
    'QUAL': 'Factor Calidad',
    'MTUM': 'Factor Momentum',
    'SIZE': 'Factor Tamano',
    'USMV': 'Factor Minima Volatilidad',
    '^MERV': 'Indice MERVAL',
    'DX-Y.NYB': 'Indice Dolar'
}

MAPEO_SECTOR_ETF = {
    'Technology': 'XLK',
    'Financial Services': 'XLF',
    'Healthcare': 'XLV',
    'Health Care': 'XLV',
    'Energy': 'XLE',
    'Communication Services': 'XLC',
    'Consumer Cyclical': 'XLY',
    'Consumer Defensive': 'XLP',
    'Industrials': 'XLI',
    'Basic Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
    'Utilities Regulated': 'XLU',
    'Technology Communication': 'XLC',
    'Financials': 'XLF',
    'Materials': 'XLB',
    'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP',
    'Telecommunication': 'XLC',
    'Information Technology': 'XLK',
}

MAPEO_INDUSTRIA_ETF = {
    'Banks': 'XLF',
    'Banks - Regional': 'XLF',
    'Banks - Diversified': 'XLF',
    'Capital Markets': 'XLF',
    'Insurance': 'XLF',
    'Insurance - Diversified': 'XLF',
    'Financial Conglomerates': 'XLF',
    'Credit Services': 'XLF',
    'Oil & Gas Integrated': 'XLE',
    'Oil & Gas E&P': 'XLE',
    'Oil & Gas Midstream': 'XLE',
    'Oil & Gas Refining & Marketing': 'XLE',
    'Oil & Gas Equipment & Services': 'XLE',
    'Drug Manufacturers - Specialty & Generic': 'XLV',
    'Drug Manufacturers - General': 'XLV',
    'Biotechnology': 'XLV',
    'Medical Devices': 'XLV',
    'Medical Care Facilities': 'XLV',
    'Diagnostics & Research': 'XLV',
    'Pharmaceuticals': 'XLV',
    'Aerospace & Defense': 'XLI',
    'Specialty Industrial Machinery': 'XLI',
    'Conglomerates': 'XLI',
    'Building Products & Equipment': 'XLI',
    'Farm & Heavy Construction Machinery': 'XLI',
    'Electrical Equipment & Parts': 'XLI',
    'Integrated Freight & Logistics': 'XLI',
    'Airlines': 'XLI',
    'Railroads': 'XLI',
    'Copper': 'XLB',
    'Steel': 'XLB',
    'Aluminum': 'XLB',
    'Chemicals': 'XLB',
    'Agricultural Inputs': 'XLB',
    'Building Materials': 'XLB',
    'Gold': 'XLB',
    'Other Industrial Metals & Mining': 'XLB',
    'Semiconductors': 'XLK',
    'Software - Application': 'XLK',
    'Software - Infrastructure': 'XLK',
    'Communication Equipment': 'XLK',
    'Electronic Components': 'XLK',
    'Information Technology Services': 'XLK',
    'Internet Content & Information': 'XLC',
    'Telecom Services': 'XLC',
    'Broadcasting': 'XLC',
    'Advertising Agencies': 'XLC',
    'Publishing': 'XLC',
    'REITs': 'XLRE',
    'Real Estate Services': 'XLRE',
    'Real Estate - Development': 'XLRE',
    'Real Estate - Diversified': 'XLRE',
    'Utilities - Regulated Electric': 'XLU',
    'Utilities - Regulated Gas': 'XLU',
    'Utilities - Renewable': 'XLU',
    'Utilities - Diversified': 'XLU',
    'Utilities Regulated': 'XLU',
    'Apparel Manufacturing': 'XLY',
    'Auto Manufacturers': 'XLY',
    'Restaurants': 'XLY',
    'Lodging': 'XLY',
    'Resorts & Casinos': 'XLY',
    'Leisure': 'XLY',
    'Specialty Retail': 'XLY',
    'Apparel Retail': 'XLY',
    'Footwear & Accessories': 'XLY',
    'Packaged Foods': 'XLP',
    'Beverages - Non-Alcoholic': 'XLP',
    'Beverages - Brewers': 'XLP',
    'Tobacco': 'XLP',
    'Household & Personal Products': 'XLP',
    'Grocery Stores': 'XLP',
    'Food Distribution': 'XLP',
}

ALTERNATIVAS_FACTOR = {
    '^STOXX': ['VGK', 'FEZ'],
    'DX-Y.NYB': ['UUP'],
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def _normalizar_timezone(df_or_series):
    """Elimina timezone del indice si existe."""
    obj = df_or_series.copy()
    if obj.index.tz is not None:
        obj.index = obj.index.tz_localize(None)
    return obj


def _extraer_close_desde_yf(raw):
    """
    Extrae precios de cierre desde un DataFrame crudo de yfinance.
    Maneja tanto columnas simples como MultiIndex ('Close', ticker).
    """
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        return None

    if not isinstance(raw.columns, pd.MultiIndex):
        if 'Close' in raw.columns:
            return raw[['Close']]
        elif 'Adj Close' in raw.columns:
            return raw[['Adj Close']]
        else:
            return raw.iloc[:, :1]

    level0 = raw.columns.get_level_values(0)
    if 'Close' in level0:
        close = raw['Close']
    elif 'Adj Close' in level0:
        close = raw['Adj Close']
    else:
        close = raw.iloc[:, raw.columns.get_level_values(0).unique().tolist().index(raw.columns.get_level_values(0)[0])]

    if isinstance(close, pd.DataFrame) and close.columns.nlevels > 1:
        close.columns = close.columns.get_level_values(1) if len(close.columns.levels) > 1 else close.columns.get_level_values(0)
    return close


def descargar_precios_activos(tickers, period="3y"):
    """Descarga precios de cierre para la lista de activos locales."""
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    precios = _extraer_close_desde_yf(raw)
    if precios is None or precios.empty:
        raise ValueError("No se pudieron descargar precios de activos")
    precios = _normalizar_timezone(precios)
    return precios


def descargar_merval_robusto(period="3y"):
    """Descarga ^MERV con fallback a auto_adjust=False."""
    merv = yf.download('^MERV', period=period, auto_adjust=True, progress=False)
    precios = _extraer_close_desde_yf(merv)
    if precios is not None and len(precios) >= 100:
        precios = _normalizar_timezone(precios)
        if isinstance(precios, pd.DataFrame) and precios.shape[1] == 1:
            s = precios.iloc[:, 0]
            s.name = '^MERV'
            return s
        return precios

    print("  [ADVERTENCIA] ^MERV con auto_adjust=True devolvio datos insuficientes. Reintentando con auto_adjust=False...")
    merv = yf.download('^MERV', period=period, auto_adjust=False, progress=False)
    precios = _extraer_close_desde_yf(merv)
    if precios is None or precios.empty:
        raise ValueError("No se pudieron descargar datos para ^MERV")
    precios = _normalizar_timezone(precios)
    if isinstance(precios, pd.DataFrame) and precios.shape[1] == 1:
        s = precios.iloc[:, 0]
        s.name = '^MERV'
        return s
    return precios


def descargar_factor_individual(ticker, period="3y"):
    """Descarga un factor individual."""
    raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    precios = _extraer_close_desde_yf(raw)
    if precios is None or precios.empty:
        return None
    precios = _normalizar_timezone(precios)
    if isinstance(precios, pd.DataFrame) and precios.shape[1] == 1:
        s = precios.iloc[:, 0]
        s.name = ticker
        return s
    return precios


def descargar_factores_individual(factores_dict, period="3y"):
    """Descarga factores en batch usando yfinance para mayor velocidad."""
    print(f"  Descargando {len(factores_dict)} factores en batch...")
    
    # Descargar todos los factores de una vez
    tickers = list(factores_dict.keys())
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    precios = _extraer_close_desde_yf(raw)
    
    if precios is None or precios.empty:
        print("  [ERROR] No se pudieron descargar factores en batch, intentando individualmente...")
        # Fallback a descarga individual
        series_ok = {}
        fallidos = []
        for ticker in factores_dict:
            serie = descargar_factor_individual(ticker, period)
            if serie is not None:
                series_ok[ticker] = serie
                continue
            if ticker in ALTERNATIVAS_FACTOR:
                for alt in ALTERNATIVAS_FACTOR[ticker]:
                    serie_alt = descargar_factor_individual(alt, period)
                    if serie_alt is not None:
                        serie_alt.name = alt
                        series_ok[alt] = serie_alt
                        break
                else:
                    fallidos.append(ticker)
            else:
                fallidos.append(ticker)
        if fallidos:
            print(f"  Factores sin datos: {fallidos}")
        if not series_ok:
            return pd.DataFrame()
        df = pd.concat(series_ok, axis=1)
        return df
    
    # Normalizar timezone
    precios = _normalizar_timezone(precios)
    
    # Verificar qué tickers se descargaron correctamente
    fallidos = []
    for ticker in tickers:
        if ticker not in precios.columns:
            if ticker in ALTERNATIVAS_FACTOR:
                for alt in ALTERNATIVAS_FACTOR[ticker]:
                    serie_alt = descargar_factor_individual(alt, period)
                    if serie_alt is not None:
                        serie_alt.name = alt
                        precios[alt] = serie_alt
                        break
                else:
                    fallidos.append(ticker)
            else:
                fallidos.append(ticker)
    
    if fallidos:
        print(f"  Factores sin datos: {fallidos}")
    
    print(f"  Factores descargados exitosamente: {len(precios.columns)}")
    return precios


def obtener_info_ticker(ticker):
    """Obtiene nombre, sector e industria de un ticker desde yfinance."""
    try:
        info = yf.Ticker(ticker).info
        return {
            'nombre': info.get('longName', info.get('shortName', 'N/A')),
            'sector': info.get('sector', 'N/A'),
            'industria': info.get('industry', 'N/A')
        }
    except Exception:
        return {'nombre': 'N/A', 'sector': 'N/A', 'industria': 'N/A'}


def calcular_capm(activo_returns, factor_returns, min_obs=100):
    """
    Calcula metricas CAPM entre dos series de retornos diarios.
    Devuelve None si hay menos de min_obs observaciones solapadas.
    """
    def _to_series(x, default_name):
        if isinstance(x, pd.DataFrame):
            x = x.iloc[:, 0]
        s = pd.Series(np.asarray(x).ravel(), name=default_name)
        return s

    a = _to_series(activo_returns, 'activo')
    f = _to_series(factor_returns, 'factor')

    df_sync = pd.DataFrame({'activo': a, 'factor': f}).dropna()
    if len(df_sync) < min_obs:
        return None

    x = df_sync['factor'].values
    y = df_sync['activo'].values
    slope, intercept, r_value, p_value, std_err = st.linregress(x, y)
    return {
        'beta': float(slope),
        'alpha_diario': float(intercept),
        'alpha_anual': float(intercept) * ANUALIZACION,
        'correlacion': float(r_value),
        'r2': float(r_value ** 2),
        'p_value': float(p_value),
        'obs': len(df_sync)
    }


def ticker_limpio(ticker_raw):
    """Elimina el sufijo .BA de los tickers argentinos."""
    return ticker_raw.replace(".BA", "")


# =============================================================================
# DIAGNOSTICO OBLIGATORIO
# =============================================================================
def diagnosticar_alineacion(precios_activos, merval, ggals_col='GGAL.BA'):
    """
    Diagnostico de alineacion temporal entre activos y ^MERV.
    """
    print("\n" + "=" * 100)
    print("  DIAGNOSTICO DE ALINEACION TEMPORAL")
    print("=" * 100)

    for label, serie in [(ggals_col, precios_activos[ggals_col] if ggals_col in precios_activos.columns else None),
                         ('^MERV', merval)]:
        if serie is None:
            print(f"  {label}: NO ENCONTRADO")
            continue
        print(f"\n  --- {label} (Precios) ---")
        print(f"    Primeras 5 fechas: {list(serie.index[:5])}")
        print(f"    Ultimas 5 fechas:  {list(serie.index[-5:])}")
        print(f"    N filas totales:   {len(serie)}")
        print(f"    Timezone:          {serie.index.tz}")

    ret_ggal = precios_activos[ggals_col].pct_change() if ggals_col in precios_activos.columns else None
    ret_merv = merval.pct_change()

    for label, ret_serie in [(ggals_col, ret_ggal), ('^MERV', ret_merv)]:
        if ret_serie is None:
            continue
        print(f"\n  --- {label} (Retornos post pct_change) ---")
        print(f"    Primeras 5 fechas: {list(ret_serie.index[:5])}")
        print(f"    Ultimas 5 fechas:  {list(ret_serie.index[-5:])}")
        print(f"    N filas totales:   {len(ret_serie)}")
        print(f"    % NaN:             {ret_serie.isna().mean()*100:.2f}%")
        if ret_serie.isna().mean() > 0.20:
            print(f"    [ERROR] Mas del 20% de NaN en retornos de {label}. Datos corruptos.")
            return False

    if ret_ggal is not None:
        df_overlap = pd.concat([ret_ggal, ret_merv], axis=1).dropna()
        print(f"\n  --- Solapamiento GGAL vs MERVAL ---")
        print(f"    N filas solapadas: {len(df_overlap)}")
        if len(df_overlap) > 0:
            print(f"    Fecha inicio solap: {df_overlap.index[0]}")
            print(f"    Fecha fin solap:    {df_overlap.index[-1]}")

    if ggals_col in precios_activos.columns:
        precios_sync = pd.concat([precios_activos[ggals_col], merval], axis=1).dropna()
        if len(precios_sync) > 10:
            corr_precios = precios_sync.iloc[:, 0].corr(precios_sync.iloc[:, 1])
            print(f"\n  --- Sanity Check: Correlacion de PRECIOS (NO retornos) ---")
            print(f"    Corr precios GGAL vs MERVAL: {corr_precios:.4f}")
            if corr_precios > 0.8:
                print(f"    [OK] Precios altamente correlacionados")
            else:
                print(f"    [ADVERTENCIA] Correlacion de precios baja")

    tz_activos = precios_activos.index.tz
    tz_merval = merval.index.tz
    print(f"\n  --- Consistencia de Timezones ---")
    print(f"    Timezone activos: {tz_activos}")
    print(f"    Timezone merval:  {tz_merval}")
    if tz_activos != tz_merval:
        print(f"    [ADVERTENCIA] Timezones diferentes")
    else:
        print(f"    [OK] Timezones consistentes")

    print("\n  [DIAGNOSTICO COMPLETADO]")
    return True


# =============================================================================
# BLOQUE 1 – CAPM vs MERVAL
# =============================================================================
def calcular_capm_vs_merval(acciones_tickers, info_map, retornos_activos, retornos_merval):
    """
    Bloque 1: CAPM de cada accion vs el benchmark ^MERV.
    Recibe retornos pre-calculados (descarga ya hecha y alineada).
    """
    registros = []
    outliers_beta = []

    for t in acciones_tickers:
        if t not in retornos_activos.columns:
            continue

        m = calcular_capm(retornos_activos[t], retornos_merval)
        if m is None:
            continue

        nombre = ticker_limpio(t)
        if abs(m['beta']) > 5:
            outliers_beta.append((nombre, m['beta']))
            nombre = nombre + "*"

        info = info_map[t]
        registros.append({
            'Ticker': nombre,
            'Empresa': info['nombre'],
            'Sector': info['sector'],
            'Industria': info['industria'],
            'Alpha_anual': round(m['alpha_anual'], 6),
            'Beta': round(m['beta'], 4),
            'Corr': round(m['correlacion'], 4),
            'R2': round(m['r2'], 4),
            'PValue': round(m['p_value'], 4),
            'Obs': m['obs']
        })

    df = pd.DataFrame(registros)
    df = df.sort_values(by='R2', ascending=False).reset_index(drop=True)
    return df, outliers_beta


# =============================================================================
# BLOQUE 2 – CAPM vs TODOS LOS FACTORES
# =============================================================================
def calcular_capm_todos_factores(acciones_tickers, factores_dict, info_map, retornos_activos, retornos_factores):
    """
    Bloque 2: CAPM de cada accion vs cada factor disponible.
    Recibe retornos pre-calculados (descarga ya hecha y alineada).
    """
    registros = []
    pares_descartados = 0

    for t in acciones_tickers:
        if t not in retornos_activos.columns:
            continue
        activo_r = retornos_activos[t]

        for f in retornos_factores.columns:
            factor_r = retornos_factores[f]

            m = calcular_capm(activo_r, factor_r)
            if m is None:
                pares_descartados += 1
                continue

            info = info_map[t]
            registros.append({
                'Ticker_Raw': t,
                'Ticker': ticker_limpio(t),
                'Empresa': info['nombre'],
                'Sector': info['sector'],
                'Industria': info['industria'],
                'Factor_Ticker': f,
                'Factor_Nombre': factores_dict.get(f, f),
                'Alpha_anual': round(m['alpha_anual'], 6),
                'Beta': round(m['beta'], 4),
                'Corr': round(m['correlacion'], 4),
                'R2': round(m['r2'], 4),
                'PValue': round(m['p_value'], 4),
                'Obs': m['obs']
            })

    df = pd.DataFrame(registros)
    return df, pares_descartados


# =============================================================================
# BLOQUE 3 – MEJOR FACTOR POR ACTIVO
# =============================================================================
def construir_mejor_factor(df_total):
    """
    Bloque 3: Para cada activo, encuentra:
      A) mejor_global  = factor con mayor R2 entre TODOS (incluyendo ^MERV)
      B) mejor_no_merv = factor con mayor R2 excluyendo ^MERV
      C) Muestra R² de TODOS los factores ordenados
    """
    print("\n" + "=" * 100)
    print("  BLOQUE 3 – MEJOR FACTOR POR ACTIVO (ANÁLISIS COMPLETO DE R²)")
    print("=" * 100)

    # Para cada activo, mostrar todos los factores con sus R²
    tickers_unicos = df_total['Ticker'].unique()
    
    for ticker in tickers_unicos:
        df_ticker = df_total[df_total['Ticker'] == ticker].copy()
        df_ticker = df_ticker.sort_values(by='R2', ascending=False)
        
        print(f"\n  --- {ticker} ---")
        print(f"  {'Factor':12s} {'Nombre':30s} {'R²':>8s} {'Beta':>8s} {'Corr':>8s}")
        print("  " + "-" * 70)
        
        for _, row in df_ticker.iterrows():
            print(f"  {row['Factor_Ticker']:12s} {row['Factor_Nombre']:30s} "
                  f"{row['R2']:8.4f} {row['Beta']:8.4f} {row['Corr']:8.4f}")

    # Resumen: mejor factor global y mejor sin MERV
    idx_global = df_total.groupby('Ticker')['R2'].idxmax()
    df_global = df_total.loc[idx_global].copy()
    df_global = df_global[['Ticker', 'Factor_Ticker', 'Factor_Nombre', 'Beta', 'Corr', 'R2']]
    df_global = df_global.rename(columns={
        'Factor_Ticker': 'Mejor_Factor',
        'Factor_Nombre': 'Mejor_Factor_Nombre',
        'Beta': 'Beta_Global',
        'Corr': 'Corr_Global',
        'R2': 'R2_Global'
    })

    df_no_merv = df_total[df_total['Factor_Ticker'] != '^MERV'].copy()
    if not df_no_merv.empty:
        idx_no_merv = df_no_merv.groupby('Ticker')['R2'].idxmax()
        df_no_merv_best = df_no_merv.loc[idx_no_merv].copy()
        df_no_merv_best = df_no_merv_best[['Ticker', 'Factor_Ticker', 'Factor_Nombre', 'Beta', 'Corr', 'R2']]
        df_no_merv_best = df_no_merv_best.rename(columns={
            'Factor_Ticker': 'Mejor_Factor_NoMerv',
            'Factor_Nombre': 'Mejor_Factor_NoMerv_Nombre',
            'Beta': 'Beta_NoMerv',
            'Corr': 'Corr_NoMerv',
            'R2': 'R2_NoMerv'
        })
    else:
        df_no_merv_best = pd.DataFrame(columns=[
            'Ticker', 'Mejor_Factor_NoMerv', 'Mejor_Factor_NoMerv_Nombre',
            'Beta_NoMerv', 'Corr_NoMerv', 'R2_NoMerv'
        ])

    df_mejor = pd.merge(df_global, df_no_merv_best, on='Ticker', how='left')
    df_mejor = df_mejor.sort_values(by='R2_Global', ascending=False).reset_index(drop=True)

    print("\n" + "=" * 100)
    print("  RESUMEN: MEJOR FACTOR POR ACTIVO")
    print("=" * 100)
    print("\n  Columnas: Ticker | Mejor_Factor | R2_Global | Beta_Global | Mejor_Factor_NoMerv | R2_NoMerv | Beta_NoMerv")
    print("-" * 100)
    for _, r in df_mejor.iterrows():
        print(f"  {r['Ticker']:8s} | {r['Mejor_Factor']:8s} ({r['Mejor_Factor_Nombre']:25s}) | "
              f"R2={r['R2_Global']:.4f} b={r['Beta_Global']:.4f} | "
              f"{r['Mejor_Factor_NoMerv'] or 'N/A':8s} ({r['Mejor_Factor_NoMerv_Nombre'] or 'N/A':25s}) | "
              f"R2={r['R2_NoMerv'] if pd.notna(r['R2_NoMerv']) else 'N/A':>6} b={r['Beta_NoMerv'] if pd.notna(r['Beta_NoMerv']) else 'N/A':>6}")

    return df_mejor


# =============================================================================
# BLOQUE 4 – ELIMINADO (Ya no usa mapeo de sector/industria)
# =============================================================================
# Esta función fue eliminada ya que ahora se prueban TODOS los factores
# y se muestran sus R² directamente, sin depender del mapeo sector/industria.


# =============================================================================
# MAIN
# =============================================================================
def main():
    # Configurar salida a archivo
    output_file = "CAPM_LOCALES_VS_MERV_RESULTADOS.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        sys.stdout = f
        
        print("=" * 100)
        print("  CAPM LOCALES vs MERVAL – ANALISIS MULTI-FACTOR")
        print(f"  Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        # Obtener info de tickers
        print("\n[INIT] Obteniendo informacion de empresa (sector / industria)...")
        info_map = {}
        for t in ACCIONES_LOCALES:
            info_map[t] = obtener_info_ticker(t)

        # -------------------------------------------------------------------------
        # 0. DESCARGAR TODOS LOS PRECIOS PRIMERO
        # -------------------------------------------------------------------------
        print("\n[0/5] Descargando precios de activos locales...")
        precios_activos = descargar_precios_activos(ACCIONES_LOCALES, PERIODO_MUESTRA)

        print("[0/5] Descargando ^MERV...")
        merval = descargar_merval_robusto(PERIODO_MUESTRA)

        print("[0/5] Descargando factores globales...")
        precios_factores = descargar_factores_individual(FACTORES, PERIODO_MUESTRA)
        if precios_factores.empty:
            raise ValueError("No se pudieron descargar factores")

        # Normalizar timezones
        precios_activos = _normalizar_timezone(precios_activos)
        precios_factores = _normalizar_timezone(precios_factores)
        if isinstance(merval, pd.DataFrame):
            merval = merval.iloc[:, 0]
        merval = _normalizar_timezone(merval)
        merval.name = '^MERV'

        # Incluir ^MERV en precios_factores (misma serie, mismo indice)
        if '^MERV' not in precios_factores.columns:
            precios_factores['^MERV'] = merval

        # -------------------------------------------------------------------------
        # 1. SINCRONIZAR PRECIOS AL MISMO INDICE DE FECHAS
        # -------------------------------------------------------------------------
        print("\n[1/5] Sincronizando precios al mismo indice de fechas...")
        fechas_comunes = precios_activos.index.intersection(precios_factores.index)
        print(f"  Fechas comunes activos∩factores: {len(fechas_comunes)}")

        precios_activos_alin = precios_activos.loc[fechas_comunes]
        precios_factores_alin = precios_factores.loc[fechas_comunes]

        # Verificacion adicional: solapamiento directo GGAL vs MERVAL (precios)
        merv_serie = precios_factores_alin['^MERV'].dropna()
        ggal_serie = precios_activos_alin['GGAL.BA'].dropna() if 'GGAL.BA' in precios_activos_alin.columns else pd.Series(dtype=float)
        overlap = merv_serie.index.intersection(ggal_serie.index)
        print(f"  Solapamiento de precios GGAL vs ^MERV: {len(overlap)} fechas")

        # -------------------------------------------------------------------------
        # 2. CALCULAR RETORNOS UNA SOLA VEZ SOBRE DATOS ALINEADOS
        # -------------------------------------------------------------------------
        print("\n[2/5] Calculando retornos...")
        retornos_activos = precios_activos_alin.pct_change().iloc[1:]
        retornos_factores = precios_factores_alin.pct_change().iloc[1:]

        print(f"  Retornos activos:  {retornos_activos.shape}")
        print(f"  Retornos factores: {retornos_factores.shape}")

        # -------------------------------------------------------------------------
        # 3. DIAGNOSTICO
        # -------------------------------------------------------------------------
        diagnosticar_alineacion(precios_activos_alin, precios_factores_alin['^MERV'])

        # Sanity check GGAL vs MERVAL
        if 'GGAL.BA' in retornos_activos.columns and '^MERV' in retornos_factores.columns:
            m_ggal = calcular_capm(retornos_activos['GGAL.BA'], retornos_factores['^MERV'])
            if m_ggal:
                print("\n  [SANITY CHECK] GGAL vs ^MERV -> "
                      f"R2={m_ggal['r2']:.4f}, Beta={m_ggal['beta']:.4f}, "
                      f"Corr={m_ggal['correlacion']:.4f}, Obs={m_ggal['obs']}")
                if m_ggal['r2'] < 0.50:
                    print("  [ALERTA] R2 de GGAL vs MERVAL esperado > 0.80. Abortando.")
                    raise SystemExit("Sanity check fallo.")
            else:
                print("  [ALERTA] No se pudo calcular CAPM para GGAL vs MERVAL")
                raise SystemExit("Sanity check fallo.")

        # -------------------------------------------------------------------------
        # 4. CALCULAR CAPMs
        # -------------------------------------------------------------------------
        df_merval, outliers_beta = calcular_capm_vs_merval(
            ACCIONES_LOCALES, info_map, retornos_activos, retornos_factores['^MERV']
        )

        df_total, pares_descartados = calcular_capm_todos_factores(
            ACCIONES_LOCALES, FACTORES, info_map, retornos_activos, retornos_factores
        )

        # -------------------------------------------------------------------------
        # 5. CROSS-CHECK: verificar que GGAL vs ^MERV sea identico en ambos bloques
        # -------------------------------------------------------------------------
        print("\n" + "=" * 100)
        print("  CROSS-CHECK BLOQUE1 vs BLOQUE2")
        print("=" * 100)

        fila_total = df_total[
            (df_total['Ticker'] == 'GGAL') &
            (df_total['Factor_Ticker'] == '^MERV')
        ]
        fila_merval = df_merval[df_merval['Ticker'] == 'GGAL']

        if not fila_total.empty and not fila_merval.empty:
            r2_total = fila_total['R2'].values[0]
            r2_merval = fila_merval['R2'].values[0]
            beta_total = fila_total['Beta'].values[0]
            beta_merval = fila_merval['Beta'].values[0]
            obs_total = fila_total['Obs'].values[0]
            obs_merval = fila_merval['Obs'].values[0]

            print(f"  GGAL vs ^MERV en df_total:  R2={r2_total:.4f}, Beta={beta_total:.4f}, Obs={obs_total}")
            print(f"  GGAL vs ^MERV en df_merval: R2={r2_merval:.4f}, Beta={beta_merval:.4f}, Obs={obs_merval}")

            if abs(r2_total - r2_merval) > 0.01 or abs(beta_total - beta_merval) > 0.01 or obs_total != obs_merval:
                raise ValueError(
                    "DIVERGENCIA DETECTADA: df_total calcula GGAL vs ^MERV "
                    "diferente a df_merval. Los retornos no estan alineados."
                )
            print("  [OK] Sin divergencia detectada.")
        else:
            print("  [ADVERTENCIA] No se encontro GGAL vs ^MERV en alguna de las tablas")

        # -------------------------------------------------------------------------
        # 6. RESUMEN DE VALIDACION
        # -------------------------------------------------------------------------
        fecha_ini = precios_activos_alin.index.min().strftime('%Y-%m-%d') if len(precios_activos_alin) else 'N/A'
        fecha_fin = precios_activos_alin.index.max().strftime('%Y-%m-%d') if len(precios_activos_alin) else 'N/A'
        activos_con_datos = len([c for c in ACCIONES_LOCALES if c in precios_activos.columns])
        factores_con_datos = len(precios_factores.columns)

        print("\n" + "=" * 100)
        print("  RESUMEN DE VALIDACION")
        print("=" * 100)
        print(f"  Activos con datos:          {activos_con_datos} / {len(ACCIONES_LOCALES)}")
        print(f"  Factores con datos:         {factores_con_datos} / {len(FACTORES)}")
        print(f"  Rango de fechas efectivo:   {fecha_ini} -> {fecha_fin}")
        print(f"  Fechas comunes alineadas:   {len(fechas_comunes)}")
        print(f"  Pares descartados (Obs < {MIN_OBSERVACIONES}): {pares_descartados}")
        print(f"  Outliers Beta detectados (|Beta| > 5): {len(outliers_beta)}")

        # -------------------------------------------------------------------------
        # 7. IMPRESION DE BLOQUES
        # -------------------------------------------------------------------------
        print("\n" + "=" * 100)
        print("  BLOQUE 1 – CAPM vs MERVAL (benchmark base)")
        print("=" * 100)
        for nom, val in outliers_beta:
            print(f"  Beta outlier: {nom} Beta={val:.4f}")
        print(f"\n  Filas generadas: {len(df_merval)}")
        print(df_merval.to_string(index=False))

        print("\n" + "=" * 100)
        print("  BLOQUE 2 – CAPM vs TODOS LOS FACTORES")
        print("=" * 100)
        print(f"\n  Total combinaciones validas: {len(df_total)}")
        print(f"  Pares descartados (Obs < {MIN_OBSERVACIONES}): {pares_descartados}")

        df_mejor = construir_mejor_factor(df_total)

        # -------------------------------------------------------------------------
        # 8. VALIDACION CRUZADA FINAL
        # -------------------------------------------------------------------------
        print("\n" + "=" * 100)
        print("  VALIDACION CRUZADA BLOQUE1 vs BLOQUE2")
        print("=" * 100)

        pares_criticos = [
            ('GGAL', '^MERV', 0.70),
            ('PAMP', '^MERV', 0.70),
            ('BMA',  '^MERV', 0.65),
        ]

        for ticker, factor, umbral in pares_criticos:
            fila_total = df_total[
                (df_total['Ticker'] == ticker) &
                (df_total['Factor_Ticker'] == factor)
            ]
            fila_merval = df_merval[df_merval['Ticker'] == ticker]

            if fila_total.empty or fila_merval.empty:
                print(f"  {ticker} vs {factor}: NO ENCONTRADO en una de las tablas")
                continue

            r2_total = fila_total['R2'].values[0]
            r2_merval = fila_merval['R2'].values[0]

            match = "OK" if abs(r2_total - r2_merval) < 0.005 else "DIVERGENCIA"
            print(f"  {ticker} vs {factor}: Bloque1 R2={r2_merval:.4f} | Bloque2 R2={r2_total:.4f} | {match}")

            if r2_total < umbral:
                print(f"  [ADVERTENCIA] {ticker} vs {factor}: R2={r2_total:.4f} por debajo del umbral esperado {umbral}")

        print("\n" + "=" * 100)
        print("  FIN DEL ANALISIS")
        print("=" * 100)
        
        # Restaurar stdout
        sys.stdout = sys.__stdout__
        print(f"\n[INFO] Resultados guardados en: {output_file}")


if __name__ == "__main__":
    main()
