import requests
import pandas as pd
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORONAR = os.path.join(_HERE, "clarity-dashboard-main6", "coronar bases")
if os.path.isdir(_CORONAR):
    sys.path.insert(0, _CORONAR)

from tokens import obtener_tokens, refrescar_token

# Carga .env manualmente si existe (misma carpeta)
_env_path = os.path.join(_HERE, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as f:
        for _line in f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                k, v = _line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

username = os.environ.get("IOL_USERNAME", "")
password = os.environ.get("IOL_PASSWORD", "")

bearer_token, refresh_token = obtener_tokens(username, password)
if not bearer_token or not refresh_token:
    raise Exception('Error al obtener los tokens de IOL. Verificá las variables IOL_USERNAME / IOL_PASSWORD.')

_headers = lambda: {
    'Accept': 'application/json',
    'Authorization': f'Bearer {bearer_token}'
}

def _get(url, params=None):
    r = requests.get(url, headers=_headers(), params=params)
    if r.status_code == 200:
        return r.json()
    print(f'Error GET {url}: {r.status_code} {r.text}')
    return None

def _post(url, data=None):
    r = requests.post(url, headers={**_headers(), 'Content-Type': 'application/json'}, json=data)
    if r.status_code == 200:
        return r.json()
    print(f'Error POST {url}: {r.status_code} {r.text}')
    return None

# ─── Cotizaciones ──────────────────────────────────────────────────────────

def cotizaciones_todos(instrumento, pais):
    return _get(f"https://api.invertironline.com/api/v2/Cotizaciones/{instrumento}/{pais}/Todos",
                params={f"cotizacionInstrumentoModel.instrumento": instrumento,
                        f"cotizacionInstrumentoModel.pais": pais})

def cotizaciones_panel(instrumento, panel, pais):
    return _get(f"https://api.invertironline.com/api/v2/Cotizaciones/{instrumento}/{panel}/{pais}",
                params={f"panelCotizacion.instrumento": instrumento,
                        f"panelCotizacion.panel": panel,
                        f"panelCotizacion.pais": pais})

def cotizaciones_mep(simbolo):
    return _get(f"https://api.invertironline.com/api/v2/Cotizaciones/MEP/{simbolo}")

def cotizaciones_mep_post(simbolo, id_plazo_compra=0, id_plazo_venta=0):
    return _post("https://api.invertironline.com/api/v2/Cotizaciones/MEP",
                 data={"simbolo": simbolo, "idPlazoOperatoriaCompra": id_plazo_compra, "idPlazoOperatoriaVenta": id_plazo_venta})

def cotizaciones_orleans_todos(instrumento, pais):
    return _get(f"https://api.invertironline.com/api/v2/cotizaciones-orleans/{instrumento}/{pais}/Todos",
                params={f"cotizacionInstrumentoModel.instrumento": instrumento,
                        f"cotizacionInstrumentoModel.pais": pais})

def cotizaciones_orleans_operables(instrumento, pais):
    return _get(f"https://api.invertironline.com/api/v2/cotizaciones-orleans/{instrumento}/{pais}/Operables",
                params={f"cotizacionInstrumentoModel.instrumento": instrumento,
                        f"cotizacionInstrumentoModel.pais": pais})

def cotizaciones_orleans_panel_todos(instrumento, pais):
    return _get(f"https://api.invertironline.com/api/v2/cotizaciones-orleans-panel/{instrumento}/{pais}/Todos",
                params={f"cotizacionInstrumentoModel.instrumento": instrumento,
                        f"cotizacionInstrumentoModel.pais": pais})

def cotizaciones_orleans_panel_operables(instrumento, pais):
    return _get(f"https://api.invertironline.com/api/v2/cotizaciones-orleans-panel/{instrumento}/{pais}/Operables",
                params={f"cotizacionInstrumentoModel.instrumento": instrumento,
                        f"cotizacionInstrumentoModel.pais": pais})

# ─── Titulos ───────────────────────────────────────────────────────────────

def titulo(mercado, simbolo):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}")

def titulo_opciones(mercado, simbolo):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Opciones")

