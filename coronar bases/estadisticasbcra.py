import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json

# ─── Configuración ────────────────────────────────────────────────────────────

BCRA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

URLS = {
    'landing': 'https://www.bcra.gob.ar/estadisticas-indicadores/',
    'api_ultimas': 'https://www.bcra.gob.ar/api/endpoints/principales-variables-ultimas.php',
    'api_rango': 'https://www.bcra.gob.ar/api/endpoints/principales-variables-rango.php',
    'datos_form': 'https://www.bcra.gob.ar/principales-variables-datos/',
}

requests.packages.urllib3.disable_warnings()


# ─── Funciones principales ────────────────────────────────────────────────────

def get_bcra_variables():
    """
    Obtiene las variables principales del BCRA con sus valores más recientes.
    
    El sitio BCRA fue rediseñado (WordPress/Divi): los datos se cargan via AJAX
    desde un endpoint JSON. Esta función:
      1. Lee la página HTML para obtener el nombre de cada variable y su serie_id.
      2. Consulta el API JSON de valores más recientes.
      3. Combina ambos y devuelve un DataFrame con nombre, fecha, valor, serie_id.
    """
    try:
        print("🔍 Obteniendo variables del BCRA...")

        # ── Paso 1: parsear la página HTML para nombres y series IDs ──
        resp = requests.get(URLS['landing'], headers=BCRA_HEADERS, verify=False, timeout=30)
        resp.raise_for_status()
        print(f"   ✓ Página cargada (status {resp.status_code})")

        soup = BeautifulSoup(resp.content, 'html.parser')
        table = soup.find('table', id='tabla-rowcolspan-int')

        if not table:
            print("   ✗ No se encontró la tabla de variables en la página.")
            return pd.DataFrame()

        variables = []
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if not tds:
                continue
            link = tds[0].find('a')
            if not link:
                continue
            href = link.get('href', '')
            serie_id = ''
            if 'serie=' in href:
                serie_id = href.split('serie=')[1].split('&')[0]

            if not serie_id:
                continue

            variables.append({
                'nombre': link.get_text(strip=True),
                'serie_id': serie_id,
            })

        print(f"   ✓ {len(variables)} variables encontradas en la página")

        if not variables:
            return pd.DataFrame()

        # ── Paso 2: obtener valores actuales desde el API ──
        resp_api = requests.get(URLS['api_ultimas'], headers=BCRA_HEADERS, verify=False, timeout=30)
        resp_api.raise_for_status()
        data_api = resp_api.json()

        if not data_api.get('success') or 'series' not in data_api:
            print("   ✗ El API no devolvió datos válidos.")
            return pd.DataFrame()

        series = data_api['series']
        print(f"   ✓ API devolvió datos de {len(series)} series")

        # ── Paso 3: combinar ──
        resultados = []
        for var in variables:
            sid = var['serie_id']
            entry = series.get(sid)
            fecha = entry['fecha'] if entry else ''
            valor = entry['valor'] if entry else ''
            resultados.append({
                'nombre': var['nombre'],
                'fecha': fecha,
                'valor': valor,
                'serie_id': sid,
            })

        df = pd.DataFrame(resultados)
        # Ordenar: primero las que tienen valor, después por nombre
        df['_tiene_valor'] = df['valor'].apply(lambda v: v != '' and pd.notna(v))
        df = df.sort_values(['_tiene_valor', 'nombre'], ascending=[False, True])
        df = df.drop(columns=['_tiene_valor'])
        df = df.reset_index(drop=True)

        print(f"   ✓ Datos listos: {len(df)} variables con valor")
        return df

    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error de conexión: {e}")
        return pd.DataFrame()
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"   ✗ Error al procesar datos: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"   ✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_historical_data(serie_id, fecha_desde=None, fecha_hasta=None):
    """
    Obtiene datos históricos para una serie específica del BCRA.
    
    El nuevo sitio BCRA protege la consulta histórica con Cloudflare Turnstile
    (captcha), por lo que el acceso automatizado directo está limitado.
    
    Esta función:
      - Obtiene el rango de fechas disponible desde el API de rango.
      - Muestra la URL manual para descargar desde el navegador.
    
    Parámetros:
      serie_id (str): ID numérico de la serie (ej. '246').
      fecha_desde (str, opcional): Fecha inicio en formato YYYY-MM-DD.
      fecha_hasta (str, opcional): Fecha fin en formato YYYY-MM-DD.
    
    Retorna:
      DataFrame vacío (el usuario debe descargar manualmente desde el navegador).
    """
    print(f"\n📊 Consultando datos históricos para serie {serie_id}...")

    # ── Obtener rango de fechas disponible ──
    try:
        resp = requests.get(
            URLS['api_rango'],
            params={'serie': serie_id},
            headers=BCRA_HEADERS,
            verify=False,
            timeout=15
        )
        if resp.status_code == 200:
            rango = resp.json()
            if rango.get('success'):
                min_f = rango.get('min_fecha', '')
                max_f = rango.get('max_fecha', '')
                print(f"   ✓ Rango disponible: {min_f} → {max_f}")
    except Exception:
        print("   - No se pudo obtener el rango de fechas.")

    # ── Construir URL manual ──
    if not fecha_desde:
        min_f = rango.get('min_fecha', '') if 'rango' in dir() else ''
        fecha_desde = min_f or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime('%Y-%m-%d')

    manual_url = f"{URLS['datos_form']}?serie={serie_id}"
    print(f"\n   ⚠  El sitio BCRA ahora requiere verificación de seguridad (Turnstile).")
    print(f"   ⚠  Para descargar datos históricos manualmente, abra este enlace en su navegador:")
    print(f"      {manual_url}")
    print(f"   ⚠  Seleccione las fechas {fecha_desde} → {fecha_hasta} y complete el captcha.\n")

    return pd.DataFrame()


