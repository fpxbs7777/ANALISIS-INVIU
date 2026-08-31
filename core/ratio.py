# -*- coding: utf-8 -*-
"""core.ratio: ratios de fuerza relativa A/B y metricas por ventana.

Extraido de intermarket_parte2_3.py (ratio_stats), intermarket_parte5.py
(ratio_stats), intermarket_parte4_6_7.py (analyze) y generar_senales.py
(analyze_pair) -- unificados en un solo modulo sin duplicacion.
"""
import numpy as np
import pandas as pd

# Ventanas estandar (Parte 4 de la guia): tactico/swing/estructural
WINS = [50, 120, 200, 365]


def ratio_series(pa, pb):
    """Serie del ratio R(t)=A(t)/B(t) alineada por fechas comunes."""
    idx = pa.index.intersection(pb.index)
    return pd.Series(pa.loc[idx].values / pb.loc[idx].values, index=idx)


def window_stats(r, w):
    """Metricas del ratio sobre las ultimas w barras.

    Returns: last, z (desvios sobre la ventana), pct (percentil de la ultima),
             slope (pendiente normalizada en % de la ventana), high/low relativo.
    """
    if len(r) < w:
        return None
    rw = r.iloc[-w:]
    last = rw.iloc[-1]
    mu, sd = rw.mean(), rw.std()
    z = (last - mu) / sd if sd else 0.0
    pct = (rw < last).mean() * 100.0
    slope = np.polyfit(np.arange(w), rw.values, 1)[0] / (abs(rw.mean()) + 1e-12) * w * 100.0
    return dict(last=float(last), z=float(z), pct=float(pct), slope=float(slope),
                high=bool(last >= rw.max() * 0.999), low=bool(last <= rw.min() * 1.001))


def analyze_pair(pa, pb, wins=None):
    """Metricas completas A/B para cada ventana de `wins` (default WINS).

    Returns: (serie del ratio, dict {w: stats}) con corr/beta de retornos.
    """
    wins = wins or WINS
    r = ratio_series(pa, pb)
    out = {}
    ra = pa.pct_change().dropna()
    rb = pb.pct_change().dropna()
    for w in wins:
        s = window_stats(r, w)
        if s is None:
            continue
        ci = ra.index.intersection(rb.index)
        ca, cb = ra.loc[ci].iloc[-w:], rb.loc[ci].iloc[-w:]
        if len(ca) >= 30:
            s["corr"] = float(ca.corr(cb))
            varb = float(cb.var())
            s["beta"] = float(ca.cov(cb) / varb) if varb else 0.0
        else:
            s["corr"], s["beta"] = np.nan, np.nan
        out[w] = s
    return r, out


def ratio_stats(pa, pb, w=200):
    """Estilo Parte 3: ultimo valor del ratio + SMA50 y SMA200 (media de la ventana).

    Usado en intermarket_parte2_3.py y intermarket_parte5.py.
    """
    idx = pa.index.intersection(pb.index)
    r = pa.loc[idx] / pb.loc[idx]
    if len(r) < w:
        return None
    rw = r.iloc[-w:]
    last = rw.iloc[-1]
    m50 = rw.rolling(50).mean().iloc[-1]
    m200 = rw.mean()
    slope = np.polyfit(np.arange(w), rw.values, 1)[0] / (abs(last) + 1e-12) * w * 100.0
    z = (last - rw.mean()) / rw.std() if rw.std() else 0.0
    pct = (rw < last).mean() * 100.0
    return dict(last=float(last), m50=float(m50), m200=float(m200),
                slope=float(slope), z=float(z), pct=float(pct),
                above50=last > m50, above200=last > m200,
                signo="SUBENDO" if (last > m50 and last > m200 and slope > 0)
                      else ("bajando" if (last < m50 and last < m200 and slope < 0) else "mixto"))


def absolute_stats(pa, wins=None):
    """Metricas sobre una serie absoluta (nivel): DXY, TNX, VIX, etc.

    Mismo contrato que analyze_pair: dict {w: stats} con last, z, pct,
    slope; corr/beta NaN (no aplica). Se usa en ratios_madre y generar_senales.
    """
    wins = wins or WINS
    out = {}
    for w in wins:
        if len(pa) < w:
            continue
        rw = pa.iloc[-w:]
        last = rw.iloc[-1]
        z = (last - rw.mean()) / rw.std() if rw.std() else 0.0
        pct = (rw < last).mean() * 100.0
        slope = np.polyfit(np.arange(w), rw.values, 1)[0] / (abs(rw.mean()) + 1e-12) * w * 100.0
        out[w] = dict(last=float(last), z=float(z), pct=float(pct), slope=float(slope),
                      high=bool(last >= rw.max() * 0.999), low=bool(last <= rw.min() * 1.001),
                      corr=float("nan"), beta=float("nan"))
    return out