def titulo_cotizacion_detalle(mercado, simbolo):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/CotizacionDetalle")

def titulo_cotizacion_detalle_mobile(mercado, simbolo, plazo):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/CotizacionDetalleMobile/{plazo}")

def titulo_cotizacion(mercado, simbolo, plazo="t0"):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
                params={"model.simbolo": simbolo, "model.mercado": mercado, "model.plazo": plazo})

def titulo_serie_historica(mercado, simbolo, fecha_desde, fecha_hasta, ajustada="ajustada"):
    return _get(f"https://api.invertironline.com/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{fecha_desde}/{fecha_hasta}/{ajustada}")

def titulos_cotizacion_instrumentos(pais):
    return _get(f"https://api.invertironline.com/api/v2/{pais}/Titulos/Cotizacion/Instrumentos")

def titulos_cotizacion_paneles(pais, instrumento):
    return _get(f"https://api.invertironline.com/api/v2/{pais}/Titulos/Cotizacion/Paneles/{instrumento}")

# ─── FCI ───────────────────────────────────────────────────────────────────

def fci_lista():
    return _get("https://api.invertironline.com/api/v2/Titulos/FCI")

def fci_por_simbolo(simbolo):
    return _get(f"https://api.invertironline.com/api/v2/Titulos/FCI/{simbolo}")

def fci_tipo_fondos():
    return _get("https://api.invertironline.com/api/v2/Titulos/FCI/TipoFondos")

def fci_administradoras():
    return _get("https://api.invertironline.com/api/v2/Titulos/FCI/Administradoras")

def fci_administradora_tipo_fondos(administradora):
    return _get(f"https://api.invertironline.com/api/v2/Titulos/FCI/Administradoras/{administradora}/TipoFondos")

def fci_administradora_tipo_fondo(administradora, tipo_fondo):
    return _get(f"https://api.invertironline.com/api/v2/Titulos/FCI/Administradoras/{administradora}/TipoFondos/{tipo_fondo}")

# ─── Portafolio ────────────────────────────────────────────────────────────

def portafolio(pais):
    return _get(f"https://api.invertironline.com/api/v2/portafolio/{pais}")

# ─── Estado de Cuenta ──────────────────────────────────────────────────────

def estado_cuenta():
    return _get("https://api.invertironline.com/api/v2/estadocuenta")

# ─── Perfil ────────────────────────────────────────────────────────────────

def datos_perfil():
    return _get("https://api.invertironline.com/api/v2/datos-perfil")

# ─── Operaciones ───────────────────────────────────────────────────────────

def operaciones(numero=None, estado=None, fecha_desde=None, fecha_hasta=None, pais=None):
    params = {}
    if numero is not None:     params["filtro.numero"] = numero
    if estado is not None:     params["filtro.estado"] = estado
    if fecha_desde is not None: params["filtro.fechaDesde"] = fecha_desde
    if fecha_hasta is not None: params["filtro.fechaHasta"] = fecha_hasta
    if pais is not None:       params["filtro.pais"] = pais
    return _get("https://api.invertironline.com/api/v2/operaciones", params=params)

def operacion_por_numero(numero):
    return _get(f"https://api.invertironline.com/api/v2/operaciones/{numero}")

# ─── Operar ────────────────────────────────────────────────────────────────

def operar_comprar(mercado, simbolo, cantidad, precio, plazo="t0", validez=None, tipo_orden="precioLimite", monto=None, id_fuente=0):
    data = {"mercado": mercado, "simbolo": simbolo, "cantidad": cantidad, "precio": precio,
            "plazo": plazo, "validez": validez, "tipoOrden": tipo_orden, "idFuente": id_fuente}
    if monto is not None: data["monto"] = monto
    return _post("https://api.invertironline.com/api/v2/operar/Comprar", data=data)

def operar_vender(mercado, simbolo, cantidad, precio, validez=None, tipo_orden="precioLimite", plazo="t0", id_fuente=0):
    data = {"mercado": mercado, "simbolo": simbolo, "cantidad": cantidad, "precio": precio,
            "validez": validez, "tipoOrden": tipo_orden, "plazo": plazo, "idFuente": id_fuente}
    return _post("https://api.invertironline.com/api/v2/operar/Vender", data=data)