# ─── Función auxiliar ─────────────────────────────────────────────────────────

def generar_enlace_manual(serie_id, nombre_variable=""):
    """Genera un enlace para abrir en el navegador."""
    url = f"{URLS['datos_form']}?serie={serie_id}"
    label = f" {nombre_variable}" if nombre_variable else f" (ID: {serie_id})"
    print(f"🔗 Abrir en navegador: {url}")
    return url


# ─── Ejemplo de uso (CLI interactivo) ────────────────────────────────────────

if __name__ == "__main__":
    import os

    print("=" * 60)
    print("  BCRA — Indicadores y Variables Económicas")
    print("  Fuente: https://www.bcra.gob.ar/estadisticas-indicadores/")
    print("=" * 60)

    df = get_bcra_variables()

    if df.empty:
        print("\n❌ No se pudieron obtener las variables del BCRA.")
        print("   Verifique su conexión a internet e intente nuevamente.")
        exit(1)

    # Mostrar variables encontradas
    print("\n" + "=" * 60)
    print("  VARIABLES PRINCIPALES — valores más recientes")
    print("=" * 60)
    for idx, row in df.iterrows():
        serie_id = row['serie_id']
        nombre = row['nombre']
        fecha = row['fecha']
        valor = row['valor']
        # Truncar nombre largo
        nombre_short = nombre if len(nombre) <= 60 else nombre[:57] + "..."
        print(f"  {idx+1:>2}. {nombre_short}")
        if fecha and valor:
            print(f"      📅 {fecha}  💰 {valor}")
        else:
            print(f"      (sin datos disponibles)")
        print()

    # Ofrecer consulta histórica
    print("\n" + "=" * 60)
    print("  CONSULTA HISTÓRICA (abrir en navegador)")
    print("=" * 60)

    try:
        opcion = input(
            "\nNúmero de variable para ver datos históricos\n"
            "(0 = salir, ENTER = mostrar todos los enlaces): "
        ).strip()

        if opcion == "":
            # Mostrar enlaces de todas
            print("\n📋 Enlaces para todas las variables:\n")
            for idx, row in df.iterrows():
                print(f"  {idx+1:>2}. {row['nombre'][:50]}")
                print(f"      {URLS['datos_form']}?serie={row['serie_id']}")
            print()

        elif opcion.isdigit() and int(opcion) > 0 and int(opcion) <= len(df):
            idx = int(opcion) - 1
            row = df.iloc[idx]
            serie_id = row['serie_id']
            nombre_variable = row['nombre']

            print(f"\n📊 {nombre_variable} (ID: {serie_id})")
            fecha_desde = input("Fecha desde (YYYY-MM-DD, dejar en blanco = 1 año atrás): ").strip()
            fecha_hasta = input("Fecha hasta (YYYY-MM-DD, dejar en blanco = hoy): ").strip()

            # Abrir el navegador con el enlace
            manual_url = f"{URLS['datos_form']}?serie={serie_id}"
            print(f"\n🌐 Abriendo en el navegador para descargar datos históricos...")
            print(f"   {manual_url}")
            try:
                os.startfile(manual_url)
            except Exception:
                print("   (no se pudo abrir el navegador automáticamente)")

        else:
            print("Opción no válida. Saliendo...")

    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Hasta luego.")
    except Exception as e:
        print(f"\nError: {e}")
