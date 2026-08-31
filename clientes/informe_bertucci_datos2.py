# -*- coding: utf-8 -*-
"""
Informe BERTUCCI (cuenta 264900) - captura de datos REALES 04/08/2026
Fuentes: Google Finance BCBA (cotizaciones CEDEAR/PAMP en ARS) | DolarAPI | ArgDatos |
         BCRA | yfinance (fundamentales, series 1y, factores intermarket)
Salida: informe_bertucci_datos_YYYYMMDD.json
Nota: IOL API devuelve 401 con todas las credenciales del repo -> se usa Google Finance
      para precios BYMA/CEDEAR en ARS (público, sin auth).
"""
import requests, json, re, time
from datetime import datetime, timedelta

OUT = 'informe_bertucci_datos_%s.json' % datetime.now().strftime('%Y%m%d')
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
       'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'}

SIMBOLOS = ['PAMP', 'AMZN', 'GOOGL', 'MP', 'MSFT', 'NVDA', 'SMH', 'SPY', 'TSM', 'URA']
NOMBRES = {'PAMP': 'Pampa Energia SA', 'AMZN': 'CEDEAR AMAZON INC', 'GOOGL': 'CEDEAR GOOGLE INC',
           'MP': 'CEDEAR MP MATERIALS CORP', 'MSFT': 'CEDEAR MICROSOFT CORP', 'NVDA': 'CEDEAR NVIDIA',
           'SMH': 'CEDEAR VAN ECK SEMICONDUCTOR ETF', 'SPY': 'CEDEAR SPDR S&P 500 ETF',
           'TSM': 'CEDEAR TAIWAN SEMICONDUCTOR', 'URA': 'CEDEAR GLOBAL X URANIUM ETF'}

# ----------------------------------------------------------------- 1) cotizaciones GF (BCBA)
def gf_quote(sim):
    url = 'https://www.google.com/finance/quote/%s:BCBA' % sim
    for intento in range(3):
        try:
            r = requests.get(url, headers=HDR, timeout=20)
            if r.status_code == 200:
                txt = r.text
                m = re.search(r'class="YMlKec fxKbKc">([^<]+)<', txt)
                precio = m.group(1).strip() if m else None
                m2 = re.search(r'data-last-price="([\d.]+)"', txt)
                if not precio and m2:
                    precio = m2.group(1)
                # variacion porcentual (sube/baja) y variacion absoluta
                varp = None
                m3 = re.search(r'class="P2Luy Ebnabc">([^<]+)<', txt)  # up
                m4 = re.search(r'class="P2Luy Ez2Ioe">([^<]+)<', txt)  # down
                if m3:
                    varp = m3.group(1).strip()
                elif m4:
                    varp = m4.group(1).strip()
                # prev close
                prev = None
                m5 = re.search(r'Previous close[^>]*>\s*([\d.,]+)', txt)
                if not m5:
                    m5 = re.search(r'class="P6K39c">([\d.,]+)</div>', txt)
                if m5:
                    prev = m5.group(1).strip()
                return {'simbolo': sim, 'precio': precio, 'varpct': varp, 'prevClose': prev}
            elif r.status_code == 429:
                time.sleep(3)
        except Exception as e:
            time.sleep(2)
    return {'simbolo': sim, 'error': 'no disponible'}

print('[1] Cotizaciones Google Finance BCBA ...')
cots = {}
for s in SIMBOLOS:
    c = gf_quote(s)
    cots[s] = c
    print('   %s -> %s' % (s, c.get('precio') or c.get('error')))
    time.sleep(1.2)

# ----------------------------------------------------------------- 2) macro Argentina
print('[2] Macro Argentina ...')
macro = {}
try:
    r = requests.get('https://dolarapi.com/v1/dolares', headers=HDR, timeout=20)
    if r.status_code == 200:
        for d in r.json():
            casa = d.get('casa', '').lower()
            if casa == 'oficial': macro['dolar_oficial'] = d.get('venta')
            if casa == 'bolsa': macro['dolar_mep'] = d.get('venta')
            if casa == 'contadoconliqui': macro['dolar_ccl'] = d.get('venta')
            if casa == 'blue': macro['dolar_blue'] = d.get('venta')
            if casa == 'tarjeta': macro['dolar_tarjeta'] = d.get('venta')
except Exception as e:
    print('   dolarapi err:', e)
