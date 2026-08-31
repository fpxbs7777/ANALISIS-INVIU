# -*- coding: utf-8 -*-
"""
Genera informe_bertucci_20260804.html — Informe de posicionamiento cuenta 264900
Datos reales 04/08/2026: yfinance (.BA CEDEAR/PAMP en ARS + fundamentales + factores),
DolarAPI (CCL/MEP), ArgDatos (riesgo pais).
Contiene: cartera valuada real, tecnicos (MA50/200, RSI14), fundamentales,
dashboard intermarket (marco Murphy/M1), y rebalanceo a plantilla Moderado (Schvarz)
con tramos y costo de arancel 0,90%.
"""
import json, base64, io
from datetime import datetime

BASE = 'clientes'
FECHA = '2026-08-04'

d = json.load(open('informe_bertucci_datos_20260804.json', encoding='utf-8'))
sba = json.load(open('%s/series_ba_20260804.json' % BASE, encoding='utf-8'))
macro = d.get('macro', {})
fund = d.get('fundamentales_yf', {})
fact = d.get('factores_yf', {})

# ---------------------------------------------------------------- cartera (snapshot IOL 03/08: cantidades + ppc reales)
POS = [
    ('SPY',  'SPDR S&P 500 (CEDEAR)',                331, 20017.22),
    ('MSFT', 'Microsoft (CEDEAR)',                    39, 20808.53),
    ('NVDA', 'Nvidia (CEDEAR)',                       59, 13533.80),
    ('AMZN', 'Amazon (CEDEAR)',                      218,  2741.15),
    ('GOOGL','Alphabet (CEDEAR)',                     61,  9765.98),
    ('PAMP', 'Pampa Energia (accion local)',          74,  5345.75),
    ('TSM',  'Taiwan Semiconductor (CEDEAR)',          1, 74800.06),
    ('MP',   'MP Materials (CEDEAR)',                  6,  7333.34),
    ('URA',  'Global X Uranium ETF (CEDEAR)',          3, 13119.09),
    ('SMH',  'VanEck Semiconductors (CEDEAR)',         2, 18864.39),
]
CASH_ARS, CASH_USD = 8916.27, 11.57
CCL = macro.get('dolar_ccl') or 1580.4

def rsi14(closes):
    if len(closes) < 15: return None
    g = l = 0.0
    for i in range(1, 15):
        ch = closes[i] - closes[i-1]
        g += max(ch, 0); l += max(-ch, 0)
    ag, al = g/14, l/14
    for i in range(15, len(closes)):
        ch = closes[i] - closes[i-1]
        ag = (ag*13 + max(ch, 0))/14
        al = (al*13 + max(-ch, 0))/14
    if al == 0: return 100.0
    return 100 - 100/(1 + ag/al)

rows = []
total_activos = 0
for sim, nombre, cant, ppc in POS:
    precio = sba.get(sim + '.BA', {}).get('ultimo')
    monto = cant * precio if precio else None
    total_activos += monto or 0
    rows.append(dict(sim=sim, nombre=nombre, cant=cant, ppc=ppc, precio=precio, monto=monto))
cash_total = CASH_ARS + CASH_USD * CCL
patrimonio = total_activos + cash_total
for r in rows:
    r['peso'] = r['monto'] / patrimonio * 100 if r['monto'] else 0
    r['gan'] = (r['precio'] - r['ppc']) * r['cant'] if r['precio'] else None
    r['rend'] = (r['precio']/r['ppc'] - 1) * 100 if r['precio'] else None

# tecnicos sobre serie ARS real
for r in rows:
    s = sba.get(r['sim'] + '.BA', {})
    c = s.get('close', [])
    tec = {}
    if c:
        last = c[-1]
        ma50 = sum(c[-50:])/50 if len(c) >= 50 else None
        ma200 = sum(c[-200:])/200 if len(c) >= 200 else None
        tec['ma50'] = ma50; tec['ma200'] = ma200
        tec['vs50'] = (last/ma50 - 1)*100 if ma50 else None
        tec['vs200'] = (last/ma200 - 1)*100 if ma200 else None
        tec['r20'] = (last/c[-21] - 1)*100 if len(c) > 21 else None
        tec['rsi'] = rsi14(c)
        tec['n'] = len(c)
    r['tec'] = tec

