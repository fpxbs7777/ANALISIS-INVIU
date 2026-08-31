# Informe de Decision de Inversion — Contexto Murphy
**Fecha:** 2026-08-16  |  **Ventana:** 6y

## 1. Resumen Ejecutivo

El regimen actual es **Stage 4 (bonos caen, acciones/comm suben)**. Hay 3 senales alcistas confirmadas, 5 bajistas confirmadas y 5 en cambio de regimen. El contexto global es alcista (correlaciones altas), sin signos de deflacion y con commodities liderando a bonos. La postura base es **mantener Tech/AMZN/SPY, evitar discrecional/comunicaciones/litio, y no incrementar apalancamiento**.

## 2. Regimen Macro
- **Etapa del ciclo (Pring):** Stage 4 (bonos caen, acciones/comm suben)
- **Contexto global:** bull global activo (SPY-ACWI corr +0.97); emergentes (+8.52) suben con commodities a pesar del dolar fuerte.
- **Deflacion:** NO activa — correlacion SPY-TLT +0.06, Japon vs tasas -0.04, commodities y tasas +0.16.
- **Liderazgo sectorial (200d):** XLE, XLK, XLI

## 3. Recomendaciones por Senal
### Mantener / Acumular
- **MAC2** (TNX 10Y): ALCISTA CONFIRMADA — MANTENER/ACUMULAR
- **AA1** (SPY/TLT): ALCISTA CONFIRMADA — MANTENER/ACUMULAR
- **A4** (AMZN/XLY): ALCISTA CONFIRMADA — MANTENER/ACUMULAR

### Rotar / No comprar
- **MAC3** (Curva IRX/TNX): BAJISTA CONFIRMADA — ROTAR/NO COMPRAR
- **MAC4** (VIX): BAJISTA CONFIRMADA — ROTAR/NO COMPRAR
- **S2** (XLY/SPY): BAJISTA CONFIRMADA — ROTAR/NO COMPRAR
- **S3** (XLC/SPY): BAJISTA CONFIRMADA — ROTAR/NO COMPRAR
- **A3** (MP/LIT): BAJISTA CONFIRMADA — ROTAR/NO COMPRAR

### Cambio de regimen (vigilar confirmacion)
- **MAC6** (GLD/DXY): CAMBIO DE REGIMEN — VIGILAR
- **AA2** (SPY/GLD): CAMBIO DE REGIMEN — VIGILAR
- **I3** (URA/XLE): CAMBIO DE REGIMEN — VIGILAR
- **I4** (URA/XLU): CAMBIO DE REGIMEN — VIGILAR
- **LOC3** (MERV/EEM): CAMBIO DE REGIMEN — VIGILAR

### Macro neutra (contexto sin disparador)
- **MAC1** (DXY (DOP)): NEUTRO
- **MAC5** (CRB/TLT inflacion): NEUTRO

## 4. Portafolios Reales
- No se encontró RECOMENDACIONES_PORTAFOLIOS.md. Ejecutar `python -m analisis.ejecutivo.diario --portfolio`.
- No se encontró REBALANCEO_PORTAFOLIOS.md. Ejecutar `python -m analisis.ejecutivo.diario --rebalanceo`.
- No se encontró CONSTRUCTOR_PORTAFOLIO.md. Ejecutar `python -m analisis.ejecutivo.diario --constructor`.

## 5. Riesgos y Triggers
- **Riesgo 1 — inversion de curva:** IRX +3.71% vs TNX +4.68% (spread +0.98 p.b.). Si IRX supera a TNX, re-evaluar todo el marco expansivo.
- **Riesgo 2 — defensivas toman el liderazgo:** XLP/SPY y VNQ/SPY girando al alza + VTV/VUG > 0 serian alerta de Late Expansion/Stage 5.
- **Riesgo 3 — dolar se debilita:** si DXY cae en 6m con oro/commodities subiendo, se activa el escenario flight-to-gold de los Cap.8-10.
- **Oportunidad — pata commodities:** correlacion commodities-bonos negativa (-0.16) sugiere que XLE/CRB mejora diversificacion vs un portafolio 100% Tech.

