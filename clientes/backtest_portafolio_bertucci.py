# -*- coding: utf-8 -*-
"""
BACKTEST PORTAFOLIO BERTUCCI — Tesis vs Realidad (misma metodologia que backtest_entrada_*.py)
Periodo: 22-Jul-2026 -> 04-Ago-2026 (13 dias) + ventanas 1M/3M/6M/1Y + tecnicos + fundamentales
10 empresas del portafolio, datos reales yfinance. Genera JSON + HTML.
"""
import yfinance as yf, pandas as pd, numpy as np, json, warnings, base64, io
warnings.filterwarnings('ignore')
from datetime import datetime

END = '2026-08-05'
BASE13 = '2026-07-22'   # baseline igual al backtest del pipeline

POS = {
    'SPY':  dict(nombre='SPDR S&P 500', peso=64.5,  rend= -0.09),
    'MSFT': dict(nombre='Microsoft',     peso= 9.2,  rend= 23.31),
    'NVDA': dict(nombre='Nvidia',        peso= 7.8,  rend=  0.49),
    'AMZN': dict(nombre='Amazon',        peso= 6.3,  rend= 13.73),
    'GOOGL':dict(nombre='Alphabet',      peso= 6.0,  rend=  4.14),
    'PAM':  dict(nombre='Pampa Energia (ADR)', peso= 4.0, rend= 2.89),
    'TSM':  dict(nombre='Taiwan Semiconductor', peso= 0.7, rend= -4.51),
    'MP':   dict(nombre='MP Materials',  peso= 0.4,  rend= -5.23),
    'URA':  dict(nombre='Global X Uranium ETF', peso= 0.4, rend= -1.82),
    'SMH':  dict(nombre='VanEck Semiconductors', peso= 0.3, rend= -8.45),
}
# pares sectoriales para comparativa (peer: peso del peer en el fondo / referencia)
PEERS = {
    'MSFT': ['GOOGL', 'AMZN'],
    'NVDA': ['AVGO', 'MU'],
    'AMZN': ['MSFT', 'GOOGL'],
    'GOOGL':['MSFT', 'AMZN'],
    'TSM':  ['NVDA', 'MU'],
    'SMH':  ['NVDA', 'TSM', 'MU'],
    'URA':  ['CCJ', 'URNM'],
    'MP':   ['UUUU', 'LAC'],
    'PAM':  ['YPF', 'GGAL'],
    'SPY':  ['XLK', 'XLB'],
}
SECTOR_CTX = {'XLK': 'Tech', 'XLB': 'Materiales', 'XLE': 'Energia', 'XLV': 'Salud', 'XLP': 'Consumo def.'}

def load(tk):
    h = yf.Ticker(tk).history(start='2025-08-01', end=END)
    return h['Close'].dropna()

def rsi14(c):
    if len(c) < 15: return None
    d = c.diff(); g = d.where(d > 0, 0).rolling(14).mean(); l = (-d.where(d < 0, 0)).rolling(14).mean()
    return float((100 - 100/(1 + g/l)).iloc[-1])

