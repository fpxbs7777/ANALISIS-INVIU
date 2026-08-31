# -*- coding: utf-8 -*-
"""
Informe BERTUCCI (cuenta 264900) - captura de datos REALES 04/08/2026
Fuentes: IOL API v2 (portafolio, cotizaciones, seriehistorica) | DolarAPI |
         ArgDatos (riesgo pais) | BCRA (reservas) | yfinance (fundamentales y series)
Salida: informe_bertucci_datos_YYYYMMDD.json
"""
import requests, json, re, sys, time
from datetime import datetime, timedelta

BASE = 'https://api.invertironline.com'
OUT = 'informe_bertucci_datos_%s.json' % datetime.now().strftime('%Y%m%d')

# ----------------------------------------------------------------- credenciales (se leen de archivos existentes del pipeline, sin imprimir)
def load_creds():
    creds = []
    for f in [r'clientes/panelescotizaciones.txt', r'clientes/SERIESHISTORICASSIMULTANEO.txt',
              r'clientes/calculadora tir bonos.py', r'coronar bases/tir_copy.py']:
        try:
            txt = open(f, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        m = re.search(r"username\s*=\s*['\"]([^'\"]+)['\"]", txt)
        p = re.search(r"password\s*=\s*['\"]([^'\"]+)['\"]", txt)
        if m and p:
            creds.append((m.group(1), p.group(1)))
    return creds

def iol_token(user, pwd):
    try:
        r = requests.post(BASE + '/token',
                          data={'username': user, 'password': pwd, 'grant_type': 'password'},
                          timeout=20)
        if r.status_code == 200:
            return r.json().get('access_token')
    except Exception as e:
        print('token err:', e)
    return None

def iol_get(token, path, params=None):
    try:
        r = requests.get(BASE + path, headers={'Authorization': 'Bearer ' + token,
                                               'Accept': 'application/json'},
                         params=params, timeout=40)
        if r.status_code == 200:
            return r.json()
        return {'error': r.status_code, 'body': r.text[:200]}
    except Exception as e:
        return {'error': 'exc', 'body': str(e)[:200]}

# ----------------------------------------------------------------- autenticación IOL (prueba ambas credenciales conocidas)
print('[1] Auth IOL ...')
token = None
for u, p in load_creds():
    t = iol_token(u, p)
    if t:
        token = t
        print('   OK token (usuario %s)' % u)
        break
if not token:
    print('   [PENDIENTE] no se pudo autenticar IOL')
    sys.exit(2)

# ----------------------------------------------------------------- 1) portafolio real
print('[2] Portafolio IOL ...')
port = iol_get(token, '/api/v2/portafolio/argentina')
posiciones = []
if isinstance(port, list):
    for a in port:
        t = a.get('titulo', {})
        posiciones.append({
            'simbolo': t.get('simbolo'),
            'descripcion': t.get('descripcion'),
            'tipo': t.get('tipo'),
            'moneda': t.get('moneda'),
            'cantidad': a.get('cantidad'),
            'ultimoPrecio': a.get('ultimoPrecio'),
            'ppc': a.get('ppc'),
            'gananciaPorcentaje': a.get('gananciaPorcentaje'),
            'gananciaDinero': a.get('gananciaDinero'),
            'valorizado': a.get('valorizado'),
            'variacionDiaria': a.get('variacionDiaria'),
        })
    print('   %d posiciones' % len(posiciones))
else:
    print('   portafolio respuesta no esperada:', str(port)[:300])

# ----------------------------------------------------------------- 2) cotizaciones masivas (cedears + acciones ARG)
print('[3] Cotizaciones IOL ...')
QUOTES = {}
for instrumento, pais in [('cedears', 'argentina'), ('acciones', 'argentina')]:
    d = iol_get(token, '/api/v2/Cotizaciones/%s/%s/Todos' % (instrumento, pais))
    if isinstance(d, dict) and 'titulos' in d:
        for t in d['titulos']:
            sim = t.get('simbolo')
            if sim:
                QUOTES[sim] = {
                    'ultimoPrecio': t.get('ultimoPrecio'),
                    'puntosVariacion': t.get('puntosVariacion'),
                    'variacionPorcentual': t.get('variacionPorcentual'),
                    'cierreAnterior': t.get('cierreAnterior'),
                    'precioPromedio': t.get('precioPromedio'),
                    'montoOperado': t.get('montoOperado'),
                    'volumen': t.get('volumen'),
                    'maximo': t.get('maximo'),
                    'minimo': t.get('minimo'),
                    'fechaHora': t.get('fechaHora'),
                }
    else:
        print('   cotizaciones %s: respuesta no esperada' % instrumento, str(d)[:200])
print('   %d cotizaciones capturadas' % len(QUOTES))

# ----------------------------------------------------------------- 3) serie histórica IOL (12 meses, ajustada) para técnicos en ARS
print('[4] Serie historica IOL (12m) ...')
SERIES_IOL = {}
SIMBOLOS = ['PAMP', 'AMZN', 'GOOGL', 'MP', 'MSFT', 'NVDA', 'SMH', 'SPY', 'TSM', 'URA']
hasta = datetime.now().strftime('%Y-%m-%d')
desde = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
for sim in SIMBOLOS:
    for mercado in ['BCBA']:
        s = iol_get(token, '/api/v2/%s/Titulos/%s/Cotizacion/seriehistorica/%s/%s/True' % (mercado, sim, desde, hasta))
        if isinstance(s, list) and len(s) > 60:
            # formato IOL: cada item {fecha, precioAjustado?, ...} -> normalizar
            claves = [k for k in s[0].keys()]
            px = None
            for c in ['precioAjustado', 'precio', 'ultimoPrecio', 'cierre']:
                if c in s[0]:
                    px = c
                    break
            if px:
                SERIES_IOL[sim] = {'fechas': [x.get('fecha') for x in s],
                                   'precios': [x.get(px) for x in s]}
            break
        elif isinstance(s, dict) and 'error' in s:
            print('   serie %s: error %s' % (sim, s['error']))
            break
print('   series IOL ok:', list(SERIES_IOL.keys()))

# ----------------------------------------------------------------- 4) macro Argentina (DolarAPI + ArgDatos + BCRA)
print('[5] Macro Argentina ...')
macro = {}
try:
    r = requests.get('https://dolarapi.com/v1/dolares', timeout=20)
    if r.status_code == 200:
        for d in r.json():
            casa = d.get('casa', '').lower()
            if 'oficial' in casa: macro['dolar_oficial'] = d.get('venta')
            if 'bolsa' in casa: macro['dolar_mep'] = d.get('venta')
            if 'contadoconliqui' in casa: macro['dolar_ccl'] = d.get('venta')
            if 'blue' in casa: macro['dolar_blue'] = d.get('venta')
except Exception as e:
    print('   dolarapi err:', e)
try:
    r = requests.get('https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo', timeout=20)
    if r.status_code == 200:
        d = r.json()
        macro['riesgo_pais'] = (d[0].get('valor') if isinstance(d, list) and d else d.get('valor'))
except Exception as e:
    print('   argendatos err:', e)
try:
    r = requests.get('https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/18', timeout=20)
    if r.status_code == 200:
        d = r.json()
        det = d.get('results', [{}])[0].get('detalle', [])
        macro['reservas_usd'] = det[-1].get('valor') if det else None
except Exception as e:
    print('   bcra err:', e)
print('   macro:', json.dumps(macro, ensure_ascii=False))

# ----------------------------------------------------------------- 5) yfinance: fundamentales + series + factores intermarket
print('[6] yfinance ...')
yf = None
try:
    import yfinance as yf
except Exception as e:
    print('   yfinance no disponible:', e)

YF_TICKERS = ['MSFT', 'NVDA', 'AMZN', 'GOOGL', 'TSM', 'MP', 'SPY', 'SMH', 'URA']
FACTORES = {'^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', '^VIX': 'VIX', 'DX-Y.NYB': 'Dolar Index',
            'GC=F': 'Oro', 'CL=F': 'Petroleo WTI', 'HG=F': 'Cobre', '^TNX': 'Treasury 10Y',
            '^TYX': 'Treasury 30Y', '^IRX': 'Treasury 3M', '^MERV': 'Merval'}
fundamentales, series_yf, factores_vals = {}, {}, {}
if yf:
    for tk in YF_TICKERS:
        try:
            info = yf.Ticker(tk).info
            fundamentales[tk] = {
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'marketCap': info.get('marketCap'),
                'dividendYield': info.get('dividendYield'),
                'profitMargins': info.get('profitMargins'),
                'returnOnEquity': info.get('returnOnEquity'),
                'revenueGrowth': info.get('revenueGrowth'),
                'earningsGrowth': info.get('earningsGrowth'),
                'debtToEquity': info.get('debtToEquity'),
                'priceToBook': info.get('priceToBook'),
                'beta': info.get('beta'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'longName': info.get('longName'),
                'currentPrice': info.get('currentPrice') or info.get('regularMarketPrice'),
                'totalRevenue': info.get('totalRevenue'),
                'freeCashflow': info.get('freeCashflow'),
                'totalDebt': info.get('totalDebt'),
                'totalCash': info.get('totalCash'),
            }
        except Exception as e:
            fundamentales[tk] = {'error': str(e)[:150]}
    for tk in YF_TICKERS + ['PAMP.BA']:
        try:
            h = yf.Ticker(tk).history(period='1y')
            if len(h):
                series_yf[tk] = {'fechas': [str(x.date()) for x in h.index],
                                 'close': [float(x) for x in h['Close'].dropna()]}
        except Exception as e:
            print('   serie %s err: %s' % (tk, str(e)[:100]))
    for tk in FACTORES:
        try:
            h = yf.Ticker(tk).history(period='6mo')
            if len(h):
                c = h['Close'].dropna()
                factores_vals[tk] = {'nombre': FACTORES[tk], 'ultimo': float(c.iloc[-1]),
                                     'hace1m': float(c.iloc[-30]) if len(c) > 30 else None,
                                     'hace6m': float(c.iloc[0]) if len(c) > 5 else None,
                                     'min': float(c.min()), 'max': float(c.max())}
        except Exception as e:
            print('   factor %s err: %s' % (tk, str(e)[:100]))

# ----------------------------------------------------------------- guardar
out = {
    'fecha_captura': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'posiciones_iol': posiciones,
    'cotizaciones_iol': QUOTES,
    'series_iol_ars': SERIES_IOL,
    'macro': macro,
    'fundamentales_yf': fundamentales,
    'series_yf': series_yf,
    'factores_yf': factores_vals,
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('[7] Guardado en', OUT)
print('RESUMEN: %d posiciones | %d cotizaciones | %d series IOL | %d fundamentales | %d factores' % (
    len(posiciones), len(QUOTES), len(SERIES_IOL), len(fundamentales), len(factores_vals)))
