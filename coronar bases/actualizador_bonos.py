from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
import re
import os
import sys
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Importar la función de scraping
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "scrapper datos tecnicos bonos iol.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
obtener_bono_completo = scraper_module.obtener_bono_completo

# ── Rutas ──
RUTA_BONOS_JSON = os.path.join(os.path.dirname(__file__), "bonos.json")
RUTA_TICKERS_MONEDA = os.path.join(os.path.dirname(__file__), "..", "src", "lib", "tickers-moneda.json")

# ── Tickers de bonos soberanos a actualizar ──
BONOS_A_ACTUALIZAR = [
    # Bonos Hard Dollar
    {"mercado": "BCBA", "simbolo": "AL29"},
    {"mercado": "BCBA", "simbolo": "AL30"},
    {"mercado": "BCBA", "simbolo": "AL35"},
    {"mercado": "BCBA", "simbolo": "AL41"},
    {"mercado": "BCBA", "simbolo": "AN29"},
    {"mercado": "BCBA", "simbolo": "AO27"},
    {"mercado": "BCBA", "simbolo": "AO28"},
    {"mercado": "BCBA", "simbolo": "GD29"},
    {"mercado": "BCBA", "simbolo": "GD30"},
    {"mercado": "BCBA", "simbolo": "GD35"},
    {"mercado": "BCBA", "simbolo": "GD38"},
    {"mercado": "BCBA", "simbolo": "GD41"},
    {"mercado": "BCBA", "simbolo": "GD46"},
    {"mercado": "BCBA", "simbolo": "GE29"},
    {"mercado": "BCBA", "simbolo": "GE38"},
    {"mercado": "BCBA", "simbolo": "GE41"},
    {"mercado": "BCBA", "simbolo": "PR17"},
    {"mercado": "BCBA", "simbolo": "AE38"},
    # Letras
    {"mercado": "BCBA", "simbolo": "TO26"},
    {"mercado": "BCBA", "simbolo": "TX26"},
    {"mercado": "BCBA", "simbolo": "TX28"},
    {"mercado": "BCBA", "simbolo": "TX31"},
    {"mercado": "BCBA", "simbolo": "TTD26"},
    {"mercado": "BCBA", "simbolo": "TTS26"},
    {"mercado": "BCBA", "simbolo": "TMF27"},
    {"mercado": "BCBA", "simbolo": "TMF28"},
    {"mercado": "BCBA", "simbolo": "TMG27"},
    {"mercado": "BCBA", "simbolo": "TMG28"},
    {"mercado": "BCBA", "simbolo": "TML27"},
    {"mercado": "BCBA", "simbolo": "TY30P"},
    {"mercado": "BCBA", "simbolo": "TZV27"},
    {"mercado": "BCBA", "simbolo": "TZV28"},
    {"mercado": "BCBA", "simbolo": "TZX27"},
    {"mercado": "BCBA", "simbolo": "TZX28"},
]

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

# ══════════════════════════════════════════════════════════════════════
# CONVERSIÓN: scraper output → formato bonos.json
# ══════════════════════════════════════════════════════════════════════

def _clasificar_ticker(simbolo):
    """Clasifica el ticker en categoría para bonos.json"""
    if simbolo.startswith(("AL", "GD", "AN", "AO", "GE", "PR", "AE")):
        return "bono_hard_dollar"
    elif simbolo.startswith("TO") and len(simbolo) <= 4:
        return "letra_tasa_fija_ars"
    elif simbolo.startswith(("TX", "TTD", "TTS", "TMF", "TMG", "TML", "TY", "TZ")):
        return "letra"
    return "otro"