## 6. Hallazgos por Capitulo
- **Cap.11 - Asset allocation con ratios**: Comm/Bonos slope200 +31.7%
- **Cap.12 - Ciclo de negocios**: Etapa Pring: Stage 4 (bonos caen, acciones/comm suben)
- **Cap.13 - Rotacion sectorial**: Lideres: XLE, XLK
- **Cap.14 - Real estate**: REITs/SPY slope200 +0.89%
- **Cap.15 - Thinking globally**: SPY-ACWI corr +0.97
- **Cap.2 - 1990 / Guerra del Golfo (divergencias y leading)**: Bonos/Comm alerta: SI
- **Cap.3 - 1994: suba de tasas y bonos liderando**: Shock 1994: TNX +12.2% vs TLT -4.62% (alerta SI)
- **Cap.4 - 1995-99: boom desinflacionario Growth**: Boom 1995-99: DXY +3.04%, CRB +18.6%, TNX +12.2% (condiciones NO)
- **Cap.5 - 1999: tendencias que precedieron al tope**: Tech +32.4% vs Energy +12.5%; Comm+Tasas suben juntas: SI
- **Cap.6 - Review of Intermarket Principles**: SPY-ACWI corr n/a; Vinculos DXY-CRB -0.09, TLT-CRB -0.16
- **Cap.8 - Spring 2003: deflacion y flight to gold**: Oro/DXY corr -0.40; TNX-CRB -0.16
- **Cap.9 - 2002: dolar debil impulsa commodities**: DXY-CRB -0.09; TNX-CRB +0.16

## 7. Noticias del ciclo (verificacion)
| driver                  |   precio_6m% |   n |   score |
|:------------------------|-------------:|----:|--------:|
| Bonos / Tasas (TNX 10Y) |         15.8 |  10 |      -3 |
| Bonos largos (TLT)      |         -6.5 |  10 |       0 |
| Dolar (DXY)             |          2.4 |  10 |       2 |
| Acciones (SPY)          |         14.5 |  10 |       2 |
| Volatilidad (VIX)       |        -29.8 |  10 |       2 |
| Oro (GLD)               |        -13.2 |  10 |       0 |
| Mineras de oro (GDX)    |        -13.4 |  10 |       3 |
| Energia (XLE)           |         15.5 |  10 |       1 |
| Petroleo (USO)          |         66.1 |  10 |       1 |
| Tech (XLK)              |         36.5 |  10 |       3 |
| Corea (EWY)             |         34.2 |  10 |       1 |
| China (FXI)             |         -9.1 |  10 |       0 |

**Coherencia vs regimen:**
- Shock de tasas (Cap.3, alerta_1994): TNX sube y bonos caen — *mixto (hay temas de apoyo y de oposicion)* (SI)
- Commodities / energia lideran (CRB al alza; Stage 4) — *CONFIRMA el analisis* (SI)
- Riesgo geopolitico sobre suministro (Hormuz/Irán) presiona energia — *CONFIRMA el analisis* (SI)
- Dolar firme (DXY al alza en 6m) — *mixto (hay temas de apoyo y de oposicion)* (SI)
- Inflacion aun elevada / presion de costos — *CONFIRMA el analisis* (SI)
- Consumidor debil (XLY/XLP negativo, defensivas resistiendo) — *CONFIRMA el analisis* (SI)
- Volatilidad contenida (VIX bajo): complacencia tipica de late-cycle — *sin evidencia noticiosa directa* (SI)

**Interpretacion:**
> Narrativa dominante: tasas, inflacion, energia, riesgo_mdo.
> El motor marca **Stage 4 (bonos caen, acciones/comm suben)**: bonos caen mientras acciones y commodities suben. Las noticias de energia (24) y tasas (32) son las que sostienen esa lectura reflacionaria.
> Temas geopoliticos (21 noticias) dan contexto al alza de energia/oro: el shock es de oferta (stagflation), no un boom de demanda clasico.
> El oro aparece 21 veces; con DXY +2.4% y oro subiendo por miedo, la relacion dolar->oro del motor (correlacion negativa) queda en tension.

## 8. Conclusion
**Postura recomendada:** mantener lo que tiene viento a favor (SPY, AMZN, Tech), no perseguir maximos (SPY/TLT pct 98), evitar nuevas entradas en XLY/XLC/MP-LIT, y vigilar IRX>TNX + defensivas para detectar el paso a Stage 5. Considerar una pata diversificadora en commodities (XLE) dada su baja correlacion con bonos.