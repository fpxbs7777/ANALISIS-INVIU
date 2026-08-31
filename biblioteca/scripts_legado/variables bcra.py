import requests
import pandas as pd
from datetime import datetime, timedelta

# API BCRA Configuration
BCRA_API_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MDg1NDI0ODYsInR5cGUiOiJleHRlcm5hbCIsInVzZXIiOiJib29zYW5kcjk3QGdtYWlsLmNvbSJ9.LPr4IzzUi1bS7z8kLXxpirNebi9Rs4CdwDPPITW9OXvQV0DnpnpURARbi_8g2ixSKByeyPIni9gxGQkdAGR3YA"
BCRA_API_HEADER = f"BEARER {BCRA_API_TOKEN}"
BCRA_TOKEN_EXPIRATION = "2027-04-24 01:54:46"
BCRA_API_BASE_URL = "https://api.estadisticasbcra.com"

# Lista completa de endpoints del API BCRA
BCRA_ENDPOINTS = {
    "milestones": "Eventos relevantes (presidencia, ministros, presidentes BCRA, cepo)",
    "base": "Base monetaria",
    "base_usd": "Base monetaria dividida USD",
    "base_usd_of": "Base monetaria dividida USD Oficial",
    "reservas": "Reservas internacionales",
    "base_div_res": "Base monetaria dividida reservas internacionales",
    "usd": "Cotización del USD",
    "usd_of": "Cotización del USD Oficial",
    "usd_of_minorista": "Cotización del USD Oficial (Minorista)",
    "var_usd_vs_usd_of": "Variación entre USD y USD oficial",
    "circulacion_monetaria": "Circulación monetaria",
    "billetes_y_monedas": "Billetes y monedas",
    "efectivo_en_ent_fin": "Efectivo en entidades financieras",
    "depositos_cuenta_ent_fin": "Depósitos de entidades financieras en cuenta del BCRA",
    "depositos": "Depósitos",
    "cuentas_corrientes": "Cuentas corrientes",
    "cajas_ahorro": "Cajas de ahorro",
    "plazo_fijo": "Plazos fijos",
    "tasa_depositos_30_dias": "Tasa de interés por depósitos",
    "prestamos": "Préstamos",
    "tasa_prestamos_personales": "Tasa préstamos personales",
    "tasa_adelantos_cuenta_corriente": "Tasa adelantos cuenta corriente",
    "porc_prestamos_vs_depositos": "Porcentaje de préstamos en relación a depósitos",
    "lebac": "LEBACs",
    "leliq": "LELIQs",
    "lebac_usd": "LEBACs en USD",
    "leliq_usd": "LELIQs en USD",
    "leliq_usd_of": "LELIQs en USD Oficial",
    "tasa_leliq": "Tasa de LELIQs",
    "m2_privado_variacion_mensual": "M2 privado variación mensual",
    "cer": "CER",
    "uva": "UVA",
    "uvi": "UVI",
    "tasa_badlar": "Tasa BADLAR",
    "tasa_baibar": "Tasa BAIBAR",
    "tasa_tm20": "Tasa TM20",
    "tasa_pase_activas_1_dia": "Tasa pase activas a 1 día",
    "tasa_pase_pasivas_1_dia": "Tasa pase pasivas a 1 día",
    "inflacion_mensual_oficial": "Inflación mensual oficial",
    "inflacion_interanual_oficial": "Inflación interanual oficial",
    "inflacion_esperada_oficial": "Inflación esperada oficial",
    "dif_inflacion_esperada_vs_interanual": "Diferencia inflación esperada vs interanual",
    "var_base_monetaria_interanual": "Variación base monetaria interanual",
    "var_usd_interanual": "Variación USD interanual",
    "var_usd_oficial_interanual": "Variación USD Oficial interanual",
    "var_merval_interanual": "Variación MERVAL interanual",
    "var_usd_anual": "Variación anual del dólar",
    "var_usd_of_anual": "Variación anual del dólar oficial",
    "var_merval_anual": "Variación anual del MERVAL",
    "merval": "MERVAL",
    "merval_usd": "MERVAL dividido cotización del USD"
}

