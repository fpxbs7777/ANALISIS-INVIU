from pydantic import BaseModel, Field
from typing import List, Dict
import json
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Importar la función de scraping de Selenium
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "scrapper datos tecnicos bonos iol.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
obtener_bono_completo = scraper_module.obtener_bono_completo

# 1. Definimos el esquema estricto que necesita tu "calculadora tir bonos.py"
class Tasa(BaseModel):
    fecha_desde: str = Field(description="Fecha de inicio en formato YYYY-MM-DD")
    fecha_hasta: str = Field(description="Fecha de fin en formato YYYY-MM-DD")
    tasa_anual: float = Field(description="Tasa de interés anual como decimal (ej. 0.0425 para 4.25%)")

class Amortizacion(BaseModel):
    numero_cuota: int = Field(description="Número correlativo de la cuota")
    fecha_pago: str = Field(description="Fecha de pago en formato YYYY-MM-DD")
    porcentaje_capital: float = Field(description="Porcentaje del capital que se amortiza (ej. 4.5454)")

class EstructuraBono(BaseModel):
    simbolo: str = Field(description="Ticker del bono, ej: AE38")
    emisor: str = Field(description="Emisor, ej: Gobierno Nacional")
    moneda: str = Field(description="Moneda, ej: Dolares")
    fecha_emision: str = Field(description="Fecha de emisión YYYY-MM-DD")
    fecha_vencimiento: str = Field(description="Fecha de vencimiento YYYY-MM-DD")
    estructura_tasas: List[Tasa] = Field(description="Lista de tasas de interés variables o step-up")
    calendario_amortizaciones: List[Amortizacion] = Field(description="Proyección de todas las cuotas de amortización")

def parsear_fecha_argentina(fecha_str):
    """Convierte fecha en formato DD/M/YYYY o D/M/YYYY a YYYY-MM-DD"""
    try:
        # Manejar formatos como "4/9/2020" o "9/7/2038"
        partes = fecha_str.split('/')
        if len(partes) == 3:
            dia, mes, anio = partes
            return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
        return fecha_str
    except:
        return fecha_str

def extraer_tasas(texto_interes):
    """Extrae las tasas step-up del texto de interés"""
    tasas = []
    # Patrones para encontrar tasas en el texto
    patron = r"Del (\d{1,2}/\d{1,2}/\d{4})\(inclusive\) al (\d{1,2}/\d{1,2}/\d{4})\(exclusive\):\s*([\d,]+)%"
    matches = re.findall(patron, texto_interes)
    
    for fecha_desde, fecha_hasta, tasa_str in matches:
        tasa_decimal = float(tasa_str.replace(',', '.')) / 100
        tasas.append(Tasa(
            fecha_desde=parsear_fecha_argentina(fecha_desde),
            fecha_hasta=parsear_fecha_argentina(fecha_hasta),
            tasa_anual=tasa_decimal
        ))
    
    return tasas

def generar_calendario_amortizaciones(texto_amortizacion, fecha_inicio, fecha_fin):
    """Genera el calendario de amortizaciones basado en el texto"""
    amortizaciones = []
    
    # Buscar pattern de cuotas
    patron_cuotas = r"(\d+)\s+cuotas\s+semestrales"
    match = re.search(patron_cuotas, texto_amortizacion)
    
    if match:
        num_cuotas = int(match.group(1))
        porcentaje = 100.0 / num_cuotas
        
        # Parsear fecha inicio
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        
        for i in range(num_cuotas):
            fecha_pago = fecha_inicio_dt + relativedelta(months=6*i)
            amortizaciones.append(Amortizacion(
                numero_cuota=i + 1,
                fecha_pago=fecha_pago.strftime("%Y-%m-%d"),
                porcentaje_capital=round(porcentaje, 4)
            ))
    
    return amortizaciones

def procesar_bono(mercado, simbolo, dias_cache=0):
    """Procesa un bono individual y devuelve su estructura"""
    print(f"Procesando {simbolo} ({mercado})...")
    
    datos_bono = obtener_bono_completo(
        mercado=mercado,
        simbolo=simbolo,
        dias_cache=dias_cache
    )
    
    if "error" in datos_bono:
        print(f"Error procesando {simbolo}: {datos_bono['error']}")
        return None
    
    # Convertir al formato que espera la calculadora
    estructura_tasas = []
    interes_data = datos_bono.get("interes", {})
    if isinstance(interes_data, dict) and "cronogramaCupon" in interes_data:
        for tramo in interes_data["cronogramaCupon"]:
            estructura_tasas.append(Tasa(
                fecha_desde=tramo.get("fecha_desde", ""),
                fecha_hasta=tramo.get("fecha_hasta", ""),
                tasa_anual=tramo.get("tasaAnual", 0.0)
            ))
    
    calendario_amortizaciones = []
    amortizacion_data = datos_bono.get("amortizacion", {})
    if isinstance(amortizacion_data, dict) and "cronogramaAmortizacion" in amortizacion_data:
        for cuota in amortizacion_data["cronogramaAmortizacion"]:
            calendario_amortizaciones.append(Amortizacion(
                numero_cuota=cuota.get("numero_cuota", 0),
                fecha_pago=cuota.get("fecha_pago", ""),
                porcentaje_capital=cuota.get("porcentaje_capital", 0.0)
            ))
    
    estructura = EstructuraBono(
        simbolo=datos_bono.get("simbolo", simbolo),
        emisor=datos_bono.get("emisor", ""),
        moneda=datos_bono.get("moneda", ""),
        fecha_emision=datos_bono.get("fecha_emision", ""),
        fecha_vencimiento=datos_bono.get("fecha_vencimiento", ""),
        estructura_tasas=estructura_tasas,
        calendario_amortizaciones=calendario_amortizaciones
    )
    
    print(f"  ✓ {simbolo}: {len(estructura.estructura_tasas)} tasas, {len(estructura.calendario_amortizaciones)} amortizaciones")
    return estructura.model_dump()

# Lista de bonos a procesar
bonos_a_procesar = [
    {"mercado": "BCBA", "simbolo": "AL30"},
    {"mercado": "BCBA", "simbolo": "AE38"},
    # Agregar más bonos aquí según sea necesario
]

print(f"Procesando {len(bonos_a_procesar)} bonos...")

# Procesar todos los bonos
json_final = {"bonos": {}}
for bono in bonos_a_procesar:
    datos = procesar_bono(bono["mercado"], bono["simbolo"], dias_cache=0)
    if datos:
        json_final["bonos"][datos["simbolo"]] = datos

# Guardar el archivo final
with open('estructura_bonos.json', 'w', encoding='utf-8') as f:
    json.dump(json_final, f, indent=4, ensure_ascii=False)

print(f"\n¡Éxito! Archivo estructura_bonos.json generado con {len(json_final['bonos'])} bonos.")