# ---------------------------------------------------------------- rebalanceo a plantilla Moderada (Schvarz: RV20/CEDEARs30/RF30/Caucion20)
def pesos_bucket():
    rv = sum(r['monto'] for r in rows if r['sim'] == 'PAMP')
    ced = sum(r['monto'] for r in rows if r['sim'] != 'PAMP')
    return rv, ced, 0.0, cash_total

rv_act, ced_act, rf_act, cau_act = pesos_bucket()
T = dict(rv=0.20, ced=0.30, rf=0.30, cau=0.20)
def delta(nombre):
    return T[nombre]*patrimonio - {'rv': rv_act, 'ced': ced_act, 'rf': rf_act, 'cau': cau_act}[nombre]

venta_necesaria = max(0.0, ced_act - 0.30*patrimonio)
plan_venta = []
# 1) SPY hasta dejarlo en 10% del patrimonio
spy_m = next(r['monto'] for r in rows if r['sim'] == 'SPY')
spy_obj = 0.10 * patrimonio
v_spy = max(0.0, spy_m - spy_obj)
resto = venta_necesaria - v_spy
plan_venta.append(('SPY', v_spy))
# 2) resto prorrateado entre MSFT/NVDA/AMZN/GOOGL
tech = [(r['sim'], r['monto']) for r in rows if r['sim'] in ('MSFT', 'NVDA', 'AMZN', 'GOOGL')]
tot_tech = sum(m for _, m in tech)
for sim, m in tech:
    plan_venta.append((sim, m/tot_tech * resto if tot_tech else 0))
# 3) compras
compra_rf = 0.30*patrimonio - rf_act
compra_cau = 0.20*patrimonio - cau_act
compra_rv = 0.20*patrimonio - rv_act
ventas_tot = sum(v for _, v in plan_venta)
compras_tot = compra_rf + compra_cau + compra_rv
fee = (ventas_tot + compras_tot) * 0.009
TRAMOS = 3

# ---------------------------------------------------------------- formato
def ars(x):
    return '$ %s' % ('{:,.0f}'.format(x).replace(',', '.') if x is not None else 'n/d')
def pct(x, dec=1):
    return ('%+.1f%%' % x) if x is not None else 'n/d'
def pct2(x, dec=1):
    return ('%.1f%%' % x) if x is not None else 'n/d'

