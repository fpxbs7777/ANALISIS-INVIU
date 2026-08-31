# -*- coding: utf-8 -*-
"""Generador de Dashboard HTML de Sectores Intermarket.

Descarga precios, calcula metricas (beta, alpha, R2, rangos normalizados,
correlaciones) y genera un HTML autocontenido con Chart.js.

Uso:
    python generar_dashboard_sectores.py
    python generar_dashboard_sectores.py --periodo 2y
    python generar_dashboard_sectores.py --out dashboard_sectores.html
"""
import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data import load_many

# ETFs sectoriales + macro
SECTORES = {
    "XLE": "Energia", "XLK": "Tecnologia", "XLI": "Industriales",
    "XLP": "Defensiva", "XLF": "Financieros", "XLY": "Ciclico",
    "XLV": "Salud", "XLC": "Comunicacion", "XLB": "Materiales",
    "XLU": "Utilidades", "XLRE": "Bienes Raices",
}
MACRO = {"GLD": "Oro", "TLT": "Bonos", "QQQ": "Nasdaq", "IWM": "SmallCaps"}
BENCH = "SPY"

# Colores para cada sector (CSS hex)
COLORES = {
    "XLE": "#e74c3c", "XLK": "#3498db", "XLI": "#2ecc71", "XLP": "#9b59b6",
    "XLF": "#f39c12", "XLY": "#1abc9c", "XLV": "#e67e22", "XLC": "#e91e63",
    "XLB": "#00bcd4", "XLU": "#8bc34a", "XLRE": "#795548",
    "GLD": "#ffd700", "TLT": "#607d8b", "QQQ": "#00e5ff", "IWM": "#ff9800",
    "SPY": "#212121",
}


