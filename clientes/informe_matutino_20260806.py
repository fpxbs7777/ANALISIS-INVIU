# -*- coding: utf-8 -*-
"""
Informe matutino clientes — 06/08/2026
En qué invertir hoy: regimen intermarket + sectores favorecidos + tickers
(unificado completo.json + screener real) + plan de rotacion por cartera.
Genera informe_matutino_20260806.html
"""
import json
from datetime import datetime

# ------------------------------------------------------------------ datos reales
screener = {m['tk']: m for m in json.load(open('clientes/screener_sectores_fav_20260805.json', encoding='utf-8'))}
precios = json.load(open('clientes/precios_hoy_20260806.json', encoding='utf-8'))

def p(tk):
    v = precios.get(tk)
    return (v['ultimo'], v['d1']) if v else (None, None)

# ------------------------------------------------------------------ lista final
SECCIONES = [
 ('1 · METALES PRECIOSOS — el activo del régimen', 'GLD/SLV', [
   ('GLD', 'ETF Oro', 'COMPRAR', '+4,1% ayer: la señal del régimen. Estanflación (ADP 44K + ISM precios 70,3) + prima geopolítica (Ormuz 0 tránsitos) + recorte Fed en puerta.'),
   ('SLV', 'ETF Plata', 'COMPRAR', 'Más beta que el oro al ciclo monetario/industrial; +4,1% ayer. Hedging directo para carteras 100% tech.'),
   ('GLD.BA', 'CEDEAR Oro (BYMA)', 'COMPRAR', 'Accesible en pesos vía CEDEAR (unificado: listaARS). Diversificador ARS vs devaluación.'),
 ]),
 ('2 · TECNOLOGÍA — líder, con rotación interna', 'XLK · NVDA.BA', [
   ('NVDA', 'Nvidia', 'MANTENER/ACUMULAR en pullback', 'Liderazgo confirmado: +3,4% ayer en rueda de caída. Catalizador: earnings 26/08. El motor de las carteras tech.'),
   ('FTNT', 'Fortinet', 'COMPRAR', 'Ciberseguridad calidad/precio: fwd 43,7x, EPS +44%, billings +33%, RSI 55 sin sobrecompra.'),
   ('PANW', 'Palo Alto', 'COMPRAR', 'Plataforma líder, +80% YTD, targets al alza ($400-430); earnings 18/08.'),
   ('MRVL', 'Marvell', 'COMPRAR en pullback', 'Custom silicon IA: fwd 33,8x (mitad del P/E), pullback −12% 1M = entrada en corrección.'),
   ('MSFT', 'Microsoft', 'MANTENER', 'Núcleo (+23,6% vs costo); Azure +43%, RPO $678B. No perseguir, RSI 81.'),
   ('GOOGL', 'Alphabet', 'MANTENER/ACUMULAR', 'El mega-cap más barato (P/E ~19x); defensivo relativo en la rotación.'),
   ('AMD', 'AMD', 'REDUCIR', '−7% pese al beat: margen bruto 56% < lo que pedía el mercado. Esperar claridad MI350/Helios.'),
 ]),
 ('3 · SALUD — defensiva del régimen', 'XLV · PFE.BA', [
   ('HUM', 'Humana', 'COMPRAR', 'fwd 22x, RSI 32 (sobreventa), turnaround Medicare; empleo en salud +36K en el ADP.'),
   ('PFE', 'Pfizer', 'COMPRAR', 'Defensiva barata (fwd ~11x), yield; XLV +1,3% ayer en rueda de caída.'),
   ('CVS', 'CVS Health', 'REENTRAR con base', 'Q2 beat + guidance alzada, pero −5,1% (sell-the-news): esperar base, tesis intacta.'),
 ]),
 ('4 · FINANCIERO — curva positiva y valor', 'XLF · GGAL.BA', [
   ('JPM', 'JPMorgan', 'COMPRAR', 'Banco US de máxima calidad; curva 10Y−3M +106pb expande NIM.'),
   ('STT', 'State Street', 'COMPRAR', 'fwd 12,2x, RSI 48, ALCISTA; valor del sector.'),
   ('GGAL.BA', 'Grupo Galicia', 'COMPRAR', 'Banco local de alta liquidez (unificado: byma); tasas altas locales + mejora de riesgo país (430 bps).'),
   ('BMA.BA', 'Banco Macro', 'COMPRAR', 'Beta financiero local; complementa GGAL.'),
 ]),
 ('5 · INDUSTRIAL / DEFENSA — Dow récord', 'XLI · ITA', [
   ('RTX', 'RTX', 'COMPRAR', '+2% ayer (defensa fuerte en la rotación); geopolítica → gasto militar.'),
   ('LMT', 'Lockheed Martin', 'MANTENER', '+34,9% vs costo en cartera de clientes; defensa estructural.'),
 ]),
 ('6 · ENERGÍA — petróleo por Hormuz, entrar en pullback', 'XLE · YPFD.BA', [
   ('XLE', 'Energy Select ETF', 'COMPRAR en pullback', 'Brent ~$80, Ormuz en 0 tránsitos; −2% ayer = pullback de compra.'),
   ('CVX', 'Chevron', 'COMPRAR', 'Integrada con yield; defensor del portafolio si el riesgo geopolítico escala.'),
   ('VLO/MPC', 'Refinadoras', 'TOMAR GANANCIAS parcial', 'Margen récord ($23-36/bbl) = pico de ciclo (TD Cowen: "no sostenible"); reciclar a GLD/SLV.'),
   ('YPFD.BA', 'YPF', 'COMPRAR en pullback', 'Plan 4x4: vendió Chachahuén (USD 200M) → foco Vaca Muerta; shale = crecimiento local.'),
   ('VIST.BA', 'Vista Energy', 'COMPRAR', 'Pura Vaca Muerta; mayor beta al shale local.'),
   ('URA/CCJ', 'Uranio', 'MANTENER', 'Temática nuclear intacta: U3O8 LT en máximos, +1% ayer pese a la caída general.'),
 ]),
]