def metrics(tk, c):
    n = len(c); last = float(c.iloc[-1])
    def ret(idx): return (last/float(c.iloc[idx]) - 1)*100 if n > idx else None
    out = {
        'ultimo': round(last, 2), 'fecha': str(c.index[-1].date()),
        'r13d': round(ret(max(n-10, 0)), 2) if n > 10 else None,   # 13d aprox (dias habiles desde 22/07)
        'r1m': round(ret(max(n-21, 0)), 2), 'r3m': round(ret(max(n-63, 0)), 2),
        'r6m': round(ret(max(n-126, 0)), 2), 'r1y': round(ret(max(n-252, 0)), 2),
    }
    if n >= 20:
        c20 = c.rolling(20).mean(); c50 = c.rolling(50).mean(); c200 = c.rolling(200).mean()
        out['sma20'] = round(float(c20.iloc[-1]), 2) if n >= 20 else None
        out['sma50'] = round(float(c50.iloc[-1]), 2) if n >= 50 else None
        out['sma200'] = round(float(c200.iloc[-1]), 2) if n >= 200 else None
        out['vs20'] = round((last/out['sma20'] - 1)*100, 1) if out['sma20'] else None
        out['vs50'] = round((last/out['sma50'] - 1)*100, 1) if out['sma50'] else None
        out['vs200'] = round((last/out['sma200'] - 1)*100, 1) if out['sma200'] else None
        out['rsi'] = round(rsi14(c), 1)
        out['mdd'] = round((float(c.min()/c.cummax().max()) - 1)*100, 1)
        out['tend'] = 'ALCISTA' if (out.get('sma20') and out.get('sma50') and out['sma20'] > out['sma50'] > out['sma200']) else ('BAJISTA' if (out.get('sma20') and out.get('sma50') and out.get('sma200') and out['sma20'] < out['sma50'] < out['sma200']) else 'MIXTA')
    return out

def beta_vs_spy(tk, c, spy):
    j = pd.concat([c, spy], axis=1, join='inner').dropna()
    if len(j) < 30: return None
    x = j.iloc[:, 1].pct_change().dropna(); y = j.iloc[:, 0].pct_change().dropna()
    j2 = pd.concat([y, x], axis=1).dropna()
    if len(j2) < 30: return None
    b = np.polyfit(j2.iloc[:, 1], j2.iloc[:, 0], 1)[0]
    corr = float(j2.corr().iloc[0, 1])
    return round(float(b), 2), round(corr, 2)

# ------------------------------------------------------------------ datos
print('[1] Descargando series 1y ...')
series, betas = {}, {}
spy = load('SPY')
for tk in POS:
    try:
        c = load(tk)
        if len(c) < 30:
            print('  %s: pocos datos (%d)' % (tk, len(c))); continue
        series[tk] = c
        print('  %s: %d pts, ult %.2f' % (tk, len(c), c.iloc[-1]))
    except Exception as e:
        print('  %s ERR %s' % (tk, str(e)[:80]))

for tk in series:
    if tk != 'SPY':
        betas[tk] = beta_vs_spy(tk, series[tk], spy)
        print('  beta %s vs SPY: %s' % (tk, betas[tk]))

# contexto sectorial (XLK, XLB, XLE, XLV, XLP)
ctx = {}
for s in SECTOR_CTX:
    try:
        c = load(s)
        ctx[s] = dict(nombre=SECTOR_CTX[s],
                      r3m=round((float(c.iloc[-1])/float(c.iloc[-63]) - 1)*100, 1) if len(c) > 63 else None,
                      r6m=round((float(c.iloc[-1])/float(c.iloc[-126]) - 1)*100, 1) if len(c) > 126 else None,
                      r1y=round((float(c.iloc[-1])/float(c.iloc[-252]) - 1)*100, 1) if len(c) > 252 else None)
    except Exception as e:
        ctx[s] = dict(nombre=SECTOR_CTX[s], error=str(e)[:60])

# peers
peers_ret = {}
for tk, lst in PEERS.items():
    peers_ret[tk] = {}
    for p in lst:
        try:
            c = load(p)
            peers_ret[tk][p] = dict(
                r13d=round((float(c.iloc[-1])/float(c.iloc[max(len(c)-10, 0)]) - 1)*100, 2),
                r3m=round((float(c.iloc[-1])/float(c.iloc[-63]) - 1)*100, 1) if len(c) > 63 else None,
                r1y=round((float(c.iloc[-1])/float(c.iloc[-252]) - 1)*100, 1) if len(c) > 252 else None)
        except Exception:
            peers_ret[tk][p] = None

