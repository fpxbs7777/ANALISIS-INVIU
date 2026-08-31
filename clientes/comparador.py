"""
Análisis comparativo de activos: SPY, QQQ, XLU, XLI y MSCI (EFA)
en el estilo de comparación directa con métricas clave.

Compara:
- Correlación y R² entre pares
- Alpha y Beta
- Retorno anual
- Volatilidad anual
- Sharpe Ratio
- Crecimiento acumulado
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Asegurar imports relativos desde el paquete principal
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from descargar_series_activos_factores import descargar_series_tickers
from calcular_metricas_tickers_factores import calcular_metricas_regresion

# Definir activos a comparar
ACTIVOS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "XLU": "Utilities Select Sector",
    "XLI": "Industrial Select Sector",
    "EFA": "MSCI EAFE (Europa, Australasia, Lejano Oriente)"
}

# Parámetros
PERIODO = "5y"
RISK_FREE_RATE = 0.04
ANNUAL_TRADING_DAYS = 252


def descargar_precios_activos(tickers: list, periodo: str = "5y") -> pd.DataFrame:
    """
    Descarga precios de cierre ajustados usando el sistema de caché.
    """
    print(f"\n📥 Descargando precios para: {', '.join(tickers)}")
    resultado = descargar_series_tickers(
        tickers=tickers,
        periodo=periodo,
        intervalo="1d",
        directorio_salida="datos_series",
        batch_size=50,
        usar_cache=True,
        max_edad_cache_horas=24,
    )

    if not resultado or not resultado.get("datos"):
        raise RuntimeError("No se pudieron descargar datos de precios.")

    df = pd.DataFrame(resultado["datos"])
    df = df.sort_index()
    return df


def calcular_retornos(df_precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula retornos diarios a partir de precios de cierre.
    """
    returns = df_precios.pct_change().dropna(how="all")
    returns = returns.dropna(axis=1, how="all")
    return returns


def calcular_metricas_individuales(returns: pd.DataFrame, risk_free_rate: float = 0.04) -> Dict[str, Dict]:
    """
    Calcula métricas individuales para cada activo:
    - Retorno anual
    - Volatilidad anual
    - Sharpe Ratio
    - Crecimiento acumulado
    """
    metricas = {}
    
    for ticker in returns.columns:
        serie = returns[ticker].dropna()
        if len(serie) < 20:
            continue
        
        # Retorno diario promedio
        mean_daily = serie.mean()
        std_daily = serie.std()
        
        # Anualizar
        mean_annual = mean_daily * ANNUAL_TRADING_DAYS
        vol_annual = std_daily * np.sqrt(ANNUAL_TRADING_DAYS)
        
        # Sharpe Ratio
        sharpe = (mean_annual - risk_free_rate) / vol_annual if vol_annual > 0 else 0.0
        
        # Crecimiento acumulado (total return)
        crecimiento_acumulado = (1 + serie).prod() - 1
        
        metricas[ticker] = {
            "retorno_anual": mean_annual,
            "volatilidad_anual": vol_annual,
            "sharpe_ratio": sharpe,
            "crecimiento_acumulado": crecimiento_acumulado,
        }
    
    return metricas


