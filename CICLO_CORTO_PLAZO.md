# Ciclo de Corto Plazo - Rango Normalizado
**Fecha:** 2026-08-28 08:07

## 1. Fase del Ciclo Intermarket
- **Fase Murphy:** 2 - Mid Expansion
- **Sectores beneficiados:** XLI, XLB, XLF, COPX/JJC, XLE
- **Fuente:** SCANNER_INTERMARKET (fase 2: Mid Expansion, conf ALTA)

## 2. Metodologia
- **Ventanas de rango:** 21D, 63D, 126D (1M, 3M, 6M)
- **Rango normalizado:** `(precio - min) / (max - min) * 100`
  - 0%% = precio en el minimo de la ventana (mas upside)
  - 100%% = precio en el maximo de la ventana (menos upside)
- **Ganancia max:** `(max - precio) / precio * 100` (si vuelve al max)
- **Perdida min:** `(precio - min) / precio * 100` (si cae al min)
- **Score:** combina fase + rango + momentum + regla de oro (0-100)

## 3. Ranking por Score de Oportunidad

| ticker   | nombre               |   precio |   score | recomendacion        |   rango_1m_pct |   gan_max_1m |   rango_3m_pct |   gan_max_3m |   rango_6m_pct |   gan_max_6m |   momentum_vs_spy | regla_oro         | es_lider_fase   |
|:---------|:---------------------|---------:|--------:|:---------------------|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|------------------:|:------------------|:----------------|
| AAPL     | AAPL                 |   305.93 |    44.9 | VIGILAR              |            9.8 |        11.07 |           47.8 |        11.07 |           63.8 |        11.07 |              5.36 | CAMBIO DE REGIMEN | False           |
| AMZN     | AMZN                 |   263.17 |    37.7 | VIGILAR              |           63.7 |         7.92 |           63.7 |         7.92 |           75.5 |         7.92 |             17.93 | CAMBIO DE REGIMEN | False           |
| CEG      | CEG                  |   282.41 |    26.1 | NO RECOMENDADO       |          100   |         0    |           90.4 |         1.73 |           49   |        17.06 |            -16.23 | NEUTRO            | True            |
| CVS      | CVS                  |    92.92 |    52.2 | OPORTUNIDAD MODERADA |            0.2 |        13.4  |           18.9 |        18.29 |           58.4 |        18.29 |             11.2  | NEUTRO            | False           |
| GLD      | Oro                  |   401.48 |    19.2 | NO RECOMENDADO       |           90.8 |         0.86 |           68.3 |         4.22 |           29.2 |        22.05 |            -27.68 | CAMBIO DE REGIMEN | False           |
| GOOGL    | GOOGL                |   345.2  |    20.9 | NO RECOMENDADO       |           45.9 |         9.4  |           34.8 |        14.92 |           55.7 |        16.56 |             -1.4  | NEUTRO            | False           |
| IBM      | IBM                  |   234.32 |    24.3 | NO RECOMENDADO       |           88   |         1.75 |           24.5 |        39.5  |           24.5 |        39.5  |            -23.85 | CAMBIO DE REGIMEN | False           |
| IWM      | Small Caps           |   299.81 |    13.3 | NO RECOMENDADO       |           62   |         1.76 |           78.1 |         1.76 |           92   |         1.76 |              2.05 | NEUTRO            | False           |
| LMT      | LMT                  |   608.68 |    23.5 | NO RECOMENDADO       |          100   |         0    |          100   |         0    |           64.8 |        10.45 |            -20.08 | NEUTRO            | True            |
| MU       | MU                   |   971.66 |    28   | NO RECOMENDADO       |           92.6 |         1.91 |           54.6 |        24.88 |           72.9 |        24.88 |            121.71 | NEUTRO            | False           |
| NU       | NU                   |    14.88 |    24.5 | NO RECOMENDADO       |           79   |         2.35 |           90.4 |         2.35 |           85.6 |         3.7  |            -23.91 | NEUTRO            | True            |
| NVDA     | NVDA                 |   225.3  |    13.1 | NO RECOMENDADO       |          100   |         0    |          100   |         0    |           85.6 |         4.51 |              8.93 | NEUTRO            | False           |
| PEP      | PEP                  |   139.72 |    29.4 | NO RECOMENDADO       |           28.7 |         3.54 |           42.2 |         4.67 |           15.1 |        19.16 |            -27.96 | CAMBIO DE REGIMEN | False           |
| PFE      | PFE                  |    28.02 |     3.6 | NO RECOMENDADO       |           85   |         1.96 |           89.6 |         1.96 |           89.6 |         1.96 |            -13.99 | NEUTRO            | False           |
| QQQ      | Nasdaq100            |   721.11 |    16.9 | NO RECOMENDADO       |           77.4 |         1.52 |           71   |         3.36 |           87.1 |         3.36 |              7.28 | NEUTRO            | False           |
| SLV      | SLV                  |    62.77 |    17.5 | NO RECOMENDADO       |          100   |         0    |           69   |         8.86 |           35.8 |        35.4  |            -30.58 | CAMBIO DE REGIMEN | False           |
| SMH      | SMH                  |   584.7  |    28.4 | NO RECOMENDADO       |           94.8 |         0.76 |           48.9 |        14.4  |           72.5 |        14.4  |             28.95 | NEUTRO            | False           |
| TLT      | Bonos Largos         |    82.04 |    47   | VIGILAR              |            5.3 |         2.61 |            2.5 |         5.78 |            1.7 |         8.23 |            -20.93 | CAMBIO DE REGIMEN | False           |
| TSM      | TSM                  |   426.09 |    15.8 | NO RECOMENDADO       |           92.1 |         1.03 |           50   |        12.08 |           68.2 |        12.08 |              2.45 | NEUTRO            | False           |
| URA      | URA                  |    44.9  |    40.2 | VIGILAR              |           95.5 |         0.78 |           46.4 |        18.98 |           35.6 |        29.76 |            -27.96 | CAMBIO DE REGIMEN | True            |
| XLB      | Materiales           |    52.54 |    24.8 | NO RECOMENDADO       |           78.2 |         1.33 |           84   |         1.33 |           89.5 |         1.33 |            -15.1  | NEUTRO            | True            |
| XLC      | Comunicacion         |   112.95 |    15.7 | NO RECOMENDADO       |          100   |         0    |           67   |         3.3  |           56.4 |         5.17 |            -15.31 | CAMBIO DE REGIMEN | False           |
| XLE      | Energia              |    61.91 |    26   | NO RECOMENDADO       |          100   |         0    |          100   |         0    |           97.8 |         0.33 |              1.02 | NEUTRO            | True            |
| XLF      | Financieros          |    57.88 |    28.8 | NO RECOMENDADO       |           68.6 |         0.74 |           94.4 |         0.74 |           96   |         0.74 |             -0.88 | NEUTRO            | True            |
| XLI      | Industriales         |   186.51 |    23.5 | NO RECOMENDADO       |          100   |         0    |          100   |         0    |          100   |         0    |             -4.93 | NEUTRO            | True            |
| XLK      | Tecnologia           |   190.01 |    24   | NO RECOMENDADO       |           96.9 |         0.4  |           74.6 |         4.19 |           88.7 |         4.19 |             22.02 | NEUTRO            | False           |
| XLP      | Defensiva Consumidor |    86.09 |     8.4 | NO RECOMENDADO       |           69.4 |         1.48 |           79.2 |         1.48 |           67.5 |         3.25 |            -17.07 | NEUTRO            | False           |
| XLRE     | Bienes Raices        |    44.66 |    11.9 | NO RECOMENDADO       |           45.3 |         1.57 |           56.7 |         3.02 |           78.7 |         3.02 |             -8.77 | NEUTRO            | False           |
| XLU      | Utilidades           |    44.31 |    26.5 | NO RECOMENDADO       |           37.3 |         4.47 |           42.8 |         4.47 |           34.7 |         6.29 |            -17.89 | CAMBIO DE REGIMEN | False           |
| XLV      | Salud                |   171.58 |     5.6 | NO RECOMENDADO       |           69.8 |         2.39 |           86.3 |         2.39 |           87.7 |         2.39 |             -7.4  | NEUTRO            | False           |
| XLY      | Consumo Ciclico      |   115.88 |    21   | NO RECOMENDADO       |           46.7 |         3.43 |           60   |         4.1  |           63.7 |         5.12 |            -12.31 | CAMBIO DE REGIMEN | False           |