def convertir_a_bonos_json(datos_scraper, ticker_api=None):
    """
    Convierte el output de obtener_bono_completo() al formato de bonos.json.
    """
    simbolo = ticker_api or datos_scraper.get("simbolo", "")
    moneda_raw = datos_scraper.get("moneda", "")
    moneda = "USD" if moneda_raw == "USD" else "ARS"
    tipo_scraper = datos_scraper.get("tipo", "")

    # Interés
    interes = datos_scraper.get("interes", {})
    cronograma_cupon = interes.get("cronogramaCupon", [])
    frecuencia_cupon = interes.get("frecuenciaCupon", "semiannual")

    # Amortización
    amort = datos_scraper.get("amortizacion", {})
    tipo_amort_raw = amort.get("tipoAmortizacion", "bullet")

    # ── tipoCupon ──
    if len(cronograma_cupon) > 1:
        tipo_cupon = "Step-up"
        tipo_tasa = "step-up"
    else:
        tipo_cupon = "Fixed rate"
        tipo_tasa = "fixed"

    # ── cuponAnual ──
    if cronograma_cupon:
        cupon_anual = cronograma_cupon[0].get("tasaAnual", 0.0)
    else:
        cupon_anual = interes.get("tasaCuponAnual", 0.0) or 0.0

    # ── yieldConvention ──
    if moneda == "USD":
        yield_conv = "STREET"
    else:
        yield_conv = "TRUE"

    # ── tipoAmortizacion en bonos.json ──
    if tipo_amort_raw == "bullet":
        tipo_amort_json = "Bullet"
    elif tipo_amort_raw in ("cuotas_iguales", "cuotas_progresivas"):
        tipo_amort_json = "Sinkable"
    else:
        tipo_amort_json = "Bullet"

    # ── flujos_futuros_cada_100_vn ──
    flujos_scraper = datos_scraper.get("flujos_futuros", [])
    flujos_json = []
    for f in flujos_scraper:
        amort_pct = f.get("amortizacion_pct", 0.0)
        flujo_total = f.get("flujo_total", 0.0)

        if tipo_amort_json == "Bullet" and amort_pct >= 99.9:
            tipo_flujo = "PagoUnico"
        elif amort_pct > 0:
            tipo_flujo = "Cupon+Amortizacion"
        else:
            tipo_flujo = "Cupon"

        flujos_json.append({
            "fecha": f["fecha_pago"],
            "monto": round(flujo_total, 2),
            "tipoFlujo": tipo_flujo
        })

    # ── valorResidualActual ──
    if tipo_amort_json == "Bullet":
        valor_residual = 100
    else:
        # Para sinkable: VR del scraper o calcular del cronograma
        valor_residual = amort.get("valorResidualActual")
        if not valor_residual:
            crono_amort = amort.get("cronogramaAmortizacion", [])
            if crono_amort:
                total_amp = sum(c.get("porcentaje_capital", 0) for c in crono_amort)
                valor_residual = max(0, round(100 - total_amp, 2))
            else:
                valor_residual = 100

    # ── tipoBono ──
    if moneda == "ARS":
        tipo_bono = "SOBERANO_TASA_FIJA_ARS"
    else:
        tipo_bono = "SOBERANO_HD"

    # ── construir bono ──
    bono = {
        "ticker_api": simbolo,
        "mercado": "bCBA",
        "instrumento": "BONO",
        "tipo": "Tasa Fija ARS" if moneda == "ARS" and tipo_tasa == "fixed" else
                "Hard Dollar" if moneda == "USD" else
                "Letra ARS" if "letra" in _clasificar_ticker(simbolo) else
                "Tasa Fija ARS",
        "tipoBono": tipo_bono,
        "descripcion": datos_scraper.get("denominacion", simbolo),
        "vencimiento": datos_scraper.get("fecha_vencimiento", ""),
        "fechaEmision": datos_scraper.get("fecha_emision", ""),
        "isin": datos_scraper.get("codigo_isin") or "",
        "jurisdiccion": "ARG",
        "tipoCupon": tipo_cupon,
        "moneda": moneda,
        "monedaPago": moneda,
        "frecuenciaPago": "Semiannual" if frecuencia_cupon == "semiannual" else
                          "Quarterly" if frecuencia_cupon == "quarterly" else
                          "Annual" if frecuencia_cupon == "annual" else
                          "Semiannual",
        "convencionDias": "30/360",
        "tipoAmortizacion": tipo_amort_json,
        "montoEmision": 0,
        "cuponAnual": round(cupon_anual, 4),
        "valorPar": 100,
        "valorResidualActual": valor_residual,
        "yieldConvention": yield_conv,
        "tipoTasa": tipo_tasa,
        "ajuste": None,
        "flujos_futuros_cada_100_vn": flujos_json,
        "historico": []
    }

    return bono


