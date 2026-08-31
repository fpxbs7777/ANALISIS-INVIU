# Scanner Intermarket — Señales en tiempo (casi) real

> **Una carpeta, un comando, todas las señales.** Este scanner consolida la lógica dispersa del proyecto (`core/`, `analisis/libro`, `analisis/ejecutivo`, `clientes/`) en un paquete autónomo que corre cada 30 min en horario de mercado US y envía solo los cambios por Telegram.

## Arquitectura

```
scanner/
  config.json              ← token/chat_id, frecuencia, umbrales
  run_scanner.py           ← orquestador (loop + --once)
  senales_nucleo.py        ← 28 señales A/B (analisis.ejecutivo.senales.TABLA)
  fase_ciclo.py            ← Pring cap12 + liderazgo 200d cap13 (Murphy)
  alertas_macro.py         ← curva invertida, shock 1994, divergencias (caps 2/3/7)
  screener_dia.py          ← sectores líderes → industrias (yfinance) → ranking fuerza
  earnings.py              ← calendario + acierto/sorp históricos (earnings_dates)
  analisis_eps.py          ← EPS básico/diluido + tendencia + rank entre pares del mismo
  │                          sector/industria (unificado_completo - copia.json)
  notificador.py           ← Telegram sendMessage con dedup (estado/ultimo_envio.json)
  estado/                  ← senales_previo.csv, historico, caches earnings/eps
  logs/                    ← scanner_YYYYMMDD.log
  instalar_tarea.ps1       ← instala tarea Windows al inicio de sesión
```

**Importa, no duplica:** todos los módulos reutilizan `core/data`, `core/ratio`, `core/senales`, `analisis/libro`, `analisis/portafolio/constructor` ya probados por `run_all.py`.

## Señales que monitorea

### 1. Las 28 señales A/B (`TABLA` de `analisis.ejecutivo.senales`)

| Familia | Ejemplos | Ventanas |
|---|---|---|
| Macro (M) | DXY, TNX, TLT/IEF, VIX | 50/120/365 |
| Activos (AA) | SPY/TLT, SPY/GLD, SPY/EEM |  |
| Sectoriales (S) | XLE/SPY, XLY/SPY, XLC/SPY, XLB/SPY, XLK/SPY | regla de oro (50=120=365) |
| Industriales (I) | SMH/XLK, LIT/XLB, URA/XLE, URA/XLU | |
| Tickers (A) | NVDA/SMH … GOOGL/XLC | |
| Locales (LOC) | PAMP/MERV, ARGT/EEM, MERV/EEM | |

Cada señal calcula `z`, `pct`, `pendiente`, `corr`, `beta` en 4 ventanas (`core/ratio.window_stats`) y clasifica:

- `ALCISTA CONFIRMADA` / `BAJISTA CONFIRMADA` (las 3 ventanas coinciden)
- `CAMBIO DE REGIMEN` (50=120 ≠ 365) — anticipa giro
- `NEUTRO`

`accion()` traduce a `MANTENER/ACUMULAR`, `ROTAR/NO COMPRAR`, `SOBRECOMPRADO: NO PERSEGUIR`, `POSIBLE MEAN-REVERSION` (z120±1.5 y pct extremo).

### 2. Fase Pring + liderazgo sectorial (cap12/cap13)

- **Etapa 1-6**: `cap12.etapa_pring` ("Stage 4 bonos caen, acciones/comm suben" = actual 2026-08-26).
- **Ranking**: `cap13.liderazgo_sectorial_200d` = pendiente ratio ETF/SPY en 200 días → top-3 sectores beneficiados (hoy XLE/XLK/XLI).

### 3. Alertas macro

`curva_invertida` (cap7), `shock_1994` (cap3), `divergencia_bonos_comm` (cap2). Se reportan como 🟢/🔴 por ciclo.

### 4. Screener de empresas (1× día, tras cierre US)

Para los 3 sectores líderes → top-4 industrias por `market weight` (`yf.Sector`) → screener Yahoo por industria (`EquityQuery`) limitado a NYSE/NASDAQ (`NMS/NGM/NYQ/ASE`), `mcap ≥ 5B` → ranking por `score = 0.45·r6m_ex + 0.35·r3m_ex + 0.20·tendencia` (fórmula de `screener_sectores_fav.py`) + `regla_oro` vs ETF + R².

### 5. Earnings (calendario + historial)

Por empresa del universo (finalistas + portafolio Inviu + watchlist):

- **Próxima fecha + hora ET** → 🌅 BMO / 🌙 AMC
- **acierto%** = beats 8T (Reported ≥ Estimate) · **sorp%** = sorpresa media — columnas `Surprise(%)` de `earnings_dates`
- Semáforo 🟩 ≥75% · ⚪ ≥50% · 🟥 <50% — fundamento PEAD (Ball & Brown 1968)

Se envía resumen de próximos 7 días y alerta "HOY reporta".

### 6. EPS cuantitativo

```
EPS = (beneficio neto − dividendos preferentes) / acciones ordinarias
EPS diluido = incluye opciones/bonos convertibles  → fila 'Diluted EPS'
```

Componentes (datos: `income_stmt`/`quarterly_income_stmt` + `info.trailingEps`):

- **Tendencia temporal**: serie trimestral 8T + anual 4A → Δ% YoY y CAGR
- **Comparación sectorial**: pares del *mismo sector+industria* según `unificado_completo - copia.json` (patrón `motor/02_validacion_r2` unificado, deduplicado ES/EN, filtrado a tickers US puros) → rank percentil del EPS diluido TTM entre pares
- **Ajustes por calidad**: se usa EPS diluido como estándar conservador; la normalización total no está disponible en fuente gratuita — limitación documentada (Fowler Newton cap.5, Biondi cap.5)

## Configuración Telegram

1. El bot ya creado es `@fpxbs777_bot` — token en `config.json` (cambiar con `/revoke` en @BotFather si se expone).
2. Tu `chat_id` ya está en `config.json` (`8179198652`).
3. Test:

```powershell
python scanner/notificador.py --test
python scanner/run_scanner.py --once --force   # fuerza envío aunque no haya cambios
```

Si falla con `400 Bad Request`, el notificador reintenta sin Markdown automáticamente y trunca a 4000 chars.

## Uso

```powershell
# una corrida completa y salir (recomendado para probar)
python scanner/run_scanner.py --once

# forzar aunque no haya cambios (útil tras cambiar config)
python scanner/run_scanner.py --once --force

# loop intraday (cada 30 min en horario US; duerme fuera de horario)
python scanner/run_scanner.py

# modo JSON fallback (sin recalcular MurphyDaily, usa contexto_actual.json)
python scanner/run_scanner.py --once --json
```

**Tarea programada Windows (al iniciar sesión, se reinicia solo):**

```powershell
powershell -ExecutionPolicy Bypass -File scanner\instalar_tarea.ps1
# desinstalar: Unregister-ScheduledTask -TaskName IntermarketScanner
```

Logs en `scanner/logs/scanner_YYYYMMDD.log`, histórico en `scanner/estado/senales_historico.csv`.

## Biblioteca

Ver `biblioteca/metodologias/INDICE.md` (qué txt fundamenta cada módulo) y `biblioteca/scripts_legado/README.md` (mapa de reciclaje).

> **Educativo — no recomendación.** Fuentes: Yahoo Finance vía yfinance; metodologías citadas arriba. Validar siempre antes de operar.
