# Biblioteca — Índice de metodologías

Fuente: `txt metodologias\` (93 archivos). Cada entrada indica dónde se usa en el proyecto.

## Fila intermarket (Murphy) — base del scanner
| Archivo | Tema | Uso |
|---|---|---|
| `intermarket-analysis-john-murphy (1).txt` | Principios intermarket, rotación sectorial, ratio A/B, regla de oro | `analisis/libro/capitulos.py` (15 caps), `core/ratio.py`, `core/senales.py`, `scanner/fase_ciclo.py`, `scanner/senales_nucleo.py` |
| `1303.7177v2.txt` | Machine learning v4 / animation | Referencia general ML |
| `1205.3482v6.txt` | Optimisation problems | Optimización Markowitz `analisis/portafolio/constructor.py` |

## Análisis fundamental y contable — Salud Fundamental
| Archivo | Tema | Cita en código |
|---|---|---|
| `Biondi_cap4_estados.txt`, `Biondi_cap5_estado.txt`, `Biondi_cap6_estados_1SH7deB.txt`, `Biondi_cap7_estados_2.txt` | Estados contables, DuPont (Biondi cap.5) | `salud_fundamental.py: dupont()`, `calcular_metricas()` |
| `GEFT_Biondi_Unidad_2.txt` | — | — |
| `CF_Fowler_Newton_Cap_*.txt` (1,2,5,6,12,13), `CONII_*`, `ICON_*`, `IFACI_*` | Ratios, liquidez, endeudamiento (Fowler Newton), análisis por dimensiones | `salud_fundamental.py: score_*()`, `analisis/portafolio/salud_fundamental` |
| `Contabilidad-y-Finanzas-para-Dummies-PDFDrive-.txt` | D/P <0.6, liquidez ~1.1 | `score_solvencia()` |
| `DFIN_Pascale_*` (7 archivos), `DFIN_Alonso_*`, `DFIN_Lopez_*` | Altman Z 1968 (corte 2.675, gris 1.81-2.89) | `altman_z()`, `zona_altman()` |
| `MATF_Lopez_*`, `PCOM_Bustamante_*`, `ECC_Bustamante_*`, `EP_Blanchard_*`, `FPUB_Dornsbusch_*` | Valuación, macro, renta fija | Contexto macro `motor/01_intermarket.py` |
| `ValueInvestingpptx-*.txt` | FCF y calidad de resultados | `score_flujo()` |
| `Perfil Inversor IOL.txt`, `Instrumentos_37.txt` | Clasificación riesgo | `analisis/portafolio` |

## Microestructura / HFT (referencia, no usado en scanner diario)
`HIGH FREQUENCY TRADING*`, `High-frequency market-making*`, `market-microstructure*`, `lectures_201*`, `electronic-trading.txt`, `stochastic_processes.txt`, `dunbar-*`, `memoire_master*`, `spectral_theory*` — material de referencia para extensiones intradía.

## Earnings / Post-anuncio
Post-Earnings Announcement Drift (PEAD): Ball & Brown 1968, Bernard & Thomas 1989 — base para `scanner/earnings.py` (consistencia de sorpresas → deriva). No tiene txt propio; se cita en `scanner/README.md`.

## EPS cuantitativo
Fowler Newton cap.5 + Biondi cap.5 (DuPont, tendencia, comparación sectorial): base para `scanner/analisis_eps.py`. Ver `salud_fundamental.py` y tráiler del balance `income_stmt` en yfinance.
