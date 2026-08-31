# SCANNER INTERMARKET — Kit de señales continuas

Detector de régimen de mercado en tiempo casi-real que **unifica y recicla** los scripts
dispersos del repo (`intermarket_cycle_detector.py v3.0`, `noticias_portfolio.py`,
`ESTIMACIONES.txt`, `analisis_nvda_earnings.py`, `analisis/ejecutivo/noticias_ciclo.py`)
en un solo servicio ejecutable las 24h que emite señales accionables.

---

## Arquitectura

```
SCANNER_INTERMARKET/
├── scanner.py              ← MAIN. Orquesta todo, deduplica y emite señales
├── api_server.py           ← API HTTP stdlib (/health /estado /senales /scan) — cero deps extra
├── __init__.py             ← shim para importar el kit como paquete desde otra app
├── ejemplo_consumo.py      ← 3 modos de integración (HTTP / paquete / JSON plano)
├── config.json             ← Tickers, ratios, umbrales, intervalo de escaneo
├── requirements.txt        ← yfinance pandas numpy (única dependencia real)
├── .env                    ← keys (copiar de .env.example si se porta a otra máquina)
├── lib_mercado.py          ← Motor: 10 ratios Murphy + fase Pring/Murphy +
│                             spreads crédito (LQD/IEF, HYG/IEF) + VIX
├── lib_noticias.py         ← Google News RSS (ES/AR) + léxico sentimiento ES/EN
│                             + Finnhub general news (opcional, usa .env)
├── lib_eventos.py          ← Próximos earnings watchlist + beat-rate histórico
│                             (patrón ESTIMACIONES.txt), cacheado por día
├── estado_actual.json      ← SNAPSHOT consumible por bots/dashboards (se reescribe cada scan)
├── señales/                ← senales_YYYYMMDD.csv (append, solo señales NUEVAS)
├── logs/                   ← cache diario de eventos
├── metodologias/           ← papers y textos fuente (copiados curados)
│   ├── papers_trading/     ← Murphy Intermarket, stat-arb, algo trading, HFT,
│   │                          microestructura, ML, procesos estocásticos...
│   └── apis/               ← notas API: yfinance, BCRA, IOL, criptoya, ArgentinaDatos
└── scripts_reciclables/    ← copias intactas de los scripts originales que alimentan este kit
```

## Uso

```powershell
cd SCANNER_INTERMARKET

python scanner.py                  # un scan único y sale
python scanner.py --loop           # continuo, escanea cada intervalo_min (default 15)
python scanner.py --loop -i 30     # loop con intervalo propio de 30 min
python scanner.py --quiet          # sin banner, imprime solo señales nuevas
```

Para dejarlo corriendo permanente en Windows (Task Scheduler):
```
Programa:  python
Argumentos: C:\...\ANALISIS INVIU\SCANNER_INTERMARKET\scanner.py --loop --quiet
Iniciar en: C:\...\ANALISIS INVIU\SCANNER_INTERMARKET
```

### Consumir las señales desde otro programa
1. **`estado_actual.json`**: snapshot completo tras cada scan
   (`fase{num,name,conf}`, `ratios[]`, `credito{IG,HY}.pct`, `vix`,
   `noticias[].neto`, `eventos[]`, `senales_activas[]`)
2. **`señales/senales_*.csv`**: append con columnas
   `timestamp_utc, nivel(INFO|WARN|ALERTA), tipo(RATIO_CRUCE|FASE_CICLO|CREDITO|VIX|SENTIMIENTO|EVENTO), id, sentido, texto`
3. **Deduplicación integrada:** una misma señal no se re-emite mientras siga activa;
   solo entran al CSV cuando aparecen o cambian de sentido.

---

## Integración en otra app (portabilidad)

La carpeta `SCANNER_INTERMARKET/` es **autocontenida**: copiala completa a cualquier
proyecto/máquina con Python 3.10+, hacé `pip install -r requirements.txt` y listo.

### Opción A — Módulo Python (embebido en tu código)
```python
import sys
sys.path.insert(0, r"C:\ruta\donde\este\la\carpeta\padre")
from SCANNER_INTERMARKET import cargar_cfg, load_env, run_scan

load_env()                                  # lee .env del kit
estado = run_scan(cargar_cfg(), quiet=True) # un scan síncrono
print(estado["fase"]["name"], estado["senales_activas"])
```