def comparar_par_activos(
    ticker1: str,
    ticker2: str,
    returns: pd.DataFrame,
    metricas_individuales: Dict[str, Dict],
    risk_free_rate: float = 0.04,
) -> None:
    """
    Compara dos activos en el estilo del ejemplo.
    """
    if ticker1 not in returns.columns or ticker2 not in returns.columns:
        return
    
    # Obtener métricas de regresión
    ret1 = returns[ticker1]
    ret2 = returns[ticker2]
    
    metricas_reg = calcular_metricas_regresion(ret1, ret2, risk_free_rate=risk_free_rate)
    
    if not metricas_reg:
        return
    
    # Obtener métricas individuales
    m1 = metricas_individuales.get(ticker1, {})
    m2 = metricas_individuales.get(ticker2, {})
    
    if not m1 or not m2:
        return
    
    # Nombres descriptivos
    nombre1 = ACTIVOS.get(ticker1, ticker1)
    nombre2 = ACTIVOS.get(ticker2, ticker2)
    
    # Formatear resultados
    correlacion_pct = metricas_reg["correlacion"] * 100
    r2_pct = metricas_reg["r_squared"] * 100
    alpha_anual_pct = metricas_reg["alpha_anual"] * 100
    beta = metricas_reg["beta"]
    
    retorno1_pct = m1["retorno_anual"] * 100
    retorno2_pct = m2["retorno_anual"] * 100
    vol1_pct = m1["volatilidad_anual"] * 100
    vol2_pct = m2["volatilidad_anual"] * 100
    sharpe1 = m1["sharpe_ratio"]
    sharpe2 = m2["sharpe_ratio"]
    crecimiento1_pct = m1["crecimiento_acumulado"] * 100
    crecimiento2_pct = m2["crecimiento_acumulado"] * 100
    
    # Determinar si se mueven igual, más o menos
    if correlacion_pct >= 90:
        movimiento = "casi igual"
    elif correlacion_pct >= 70:
        movimiento = "similar"
    elif correlacion_pct >= 50:
        movimiento = "moderadamente relacionado"
    else:
        movimiento = "poco relacionado"
    
    print(f"\n{nombre1} vs {nombre2}:")
    print(f" Se mueven {movimiento} (correlación {correlacion_pct:.1f}%, R² {r2_pct:.1f}%).")
    
    # Alpha y Beta - interpretación basada en retorno absoluto
    # Solo decir "rinde más/menos" si el retorno absoluto coincide con el alpha
    if retorno1_pct > retorno2_pct:
        if alpha_anual_pct > 0.1:
            interpretacion_rendimiento = "rinde más"
        else:
            interpretacion_rendimiento = "rinde más"  # Aunque alpha sea bajo, el retorno absoluto es mayor
    elif retorno1_pct < retorno2_pct:
        if alpha_anual_pct < -0.1:
            interpretacion_rendimiento = "rinde menos"
        else:
            interpretacion_rendimiento = "rinde menos"  # Aunque alpha sea positivo, el retorno absoluto es menor
    else:
        # Retornos muy similares
        if alpha_anual_pct > 0.1:
            interpretacion_rendimiento = "rinde un poco más"
        elif alpha_anual_pct < -0.1:
            interpretacion_rendimiento = "rinde un poco menos"
        else:
            interpretacion_rendimiento = "rinde similar"
    
    print(f" El {ticker1} muestra un alpha anualizado de {alpha_anual_pct:.2f}% y un beta de {beta:.2f}, "
          f"lo que indica que {interpretacion_rendimiento} y se mueve ", end="")
    
    if beta > 1.05:
        print("más que el", end="")
    elif beta < 0.95:
        print("menos que el", end="")
    else:
        print("similar al", end="")
    print(f" {ticker2}.")
    
    # Comparación de rendimiento
    ganador_retorno = ticker1 if retorno1_pct > retorno2_pct else ticker2
    perdedor_retorno = ticker2 if retorno1_pct > retorno2_pct else ticker1
    
    print(f" En rendimiento puro, {ganador_retorno} gana con {max(retorno1_pct, retorno2_pct):.1f}% anual "
          f"contra {min(retorno1_pct, retorno2_pct):.1f}%, ", end="")
    
    # Determinar quién tiene mayor/menor volatilidad según el ganador
    if ganador_retorno == ticker1:
        vol_ganador = vol1_pct
        vol_perdedor = vol2_pct
        sharpe_ganador = sharpe1
        sharpe_perdedor = sharpe2
        crecimiento_ganador = crecimiento1_pct
        crecimiento_perdedor = crecimiento2_pct
    else:
        vol_ganador = vol2_pct
        vol_perdedor = vol1_pct
        sharpe_ganador = sharpe2
        sharpe_perdedor = sharpe1
        crecimiento_ganador = crecimiento2_pct
        crecimiento_perdedor = crecimiento1_pct
    
    # Volatilidad - comparar desde la perspectiva del ganador
    diff_vol = abs(vol_ganador - vol_perdedor)
    if diff_vol < 0.5:  # Similar si diferencia < 0.5%
        print(f"con volatilidad similar ({vol_ganador:.1f}% vs {vol_perdedor:.1f}%) ", end="")
    elif vol_ganador > vol_perdedor:
        print(f"y aun con mayor volatilidad ({vol_ganador:.1f}% vs {vol_perdedor:.1f}%) ", end="")
    else:
        print(f"y con menor volatilidad ({vol_ganador:.1f}% vs {vol_perdedor:.1f}%) ", end="")
    
    # Sharpe
    if sharpe_ganador > sharpe_perdedor:
        print(f"mantiene mejor Sharpe ({sharpe_ganador:.2f} vs {sharpe_perdedor:.2f}) ", end="")
    elif sharpe_ganador < sharpe_perdedor:
        print(f"aunque con peor Sharpe ({sharpe_ganador:.2f} vs {sharpe_perdedor:.2f}) ", end="")
    
    print(f"y mayor crecimiento acumulado ({crecimiento_ganador:.0f}% vs {crecimiento_perdedor:.0f}%).")