## 4. Top 5 Oportunidades de Corto Plazo

### CVS (CVS) — Score: 52.2
- **Recomendacion:** OPORTUNIDAD MODERADA
- **Precio actual:** $92.92
- **Rango 1M:** 0.2% del rango | GanMax: +13.40% | PerdMin: -0.02%
- **Rango 3M:** 18.9% del rango | GanMax: +18.29% | PerdMin: -4.27%
- **Rango 6M:** 58.4% del rango | GanMax: +18.29% | PerdMin: -25.70%
- **Momentum vs SPY (6M):** +11.20%
- **Regla de oro:** NEUTRO
- **Lider de fase:** NO

### TLT (Bonos Largos) — Score: 47.0
- **Recomendacion:** VIGILAR
- **Precio actual:** $82.04
- **Rango 1M:** 5.3% del rango | GanMax: +2.61% | PerdMin: -0.15%
- **Rango 3M:** 2.5% del rango | GanMax: +5.78% | PerdMin: -0.15%
- **Rango 6M:** 1.7% del rango | GanMax: +8.23% | PerdMin: -0.15%
- **Momentum vs SPY (6M):** -20.93%
- **Regla de oro:** CAMBIO DE REGIMEN
- **Lider de fase:** NO

### AAPL (AAPL) — Score: 44.9
- **Recomendacion:** VIGILAR
- **Precio actual:** $305.93
- **Rango 1M:** 9.8% del rango | GanMax: +11.07% | PerdMin: -1.20%
- **Rango 3M:** 47.8% del rango | GanMax: +11.07% | PerdMin: -10.14%
- **Rango 6M:** 63.8% del rango | GanMax: +11.07% | PerdMin: -19.53%
- **Momentum vs SPY (6M):** +5.36%
- **Regla de oro:** CAMBIO DE REGIMEN
- **Lider de fase:** NO