try:
    r = requests.get('https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo', timeout=20)
    if r.status_code == 200:
        d = r.json()
        macro['riesgo_pais'] = (d[0].get('valor') if isinstance(d, list) and d else d.get('valor'))
        macro['riesgo_pais_fecha'] = (d[0].get('fecha') if isinstance(d, list) and d else d.get('fecha'))
except Exception as e:
    print('   argendatos err:', e)
print('   macro:', json.dumps(macro, ensure_ascii=False))

# ----------------------------------------------------------------- 3) yfinance
print('[3] yfinance ...')
import yfinance as yf, warnings
warnings.filterwarnings('ignore')

YF_TICKERS = ['MSFT', 'NVDA', 'AMZN', 'GOOGL', 'TSM', 'MP', 'SPY', 'SMH', 'URA']
FACTORES = {'^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', '^VIX': 'VIX', 'DX-Y.NYB': 'Dolar Index',
            'GC=F': 'Oro', 'CL=F': 'Petroleo WTI', 'HG=F': 'Cobre', '^TNX': 'Treasury 10Y',
            '^TYX': 'Treasury 30Y', '^IRX': 'Treasury 3M', '^MERV': 'Merval'}
fundamentales, series_yf, factores_vals = {}, {}, {}

def hist_clean(tk, period='1y'):
    try:
        h = yf.Ticker(tk).history(period=period)
        if len(h):
            c = h['Close'].dropna()
            if len(c):
                return {'fechas': [str(x.date()) for x in c.index], 'close': [float(x) for x in c]}
    except Exception as e:
        return {'error': str(e)[:120]}
    return {'error': 'sin datos'}

for tk in YF_TICKERS:
    try:
        info = yf.Ticker(tk).info
        fundamentales[tk] = {
            'trailingPE': info.get('trailingPE'), 'forwardPE': info.get('forwardPE'),
            'marketCap': info.get('marketCap'), 'dividendYield': info.get('dividendYield'),
            'profitMargins': info.get('profitMargins'), 'returnOnEquity': info.get('returnOnEquity'),
            'revenueGrowth': info.get('revenueGrowth'), 'earningsGrowth': info.get('earningsGrowth'),
            'debtToEquity': info.get('debtToEquity'), 'priceToBook': info.get('priceToBook'),
            'beta': info.get('beta'), 'sector': info.get('sector'), 'industry': info.get('industry'),
            'longName': info.get('longName'), 'currentPrice': info.get('currentPrice'),
            'totalRevenue': info.get('totalRevenue'), 'freeCashflow': info.get('freeCashflow'),
            'totalDebt': info.get('totalDebt'), 'totalCash': info.get('totalCash'),
            'trailingEps': info.get('trailingEps'), 'forwardEps': info.get('forwardEps'),
        }
        print('   fund %s OK (PE %.1f)' % (tk, info.get('trailingPE') or -1))
    except Exception as e:
        fundamentales[tk] = {'error': str(e)[:150]}
        print('   fund %s ERR %s' % (tk, str(e)[:80]))
for tk in YF_TICKERS:
    series_yf[tk] = hist_clean(tk)
    print('   serie %s: %d pts' % (tk, len(series_yf[tk].get('close', [])) if isinstance(series_yf.get(tk), dict) and 'close' in series_yf.get(tk, {}) else 0))
series_yf['PAMP.BA'] = hist_clean('PAMP.BA')
for tk in FACTORES:
    h = hist_clean(tk, '6mo')
    if h and 'close' in h:
        c = h['close']
        factores_vals[tk] = {'nombre': FACTORES[tk], 'ultimo': c[-1],
                             'hace1m': c[-30] if len(c) > 30 else None,
                             'hace6m': c[0] if len(c) > 5 else None}
        print('   factor %s = %.2f' % (tk, c[-1]))
    else:
        factores_vals[tk] = {'nombre': FACTORES[tk], 'error': 'sin datos'}
        print('   factor %s: sin datos' % tk)

out = {'fecha_captura': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
       'fuentes': {'cotizaciones_ars': 'Google Finance BCBA', 'macro': 'DolarAPI+ArgDatos+BCRA',
                   'fundamentales_series': 'yfinance', 'nota_iol': 'API IOL 401 con credenciales del repo'},
       'cotizaciones_ars': cots, 'macro': macro,
       'fundamentales_yf': fundamentales, 'series_yf': series_yf, 'factores_yf': factores_vals}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('[4] Guardado en', OUT)
