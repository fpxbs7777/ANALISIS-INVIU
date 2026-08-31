import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

CACHE_FILE = "cache_fundamentales.json"
CACHE_DIAS = 90
RATE_LIMIT_SEG = 2.5
ROBOTS_URL = "https://iol.invertironline.com/robots.txt"

MESES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

NUMEROS_PALABRA = {
    'un': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
    'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
    'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15,
    'dieciseis': 16, 'dieciséis': 16, 'diecisiete': 17, 'dieciocho': 18,
    'diecinueve': 19, 'veinte': 20, 'veintiun': 21, 'veintiún': 21,
    'veintiuno': 21, 'veintiuna': 21, 'veintidos': 22, 'veintidós': 22,
    'veintitres': 23, 'veintitrés': 23, 'veinticuatro': 24, 'veinticinco': 25,
    'veintiseis': 26, 'veintiséis': 26, 'veintisiete': 27, 'veintiocho': 28,
    'veintinueve': 29, 'treinta': 30
}

_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})
_last_request_time = 0


def _rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_SEG:
        time.sleep(RATE_LIMIT_SEG - elapsed)
    _last_request_time = time.time()


def check_robots_txt():
    try:
        r = requests.get(ROBOTS_URL, timeout=10)
        if r.status_code == 200 and 'Disallow' in r.text:
            for line in r.text.splitlines():
                if '/titulo/cotizacion/' in line and 'Disallow' in line:
                    print("ADVERTENCIA: robots.txt disallows /titulo/cotizacion/")
                    print("Batch scraping masivo puede violar los términos de uso.")
                    print("Continuá solo si tenés permiso explícito.")
                    return False
        print("robots.txt OK: /titulo/cotizacion/ no está disallowed (o no se encontró regla).")
        return True
    except Exception as e:
        print(f"No se pudo verificar robots.txt ({e}). Procediendo con precaución.")
        return True


def cargar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def guardar_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _fecha_dict_a_iso(d, m, y):
    mm = MESES.get(m.lower().strip(), m.strip().zfill(2))
    return f"{int(y):04d}-{int(mm):02d}-{int(d):02d}"


def _fecha_str_a_iso(fecha_str):
    fecha_str = fecha_str.strip()
    m_dmy = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', fecha_str)
    if m_dmy:
        d, m, y = m_dmy.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    m_texto = re.match(r'^(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})$', fecha_str, re.IGNORECASE)
    if m_texto:
        d, mes_texto, y = m_texto.groups()
        return _fecha_dict_a_iso(d, mes_texto, y)
    return None


def _palabra_a_numero(palabra):
    p = palabra.lower().strip()
    return NUMEROS_PALABRA.get(p)


def _extraer_numero_entre_parentesis(texto):
    m = re.search(r'\((\d+)\)', texto)
    return int(m.group(1)) if m else None


def _floats_approx_equal(a, b, tol=1e-9):
    return abs(a - b) < tol


def resolver_url(mercado, simbolo):
    """
    Fase 1: Resuelve la URL automáticamente.
    Estrategia 1: Sin slug + allow_redirects (no funciona, no redirige).
    Estrategia 2: Placeholder slug (funciona, slug no se valida).
    """
    url = f"https://iol.invertironline.com/titulo/cotizacion/{mercado}/{simbolo}"
    _rate_limit()
    r = _session.get(url, allow_redirects=True, timeout=15)
    if r.status_code == 200:
        id_titulo = _extract_id_titulo(r.text)
        if id_titulo:
            return {
                "url_base": r.url,
                "id_titulo": id_titulo,
                "slug_placeholder": True
            }
    url_placeholder = f"{url}/x/fundamentalesTecnicos"
    _rate_limit()
    r = _session.get(url_placeholder, timeout=15)
    if r.status_code == 200:
        id_titulo = _extract_id_titulo(r.text)
        if id_titulo:
            return {
                "url_base": url_placeholder,
                "id_titulo": id_titulo,
                "slug_placeholder": True
            }
    return {"error": "No se pudo resolver la URL automáticamente."}