# fundamentales (info ya capturada antes, re-fetch rapido por ticker)
fund = {}
for tk in POS:
    try:
        i = yf.Ticker(tk).info
        fund[tk] = dict(pe=i.get('trailingPE'), pef=i.get('forwardPE'), beta=i.get('beta'),
                        margen=i.get('profitMargins'), eg=i.get('earningsGrowth'),
                        rg=i.get('revenueGrowth'), sector=i.get('sector'), mcap=i.get('marketCap'),
                        tgt=i.get('targetMeanPrice'))
    except Exception as e:
        fund[tk] = dict(error=str(e)[:100])

# ------------------------------------------------------------------ drivers y noticias (reales, de busquedas 04-05/08/2026)
NEWS = {
 'MSFT': [('29/07','Q4 FY26: ingresos $90,0B (+18%), EPS GAAP $4,81 (+32%), Azure +43% y cruza $100B anuales, Copilot 30M asientos pagos'),
          ('29/07','RPO comercial $678B (+84% YoY); acuerdo OpenAI extiende compromiso Azure por $250B hasta 2032'),
          ('31/07-04/08','Rally post-earnings +25% en la semana (de ~$389 a $487,65); mayor reaccion a earnings en el dataset'),
          ('04/08','Lado bajista: capex FY26 $115,9B (Q4 +109,6% YoY), FCF -23,2% en el Q4; promedio historico post-earnings -2,16%'),
          ('04/08','Target 24/7WS $573,79 (+23%) con 90% confianza; bull $603,61; escala en pullbacks >$460, no perseguir')],
 'NVDA': [('26/08','Earnings programado 26-Ago (proxima catalisis mayor del portafolio)'),
          ('Q1 FY26','Revenue $81,6B (+85% YoY); data center +92% a $75,2B (92% de ventas)'),
          ('jul-26','Correccion de semis: SOX -21% en julio (peor desde 2008); NVDA -6,4% desde pico del 22-jun'),
          ('jul-26','FCF a -$7,6B (outflow) por capex de IA TTM +$66,1B; el mercado pregunta por la conversion de capex en demanda')],
 'AMZN': [('2026','P/E 22,8x, el 2do mas barato del grupo; AWS sigue siendo el motor de margen'),
          ('jul-26','Resistio mejor la correccion de julio que los semis (menor beta a IA capex)'),
          ('ago-26','Mantiene tendencia alcista con RSI ~70: sobrecompra pero sin ruptura')],
 'GOOGL':[('ago-26','P/E 18,7x: el mega-cap mas barato del portafolio; margen neto ~28-30%'),
          ('2026','Riesgo estructural: disrupcion IA en busqueda; cloud crece fuerte'),
          ('jul-26','Comportamiento defensivo relativo en la correccion tech')],
 'TSM':  [('16/07','Q2: utilidad operativa +77% YoY y sube guidance, pero la accion cayo -7% en la sesion: el mercado no discute el trimestre sino lo que viene'),
          ('jul-26','-13,8% desde pico del 22-jun; la cadena sin amortiguadores amplifica cualquier noticia de timing (HBM4, 2nm)'),
          ('jul-26','Samsung extiende escasez de memoria a 2028; capacidad de empaque avanzado vendida'),
          ('ago-26','Rebote 30-31/07: SOX +10% en dos dias; NVDA reporta 26/08')],
 'SMH':  [('03/08','-18% en el mes tras +75% en 12m: correccion dentro de tendencia, no quiebre de ciclo'),
          ('03/08','Gatillos: guia cauta de Broadcom, caida de precios de memoria, avances de China (Kimi K3, litografia), smartphone debil'),
          ('03/08','Concentracion: NVDA 21,7%, TSM 9,5%, AVGO 6,7%, MU ~6%: el fondo amplifica la volatilidad de un puñado de names'),
          ('jul-26','MU: Q3 blockbuster (+17,6% beat, GM 84,6%) y aun asi -15% en el mes: profit-taking dentro de uptrend (+190% YTD)')],
 'URA':  [('31/07','CCJ Q2: EPS $0,13 vs $0,26 consenso (miss), revenue $588M vs $534M (+10% beat); produccion 2026 sin cambios 19,5-21,5M lbs'),
          ('31/07','U3O8 largo plazo en maximos de decada (mid-$90s/lb); contratos 28M lbs/año prox 5 años; Westinghouse pipeline 91 AP1000'),
          ('jul-26','Acciones de uranio -31% en el trimestre (sentimiento) mientras el precio fisico sigue en maximos: descople clasico'),
          ('01/08','Acuerdo nuclear USA-Arabia Saudita = catalisis potencial de demanda; URA 5y anualizado +20,2%'),
          ('04/08','CCJ rebota +3,76% a $93,09; URA todavia -1,8% vs costo del cliente')],
 'MP':   [('06/08','Earnings Q2 el 06/08: revenue esperado $99,2M (+72,9% YoY), EPS $0,02 (vs -$0,13 año atras); ESP -72,7% (riesgo de sorpresa negativa)'),
          ('ago-26','-34,7% en 90d y -30,6% en 12m; rebote reciente +8,3% en 1d y +15% en 7d desde minimo de 52 semanas ($37,81 el 29/07)'),
          ('ago-26','Valuacion: P/S 24,3x vs industria 2,9x (y fwd 12x vs 1,42x): prima enorme, "bargain" solo si el flujo acompaña'),
          ('ago-26','Catalizadores: PPA con el DoD (precio piso y EBITDA garantizado para imanes), contrato Apple $500M+, restricciones de exportacion de minerales criticos de USA'),
          ('Q1-26','Produccion record NdPr 917 MT (+63% YoY), ventas NdPr +117%: crecimiento operativo real, costos de expansion presionando margenes')],
 'PAM':  [('ago-26','Accion local +2,9% vs costo; RSI 63; XLE (energia USA) como contexto sectorial'),
          ('ago-26','Riesgo pais 430 bps (31/07): mejora vs historico pero sigue siendo el riesgo dominante'),
          ('2026','Tesis value: P/E bajo, dividendos, integracion generacion+upstream; contraciclico dentro del portafolio')],
 'SPY':  [('jul-26','Mercado lateral tras el selloff de semis de julio (-21% SOX, -$3T valor) y rebote del 30-31/07'),
          ('ago-26','VIX 15,6 (risk-on), 10Y 4,74% (presion estructural sobre growth), S&P 7489,7'),
          ('04/08','Temporada de earnings fuerte liderada por MSFT (Azure +43%); la concentracion del indice sigue en mega-cap tech'),
          ('ago-26','Plano vs costo (-0,09%): el indice digiere la rotacion sectorial')],
}