def get_api_data(endpoint):
    """Obtiene datos del API de estadísticas BCRA para un endpoint específico"""
    url = f"{BCRA_API_BASE_URL}/{endpoint}"
    headers = {
        'Authorization': BCRA_API_HEADER
    }
    
    try:
        print(f"Consultando API: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            print(f"No se encontraron datos para {endpoint}")
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        # Renombrar columnas para consistencia
        if 'd' in df.columns:
            df = df.rename(columns={'d': 'fecha'})
        if 'v' in df.columns:
            df = df.rename(columns={'v': 'valor'})
        
        print(f"Se obtuvieron {len(df)} registros para {endpoint}")
        return df
    
    except Exception as e:
        print(f"Error al obtener datos del API para {endpoint}: {str(e)}")
        return pd.DataFrame()

def calculate_variations_from_api(df):
    """Calcula variaciones diaria, semanal, mensual y anual desde datos del API"""
    if df.empty or 'valor' not in df.columns:
        return None
    
    try:
        # Asegurar que valor sea numérico
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
        df = df.dropna(subset=['valor'])
        
        if len(df) < 2:
            return None
        
        # Ordenar por fecha
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df = df.sort_values('fecha')
        
        values = df['valor'].values
        
        # Variación diaria
        var_diaria = ((values[-1] - values[-2]) / values[-2] * 100) if len(values) >= 2 else 0
        
        # Variación semanal (último vs hace 7 días aprox)
        var_semanal = ((values[-1] - values[-7]) / values[-7] * 100) if len(values) >= 7 else 0
        
        # Variación mensual (último vs hace 30 días aprox)
        var_mensual = ((values[-1] - values[-30]) / values[-30] * 100) if len(values) >= 30 else 0
        
        # Variación anual (último vs hace 365 días aprox)
        var_anual = ((values[-1] - values[-365]) / values[-365] * 100) if len(values) >= 365 else 0
        
        return {
            'diaria': var_diaria,
            'semanal': var_semanal,
            'mensual': var_mensual,
            'anual': var_anual,
            'valor_actual': values[-1],
            'valor_anterior': values[-2] if len(values) >= 2 else None
        }
    except Exception as e:
        print(f"Error al calcular variaciones: {str(e)}")
        return None

def get_bcra_variables():
    url = "https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Deshabilitar advertencias de SSL
        requests.packages.urllib3.disable_warnings()
        
        print("Haciendo la solicitud al BCRA...")
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        print(f"Respuesta recibida. Código de estado: {response.status_code}")
        
        # Parsear el contenido HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Lista para almacenar los datos
        variables = []
        
        # Buscar todas las tablas
        tables = soup.find_all('table', {'class': 'table'})
        print(f"Se encontraron {len(tables)} tablas en la página")
        
        if not tables:
            print("No se encontraron tablas en la página")
            return pd.DataFrame()
            
        # Tomar la primera tabla que parece contener los datos
        table = tables[0]
        
        # Buscar todas las filas de la tabla
        rows = table.find_all('tr')
        print(f"Se encontraron {len(rows)} filas en la tabla")
        
        for row in rows:
            cols = row.find_all('td')
            # Buscar filas con al menos 3 columnas
            if len(cols) >= 3:
                # Extraer el enlace si existe
                link = cols[0].find('a')
                href = link.get('href') if link else ''
                serie = ''
                
                # Extraer el número de serie del href si existe
                if href and 'serie=' in href:
                    serie = href.split('serie=')[1].split('&')[0]
                
                variable = {
                    'nombre': cols[0].get_text(strip=True),
                    'fecha': cols[1].get_text(strip=True) if len(cols) > 1 else '',
                    'valor': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                    'serie_id': serie,
                    'url_completa': f"https://www.bcra.gob.ar{href}" if href else ''
                }
                variables.append(variable)
                print(f"Variable encontrada: {variable['nombre']} (ID: {serie})")
        
        return pd.DataFrame(variables)
    
    except Exception as e:
        print(f"Error al obtener las variables del BCRA: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def calculate_variations(historical_df):
    """Calcula variaciones diaria, semanal, mensual y anual"""
    if historical_df.empty:
        return None
    
    try:
        # Asumimos que la columna de valor es la última o se llama 'valor'
        # Intentar encontrar la columna numérica
        valor_col = None
        for col in historical_df.columns:
            if historical_df[col].dtype in ['float64', 'int64', 'object']:
                try:
                    historical_df[col] = pd.to_numeric(historical_df[col], errors='coerce')
                    if historical_df[col].notna().any():
                        valor_col = col
                        break
                except:
                    continue
        
        if valor_col is None:
            print("No se encontró columna numérica para calcular variaciones")
            return None
        
        # Ordenar por fecha si existe columna de fecha
        fecha_col = None
        for col in historical_df.columns:
            if 'fecha' in col.lower() or 'date' in col.lower():
                fecha_col = col
                break
        
        if fecha_col:
            historical_df = historical_df.sort_values(fecha_col)
        
        values = historical_df[valor_col].dropna()
        if len(values) < 2:
            return None
        
        # Variación diaria (último vs anterior)
        var_diaria = ((values.iloc[-1] - values.iloc[-2]) / values.iloc[-2] * 100) if len(values) >= 2 else 0
        
        # Variación semanal (último vs hace 7 días aprox)
        var_semanal = ((values.iloc[-1] - values.iloc[-7]) / values.iloc[-7] * 100) if len(values) >= 7 else 0
        
        # Variación mensual (último vs hace 30 días aprox)
        var_mensual = ((values.iloc[-1] - values.iloc[-30]) / values.iloc[-30] * 100) if len(values) >= 30 else 0
        
        # Variación anual (último vs hace 365 días aprox)
        var_anual = ((values.iloc[-1] - values.iloc[-365]) / values.iloc[-365] * 100) if len(values) >= 365 else 0
        
        return {
            'diaria': var_diaria,
            'semanal': var_semanal,
            'mensual': var_mensual,
            'anual': var_anual,
            'valor_actual': values.iloc[-1],
            'valor_anterior': values.iloc[-2] if len(values) >= 2 else None
        }
    except Exception as e:
        print(f"Error al calcular variaciones: {str(e)}")
        return None

def print_variations(variable_name, variations):
    """Imprime las variaciones formateadas"""
    if not variations:
        print(f"{variable_name}: No se pudieron calcular variaciones")
        return
    
    print(f"\n{'='*60}")
    print(f"VARIABLE: {variable_name}")
    print(f"{'='*60}")
    print(f"Valor actual: {variations['valor_actual']}")
    if variations['valor_anterior']:
        print(f"Valor anterior: {variations['valor_anterior']}")
    print(f"{'-'*60}")
    print(f"Variación DIARIA:   {variations['diaria']:+.2f}%")
    print(f"Variación SEMANAL:  {variations['semanal']:+.2f}%")
    print(f"Variación MENSUAL:  {variations['mensual']:+.2f}%")
    print(f"Variación ANUAL:    {variations['anual']:+.2f}%")
    print(f"{'='*60}")

def get_historical_data(serie_id, fecha_desde=None, fecha_hasta=None):
    """Obtiene datos históricos para una serie específica"""
    if not fecha_desde:
        fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime('%Y-%m-%d')
    
    url = "https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables_datos.asp"
    params = {
        'serie': serie_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'primeravez': '1'
    }
    
    try:
        print(f"\nObteniendo datos históricos para serie {serie_id}...")
        response = requests.get(url, params=params, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar la tabla de datos históricos
        table = soup.find('table', {'class': 'table'})
        if table:
            data = []
            rows = table.find_all('tr')
            if not rows:
                print("No se encontraron filas en la tabla de datos históricos")
                return pd.DataFrame()
                
            headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
            print(f"Encabezados encontrados: {headers}")
            
            for row in rows[1:]:
                cols = row.find_all('td')
                if cols:
                    row_data = [col.get_text(strip=True) for col in cols]
                    data.append(row_data)
            
            if data:
                print(f"Se encontraron {len(data)} registros históricos")
                return pd.DataFrame(data, columns=headers)
            else:
                print("No se encontraron datos en la tabla")
                return pd.DataFrame()
        else:
            print("No se encontró la tabla de datos históricos")
            return pd.DataFrame()
    
    except Exception as e:
        print(f"Error al obtener datos históricos: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Ejemplo de uso mejorado
if __name__ == "__main__":
    print("="*70)
    print("CONSULTANDO API DE ESTADÍSTICAS BCRA")
    print("="*70)
    print(f"Token válido hasta: {BCRA_TOKEN_EXPIRATION}")
    print(f"Total de endpoints disponibles: {len(BCRA_ENDPOINTS)}")
    print("="*70)
    
    # Calcular variaciones para todas las variables del API
    print("\nCALCULANDO VARIACIONES PARA TODAS LAS VARIABLES DEL API")
    print("="*70)
    
    for endpoint, descripcion in BCRA_ENDPOINTS.items():
        # Omitir milestones ya que tiene estructura diferente
        if endpoint == "milestones":
            continue
        
        print(f"\nProcesando: {endpoint} - {descripcion}")
        df = get_api_data(endpoint)
        
        if not df.empty:
            variaciones = calculate_variations_from_api(df)
            print_variations(f"{endpoint} - {descripcion}", variaciones)
        else:
            print(f"No se pudieron obtener datos para {endpoint}")
    
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)
    
    # Opción interactiva para ver detalles de una variable específica
    print("\n=== Variables disponibles ===")
    for idx, (endpoint, descripcion) in enumerate(BCRA_ENDPOINTS.items(), 1):
        print(f"{idx}. {endpoint} - {descripcion}")
    
    try:
        opcion = input("\nIngrese el número de la variable para ver datos detallados (o 0 para salir): ")
        if opcion.isdigit() and int(opcion) > 0 and int(opcion) <= len(BCRA_ENDPOINTS):
            idx = int(opcion) - 1
            endpoint = list(BCRA_ENDPOINTS.keys())[idx]
            descripcion = BCRA_ENDPOINTS[endpoint]
            
            print(f"\nObteniendo datos para: {endpoint} - {descripcion}")
            df = get_api_data(endpoint)
            
            if not df.empty:
                print(f"\n=== Datos para {endpoint} ===")
                print(df)
                
                guardar = input("\n¿Desea guardar los datos en un archivo CSV? (s/n): ")
                if guardar.lower() == 's':
                    nombre_archivo = f"bcra_api_{endpoint}_{datetime.now().strftime('%Y%m%d')}.csv"
                    df.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
                    print(f"Datos guardados en {nombre_archivo}")
            else:
                print("No se encontraron datos.")
        else:
            print("Saliendo...")
    except Exception as e:
        print(f"Error: {str(e)}")