def _extract_id_titulo(html):
    m = re.search(r'idTitulo[:\s]+(\d+)', html)
    if m:
        return m.group(1)
    m = re.search(r'data-tituloid="(\d+)"', html, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def obtener_tabla_api(id_titulo):
    """
    Fase 2: Obtiene la tabla técnica via API interna AJAX.
    No necesita Selenium.
    """
    _rate_limit()
    r = _session.post(
        "https://iol.invertironline.com/Titulo/FundamentalesTecnicosBonos",
        data={'id': id_titulo},
        headers={
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': f'https://iol.invertironline.com/titulo/cotizacion/BCBA/{id_titulo}/x/fundamentalesTecnicos',
        },
        timeout=15
    )
    if r.status_code != 200:
        return {"error": f"API returned status {r.status_code}"}
    return r.text


def parsear_tabla_cruda(html):
    """Parsea el HTML de la tabla a dict clave-valor."""
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    for t in soup.find_all('table'):
        for tr in t.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                data[key] = val
    return data


def parsear_interes(texto):
    """
    Fase 3: Parsea el campo 'Interés'.
    Patrón A: Tasa fija simple (ej. TO26)
    Patrón B: Step-up con tramos (ej. AL30, AE38)
    """
    resultado = {
        "cronogramaCupon": [],
        "frecuenciaCupon": None,
        "tasaCuponAnual": None,
        "fechasPagoRecurrentes": None,
        "texto_original": texto,
        "texto_truncado": False,
        "requiere_revision_manual": False
    }

    if not texto or texto == "N/A":
        resultado["requiere_revision_manual"] = True
        return resultado

    # Detectar truncamiento: tramo step-up incompleto (ej. termina en "Del ")
    if re.search(r'(?:^|\.\s*)[ivx]+\.\s*Del\s+\d+\s+de\s+\w+\s*$', texto.strip(), re.IGNORECASE):
        resultado["texto_truncado"] = True

    # Patrón A: Tasa fija simple
    pa = re.search(
        r'Tasa fija del ([\d,]+)%\s*anual.*?pagaderos por semestre vencido los (\d{1,2}/\d{1,2}) y (\d{1,2}/\d{1,2})',
        texto, re.IGNORECASE | re.DOTALL
    )
    if not pa:
        pa = re.search(
            r'Tasa fija del ([\d,]+)%\s*anual.*?semestre vencido los (\d{1,2}/\d{1,2}) y (\d{1,2}/\d{1,2})',
            texto, re.IGNORECASE | re.DOTALL
        )
    if pa:
        tasa_str = pa.group(1).replace(',', '.')
        resultado["tasaCuponAnual"] = float(tasa_str)
        resultado["frecuenciaCupon"] = "semiannual"
        resultado["fechasPagoRecurrentes"] = [pa.group(2), pa.group(3)]
        resultado["cronogramaCupon"] = [{
            "tasaAnual": float(tasa_str)
        }]
        return resultado

    # Patrón B: Step-up con tramos
    # Try primary: capture desde, hasta, tasa (with (exclusive) marker)
    tramos_raw = re.findall(
        r'Del\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\s*\(inclusive\)\s+al\s+'
        r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}|\w+\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|vencimiento)\s*'
        r'(?:\(exclusive\))?:\s*([\d,]+)\s*%',
        texto, re.IGNORECASE
    )
    # Fallback: capture desde + tasa (handles last tramo w/o (inclusive))
    tramos_simple = re.findall(
        r'Del\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})(?:\s*\(inclusive\))?.*?:\s*([\d,]+)\s*%',
        texto, re.IGNORECASE
    )
    if tramos_simple and len(tramos_simple) > len(tramos_raw):
        tramos_raw = tramos_simple

    if tramos_raw:
        crono = []
        items = tramos_raw if isinstance(tramos_raw[0], (list, tuple)) else [(tramos_raw[0], None, tramos_raw[1])]
        for raw in tramos_raw:
            if len(raw) == 3:
                desde, _, tasa_str = raw
            elif len(raw) == 2:
                desde, tasa_str = raw
            else:
                continue
            fecha_desde = _fecha_str_a_iso(desde)
            try:
                tasa = float(tasa_str.replace(',', '.'))
            except (ValueError, AttributeError):
                continue
            crono.append({
                "fecha_desde": fecha_desde,
                "tasaAnual": tasa
            })
        resultado["frecuenciaCupon"] = "semiannual"
        resultado["cronogramaCupon"] = crono
        return resultado

    resultado["requiere_revision_manual"] = True
    return resultado


