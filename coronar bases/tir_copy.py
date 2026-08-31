import os
import requests
import pandas as pd
import json
from datetime import datetime, date
from scipy.optimize import brentq

username = "boosandr97@gmail.com"
password = "Chule348936_"

def obtener_tokens(user, pwd):
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
        raise Exception(f"Error al obtener cotizacion: {response.status_code} - {response.text}")

def obtener_dolar_mep():
    url = "https://dolarapi.com/v1/dolares/bolsa"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('venta')
    except Exception as e:
        print(f"[ERROR] Error al obtener dolar MEP: {e}")
    return None

def normalizar_flujo(flujo_raw):
    y, m, dd = flujo_raw['fecha'].split('-')
    fecha = date(int(y), int(m), int(dd))
    if 'cupon_pct' in flujo_raw or 'amort_pct' in flujo_raw:
        monto = flujo_raw.get('cupon_pct', 0) + flujo_raw.get('amort_pct', 0)
    else:
        monto = flujo_raw.get('monto_por_cien', 0)
    return {'fecha': fecha, 'monto': monto}

def precio_a_usd_par100(precio_ars, fx_mep, precio_especie_usd_directo=None):
    if precio_especie_usd_directo is not None:
        return precio_especie_usd_directo
    return (precio_ars * 100) / fx_mep

def calcular_tir(flujos, precio_usd_par100, fecha_actual):
    flujos_futuros = [f for f in flujos if f['fecha'] > fecha_actual]
    if not flujos_futuros:
        return None

    def npv(r):
        total = 0.0
        for f in flujos_futuros:
            dias = (f['fecha'] - fecha_actual).days
            t = dias / 365.0
            total += f['monto'] / ((1 + r) ** t)
        return total - precio_usd_par100

    lo, hi = -0.9, 5.0
    npv_lo, npv_hi = npv(lo), npv(hi)

    if npv_lo * npv_hi > 0:
        print(f"  [WARN] No hay cambio de signo en el rango [{lo}, {hi}] - "
              f"TIR no calculable.")
        return None

    try:
        return brentq(npv, lo, hi, xtol=1e-10, maxiter=200)
    except Exception as e:
        print(f"  [ERROR] Error en biseccion: {e}")
        return None

def test_validacion_contra_json(path_json='ONs_Seleccionadas_Alta_Calidad.json', fx_mep_fijo=1529.30):
    with open(path_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fecha_valuacion = date(2026, 7, 26)
    desvios = []

    print("\n" + "="*70)
    print("TEST DE AUTO-VALIDACION - motor nuevo vs TIR publicada en el JSON")
    print("="*70)

    for bono in data['datos_completos']:
        ticker = bono['ticker']
        precio_ars = bono['panel_balanz']['precio_ultimo']
        tir_publicada = bono['panel_balanz']['tir_porcentual']

        flujos = [normalizar_flujo(f) for f in bono['flujo_fondos']]
        precio_usd = precio_a_usd_par100(precio_ars, fx_mep_fijo)
        tir_calculada = calcular_tir(flujos, precio_usd, fecha_valuacion)

        if tir_calculada is None:
            print(f"  {ticker}: [WARN] TIR no calculable")
            continue

        diff = (tir_calculada * 100) - tir_publicada
        desvios.append(abs(diff))
        estado = "OK" if abs(diff) < 0.5 else "DESVIO ALTO"
        print(f"  {ticker}: publicada={tir_publicada:.2f}%  calculada={tir_calculada*100:.2f}%  diff={diff:+.2f}pp  [{estado}]")

    if desvios:
        promedio = sum(desvios) / len(desvios)
        print(f"\nDesvio absoluto promedio: {promedio:.3f}pp sobre {len(desvios)} bonos")
        if promedio > 0.5:
            print("[ERROR] EL MOTOR NO ESTA VALIDADO - no usar estos resultados en produccion hasta corregir.")
        else:
            print("[OK] Motor validado dentro de tolerancia (+-0.5pp).")

def ejecutar_reporte_iol(archivo_json='ONs_Seleccionadas_Alta_Calidad.json'):
    print("Cargando bonos desde ONs_Seleccionadas_Alta_Calidad.json...")
    with open(archivo_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    base_bonos = data['datos_completos']

    print("Obteniendo token de acceso...")
    token = obtener_tokens(username, password)

    print("Obteniendo dolar MEP...")
    fx_mep = obtener_dolar_mep()
    if fx_mep is None:
        print("[ERROR] No se pudo obtener el dolar MEP. Abortando calculo (no usar fallback inventado).")
        fx_mep = None
    else:
        print(f"Dolar MEP actual: ARS {fx_mep:.2f}")

    fecha_hoy = datetime.now().date()
    resultados = []

    for bono in base_bonos:
        ticker = bono['ticker']
        mercado = bono['datos_tecnicos']['mercado']
        flujos_json = bono['flujo_fondos']

        print(f"\nAnalizando {ticker}...")
        try:
            precio = obtener_precio_actual(ticker, mercado, token)
        except Exception as e:
            print(f"  [WARN] No se pudo obtener precio para {ticker}: {e}")
            continue

        if not precio:
            print(f"  [WARN] No se pudo obtener liquidez/precio para {ticker}.")
            continue

        flujos = [normalizar_flujo(f) for f in flujos_json]

        if fx_mep is None:
            print(f"  [WARN] {ticker}: no hay dolar MEP disponible para convertir precio.")
            continue

        precio_especie_usd = None
        especies_rel = bono['datos_tecnicos'].get('especies_relacionadas', {})
        if 'D' in especies_rel:
            try:
                precio_usd_directo = obtener_precio_actual(especies_rel['D'], mercado, token)
                if precio_usd_directo:
                    precio_especie_usd = precio_usd_directo
            except Exception:
                pass

        precio_usd = precio_a_usd_par100(precio, fx_mep, precio_especie_usd)

        print(f"  Precio en ARS: {precio:.2f}  |  USD (par 100): {precio_usd:.4f}")

        tir = calcular_tir(flujos, precio_usd, fecha_hoy)

        if tir is not None:
            tir_formateada = f"{tir * 100:.2f}%"
            resultados.append({
                "Ticker": ticker,
                "Precio ARS": precio,
                "Precio USD (par 100)": round(precio_usd, 4),
                "TIR (TEA)": tir_formateada
            })
        else:
            print(f"  [WARN] Error de calculo de TIR para {ticker}")

    if resultados:
        df_resultados = pd.DataFrame(resultados)
        print("\n" + "="*70)
        print("REPORTE DE RENDIMIENTOS - IOL")
        print("="*70)
        print(df_resultados.to_string(index=False))
        print("="*70)
    else:
        print("\nNo se obtuvieron resultados para ningun bono.")

if __name__ == '__main__':
    if not username or not password:
        print("[INFO] Credenciales IOL no configuradas (IOL_USERNAME/IOL_PASSWORD) - saltando reporte IOL.")
    else:
        try:
            ejecutar_reporte_iol()
        except Exception as e:
            print(f"\n[ERROR] Error en reporte IOL: {e}")
            import traceback
            traceback.print_exc()

    test_validacion_contra_json()
