import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import scipy.optimize as optimize

# Credenciales desde variables de entorno
username = os.environ.get("IOL_USERNAME", "")
password = os.environ.get("IOL_PASSWORD", "")

def obtener_tokens(user, pwd):
    """Obtiene el bearer token de la API de IOL."""
    token_url = 'https://api.invertironline.com/token'
    payload = {
        'username': user,
        'password': pwd,
        'grant_type': 'password'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(token_url, data=payload, headers=headers)
    
    if response.status_code == 200:
        tokens = response.json()
        return tokens['access_token']
    else:
        raise Exception(f'Error al obtener tokens: {response.text}')

def obtener_precio_actual(simbolo, mercado, bearer_token):
    """Obtiene el último precio operado de un título específico."""
    url = f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('ultimoPrecio')
    else:
        raise Exception(f"Error al obtener cotización: {response.status_code} - {response.text}")

def obtener_tipo_cambio_oficial():
    """Obtiene el tipo de cambio oficial actual desde ArgentinaDatos API."""
    url = "https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # La API devuelve un array, tomamos el último valor
            if isinstance(data, list) and len(data) > 0:
                return data[-1].get('venta')  # Usamos precio de venta
        return None
    except Exception as e:
        print(f"Error al obtener tipo de cambio oficial: {e}")
        return None

def proyectar_tipo_cambio(tasa_actual, fecha_actual, fecha_objetivo, tasa_proyeccion_anual=0.30):
    """
    Proyecta el tipo de cambio a una fecha futura usando una tasa de devaluación anual.
    Por defecto usa 30% anual como estimación conservadora.
    """
    dias = (fecha_objetivo - fecha_actual).days
    anios = dias / 365.0
    tasa_proyectada = tasa_actual * ((1 + tasa_proyeccion_anual) ** anios)
    return tasa_proyectada

def ajustar_flujos_dollar_linked(flujos, tipo_cambio_actual, fecha_actual, tasa_proyeccion_anual=0.30):
    """
    Ajusta los flujos de bonos Dollar-Linked proyectando el tipo de cambio oficial
    a la fecha de cada flujo y convirtiendo el monto nominal a pesos.
    """
    flujos_ajustados = []
    for flujo in flujos:
        fecha_flujo = datetime.strptime(flujo['fecha'], '%Y-%m-%d').date()
        if fecha_flujo > fecha_actual:
            tc_proyectado = proyectar_tipo_cambio(tipo_cambio_actual, fecha_actual, fecha_flujo, tasa_proyeccion_anual)
            monto_ars = flujo['monto'] * tc_proyectado
            flujos_ajustados.append({
                'fecha': fecha_flujo,
                'monto': monto_ars,
                'monto_original_usd': flujo['monto'],
                'tc_proyectado': tc_proyectado
            })
    return flujos_ajustados

def calcular_tir(flujos, precio_actual, fecha_actual):
    """
    Calcula la TIR (XIRR) basándose en los flujos futuros y el precio actual.
    Utiliza el método de Newton-Raphson para encontrar la raíz.
    """
    # Filtrar solo los flujos futuros
    flujos_futuros = [f for f in flujos if f['fecha'] > fecha_actual]
    
    if not flujos_futuros:
        return None
    
    # Agregar el precio de compra (flujo negativo) en la fecha actual
    fechas = [fecha_actual] + [f['fecha'] for f in flujos_futuros]
    montos = [-precio_actual] + [f['monto'] for f in flujos_futuros]
    
    def npv(tir):
        total_npv = 0.0
        for fecha, monto in zip(fechas, montos):
            dias = (fecha - fecha_actual).days
            # Evitar TIR <= -1 para que no arroje error matemático
            if tir <= -1.0:
                return float('inf')
            total_npv += monto / ((1 + tir) ** (dias / 365.0))
        return total_npv

    # Buscar la TIR iterando. Se pasa un estimado inicial del 15% (0.15)
    try:
        tir_calculada = optimize.newton(npv, 0.15)
        return tir_calculada
    except RuntimeError:
        return None

if __name__ == '__main__':
    try:
        # 1. Cargar configuración de bonos
        print("Cargando configuración de bonos...")
        with open('bonos.json', 'r', encoding='utf-8') as f:
            base_bonos = json.load(f)
        
        # 2. Autenticación
        print("Obteniendo token de acceso...")
        token = obtener_tokens(username, password)
        
        # 3. Obtener tipo de cambio oficial actual
        print("Obteniendo tipo de cambio oficial...")
        tc_oficial = obtener_tipo_cambio_oficial()
        if tc_oficial:
            print(f"Tipo de cambio oficial actual: ARS {tc_oficial:.2f}")
        else:
            print("⚠️ No se pudo obtener el tipo de cambio oficial. Usando estimación.")
            tc_oficial = 1000.0  # Valor fallback
        
        fecha_hoy = datetime.now().date()
        resultados = []
        
        # 4. Procesar cada bono del JSON
        for clave, datos in base_bonos.items():
            ticker = datos['ticker_api']
            mercado = datos['mercado']
            tipo = datos['tipo']
            flujos_json = datos['flujos_futuros_cada_100_vn']
            
            print(f"\nAnalizando {ticker} ({tipo})...")
            precio = obtener_precio_actual(ticker, mercado, token)
            
            if not precio:
                print(f"⚠️ No se pudo obtener liquidez/precio para {ticker}.")
                continue
            
            # Convertir flujos JSON a formato interno
            flujos = []
            for f in flujos_json:
                fecha_flujo = datetime.strptime(f['fecha'], '%Y-%m-%d').date()
                flujos.append({'fecha': fecha_flujo, 'monto': f['monto']})
            
            # Ajustar flujos para Dollar-Linked
            if tipo == 'Dollar-Linked':
                print(f"  Ajustando flujos por proyección de tipo de cambio (tasa anual: 30%)...")
                flujos = ajustar_flujos_dollar_linked(flujos_json, tc_oficial, fecha_hoy, tasa_proyeccion_anual=0.30)
                print(f"  Precio en ARS: {precio:.2f}")
                for f in flujos:
                    print(f"    Flujo {f['fecha']}: ARS {f['monto']:.2f} (USD {f['monto_original_usd']:.2f} @ TC {f['tc_proyectado']:.2f})")
            else:
                print(f"  Precio en USD: {precio:.2f}")
            
            # Calcular TIR
            tir = calcular_tir(flujos, precio, fecha_hoy)
            
            if tir is not None:
                tir_formateada = f"{tir * 100:.2f}%"
                moneda = "ARS" if tipo == "Dollar-Linked" else "USD"
                resultados.append({
                    "Ticker": ticker,
                    "Tipo": tipo,
                    "Precio": precio,
                    "Moneda": moneda,
                    "TIR (TEA)": tir_formateada
                })
            else:
                print(f"  ⚠️ Error de cálculo de TIR para {ticker}")
        
        # 5. Mostrar Resultados Finales en tabla
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            print("\n" + "="*50)
            print("REPORTE DE RENDIMIENTOS")
            print("="*50)
            print(df_resultados.to_string(index=False))
            print("="*50)
        else:
            print("\nNo se obtuvieron resultados para ningún bono.")

    except Exception as e:
        print(f"\nError fatal en la ejecución: {e}")
        import traceback
        traceback.print_exc()