TACTICA = [
 ('IWM', 'Small caps', 'COMPRA CONDICIONAL', 'Call al recorte de la Fed: si mañana el payroll sorprende a la baja, es el activo de mayor beta a tasa.'),
 ('AO28 / YMCIO', 'Bonos USD cortos', 'MANTENER', 'Carry + refugio; AO28 +5,2% y YMCIO +95,8% vs costo en carteras.'),
 ('Caja USD', 'Dólares', 'DRY POWDER', 'NFP mañana = evento binario: no apalancarse, deployar en tramos.'),
]

# ------------------------------------------------------------------ rotación por cartera
CART = [
 ('A · BERTUCCI (264900)', [
   ('NVDA / MSFT / SPY / GOOGL / AMZN', 'MANTENER', 'Núcleo tech: el motor es NVDA (26/08); MSFT +23,6% no se persigue.'),
   ('SMH / TSM', 'REDUCIR → rotar a NVDA o GLD/SLV', 'Semis débiles (SMH −4,2% y TSM −2,8% ayer en ARS); rotación interna del sector.'),
   ('MP', 'SALIR (hoy earnings 06/08)', 'Usar el rebote (+4% ayer); P/S 24x insostenible.'),
   ('URA / PAMP', 'MANTENER', 'Nuclear y energía local; PAMP en pausa (−0,7%).'),
   ('USD 59% en caja', 'DEPLOYAR en 3 tramos', '→ GLD/SLV (10-15%), NVDA en pullback, HUM/PFE, GGAL/BMA, VIST/YPF.'),
 ]),
 ('B · Diversificada (AAPL/LMT/MSFT/NU/PEP/PFE/SLV/URA/XLE + bonos)', [
   ('SLV', 'MANTENER (agregar si falta)', 'El activo del régimen: +4,1% ayer; hedge estanflación.'),
   ('LMT / URA / XLE', 'MANTENER (toma parcial en XLE)', 'Defensa, nuclear y energía: exactamente los sectores favorecidos.'),
   ('GOOGL (+213%) / YMCIO (+95,8%) / IRCFO (+141,7%) / IRCPO (+43,8%)', 'TOMAR GANANCIAS parciales', 'Reciclar el exceso a GLD/SLV y caja; no dejar ganancias de +100-200% sin gestionar.'),
   ('CRCEO (−50,8%)', 'SALIR', 'ON vencida 04/06/2025: papel muerto, no aporta.'),
   ('CEG (−6,4%) / PEP / PFE', 'MANTENER', 'Nuclear y defensivas; temática intacta.'),
 ]),
 ('C · Conservadora (MCD + GALILEO + Consultatio RF)', [
   ('FCIs renta fija (GALILEO, Consultatio)', 'MANTENER', 'Capturan tasas; refugio del régimen.'),
   ('MCD', 'MANTENER', 'Defensiva de consumo; sin señales de debilidad.'),
   ('Opcional: GLD 3-5%', 'AGREGAR', 'Hedge de estanflación para una cartera conservadora.'),
 ]),
]

