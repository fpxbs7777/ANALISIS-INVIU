import requests
import pandas as pd

def obtener_tokens(usuario, contraseña):
    url_token = 'https://api.invertironline.com/token'
    datos = {
        'username': usuario,
        'password': contraseña,
        'grant_type': 'password'
    }
    encabezados = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    respuesta = requests.post(url_token, data=datos, headers=encabezados)
    if respuesta.status_code == 200:
        tokens = respuesta.json()
        return tokens['access_token'], tokens['refresh_token']
    else:
        print(f'Error en la solicitud: {respuesta.status_code}')
        print(respuesta.text)
        return None, None

def refrescar_token(token_refresco):
    url_token = 'https://api.invertironline.com/token'
    datos = {
        'refresh_token': token_refresco,
        'grant_type': 'refresh_token'
    }
    encabezados = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    respuesta = requests.post(url_token, data=datos, headers=encabezados)
    if respuesta.status_code == 200:
        tokens = respuesta.json()
        return tokens['access_token'], tokens['refresh_token']
    else:
        print(f'Error en la solicitud: {respuesta.status_code}')
        print(respuesta.text)
        return None, None

def obtener_encabezado_autorizacion(token_portador):
    return {
        'Authorization': f'Bearer {token_portador}',
        'Content-Type': 'application/json'
    }

def obtener_lista_clientes(token_portador):
    url_clientes = 'https://api.invertironline.com/api/v2/Asesores/Clientes'
    encabezados = obtener_encabezado_autorizacion(token_portador)
    respuesta = requests.get(url_clientes, headers=encabezados)
    if respuesta.status_code == 200:
        return respuesta.json()
    else:
        print(f'Error al obtener la lista de clientes: {respuesta.status_code}')
        print(respuesta.text)
        return []

def seleccionar_cliente(lista_clientes):
    if not lista_clientes:
        print("No hay clientes disponibles.")
        return None
    print("Lista de clientes:")
    for i, cliente in enumerate(lista_clientes):
        print(f"{i + 1}. {cliente['nombre']} - Total Cuenta Valorizado: {cliente['totalCuentaValorizado']}")
    while True:
        try:
            seleccion = int(input("Seleccione un cliente por número: "))
            if 1 <= seleccion <= len(lista_clientes):
                return lista_clientes[seleccion - 1]
            else:
                print("Selección inválida. Intente nuevamente.")
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número.")

def obtener_estado_cuenta(token_portador, id_cliente):
    url_estado_cuenta = f'https://api.invertironline.com/api/v2/Asesores/EstadoDeCuenta/{id_cliente}'
    encabezados = obtener_encabezado_autorizacion(token_portador)
    respuesta = requests.get(url_estado_cuenta, headers=encabezados)
    if respuesta.status_code == 200:
        return respuesta.json()
    else:
        print(f'Error al obtener el estado de cuenta: {respuesta.status_code}')
        print(respuesta.text)
        return None

def obtener_portafolio(token_portador, id_cliente, pais='Argentina'):
    url_portafolio = f'https://api.invertironline.com/api/v2/Asesores/Portafolio/{id_cliente}/{pais}'
    encabezados = obtener_encabezado_autorizacion(token_portador)
    respuesta = requests.get(url_portafolio, headers=encabezados)
    if respuesta.status_code == 200:
        return respuesta.json()
    else:
        print(f'Error al obtener el portafolio: {respuesta.status_code}')
        print(respuesta.text)
        return None

def format_argentino(numero, decimales=2, es_moneda=True):
    """Formatea número en formato argentino: puntos para miles, coma para decimales"""
    if numero is None or numero == '':
        return ''
    try:
        num = float(numero)
        if es_moneda:
            # Formato con separadores
            entero = int(abs(num))
            decimal = abs(num) - entero
            entero_str = f"{entero:,}".replace(",", ".")
            decimal_str = f"{decimal:.{decimales}f}"[1:].replace(".", ",")
            signo = '-' if num < 0 else ''
            return f"{signo}{entero_str}{decimal_str}"
        else:
            return f"{num:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(numero)

