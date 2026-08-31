# Scripts legado — qué se recicla y adónde

Copias intactas con fines de referencia. El código vivo está en `scanner\` y `core/`/`analisis/`.

| Archivo legado | Qué aporta | ¿Reciclado? → destino |
|---|---|---|
| `screener_sectores_fav.py` | Fórmula score 0.45·r6m+0.35·r3m+0.20·tendencia; métricas r1m/r3m/r6m vs SMA | Sí → `scanner/screener_dia.py` |
| `rotacion_ciclo_empresas.py` | Pipeline sectores→industrias→screener Yahoo→ranking→comparación 5 bloques | Sí → base de `scanner/screener_dia.py` + parte de `analisis_eps/earnings` |
| `comparar_mu_amd.py` / `comparador.py` | Framework 5 bloques (cuant/fund/téc/noticias) Distribution+CAPM | Sí → `scanner/analisis_eps.py` (parte fund) y `screener_dia` detalle |
| `analisis_sector_industria.py` | Cache pickle incremental, AssetAnalyzer, matriz correlaciones | Referencia `core/data.py` + `analisis/portafolio/constructor.descargar_precios` |
| `sector_e_industria.py` / `sector e industria.py` | Cache CEDEARs, normalización .BA/.SA | Referencia `scanner/screener_dia` mapa CEDEAR |
| `obtener_sectores_industrias.py` | Agrupa por sector→industria desde yfinance | Integrado en `screener_dia` |
| `descargar series de activos a json.py` | SECTOR_TICKERS_EN/ES, descarga incremental batch 50 + edad cache | Referencia `core/data.load_many` |
| `yfinance analisis/*` (5 scripts) | Screener Yahoo EquityQuery, obtención industries por sector | Sí → `scanner/screener_dia.screener_industria` (fix variantes em-dash) |
| `intermarket_cycle_detector.py` | SECTOR_ROTATION por fase Pring + Stovall ranking | Sí → `scanner/fase_ciclo.py` (texto de referencia para fase) + `alertas_macro.py` |
| `backtest_entrada_*.py` (9) | Tests puntuales de tesis (CCJ, FCX, MU, URA...) | No — se mantienen solo como casos de estudio |
| `pe_percentil_10y.py`, `variables bcra.py` | P/E histórico, BCRA | No — utilidades puntuales |

## Estructura `yfinance analisis` copiada
- `obtener_tickers_sector_industria.py` → `get_tickers_by_industry()` paginado
- `sectores_industrias.py` → `yf.Sector(key).industries` por market weight
- `tickers_buenos_aires_sectores.py` → lista manual BCBA