# ------------------------------------------------------------------ veredictos (reglas transparentes)
def veredicto(tk, m):
    rend = POS[tk]['rend']
    rsi = m.get('rsi'); tend = m.get('tend'); r1m = m.get('r1m'); r3m = m.get('r3m'); r6m = m.get('r6m')
    razones = []
    v = 'MANTENER'
    if rend >= 10 and (rsi is not None and rsi >= 68):
        v = 'TOMAR GANANCIAS (parcial)'
        razones.append('ganancia %+.1f%% y RSI %.0f (sobrecompra)' % (rend, rsi))
    elif rend >= 10 and (r1m is not None and r1m < 0):
        v = 'TOMAR GANANCIAS (parcial)'
        razones.append('ganancia %+.1f%% con momentum 1M negativo' % rend)
    elif rend <= -3 and tend == 'BAJISTA' and (r3m or 0) < -10:
        v = 'SALIR / REEMPLAZAR'
        razones.append('perdida %+.1f%%, tendencia bajista y 3M %+.1f%%' % (rend, r3m))
    elif rend <= -3 and tend == 'BAJISTA':
        v = 'MANTENER CON CAUCION'
        razones.append('perdida %+.1f%% y tendencia bajista; no promediar, esperar catalizador' % rend)
    elif rend <= -3 and (r1m or 0) < 0 and (r3m or 0) < 0:
        v = 'REVISAR TESIS'
        razones.append('perdida %+.1f%% con momentum 1M/3M negativo' % rend)
    elif tend == 'ALCISTA' and rsi is not None and 45 <= rsi <= 68:
        v = 'MANTENER'
        razones.append('tendencia alcista y RSI %.0f' % (rsi or 0))
    elif (r6m or 0) > 0 and (rsi or 99) < 60 and rend < 5:
        v = 'ACUMULAR EN PULLBACK'
        razones.append('tendencia de fondo fuerte, RSI %.0f, entrada vs costo %+.1f%%' % (rsi or 0, rend))
    else:
        v = 'MANTENER CON CAUCION'
        razones.append('estructura mixta: RSI %.0f, tend %s, 6M %+.1f%%' % (rsi or 0, tend, r6m or 0))
    return v, razones

