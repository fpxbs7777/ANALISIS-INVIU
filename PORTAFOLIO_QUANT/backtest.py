# -*- coding: utf-8 -*-
"""Backtest walk-forward mensual + metrica MFE/MAE por entrada."""
import numpy as np
import pandas as pd


def mfe_mae(precios_ventana, precio_entrada):
    hi = float(precios_ventana.max())
    lo = float(precios_ventana.min())
    return (hi / precio_entrada - 1) * 100, (lo / precio_entrada - 1) * 100


def walk_forward(close_df, construir_fn, inicio="2018-01-01", rebalanceo="M",
                 costo_bps=15, benchmark=None):
    close_df = close_df.sort_index()
    close_df = close_df[close_df.index >= inicio]
    if close_df.empty:
        return {}
    # fechas de rebalanceo: fin de mes
    idx = pd.date_range(close_df.index.min(), close_df.index.max(), freq=rebalanceo)
    # mapear a trading days
    reb = [close_df.index[close_df.index.get_indexer([d], method="ffill")[0]] for d in idx]
    reb = sorted(set(r for r in reb if r in close_df.index))
    equity = []
    trades = []
    pesos_hist = []
    prev_pesos = None
    for i, d in enumerate(reb[:-1]):
        d_next = reb[i + 1]
        hist = close_df.loc[:d]
        fwd = close_df.loc[d:d_next]
        if len(hist) < 120 or len(fwd) < 5:
            continue
        carteras, _ = construir_fn(hist)
        # elegimos long-only como cartera representativa para backtest base
        pesos = carteras.get("long-only", {}).get("pesos", {})
        if not pesos or not any(v > 1e-4 for v in pesos.values()):
            continue
        activos = [k for k, v in pesos.items() if v > 1e-4]
        w = np.array([pesos[k] for k in activos])
        # costo turnover
        if prev_pesos is not None:
            prev_alineado = np.array([prev_pesos.get(k, 0) for k in activos])
            turnover = np.abs(w - prev_alineado).sum()
        else:
            turnover = np.abs(w).sum()
        costo = turnover * (costo_bps / 10000)
        rets_fwd = np.log(fwd[activos] / fwd[activos].shift(1)).dropna()
        port_ret = (rets_fwd.values * w).sum(axis=1)
        # aplicar costo prorrateado al primer dia
        if len(port_ret) > 0:
            port_ret[0] -= costo
        # equity
        for j, (dt, r) in enumerate(zip(rets_fwd.index, port_ret)):
            equity.append((dt, r))
        # MFE/MAE por posicion (ventana hasta proximo rebalanceo)
        for k, weight in pesos.items():
            if weight < 1e-4:
                continue
            px_entry = float(fwd[k].iloc[0])
            mfe, mae = mfe_mae(fwd[k], px_entry)
            trades.append({"fecha": d.strftime("%Y-%m-%d"), "ticker": k,
                           "peso": round(weight, 4), "mfe": round(mfe, 2),
                           "mae": round(mae, 2),
                           "ret_hold": round((fwd[k].iloc[-1] / px_entry - 1) * 100, 2)})
        pesos_hist.append({"fecha": d.strftime("%Y-%m-%d"), "pesos": pesos})
        prev_pesos = dict(zip(activos, w))

    if not equity:
        return {"equity": pd.DataFrame(), "trades": pd.DataFrame(), "pesos": pesos_hist}
    eq_df = pd.DataFrame(equity, columns=["fecha", "ret"])
    eq_df["equity"] = (1 + eq_df["ret"]).cumprod()
    trades_df = pd.DataFrame(trades)
    win = (trades_df["ret_hold"] > 0).mean() if not trades_df.empty else 0
    return {"equity": eq_df, "trades": trades_df, "pesos": pesos_hist,
            "win_rate": round(float(win), 3), "n_trades": len(trades_df)}