### URA (URA) — Score: 40.2
- **Recomendacion:** VIGILAR
- **Precio actual:** $44.90
- **Rango 1M:** 95.5% del rango | GanMax: +0.78% | PerdMin: -16.44%
- **Rango 3M:** 46.4% del rango | GanMax: +18.98% | PerdMin: -16.44%
- **Rango 6M:** 35.6% del rango | GanMax: +29.76% | PerdMin: -16.44%
- **Momentum vs SPY (6M):** -27.96%
- **Regla de oro:** CAMBIO DE REGIMEN
- **Lider de fase:** SI

### AMZN (AMZN) — Score: 37.7
- **Recomendacion:** VIGILAR
- **Precio actual:** $263.17
- **Rango 1M:** 63.7% del rango | GanMax: +7.92% | PerdMin: -13.88%
- **Rango 3M:** 63.7% del rango | GanMax: +7.92% | PerdMin: -13.88%
- **Rango 6M:** 75.5% del rango | GanMax: +7.92% | PerdMin: -24.46%
- **Momentum vs SPY (6M):** +17.93%
- **Regla de oro:** CAMBIO DE REGIMEN
- **Lider de fase:** NO

## 5. Advertencias
- El rango normalizado es una measure de posicion relativa, no garantiza rebote.
- Los sectores beneficiados dependen de la fase detectada; un cambio de fase invalida la tesis.
- Para activos con poca historia (< ventana), el rango puede ser enganioso.
- Combinar con fundamentales y liquidez antes de operar.