def parsear_amortizacion(texto, frecuencia_cupon="semiannual"):
    """
    Fase 3: Parsea el campo 'Forma de amortización'.
    Patrón A: Bullet (ej. TO26)
    Patrón B: Cuotas con % distintos (ej. AL30)
    Patrón C: Cuotas iguales (ej. AE38)
    """
    resultado = {
        "tipoAmortizacion": None,
        "numCuotas": None,
        "porcentajePrimeraCuota": None,
        "porcentajeCuotasRestantes": None,
        "fechaPrimeraCuota": None,
        "fechaUltimaCuota": None,
        "cronogramaAmortizacion": [],
        "texto_original": texto,
        "texto_truncado": False,
        "requiere_revision_manual": False
    }

    if not texto or texto == "N/A":
        resultado["requiere_revision_manual"] = True
        return resultado

    # Patrón A: Bullet
    pa = re.search(r'En su totalidad al vencim\w{3,6}\s*el\s+(\d{1,2}/\d{1,2}/\d{4})', texto, re.IGNORECASE)
    if pa:
        fecha_vto = _fecha_str_a_iso(pa.group(1))
        resultado["tipoAmortizacion"] = "bullet"
        resultado["numCuotas"] = 1
        resultado["porcentajeCuota"] = 100.0
        resultado["fechaPrimeraCuota"] = fecha_vto
        resultado["fechaUltimaCuota"] = fecha_vto
        resultado["cronogramaAmortizacion"] = [{
            "numero_cuota": 1,
            "fecha_pago": fecha_vto,
            "porcentaje_capital": 100.0
        }]
        return resultado

    # Patrón B: Cuotas con % distintos (AL30)
    pb = re.search(
        r'en\s+(\w+)\s*\((\d+)\)\s+cuotas\s+semestrales.*?'
        r'primera\s+cuota\s+representativa\s+del\s+([\d,]+)%'
        r'.*?restantes\s+(\w+)\s+equivalentes\s+al\s+([\d,]+)%'
        r'.*?primera\s+cuota\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
        r'.*?ultima\s+cuota\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        texto, re.IGNORECASE | re.DOTALL
    )

    if pb:
        num_cuotas = int(pb.group(2))
        pct_primera = float(pb.group(3).replace(',', '.'))
        pct_restantes = float(pb.group(5).replace(',', '.'))
        fecha_primera = _fecha_str_a_iso(pb.group(6))
        fecha_ultima = _fecha_str_a_iso(pb.group(7))

        resultado["tipoAmortizacion"] = "cuotas_progresivas"
        resultado["numCuotas"] = num_cuotas
        resultado["porcentajePrimeraCuota"] = pct_primera
        resultado["porcentajeCuotasRestantes"] = pct_restantes
        resultado["fechaPrimeraCuota"] = fecha_primera
        resultado["fechaUltimaCuota"] = fecha_ultima

        resultado["cronogramaAmortizacion"] = _generar_cronograma_cuotas(
            num_cuotas, pct_primera, pct_restantes, fecha_primera, fecha_ultima
        )
        return resultado

    # Patrón C: Cuotas iguales (AE38)
    pc = re.search(
        r'en\s+(\w+)\s*\((\d+)\)\s+cuotas\s+semestrales\s+iguales.*?'
        r'primera\s+cuota\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
        r'.*?ultima\s+cuota\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        texto, re.IGNORECASE | re.DOTALL
    )
    if pc:
        num_cuotas = int(pc.group(2))
        pct_cuota = 100.0 / num_cuotas
        fecha_primera = _fecha_str_a_iso(pc.group(3))
        fecha_ultima = _fecha_str_a_iso(pc.group(4))

        resultado["tipoAmortizacion"] = "cuotas_iguales"
        resultado["numCuotas"] = num_cuotas
        resultado["porcentajeCuota"] = pct_cuota
        resultado["fechaPrimeraCuota"] = fecha_primera
        resultado["fechaUltimaCuota"] = fecha_ultima

        resultado["cronogramaAmortizacion"] = _generar_cronograma_cuotas(
            num_cuotas, pct_cuota, pct_cuota, fecha_primera, fecha_ultima, todas_iguales=True
        )
        return resultado

    resultado["requiere_revision_manual"] = True
    return resultado


