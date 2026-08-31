import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from scipy import stats

# Token de autenticación para API BCRA (desde variables bcra.py)
BCRA_API_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MDg1NDI0ODYsInR5cGUiOiJleHRlcm5hbCIsInVzZXIiOiJib29zYW5kcjk3QGdtYWlsLmNvbSJ9.LPr4IzzUi1bS7z8kLXxpirNebi9Rs4CdwDPPITW9OXvQV0DnpnpURARbi_8g2ixSKByeyPIni9gxGQkdAGR3YA"
BCRA_API_HEADER = f"BEARER {BCRA_API_TOKEN}"

# Configuración de gráficos
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

def obtener_riesgo_pais():
    """Obtiene el histórico de riesgo país desde ArgentinaDatos API"""
    url = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.sort_values('fecha')
        df = df.rename(columns={'valor': 'riesgo_pais'})
        
        print(f"✓ Riesgo país: {len(df)} registros desde {df['fecha'].min().date()} hasta {df['fecha'].max().date()}")
        return df
    except Exception as e:
        print(f"✗ Error al obtener riesgo país: {e}")
        return None

def obtener_reservas_bcra():
    """Obtiene el histórico de reservas internacionales desde Estadísticas BCRA API"""
    url = "https://api.estadisticasbcra.com/reservas"
    headers = {
        'Authorization': BCRA_API_HEADER
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['d'])
        df = df.sort_values('fecha')
        df = df.rename(columns={'v': 'reservas'})
        df = df[['fecha', 'reservas']]
        
        print(f"✓ Reservas BCRA: {len(df)} registros desde {df['fecha'].min().date()} hasta {df['fecha'].max().date()}")
        return df
    except Exception as e:
        print(f"✗ Error al obtener reservas: {e}")
        return None

def combinar_datos(df_riesgo, df_reservas):
    """Combina ambos DataFrames por fecha"""
    df = pd.merge(df_riesgo, df_reservas, on='fecha', how='inner')
    df = df.dropna()
    print(f"✓ Datos combinados: {len(df)} registros en común")
    return df

def calcular_estadisticas(df):
    """Calcula correlación y R² entre riesgo país y reservas"""
    x = df['reservas'].values
    y = df['riesgo_pais'].values
    
    # Correlación de Pearson
    correlacion, p_value = stats.pearsonr(x, y)
    
    # R² (coeficiente de determinación)
    slope, intercept, r_value, p_value_linreg, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2
    
    print("\n" + "="*70)
    print(" "*15 + "RESULTADOS NUMÉRICOS DEL ANÁLISIS")
    print("="*70)
    print(f"\n📊 CORRELACIÓN Y R² ENTRE RIESGO PAÍS Y RESERVAS DEL BCRA")
    print("-"*70)
    print(f"  Correlación de Pearson:  {correlacion:.4f}")
    print(f"  P-value:                 {p_value:.4e}")
    print(f"  R² (Coef. determinación): {r_squared:.4f}  ({r_squared*100:.2f}%)")
    print(f"  Pendiente (regresión):    {slope:.6f}")
    print(f"  Intercepto:              {intercept:.2f}")
    print("-"*70)
    print(f"  Registros analizados:     {len(df)}")
    print(f"  Período:                 {df['fecha'].min().date()} a {df['fecha'].max().date()}")
    print("="*70)
    
    return {
        'correlacion': correlacion,
        'p_value': p_value,
        'r_squared': r_squared,
        'slope': slope,
        'intercept': intercept
    }

def graficar_series(df):
    """Grafica ambas series temporales"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Gráfico 1: Riesgo País
    ax1.plot(df['fecha'], df['riesgo_pais'], color='red', linewidth=2, label='Riesgo País')
    ax1.set_ylabel('Riesgo País (bps)', fontsize=12, fontweight='bold')
    ax1.set_title('Histórico de Riesgo País', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Gráfico 2: Reservas
    ax2.plot(df['fecha'], df['reservas'], color='blue', linewidth=2, label='Reservas Internacionales')
    ax2.set_ylabel('Reservas (USD millones)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
    ax2.set_title('Histórico de Reservas Internacionales BCRA', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('riesgo_pais_reservas_historico.png', dpi=150, bbox_inches='tight')
    print("✓ Gráfico guardado: riesgo_pais_reservas_historico.png")
    plt.show()

def graficar_dispersion(df, stats_dict):
    """Grafica diagrama de dispersión con línea de regresión"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    x = df['reservas'].values
    y = df['riesgo_pais'].values
    
    # Diagrama de dispersión
    scatter = ax.scatter(x, y, alpha=0.6, c=df['fecha'].dt.year, cmap='viridis', s=50)
    
    # Línea de regresión
    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = stats_dict['slope'] * x_line + stats_dict['intercept']
    ax.plot(x_line, y_line, 'r--', linewidth=2, label=f'Regresión lineal (R²={stats_dict["r_squared"]:.4f})')
    
    ax.set_xlabel('Reservas Internacionales (USD millones)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Riesgo País (bps)', fontsize=12, fontweight='bold')
    ax.set_title('Relación entre Riesgo País y Reservas del BCRA', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Colorbar para años
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Año', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('riesgo_pais_reservas_dispersion.png', dpi=150, bbox_inches='tight')
    print("✓ Gráfico guardado: riesgo_pais_reservas_dispersion.png")
    plt.show()

def graficar_doble_eje(df):
    """Grafica ambas series en un mismo gráfico con doble eje"""
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # Eje izquierdo: Riesgo País
    color1 = 'tab:red'
    ax1.set_xlabel('Fecha', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Riesgo País (bps)', color=color1, fontsize=12, fontweight='bold')
    line1 = ax1.plot(df['fecha'], df['riesgo_pais'], color=color1, linewidth=2, label='Riesgo País')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    
    # Eje derecho: Reservas
    ax2 = ax1.twinx()
    color2 = 'tab:blue'
    ax2.set_ylabel('Reservas (USD millones)', color=color2, fontsize=12, fontweight='bold')
    line2 = ax2.plot(df['fecha'], df['reservas'], color=color2, linewidth=2, label='Reservas')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Combinar leyendas
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    plt.title('Riesgo País vs Reservas del BCRA', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('riesgo_pais_reservas_doble_eje.png', dpi=150, bbox_inches='tight')
    print("✓ Gráfico guardado: riesgo_pais_reservas_doble_eje.png")
    plt.show()

def main():
    print("="*60)
    print("OBTENIENDO DATOS DE RIESGO PAÍS Y RESERVAS BCRA")
    print("="*60 + "\n")
    
    # Obtener datos
    df_riesgo = obtener_riesgo_pais()
    df_reservas = obtener_reservas_bcra()
    
    if df_riesgo is None or df_reservas is None:
        print("✗ No se pudieron obtener los datos necesarios")
        return
    
    # Combinar datos
    df = combinar_datos(df_riesgo, df_reservas)
    
    if len(df) == 0:
        print("✗ No hay datos en común entre ambas series")
        return
    
    # Calcular estadísticas
    stats_dict = calcular_estadisticas(df)
    
    # Generar gráficos
    print("\nGenerando gráficos...")
    graficar_series(df)
    graficar_dispersion(df, stats_dict)
    graficar_doble_eje(df)
    
    # Guardar datos combinados
    df.to_csv('riesgo_pais_reservas_datos.csv', index=False)
    print(f"✓ Datos guardados: riesgo_pais_reservas_datos.csv")
    
    print("\n✓ Análisis completado exitosamente")

if __name__ == "__main__":
    main()