def mostrar_tabla_resumen(metricas_individuales: Dict[str, Dict]):
    """
    Muestra una tabla resumen con todas las métricas individuales.
    """
    print(f"\n{'='*80}")
    print("📊 RESUMEN DE MÉTRICAS INDIVIDUALES")
    print(f"{'='*80}")
    
    filas = []
    for ticker, metricas in metricas_individuales.items():
        nombre = ACTIVOS.get(ticker, ticker)
        filas.append({
            "Activo": nombre,
            "Ticker": ticker,
            "Retorno Anual %": metricas["retorno_anual"] * 100,
            "Volatilidad Anual %": metricas["volatilidad_anual"] * 100,
            "Sharpe Ratio": metricas["sharpe_ratio"],
            "Crecimiento Acumulado %": metricas["crecimiento_acumulado"] * 100,
        })
    
    df = pd.DataFrame(filas)
    print(df.round(2).to_string(index=False))


def main():
    """
    Función principal que ejecuta el análisis comparativo.
    """
    print("="*80)
    print("🔍 ANÁLISIS COMPARATIVO DE ACTIVOS")
    print("="*80)
    print(f"Activos: {', '.join([f'{k} ({v})' for k, v in ACTIVOS.items()])}")
    print(f"Período: {PERIODO}")
    print(f"Tasa libre de riesgo: {RISK_FREE_RATE*100:.1f}%")
    
    # 1. Descargar precios
    tickers = list(ACTIVOS.keys())
    df_precios = descargar_precios_activos(tickers, periodo=PERIODO)
    
    if df_precios.empty:
        print("❌ No se pudieron descargar datos de precios.")
        return
    
    # 2. Calcular retornos
    returns = calcular_retornos(df_precios)
    
    # Verificar que todos los activos estén presentes
    tickers_validos = [t for t in tickers if t in returns.columns]
    if len(tickers_validos) < len(tickers):
        faltantes = set(tickers) - set(tickers_validos)
        print(f"⚠️ Advertencia: No se encontraron datos para: {', '.join(faltantes)}")
    
    if len(tickers_validos) < 2:
        print("❌ Se necesitan al menos 2 activos con datos válidos.")
        return
    
    # 3. Calcular métricas individuales
    print("\n📊 Calculando métricas individuales...")
    metricas_individuales = calcular_metricas_individuales(returns, risk_free_rate=RISK_FREE_RATE)
    
    # 4. Mostrar tabla resumen
    mostrar_tabla_resumen(metricas_individuales)
    
    # 5. Comparaciones por pares (enfocadas en SPY como referencia principal)
    print(f"\n{'='*80}")
    print("🔍 COMPARACIONES POR PARES")
    print(f"{'='*80}")
    
    # Comparar SPY con los demás
    if "SPY" in tickers_validos:
        for ticker in tickers_validos:
            if ticker != "SPY":
                comparar_par_activos("SPY", ticker, returns, metricas_individuales, RISK_FREE_RATE)
    
    # Comparar QQQ con XLU y XLI (sectores vs tech)
    if "QQQ" in tickers_validos:
        for ticker in ["XLU", "XLI"]:
            if ticker in tickers_validos:
                comparar_par_activos("QQQ", ticker, returns, metricas_individuales, RISK_FREE_RATE)
    
    # Comparar XLU vs XLI (sectores diferentes)
    if "XLU" in tickers_validos and "XLI" in tickers_validos:
        comparar_par_activos("XLU", "XLI", returns, metricas_individuales, RISK_FREE_RATE)
    
    # Comparar EFA (MSCI) con SPY (internacional vs US)
    if "EFA" in tickers_validos and "SPY" in tickers_validos:
        comparar_par_activos("EFA", "SPY", returns, metricas_individuales, RISK_FREE_RATE)
    
    print("\n\n✅ Análisis completado.")


if __name__ == "__main__":
    main()