def _generar_cronograma_cuotas(num_cuotas, pct_primera, pct_restantes,
                                fecha_primera_str, fecha_ultima_str,
                                todas_iguales=False):
    """Genera el cronograma de amortización con fechas semestrales exactas."""
    if not fecha_primera_str or not fecha_ultima_str:
        return []

    try:
        f_primera = datetime.strptime(fecha_primera_str, "%Y-%m-%d")
        f_ultima = datetime.strptime(fecha_ultima_str, "%Y-%m-%d")
    except ValueError:
        return []

    if num_cuotas == 1:
        return [{
            "numero_cuota": 1,
            "fecha_pago": fecha_ultima_str,
            "porcentaje_capital": round(100.0, 4),
        }]

    # Generate semiannual dates from primera to ultima
    crono = []
    dia = f_primera.day
    for i in range(num_cuotas):
        meses_adelante = i * 6
        m = f_primera.month + meses_adelante
        y = f_primera.year
        while m > 12:
            m -= 12
            y += 1
        try:
            fecha = datetime(y, m, min(dia, 28))
        except ValueError:
            fecha = datetime(y, m, 1)

        pct = pct_primera if (i == 0 and not todas_iguales) else pct_restantes
        crono.append({
            "numero_cuota": i + 1,
            "fecha_pago": fecha.strftime("%Y-%m-%d"),
            "porcentaje_capital": round(pct, 4),
        })

    # Force last date
    if crono:
        crono[-1]["fecha_pago"] = fecha_ultima_str

    return crono


def _determinar_fechas_pago(frecuencia, fecha_emision, fecha_vencimiento,
                            fechas_pago_recurrentes=None, fecha_primera_cuota=None,
                            fecha_ultima_cuota=None):
    if frecuencia != "semiannual":
        return []

    meses_pago = set()
    dia_pago = None

    if fechas_pago_recurrentes:
        for fp in fechas_pago_recurrentes:
            m = re.match(r'(\d{1,2})/(\d{1,2})', fp)
            if m:
                d, mes = int(m.group(1)), int(m.group(2))
                meses_pago.add(mes)
                dia_pago = d

    if not meses_pago and fecha_primera_cuota:
        try:
            fpc = datetime.strptime(fecha_primera_cuota, "%Y-%m-%d")
            d, m = fpc.day, fpc.month
            dia_pago = d
            meses_pago.add(m)
            m2 = m - 6 if m > 6 else m + 6
            meses_pago.add(m2)
        except ValueError:
            pass

    if not meses_pago and fecha_vencimiento:
        d, m = fecha_vencimiento.day, fecha_vencimiento.month
        if dia_pago is None:
            dia_pago = d
        meses_pago.add(m)
        m2 = m - 6 if m > 6 else m + 6
        meses_pago.add(m2)

    if not meses_pago or not dia_pago:
        return []

    fechas = []

    def _first_payment_after(ref, months, day):
        best = None
        for m in months:
            for y in (ref.year, ref.year + 1):
                try:
                    cand = datetime(y, m, day)
                except ValueError:
                    cand = datetime(y, m, 1)
                if cand > ref and (best is None or cand < best):
                    best = cand
        return best

    primer_pago = _first_payment_after(fecha_emision or datetime(2020, 1, 1), sorted(meses_pago), dia_pago)
    if primer_pago is None:
        return []

    actual = primer_pago
    month_cycle = sorted(meses_pago)
    safety = 0
    while actual <= (fecha_vencimiento or actual) and safety < 200:
        fechas.append(actual)
        safety += 1
        current_m = actual.month
        current_y = actual.year
        next_m = current_m + 6
        next_y = current_y
        if next_m > 12:
            next_m -= 12
            next_y += 1
        try:
            actual = datetime(next_y, next_m, dia_pago)
        except ValueError:
            actual = datetime(next_y, next_m, 1)

    if fecha_vencimiento and (not fechas or fechas[-1] != fecha_vencimiento):
        fechas.append(fecha_vencimiento)

    return fechas


