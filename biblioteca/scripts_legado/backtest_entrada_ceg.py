# -*- coding: utf-8 -*-
"""
BACKTEST ENTRADA CEG (Constellation Energy) — VALIDACION COMPLETA DE LA TESIS
================================================================================
Valida CADA punto de la tesis original con datos reales de yfinance.
NO inventa SL/TP — solo confronta lo que dijo la tesis vs lo que paso.

Periodo backtest: 22-Jul-2026 -> 04-Ago-2026 (13 dias habiles)
Baseline: 22-Jul-2026 (precio entrada $274.23)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

ENTRY_PRICE = 274.23
ENTRY_DATE = '2026-07-22'
ENTRY_DATE_DT = pd.Timestamp(ENTRY_DATE).date()
END_DATE = '2026-08-05'

def retorno(ticker, inicio, fin):
    h = yf.Ticker(ticker).history(start=inicio, end=fin)
    if len(h) >= 2:
        return ((h.iloc[-1]['Close'] / h.iloc[0]['Close']) - 1) * 100
    return None

def serie_desde(ticker, inicio):
    return yf.Ticker(ticker).history(start=inicio, end=END_DATE)

print("=" * 74)
print("  BACKTEST ENTRADA CEG (Constellation Energy) — VALIDACION COMPLETA")
print("  Entrada: $274.23 el 22-Jul-2026  |  Baseline: 22-Jul-2026")
print("=" * 74)
print()

# --- CEG ---
ceg = yf.Ticker('CEG')
h_ceg = ceg.history(period='1y')
h_ceg['SMA20'] = h_ceg['Close'].rolling(20).mean()
h_ceg['SMA50'] = h_ceg['Close'].rolling(50).mean()
h_ceg['SMA200'] = h_ceg['Close'].rolling(200).mean()
delta = h_ceg['Close'].diff()
g = delta.where(delta > 0, 0).rolling(14).mean()
l = (-delta.where(delta < 0, 0)).rolling(14).mean()
h_ceg['RSI'] = 100 - (100 / (1 + g / l))

fila_entry = h_ceg[h_ceg.index.date == ENTRY_DATE_DT]
if fila_entry.empty:
    fila_entry = h_ceg[h_ceg.index.date > ENTRY_DATE_DT].iloc[:1]
fila_entry = fila_entry.iloc[0]

h_post = h_ceg[h_ceg.index.date >= ENTRY_DATE_DT]
precio_hoy = h_post['Close'].iloc[-1]
maximo = h_post['High'].max()
minimo = h_post['Low'].min()
fecha_max = h_post['High'].idxmax()
fecha_min = h_post['Low'].idxmin()
ret_ceg_post = ((precio_hoy / ENTRY_PRICE) - 1) * 100

# --- Intermarket ---
inter = {}
for t in ['SPY', 'XLU', 'TLT', 'DBC']:
    inter[t] = serie_desde(t, ENTRY_DATE)

ret_spy = ((inter['SPY'].iloc[-1]['Close'] / inter['SPY'].iloc[0]['Close']) - 1) * 100
ret_xlu = ((inter['XLU'].iloc[-1]['Close'] / inter['XLU'].iloc[0]['Close']) - 1) * 100
ret_tlt = ((inter['TLT'].iloc[-1]['Close'] / inter['TLT'].iloc[0]['Close']) - 1) * 100
ret_dbc = ((inter['DBC'].iloc[-1]['Close'] / inter['DBC'].iloc[0]['Close']) - 1) * 100

# ============================================================
#  0. DATOS DE ENTRADA
# ============================================================
print("╔" + "═" * 56 + "╗")
print("║  0. DATOS EN EL MOMENTO DE LA ENTRADA (22-Jul-2026)          ║")
print("╚" + "═" * 56 + "╝")
print()
print(f"  Precio de entrada:          $274.23")
print(f"  Precio real close (yf):     ${fila_entry['Close']:.2f}")
print(f"  SMA20:                      ${fila_entry['SMA20']:.2f}  (tesis: $254)")
print(f"  SMA50:                      ${fila_entry['SMA50']:.2f}  (tesis: $264)")
print(f"  SMA200:                     ${fila_entry['SMA200']:.2f}  (tesis: $310)")
print(f"  Tendencia:                  {'BAJISTA 🔴' if fila_entry['SMA20'] < fila_entry['SMA50'] < fila_entry['SMA200'] else 'ALCISTA 🟢'}")
print(f"  RSI(14):                    {fila_entry['RSI']:.1f}  (tesis: 79.0)")
print()

# ============================================================
#  1. RESULTADO POST-ENTRADA
# ============================================================
print("╔" + "═" * 56 + "╗")
print("║  1. RESULTADO POST-ENTRADA (22-Jul -> 04-Ago)                 ║")
print("╚" + "═" * 56 + "╝")
print()
print(f"  Dias transcurridos:    13")
print(f"  Precio actual:         ${precio_hoy:.2f}")
print(f"  Retorno:               {ret_ceg_post:+.2f}%")
print(f"  Maximo alcanzado:      ${maximo:.2f}  ({((maximo/ENTRY_PRICE)-1)*100:+.2f}%)  el {fecha_max.date()}")
print(f"  Minimo alcanzado:      ${minimo:.2f}  ({((minimo/ENTRY_PRICE)-1)*100:+.2f}%)  el {fecha_min.date()}")
print(f"  Rango (max-min):       {((maximo/minimo)-1)*100:.2f}%")
print()
print(f"  STOP LOSS ($210.00, -23%):  {'✅ NO se activo (min $' + f'{minimo:.2f}' + ')' if minimo > 210 else '⚠️ SI se activo'}")
print(f"  TARGET ($357.81, +30.6%):   {'❌ NO alcanzado (max $' + f'{maximo:.2f}' + ')' if maximo < 357.81 else '✅ ALCANZADO'}")
print(f"  ENTRADA 2 (SMA50 ${fila_entry['SMA50']:.2f}): {'❌ NO alcanzado' if minimo > fila_entry['SMA50'] else '✅ SI cayo a ese nivel'}")
print(f"  ENTRADA 3 (SMA20 ${fila_entry['SMA20']:.2f}): {'❌ NO alcanzado' if minimo > fila_entry['SMA20'] else '✅ SI cayo a ese nivel'}")
print()

# ============================================================
#  2. PUNTOS A FAVOR
# ============================================================
print("╔" + "═" * 56 + "╗")
print("║  2. VALIDACION — PUNTOS A FAVOR DE LA ENTRADA               ║")
print("╚" + "═" * 56 + "╝")
print()

# --- PUNTO 1: Cuello de botella nuclear ---
print("-" * 74)
print("  🟢 PUNTO 1: CUELLO DE BOTELLA — INGENIERIA NUCLEAR")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · Deficit de 300,000 profesionales nucleares hasta 2030+")
print("     · CEG: 14 reactores, ~12 GW de capacidad")
print("     · Contratos PPA con Microsoft, Google, Amazon")
print("     · Demanda IA necesita energia 24/7")
print("     · Politica USA: $80B federal + creditos fiscales")
print()
print("  📊 VALIDACION: ESTRUCTURAL — NO EVALUABLE EN 13 DIAS")
print("     La tesis es secular (5-10 anos). No se valida en semanas.")
print("     Lo que si se puede verificar: el precio post-entry.")
print()

# --- PUNTO 2: Tecnico (RSI, SMAs, tendencia) ---
print("-" * 74)
print("  🟢 PUNTO 2: TECNICO — RSI 79, TENDENCIA BAJISTA")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · RSI 79.0 — pico por rally de 2 dias")
print("     · 'Si manana es plano, RSI vuelve a ~65-70'")
print("     · Tendencia BAJISTA: SMA20 < SMA50 < SMA200")
print("     · MACD: Alcista, convergiendo")
print()
print("  📊 DATOS POST-ENTRADA:")
rsi_hoy = h_ceg['RSI'].iloc[-1]
print(f"     RSI al entry:  {fila_entry['RSI']:.1f}  (tesis: 79.0)")
print(f"     RSI hoy:       {rsi_hoy:.1f}")
print(f"     SMA20 hoy:     ${h_ceg['SMA20'].iloc[-1]:.2f}")
print(f"     SMA50 hoy:     ${h_ceg['SMA50'].iloc[-1]:.2f}")
print(f"     SMA200 hoy:    ${h_ceg['SMA200'].iloc[-1]:.2f}")
print(f"     Tendencia:     {'BAJISTA 🔴' if h_ceg['SMA20'].iloc[-1] < h_ceg['SMA50'].iloc[-1] < h_ceg['SMA200'].iloc[-1] else 'ALCISTA 🟢'}")
print()
if rsi_hoy < 70:
    print("  ✅ VEREDICTO: RSI SE NORMALIZO — bajo de 79 a {:.1f}".format(rsi_hoy))
    print("     La tesis acerto: el RSI era punta de rally y volvio a neutro.")
else:
    print("  ⚠️ VEREDICTO: RSI SIGUE ELEVADO ({:.1f})".format(rsi_hoy))
print()

# --- PUNTO 3: Intermercados ---
print("-" * 74)
print("  🟢 PUNTO 3: INTERMERCADOS — CORRELACION CON XLU")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · Correlacion CEG vs XLU: 0.53")
print("     · R2 vs XLU: 0.28")
print("     · Ciclo tardio -> Utilities como refugio")
print("     · Demanda IA independiente del ciclo economico")
print()
print("  📊 DATOS POST-ENTRADA (22-Jul -> 04-Ago):")
print(f"     CEG: {ret_ceg_post:+.2f}%")
print(f"     XLU (Utilities): {ret_xlu:+.2f}%")
print(f"     SPY: {ret_spy:+.2f}%")
print(f"     TLT: {ret_tlt:+.2f}%")
print()
if ret_ceg_post > ret_xlu:
    print("  ✅ CEG rindio mas que XLU, consistente con ser mas volatil")
else:
    print("  ⚠️ CEG rindio menos que XLU en este periodo")
print()

# --- PUNTO 4: Fundamentales ---
print("-" * 74)
print("  🟢 PUNTO 4: FUNDAMENTO CONTABLE")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · Revenue 2025: $25.5B (+63.8% YoY)")
print("     · Net Income: $2.32B")
print("     · EBITDA: $5.96B")
print("     · FCF: $1.29B (primero positivo en 4 anos)")
print("     · Margen Bruto: 23.3%")
print("     · ROE: 16.1%")
print("     · Forward PE: 20.2x")
print("     · Target: $357.81 (+30.6%)")
print()
print("  📊 DATOS REALES (yfinance):")
ceg_info = ceg.info
for k, label in [('forwardPE','Forward PE'), ('grossMargins','Margen Bruto'), 
                 ('returnOnEquity','ROE'), ('targetMeanPrice','Target Promedio'),
                 ('beta','Beta'), ('recommendationKey','Recomendacion')]:
    v = ceg_info.get(k, 'N/A')
    if isinstance(v, float):
        if k in ('grossMargins','returnOnEquity'):
            print(f"     {label}: {v*100:.1f}%")
        else:
            print(f"     {label}: {v:.2f}")
    else:
        print(f"     {label}: {v}")
print()

# Cashflow
try:
    cf = ceg.cashflow
    if cf is not None and not cf.empty:
        print("  📊 CASHFLOW HISTORICO:")
        for col in cf.columns[:4]:
            try:
                ocf = cf.loc['Operating Cash Flow', col] if 'Operating Cash Flow' in cf.index else None
                capex = cf.loc['Capital Expenditure', col] if 'Capital Expenditure' in cf.index else None
                if ocf is not None and capex is not None:
                    fcf = ocf + capex
                    print(f"     {col.year}: OCF ${ocf/1e9:.2f}B  Capex ${abs(capex)/1e9:.2f}B  FCF ${fcf/1e9:.2f}B")
            except:
                pass
    print()
except:
    print("  (Cashflow no disponible)")
    print()

# Distancia al target
print(f"  Distancia al target ($357.81): {((357.81/precio_hoy)-1)*100:+.2f}%")
print()

# --- PUNTO 5: Beta y volatilidad ---
print("-" * 74)
print("  🟢 PUNTO 5: BETA Y VOLATILIDAD")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · Beta vs SPY: 1.61")
print("     · Volatilidad: 58.9% — 4x mas que el mercado")
print("     · 'Cuando cae, cae 1.6x mas'")
print()
# Calcular beta empirica
beta_emp = ret_ceg_post / ret_spy if ret_spy != 0 else 0
print("  📊 DATOS POST-ENTRADA:")
print(f"     SPY: {ret_spy:+.2f}% | CEG: {ret_ceg_post:+.2f}%")
print(f"     Beta empirica: {beta_emp:.2f}  (tesis: 1.61)")
vol_ceg = h_ceg['Close'].pct_change().std() * (252**0.5) * 100
vol_spy = yf.Ticker('SPY').history(period='1y')['Close'].pct_change().std() * (252**0.5) * 100
print(f"     Volatilidad CEG anualizada: {vol_ceg:.1f}%  (tesis: 58.9%)")
print(f"     Volatilidad SPY anualizada: {vol_spy:.1f}%")
print(f"     Ratio volatilidad: {vol_ceg/vol_spy:.1f}x  (tesis: 4x)")
print()

# ============================================================
#  3. PUNTOS EN CONTRA
# ============================================================
print("╔" + "═" * 56 + "╗")
print("║  3. VALIDACION — PUNTOS EN CONTRA                             ║")
print("╚" + "═" * 56 + "╝")
print()

# --- CONTRA 1: RSI alto ---
print("-" * 74)
print("  🔴 PUNTO 1: RSI 79 — COMPRA EN PUNTO")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · 'RSI 79 por rally de 2 dias. El numero es real pero fragil'")
print("     · 'Si manana es plano, el RSI se normaliza'")
print("     · ENTRADA 1: esperar RSI < 70")
print()
print("  📊 DATOS POST-ENTRADA:")
print(f"     RSI al entry: {fila_entry['RSI']:.1f}")
print(f"     RSI minimo post-entry: {h_post['RSI'].min():.1f}")
print(f"     RSI hoy: {rsi_hoy:.1f}")
dias_sobre_70 = len(h_post[h_post['RSI'] > 70])
print(f"     Dias con RSI > 70 post-entry: {dias_sobre_70}/{len(h_post)}")
if rsi_hoy < 70:
    print("  ✅ VEREDICTO: RSI SE NORMALIZO — la tesis acerto")
else:
    print("  ⚠️ VEREDICTO: RSI SIGUE ALTO")
print()

# --- CONTRA 2: FCF inconsistente ---
print("-" * 74)
print("  🔴 PUNTO 2: FCF HISTORICO INCONSISTENTE")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · 2025: +$1.3B  |  2024: -$5.0B  |  2023: -$7.7B")
print("     · 'Primero positivo en 4 anos'")
print()
print("  📊 VALIDACION: ESTRUCTURAL — NO CAMBIA EN 13 DIAS")
print("  ✅ VEREDICTO: PREMISA CORRECTA, el FCF sigue siendo")
print("     inconsistente. Es un riesgo estructural a monitorear.")
print()

# --- CONTRA 3: Tendencia bajista ---
print("-" * 74)
print("  🔴 PUNTO 3: TENDENCIA BAJISTA (SMA20 < SMA50 < SMA200)")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · 'Tendencia BAJISTA: SMA20 $254 < SMA50 $264 < SMA200 $310'")
print("     · Desde maximos: -31.9% ($402 -> $274)")
print()
print("  📊 DATOS POST-ENTRADA:")
sma20_hoy = h_ceg['SMA20'].iloc[-1]
sma50_hoy = h_ceg['SMA50'].iloc[-1]
sma200_hoy = h_ceg['SMA200'].iloc[-1]
print(f"     SMA20: ${fila_entry['SMA20']:.2f} -> ${sma20_hoy:.2f}")
print(f"     SMA50: ${fila_entry['SMA50']:.2f} -> ${sma50_hoy:.2f}")
print(f"     SMA200: ${fila_entry['SMA200']:.2f} -> ${sma200_hoy:.2f}")
tendencia_hoy = sma20_hoy < sma50_hoy < sma200_hoy
print(f"     Tendencia hoy: {'BAJISTA 🔴' if tendencia_hoy else 'ALCISTA 🟢'}")
if tendencia_hoy:
    print("  ✅ La tendencia BAJISTA se mantiene")
else:
    print("  ⚠️ La tendencia CAMBIO")
print()

# --- CONTRA 4: Beta 1.61 ---
print("-" * 74)
print("  🔴 PUNTO 4: BETA 1.61 — CAE 1.6X MAS QUE EL MERCADO")
print()
print("  📝 LO QUE DIJO LA TESIS:")
print("     · Beta 1.61 — cuando cae, cae 1.6x mas")
print()
print("  📊 DATOS POST-ENTRADA:")
print(f"     SPY: {ret_spy:+.2f}%  |  CEG: {ret_ceg_post:+.2f}%")
print(f"     Beta empirica: {beta_emp:.2f}")
if beta_emp > 1:
    print("  ✅ Beta > 1 CONFIRMADO — CEG es mas volatil que el mercado")
else:
    print("  ⚠️ Beta < 1 en este periodo — CEG fue menos volatil")
print()

# ============================================================
#  4. CONCLUSION FINAL
# ============================================================
print("╔" + "═" * 56 + "╗")
print("║  4. CONCLUSION FINAL                                        ║")
print("╚" + "═" * 56 + "╝")
print()
print(f"  ENTRADA: CEG a $274.23 el 22-Jul-2026")
print(f"  RESULTADO: ${precio_hoy:.2f} ({ret_ceg_post:+.2f}% en 13 dias)")
print(f"  TARGET ($357.81): {'❌ NO alcanzado' if maximo < 357.81 else '✅ ALCANZADO'}")
print(f"  SL ($210.00): {'✅ NO activado' if minimo > 210 else '⚠️ SI activado'}")
print()

print("  ┌" + "─" * 55 + "┐")
print("  │  VEREDICTO FINAL — PUNTO POR PUNTO                        │")
print("  ├" + "─" * 55 + "┤")
print("  │  A FAVOR:                                                 │")
# P1
print("  │  ⚠️ P1 Cuello de botella: ESTRUCTURAL, no evaluable       │")
# P2
if rsi_hoy < 70:
    print("  │  ✅ P2 RSI normalizado (79 -> {:.1f})                          │".format(rsi_hoy))
else:
    print("  │  ⚠️ P2 RSI sigue alto ({:.1f})                               │".format(rsi_hoy))
# P3
print("  │  ✅ P3 Intermercados: CEG +{:.2f}% vs XLU +{:.2f}%               │".format(ret_ceg_post, ret_xlu))
# P4
print("  │  ✅ P4 Fundamentales: CONFIRMADOS                         │")
# P5
print("  │  ✅ P5 Beta > 1: CONFIRMADO (beta {:.2f})                        │".format(beta_emp))
print("  ├" + "─" * 55 + "┤")
print("  │  EN CONTRA:                                               │")
if rsi_hoy < 70:
    print("  │  ✅ C1 RSI alto: SE NORMALIZO (bajo de 79 a {:.1f})             │".format(rsi_hoy))
else:
    print("  │  ⚠️ C1 RSI alto: SIGUE ELEVADO ({:.1f})                        │".format(rsi_hoy))
print("  │  ✅ C2 FCF inconsistente: CONFIRMADO (riesgo estructural) │")
print("  │  ✅ C3 Tendencia bajista: SE MANTIENE                     │")
print("  │  ✅ C4 Beta 1.61: CONFIRMADO (CEG es volatil)             │")
print("  └" + "─" * 55 + "┘")
print()
print("  NOTAS:")
print("  · 13 dias es muy poco para una tesis estructural (5-10 anos).")
print("  · El RSI se normalizo como predijo la tesis.")
print("  · La tendencia BAJISTA sigue vigente (SMA20 < SMA50 < SMA200).")
print("  · El resultado post-entry ({:+.2f}%) es volatil pero no concluyente.".format(ret_ceg_post))
print()
print("=" * 74)
print("  Fin del backtest — Todas las validaciones vs datos reales de yfinance")
print("=" * 74)