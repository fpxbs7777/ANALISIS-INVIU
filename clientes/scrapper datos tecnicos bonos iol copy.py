from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import time

def obtener_datos_tecnicos_bono(mercado, simbolo, descripcion_url):
    """
    Obtiene los datos técnicos de un bono desde IOL.
    
    Args:
        mercado: Código del mercado (ej: BCBA)
        simbolo: Símbolo del título (ej: AL30)
        descripcion_url: Descripción formateada para la URL (ej: BONO-REP.-ARGENTINA-USD-STEP-UP-2030)
    
    Returns:
        dict: Diccionario con los datos técnicos del bono
    """
    # Construir URL
    url = f"https://iol.invertironline.com/titulo/cotizacion/{mercado}/{simbolo}/{descripcion_url}/fundamentalesTecnicos"
    
    # Configurar opciones de Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar la tabla de datos técnicos
        tablas = soup.select('table.table.table-striped')
        tabla = None
        for t in tablas:
            thead = t.find('thead')
            if thead and 'Datos técnicos del bono' in thead.text:
                tabla = t
                break
        
        if not tabla:
            return {"error": "No se encontró la tabla de datos técnicos"}
        
        datos_tecnicos = {}
        tbody = tabla.find('tbody')
        filas = tbody.find_all('tr') if tbody else tabla.find_all('tr')
        
        for fila in filas:
            columnas = fila.find_all('td')
            if len(columnas) == 2:
                clave = columnas[0].text.strip()
                valor = columnas[1].text.strip()
                datos_tecnicos[clave] = valor
        
        return datos_tecnicos

    except Exception as e:
        return {"error": str(e)}
    finally:
        if driver:
            driver.quit()

def scrapear_datos_bono():
    """Función original para compatibilidad"""
    datos = obtener_datos_tecnicos_bono(
        mercado="BCBA",
        simbolo="AL30",
        descripcion_url="BONO-REP.-ARGENTINA-USD-STEP-UP-2030"
    )
    
    if "error" in datos:
        print(f"Error: {datos['error']}")
    else:
        with open('al30_datos_tecnicos.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        print(f"Scrapeo exitoso. Datos guardados en al30_datos_tecnicos.json")

if __name__ == "__main__":
    scrapear_datos_bono()