def calcular_metricas_precios(data, ventana_corr=60):
    """Calcula todas las metricas necesarias para el dashboard."""
    all_tickers = list(SECTORES.keys()) + list(MACRO.keys()) + [BENCH]
    precios = pd.DataFrame({tk: s for tk, s in data.items() if tk in all_tickers and s is not None})

    # Retornos diarios
    retornos = precios.pct_change().dropna()

    # Normalizados (rebase 100)
    normalizados = (precios / precios.iloc[0]) * 100

    # Rango normalizado (min-max) por ventana de 126d (6M)
    ventana = min(126, len(precios) - 1)
    rango_data = {}
    for tk in precios.columns:
        s = precios[tk].dropna().iloc[-ventana:]
        if len(s) < 20:
            continue
        mn, mx = float(s.min()), float(s.max())
        actual = float(s.iloc[-1])
        rango = mx - mn
        pct_dentro = (actual - mn) / rango * 100 if rango > 0 else 50
        gan_max = (mx - actual) / actual * 100 if actual > 0 else 0
        per_min = (actual - mn) / actual * 100 if actual > 0 else 0
        rango_data[tk] = {
            "pct_dentro": round(pct_dentro, 1),
            "gan_max": round(gan_max, 2),
            "perd_min": round(per_min, 2),
            "min": round(mn, 2), "max": round(mx, 2),
            "actual": round(actual, 2),
        }

    # Beta, Alpha, R2 entre todos los pares
    regression = {}
    tickers_reg = list(SECTORES.keys())
    for tk_x in tickers_reg:
        for tk_y in tickers_reg:
            if tk_x == tk_y:
                continue
            if tk_x not in retornos.columns or tk_y not in retornos.columns:
                continue
            rx = retornos[tk_x].dropna()
            ry = retornos[tk_y].dropna()
            idx = rx.index.intersection(ry.index)
            if len(idx) < 60:
                continue
            x, y = rx.loc[idx].values, ry.loc[idx].values
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            regression[(tk_x, tk_y)] = {
                "beta": round(slope, 4),
                "alpha": round(intercept * 252 * 100, 4),  # anualizado en %
                "r2": round(r_value ** 2, 4),
                "corr": round(r_value, 4),
                "p_value": round(p_value, 6),
            }

    # Correlacion movil 60d
    corr_movel = {}
    for tk_x in tickers_reg:
        for tk_y in tickers_reg:
            if tk_x >= tk_y:
                continue
            if tk_x not in retornos.columns or tk_y not in retornos.columns:
                continue
            corrserie = retornos[tk_x].rolling(ventana_corr).corr(retornos[tk_y]).dropna()
            if len(corrserie) > 0:
                corr_movel[(tk_x, tk_y)] = {
                    "serie": [round(v, 3) for v in corrserie.values[-60:]],
                    "fechas": [d.strftime("%Y-%m-%d") for d in corrserie.index[-60:]],
                    "actual": round(float(corrserie.iloc[-1]), 3),
                }

    # Fechas para el eje X
    fechas = [d.strftime("%Y-%m-%d") for d in normalizados.index[-252:]]

    # Series normalizadas (ultimos 252 dias)
    series_norm = {}
    for tk in normalizados.columns:
        s = normalizados[tk].dropna().iloc[-252:]
        series_norm[tk] = [round(v, 2) for v in s.values]

    return {
        "fechas": fechas,
        "series_norm": series_norm,
        "rango": rango_data,
        "regression": {("%s/%s" % k): v for k, v in regression.items()},
        "corr_movel": {("%s/%s" % k): v for k, v in corr_movel.items()},
        "sectores": SECTORES,
        "macro": MACRO,
        "colores": COLORES,
        "fecha_gen": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def generar_html(metricas):
    """Genera el HTML autocontenido con Chart.js."""
    data_json = json.dumps(metricas, ensure_ascii=False)

    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Intermarket Sector Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
  .header { background: linear-gradient(135deg, #1e293b, #334155); padding: 20px 30px; border-bottom: 2px solid #3b82f6; }
  .header h1 { font-size: 1.5rem; color: #60a5fa; }
  .header .sub { color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }
  .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
  .section { background: #1e293b; border-radius: 12px; margin-bottom: 20px; padding: 20px; border: 1px solid #334155; }
  .section h2 { color: #60a5fa; font-size: 1.1rem; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
  .row { display: flex; gap: 20px; flex-wrap: wrap; }
  .col-full { flex: 1 1 100%; }
  .col-half { flex: 1 1 45%; min-width: 300px; }
  canvas { max-height: 400px; }
  select { background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 8px 12px; border-radius: 6px; font-size: 0.9rem; }
  select:focus { outline: none; border-color: #3b82f6; }

  /* Gauges */
  .gauges { display: flex; flex-wrap: wrap; gap: 12px; }
  .gauge { flex: 1 1 100px; min-width: 100px; background: #0f172a; border-radius: 8px; padding: 10px; text-align: center; }
  .gauge .name { font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; }
  .gauge .bar-bg { height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin: 6px 0; }
  .gauge .bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
  .gauge .pct { font-size: 1.1rem; font-weight: bold; }
  .gauge .gan { font-size: 0.7rem; margin-top: 2px; }
  .gan-pos { color: #4ade80; }
  .gan-neg { color: #f87171; }

  /* Prediction table */
  .pred-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
  .pred-table th, .pred-table td { padding: 6px 8px; border: 1px solid #334155; text-align: center; }
  .pred-table th { background: #334155; color: #60a5fa; position: sticky; top: 0; }
  .pred-table .pos { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
  .pred-table .neg { background: rgba(248, 113, 113, 0.15); color: #f87171; }
  .pred-table .neu { color: #94a3b8; }

  /* Heatmap */
  .heatmap-wrap { overflow-x: auto; }
  .heatmap { border-collapse: collapse; font-size: 0.7rem; }
  .heatmap th, .heatmap td { padding: 4px 6px; text-align: center; min-width: 50px; }
  .heatmap th { background: #334155; color: #60a5fa; position: sticky; top: 0; }

  /* Range bars */
  .range-row { display: flex; align-items: center; margin-bottom: 8px; gap: 10px; }
  .range-label { width: 60px; font-size: 0.75rem; color: #94a3b8; text-align: right; }
  .range-track { flex: 1; height: 20px; background: #0f172a; border-radius: 4px; position: relative; overflow: visible; }
  .range-minmax { position: absolute; top: 0; height: 100%; border-radius: 4px; opacity: 0.3; }
  .range-marker { position: absolute; top: -2px; width: 4px; height: 24px; border-radius: 2px; transform: translateX(-2px); }
  .range-text { width: 80px; font-size: 0.75rem; }
</style>
</head>
<body>

<div class="header">
  <h1>Intermarket Sector Dashboard — Murphy Cycle</h1>
  <div class="sub">Generado: """ + metricas["fecha_gen"] + """ | Sectores: """ + str(len(metricas["sectores"])) + """ | Datos: 12 meses</div>
</div>

<div class="container">

  <!-- [1] TRAYECTORIA NORMALIZADA -->
  <div class="section">
    <h2>[1] Trayectoria Normalizada (Base 100 = inicio del periodo)</h2>
    <canvas id="chartNorm"></canvas>
  </div>

  <!-- [2] GAUGES DE RANGO -->
  <div class="section">
    <h2>[2] Rango Normalizado — Cuánto recorrido queda (6M)</h2>
    <div id="gaugesContainer" class="gauges"></div>
  </div>

  <!-- [3] SCATTER DE REGRESION -->
  <div class="section">
    <h2>[3] Matriz de Regresión — ¿Cómo impacta cada sector a los demás?</h2>
    <div style="margin-bottom:10px;">
      <label style="color:#94a3b8;font-size:0.85rem;">Sector en eje X: </label>
      <select id="selRegX" onchange="updateRegression()"></select>
      <label style="color:#94a3b8;font-size:0.85rem;margin-left:20px;">Sector en eje Y: </label>
      <select id="selRegY" onchange="updateRegression()"></select>
    </div>
    <div class="row">
      <div class="col-half"><canvas id="chartScatter"></canvas></div>
      <div class="col-half" id="regInfo" style="display:flex;flex-direction:column;justify-content:center;font-size:0.9rem;"></div>
    </div>
  </div>

  <!-- [4] TABLA DE PREDICCION -->
  <div class="section">
    <h2>[4] Tabla de Predicción — ¿Qué pasa con los demás si uno sube 1%?</h2>
    <div style="overflow-x:auto;">
      <table id="predTable" class="pred-table"></table>
    </div>
  </div>

  <!-- [5] HEATMAP CORRELACION -->
  <div class="section">
    <h2>[5] Heatmap de Correlación Móvil (60d)</h2>
    <div class="heatmap-wrap">
      <table id="heatmapTable" class="heatmap"></table>
    </div>
  </div>

  <!-- [6] BARRAS DE RANGO -->
  <div class="section">
    <h2>[6] Posición en el Rango — Min ──●── Max (6M)</h2>
    <div id="rangeBars"></div>
  </div>

</div>

<script>
const DATA = """ + data_json + """;
const SECT = DATA.sectores;
const MAC = DATA.macro;
const ALL_TICKERS = {...SECT, ...MAC, "SPY": "Benchmark"};
const COL = DATA.colores;

// [1] TRAYECTORIA NORMALIZADA
(function() {
  const ctx = document.getElementById('chartNorm').getContext('2d');
  const datasets = [];
  for (const [tk, vals] of Object.entries(DATA.series_norm)) {
    datasets.push({
      label: tk + ' (' + (ALL_TICKERS[tk]||tk) + ')',
      data: vals,
      borderColor: COL[tk] || '#888',
      backgroundColor: 'transparent',
      borderWidth: tk === 'SPY' ? 3 : 1.5,
      pointRadius: 0,
      tension: 0.1,
    });
  }
  new Chart(ctx, {
    type: 'line',
    data: { labels: DATA.fechas, datasets },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { size: 10 }, usePointStyle: true, pointStyle: 'line' } },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: { ticks: { color: '#64748b', maxTicksLimit: 12, font: { size: 9 } }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#64748b', font: { size: 9 } }, grid: { color: '#1e293b' } },
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
    }
  });
})();

// [2] GAUGES
(function() {
  const c = document.getElementById('gaugesContainer');
  for (const [tk, info] of Object.entries(DATA.rango)) {
    const g = document.createElement('div');
    g.className = 'gauge';
    const color = info.pct_dentro < 30 ? '#4ade80' : info.pct_dentro < 70 ? '#facc15' : '#f87171';
    const ganClass = info.gan_max > 0 ? 'gan-pos' : 'gan-neg';
    g.innerHTML = '<div class="name">' + tk + ' (' + (ALL_TICKERS[tk]||tk) + ')</div>'
      + '<div class="pct" style="color:' + color + '">' + info.pct_dentro.toFixed(0) + '%</div>'
      + '<div class="bar-bg"><div class="bar-fill" style="width:' + info.pct_dentro + '%;background:' + color + '"></div></div>'
      + '<div class="gan ' + ganClass + '">' + (info.gan_max>0?'+':'') + info.gan_max.toFixed(1) + '% al max</div>';
    c.appendChild(g);
  }
})();

// [3] REGRESION
let scatterChart = null;
function updateRegression() {
  const xTk = document.getElementById('selRegX').value;
  const yTk = document.getElementById('selRegY').value;
  const key = xTk + '/' + yTk;
  const reg = DATA.regression[key];
  if (!reg) return;

  const xVals = DATA.series_norm[xTk] || [];
  const yVals = DATA.series_norm[yTk] || [];
  const points = [];
  for (let i = 0; i < Math.min(xVals.length, yVals.length); i++) {
    points.push({x: xVals[i], y: yVals[i]});
  }
  // Linea de regresion
  const xMin = Math.min(...xVals), xMax = Math.max(...xVals);
  const linePoints = [
    {x: xMin, y: reg.alpha/100*252 + reg.beta * xMin},
    {x: xMax, y: reg.alpha/100*252 + reg.beta * xMax},
  ];

  if (scatterChart) scatterChart.destroy();
  const ctx = document.getElementById('chartScatter').getContext('2d');
  scatterChart = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        { label: xTk + ' vs ' + yTk, data: points, backgroundColor: COL[yTk] || '#60a5fa', pointRadius: 2 },
        { label: 'Regresión', data: linePoints, type: 'line', borderColor: '#f59e0b', borderWidth: 2, pointRadius: 0 },
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#94a3b8' } },
        title: { display: true, text: yTk + ' = ' + reg.alpha.toFixed(2) + '% + ' + reg.beta.toFixed(3) + '·' + xTk + '  R²=' + reg.r2.toFixed(3), color: '#e2e8f0' },
      },
      scales: {
        x: { title: { display: true, text: xTk + ' (normalizado)', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
        y: { title: { display: true, text: yTk + ' (normalizado)', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
      }
    }
  });

  const info = document.getElementById('regInfo');
  const direction = reg.beta > 0 ? 'sube' : 'cae';
  const strength = reg.r2 > 0.3 ? 'fuerte' : reg.r2 > 0.1 ? 'moderada' : 'débil';
  info.innerHTML = '<div style="padding:15px;background:#0f172a;border-radius:8px;">'
    + '<div style="font-size:1.1rem;color:#60a5fa;margin-bottom:10px;">Resultado de Regresión</div>'
    + '<div style="margin-bottom:6px;"><b>EC:</b> ' + yTk + ' = ' + reg.alpha.toFixed(2) + '% + ' + reg.beta.toFixed(4) + '·' + xTk + '</div>'
    + '<div style="margin-bottom:6px;"><b>Beta:</b> ' + reg.beta.toFixed(4) + ' → Si ' + xTk + ' sube 1%, ' + yTk + ' ' + direction + ' <b>' + (reg.beta*1).toFixed(3) + '%</b></div>'
    + '<div style="margin-bottom:6px;"><b>Alpha anual:</b> ' + reg.alpha.toFixed(2) + '% (exceso no explicado por ' + xTk + ')</div>'
    + '<div style="margin-bottom:6px;"><b>R²:</b> ' + reg.r2.toFixed(4) + ' — Correlación ' + strength + ' (' + (reg.r2*100).toFixed(1) + '% de varianza compartida)</div>'
    + '<div style="margin-bottom:6px;"><b>Correlación:</b> ' + reg.corr.toFixed(4) + '</div>'
    + '<div style="margin-top:12px;padding:10px;background:#1e293b;border-radius:6px;font-size:0.85rem;">'
    + '💡 <b>Interpretación:</b> Por cada 1% que sube ' + xTk + ', se espera que ' + yTk + ' '
    + (reg.beta > 0 ? 'suba ' + (reg.beta).toFixed(3) + '%' : 'caiga ' + Math.abs(reg.beta).toFixed(3) + '%')
    + '. La confianza en esta relación es ' + strength + ' (R²=' + reg.r2.toFixed(3) + ').</div>'
    + '</div>';
}

// Poblar selects
(function() {
  const selX = document.getElementById('selRegX');
  const selY = document.getElementById('selRegY');
  const sects = Object.keys(SECT);
  sects.forEach(tk => {
    selX.innerHTML += '<option value="' + tk + '">' + tk + ' (' + SECT[tk] + ')</option>';
    selY.innerHTML += '<option value="' + tk + '">' + tk + ' (' + SECT[tk] + ')</option>';
  });
  selY.selectedIndex = 1;
  updateRegression();
})();

// [4] TABLA PREDICCION
(function() {
  const tbl = document.getElementById('predTable');
  const sects = Object.keys(SECT);
  let html = '<tr><th>Si ↑1% →</th>';
  sects.forEach(tk => html += '<th>' + tk + '</th>');
  html += '</tr>';
  sects.forEach(tk_row => {
    html += '<tr><th>' + tk_row + '</th>';
    sects.forEach(tk_col => {
      if (tk_row === tk_col) {
        html += '<td style="background:#334155;">—</td>';
      } else {
        const key = tk_row + '/' + tk_col;
        const reg = DATA.regression[key];
        if (reg) {
          const val = reg.beta;
          const cls = val > 0.01 ? 'pos' : val < -0.01 ? 'neg' : 'neu';
          const arrow = val > 0.01 ? '↑' : val < -0.01 ? '↓' : '→';
          html += '<td class="' + cls + '">' + (val > 0 ? '+' : '') + val.toFixed(3) + '% ' + arrow + '<br><span style="font-size:0.65rem;opacity:0.7">R²=' + reg.r2.toFixed(2) + '</span></td>';
        } else {
          html += '<td class="neu">N/D</td>';
        }
      }
    });
    html += '</tr>';
  });
  tbl.innerHTML = html;
})();

// [5] HEATMAP
(function() {
  const tbl = document.getElementById('heatmapTable');
  const sects = Object.keys(SECT);
  let html = '<tr><th></th>';
  sects.forEach(tk => html += '<th>' + tk + '</th>');
  html += '</tr>';
  sects.forEach(r => {
    html += '<tr><th>' + r + '</th>';
    sects.forEach(c => {
      if (r === c) {
        html += '<td style="background:#3b82f6;color:#fff;">1.00</td>';
      } else {
        // Buscar en regression o usar promo
        let corr = 0;
        const key1 = r + '/' + c;
        const key2 = c + '/' + r;
        if (DATA.regression[key1]) corr = DATA.regression[key1].corr;
        else if (DATA.regression[key2]) corr = DATA.regression[key2].corr;

        const intensity = Math.abs(corr);
        let bg;
        if (corr > 0) bg = 'rgba(59,130,246,' + (intensity * 0.7) + ')';
        else bg = 'rgba(239,68,68,' + (intensity * 0.7) + ')';
        html += '<td style="background:' + bg + ';color:#e2e8f0;">' + corr.toFixed(2) + '</td>';
      }
    });
    html += '</tr>';
  });
  tbl.innerHTML = html;
})();

// [6] BARRAS DE RANGO
(function() {
  const c = document.getElementById('rangeBars');
  for (const [tk, info] of Object.entries(DATA.rango)) {
    const color = info.pct_dentro < 30 ? '#4ade80' : info.pct_dentro < 70 ? '#facc15' : '#f87171';
    const ganClass = info.gan_max > 0 ? 'gan-pos' : 'gan-neg';
    c.innerHTML += '<div class="range-row">'
      + '<div class="range-label">' + tk + '</div>'
      + '<div class="range-track">'
      + '  <div class="range-minmax" style="left:0;width:100%;background:linear-gradient(90deg,#4ade80,#facc15,#f87171);"></div>'
      + '  <div class="range-marker" style="left:' + info.pct_dentro + '%;background:' + color + ';"></div>'
      + '</div>'
      + '<div class="range-text ' + ganClass + '">' + (info.gan_max > 0 ? '+' : '') + info.gan_max.toFixed(1) + '% al max</div>'
      + '</div>';
  }
})();
</script>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Dashboard HTML de sectores intermarket")
    parser.add_argument("--periodo", default="1y", help="Periodo de datos (1y, 2y)")
    parser.add_argument("--out", default="dashboard_sectores.html", help="Archivo HTML de salida")
    parser.add_argument("--json", default=None, help="Guardar datos como JSON tambien")
    args = parser.parse_args()

    all_tickers = list(SECTORES.keys()) + list(MACRO.keys()) + [BENCH]
    print("=" * 70)
    print("GENERADOR DE DASHBOARD DE SECTORES INTERMARKET")
    print("=" * 70)

    print("\n[1/3] Descargando precios (%s)..." % args.periodo)
    data = load_many(all_tickers, period=args.periodo)
    print("  Descargados: %d / %d" % (len(data), len(all_tickers)))

    print("\n[2/3] Calculando metricas (beta, alpha, R2, rangos, correlaciones)...")
    metricas = calcular_metricas_precios(data)
    print("  Sectores: %d" % len(metricas["sectores"]))
    print("  Pares de regresion: %d" % len(metricas["regression"]))
    print("  Pares de correlacion: %d" % len(metricas["corr_movel"]))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(metricas, f, ensure_ascii=False, indent=2)
        print("  JSON: %s" % args.json)

    print("\n[3/3] Generando HTML...")
    html = generar_html(metricas)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("  Dashboard: %s" % args.out)
    print("\n  Abrilo en el navegador para ver los graficos interactivos.")
    print("=" * 70)


if __name__ == "__main__":
    main()
