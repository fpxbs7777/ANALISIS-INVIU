# -*- coding: utf-8 -*-
"""core.corr: correlaciones de retornos con delay (usadas en Parte 1 y Cap.1)."""
import numpy as np


def corr_lag(a, b, max_lag=21, min_n=120):
    """Correlacion de retornos diarios con 'a' desplazado hasta max_lag dias.

    Args:
        a: Serie de precios del mercado que queres adelantar (p.ej. DXY).
        b: Serie de precios del mercado que responde.
        max_lag: hasta cuantos dias probar el adelanto.
        min_n: minimo de observaciones solapadas para aceptar la corr.

    Returns:
        dict {lag: corr}. lag=0 es contemp raneo; lag=14 => a vista 14 dias antes.
    """
    ra = a.pct_change().dropna()
    rb = b.pct_change().dropna()
    out = {}
    for lag in range(max_lag + 1):
        ax = ra.shift(-lag) if lag else ra
        idx = ax.index.intersection(rb.index)
        if len(idx) < min_n:
            continue
        out[lag] = float(ax.loc[idx].corr(rb.loc[idx]))
    return out


def best_lag(corr):
    """Devuelve (lag, |corr|) del lag con correlacion mas fuerte en valor absoluto."""
    if not corr:
        return None, None
    best = max(corr.items(), key=lambda kv: abs(kv[1]))
    return best[0], best[1]


def rolling_corr(a, b, window=120):
    """Correlacion movil de retornos para graficar evolucion del vinculo."""
    ra = a.pct_change().dropna()
    rb = b.pct_change().dropna()
    idx = ra.index.intersection(rb.index)
    ra, rb = ra.loc[idx], rb.loc[idx]
    return ra.rolling(window).corr(rb)


def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1])