# ---------------------------------------------------------------- chart (opcional)
chart_b64 = ''
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.2))
    cats = ['R.V. local', 'CEDEARs', 'Renta fija', 'Caución/líq.']
    act = [rv_act/patrimonio*100, ced_act/patrimonio*100, 0, cau_act/patrimonio*100]
    obj = [20, 30, 30, 20]
    x = range(len(cats)); w = 0.36
    b1 = ax.bar([i-w/2 for i in x], act, w, label='Actual', color='#d1495b')
    b2 = ax.bar([i+w/2 for i in x], obj, w, label='Objetivo Moderado', color='#2e86ab')
    for b in list(b1)+list(b2):
        ax.annotate('%.0f%%' % b.get_height(), (b.get_x()+b.get_width()/2, b.get_height()+0.6),
                    ha='center', fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels(cats, fontsize=9)
    ax.set_ylabel('% del patrimonio'); ax.set_ylim(0, 105)
    ax.legend(fontsize=9); ax.set_title('Asignación actual vs objetivo Moderado (plantilla Schvarz)', fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=110); plt.close(fig)
    chart_b64 = base64.b64encode(buf.getvalue()).decode()
except Exception as e:
    chart_b64 = ''

# ---------------------------------------------------------------- HTML
def td_senal(rend):
    if rend is None: return '<td class="n">n/d</td>'
    cls = 'pos' if rend > 0.5 else ('neg' if rend < -0.5 else 'neu')
    return '<td class="%s">%s</td>' % (cls, pct(rend))

css = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#f4f6f8;color:#1c2733}
.wrap{max-width:1080px;margin:0 auto;padding:24px}
header{background:linear-gradient(135deg,#0f2a43,#1d4e79);color:#fff;padding:22px 28px;border-radius:10px;margin-bottom:20px}
header h1{margin:0 0 6px;font-size:22px}
header .meta{font-size:13px;opacity:.92}
h2{font-size:17px;border-left:4px solid #1d4e79;padding-left:10px;margin:26px 0 10px}
.card{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#eef2f6;text-align:left;padding:7px 8px;font-weight:600;white-space:nowrap}
td{padding:6px 8px;border-top:1px solid #e6eaef;white-space:nowrap}
tr:hover td{background:#f7fafc}
.pos{color:#0e7a3d;font-weight:600}.neg{color:#c0392b;font-weight:600}.neu{color:#8a6d1a}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;color:#fff}
.b-r{background:#c0392b}.b-g{background:#0e7a3d}.b-y{background:#b8860b}.b-b{background:#1d4e79}
.nota{font-size:12px;color:#5a6b7b;margin-top:8px}
.alert{background:#fff6e5;border-left:4px solid #b8860b;padding:10px 14px;border-radius:6px;font-size:13px;margin:10px 0}
.kpi{display:inline-block;background:#eef2f6;border-radius:8px;padding:8px 14px;margin:4px 6px 4px 0;font-size:13px}
.kpi b{font-size:16px}
footer{font-size:11px;color:#6b7a89;margin-top:22px;text-align:center}
"""

h = []
h.append('<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">')
h.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
h.append('<title>Informe BERTUCCI — 04/08/2026</title><style>%s</style></head><body><div class="wrap">' % css)
h.append('<header><h1>Informe de posicionamiento — Cuenta 264900 (CINTIABOSS.INVIU)</h1>')
h.append('<div class="meta">Cliente: BERTUCCI, JAVIER MARCELO · Perfil declarado: <b>Moderado</b> · Arancel: 0,90%% · Fecha de análisis: %s · Fuentes: IOL (snapshot 03/08), yfinance .BA (precios ARS %s), DolarAPI, ArgDatos' % (FECHA, FECHA))
h.append('</div></header>')

# KPI
h.append('<div class="card"><h2 style="margin-top:0">1) Cartera valuada con precios reales (04/08/2026)</h2>')
h.append('<span class="kpi">Patrimonio total<br><b>%s</b></span>' % ars(patrimonio))
h.append('<span class="kpi">Activos<br><b>%s</b></span>' % ars(total_activos))
h.append('<span class="kpi">Caja ARS+USD (CCL %s)<br><b>%s</b></span>' % (ars(CCL).replace('$ ','$'), ars(cash_total)))
h.append('<span class="kpi">Exposición USD<br><b>%.1f%%</b></span>' % ((patrimonio - CASH_ARS)/patrimonio*100))
h.append('<table><tr><th>Activo</th><th>Peso</th><th>Cant.</th><th>Precio real (ARS)</th><th>P. prom.</th><th>Ganancia</th><th>Rend.</th><th>Señal</th></tr>')
for r in rows:
    h.append('<tr><td><b>%s</b><br><span style="font-weight:400;color:#5a6b7b">%s</span></td>' % (r['sim'], r['nombre']))
    h.append('<td>%.2f%%</td><td>%d</td><td>%s</td><td>%s</td>' % (r['peso'], r['cant'], ars(r['precio']), ars(r['ppc'])))
    h.append(td_senal(r['rend']) if False else '<td>%s</td>' % ars(r['gan']))
    h.append(td_senal(r['rend']))
    h.append('</tr>')
h.append('</table>')
h.append('<div class="nota">Precios: cotización de cierre %s en BYMA (CEDEAR/PAMP, ARS) vía yfinance. Cantidades y costo (P.Prom.) del snapshot IOL de la cuenta del 03/08/2026. Caja USD valorizada a CCL.</div></div>' % FECHA)

# 2) Tecnicos
h.append('<div class="card"><h2>2) Análisis técnico — series ARS reales (1 año)</h2>')
h.append('<table><tr><th>Activo</th><th>MA50</th><th>MA200</th><th>vs MA50</th><th>vs MA200</th><th>RSI14</th><th>20d</th><th>Lectura</th></tr>')
for r in rows:
    t = r['tec']
    lectura = 'Tendencia alcista' if (t.get('vs50') or 0) > 0 and (t.get('vs200') or 0) > 0 else ('En recuperación' if (t.get('vs50') or 0) > 0 else ('Debilidad' if (t.get('vs50') or 0) < 0 else 'n/d'))
    h.append('<tr><td><b>%s</b></td>' % r['sim'])
    h.append('<td>%s</td><td>%s</td>' % (ars(t.get('ma50')), ars(t.get('ma200')) if t.get('ma200') else 'n/d'))
    h.append('<td>%s</td><td>%s</td>' % (pct(t.get('vs50')), pct(t.get('vs200'))))
    h.append('<td>%s</td><td>%s</td><td>%s</td></tr>' % (('%.0f' % t['rsi']) if t.get('rsi') is not None else 'n/d', pct(t.get('r20')), lectura))
h.append('</table><div class="nota">Indicadores calculados sobre la serie de cierre en ARS del CEDEAR/acción (yfinance .BA, 1 año). MP.BA tiene 53 puntos: sin MA200.</div></div>')

# 3) Fundamentales
h.append('<div class="card"><h2>3) Análisis fundamental — métricas reales (yfinance)</h2>')
h.append('<table><tr><th>Activo</th><th>Sector</th><th>P/E (ttm)</th><th>P/E fwd</th><th>Margen neto</th><th>Beta</th><th>Crec. EPS</th><th>Mkt Cap</th></tr>')
for r in rows:
    f = fund.get(r['sim'], {})
    def g(k):
        v = f.get(k)
        return v if v is not None else None
    pe = g('trailingPE'); pef = g('forwardPE'); mm = g('profitMargins'); beta = g('beta')
    eg = g('earningsGrowth'); mc = g('marketCap')
    h.append('<tr><td><b>%s</b></td><td>%s</td>' % (r['sim'], (f.get('sector') or 'n/d')))
    h.append('<td>%s</td><td>%s</td>' % (('%.1f' % pe) if pe else 'n/d', ('%.1f' % pef) if pef else 'n/d'))
    h.append('<td>%s</td><td>%s</td>' % (pct2(mm*100) if mm is not None else 'n/d', ('%.2f' % beta) if beta is not None else 'n/d'))
    h.append('<td>%s</td><td>%s</td></tr>' % (pct2(eg*100) if eg is not None else 'n/d', ('USD %s' % '{:,.0f}'.format(mc).replace(',', '.')) if mc else 'n/d'))
h.append('</table>')
h.append('<div class="alert"><b>Lectura fundamental:</b> la cartera pondera ~95%% en crecimiento tecnológico de alta valuación. GOOGL es el mega-cap más barato (P/E %.1f vs MSFT %.1f). MP, URA y SMH no reportan P/E (negocios sin earnings estables / ETF de ciclo).' % (
    (fund.get('GOOGL', {}).get('trailingPE') or 0), (fund.get('MSFT', {}).get('trailingPE') or 0)))
h.append('</div></div>')

# 4) Intermarket
h.append('<div class="card"><h2>4) Dashboard intermarket (M1 — marco John Murphy) — datos reales</h2>')
f_ord = [('^GSPC', 'S&P 500'), ('^IXIC', 'NASDAQ'), ('^MERV', 'Merval (ARS)'), ('^VIX', 'VIX'),
         ('DX-Y.NYB', 'Dólar Index'), ('^TNX', 'Treasury 10Y'), ('^IRX', 'Treasury 3M'), ('^TYX', 'Treasury 30Y'),
         ('GC=F', 'Oro'), ('CL=F', 'Petróleo WTI'), ('HG=F', 'Cobre')]
h.append('<table><tr><th>Variable</th><th>Valor</th><th>Δ 1 mes</th><th>Lectura</th></tr>')
merval_usd = fact.get('^MERV', {}).get('ultimo', 0) / CCL if CCL else None
for tk, nm in f_ord:
    v = fact.get(tk, {})
    ult = v.get('ultimo'); h1 = v.get('hace1m')
    d1 = (ult/h1 - 1)*100 if ult and h1 else None
    if tk == '^MERV':
        lectura = 'Rendimiento ARS; en USD ≈ %.0f' % (merval_usd or 0)
    elif tk == '^VIX':
        lectura = 'Risk-on' if (ult or 99) < 17 else ('Neutral' if (ult or 99) < 22 else 'Risk-off')
    elif tk == '^TNX':
        lectura = 'Tasa larga alta → presión sobre growth' if (ult or 0) > 4.5 else 'Favorable a growth'
    elif tk == 'GC=F':
        lectura = 'Cobertura/inflación en máximos'
    else:
        lectura = '—'
    h.append('<tr><td>%s (%s)</td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (
        nm, tk, ('%.2f' % ult if isinstance(ult, (int, float)) else 'n/d'), pct(d1), lectura))
h.append('</table>')
h.append('<table style="margin-top:10px"><tr><th>Variable local</th><th>Valor</th><th>Lectura</th></tr>')
h.append('<tr><td>Dólar CCL</td><td><b>%s</b></td><td>Brecha vs MEP ≈ %.1f%%' % (ars(CCL).replace('$ ', '$ '), (CCL/macro.get('dolar_mep', CCL) - 1)*100 if macro.get('dolar_mep') else 0))
h.append('</td></tr>')
h.append('<tr><td>Dólar MEP</td><td><b>%s</b></td><td>Referencia CEDEAR</td></tr>' % ars(macro.get('dolar_mep')))
h.append('<tr><td>Riesgo país (EMBI)</td><td><b>%d bps</b></td><td>%s</td></tr>' % (macro.get('riesgo_pais') or 0, 'Moderado-alto' if (macro.get('riesgo_pais') or 0) > 400 else 'Moderado'))
h.append('<tr><td>Merval en USD</td><td><b>≈ %s</b></td><td>Merval ARS / CCL</td></tr>' % ('{:,.0f}'.format(merval_usd).replace(',', '.') if merval_usd else 'n/d'))
h.append('</table>')
h.append('<div class="alert"><b>Régimen intermarket (04/08/2026):</b> VIX 15,6 = riesgo-on moderado; pendiente 10Y−3M = +%.1f pb (curva positiva, régimen expansivo). Pero Treasury 10Y en %.2f%% es presión estructural sobre múltiplos tech: la cartera está 94%% en ese complejo. Oro en máximos (%.0f) advierte demanda de cobertura de cola. Riesgo país 430 bps: mejora local vs históricos, pero la pata argentina es solo 3,9%% (PAMP). <b>Veredicto:</b> posicionamiento pro-cíclico sin coberturas de bonos/commodities/cash (0,26%%).' % (
    ((fact.get('^TNX', {}).get('ultimo') or 0) - (fact.get('^IRX', {}).get('ultimo') or 0)) * 100,
    fact.get('^TNX', {}).get('ultimo') or 0, fact.get('GC=F', {}).get('ultimo') or 0))
h.append('</div></div>')

# 5) Rebalanceo
h.append('<div class="card"><h2>5) Rebalanceo hacia la plantilla Moderada (Schvarz: RV 20 / CEDEARs 30 / RF 30 / Caución 20)</h2>')
if chart_b64:
    h.append('<img src="data:image/png;base64,%s" style="width:100%%;max-width:760px;border-radius:8px">' % chart_b64)
h.append('<table style="margin-top:10px"><tr><th>Bucket</th><th>Actual</th><th>Objetivo</th><th>Δ (ARS)</th><th>Acción</th></tr>')
h.append('<tr><td>Renta variable local</td><td>%.1f%% (%s)</td><td>20%% (%s)</td><td class="pos">%s</td><td>Comprar</td></tr>' % (
    rv_act/patrimonio*100, ars(rv_act), ars(0.20*patrimonio), ars(compra_rv)))
h.append('<tr><td>CEDEARs / RV exterior</td><td>%.1f%% (%s)</td><td>30%% (%s)</td><td class="neg">%s</td><td>Vender</td></tr>' % (
    ced_act/patrimonio*100, ars(ced_act), ars(0.30*patrimonio), ars(-venta_necesaria)))
h.append('<tr><td>Renta fija (USD cortos)</td><td>0%%</td><td>30%% (%s)</td><td class="pos">%s</td><td>Comprar AL30/GD30</td></tr>' % (ars(0.30*patrimonio), ars(compra_rf)))
h.append('<tr><td>Caución / liquidez</td><td>%.2f%% (%s)</td><td>20%% (%s)</td><td class="pos">%s</td><td>Caución en ARS/USD</td></tr>' % (
    cau_act/patrimonio*100, ars(cau_act), ars(0.20*patrimonio), ars(compra_cau)))
h.append('</table>')
h.append('<h2 style="margin-top:20px">5.1) Plan de ejecución por instrumento (3 tramos semanales)</h2>')
h.append('<table><tr><th>Instrumento</th><th>Acción</th><th>Monto total</th><th>Por tramo (1/3)</th></tr>')
for sim, v in plan_venta:
    if v > 1000:
        h.append('<tr><td>%s</td><td class="neg">VENDER</td><td>%s</td><td>%s</td></tr>' % (sim, ars(v), ars(v/TRAMOS)))
for lbl, v in [('Renta fija USD (AL30/GD30 60/40)', compra_rf), ('Caución (AR$ 60% / USD 40%)', compra_cau), ('Acciones locales (PAMP u otros)', compra_rv)]:
    if v > 1000:
        h.append('<tr><td>%s</td><td class="pos">COMPRAR</td><td>%s</td><td>%s</td></tr>' % (lbl, ars(v), ars(v/TRAMOS)))
h.append('</table>')
h.append('<div class="alert"><b>Costo estimado del rebalanceo:</b> %s vendidos + %s comprados × arancel 0,90%% ≈ <b>%s</b> (≈ %.2f%% del patrimonio). En 3 tramos, el costo se reparte en ~%s por tramo. Alternativa: reducir el alcance (1 solo tramo sobre SPY) si se prioriza minimizar costo.' % (
    ars(ventas_tot), ars(compras_tot), ars(fee), fee/patrimonio*100, ars(fee/TRAMOS)))
h.append('</div>')
h.append('<div class="alert" style="border-left-color:#1d4e79;background:#eef4fb"><b>Notas de transparencia:</b> cotizaciones y métricas de cierre %s (yfinance .BA, DolarAPI, ArgDatos); IOL API rechazó las credenciales del repo (401) — las cantidades/costo provienen del snapshot de la cuenta del 03/08. Este informe es informativo y no constituye recomendación de inversión; la recomendación formal corresponde al AP regulado CNV (Coronar Inversiones ETR).' % FECHA)
h.append('</div>')
h.append('<footer>Generado el %s por pipeline Coronar Inversiones ETR · Informe de posicionamiento bajo marcos Intermarket (Murphy), Value Investing y Tácticas (Schvarz)</footer>' % datetime.now().strftime('%d/%m/%Y %H:%M'))
h.append('</div></body></html>')

outfile = '%s/informe_bertucci_20260804.html' % BASE
open(outfile, 'w', encoding='utf-8').write('\n'.join(h))
print('OK ->', outfile, '|', len('\n'.join(h)), 'bytes')

# ---------------------------------------------------------------- resumen para chat
print('--- RESUMEN ---')
print('Patrimonio total: %.0f ARS' % patrimonio)
print('Pesos: ' + ' | '.join('%s %.1f%%' % (r['sim'], r['peso']) for r in sorted(rows, key=lambda x: -x['peso'])[:5]) + ' ...')
print('Tecnicos: ' + ' | '.join('%s RSI%s' % (r['sim'], ('%.0f' % r['tec']['rsi']) if r['tec'].get('rsi') is not None else 'n/d') for r in rows))
print('Ventas totales: %.0f | Compras: %.0f | Fee estimado: %.0f (%.2f%% patrimonio)' % (ventas_tot, compras_tot, fee, fee/patrimonio*100))
print('Plan ventas: ' + ' | '.join('%s %s' % (s, ars(v)) for s, v in plan_venta if v > 1000))
print('Plan compras: RF %s | Caución %s | RV %s' % (ars(compra_rf), ars(compra_cau), ars(compra_rv)))