MET = {}
for tk, c in series.items():
    MET[tk] = metrics(tk, c)
    MET[tk]['beta_spy'], MET[tk]['corr_spy'] = betas.get(tk, (None, None))
    v, rz = veredicto(tk, MET[tk])
    MET[tk]['veredicto'] = v; MET[tk]['razones'] = rz

# ranking de rotacion (fuerza relativa vs SPY)
rank = []
for tk in series:
    if tk == 'SPY': continue
    m = MET[tk]
    x6 = (m.get('r6m') or 0) - (MET['SPY'].get('r6m') or 0)
    x3 = (m.get('r3m') or 0) - (MET['SPY'].get('r3m') or 0)
    trend = {'ALCISTA': 2, 'MIXTA': 1, 'BAJISTA': 0}.get(m.get('tend'), 1)
    score = 0.45*x6 + 0.35*x3 + 0.20*trend
    rank.append(dict(tk=tk, x6=round(x6, 1), x3=round(x3, 1), tend=m.get('tend'), rsi=m.get('rsi'), score=round(score, 1)))
rank.sort(key=lambda r: -r['score'])

out = dict(fecha=datetime.now().strftime('%Y-%m-%d %H:%M'), pos=POS, met=MET, ctx=ctx,
           peers=peers_ret, fund=fund, news=NEWS, rank=rank)