def _make_date(year, month, day):
    try:
        return datetime(year, month, day)
    except ValueError:
        return datetime(year, month, 1)


def generar_flujos_futuros(interes_data, amortizacion_data,
                           fecha_emision_str, fecha_vencimiento_str):
    """
    Fase 4: Genera el array completo de flujos futuros.
    Filtra solo flujos con fecha > hoy.
    """
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    flujos = []

    try:
        f_emision = datetime.strptime(fecha_emision_str, "%Y-%m-%d") if fecha_emision_str else None
        f_vencimiento = datetime.strptime(fecha_vencimiento_str, "%Y-%m-%d") if fecha_vencimiento_str else None
    except (ValueError, TypeError):
        return flujos

    if not f_vencimiento:
        return flujos

    cronograma_cupon = interes_data.get("cronogramaCupon", []) if interes_data else []
    fechas_pago_recurrentes = interes_data.get("fechasPagoRecurrentes") if interes_data else None
    frecuencia = interes_data.get("frecuenciaCupon", "semiannual") if interes_data else "semiannual"

    amort_cronograma = amortizacion_data.get("cronogramaAmortizacion", []) if amortizacion_data else []
    fecha_primera_amort = amortizacion_data.get("fechaPrimeraCuota") if amortizacion_data else None
    fecha_ultima_amort = amortizacion_data.get("fechaUltimaCuota") if amortizacion_data else None

    fechas_pago = _determinar_fechas_pago(
        frecuencia, f_emision, f_vencimiento,
        fechas_pago_recurrentes, fecha_primera_amort, fecha_ultima_amort
    )

    if not fechas_pago:
        return flujos

    tramos_ordenados = sorted(cronograma_cupon, key=lambda x: x.get("fecha_desde", ""))

    # Build amort schedule lookup
    amort_lookup = {}
    for c in amort_cronograma:
        try:
            fd = datetime.strptime(c["fecha_pago"], "%Y-%m-%d")
            amort_lookup[fd.strftime("%Y-%m-%d")] = c["porcentaje_capital"]
        except (ValueError, KeyError):
            pass

    nominal_residual = 100.0
    total_capital_amortizado = 0.0

    for fecha_pago in fechas_pago:
        if fecha_pago <= hoy:
            continue

        tasa_vigente = _get_tasa_vigente(tramos_ordenados, fecha_pago)
        if tasa_vigente is None and tramos_ordenados:
            tasa_vigente = tramos_ordenados[-1].get("tasaAnual")

        if tasa_vigente is None:
            continue

        fecha_str = fecha_pago.strftime("%Y-%m-%d")
        amort_pct = amort_lookup.get(fecha_str, 0.0)

        cupon_efectivo = (tasa_vigente / 2.0) * (nominal_residual / 100.0)
        amort_monto = (amort_pct / 100.0) * nominal_residual if amort_pct > 0 else 0.0

        flujo = {
            "fecha_pago": fecha_str,
            "tasa_anual_vigente": tasa_vigente,
            "nominal_residual_inicial": round(nominal_residual, 6),
            "cupon_efectivo": round(cupon_efectivo, 6),
            "amortizacion_pct": amort_pct,
            "amortizacion_monto": round(amort_monto, 6),
            "flujo_total": round(cupon_efectivo + amort_monto, 6),
        }
        flujos.append(flujo)

        nominal_residual -= amort_monto
        total_capital_amortizado += amort_monto

        if nominal_residual <= 0.01:
            break

    return flujos