def imprimir_portafolio_df(portafolio):
    """Imprime el portafolio en formato DataFrame ordenado"""
    if not portafolio:
        print("No hay datos de portafolio para mostrar")
        return
    
    # La API puede devolver 'activos' o lista directa
    activos = portafolio.get('activos', [])
    if not activos and isinstance(portafolio, list):
        activos = portafolio
    
    # Preparar datos para el DataFrame
    data = []
    for activo in activos:
        # La API de IOL anida los datos del título en un sub-objeto 'titulo'
        titulo = activo.get('titulo', {}) if isinstance(activo, dict) else {}
        
        # Intentar extraer del sub-objeto 'titulo' primero, luego del objeto raíz
        ticker = (titulo.get('simbolo') if titulo else None) or activo.get('simbolo') or activo.get('codigo') or 'N/A'
        descripcion = (titulo.get('descripcion') if titulo else None) or activo.get('descripcion') or ''
        
        cantidad = activo.get('cantidad') or 0
        ultimo_precio = activo.get('ultimoPrecio') or 0
        precio_compra = activo.get('precioPromedioCompra') or 0
        valorizado = activo.get('valorizado') or 0
        variacion_diaria = activo.get('variacionDiaria') or activo.get('variacionPorcentaje') or 0
        ganancia_perdida = activo.get('gananciaPerdida') or 0
        comprometido = activo.get('comprometido') or 0
        
        # Calcular ganancia si no viene en la API
        if not ganancia_perdida and cantidad and precio_compra:
            ganancia_perdida = valorizado - (cantidad * precio_compra)
        
        # Calcular rendimiento porcentaje
        if precio_compra and precio_compra > 0 and ultimo_precio:
            rendimiento_pct = ((ultimo_precio - precio_compra) / precio_compra) * 100
        else:
            rendimiento_pct = 0
        
        data.append({
            'Activo': ticker,
            'Descripción': str(descripcion)[:40] if descripcion else '',
            'Alarmas': '',
            'Cantidad': int(cantidad) if cantidad == int(cantidad) else cantidad,
            'Activos comp.': int(comprometido) if comprometido else 0,
            'Variación diaria': f"{format_argentino(variacion_diaria, 2, False)} %" if variacion_diaria else "0,00 %",
            'Último precio': f"${format_argentino(ultimo_precio, 3)}",
            'Precio promedio compra': f"${format_argentino(precio_compra, 2)}" if precio_compra else "$0,00",
            'Rendimiento %': f"{format_argentino(rendimiento_pct, 2, False)} %",
            'Rendimiento $': f"${format_argentino(ganancia_perdida, 2)}",
            'Valorizado': f"${format_argentino(valorizado, 2)}"
        })
    
    # Agregar efectivo si está disponible en el estado de cuenta
    efectivo_pesos = 0
    efectivo_dolares = 0
    
    # Intentar extraer efectivo de diferentes estructuras posibles
    if isinstance(portafolio, dict):
        efectivo = portafolio.get('efectivo', {})
        if efectivo:
            efectivo_pesos = efectivo.get('pesos', 0)
            efectivo_dolares = efectivo.get('dolares', 0)
    
    if efectivo_pesos:
        data.append({
            'Activo': 'Efectivo',
            'Descripción': 'PESOS - Disponible para operar',
            'Alarmas': '',
            'Cantidad': '',
            'Activos comp.': '',
            'Variación diaria': '',
            'Último precio': '',
            'Precio promedio compra': '',
            'Rendimiento %': '',
            'Rendimiento $': '',
            'Valorizado': f"${format_argentino(efectivo_pesos, 2)}"
        })
    if efectivo_dolares:
        data.append({
            'Activo': 'Efectivo',
            'Descripción': 'DÓLARES - Disponible para operar',
            'Alarmas': '',
            'Cantidad': '',
            'Activos comp.': '',
            'Variación diaria': '',
            'Último precio': '',
            'Precio promedio compra': '',
            'Rendimiento %': '',
            'Rendimiento $': '',
            'Valorizado': f"US$ {format_argentino(efectivo_dolares, 2)}"
        })
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Calcular totales
    total_valorizado = sum(activo.get('valorizado', 0) or 0 for activo in activos)
    total_ganancia = sum(
        (activo.get('gananciaPerdida', 0) or 0) or 
        ((activo.get('valorizado', 0) or 0) - (activo.get('cantidad', 0) or 0) * (activo.get('precioPromedioCompra', 0) or 0))
        for activo in activos
    )
    
    # Agregar fila de total
    if data:
        total_valorizado_con_efectivo = total_valorizado + efectivo_pesos
        total_row = {
            'Activo': 'Total',
            'Descripción': '',
            'Alarmas': '',
            'Cantidad': '',
            'Activos comp.': '',
            'Variación diaria': '',
            'Último precio': '',
            'Precio promedio compra': '',
            'Rendimiento %': '',
            'Rendimiento $': f"${format_argentino(total_ganancia, 2)}",
            'Valorizado': f"${format_argentino(total_valorizado_con_efectivo, 2)}"
        }
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    
    # Configurar opciones de display de pandas para ancho completo
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 40)
    
    # Imprimir con formato
    print("\n" + "="*140)
    print("PORTAFOLIO - Resumen Argentina".center(140))
    print("="*140)
    print(df.to_string(index=False))
    print("="*140)
    
    # Mostrar totales adicionales
    print(f"\nTotal Valorizado: ${format_argentino(total_valorizado_con_efectivo, 2)}")
    if efectivo_dolares:
        print(f"Efectivo en USD: US$ {format_argentino(efectivo_dolares, 2)}")
    
    return df

# Credenciales de usuario
usuario = 'boosandr97@gmail.com'
contraseña = 'Chule248936_'

# Obtener los tokens
token_portador, token_refresco = obtener_tokens(usuario, contraseña)
if token_portador and token_refresco:
    # Refrescar el token cuando expire
    token_portador, token_refresco = refrescar_token(token_refresco)

# Exportar el token_portador
productor_token = token_portador

# Obtener la lista de clientes
lista_clientes = obtener_lista_clientes(token_portador)
cliente_seleccionado = seleccionar_cliente(lista_clientes)
if cliente_seleccionado:
    print(f"Cliente seleccionado: {cliente_seleccionado['nombre']} (ID: {cliente_seleccionado['id']})")
    
    # Obtener el estado de cuenta del cliente seleccionado
    estado_cuenta = obtener_estado_cuenta(token_portador, cliente_seleccionado['id'])
    if estado_cuenta:
        print("Estado de Cuenta:")
        print(estado_cuenta)
    
    # Obtener el portafolio del cliente seleccionado
    portafolio = obtener_portafolio(token_portador, cliente_seleccionado['id'])
    if portafolio:
        df_portafolio = imprimir_portafolio_df(portafolio)