def operar_comprar_especie_d(mercado, simbolo, cantidad, precio, plazo="t0", validez=None, tipo_orden="precioLimite", monto=None, id_fuente=0):
    data = {"mercado": mercado, "simbolo": simbolo, "cantidad": cantidad, "precio": precio,
            "plazo": plazo, "validez": validez, "tipoOrden": tipo_orden, "idFuente": id_fuente}
    if monto is not None: data["monto"] = monto
    return _post("https://api.invertironline.com/api/v2/operar/ComprarEspecieD", data=data)

def operar_vender_especie_d(mercado, simbolo, cantidad, precio, id_cuenta_bancaria=0, validez=None, tipo_orden="precioLimite", plazo="t0", id_fuente=0):
    data = {"mercado": mercado, "simbolo": simbolo, "cantidad": cantidad, "precio": precio,
            "idCuentaBancaria": id_cuenta_bancaria, "validez": validez,
            "tipoOrden": tipo_orden, "plazo": plazo, "idFuente": id_fuente}
    return _post("https://api.invertironline.com/api/v2/operar/VenderEspecieD", data=data)

def operar_token(mercado, simbolo, cantidad, monto):
    data = {"mercado": mercado, "simbolo": simbolo, "cantidad": cantidad, "monto": monto}
    return _post("https://api.invertironline.com/api/v2/operar/Token", data=data)

# ─── CPD (Cheque de Pago Diferido) ─────────────────────────────────────────

def cpd_puede_operar():
    return _get("https://api.invertironline.com/api/v2/operar/CPD/PuedeOperar")

def cpd_por_estado_segmento(estado, segmento):
    return _get(f"https://api.invertironline.com/api/v2/operar/CPD/{estado}/{segmento}")

def cpd_comisiones(importe, plazo, tasa):
    return _get(f"https://api.invertironline.com/api/v2/operar/CPD/Comisiones/{importe}/{plazo}/{tasa}")

def cpd_operar(id_subasta, tasa, fuente="compra_Venta_Por_Web"):
    return _post("https://api.invertironline.com/api/v2/operar/CPD",
                 data={"idSubasta": id_subasta, "tasa": tasa, "fuente": fuente})

# ─── FCI Operar (Suscripción / Rescate) ────────────────────────────────────

def fci_suscribir(simbolo, monto, solo_validar=False):
    return _post("https://api.invertironline.com/api/v2/operar/suscripcion/fci",
                 data={"simbolo": simbolo, "monto": monto, "soloValidar": solo_validar})

def fci_rescatar(simbolo, cantidad, solo_validar=False):
    return _post("https://api.invertironline.com/api/v2/operar/rescate/fci",
                 data={"simbolo": simbolo, "cantidad": cantidad, "soloValidar": solo_validar})

# ─── Operatoria Simplificada ───────────────────────────────────────────────

def operatoria_simplificada_parametros(id_tipo_operatoria):
    return _get(f"https://api.invertironline.com/api/v2/OperatoriaSimplificada/{id_tipo_operatoria}/Parametros")

def operatoria_simplificada_montos_estimados(monto):
    return _get(f"https://api.invertironline.com/api/v2/OperatoriaSimplificada/MontosEstimados/{monto}")

def operatoria_simplificada_validar(monto, id_tipo_operatoria):
    return _get(f"https://api.invertironline.com/api/v2/OperatoriaSimplificada/Validar/{monto}/{id_tipo_operatoria}")

def operatoria_simplificada_venta_mep_montos_estimados(monto):
    return _get(f"https://api.invertironline.com/api/v2/OperatoriaSimplificada/VentaMepSimple/MontosEstimados/{monto}")

def operatoria_simplificada_comprar(monto, id_tipo_operatoria, id_cuenta_bancaria=0):
    return _post("https://api.invertironline.com/api/v2/OperatoriaSimplificada/Comprar",
                 data={"monto": monto, "idTipoOperatoriaSimplificada": id_tipo_operatoria, "idCuentaBancaria": id_cuenta_bancaria})