def _sumar_semestre(fecha):
    """Suma 6 meses (180 días en base 30/360 o sumando 6 meses al mes)."""
    mes = fecha.month + 6
    anio = fecha.year
    if mes > 12:
        mes -= 12
        anio += 1
    dia = min(fecha.day, [31, 29 if anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0) else 28,
                          31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    try:
        return fecha.replace(year=anio, month=mes, day=dia)
    except ValueError:
        return fecha.replace(year=anio, month=mes, day=fecha.day)


def _get_tasa_vigente(tramos, fecha):
    if not tramos:
        return None
    if len(tramos) == 1 and "tasaAnual" in tramos[0] and "fecha_desde" not in tramos[0]:
        return tramos[0]["tasaAnual"]

    for i, tramo in enumerate(tramos):
        fd_str = tramo.get("fecha_desde")
        if not fd_str:
            continue
        try:
            fd = datetime.strptime(fd_str, "%Y-%m-%d")
        except ValueError:
            continue
        if i + 1 < len(tramos):
            fh_str = tramos[i + 1].get("fecha_desde")
            if fh_str:
                try:
                    fh = datetime.strptime(fh_str, "%Y-%m-%d")
                    if fd <= fecha < fh:
                        return tramo["tasaAnual"]
                except ValueError:
                    continue
        else:
            if fd <= fecha:
                return tramo["tasaAnual"]
    return tramos[-1]["tasaAnual"] if tramos else None


def obtener_bono_completo(mercado, simbolo, codigo_isin=None, dias_cache=CACHE_DIAS):
    """
    Función principal que encadena todo el pipeline.
    """
    cache = cargar_cache()
    cache_key = codigo_isin or f"{mercado}_{simbolo}"

    if cache_key in cache:
        entry = cache[cache_key]
        ts = entry.get("timestamp", "")
        try:
            ts_dt = datetime.fromisoformat(ts)
            if (datetime.now() - ts_dt).days < dias_cache:
                print(f"Cache hit para {cache_key} ({ts})")
                return entry["data"]
        except ValueError:
            pass

    print(f"Scrapeando {simbolo} ({mercado})...")

    res = resolver_url(mercado, simbolo)
    if "error" in res:
        return {"error": res["error"]}

    id_titulo = res["id_titulo"]
    html_tabla = obtener_tabla_api(id_titulo)
    if isinstance(html_tabla, dict) and "error" in html_tabla:
        return html_tabla

    datos_crudos = parsear_tabla_cruda(html_tabla)
    if "error" in datos_crudos:
        return datos_crudos

    def _buscar_campo(claves_posibles, excluir=None):
        for k, v in datos_crudos.items():
            k_clean = k.lower().replace('\ufffd', '')
            if excluir and excluir.lower() in k_clean:
                continue
            for cp in claves_posibles:
                if cp.lower() in k_clean:
                    return v
        return ""

    moneda_raw = _buscar_campo(["Moneda de emision", "Moneda de emisi"])
    moneda_map = {"Pesos": "ARS", "Dolares": "USD", "Dólares": "USD"}
    moneda = moneda_map.get(moneda_raw, moneda_raw)

    fecha_emision = _fecha_str_a_iso(_buscar_campo(["Fecha de Emision", "Fecha de Emisi"]))
    fecha_vencimiento = _fecha_str_a_iso(_buscar_campo(["Fecha Vencimiento"]))

    campo_interes = _buscar_campo(["Interes", "Inter", "Inter\u00e9s"], excluir="corridos")
    interes = parsear_interes(campo_interes)
    campo_amort = _buscar_campo(["Forma de amortizacion", "Forma de amortizaci", "Forma de amortizaci\u00f3n"])
    amortizacion = parsear_amortizacion(campo_amort)

    flujos = generar_flujos_futuros(
        interes,
        amortizacion,
        fecha_emision,
        fecha_vencimiento
    )

    denominacion = _buscar_campo(["Denominacion", "Denominaci"])
    tipo_especie = _buscar_campo(["Tipo de Especie"])
    tipo_bono = "Bono"
    if "obligacion" in tipo_especie.lower() or "obligaci" in tipo_especie.lower():
        tipo_bono = "Obligación Negociable (ON)"
    elif "titulos publicos" in tipo_especie.lower() or "titulos" in tipo_especie.lower():
        tipo_bono = "Bono"

    bono = {
        "simbolo": simbolo,
        "mercado": mercado,
        "codigo_isin": codigo_isin,
        "denominacion": denominacion,
        "emisor": datos_crudos.get("Emisor", ""),
        "tipo": tipo_bono,
        "moneda": moneda,
        "fecha_emision": fecha_emision,
        "fecha_vencimiento": fecha_vencimiento,
        "moneda_emision": moneda_raw,
        "monto_nominal_vigente": datos_crudos.get("Monto nominal vigente en la moneda original de emisión", ""),
        "monto_residual": datos_crudos.get("Monto residual en la moneda original de emisión", ""),
        "denominacion_minima": datos_crudos.get("Denominación mínima", ""),
        "tipo_garantia": datos_crudos.get("Tipo de garantía", ""),
        "ley": datos_crudos.get("Ley", ""),
        "base_calculo": {
            "dias_ano": 360,
            "dias_mes": 30,
            "meses_ano": 12
        },
        "convencion_dias": "30/360",
        "precio_es_dirty": True,
        "yield_convention": "ACT/360" if moneda == "ARS" else "30/360",
        "interes": interes,
        "amortizacion": amortizacion,
        "flujos_futuros": flujos,
        "datos_crudos": datos_crudos
    }

    cache[cache_key] = {
        "timestamp": datetime.now().isoformat(),
        "data": bono
    }
    guardar_cache(cache)

    return bono


def test_parser(mercado, simbolo, label=None):
    """Prueba el pipeline completo y muestra output."""
    if not label:
        label = simbolo
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    resultado = obtener_bono_completo(mercado, simbolo)
    if "error" in resultado:
        print(f"  ERROR: {resultado['error']}")
        return resultado

    print(f"\n  Denominación: {resultado['denominacion'][:80]}...")
    print(f"  Moneda: {resultado['moneda']}")
    print(f"  Emisión: {resultado['fecha_emision']}")
    print(f"  Vencimiento: {resultado['fecha_vencimiento']}")

    interes = resultado.get("interes", {})
    if interes.get("requiere_revision_manual"):
        print(f"  [!] Interes: requiere revision manual")
        print(f"    Texto: {interes.get('texto_original', '')[:100]}...")
    else:
        print(f"  Interes: {len(interes.get('cronogramaCupon', []))} tramo(s)")
        for t in interes.get("cronogramaCupon", []):
            print(f"    - Tasa {t.get('tasaAnual', '?')}% desde {t.get('fecha_desde', '?')}")

    amort = resultado.get("amortizacion", {})
    if amort.get("requiere_revision_manual"):
        print(f"  [!] Amortizacion: requiere revision manual")
        print(f"    Texto: {amort.get('texto_original', '')[:100]}...")
    else:
        print(f"  Amortización: {amort.get('tipoAmortizacion')}, {amort.get('numCuotas')} cuota(s)")
        print(f"    Primera: {amort.get('fechaPrimeraCuota', '?')}, Última: {amort.get('fechaUltimaCuota', '?')}")
        for c in amort.get("cronogramaAmortizacion", []):
            print(f"    Cuota {c['numero_cuota']}: {c['fecha_pago']} {c['porcentaje_capital']}%")

    flujos = resultado.get("flujos_futuros", [])
    print(f"\n  Flujos futuros pendientes: {len(flujos)}")
    for f in flujos[:5]:
        print(f"    {f['fecha_pago']}: cupón={f['cupon_efectivo']:.4f}, amort={f['amortizacion_pct']}%")
    if len(flujos) > 5:
        print(f"    ... y {len(flujos) - 5} más")

    return resultado


if __name__ == "__main__":
    import sys

    if "--check-robots" in sys.argv:
        check_robots_txt()
    elif "--test" in sys.argv:
        check_robots_txt()
        test_parser("BCBA", "TO26", "TO26 (Tasa Fija, Bullet)")
        test_parser("BCBA", "AE38", "AE38 (Step-up truncado, Cuotas iguales)")
        test_parser("BCBA", "AL30", "AL30 (Step-up completo, Cuotas progresivas)")
    elif len(sys.argv) >= 3:
        mercado = sys.argv[1]
        simbolo = sys.argv[2]
        isin = sys.argv[3] if len(sys.argv) >= 4 else None
        resultado = obtener_bono_completo(mercado, simbolo, codigo_isin=isin)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        check_robots_txt()
        resultados = {}
        for sim in ["TO26", "AE38", "AL30"]:
            resultados[sim] = test_parser("BCBA", sim)
        with open("test_fundamentales_output.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print("\nOutput guardado en test_fundamentales_output.json")
