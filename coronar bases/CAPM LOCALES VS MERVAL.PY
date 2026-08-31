import numpy as np
import pandas as pd
import scipy.stats as st
import yfinance as yf
from datetime import datetime

# Lista completa de acciones locales de la BCBA (con el sufijo .BA necesario para Yahoo Finance)
ACCIONES_LOCALES = [
    "ALUA.BA", "AUSO.BA", "BBAR.BA", "BMA.BA", "BOLT.BA", "BYMA.BA", "CAPX.BA", "CARC.BA",
    "CECO2.BA", "CELU.BA", "CEPU.BA", "CGPA2.BA", "COME.BA", "CRES.BA", "CTIO.BA", "DGCU2.BA",
    "EDN.BA", "FERR.BA", "GGAL.BA", "GRIM.BA", "HARG.BA", "INTR.BA", "IRSA.BA",
    "LEDE.BA", "LOMA.BA", "METR.BA", "MIRG.BA", "MOLA.BA", "MORI.BA", "OEST.BA",
    "PAMP.BA", "PATA.BA", "RICH.BA", "RIGO.BA", "SAMI.BA", "SEMI.BA", "SUPV.BA",
    "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"
]

def calcular_tabla_capm(tickers_acciones, benchmark="^MERV", period="3y", decimals=4):
    """
    Descarga masivamente datos de Yahoo Finance y calcula las métricas CAPM
    para todas las acciones frente al benchmark seleccionado.
    """
    print(f"Descargando datos históricos ({period}) para el mercado local...")
    
    # 1. Descargar datos de acciones
    raw_data = yf.download(tickers_acciones, period=period, progress=False, auto_adjust=True)
    # Compatibilidad: usar Close si Adj Close no existe
    if 'Adj Close' in raw_data.columns:
        raw_data = raw_data['Adj Close']
    else:
        raw_data = raw_data['Close']

    # 2. Descargar benchmark por separado para mejor control de errores
    bench_data = None
    bench_ticker = benchmark
    try:
        bench_download = yf.download(bench_ticker, period=period, progress=False, auto_adjust=True)
        if not bench_download.empty:
            if 'Adj Close' in bench_download.columns:
                bench_data = bench_download['Adj Close']
            else:
                bench_data = bench_download['Close']
    except Exception:
        bench_data = None

    # Fallback: intentar sin el prefijo ^ si aplica
    if bench_data is None and bench_ticker.startswith("^"):
        alt_ticker = bench_ticker.lstrip("^")
        print(f"  → Intentando ticker alternativo para benchmark: {alt_ticker}")
        try:
            bench_download = yf.download(alt_ticker, period=period, progress=False, auto_adjust=True)
            if not bench_download.empty:
                if 'Adj Close' in bench_download.columns:
                    bench_data = bench_download['Adj Close']
                else:
                    bench_data = bench_download['Close']
                bench_ticker = alt_ticker
        except Exception:
            bench_data = None

    if bench_data is None or bench_data.empty:
        raise ValueError(f"No se pudieron obtener datos para el benchmark {benchmark} (ni alternativos)")

    # Agregar benchmark al DataFrame unificado
    raw_data[bench_ticker] = bench_data
    benchmark = bench_ticker  # Usar el ticker que efectivamente funcionó
        
    # Calcular retornos del mercado (Merval)
    merval_returns = raw_data[benchmark].pct_change().dropna()
    
    # Listas para almacenar los resultados del bucle
    resultados = []
    
    print("\nProcesando regresiones lineales CAPM...")
    for ticker in tickers_acciones:
        if ticker not in raw_data.columns:
            continue
            
        try:
            # Sincronizar retornos de la acción con el Merval rueda por rueda
            accion_returns = raw_data[ticker].pct_change().dropna()
            
            # Alinear los índices de fechas para evitar problemas de feriados individuales
            df_sync = pd.DataFrame({
                'mercado': merval_returns,
                'activo': accion_returns
            }).dropna()
            
            # Validar que tengamos una muestra representativa de ruedas operadas
            if len(df_sync) < 100:
                continue
                
            x = df_sync['mercado'].values
            y = df_sync['activo'].values
            
            # Ejecutar regresión lineal de mínimos cuadrados
            slope, intercept, r_value, p_value, std_err = st.linregress(x, y)
            
            # Guardar métricas en un diccionario limpio
            resultados.append({
                'Ticker': ticker.replace(".BA", ""), # Limpiamos el ticker para el output final
                'Beta (Sistemático)': np.round(slope, decimals),
                'Alpha (Idiosincrático)': np.round(intercept, decimals),
                'Correlación (R)': np.round(r_value, decimals),
                'R-Cuadrado (R²)': np.round(r_value**2, decimals),
                'P-Value': np.round(p_value, decimals),
                'Error Estándar': np.round(std_err, decimals),
                'Significativo (95%)': "Sí" if p_value < 0.05 else "No"
            })
            
        except Exception:
            # Si una acción falla o no tiene suficiente liquidez/datos, el script continúa sin detenerse
            continue

    # 2. Construir el DataFrame final unificado
    df_capm = pd.DataFrame(resultados)
    
    # Ordenar por el coeficiente de correlación de mayor a menor dependencia con el mercado
    df_capm = df_capm.sort_values(by='Correlación (R)', ascending=False).reset_index(drop=True)
    
    return df_capm

# ==========================================
# PARÁMETROS Y EJECUCIÓN DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    PERIODO_MUESTRA = "3y"  # Ventana temporal (puede ser '1y', '2y', '3y' o '5y')
    
    try:
        # Ejecutar el cálculo unificado
        df_final_merval = calcular_tabla_capm(ACCIONES_LOCALES, benchmark="^MERV", period=PERIODO_MUESTRA)
        
        # Configurar pandas para mostrar todas las columnas y filas cómodamente en consola
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 1000)
        
        print("\n" + "="*85)
        print(f" TABLA CONSOLIDADA: ESTADÍSTICAS CAPM VS MERCADO (^MERV) - ÚLTIMOS {PERIODO_MUESTRA.upper()}")
        print("="*85)
        print(df_final_merval)
        print("="*85)
        
        # Opcional: Descomenta la línea de abajo si quieres exportar la tabla directamente a un Excel
        # df_final_merval.to_excel("capm_acciones_locales.xlsx", index=False)
        
    except Exception as e:
        print(f"\n❌ Error al procesar la matriz del mercado: {e}")