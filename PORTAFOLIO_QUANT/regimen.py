# -*- coding: utf-8 -*-
"""Regimen: motor de analogos empirico.

Vector de regimen diario [vol_pctil, vix_z, fase_num, ig_pctil, hy_pctil, roc_XLY_XLP].
Busca ventanas historicas de distancia minima y evalua que pool/tipo gano despues.
Si las condiciones se repitieron >= umbral, emite senal con win-rate por horizonte.
"""
import numpy as np
import pandas as pd

try:
    import scipy.stats as st
except Exception:
    st = None


def _zscore(s, lb=252):
    m = s.rolling(lb).mean()
    sd = s.rolling(lb).std()
    return (s - m) / sd


def construir_regimen(close_df, estados_fase_por_fecha=None):
    rets = np.log(close_df / close_df.shift(1))
    # 1 vol del mercado (SPY rolling 21d)
    spy_ret = rets["SPY"] if "SPY" in rets.columns else rets.iloc[:, 0]
    vol21 = spy_ret.rolling(21).std() * (252 ** 0.5)
    vol_pctil = vol21.rolling(500).apply(
        lambda x: (x <= x.iloc[-1]).mean() * 100, raw=False)
    # 2 VIX z si existe
    vix_z = pd.Series(index=close_df.index, dtype=float)
    if "^VIX" in close_df.columns:
        vix_z = _zscore(close_df["^VIX"], 252)
    elif "VIX" in close_df.columns:
        vix_z = _zscore(close_df["VIX"], 252)
    # 3 fase historica simplificada: proxy por tendencias b/s/c si no hay estados
    #    Si tenemos estados por fecha del kit, usarlos; sino aproximar con SMA senal
    fase_num = pd.Series(index=close_df.index, dtype=float)
    if estados_fase_por_fecha:
        for d, v in estados_fase_por_fecha.items():
            try:
                fase_num.loc[d] = float(v)
            except Exception:
                pass
        fase_num = fase_num.ffill()
    else:
        # proxy rapido: fase 3 (Late Expansion) cuando SPY>TMI y commodities>TMI
        fase_num[:] = 3.0
    # 4 credito percentiles si existen LQD/IEF/HYG
    ig_pctil = pd.Series(index=close_df.index, dtype=float)
    hy_pctil = pd.Series(index=close_df.index, dtype=float)
    if "LQD" in close_df.columns and "IEF" in close_df.columns:
        proxy = (close_df["LQD"] / close_df["IEF"]).dropna()
        ig_pctil.loc[proxy.index] = proxy.expanding().apply(
            lambda x: (x <= x.iloc[-1]).mean() * 100, raw=False)
    if "HYG" in close_df.columns and "IEF" in close_df.columns:
        proxy = (close_df["HYG"] / close_df["IEF"]).dropna()
        hy_pctil.loc[proxy.index] = proxy.expanding().apply(
            lambda x: (x <= x.iloc[-1]).mean() * 100, raw=False)
    # 5 ROC XLY/XLP como proxy confianza consumidor si existen
    roc_xly_xlp = pd.Series(index=close_df.index, dtype=float)
    if "XLY" in close_df.columns and "XLP" in close_df.columns:
        ratio = close_df["XLY"] / close_df["XLP"]
        roc_xly_xlp = (ratio / ratio.shift(63) - 1) * 100

    regimen = pd.DataFrame({
        "vol_pctil": vol_pctil, "vix_z": vix_z, "fase_num": fase_num,
        "ig_pctil": ig_pctil, "hy_pctil": hy_pctil, "roc_xly_xlp": roc_xly_xlp,
    }).dropna(how="all")
    # normalizar para distancia euclidiana (z-score por columna)
    norm = (regimen - regimen.mean()) / regimen.std().replace(0, 1)
    return regimen, norm


def analogos(norm_df, fecha_ref, n=20, dist_umbral=1.2):
    if fecha_ref not in norm_df.index:
        fecha_ref = norm_df.index[norm_df.index.get_indexer([fecha_ref], method="nearest")[0]]
    vec = norm_df.loc[fecha_ref].values
    dists = np.sqrt(((norm_df - vec) ** 2).sum(axis=1))
    dists = dists[dists.index < fecha_ref]
    candidatos = dists.nsmallest(n * 3)
    candidatos = candidatos[candidatos <= dist_umbral]
    return candidatos.head(n)


def evaluar_analogos(close_df, analogos_series, horizontes=(21, 63, 126)):
    rets = np.log(close_df / close_df.shift(1))
    # pool proxy: mejor activo del universo en cada horizonte? Para regimen simple,
    # usamos retorno del equal-weight del universo como proxy de tipo "equi-weight"
    eq_ret = rets.mean(axis=1)
    out = {}
    for h in horizontes:
        fwd = eq_ret.rolling(h).sum().shift(-h)
        vals = []
        for d in analogos_series.index:
            try:
                vals.append(float(fwd.loc[d]))
            except Exception:
                pass
        vals = [v for v in vals if v is not None and np.isfinite(v)]
        win = sum(1 for v in vals if v > 0) / max(1, len(vals)) if vals else 0
        out[h] = {"win_rate": round(win, 3), "n": len(vals),
                  "ret_medio": round(float(np.mean(vals)), 4) if vals else 0}
    return out
