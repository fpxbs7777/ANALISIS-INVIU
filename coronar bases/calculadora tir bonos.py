# -*- coding: utf-8 -*-
"""
Calculadora de TIR para Títulos Públicos
Calcula la Tasa Interna de Retorno (TIR) de títulos públicos argentinos
usando datos de la API de InvertirOnline

Archivo independiente - incluye todas las funciones necesarias
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# ============================================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================================

def obtener_tokens(usuario, contraseña):
    """
    Obtiene los tokens de autenticación de la API de InvertirOnline
    
    Args:
        usuario: Usuario de InvertirOnline
        contraseña: Contraseña de InvertirOnline
    
    Returns:
        tuple: (access_token, refresh_token) o (None, None) si hay error
    """
    url_token = 'https://api.invertironline.com/token'
    datos = {
        'username': usuario,
        'password': contraseña,
        'grant_type': 'password'
    }
    encabezados = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        respuesta = requests.post(url_token, data=datos, headers=encabezados)
        if respuesta.status_code == 200:
            tokens = respuesta.json()
            return tokens.get('access_token'), tokens.get('refresh_token')
        else:
            print(f'Error en la solicitud de tokens: {respuesta.status_code}')
            print(respuesta.text)
            return None, None
    except Exception as e:
        print(f'Error al obtener tokens: {str(e)}')
        return None, None

def refrescar_token(refresh_token):
    """
    Refresca el token de acceso usando el refresh token
    
    Args:
        refresh_token: Token de refresco
    
    Returns:
        tuple: (access_token, refresh_token) o (None, None) si hay error
    """
    url_token = 'https://api.invertironline.com/token'
    datos = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    encabezados = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        respuesta = requests.post(url_token, data=datos, headers=encabezados)
        if respuesta.status_code == 200:
            tokens = respuesta.json()
            return tokens.get('access_token'), tokens.get('refresh_token')
        else:
            print(f'Error al refrescar token: {respuesta.status_code}')
            return None, None
    except Exception as e:
        print(f'Error al refrescar token: {str(e)}')
        return None, None

# ============================================================================
# FUNCIONES DE OBTENCIÓN DE DATOS
# ============================================================================

def obtener_cotizacion_bono(simbolo, mercado='BCBA', bearer_token=None):
    """Obtiene la cotización actual del bono"""
    url = f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener cotización: {response.status_code}")
        print(response.text)
        return None

def obtener_serie_historica(simbolo, mercado, fecha_desde, fecha_hasta, ajustada, bearer_token):
    """Obtiene la serie histórica del bono"""
    url = f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{fecha_desde}/{fecha_hasta}/{ajustada}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error en la solicitud de serie histórica: {response.status_code}")
        return None

# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_dias_30_360(fecha_desde, fecha_hasta):
    """Calcula días según convención 30/360"""
    d1, m1, y1 = fecha_desde.day, fecha_desde.month, fecha_desde.year
    d2, m2, y2 = fecha_hasta.day, fecha_hasta.month, fecha_hasta.year
    
    # Ajuste para días 31
    if d1 == 31:
        d1 = 30
    if d2 == 31:
        d2 = 30
    
    return (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)

def obtener_tasa_vigente(estructura_bono, fecha):
    """Obtiene la tasa anual vigente para una fecha dada"""
    estructura_tasas = estructura_bono.get('estructura_tasas', [])
    if not estructura_tasas:
        # Si no hay estructura de tasas, retornar 0
        return 0.0
    
    for periodo in estructura_tasas:
        fecha_desde = datetime.strptime(periodo['fecha_desde'], '%Y-%m-%d')
        fecha_hasta = datetime.strptime(periodo['fecha_hasta'], '%Y-%m-%d')
        if fecha_desde <= fecha < fecha_hasta:
            return periodo['tasa_anual']
    # Si no encuentra, usar la última tasa
    return estructura_tasas[-1]['tasa_anual']

def calcular_flujos_fondos(estructura_bono, fecha_actual, precio_compra, valor_nominal=100, precio_en_usd=False):
    """
    Calcula los flujos de fondos del bono sobre una base unitaria de VN = 100
    precio_compra: precio de cotización
    valor_nominal: valor nominal base = 100 (NUNCA usar el monto emitido total)
    precio_en_usd: True si el precio ya viene en USD (AL30D), False si viene en pesos (AL30)
    
    Returns:
        tuple: (flujos, capital_vigente_actual) donde capital_vigente_actual es el valor residual
    """
    if estructura_bono is None:
        raise ValueError("estructura_bono no puede ser None")
    
    # Validar que existan los campos necesarios
    if 'calendario_cupones' not in estructura_bono and 'calendario_amortizaciones' not in estructura_bono:
        raise ValueError("La estructura del bono debe tener al menos 'calendario_cupones' o 'calendario_amortizaciones'")
    
    flujos = []
    
    # Interpretar precio según la moneda
    if precio_en_usd:
        # AL30D: precio ya viene en USD por cada 100 nominales (ej: 64.72 USD)
        precio_unitario = precio_compra
    else:
        # AL30: precio viene en pesos, dividir por 1000 (ej: 95270 -> 95.27 ARS)
        precio_unitario = precio_compra / 1000.0
    
    # Flujo inicial: compra del bono (negativo)
    # IMPORTANTE: Si la paridad es menor (ej: 50%), pagas menos (ej: $50), 
    # entonces el flujo inicial es menos negativo (ej: -$50 en lugar de -$100)
    # El flujo siempre es negativo porque es una salida de dinero, pero su magnitud
    # debe reflejar el precio pagado, no el valor nominal
    flujos.append({
        'fecha': fecha_actual,
        'dias_desde_actual': 0,
        'tipo': 'compra',
        'monto': -precio_unitario,  # Negativo porque es salida de dinero
        'capital_vigente': valor_nominal
    })
    
    # Determinar qué amortizaciones ya pasaron
    # Algunos bonos no tienen calendario_amortizaciones (bonos bullet)
    amortizaciones_pasadas = []
    calendario_amort = estructura_bono.get('calendario_amortizaciones', [])
    if calendario_amort:
        for amortizacion in calendario_amort:
            fecha_amort = datetime.strptime(amortizacion['fecha_pago'], '%Y-%m-%d')
            if fecha_amort <= fecha_actual:
                amortizaciones_pasadas.append(amortizacion)
    
    # Calcular capital vigente actual (restando amortizaciones ya pagadas)
    capital_actual = valor_nominal
    for amortizacion in sorted(amortizaciones_pasadas, key=lambda x: x['fecha_pago']):
        monto_amort = valor_nominal * (amortizacion['porcentaje_capital'] / 100)
        capital_actual -= monto_amort
    
    # Guardar el valor residual ANTES de procesar eventos futuros
    # Este es el capital vigente actual sobre el cual se calcula la paridad
    valor_residual = capital_actual
    
    # Crear lista de eventos futuros (cupones y amortizaciones)
    eventos = []
    
    # Agregar cupones futuros (solo uno por fecha)
    cupones_por_fecha = {}
    calendario_cupones = estructura_bono.get('calendario_cupones', [])
    if calendario_cupones:
        for cupon in calendario_cupones:
            fecha_cupon = datetime.strptime(cupon['fecha_pago'], '%Y-%m-%d')
            if fecha_cupon > fecha_actual:
                fecha_str = fecha_cupon.strftime('%Y-%m-%d')
                if fecha_str not in cupones_por_fecha:
                    cupones_por_fecha[fecha_str] = cupon
    
    # Agregar amortizaciones futuras
    calendario_amort = estructura_bono.get('calendario_amortizaciones', [])
    if calendario_amort:
        for amortizacion in calendario_amort:
            fecha_amort = datetime.strptime(amortizacion['fecha_pago'], '%Y-%m-%d')
            if fecha_amort > fecha_actual:
                fecha_str = fecha_amort.strftime('%Y-%m-%d')
                eventos.append({
                    'fecha': fecha_amort,
                    'tipo': 'amortizacion',
                    'porcentaje': amortizacion['porcentaje_capital'],
                    'numero': amortizacion['numero_cuota']
                })
    else:
        # Bono bullet: agregar amortización final al vencimiento
        fecha_vencimiento_str = estructura_bono.get('fecha_vencimiento')
        if fecha_vencimiento_str:
            fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d')
            if fecha_vencimiento > fecha_actual:
                eventos.append({
                    'fecha': fecha_vencimiento,
                    'tipo': 'amortizacion',
                    'porcentaje': 100.0,  # 100% del capital al vencimiento
                    'numero': 1
                })
    
    # Consolidar eventos por fecha (evitar duplicados)
    eventos_consolidados = {}
    
    # Agregar amortizaciones
    for evento in eventos:
        if evento['tipo'] == 'amortizacion':
            fecha_str = evento['fecha'].strftime('%Y-%m-%d')
            eventos_consolidados[fecha_str] = {
                'fecha': evento['fecha'],
                'amortizacion': evento,
                'cupon': None
            }
    
    # Agregar cupones (solo si no hay amortización en esa fecha)
    for fecha_str, cupon in cupones_por_fecha.items():
        fecha_cupon = datetime.strptime(cupon['fecha_pago'], '%Y-%m-%d')
        fecha_str = fecha_cupon.strftime('%Y-%m-%d')
        if fecha_str in eventos_consolidados:
            # Ya hay amortización en esta fecha, agregar cupón ahí
            eventos_consolidados[fecha_str]['cupon'] = cupon
        else:
            # Solo cupón, sin amortización
            eventos_consolidados[fecha_str] = {
                'fecha': fecha_cupon,
                'amortizacion': None,
                'cupon': cupon
            }
    
    # Ordenar eventos por fecha
    fechas_ordenadas = sorted(eventos_consolidados.keys())
    
    # Calcular flujos
    fecha_anterior = fecha_actual
    
    for fecha_str in fechas_ordenadas:
        evento_consolidado = eventos_consolidados[fecha_str]
        fecha_evento = evento_consolidado['fecha']
        dias_desde_actual = (fecha_evento - fecha_actual).days
        dias_periodo = calcular_dias_30_360(fecha_anterior, fecha_evento)
        
        # Procesar cupón (si existe)
        if evento_consolidado['cupon']:
            cupon = evento_consolidado['cupon']
            tasa_anual = obtener_tasa_vigente(estructura_bono, fecha_evento)
            monto_cupon = capital_actual * tasa_anual * (cupon['dias'] / 360)
            
            flujos.append({
                'fecha': fecha_evento,
                'dias_desde_actual': dias_desde_actual,
                'tipo': 'cupon',
                'monto': monto_cupon,
                'capital_vigente': capital_actual,
                'numero_cupon': cupon['numero_cupon']
            })
        
        # Procesar amortización (si existe)
        if evento_consolidado['amortizacion']:
            amortizacion = evento_consolidado['amortizacion']
            # Los porcentajes son sobre el capital ORIGINAL (valor_nominal), no sobre el capital vigente
            monto_amortizacion = valor_nominal * (amortizacion['porcentaje'] / 100)
            
            flujos.append({
                'fecha': fecha_evento,
                'dias_desde_actual': dias_desde_actual,
                'tipo': 'amortizacion',
                'monto': monto_amortizacion,
                'capital_vigente': capital_actual,
                'numero_cuota': amortizacion['numero']
            })
            
            # Reducir capital después de la amortización
            capital_actual -= monto_amortizacion
        
        fecha_anterior = fecha_evento
    
    # Retornar flujos y valor residual (capital vigente actual ANTES de procesar eventos futuros)
    return flujos, valor_residual

def calcular_tir(flujos):
    """Calcula la TIR usando método de bisección mejorado"""
    # Extraer montos y días
    montos = np.array([f['monto'] for f in flujos])
    dias = np.array([f['dias_desde_actual'] for f in flujos])
    
    # Convertir días a años (usando 360 días por año)
    años = dias / 360.0
    
    def van(tir_anual):
        """Valor Actual Neto para una TIR anual"""
        if tir_anual <= -1:
            return float('inf')
        return np.sum(montos / ((1 + tir_anual) ** años))
    
    # Buscar rango inicial
    tir_min = -0.99
    tir_max = 5.0  # 500% anual como máximo razonable
    
    # Verificar que hay cambio de signo
    van_min = van(tir_min)
    van_max = van(tir_max)
    
    if van_min * van_max > 0:
        # No hay cambio de signo, intentar ampliar rango
        tir_max = 10.0
        van_max = van(tir_max)
        if van_min * van_max > 0:
            return None  # No se puede calcular
    
    # Método de bisección
    precision = 1e-8
    max_iter = 200
    
    for i in range(max_iter):
        tir_medio = (tir_min + tir_max) / 2
        van_medio = van(tir_medio)
        
        if abs(van_medio) < precision:
            return tir_medio * 100  # Retornar en porcentaje
        
        if van_medio * van_min < 0:
            tir_max = tir_medio
            van_max = van_medio
        else:
            tir_min = tir_medio
            van_min = van_medio
    
    # Retornar el valor medio si no converge exactamente
    tir_medio = (tir_min + tir_max) / 2
    return tir_medio * 100

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    # Credenciales
    usuario = 'boosandr97@gmail.com'
    contraseña = 'Olivia12102016_'
    
    # Obtener tokens
    print("Obteniendo tokens de autenticación...")
    token_portador, token_refresco = obtener_tokens(usuario, contraseña)
    if not token_portador or not token_refresco:
        raise Exception('Error al obtener los tokens')
    
    # Usar token_portador como bearer_token
    bearer_token = token_portador
    print("✓ Tokens obtenidos correctamente\n")
    
    # Cargar estructura del bono
    # Intentar diferentes rutas posibles para el archivo JSON
    archivo_estructura = None
    posibles_rutas = [
        'AL30_estructura.json',
        'estructura_bonos.json',
        os.path.join(os.path.dirname(__file__), 'AL30_estructura.json'),
        os.path.join(os.path.dirname(__file__), 'estructura_bonos.json'),
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            archivo_estructura = ruta
            break
    
    if not archivo_estructura:
        print("⚠️ ADVERTENCIA: No se encontró el archivo de estructura del bono")
        print("   Buscado en:", posibles_rutas)
        print("   Continuando sin estructura...")
        estructura_al30 = None
    else:
        print(f"Cargando estructura del bono desde: {archivo_estructura}")
        with open(archivo_estructura, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
        
        # El JSON puede tener estructura {"bonos": {"AL30": {...}}} o ser directamente el bono
        if 'bonos' in datos_json:
            # Buscar AL30 o AL30D en la sección de bonos
            bonos = datos_json['bonos']
            if 'AL30' in bonos:
                estructura_al30 = bonos['AL30']
            elif 'AL30D' in bonos:
                estructura_al30 = bonos['AL30D']
            else:
                # Tomar el primer bono disponible
                estructura_al30 = list(bonos.values())[0] if bonos else None
        elif 'obligaciones_negociables' in datos_json:
            # Si está en obligaciones negociables, tomar el primero
            on = datos_json['obligaciones_negociables']
            estructura_al30 = list(on.values())[0] if on else None
        else:
            # Asumir que es directamente la estructura del bono
            estructura_al30 = datos_json
        
        if estructura_al30:
            print("✓ Estructura cargada correctamente\n")
        else:
            print("⚠️ No se pudo extraer la estructura del bono del JSON\n")
    
    # Obtener cotización actual del AL30D (cotiza en USD)
    print("Obteniendo cotización del AL30D (USD)...")
    cotizacion = obtener_cotizacion_bono('AL30D', 'BCBA', bearer_token)
    
    # Si no hay AL30D, intentar con AL30 pero advertir
    if not cotizacion or cotizacion.get('moneda') != 'dolar_Estadounidense':
        print("⚠️ AL30D no disponible, intentando con AL30 (pesos)...")
        cotizacion = obtener_cotizacion_bono('AL30', 'BCBA', bearer_token)
        if cotizacion:
            print("⚠️ ADVERTENCIA: AL30 cotiza en pesos, necesitarás tipo de cambio para calcular TIR en USD")
    
    if cotizacion and estructura_al30:
        print(f"\nCotización obtenida:")
        print(json.dumps(cotizacion, indent=2, ensure_ascii=False))
        
        # Extraer precio (puede estar en diferentes campos según la API)
        precio_ultimo = None
        if 'ultimoPrecio' in cotizacion:
            precio_ultimo = cotizacion['ultimoPrecio']
        elif 'precio' in cotizacion:
            precio_ultimo = cotizacion['precio']
        elif 'precioUltimoCierre' in cotizacion:
            precio_ultimo = cotizacion['precioUltimoCierre']
        
        if precio_ultimo:
            print(f"\nPrecio de cotización: ${precio_ultimo}")
            moneda = cotizacion.get('moneda', 'N/A')
            print(f"Moneda: {moneda}")
            
            # Fecha actual
            fecha_actual = datetime.now()
            
            # Valor nominal siempre es 100 USD (base unitaria)
            valor_nominal = 100  # NUNCA usar el monto emitido total
            
            # Interpretar precio según la moneda
            precio_en_usd = (moneda == 'dolar_Estadounidense' or 'AL30D' in cotizacion.get('descripcionTitulo', ''))
            
            if precio_en_usd:
                # AL30D cotiza en USD, precio ya viene en USD por cada 100 nominales
                # Ejemplo: 64.72 significa 64.72 USD por cada VN 100
                precio_interpretado = precio_ultimo  # Ya está en USD, no dividir
                print(f"\nCalculando flujos de fondos en USD (base: VN = {valor_nominal} USD)...")
                print(f"Precio de cotización (por cada VN 100 USD): {precio_interpretado:.2f} USD")
            else:
                # AL30 cotiza en pesos, necesitaríamos tipo de cambio
                precio_interpretado = precio_ultimo / 1000.0  # Ej: 95280 -> 95.28 ARS
                print(f"\nADVERTENCIA: Precio en pesos ({precio_interpretado:.2f} ARS)")
                print("Para calcular TIR en USD, necesitarías el tipo de cambio CCL")
                print("Usando precio en pesos directamente (TIR será inconsistente)")
            
            flujos, valor_residual = calcular_flujos_fondos(estructura_al30, fecha_actual, precio_ultimo, valor_nominal=valor_nominal, precio_en_usd=precio_en_usd)
            
            # Mostrar flujos
            print(f"\nTotal de flujos: {len(flujos)}")
            print(f"Valor residual (capital vigente actual): {valor_residual:.2f}")
            
            if valor_residual == 0:
                print("⚠️ ADVERTENCIA: El valor residual es cero.")
                print("   Esto puede ocurrir si:")
                print("   - El bono ya venció y todas las amortizaciones se pagaron")
                print("   - Todas las amortizaciones programadas ya se ejecutaron")
                print("   - Se usará el valor nominal original para calcular la paridad")
            print("\nPrimeros 10 flujos:")
            for i, flujo in enumerate(flujos[:10]):
                print(f"{i+1}. {flujo['fecha'].strftime('%Y-%m-%d')} | "
                      f"{flujo['tipo']:12} | "
                      f"${flujo['monto']:>15,.2f} | "
                      f"Días: {flujo['dias_desde_actual']}")
            
            # Calcular TIR
            print("\nCalculando TIR...")
            tir = calcular_tir(flujos)
            
            if tir is not None:
                # Calcular paridad sobre el valor residual (capital vigente actual)
                # Si el valor residual es cero (bono totalmente amortizado), usar valor nominal
                if valor_residual > 0:
                    paridad = (precio_interpretado / valor_residual) * 100
                    base_paridad = valor_residual
                    tipo_base = "Valor Residual"
                else:
                    # Si el valor residual es cero, el bono ya está totalmente amortizado
                    # Usar valor nominal como referencia
                    paridad = (precio_interpretado / valor_nominal) * 100
                    base_paridad = valor_nominal
                    tipo_base = "Valor Nominal (bono totalmente amortizado)"
                
                print(f"\n{'='*60}")
                print(f"TIR del AL30D: {tir:.4f}% anual")
                print(f"Paridad: {paridad:.2f}% (Precio: {precio_interpretado:.2f} USD / {tipo_base}: {base_paridad:.2f} USD)")
                print(f"Valor Residual: {valor_residual:.2f} USD")
                print(f"Valor Nominal Original: {valor_nominal} USD")
                print(f"{'='*60}")
            else:
                print(f"\n{'='*60}")
                print("ADVERTENCIA: No se pudo calcular la TIR (verificar flujos)")
                print(f"{'='*60}")
            
            # Crear DataFrame con flujos para análisis
            df_flujos = pd.DataFrame(flujos)
            flujo_inicial = df_flujos[df_flujos['tipo']=='compra']['monto'].sum()
            
            # Validar consistencia entre paridad y flujo inicial
            if tir is not None:
                # Calcular paridad (usar valor residual si > 0, sino valor nominal)
                if valor_residual > 0:
                    paridad = (precio_interpretado / valor_residual) * 100
                    base_paridad = valor_residual
                    tipo_base = "valor residual"
                else:
                    paridad = (precio_interpretado / valor_nominal) * 100
                    base_paridad = valor_nominal
                    tipo_base = "valor nominal (bono totalmente amortizado)"
                
                flujo_esperado = -precio_interpretado
                
                print("\nResumen de flujos:")
                print(f"Flujo inicial (compra): ${flujo_inicial:,.2f}")
                print(f"Paridad sobre {tipo_base}: {paridad:.2f}%")
                print(f"Valor residual (capital vigente): ${valor_residual:.2f}")
                print(f"Valor nominal original: ${valor_nominal:.2f}")
                
                if valor_residual == 0:
                    print("⚠️ ADVERTENCIA: El bono está totalmente amortizado (valor residual = 0)")
                    print("   La paridad se calcula sobre el valor nominal original como referencia.")
                
                # Verificar consistencia
                if abs(flujo_inicial - flujo_esperado) > 0.01:
                    print(f"⚠️ ADVERTENCIA: Inconsistencia detectada!")
                    print(f"   Flujo inicial calculado: ${flujo_inicial:,.2f}")
                    print(f"   Flujo esperado (basado en precio): ${flujo_esperado:,.2f}")
                else:
                    print(f"✓ Flujo inicial consistente con paridad {paridad:.2f}%")
                
                # Explicación sobre paridad y flujo
                if valor_residual > 0:
                    if paridad < 100:
                        print(f"\nNota: Paridad {paridad:.2f}% significa que compras a descuento sobre el valor residual.")
                        print(f"      Pagas ${precio_interpretado:.2f} por cada ${valor_residual:.2f} de valor residual.")
                        print(f"      El flujo inicial negativo (${flujo_inicial:,.2f}) es correcto: representa el pago.")
                    elif paridad > 100:
                        print(f"\nNota: Paridad {paridad:.2f}% significa que compras con prima sobre el valor residual.")
                        print(f"      Pagas ${precio_interpretado:.2f} por cada ${valor_residual:.2f} de valor residual.")
                        print(f"      El flujo inicial negativo (${flujo_inicial:,.2f}) es correcto: representa el pago.")
                    else:
                        print(f"\nNota: Paridad {paridad:.2f}% significa que compras a la par del valor residual.")
                        print(f"      Pagas ${precio_interpretado:.2f} por cada ${valor_residual:.2f} de valor residual.")
                else:
                    print(f"\nNota: El bono está totalmente amortizado. La paridad se calcula sobre el valor nominal original como referencia.")
            
            print(f"\nTotal cupones: ${df_flujos[df_flujos['tipo']=='cupon']['monto'].sum():,.2f}")
            print(f"Total amortizaciones: ${df_flujos[df_flujos['tipo']=='amortizacion']['monto'].sum():,.2f}")
            print(f"Flujo neto total: ${df_flujos['monto'].sum():,.2f}")
            
        else:
            print("No se pudo extraer el precio de la cotización")
    else:
        if not cotizacion:
            print("No se pudo obtener la cotización del bono")
        if not estructura_al30:
            print("No se pudo cargar la estructura del bono")
    
    # Obtener serie histórica para análisis adicional
    print("\n\nObteniendo serie histórica del AL30D...")
    fecha_desde = '2024-01-01'
    fecha_hasta = datetime.now().strftime('%Y-%m-%d')
    serie_historica = obtener_serie_historica('AL30D', 'BCBA', fecha_desde, fecha_hasta, 'SinAjustar', bearer_token)
    
    if serie_historica:
        df_serie = pd.DataFrame(serie_historica)
        if not df_serie.empty:
            print(f"\nSerie histórica obtenida: {len(df_serie)} registros")
            print("\nÚltimos 5 registros:")
            print(df_serie.tail())
            
            # Calcular estadísticas
            if 'precioCierre' in df_serie.columns or 'cierre' in df_serie.columns:
                col_precio = 'precioCierre' if 'precioCierre' in df_serie.columns else 'cierre'
                print(f"\nEstadísticas de precios:")
                print(f"Precio mínimo: ${df_serie[col_precio].min():,.2f}")
                print(f"Precio máximo: ${df_serie[col_precio].max():,.2f}")
                print(f"Precio promedio: ${df_serie[col_precio].mean():,.2f}")
        else:
            print("La serie histórica está vacía")
    else:
        print("No se pudo obtener la serie histórica")