def mergear_bonos_json(nuevos_bonos, ruta_bonos_json=None, sobrescribir=False):
    """
    Lee bonos.json existente, mergea/actualiza entradas, guarda.
    - nuevos_bonos: dict {ticker: bono_data}
    - sobrescribir: si True, reemplaza completamente; si False, solo actualiza
    """
    ruta = ruta_bonos_json or RUTA_BONOS_JSON

    if os.path.exists(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            bonos_existentes = json.load(f)
    else:
        bonos_existentes = {}

    actualizados = 0
    nuevos = 0
    for ticker, datos in nuevos_bonos.items():
        if ticker in bonos_existentes:
            # Solo sobrescribir si se pide explícitamente
            if sobrescribir:
                bonos_existentes[ticker] = datos
                actualizados += 1
            # Si no sobrescribir, mantener el existente
        else:
            bonos_existentes[ticker] = datos
            nuevos += 1

    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(bonos_existentes, f, indent=4, ensure_ascii=False)

    print(f"\nbonos.json: {nuevos} nuevos, {actualizados} actualizados, {len(bonos_existentes)} total")
    return bonos_existentes


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

# Lista legacy (estructura_bonos.json)
bonos_a_procesar_legacy = [
    {"mercado": "BCBA", "simbolo": "AL30"},
    {"mercado": "BCBA", "simbolo": "AE38"},
]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Actualizador de bonos desde IOL")
    ap.add_argument("--test", action="store_true", help="Test rápido con TO26/AE38/AL30")
    ap.add_argument("--check-robots", action="store_true", help="Verificar robots.txt de IOL")
    ap.add_argument("--ticker", type=str, help="Procesar un solo ticker (ej: AL30)")
    ap.add_argument("--all", action="store_true", help="Procesar TODOS los bonos soberanos a bonos.json")
    ap.add_argument("--legacy", action="store_true", help="Generar estructura_bonos.json (formato anterior)")
    ap.add_argument("--sobrescribir", action="store_true", help="Sobrescribir entradas existentes en bonos.json")
    args = ap.parse_args()

    if args.check_robots:
        scraper_module.check_robots_txt()

    elif args.test:
        scraper_module.check_robots_txt()
        test_parser("BCBA", "TO26", "TO26 (Tasa Fija, Bullet)")
        test_parser("BCBA", "AE38", "AE38 (Step-up truncado, Cuotas iguales)")
        test_parser("BCBA", "AL30", "AL30 (Step-up completo, Cuotas progresivas)")

    elif args.ticker:
        simbolo = args.ticker.upper()
        scraper_module.check_robots_txt()
        print(f"Procesando {simbolo}...")
        datos = obtener_bono_completo("BCBA", simbolo, dias_cache=0)
        if "error" in datos:
            print(f"ERROR: {datos['error']}")
            sys.exit(1)
        bono_json = convertir_a_bonos_json(datos, ticker_api=simbolo)
        mergear_bonos_json({simbolo: bono_json}, sobrescribir=args.sobrescribir)

    elif args.all:
        scraper_module.check_robots_txt()
        total = len(BONOS_A_ACTUALIZAR)
        print(f"Procesando {total} bonos soberanos...\n")
        resultados = {}
        errores = []
        for i, bono_cfg in enumerate(BONOS_A_ACTUALIZAR, 1):
            sim = bono_cfg["simbolo"]
            mdo = bono_cfg["mercado"]
            print(f"[{i}/{total}] {sim}...", end=" ", flush=True)
            try:
                datos = obtener_bono_completo(mdo, sim, dias_cache=0)
                if "error" in datos:
                    print(f"ERROR: {datos['error']}")
                    errores.append(f"{sim}: {datos['error']}")
                    continue
                bono_json = convertir_a_bonos_json(datos, ticker_api=sim)
                resultados[sim] = bono_json
                n_flujos = len(bono_json.get("flujos_futuros_cada_100_vn", []))
                print(f"OK ({n_flujos} flujos)")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"EXCEPCIÓN: {e}")
                errores.append(f"{sim}: {e}")

        if resultados:
            mergear_bonos_json(resultados, sobrescribir=args.sobrescribir)

        print(f"\n{'='*50}")
        print(f"Exitosos: {len(resultados)}")
        print(f"Errores:  {len(errores)}")
        if errores:
            print("\nDetalles errores:")
            for e in errores:
                print(f"  - {e}")

    elif args.legacy:
        print(f"Procesando {len(bonos_a_procesar_legacy)} bonos (legacy)...")
        json_final = {"bonos": {}}
        for bono in bonos_a_procesar_legacy:
            datos = procesar_bono(bono["mercado"], bono["simbolo"], dias_cache=0)
            if datos:
                json_final["bonos"][datos["simbolo"]] = datos
        with open('estructura_bonos.json', 'w', encoding='utf-8') as f:
            json.dump(json_final, f, indent=4, ensure_ascii=False)
        print(f"OK: estructura_bonos.json con {len(json_final['bonos'])} bonos")

    else:
        ap.print_help()