# ─── Asesores ──────────────────────────────────────────────────────────────

def asesor_movimientos(clientes, desde, hasta, date_type="", status="", tipo="", country="", currency="", cuenta_comitente=""):
    data = {"clientes": clientes, "from": desde, "to": hasta, "dateType": date_type,
            "status": status, "type": tipo, "country": country, "currency": currency,
            "cuentaComitente": cuenta_comitente}
    return _post("https://api.invertironline.com/api/v2/Asesor/Movimientos", data=data)

def asesor_operar_vender_especie_d(id_cliente, fondos, mercado, simbolo, cantidad, precio, validez=None,
                                    id_cuenta_bancaria=0, tipo_orden="precioLimite", plazo="t0", id_fuente=0):
    data = {"idClienteAsesorado": id_cliente, "fondosParaOperacion": fondos, "mercado": mercado,
            "simbolo": simbolo, "cantidad": cantidad, "precio": precio, "validez": validez,
            "idCuentaBancaria": id_cuenta_bancaria, "tipoOrden": tipo_orden, "plazo": plazo, "idFuente": id_fuente}
    return _post("https://api.invertironline.com/api/v2/asesores/operar/VenderEspecieD", data=data)

def asesor_test_inversor():
    return _get("https://api.invertironline.com/api/v2/asesores/test-inversor")

def asesor_test_inversor_enviar(respuesta):
    return _post("https://api.invertironline.com/api/v2/asesores/test-inversor", data=respuesta)

def asesor_test_inversor_por_cliente(id_cliente, respuesta):
    return _post(f"https://api.invertironline.com/api/v2/asesores/test-inversor/{id_cliente}", data=respuesta)

# ─── Notificaciones ────────────────────────────────────────────────────────

def notificaciones():
    return _get("https://api.invertironline.com/api/v2/Notificacion")

# ─── Helpers: wrappers que devuelven DataFrame (como panelescotizaciones) ──

def _df(data, key="titulos"):
    if data and key in data:
        return pd.DataFrame(data[key])
    if isinstance(data, list):
        return pd.DataFrame(data)
    return pd.DataFrame()

def df_adrs():
    return _df(cotizaciones_todos("adrs", "estados_unidos"))

def df_acciones_eeuu():
    return _df(cotizaciones_todos("acciones", "estados_unidos"))

def df_acciones():
    return _df(cotizaciones_todos("acciones", "argentina"))

def df_titulos_publicos():
    return _df(cotizaciones_todos("titulosPublicos", "argentina"))

def df_obligaciones_negociables():
    return _df(cotizaciones_todos("obligacionesNegociables", "argentina"))

def df_cedears():
    return _df(cotizaciones_todos("cedears", "argentina"))

def df_cauciones():
    return _df(cotizaciones_todos("cauciones", "argentina"))

def df_fci():
    return _df(fci_lista())

def df_portafolio(pais):
    data = portafolio(pais)
    if data and "activos" in data:
        return pd.DataFrame(data["activos"])
    return pd.DataFrame()

def df_operaciones(**filtros):
    data = operaciones(**filtros)
    if isinstance(data, list):
        return pd.DataFrame(data)
    return pd.DataFrame()

# ─── Aliases compatibles con panelescotizaciones ──────────────────────────

def obtener_cotizaciones(instrumento, pais):
    return cotizaciones_todos(instrumento, pais)

def obtener_cotizaciones_adrs():
    return df_adrs()

def obtener_cotizaciones_acciones_eeuu():
    return df_acciones_eeuu()

def obtener_cotizaciones_acciones():
    return df_acciones()

def obtener_cotizaciones_titulos_publicos():
    return df_titulos_publicos()

def obtener_cotizaciones_obligaciones_negociables():
    return df_obligaciones_negociables()

def obtener_cotizaciones_cedears():
    return df_cedears()

def obtener_cotizaciones_cauciones():
    return df_cauciones()
