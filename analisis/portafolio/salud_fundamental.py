# -*- coding: utf-8 -*-
"""Salud fundamental de las empresas de un portafolio Inviu.

Uso:
    python -m analisis.portafolio.salud_fundamental --in portafolios_inviu.json --cuenta 264900

Genera SALUD_FUNDAMENTAL.md + salud_fundamental.json con ratios, Altman Z,
modelo Pascale 1988, test de leverage, score por dimension y semaforo.

Metodologia con umbral textual en el corpus (txt metodologias/, lectura integra):
- Liquidez corriente no <1; ideal 1-2 (>1.5 pref.) .... Biondi cap.5 2.3.2.2 (l.838); Amat (l.2333)
- Prueba acida normal cerca de 1 o algo por debajo .... Biondi cap.5 2.3.2.3 (l.877); Pascale U2-1 (l.203)
- Endeudamiento P/PN estandar ~1 ...................... Biondi cap.5 2.3.2.7 (l.924)
- Endeudamiento P/(PN+P) <= 0.6; calidad deuda PC/P ... Amat (l.2291 y l.2313)
- Cobertura GAII/intereses; covenant EBITDA/int 1.75-2x Pascale U2-1 (l.269); Elbaum IFACI U4 (l.5044)
- Test leverage: rentabilidad activo vs costo deuda ... Fowler Newton c.6 (l.2756); Biondi cap.5 (l.985); Pascale U2-2 (l.550)
- Du Pont modificado ROA=margen x rotacion; ROE=ROA x mult . Pascale U2-1 (l.705); Biondi cap.5 4.4 (l.1598)
- Altman Z 1968 corte 2.675 zona gris 1.81-2.89 ....... Pascale U2-1 (l.881)
- Modelo PASCALE 1988 (LatAm) critico 0 gris -1.05..0.4 . Pascale U2-1 (l.950)

Criterio propio (sin umbral textual en el corpus): bandas de scoring de
rentabilidad y flujo; definicion de cash flow segun Glosario IFACI (l.251)
y Amat (l.3192). Datos reales via yfinance
(coronar bases/api yfinance.txt), cache en data_cache/fundamentales/.
Los ETFs no publican estados contables: composicion via funds_data.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data_cache", "fundamentales")
TTL_DIAS = 7

MAPEO_SUBYACENTE = {
    "PAMP": "PAM",
}

ETFS_SUBYACENTES = {"SPY", "SMH", "URA", "XLE"}

PESOS_DIMENSIONES = {
    "liquidez": 0.15,
    "solvencia": 0.25,
    "rentabilidad": 0.20,
    "bancarrota": 0.20,
    "flujo": 0.20,
}


def _num(x):
    try:
        v = float(x)
        if pd.isna(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _fila(df, nombres):
    """Ultimo valor disponible de una fila del estado contable probando varios rotulos."""
    if df is None or getattr(df, "empty", True):
        return None
    for nombre in nombres:
        if nombre in df.index:
            for col in df.columns:
                v = _num(df.loc[nombre, col])
                if v is not None:
                    return v
    return None


def altman_z(x1, x2, x3, x4, x5):
    """Z = 1.2*WC/AT + 1.4*RE/AT + 3.3*GAII/AT + 0.6*MV/D + 1.0*V/AT (Pascale U2-1, l.886)."""
    if any(v is None for v in (x1, x2, x3, x4, x5)):
        return None
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def pascale_z(x1, x2, x3):
    """Z = -3.70992 + 0.99418*(Vtas/Deudas) + 6.55340*(Gain/AT) + 5.51253*(LP/DT).

    Modelo calibrado para manufactura latinoamericana (Uruguay 1988);
    x2 usa ganancia neta como proxy de ganancia ajustada por inflacion.
    """
    if any(v is None for v in (x1, x2, x3)):
        return None
    return -3.70992 + 0.99418 * x1 + 6.55340 * x2 + 5.51253 * x3


def zona_altman(z):
    """Segura >=2.9; ignorancia 1.81-2.89; riesgo <1.81 (Pascale U2-1, l.902)."""
    if z is None:
        return None
    if z >= 2.9:
        return "SEGURA"
    if z >= 1.81:
        return "GRIS"
    return "RIESGO"


def zona_pascale(z):
    """Critico 0; ignorancia -1.05 < Z < 0.4 (Pascale U2-1, l.964)."""
    if z is None:
        return None
    if z > 0.4:
        return "SEGURA"
    if z >= -1.05:
        return "GRIS"
    return "RIESGO"


def dupont(margen_neto, rotacion_activos, apalancamiento):
    """Du Pont modificado (Pascale U2-1, l.705): ROE = margen x rotacion x multiplicador."""
    if None in (margen_neto, rotacion_activos, apalancamiento):
        return None
    return margen_neto * rotacion_activos * apalancamiento


def calcular_metricas(info, bs, inc, cf):
    """Ratios desde estados contables (DataFrames yfinance) con fallback a info."""
    ta = _fila(bs, ["Total Assets"])
    ca = _fila(bs, ["Current Assets"])
    cl = _fila(bs, ["Current Liabilities"])
    wc = _fila(bs, ["Working Capital"])
    inv = _fila(bs, ["Inventory"])
    re_ = _fila(bs, ["Retained Earnings"])
    td = _fila(bs, ["Total Debt"])
    eq = _fila(bs, ["Stockholders Equity", "Common Stock Equity"])
    pt = _fila(bs, ["Total Liabilities Net Minority Interest", "Total Liabilities"])
    rev = _fila(inc, ["Total Revenue", "Operating Revenue"])
    ebit = _fila(inc, ["EBIT", "Operating Income"])
    ebitda = _fila(inc, ["EBITDA", "Normalized EBITDA"])
    ni = _fila(inc, ["Net Income Common Stockholders", "Net Income"])
    gp = _fila(inc, ["Gross Profit"])
    ltd = _fila(bs, ["Long Term Debt"])
    intereses = _fila(inc, ["Interest Expense", "Interest Expense Non Operating"])
    ocf = _fila(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    capex = _fila(cf, ["Capital Expenditure"])

    def info_val(*claves):
        for k in claves:
            v = _num(info.get(k)) if isinstance(info, dict) else None
            if v is not None:
                return v
        return None

    market_cap = info_val("marketCap")
    td = td if td is not None else info_val("totalDebt")
    rev = rev if rev is not None else info_val("totalRevenue")
    ebitda = ebitda if ebitda is not None else info_val("ebitda")

    if pt is None and ta is not None and eq is not None:
        pt = ta - eq
    if intereses is None and isinstance(info, dict):
        ie = _num(info.get("interestExpense"))
        intereses = abs(ie) if ie is not None else None

    def div(a, b):
        if a is None or b in (None, 0):
            return None
        return a / b

    razon_corriente = div(ca, cl)
    if razon_corriente is None:
        razon_corriente = info_val("currentRatio")
    prueba_acida = None
    if ca is not None and cl not in (None, 0):
        prueba_acida = (ca - (inv if inv is not None else 0)) / cl
    if prueba_acida is None:
        prueba_acida = info_val("quickRatio")

    endeudamiento_biondi = div(pt, eq)
    endeudamiento_amat = div(pt, pt + eq if eq is not None else None)
    calidad_deuda = div(cl, pt)
    deuda_patrimonio = div(td, eq)
    dp_info = info_val("debtToEquity")
    if deuda_patrimonio is None and dp_info is not None:
        deuda_patrimonio = dp_info / 100.0
    deuda_ebitda = div(td, ebitda)
    lp_deuda_total = div(ltd, td)

    cobertura_intereses = div(abs(ebit), intereses) if ebit is not None else None
    rentabilidad_activa = div(ebit, ta)
    costo_deuda = div(intereses, td)
    spread_leverage = None
    if rentabilidad_activa is not None and costo_deuda is not None:
        spread_leverage = rentabilidad_activa - costo_deuda

    margen_bruto = div(gp, rev)
    if margen_bruto is None:
        margen_bruto = info_val("grossMargins")
    margen_operativo = div(ebit, rev)
    if margen_operativo is None:
        margen_operativo = info_val("operatingMargins")
    margen_neto = div(ni, rev)
    if margen_neto is None:
        margen_neto = info_val("profitMargins")
    roe = div(ni, eq)
    if roe is None:
        roe = info_val("returnOnEquity")
    roa = div(ni, ta)
    if roa is None:
        roa = info_val("returnOnAssets")

    rotacion_activos = div(rev, ta)
    multiplicador_leverage = div(ta, eq)
    roe_dupont = dupont(margen_neto, rotacion_activos, multiplicador_leverage)

    fcf = _fila(cf, ["Free Cash Flow"])
    if fcf is None and ocf is not None and capex is not None:
        fcf = ocf + capex
    if fcf is None:
        fcf = info_val("freeCashflow")

    if wc is not None and ta not in (None, 0):
        x1 = wc / ta
    elif ca is not None and cl is not None and ta not in (None, 0):
        x1 = (ca - cl) / ta
    else:
        x1 = None
    x2 = div(re_, ta)
    x3 = div(ebit, ta)
    x4 = div(market_cap, td)
    x5 = div(rev, ta)
    z = altman_z(x1, x2, x3, x4, x5)

    zx1 = div(rev, pt)
    zx2 = div(ni, ta)
    zx3 = lp_deuda_total
    zp = pascale_z(zx1, zx2, zx3)

    return {
        "empresa": info.get("longName") or info.get("shortName") or "",
        "moneda": info.get("currency") or "",
        "sector_yf": info.get("sector") or "",
        "market_cap": market_cap,
        "razon_corriente": razon_corriente,
        "prueba_acida": prueba_acida,
        "endeudamiento_biondi": endeudamiento_biondi,
        "endeudamiento_amat": endeudamiento_amat,
        "calidad_deuda": calidad_deuda,
        "deuda_patrimonio": deuda_patrimonio,
        "deuda_ebitda": deuda_ebitda,
        "lp_deuda_total": lp_deuda_total,
        "cobertura_intereses": cobertura_intereses,
        "rentabilidad_activa": rentabilidad_activa,
        "costo_deuda": costo_deuda,
        "spread_leverage": spread_leverage,
        "margen_bruto": margen_bruto,
        "margen_operativo": margen_operativo,
        "margen_neto": margen_neto,
        "roe": roe,
        "roa": roa,
        "roe_dupont": roe_dupont,
        "rotacion_activos": rotacion_activos,
        "multiplicador_leverage": multiplicador_leverage,
        "fcf": fcf,
        "fcf_ingresos": div(fcf, rev),
        "fcf_utilidad": div(fcf, ni),
        "crec_ingresos": info_val("revenueGrowth"),
        "crec_utilidades": info_val("earningsGrowth"),
        "altman": {"x1_wc_at": x1, "x2_re_at": x2, "x3_gaii_at": x3, "x4_mv_d": x4, "x5_v_at": x5},
        "z": z,
        "pascale": {"x1_vtas_d": zx1, "x2_gain_at": zx2, "x3_lp_dt": zx3},
        "z_pascale": zp,
        "fuente": "yfinance",
    }


def score_liquidez(m):
    """Ideal 1.5-2 (Amat l.2340); piso 1 (Biondi l.848); exceso leve penalizado (Amat l.2451)."""
    puntajes = []
    rc = m.get("razon_corriente")
    if rc is not None:
        if rc >= 2.5:
            s = 88
        elif rc >= 1.5:
            s = 100
        elif rc >= 1.2:
            s = 88
        elif rc >= 1.0:
            s = 72
        elif rc >= 0.8:
            s = 45
        else:
            s = 15
        puntajes.append(s)
    pa = m.get("prueba_acida")
    if pa is not None:
        if pa >= 1.0:
            s = 100
        elif pa >= 0.86:
            s = 92
        elif pa >= 0.7:
            s = 75
        elif pa >= 0.5:
            s = 55
        else:
            s = 25
        puntajes.append(s)
    return round(sum(puntajes) / len(puntajes), 1) if puntajes else None


def _score_cobertura(cob):
    """Covenant argentino: EBITDA/int >= 1.75-2x (Elbaum U4, l.5044)."""
    if cob is None:
        return None
    if cob >= 2.0:
        return 100.0
    if cob >= 1.75:
        return 90.0
    if cob >= 1.25:
        return 65.0
    if cob >= 1.0:
        return 45.0
    return 10.0


def _score_leverage(spread):
    """Test FN c.6/Biondi/Pascale U2-2: >0 apalancamiento provechoso."""
    if spread is None:
        return None
    if spread > 0.05:
        return 100.0
    if spread > 0:
        return 85.0
    if spread >= -0.02:
        return 50.0
    return 20.0


def score_solvencia(m):
    """P/(PN+P)<=0.6 (Amat l.2297); calidad deuda PC/P (l.2313); D/EBITDA tope 6x covenant."""
    puntajes = []
    ea = m.get("endeudamiento_amat")
    if ea is not None:
        s = 100 if ea <= 0.5 else 85 if ea <= 0.6 else 60 if ea <= 0.75 else 35 if ea <= 0.9 else 10
        puntajes.append(s)
    de = m.get("deuda_ebitda")
    if de is not None:
        s = 100 if de <= 1 else 85 if de <= 2 else 70 if de <= 3 else 45 if de <= 4 else 15 if de <= 6 else 5
        puntajes.append(s)
    cd = m.get("calidad_deuda")
    if cd is not None:
        s = 100 if cd <= 0.4 else 70 if cd <= 0.6 else 40
        puntajes.append(s)
    cob = _score_cobertura(m.get("cobertura_intereses"))
    if cob is not None:
        puntajes.append(cob)
    lev = _score_leverage(m.get("spread_leverage"))
    if lev is not None:
        puntajes.append(lev)
    return round(sum(puntajes) / len(puntajes), 1) if puntajes else None


def score_rentabilidad(m):
    """Bandas criterio propio; referencias corpus: XYZ ROE 28% solido, Saludable 2% debil."""
    puntajes = []
    roe = m.get("roe")
    if roe is not None:
        s = 100 if roe >= 0.20 else 90 if roe >= 0.15 else 75 if roe >= 0.10 else 55 if roe >= 0.05 else 35 if roe > 0 else 10
        puntajes.append(s)
    roa = m.get("roa")
    if roa is not None:
        s = 100 if roa >= 0.10 else 85 if roa >= 0.05 else 70 if roa >= 0.03 else 45 if roa > 0 else 10
        puntajes.append(s)
    mo = m.get("margen_operativo")
    if mo is not None:
        s = 100 if mo >= 0.25 else 85 if mo >= 0.15 else 65 if mo >= 0.08 else 40 if mo > 0 else 10
        puntajes.append(s)
    return round(sum(puntajes) / len(puntajes), 1) if puntajes else None


def score_bancarrota(m):
    """Promedio entre Altman 1968 y modelo Pascale 1988 cuando ambos existen."""
    scores = []
    z = m.get("z")
    if z is not None:
        if z >= 2.9:
            scores.append(100.0)
        elif z >= 2.675:
            scores.append(85.0)
        elif z >= 1.81:
            scores.append(55.0)
        elif z >= 1.10:
            scores.append(30.0)
        else:
            scores.append(5.0)
    zp = m.get("z_pascale")
    if zp is not None:
        if zp > 0.4:
            scores.append(100.0)
        elif zp >= 0:
            scores.append(70.0)
        elif zp >= -1.05:
            scores.append(35.0)
        else:
            scores.append(5.0)
    return round(sum(scores) / len(scores), 1) if scores else None


def score_flujo(m):
    """Bandas criterio propio; cash flow = resultado + partidas no dinerarias (IFACI l.251)."""
    puntajes = []
    fcfu = m.get("fcf_utilidad")
    if fcfu is not None:
        s = 100 if fcfu >= 0.8 else 75 if fcfu >= 0.5 else 50 if fcfu > 0 else 15
        puntajes.append(s)
    elif m.get("fcf") is not None:
        puntajes.append(80.0 if m["fcf"] > 0 else 20.0)
    ci = m.get("crec_ingresos")
    if ci is not None:
        s = 100 if ci >= 0.15 else 85 if ci >= 0.08 else 70 if ci >= 0.02 else 50 if ci > 0 else 20
        puntajes.append(s)
    cu = m.get("crec_utilidades")
    if cu is not None:
        s = 100 if cu >= 0.15 else 80 if cu >= 0.05 else 60 if cu > 0 else 20
        puntajes.append(s)
    return round(sum(puntajes) / len(puntajes), 1) if puntajes else None


def clasificar(score):
    if score is None:
        return "SIN DATOS"
    if score >= 75:
        return "SANO"
    if score >= 55:
        return "MODERADO"
    if score >= 40:
        return "FRAGIL"
    return "EN RIESGO"


def score_total(scores):
    num = den = 0.0
    for dim, peso in PESOS_DIMENSIONES.items():
        s = scores.get(dim)
        if s is not None:
            num += s * peso
            den += peso
    return round(num / den, 1) if den else None


def _cache_path(tk):
    return os.path.join(CACHE_DIR, "%s.json" % tk)


def _cache_valido(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        fetched = datetime.fromisoformat(data["_fetched_at"])
        return datetime.now() - fetched < timedelta(days=TTL_DIAS)
    except Exception:
        return False


def _guardar_cache(tk, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data["_fetched_at"] = datetime.now().isoformat()
        with open(_cache_path(tk), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    except Exception:
        pass


def descargar_empresa(tk, force=False):
    """Metricas fundamentales reales del subyacente via yfinance (con cache)."""
    path = _cache_path(tk)
    if not force and _cache_valido(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import yfinance as yf

    t = yf.Ticker(tk)
    info = t.info or {}
    try:
        bs = t.balance_sheet
    except Exception:
        bs = pd.DataFrame()
    try:
        inc = t.income_stmt
    except Exception:
        inc = pd.DataFrame()
    try:
        cf = t.cashflow
    except Exception:
        cf = pd.DataFrame()
    metricas = calcular_metricas(info, bs, inc, cf)
    metricas["ticker_yf"] = tk
    _guardar_cache(tk, metricas)
    return metricas


def descargar_etf(tk, force=False):
    """Composicion del ETF (top-holdings y ratio de gastos) via funds_data."""
    path = _cache_path("ETF_" + tk)
    if not force and _cache_valido(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import yfinance as yf

    t = yf.Ticker(tk)
    out = {"ticker_yf": tk, "empresa": "", "es_etf": True}
    try:
        fd = t.funds_data
        th = fd.top_holdings
        if th is not None and not th.empty:
            col_nombre = "Holding" if "Holding" in th.columns else ("Name" if "Name" in th.columns else None)
            col_peso = "Weight" if "Weight" in th.columns else ("Holding Percent" if "Holding Percent" in th.columns else None)
            pesos = [_num(r.get(col_peso)) for _, r in th.head(10).iterrows()] if col_peso else []
            es_porcentaje = bool(pesos) and max(p for p in pesos if p is not None) > 1.5
            filas = []
            for idx, r in th.head(10).iterrows():
                nombre = str(r[col_nombre]) if col_nombre else ""
                sym = str(idx) if idx is not None else ""
                peso = _num(r.get(col_peso)) if col_peso else None
                if peso is not None and es_porcentaje:
                    peso = peso / 100.0
                filas.append({"holding": nombre, "symbol": sym, "peso": peso})
            out["top_holdings"] = filas
        out["descripcion"] = (fd.description or "")[:400]
    except Exception:
        pass
    try:
        info = t.info or {}
        out["empresa"] = info.get("longName") or info.get("shortName") or ""
        out["expense_ratio"] = _num(info.get("annualReportExpenseRatio"))
    except Exception:
        pass
    _guardar_cache("ETF_" + tk, out)
    return out


def es_entidad_financiera(sector):
    """Modelos de bancarrota calibrados para manufactura (Pascale U2-1 l.951);
    en bancos los depositos inflan pasivo/costo de deuda -> no aplican."""
    return str(sector or "").lower().startswith("financial")


def preparar_metricas_para_scoring(m):
    """Quita a una entidad financiera las metricas que no le aplican."""
    if es_entidad_financiera(m.get("sector_yf")):
        excluir = {"z", "z_pascale", "endeudamiento_amat", "spread_leverage",
                   "cobertura_intereses", "costo_deuda"}
        return {k: v for k, v in m.items() if k not in excluir}, True
    return m, False


def analizar_cuenta_fundamental(cuenta, force=False):
    empresas, etfs, errores = [], [], []
    for t in cuenta.get("tenencias", []):
        tk_local = t["ticker"]
        tk_yf = MAPEO_SUBYACENTE.get(tk_local, tk_local)
        es_etf = tk_yf in ETFS_SUBYACENTES or t.get("tipo") == "etf"
        try:
            if es_etf:
                data = descargar_etf(tk_yf, force=force)
                etfs.append({"ticker": tk_local, **data})
                continue
            m = descargar_empresa(tk_yf, force=force)
        except Exception as e:
            errores.append("%s: %s" % (tk_local, e))
            continue
        m_score, excluida = preparar_metricas_para_scoring(m)
        notas = []
        if excluida:
            notas.append("Entidad financiera (%s): modelos de bancarrota y ratios corporativos de deuda no aplicables (depositos distorsionan el pasivo)" % m.get("sector_yf"))
        scores = {
            "liquidez": score_liquidez(m_score),
            "solvencia": score_solvencia(m_score),
            "rentabilidad": score_rentabilidad(m_score),
            "bancarrota": score_bancarrota(m_score),
            "flujo": score_flujo(m_score),
        }
        total = score_total(scores)
        empresas.append({
            "ticker": tk_local,
            "ticker_yf": tk_yf,
            "sector": t.get("sector", ""),
            "cantidad": t.get("cantidad"),
            "scores": scores,
            "score_total": total,
            "calificacion": clasificar(total),
            "es_financiera": excluida,
            "notas": notas,
            **{k: v for k, v in m.items() if k != "altman"},
            "altman": m.get("altman"),
        })
    empresas.sort(key=lambda e: -(e.get("score_total") or -1))
    return {"empresas": empresas, "etfs": etfs, "errores": errores}


def _fmt(v, pct=False, dec=2):
    if v is None:
        return "n/d"
    if pct:
        return "%.1f%%" % (v * 100)
    return "%.*f" % (dec, v)


FUENTES_METODOLOGIA = [
    ("Razon corriente", "no <1; ideal 1-2 (>1.5)", "Biondi c.5 2.3.2.2 l.838; Amat l.2333"),
    ("Prueba acida", "~1 o algo por debajo", "Biondi c.5 2.3.2.3 l.877; Pascale U2-1 l.203"),
    ("Endeudamiento Biondi P/PN", "~1", "Biondi c.5 2.3.2.7 l.924"),
    ("Endeudamiento Amat P/(PN+P)", "<=0.6", "Amat l.2297"),
    ("Calidad deuda PC/P", "menor mejor", "Amat l.2313"),
    ("Cobertura intereses", "covenant 1.75-2.0x", "Pascale U2-1 l.269; Elbaum U4 l.5044"),
    ("Test leverage", "rent.activo vs costo deuda >0", "FN c.6 l.2756; Biondi c.5 l.985; Pascale U2-2 l.550"),
    ("Du Pont modificado", "ROE=margen x rot x mult", "Pascale U2-1 l.705; Biondi c.5 4.4 l.1598"),
    ("Altman Z 1968", "corte 2.675; gris 1.81-2.89", "Pascale U2-1 l.881"),
    ("Modelo Pascale 1988", "critico 0; gris -1.05..0.4", "Pascale U2-1 l.950"),
    ("Score rentabilidad y flujo", "bandas criterio propio", "cash flow: IFACI l.251; Amat l.3192"),
]


def generar_informe(archivo_in="portafolios_inviu.json", cuenta_id=None, archivo_out="SALUD_FUNDAMENTAL.md", force=False):
    with open(archivo_in, encoding="utf-8") as f:
        data = json.load(f)
    cuentas = data["cuentas"]
    cuenta = next((c for c in cuentas if str(c.get("cuenta")) == str(cuenta_id)), cuentas[0])
    res = analizar_cuenta_fundamental(cuenta, force=force)
    res["subyacentes_cartera"] = sorted({MAPEO_SUBYACENTE.get(t["ticker"], t["ticker"]) for t in cuenta.get("tenencias", [])})

    md = []
    md.append("# Salud Fundamental — Portafolio %s (cuenta %s)" % (cuenta["nombre"], cuenta["cuenta"]))
    md.append("**Fecha:** %s  |  **Datos:** yfinance (subyacentes; PAMP via ADR PAM)" % datetime.now().strftime("%Y-%m-%d"))
    md.append("")
    md.append("> Corpus metodologico leido integramente (txt metodologias/): umbrales tomados de los")
    md.append("> textos donde existen; ver tabla 'Metodologia y fuentes' al final. Lo no respaldado")
    md.append("> textualmente esta marcado como criterio propio.")
    md.append("")
    md.append("## Resumen")
    md.append("| Ticker | Empresa | Score | Calificacion | Altman Z | Pascale Z | ROE | P/(PN+P) | Razon Corr. | Cob.Int. | FCF |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for e in res["empresas"]:
        fin = bool(e.get("es_financiera"))
        z_alt = "n/ap" if fin else "%s (%s)" % (_fmt(e.get("z")), zona_altman(e.get("z")) or "n/d")
        z_pas = "n/ap" if fin else "%s (%s)" % (_fmt(e.get("z_pascale")), zona_pascale(e.get("z_pascale")) or "n/d")
        md.append("| %s | %s | %s | **%s** | %s | %s | %s | %s | %s | %s | %s |" % (
            e["ticker"],
            (e.get("empresa") or "-")[:26],
            _fmt(e.get("score_total"), dec=1),
            e["calificacion"],
            z_alt,
            z_pas,
            _fmt(e.get("roe"), pct=True),
            _fmt(e.get("endeudamiento_amat")),
            _fmt(e.get("razon_corriente")),
            _fmt(e.get("cobertura_intereses"), dec=2),
            _fmt(e.get("fcf"), dec=0),
        ))
    md.append("")

    for e in res["empresas"]:
        md.append("---")
        md.append("## %s — %s [%s]" % (e["ticker"], e.get("empresa") or "n/d", e["calificacion"]))
        for nota in e.get("notas", []):
            md.append("")
            md.append("> **Nota:** %s" % nota)
        md.append("")
        md.append("| Dimension | Score | Detalle |")
        md.append("|---|---|---|")
        det = {
            "Liquidez (Biondi/Amat)": "razon corr. %s | acida %s" % (_fmt(e.get("razon_corriente")), _fmt(e.get("prueba_acida"))),
            "Solvencia (Amat/Biondi/covenants)": "P/(PN+P) %s | P/PN %s | PC/P %s | D/EBITDA %s | cob.int. %s | rent.activo %s vs costo deuda %s (spread %s)" % (
                _fmt(e.get("endeudamiento_amat")), _fmt(e.get("endeudamiento_biondi")), _fmt(e.get("calidad_deuda")),
                _fmt(e.get("deuda_ebitda")), _fmt(e.get("cobertura_intereses")),
                _fmt(e.get("rentabilidad_activa"), pct=True), _fmt(e.get("costo_deuda"), pct=True), _fmt(e.get("spread_leverage"), pct=True)),
            "Rentabilidad (Du Pont mod.)": "ROE %s (DuPont %s) | ROA %s | m.arg. %s | m.op. %s | m.neto %s" % (
                _fmt(e.get("roe"), pct=True), _fmt(e.get("roe_dupont"), pct=True), _fmt(e.get("roa"), pct=True),
                _fmt(e.get("margen_bruto"), pct=True), _fmt(e.get("margen_operativo"), pct=True), _fmt(e.get("margen_neto"), pct=True)),
            "Bancarrota (Altman+Pascale)": "Altman Z=%s (%s) | Pascale Z=%s (%s)" % (
                _fmt(e.get("z")), zona_altman(e.get("z")) or "n/d",
                _fmt(e.get("z_pascale")), zona_pascale(e.get("z_pascale")) or "n/d"),
            "Flujo/Calidad (crit. propio)": "FCF %s | FCF/ingr. %s | FCF/util. %s | crec. ingr. %s | crec. util. %s" % (
                _fmt(e.get("fcf"), dec=0), _fmt(e.get("fcf_ingresos"), pct=True), _fmt(e.get("fcf_utilidad"), pct=True),
                _fmt(e.get("crec_ingresos"), pct=True), _fmt(e.get("crec_utilidades"), pct=True)),
        }
        claves = ["liquidez", "solvencia", "rentabilidad", "bancarrota", "flujo"]
        for (titulo, detalle), clave in zip(det.items(), claves):
            md.append("| %s | %s | %s |" % (titulo, _fmt(e["scores"].get(clave), dec=0), detalle))
        md.append("| **TOTAL ponderado** | **%s** | **%s** |" % (_fmt(e.get("score_total"), dec=1), e["calificacion"]))
        md.append("")

    if res["etfs"]:
        md.append("---")
        md.append("## ETFs del portafolio (no aplican estados contables)")
        md.append("")
        for etf in res["etfs"]:
            md.append("### %s — %s" % (etf["ticker"], etf.get("empresa") or ""))
            er = etf.get("expense_ratio")
            if er is not None:
                md.append("- Ratio de gastos anual: %.2f%%" % (er * 100))
            th = etf.get("top_holdings") or []
            if th:
                md.append("")
                md.append("| Holding | Simbolo | Peso |")
                md.append("|---|---|---|")
                for h in th:
                    md.append("| %s | %s | %.2f%% |" % (h["holding"][:40], h.get("symbol") or "-", (h.get("peso") or 0) * 100))
                en_cartera = [h for h in th if h.get("symbol") in set(res.get("subyacentes_cartera", []))]
                if en_cartera:
                    md.append("")
                    md.append("- Solapamiento con tenencias propias: %s" % ", ".join("%s (%.2f%%)" % (h["symbol"], (h.get("peso") or 0) * 100) for h in en_cartera))
            md.append("")

    if res["errores"]:
        md.append("---")
        md.append("## Errores de descarga")
        for err in res["errores"]:
            md.append("- %s" % err)
        md.append("")

    md.append("---")
    md.append("## Metodologia y fuentes (txt metodologias/)")
    md.append("")
    md.append("| Ratio | Umbral aplicado | Fuente |")
    md.append("|---|---|---|")
    for ratio, umbral, fuente in FUENTES_METODOLOGIA:
        md.append("| %s | %s | %s |" % (ratio, umbral, fuente))
    md.append("| Exclusion entidades financieras | modelos no aplicables | Pascale U2-1 l.951 (calibrado a manufactura) |")

    texto = "\n".join(md)
    with open(archivo_out, "w", encoding="utf-8") as f:
        f.write(texto)
    json_out = os.path.splitext(archivo_out)[0] + ".json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump({"fecha": datetime.now().strftime("%Y-%m-%d"), "cuenta": cuenta["cuenta"], **res}, f, ensure_ascii=False, indent=1, default=str)
    return texto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="portafolios_inviu.json")
    parser.add_argument("--cuenta", default=None)
    parser.add_argument("--out", default="SALUD_FUNDAMENTAL.md")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    texto = generar_informe(args.input, args.cuenta, args.out, force=args.force)
    print(texto)
    print("\nGuardado en %s (+json)" % args.out)


if __name__ == "__main__":
    main()