json.dump(out, open('clientes/backtest_bertucci_datos_20260805.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- HTML
def ars2(x): return ('%s' % ('{:,.0f}'.format(x).replace(',', '.'))) if x is not None else 'n/d'
def p(x, s='+'): return ('%s%.1f%%' % (s, x)) if x is not None else 'n/d'

css = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#0d1117;color:#e6edf3}
.wrap{max-width:1120px;margin:0 auto;padding:22px}
h1{font-size:22px;margin:0 0 4px;color:#fff}
h2{font-size:16px;border-left:4px solid #f0b90b;padding-left:10px;margin:26px 0 10px;color:#f0b90b}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:#21262d;color:#8b949e;text-align:left;padding:6px 8px}
td{padding:5px 8px;border-top:1px solid #21262d}
.pos{color:#3fb950;font-weight:600}.neg{color:#f85149;font-weight:600}.neu{color:#d29922}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700;color:#0d1117}
.b-t{background:#3fb950}.b-m{background:#d29922}.b-r{background:#f85149}.b-a{background:#58a6ff}.b-g{background:#a371f7}
.tick{font-size:17px;font-weight:700;color:#fff}
.sub{color:#8b949e;font-size:12px}
.news{font-size:12px;color:#c9d1d9;margin:6px 0 0 0;padding-left:14px}
.news li{margin-bottom:3px}
.nota{font-size:11.5px;color:#8b949e;margin-top:8px}
footer{font-size:11px;color:#8b949e;margin-top:20px;text-align:center}
.ver{font-size:13px;font-weight:700}
"""

h = ['<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
     '<title>Backtest Portafolio BERTUCCI — 05/08/2026</title><style>%s</style></head><body><div class="wrap">' % css]
h.append('<h1>Backtesting — Tesis vs Realidad · Portafolio BERTUCCI (cuenta 264900)</h1>')
h.append('<div class="sub">10 posiciones · ventanas 13d/1M/3M/6M/1Y · 22-Jul → 04-Ago-2026 · datos reales yfinance · generado %s</div>' % datetime.now().strftime('%d/%m/%Y %H:%M'))

# ranking
h.append('<h2>0) Ranking de rotacion (fuerza relativa vs SPY)</h2><div class="card">')
h.append('<table><tr><th>#</th><th>Activo</th><th>Exceso 6M vs SPY</th><th>Exceso 3M vs SPY</th><th>Tendencia</th><th>RSI</th><th>Score</th><th>Veredicto</th></tr>')
for i, r in enumerate(rank, 1):
    m = MET[r['tk']]
    cls = {'TOMAR GANANCIAS (parcial)': 'b-t', 'MANTENER': 'b-m', 'ACUMULAR EN PULLBACK': 'b-a',
           'REVISAR TESIS': 'b-g', 'SALIR / REEMPLAZAR': 'b-r'}.get(m['veredicto'], 'b-m')
    h.append('<tr><td>%d</td><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><b>%.1f</b></td><td><span class="badge %s">%s</span></td></tr>' % (
        i, r['tk'], p(r['x6']), p(r['x3']), r['tend'], ('%.0f' % r['rsi']) if r['rsi'] is not None else 'n/d',
        r['score'], cls, m['veredicto']))
h.append('</table><div class="nota">Score = 0,45·exceso6M + 0,35·exceso3M + 0,20·tendencia (2 alcista / 1 mixta / 0 bajista), ambos excesos vs SPY.</div></div>')

# contexto sectorial
h.append('<h2>1) Contexto sectorial (dónde rota el dinero)</h2><div class="card">')
h.append('<table><tr><th>Sector ETF</th><th>3M</th><th>6M</th><th>1Y</th></tr>')
for s, v in ctx.items():
    if 'error' in v: continue
    c = 'pos' if (v.get('r3m') or 0) > 0 else 'neg'
    h.append('<tr><td><b>%s</b></td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td></tr>' % (
        v['nombre'], c, p(v.get('r3m')), c, p(v.get('r6m')), c, p(v.get('r1y'))))
h.append('</table></div>')

# por empresa
for tk in POS:
    m = MET.get(tk)
    if not m: continue
    pos = POS[tk]
    cls = {'TOMAR GANANCIAS (parcial)': 'b-t', 'MANTENER': 'b-m', 'ACUMULAR EN PULLBACK': 'b-a',
           'REVISAR TESIS': 'b-g', 'SALIR / REEMPLAZAR': 'b-r'}.get(m['veredicto'], 'b-m')
    h.append('<h2>%s — %s <span class="badge %s">%s</span></h2>' % (tk, pos['nombre'], cls, m['veredicto']))
    h.append('<div class="card">')
    h.append('<div class="sub">Peso %.1f%% · Rend vs costo <b class="%s">%+.2f%%</b> · Beta vs SPY %s · Corr %s · MDD 1y %s</div>' % (
        pos['peso'], 'pos' if pos['rend'] >= 0 else 'neg', pos['rend'],
        ('%.2f' % m['beta_spy']) if m.get('beta_spy') else 'n/d',
        ('%.2f' % m['corr_spy']) if m.get('corr_spy') else 'n/d', p(m.get('mdd'), '')))
    h.append('<table><tr><th>Último</th><th>13d</th><th>1M</th><th>3M</th><th>6M</th><th>1Y</th><th>SMA20</th><th>SMA50</th><th>SMA200</th><th>RSI14</th><th>Tend.</th></tr>')
    h.append('<tr><td><b>$%s</b></td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td>' % (
        ars2(m['ultimo']),
        'pos' if (m.get('r13d') or 0) >= 0 else 'neg', p(m.get('r13d')),
        'pos' if (m.get('r1m') or 0) >= 0 else 'neg', p(m.get('r1m')),
        'pos' if (m.get('r3m') or 0) >= 0 else 'neg', p(m.get('r3m')),
        'pos' if (m.get('r6m') or 0) >= 0 else 'neg', p(m.get('r6m')),
        'pos' if (m.get('r1y') or 0) >= 0 else 'neg', p(m.get('r1y'))))
    h.append('<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>' % (
        ars2(m.get('sma20')), ars2(m.get('sma50')), ars2(m.get('sma200')),
        ('%.0f' % m['rsi']) if m.get('rsi') is not None else 'n/d', m.get('tend')))
    f = fund.get(tk, {})
    if f and 'error' not in f:
        h.append('<div class="sub">P/E ttm %s · P/E fwd %s · Crec. EPS %s · Crec. Rev %s · Margen %s · Target %s</div>' % (
            ('%.1f' % f['pe']) if f.get('pe') else 'n/d', ('%.1f' % f['pef']) if f.get('pef') else 'n/d',
            p((f.get('eg') or 0)*100, '') if f.get('eg') is not None else 'n/d',
            p((f.get('rg') or 0)*100, '') if f.get('rg') is not None else 'n/d',
            p((f.get('margen') or 0)*100, '') if f.get('margen') is not None else 'n/d',
            ('$%.0f' % f['tgt']) if f.get('tgt') else 'n/d'))
    h.append('<ul class="news">')
    for d_, tx in NEWS.get(tk, [('—', 'sin datos')]):
        h.append('<li><b>%s:</b> %s</li>' % (d_, tx))
    h.append('</ul>')
    h.append('<div class="sub" style="margin-top:6px"><b>Veredicto:</b> %s. %s</div>' % (m['veredicto'], ' '.join(m['razones'])))
    # peers
    if tk in peers_ret and peers_ret[tk]:
        h.append('<div class="sub" style="margin-top:8px">Comparativa: ')
        for pk, pv in peers_ret[tk].items():
            if pv:
                h.append('<b>%s</b> 13d %s · 3M %s · 1Y %s &nbsp;|&nbsp; ' % (pk, p(pv.get('r13d')), p(pv.get('r3m')), p(pv.get('r1y'))))
        h.append('</div>')
    h.append('</div>')

h.append('<footer>Backtesting Tesis vs Realidad · datos reales yfinance (series 1y, cierre 04/08/2026) · noticias de fuentes publicas (Microsoft Source, CNBC, HyperFRAME, Global X, Zacks, Yahoo Finance, Simply Wall St, 24/7WS, Cameco IR) · informativo, no es recomendacion de inversion</footer>')
h.append('</div></body></html>')
open('clientes/backtest_portafolio_bertucci_20260805.html', 'w', encoding='utf-8').write('\n'.join(h))

print('--- RANKING ROTACION ---')
for i, r in enumerate(rank, 1):
    print('%d. %-6s x6 %+5.1f  x3 %+5.1f  %-7s RSI %s  score %.1f  -> %s' % (
        i, r['tk'], r['x6'], r['x3'], r['tend'], ('%.0f' % r['rsi']) if r['rsi'] is not None else 'n/d', r['score'], MET[r['tk']]['veredicto']))
print('--- CONTEXTO SECTORIAL ---')
for s, v in ctx.items():
    if 'error' not in v:
        print('%-4s 3M %+5.1f | 6M %+5.1f | 1Y %+6.1f' % (v['nombre'], v.get('r3m') or 0, v.get('r6m') or 0, v.get('r1y') or 0))
print('OK -> clientes/backtest_portafolio_bertucci_20260805.html')