### Opción B — Microservicio HTTP (otro proceso, otro lenguaje)
```powershell
python api_server.py --port 5010        # arranca API + scan automático inicial
```
| Endpoint | Devuelve |
|---|---|
| `GET /health` | `{ok, listo, fase, timestamp}` |
| `GET /estado` | snapshot JSON completo del último scan |
| `GET /senales?dias=3` | señales nuevas acumuladas N días |
| `POST /scan` | dispara scan inmediato en background |

Consumible desde Python, JS, C#, Excel (Power Query), n8n, etc.
Ver `ejemplo_consumo.py` para los tres modos listos para copiar.

### Opción C — Archivo plano
Leer `estado_actual.json` directamente cada X minutos; el CSV de `señales/`
funciona como log incremental.

**Checklist de portado:** ① carpeta completa → ② `pip install -r requirements.txt`
→ ③ crear `.env` desde `.env.example` con tu FINNHUB key (opcional: sin ella el
scanner funciona igual vía Google News RSS) → ④ ajustar `config.json`.

---

## Metodología (de dónde sale cada cosa)

| Módulo | Lógica | Fuente original / paper |
|---|---|---|
| 10 ratios intermarket | GSG/TLT, XLY/XLP, IWM/SPY, IYT/DIA, XLY/SPY, QQQ/SPY, GLD/USO, EFA/EEM, IEF/BIL, IVW/IVE | *Intermarket Analysis* (John Murphy) → `metodologias/papers_trading/intermarket-analysis-john-murphy (1).txt`; motor completo en `scripts_reciclables/intermarket_cycle_detector.py` |
| Fase del ciclo (6 fases) | Perfil b/s/c (bonos/stocks/commodities) + 3 ratios de confirmación; match por distancia mínima al perfil | Murphy + Martin Pring; implementación original del detector v3.0 |
| Rotación sectorial | Tabla comprar/vender por fase | Sam Stovall (S&P) + Murphy |
| Crédito corporativo | Percentiles históricos LQD/IEF (IG) e HYG/IEF (HY); ≥90% complacencia WARN, ≥95% ALERTA, ≤20% estrés | Detector v3.0 secciones 4.x |
| VIX | Umbrales fijos + z-score 252d | estándar |
| Sentimiento noticias | Léxico ES/EN ~130 términos sobre Google News RSS (hl=es-419, gl=AR); neto ≤ -4 dispara WARN | reciclado de `noticias_portfolio.py` |
| Eventos/catalizadores | Earnings próximos ≤10 días de la watchlist CEDEAR→ADR + beat-rate 8 trimestres | patrón `ESTIMACIONES.txt` / estudio NVDA |
| Referencias cuantitativas | Stat-arb, algo trading, HFT, microestructura | `papers_trading/lectures_*`, `high-frequency*`, `electronic-trading.txt` |
| APIs locales | BCRA, IOL, CryptoYa, ArgentinaDatos | `metodologias/apis/*.txt` |

## Configuración (`config.json`)

| Clave | Default | Significado |
|---|---|---|
| `intervalo_min` | 15 | minutos entre scans en modo `--loop` |
| `roc_umbral_pct` | 2.0 | % mínimo de cambio para llamar a una tendencia "up/down" |
| `main_period` | "2y" | historial del batch principal (ratios + MA50/200) |
| `credit_start` | 2016-01-01 | desde cuándo computar percentiles de crédito |
| `vix_warn / vix_alert` | 20 / 25 | umbrales de volatilidad |
| `eventos_dias` | 10 | ventana para anticipar earnings |
| `watchlist_portafolio` | tus 12 CEDEARs | tickers monitoreados para catalizadores |
| `ratios` | 10 definidos | agregá/editá entradas `{id,num,den,desc,fase_key}` libremente |

## Señales que emite

- **RATIO_CRUCE** (ALERTA si el ratio participa de la detección de fase): cruce nuevo de MA50/200 en cualquier ratio
- **FASE_CICLO** (ALERTA): cambio de fase Pring/Murphy, incluye lista comprar/vender
- **CREDITO IG/HY**: percentil ≥90 WARN · ≥95 ALERTA complacencia · ≤20 ALERTA estrés
- **VIX**: ≥20 WARN · ≥25 ALERTA
- **SENTIMIENTO**: neto de titulares ≤ -4
- **EVENTO**: earnings de tu portafolio a ≤10 días con EPS estimado y beat-rate

## Limitaciones conocidas

- Datos yfinance con delay (~15 min intradía); el scanner trabaja con cierres diarios → pensado para régimen, no para scalping
- Google News RSS puede tardar ~20-30s por query desde AR (está paralelizado)
- Los percentiles de crédito dependen del rango `credit_start`: cambiarlo recalibra todos los niveles
- No es asesoramiento financiero; es automatización de tu propia metodología