# ------------------------------------------------------------------ régimen (KPIs)
REGIMEN = [
 ('VIX', '15,6', 'Risk-on, pero subiendo la sensibilidad'),
 ('Curva 10Y−3M', '+106 pb', 'Positiva: NIM bancario, crecimiento'),
 ('Oro / Plata', '+4,1% / +4,1%', 'LA SEÑAL: estanflación + Hormuz'),
 ('Brent', '~$80', 'Prima geopolítica: Ormuz 0 tránsitos'),
 ('ADP julio', '+44K vs 70K', 'Peor desde enero; refuerza recorte Fed'),
 ('ISM Servicios', '54,1 · empleo 47,4 · precios 70,3', 'Estanflación incipiente'),
 ('Hoy / Mañana', 'Jobless 195K · NFP julio', 'Evento binario de la semana'),
 ('Riesgo país', '430 bps', 'Local estable; YPF vende Chachahuén → Vaca Muerta'),
]

# ------------------------------------------------------------------ HTML
css = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#0d1117;color:#e6edf3}
.wrap{max-width:1120px;margin:0 auto;padding:22px}
h1{font-size:23px;margin:0 0 4px;color:#fff}
h2{font-size:16px;border-left:4px solid #f0b90b;padding-left:10px;margin:24px 0 10px;color:#f0b90b}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:#21262d;color:#8b949e;text-align:left;padding:6px 8px}
td{padding:5px 8px;border-top:1px solid #21262d;vertical-align:top}
.pos{color:#3fb950;font-weight:600}.neg{color:#f85149;font-weight:600}.neu{color:#d29922}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700;color:#0d1117}
.b-comprar{background:#3fb950}.b-mantener{background:#58a6ff}.b-reducir{background:#d29922}.b-salir{background:#f85149}
.kpi{display:inline-block;background:#21262d;border-radius:8px;padding:7px 13px;margin:3px 5px 3px 0;font-size:12.5px}
.kpi b{font-size:15px}
.nota{font-size:11.5px;color:#8b949e;margin-top:8px}
footer{font-size:11px;color:#8b949e;margin-top:20px;text-align:center}
"""

BADGE = {'COMPRAR': 'b-comprar', 'MANTENER': 'b-mantener', 'REDUCIR': 'b-reducir', 'SALIR': 'b-salir'}

h = ['<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
     '<title>Informe matutino — 06/08/2026 · En qué invertir hoy</title><style>' + css + '</style></head><body><div class="wrap">']
h.append('<h1>📰 Informe matutino — Lo que hay que saber esta mañana</h1>')
h.append('<div class="nota">Jueves 06/08/2026 · Coronar Inversiones ETR · datos reales (yfinance cierre 05/08, briefing #Inviu, ADP, Kpler/Reuters, AMD IR, CVS IR) · fuentes citadas al pie</div>')

h.append('<h2>1) Régimen intermarket</h2><div class="card">')
for k, v, l in REGIMEN:
    h.append('<span class="kpi">' + k + '<br><b>' + v + '</b><br><span style="color:#8b949e">' + l + '</span></span>')
h.append('</div>')

h.append('<h2>2) En qué invertir hoy — sectores favorecidos y empresas</h2>')
for titulo, etf, items in SECCIONES:
    h.append('<div class="card"><div><b style="font-size:14px">' + titulo + '</b> <span class="nota">ETF proxy: ' + etf + '</span></div>')
    h.append('<table style="margin-top:6px"><tr><th>Activo</th><th>Acción</th><th>Por qué</th></tr>')
    for tk, nombre, acc, porque in items:
        b = BADGE.get(acc.split(' ')[0], 'b-mantener')
        h.append('<tr><td><b>' + tk + '</b><br><span class="nota">' + nombre + '</span></td><td><span class="badge ' + b + '" style="color:#fff">' + acc + '</span></td><td>' + porque + '</td></tr>')
    h.append('</table></div>')

h.append('<h2>3) Táctica (evento binario: NFP mañana)</h2><div class="card">')
h.append('<table><tr><th>Activo</th><th>Acción</th><th>Por qué</th></tr>')
for tk, nombre, acc, porque in TACTICA:
    b = BADGE.get(acc.split(' ')[0], 'b-mantener')
    h.append('<tr><td><b>' + tk + '</b><br><span class="nota">' + nombre + '</span></td><td><span class="badge ' + b + '" style="color:#fff">' + acc + '</span></td><td>' + porque + '</td></tr>')
h.append('</table></div>')

h.append('<h2>4) Plan de rotación por cartera (arancel 0,90% — ejecutar en tramos)</h2>')
for car, rows in CART:
    h.append('<div class="card"><div><b style="font-size:14px">' + car + '</b></div>')
    h.append('<table style="margin-top:6px"><tr><th>Posición</th><th>Acción</th><th>Detalle</th></tr>')
    for pos, acc, det in rows:
        b = BADGE.get(acc.split(' ')[0], 'b-mantener')
        h.append('<tr><td><b>' + pos + '</b></td><td><span class="badge ' + b + '" style="color:#fff">' + acc + '</span></td><td>' + det + '</td></tr>')
    h.append('</table></div>')

# ------------------------------------------------------------------ montos y tramos por cartera (valores reales del paste 05/08)
FEE = 0.009
MONTOS = [
 {'car': 'A · BERTUCCI (264900) — total ≈ $25,6M ARS · caja USD ≈ $15,8M (59%)',
  'rows': [
   ('Deploy 50% de la caja USD', '$7,9M', '$2,64M', 'GLD/SLV $3,2M · NVDA pullback $1,6M · HUM/PFE $1,6M · GGAL/BMA $0,8M · VIST/YPF $0,8M'),
   ('Mantener 50% caja USD', '$7,9M', '—', 'Dry powder hasta el NFP de mañana (evento binario)'),
   ('Rotar: SMH/TSM −50%', '$0,05M', '$0,02M', 'Reciclar a GLD/SLV; semis débiles'),
   ('Salir: MP 100%', '$0,05M', '$0,02M', 'Earnings hoy 06/08: usar el rebote (+4% ayer)'),
  ]},
 {'car': 'B · Diversificada (AAPL/LMT/MSFT/NU/PEP/PFE/SLV/URA/XLE + bonos) — total ≈ $23,6M ARS',
  'rows': [
   ('Tomar ganancias: GOOGL (+213%) 50%', '$0,25M', '$0,08M', 'Reciclar a GLD/SLV'),
   ('Tomar: YMCIO (+95,8%) 50%', '$0,14M', '$0,05M', 'Carry realizado; no dejar +95% sin gestionar'),
   ('Tomar: IRCFO (+141,7%) 100%', '$0,04M', '$0,01M', 'Realizar la ganancia extrema'),
   ('Tomar: IRCPO (+43,8%) 50%', '$0,03M', '$0,01M', 'Reciclar'),
   ('Tomar: XLE (+81,7%) 30%', '$0,11M', '$0,04M', 'Energía en pico de margen: asegurar parte'),
   ('Salir: CRCEO (vencida) 100%', '$0,004M', '$0,001M', 'Papel vencido 06/2025, no aporta'),
   ('Reasignar lo reciclado (~$0,57M)', 'GLD/SLV 60% · Caja 40%', '—', 'Refuerza el hedge del régimen'),
  ]},
 {'car': 'C · Conservadora (MCD + GALILEO + Consultatio RF) — total ≈ $7,1M ARS',
  'rows': [
   ('Mantener FCIs RF + MCD', '—', '—', 'Refugio: tasas altas locales'),
   ('Opcional: GLD 3%', '$0,21M', '$0,07M', 'Hedge de estanflación (solo si el cliente acepta volatilidad)'),
  ]},
]

h.append('<h2>4.1) Montos y tramos (arancel 0,90% — 3 tramos semanales)</h2>')
for mc in MONTOS:
    h.append('<div class="card"><div><b style="font-size:13.5px">' + mc['car'] + '</b></div>')
    h.append('<table style="margin-top:6px"><tr><th>Acción</th><th>Monto total</th><th>Por tramo (1/3)</th><th>Detalle</th></tr>')
    for acc, monto, tramo, det in mc['rows']:
        h.append('<tr><td>' + acc + '</td><td><b>' + monto + '</b></td><td>' + tramo + '</td><td>' + det + '</td></tr>')
    h.append('</table></div>')

h.append('<h2>5) Noticias del período validadas</h2><div class="card">')
h.append('<table><tr><th>Noticia</th><th>Validación</th></tr>')
for n_, f_ in [
 ('ADP julio +44K (vs 70K): peor desde enero; junio revisado a 95K; salarios job-changers +7%', 'ADP oficial · CNBC · Haver ✅'),
 ('ISM Servicios 54,1: empleo 47,4 (contracción), precios 70,3 (↑) — estanflación incipiente', 'ISM/Briefing ✅'),
 ('Hormuz: 0 tránsitos de petroleros (Kpler 04-05/08 vs >100/día pre-guerra); hutíes atacan petrolero saudita en Yanbu', 'Kpler · Reuters · BBC · Oman Observer ✅'),
 ('Brent ~$80 tras el ataque; Trump advierte sobre reabrir Ormuz', 'Briefing + Reuters ✅'),
 ('AMD −7% pese a beat (revenue $11,54B, EPS $1,66): margen bruto 56% por debajo de lo pretendido', 'AMD IR + Briefing ✅'),
 ('CVS Q2 beat (EPS adj $2,58) + guidance alzada, pero −5,1% (sell-the-news)', 'CVS IR + Yahoo ✅'),
 ('YPF vende Chachahuén (Mendoza) por USD 200M → Plan 4x4 → foco Vaca Muerta', 'Briefing + YPF ✅'),
]:
    h.append('<tr><td>' + n_ + '</td><td>' + f_ + '</td></tr>')
h.append('</table>')
h.append('<div class="nota">Fuentes: yfinance (series/precios), unificado completo.json (mapeo sectores/ETFs/CEDEARs), screener propio (253 tickers, datos 04/08), ADP, ISM, Kpler, Reuters, BBC, AMD IR, CVS IR, Marathon/Valero IR, briefing #Inviu. Informe informativo — no constituye recomendación de inversión; la recomendación formal corresponde al AP regulado CNV (Coronar Inversiones ETR).</div></div>')
h.append('<footer>Generado ' + datetime.now().strftime('%d/%m/%Y %H:%M') + ' · pipeline Coronar Inversiones ETR</footer>')
h.append('</div></body></html>')

open('clientes/informe_matutino_20260806.html', 'w', encoding='utf-8').write('\n'.join(h))
print('OK -> clientes/informe_matutino_20260806.html', len('\n'.join(h)), 'bytes')

print('--- EN QUE INVERTIR HOY (resumen) ---')
for titulo, etf, items in SECCIONES:
    print(titulo)
    for tk, nombre, acc, porque in items:
        print('  %-9s %-22s %s' % (tk, nombre, acc))
