import sys
import time
import traceback

# -----------------------------------------------------------------------------
# 1. BLINDAJE ANTI-CIERRE: Capturamos errores fatales (incluso durante imports)
# -----------------------------------------------------------------------------
def mantener_consola_abierta(tipo_error, valor_error, traza):
    print("\n" + "="*60)
    print("🚨 SE PRODUJO UN ERROR FATAL ANTES O DURANTE LA IMPORTACIÓN 🚨")
    print("="*60)
    print("Detalle técnico del error:")
    print("------------------------------------------------------------")
    traceback.print_exception(tipo_error, valor_error, traza)
    print("------------------------------------------------------------\n")
    input("👉 Presioná la tecla ENTER para cerrar esta ventana...")
    sys.exit(1)

# Asignamos el interceptor antes de importar cualquier otra librería
sys.excepthook = mantener_consola_abierta
# -----------------------------------------------------------------------------

import json
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Si panelescotizaciones.py falla al traer el token, el excepthook atrapará el error y no se cerrará
from panelescotizaciones import obtener_cotizaciones_titulos_publicos


def scrapear_tecnicos_bono(simbolo, mercado="BCBA", sesion=None):
    """Scrapea la tabla de 'Datos técnicos del bono' desde la web pública de IOL."""
    url = f"https://iol.invertironline.com/titulo/cotizacion/{mercado}/{simbolo}/-/fundamentalesTecnicos"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        cliente = sesion if sesion else requests
        res = cliente.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print(f"  -> [{simbolo}] Error HTTP {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        tabla = soup.find("table", class_="table-striped")
        
        if not tabla:
            print(f"  -> [{simbolo}] No se encontró la tabla técnica (sin liquidez o sin datos).")
            return None

        datos_bono = {"simbolo": simbolo, "mercado": mercado, "url": url}

        for fila in tabla.find_all("tr"):
            columnas = fila.find_all("td")
            if len(columnas) == 2:
                clave = columnas[0].text.strip()
                valor = columnas[1].text.strip()

                # Normalización de claves para JSON
                clave_norm = (
                    clave.lower()
                    .replace(" ", "_")
                    .replace("ó", "o")
                    .replace("í", "i")
                    .replace("á", "a")
                    .replace("é", "e")
                    .replace("ú", "u")
                    .replace("?", "")
                )
                datos_bono[clave_norm] = valor

        return datos_bono

    except Exception as e:
        print(f"  -> [{simbolo}] Error puntual de scraping: {e}")
        return None


def generar_base_tecnica_bonos_json():
    print("--- PASO 1: Obteniendo panel de Títulos Públicos desde API IOL ---")
    df_bonos = obtener_cotizaciones_titulos_publicos()

    if df_bonos is None or df_bonos.empty:
        raise ValueError("La función 'obtener_cotizaciones_titulos_publicos()' devolvió un panel vacío o falló la autenticación en IOL.")

    simbolos = df_bonos["simbolo"].unique().tolist()
    print(f"✅ Se encontraron {len(simbolos)} bonos en el panel. Iniciando scraping...\n")

    base_datos_tecnicos = []

    with requests.Session() as sesion:
        for i, simbolo in enumerate(simbolos, 1):
            print(f"[{i}/{len(simbolos)}] Consultando técnicos de {simbolo}...")

            datos = scrapear_tecnicos_bono(simbolo, mercado="BCBA", sesion=sesion)
            if datos and len(datos) > 3:
                base_datos_tecnicos.append(datos)

            # Rate Limiting para evitar bloqueo 403 o 429 por parte del firewall de IOL
            time.sleep(0.7)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    nombre_archivo = os.path.join(script_dir, "bonos_tecnicos_iol.json")
    print(f"\n--- PASO 2: Guardando archivo {nombre_archivo} ---")
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(base_datos_tecnicos, f, indent=2, ensure_ascii=False)

    print(f"🎉 ¡Éxito total! Se guardaron los datos de {len(base_datos_tecnicos)} bonos correctamente.")


if __name__ == "__main__":
    try:
        generar_base_tecnica_bonos_json()
        
    except Exception as error_principal:
        print("\n" + "="*60)
        print("🚨 SE PRODUJO UN ERROR DURANTE LA EJECUCIÓN 🚨")
        print("="*60)
        print("Detalle técnico del error (Traceback):")
        print("------------------------------------------------------------")
        traceback.print_exc()
        print("------------------------------------------------------------\n")
        
    finally:
        print("\n" + "="*60)
        input("👉 Presioná la tecla ENTER para cerrar esta ventana...")
        print("="*60)