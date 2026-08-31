# -*- coding: utf-8 -*-
"""Clases reutilizables para cada capitulo del libro de Murphy.

Cada clase define TICKERS y el metodo ejecutar(), que devuelve un dict con
los hallazgos clave. El formato es compacto para uso diario; el texto detallado
sigue en INFORME_AUDITORIA_INTERMARKET.md.
"""
from .base import CapituloBase


class Capitulo1(CapituloBase):
    TITULO = "Cap.1 - Intermarket Analysis (riesgo 1987)"
    TICKERS = {
        "SPY": "SPY", "TLT": "TLT", "CRB": "^SPGSCI",
        "DXY": "DX-Y.NYB", "TNX": "^TNX", "VIX": "^VIX",
    }

    def ejecutar(self):
        r = {}
        # relaciones con delay
        for a, b in [("DXY", "CRB"), ("TLT", "SPY"), ("CRB", "SPY"), ("TNX", "CRB")]:
            lag, val = self.corr(a, b)
            r["%s->%s" % (a, b)] = {"lag": lag, "corr": val}
        # filtro de riesgo
        r["filtro_riesgo"] = {
            "dxy_6m": self.v6("DXY"),
            "crb_6m": self.v6("CRB"),
            "tnx_6m": self.v6("TNX"),
            "vix_nivel": self.precio("VIX"),
        }
        return r


class Capitulo2(CapituloBase):
    TITULO = "Cap.2 - 1990 / Guerra del Golfo (divergencias y leading)"
    TICKERS = {
        "TLT": "TLT", "CRB": "^SPGSCI", "DXY": "DX-Y.NYB",
        "GOLD": "GC=F", "SPY": "SPY", "XLE": "XLE",
        "USO": "USO", "EWU": "EWU", "EWJ": "EWJ",
    }

    def ejecutar(self):
        r = {}
        r["divergencia_bonos_comm"] = {
            "tlt_6m": self.v6("TLT"),
            "crb_6m": self.v6("CRB"),
            "corr": self.corr("TLT", "CRB")[1],
            "alerta": self.v6("TLT") < 0 and self.v6("CRB") > 0,
        }
        r["dxy_oro"] = {
            "dxy_6m": self.v6("DXY"),
            "gold_6m": self.v6("GOLD"),
            "corr": self.corr("DXY", "GOLD")[1],
        }
        r["xle_wtic"] = {
            "xle_6m": self.v6("XLE"),
            "uso_6m": self.v6("USO"),
            "corr": self.corr("XLE", "USO")[1],
        }
        r["divergencia_global"] = {
            "ewu_6m": self.v6("EWU"),
            "ewj_6m": self.v6("EWJ"),
            "corr": self.corr("EWU", "EWJ")[1],
        }
        return r


class Capitulo3(CapituloBase):
    TITULO = "Cap.3 - 1994: suba de tasas y bonos liderando"
    TICKERS = {
        "TNX": "^TNX", "TLT": "TLT", "IRX": "^IRX", "SPY": "SPY",
        "DXY": "DX-Y.NYB", "VIX": "^VIX", "XLF": "XLF", "EEM": "EEM",
        "CRB": "^SPGSCI",
    }

    def ejecutar(self):
        r = {}
        tnx6 = self.v6("TNX")
        tlt6 = self.v6("TLT")
        r["shock_tasas"] = {
            "tnx_6m": tnx6,
            "tlt_6m": tlt6,
            "corr": self.corr("TNX", "SPY")[1],
            "alerta_1994": tnx6 is not None and tnx6 > 0.5 and (tlt6 is None or tlt6 < 0),
        }
        r["curva"] = {
            "irx": self.precio("IRX"),
            "tnx": self.precio("TNX"),
            "spread": (self.precio("TNX") - self.precio("IRX")) if self.precio("TNX") and self.precio("IRX") else None,
            "pendiente_6m": None,
        }
        if self.precio("IRX") is not None and self.precio("TNX") is not None:
            r["curva"]["pendiente_6m"] = (self.precio("IRX") - self.datos["IRX"].iloc[-126] if len(self.datos["IRX"]) > 126 else None)
        r["financieras_tasas"] = {
            "xlf_6m": self.v6("XLF"),
            "tnx_6m": tnx6,
            "corr": self.corr("XLF", "TNX")[1],
        }
        r["emer_tasas"] = {
            "eem_6m": self.v6("EEM"),
            "tnx_6m": tnx6,
            "corr": self.corr("EEM", "TNX")[1],
        }
        r["riesgo"] = {
            "vix": self.precio("VIX"),
            "dxy_6m": self.v6("DXY"),
        }
        return r


class Capitulo4(CapituloBase):
    TITULO = "Cap.4 - 1995-99: boom desinflacionario Growth"
    TICKERS = {
        "DXY": "DX-Y.NYB", "CRB": "^SPGSCI", "TNX": "^TNX", "TLT": "TLT",
        "SPY": "SPY", "QQQ": "QQQ", "XLK": "XLK", "IWM": "IWM",
        "VUG": "VUG", "VTV": "VTV", "EEM": "EEM", "GOLD": "GC=F",
    }

    def ejecutar(self):
        r = {}
        dxy6, crb6, tnx6 = self.v6("DXY"), self.v6("CRB"), self.v6("TNX")
        r["boom_definacional"] = {
            "dxy_6m": dxy6,
            "crb_6m": crb6,
            "tnx_6m": tnx6,
            "spy_6m": self.v6("SPY"),
            "condiciones_1995": (dxy6 is not None and dxy6 > 0 and crb6 is not None and crb6 < 0
                                 and tnx6 is not None and tnx6 < 0),
        }
        r["growth_vs_value"] = {
            "vug_6m": self.v6("VUG"),
            "vtv_6m": self.v6("VTV"),
            "growth_lidera": (self.v6("VUG") or -99) > (self.v6("VTV") or -99),
            "qqq_spy_slope200": self.ratio_slope("QQQ", "SPY", 200),
            "xlk_spy_slope200": self.ratio_slope("XLK", "SPY", 200),
        }
        r["small_caps"] = {"iwm_spy_slope200": self.ratio_slope("IWM", "SPY", 200)}
        r["oro_comm"] = {
            "gold_6m": self.v6("GOLD"),
            "crb_6m": crb6,
            "corr": self.corr("GOLD", "CRB")[1],
        }
        r["emer_dolar"] = {
            "eem_6m": self.v6("EEM"),
            "dxy_6m": dxy6,
            "corr": self.corr("EEM", "DXY")[1],
            "debil_1997": dxy6 is not None and dxy6 > 0 and (self.v6("EEM") or 99) < 0,
        }
        r["bonos_acciones"] = {
            "tlt_6m": self.v6("TLT"),
            "spy_6m": self.v6("SPY"),
            "corr": self.corr("TLT", "SPY")[1],
        }
        return r


class Capitulo5(CapituloBase):
    TITULO = "Cap.5 - 1999: tendencias que precedieron al tope"
    TICKERS = {
        "CRB": "^SPGSCI", "TNX": "^TNX", "GSCI": "^SPGSCI",
        "TLT": "TLT", "SPY": "SPY", "XLK": "XLK", "XLE": "XLE",
        "XLP": "XLP", "XLF": "XLF", "HK": "^HSI", "AUD": "FXA",
    }

    def ejecutar(self):
        r = {}
        r["comm_tasas_juntas"] = {
            "crb_6m": self.v6("CRB"),
            "tnx_6m": self.v6("TNX"),
            "corr": self.corr("CRB", "TNX")[1],
            "reflacion": self.v6("CRB") > 0 and self.v6("TNX") > 0,
        }
        r["ratio_comm_bond"] = {
            "slope200": self.ratio_slope("CRB", "TLT", 200),
            "pct200": (lambda st: st["pct"] if st else None)(self.ratio_stats("CRB", "TLT", 200)),
        }
        r["sector_rotation"] = {
            "xlk_6m": self.v6("XLK"),
            "xle_6m": self.v6("XLE"),
            "xlp_6m": self.v6("XLP"),
            "xlf_6m": self.v6("XLF"),
        }
        r["asia"] = {
            "hsi_6m": self.v6("HK"),
            "aud_corr_crb": self.corr("AUD", "CRB")[1],
        }
        return r


class Capitulo6(CapituloBase):
    TITULO = "Cap.6 - Review of Intermarket Principles"
    TICKERS = {
        "DXY": "DX-Y.NYB", "CRB": "^SPGSCI", "TLT": "TLT", "SPY": "SPY",
        "XLE": "XLE", "XLB": "XLB", "GOLD": "GC=F", "XLP": "XLP",
        "XLF": "XLF", "XLU": "XLU", "N225": "^N225", "TNX": "^TNX",
        "SMH": "SMH", "TSM": "TSM", "GM": "GM", "TM": "TM",
        "IWM": "IWM", "UPS": "UPS",
    }

    def ejecutar(self):
        r = {}
        r["vinculos_madre"] = {
            "dxy_crb": self.corr("DXY", "CRB")[1],
            "tlt_crb": self.corr("TLT", "CRB")[1],
            "tlt_spy": self.corr("TLT", "SPY")[1],
        }
        for sec in ["XLE", "XLB", "GOLD", "XLP", "XLF", "XLU"]:
            r["comm_bond_%s" % sec] = self.corr(sec, "CRB")[1]
        r["japon"] = {
            "n225_1y": self.v1y("N225"),
            "tnx_1y": self.v1y("TNX"),
            "corr": self.corr("N225", "TNX")[1],
        }
        r["global"] = {
            "smh_tsm": self.corr("SMH", "TSM")[1],
            "gm_tm": self.corr("GM", "TM")[1],
        }
        r["dolar_tamano"] = {
            "dxy_iwm": self.corr("DXY", "IWM")[1],
            "dxy_ups": self.corr("DXY", "UPS")[1],
        }
        return r


class Capitulo7(CapituloBase):
    TITULO = "Cap.7 - 2000: el estallido de la burbuja Nasdaq"
    TICKERS = {
        "SPY": "SPY", "DIA": "DIA", "QQQ": "QQQ", "TNX": "^TNX",
        "IRX": "^IRX", "XLP": "XLP", "VNQ": "VNQ", "XLU": "XLU",
        "COPPER": "HG=F", "VTV": "VTV", "VUG": "VUG",
        "XLK": "XLK", "XLE": "XLE",
    }

    def ejecutar(self):
        r = {}
        irx, tnx = self.precio("IRX"), self.precio("TNX")
        r["curva_invertida"] = {
            "IRX": irx, "TNX": tnx, "invertida": irx is not None and tnx is not None and irx > tnx,
        }
        for idx in ["SPY", "DIA", "QQQ"]:
            s = self.datos.get(idx)
            if s is not None and len(s) > 200:
                ma200 = s.iloc[-200:].mean()
                r["%s_sobre_ma200" % idx] = s.iloc[-1] > ma200
        r["value_vs_growth"] = {
            "vtv_6m": self.v6("VTV"),
            "vug_6m": self.v6("VUG"),
            "value_lidera": self.v6("VTV") > self.v6("VUG"),
        }
        r["defensivas"] = {
            "xlp_spy_6m": self.v6("XLP") - self.v6("SPY"),
            "vnq_spy_6m": self.v6("VNQ") - self.v6("SPY"),
        }
        r["cobre"] = {
            "copper_6m": self.v6("COPPER"),
            "tnx_6m": self.v6("TNX"),
        }
        r["ranking"] = {
            "xlk_6m": self.v6("XLK"),
            "xle_6m": self.v6("XLE"),
        }
        return r


class Capitulo8(CapituloBase):
    TITULO = "Cap.8 - Spring 2003: deflacion y flight to gold"
    TICKERS = {
        "DXY": "DX-Y.NYB", "GOLD": "GC=F", "GDX": "GDX", "CRB": "^SPGSCI",
        "TLT": "TLT", "TNX": "^TNX", "SPY": "SPY", "USO": "USO", "XLE": "XLE",
    }

    def ejecutar(self):
        r = {}
        r["oro_dolar"] = {
            "dxy_6m": self.v6("DXY"),
            "gold_6m": self.v6("GOLD"),
            "corr": self.corr("DXY", "GOLD")[1],
        }
        r["gold_stocks"] = {
            "gdx_6m": self.v6("GDX"),
            "gold_6m": self.v6("GOLD"),
            "gdx_gold_slope200": self.ratio_slope("GDX", "GOLD", 200),
        }
        r["bonos_comm"] = {
            "tlt_6m": self.v6("TLT"),
            "crb_6m": self.v6("CRB"),
            "corr": self.corr("TLT", "CRB")[1],
        }
        r["acciones_comm"] = {
            "spy_crb_corr": self.corr("SPY", "CRB")[1],
        }
        r["bonos_acciones"] = {
            "tlt_spy_corr": self.corr("TLT", "SPY")[1],
        }
        r["clima_deflacionario"] = {
            "dxy_6m": self.v6("DXY"),
            "spy_6m": self.v6("SPY"),
            "tnx_nivel": self.precio("TNX"),
            "gold_6m": self.v6("GOLD"),
            "activo": self.v6("DXY") < 0 and self.v6("SPY") < 0,
        }
        return r


class Capitulo9(CapituloBase):
    TITULO = "Cap.9 - 2002: dolar debil impulsa commodities"
    TICKERS = {
        "DXY": "DX-Y.NYB", "CRB": "^SPGSCI", "TNX": "^TNX", "SPY": "SPY",
        "TLT": "TLT", "GOLD": "GC=F", "N225": "^N225", "EFA": "EFA", "ACWI": "ACWI",
        "DBA": "DBA", "HG": "HG=F",
    }

    def ejecutar(self):
        r = {}
        r["dolar_comm"] = {
            "dxy_6m": self.v6("DXY"),
            "crb_6m": self.v6("CRB"),
            "corr": self.corr("DXY", "CRB")[1],
        }
        r["bonos_comm"] = {
            "tnx_6m": self.v6("TNX"),
            "crb_6m": self.v6("CRB"),
            "corr": self.corr("TNX", "CRB")[1],
            "decoupling": self.corr("TNX", "CRB")[1] is not None and self.corr("TNX", "CRB")[1] < -0.1,
        }
        r["divergencia_agri_metales"] = {
            "dba_6m": self.v6("DBA"),
            "hg_6m": self.v6("HG"),
        }
        r["metales_tasas"] = {
            "hg_6m": self.v6("HG"),
            "tnx_6m": self.v6("TNX"),
            "corr": self.corr("HG", "TNX")[1],
        }
        r["japon_tasas"] = {
            "n225_6m": self.v6("N225"),
            "tnx_6m": self.v6("TNX"),
            "corr": self.corr("N225", "TNX")[1],
        }
        r["bear_global"] = {
            "spy_efa": self.corr("SPY", "EFA")[1],
            "spy_acwi": self.corr("SPY", "ACWI")[1],
        }
        r["deflacion_stocks_tasas"] = {
            "spy_6m": self.v6("SPY"),
            "tnx_6m": self.v6("TNX"),
            "ambos_cae": self.v6("SPY") < 0 and self.v6("TNX") < 0,
        }
        r["dolar_oro"] = {
            "dxy_6m": self.v6("DXY"),
            "gold_6m": self.v6("GOLD"),
        }
        return r


class Capitulo10(CapituloBase):
    TITULO = "Cap.10 - Giro de papel a hard assets"
    TICKERS = {
        "DXY": "DX-Y.NYB", "GOLD": "GC=F", "SPY": "SPY", "CRB": "^SPGSCI",
        "GDX": "GDX", "FXE": "FXE", "FXA": "FXA", "FXC": "FXC", "FXY": "FXY",
        "FXB": "FXB", "XLE": "XLE", "XLB": "XLB", "HG": "HG=F",
    }

    def ejecutar(self):
        r = {}
        r["oro_proxy_comm"] = {
            "gold_6m": self.v6("GOLD"),
            "crb_6m": self.v6("CRB"),
            "corr": self.corr("GOLD", "CRB")[1],
            "gold_crb_slope200": self.ratio_slope("GOLD", "CRB", 200),
        }
        r["oro_vs_acciones"] = {
            "gold_6m": self.v6("GOLD"),
            "spy_6m": self.v6("SPY"),
            "corr": self.corr("GOLD", "SPY")[1],
        }
        r["crb_spy"] = {
            "crb_spy_slope200": self.ratio_slope("CRB", "SPY", 200),
        }
        r["monedas_comm"] = {
            "aud_crb": self.corr("FXA", "CRB")[1],
            "cad_crb": self.corr("FXC", "CRB")[1],
        }
        r["dolar_divisas_oro"] = {
            "dxy_eur": self.corr("DXY", "FXE")[1],
            "eur_gold": self.corr("FXE", "GOLD")[1],
            "dxy_gold": self.corr("DXY", "GOLD")[1],
        }
        r["gold_stocks"] = {
            "gdx_1y": self.v1y("GDX"),
            "gold_1y": self.v1y("GOLD"),
            "gdx_gold_slope200": self.ratio_slope("GDX", "GOLD", 200),
        }
        r["acciones_comm"] = {
            "xle_crb": self.corr("XLE", "CRB")[1],
            "xlb_crb": self.corr("XLB", "CRB")[1],
            "xlb_hg": self.corr("XLB", "HG")[1],
        }
        return r


class Capitulo11(CapituloBase):
    TITULO = "Cap.11 - Asset allocation con ratios"
    TICKERS = {
        "DXY": "DX-Y.NYB", "GOLD": "GC=F", "CRB": "^SPGSCI", "SPY": "SPY",
        "TLT": "TLT", "DJI": "^DJI", "TNX": "^TNX", "GDX": "GDX",
        "FXE": "FXE", "FXY": "FXY", "FXB": "FXB", "FXC": "FXC",
    }

    def _ratio_ret(self, num, den, dias):
        if num not in self.datos or den not in self.datos:
            return None
        rn = self.datos[num].iloc[-1] / self.datos[num].iloc[-dias]
        rd = self.datos[den].iloc[-1] / self.datos[den].iloc[-dias]
        return (rn / rd - 1) * 100

    def ejecutar(self):
        r = {}
        r["bonos_vs_stocks"] = {
            "tlt_spy_slope200": self.ratio_slope("TLT", "SPY", 200),
            "tlt_6m": self.v6("TLT"),
            "spy_6m": self.v6("SPY"),
        }
        st = self.ratio_stats("CRB", "TLT", 200)
        r["comm_vs_bonos"] = {
            "crb_tlt_slope200": self.ratio_slope("CRB", "TLT", 200),
            "crb_tlt_pct200": st["pct"] if st else None,
        }
        r["dow_gold"] = {
            "dji_gold_slope200": self.ratio_slope("DJI", "GOLD", 200),
            "dji_gold_6m": self._ratio_ret("DJI", "GOLD", 126),
        }
        r["oro_divisas_1y"] = {
            "gbp": self._ratio_ret("GOLD", "FXB", 252),
            "cad": self._ratio_ret("GOLD", "FXC", 252),
            "jpy": self._ratio_ret("GOLD", "FXY", 252),
            "eur": self._ratio_ret("GOLD", "FXE", 252),
        }
        r["diversificacion"] = {
            "spy_tlt": self.corr("SPY", "TLT")[1],
            "crb_tlt": self.corr("CRB", "TLT")[1],
            "crb_spy": self.corr("CRB", "SPY")[1],
        }
        return r


class Capitulo12(CapituloBase):
    TITULO = "Cap.12 - Ciclo de negocios"
    TICKERS = {
        "TLT": "TLT", "SPY": "SPY", "CRB": "^SPGSCI", "GOLD": "GC=F",
        "DXY": "DX-Y.NYB", "TNX": "^TNX",
    }

    def ejecutar(self):
        tlt6, spy6, crb6 = self.v6("TLT"), self.v6("SPY"), self.v6("CRB")
        if tlt6 is None or spy6 is None or crb6 is None:
            return {}
        if tlt6 > 0 and spy6 < 0:
            etapa = "Stage 1 (recuperacion: bonos suben)"
        elif spy6 > 0 and crb6 < 0:
            etapa = "Stage 2 (acciones suben)"
        elif tlt6 > 0 and spy6 > 0 and crb6 > 0:
            etapa = "Stage 3 (todos suben)"
        elif tlt6 < 0 and spy6 > 0 and crb6 > 0:
            etapa = "Stage 4 (bonos caen, acciones/comm suben)"
        elif tlt6 < 0 and spy6 < 0 and crb6 > 0:
            etapa = "Stage 5 (acciones caen, comm suben)"
        elif tlt6 < 0 and spy6 < 0 and crb6 < 0:
            etapa = "Stage 6 (todos caen)"
        else:
            etapa = "mixta"
        return {
            "etapa_pring": etapa,
            "tlt_6m": tlt6, "spy_6m": spy6, "crb_6m": crb6,
            "tlt_spy_corr": self.corr("TLT", "SPY")[1],
            "spy_crb_corr": self.corr("SPY", "CRB")[1],
            "dxy_gold_corr": self.corr("DXY", "GOLD")[1],
        }


class Capitulo13(CapituloBase):
    TITULO = "Cap.13 - Rotacion sectorial"
    TICKERS = {
        "SPY": "SPY", "XLB": "XLB", "XLE": "XLE", "XLF": "XLF", "XLI": "XLI",
        "XLK": "XLK", "XLP": "XLP", "XLU": "XLU", "XLV": "XLV", "XLY": "XLY",
        "IYT": "IYT", "IWM": "IWM", "QQQ": "QQQ", "DJI": "^DJI",
        "IRX": "^IRX", "TNX": "^TNX",
    }

    def cargar(self):
        # ^IRX con 6y devuelve 14 filas por bug yfinance; usar 5y para este ticker.
        super().cargar()
        if "IRX" in self.TICKERS:
            try:
                self.datos["IRX"] = load("^IRX", period="5y")
            except Exception as e:
                if self.verbose:
                    print("  [!] IRX (5y): %s" % e)
        return self

    def ejecutar(self):
        r = {}
        sectores = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
        liderazgo = {}
        for s in sectores:
            if s in self.datos:
                liderazgo[s] = self.ratio_slope(s, "SPY", 200)
        r["liderazgo_sectorial_200d"] = dict(sorted(liderazgo.items(), key=lambda x: -x[1] if x[1] else 0))
        r["ciclicos_vs_staples"] = {"xly_xlp_slope200": self.ratio_slope("XLY", "XLP", 200)}
        r["tech"] = {
            "xlk_spy_slope200": self.ratio_slope("XLK", "SPY", 200),
            "qqq_spy_slope200": self.ratio_slope("QQQ", "SPY", 200),
        }
        r["transports"] = {"iyt_dji_slope200": self.ratio_slope("IYT", "DJI", 200)}
        r["small_caps"] = {"iwm_spy_slope200": self.ratio_slope("IWM", "SPY", 200)}
        r["yield_curve"] = {
            "irx": self.precio("IRX"),
            "tnx": self.precio("TNX"),
            "spread": (self.precio("TNX") - self.precio("IRX")) if self.precio("TNX") and self.precio("IRX") else None,
            "irx_tnx_slope200": self.ratio_slope("IRX", "TNX", 200),
        }
        return r


class Capitulo14(CapituloBase):
    TITULO = "Cap.14 - Real estate"
    TICKERS = {
        "VNQ": "VNQ", "XHB": "XHB", "QQQ": "QQQ", "SPY": "SPY",
        "TNX": "^TNX", "TLT": "TLT",
    }

    def ejecutar(self):
        return {
            "reits_tech": {
                "vnq_6m": self.v6("VNQ"),
                "qqq_6m": self.v6("QQQ"),
                "corr": self.corr("VNQ", "QQQ")[1],
            },
            "reits_tasas": {
                "vnq_6m": self.v6("VNQ"),
                "tnx_6m": self.v6("TNX"),
                "corr": self.corr("VNQ", "TNX")[1],
            },
            "reits_spy": {
                "vnq_spy_slope200": self.ratio_slope("VNQ", "SPY", 200),
                "vnq_1y": self.v1y("VNQ"),
                "spy_1y": self.v1y("SPY"),
            },
            "homebuilders_tasas": {
                "xhb_6m": self.v6("XHB"),
                "tnx_6m": self.v6("TNX"),
                "corr": self.corr("XHB", "TNX")[1],
            },
        }


class Capitulo15(CapituloBase):
    TITULO = "Cap.15 - Thinking globally"
    TICKERS = {
        "SPY": "SPY", "EFA": "EFA", "ACWI": "ACWI", "EEM": "EEM",
        "CRB": "^SPGSCI", "DXY": "DX-Y.NYB", "N225": "^N225", "TNX": "^TNX",
        "TLT": "TLT", "FXA": "FXA", "FXC": "FXC", "GOLD": "GC=F",
    }

    def ejecutar(self):
        return {
            "global": {
                "spy_efa": self.corr("SPY", "EFA")[1],
                "spy_acwi": self.corr("SPY", "ACWI")[1],
                "spy_eem": self.corr("SPY", "EEM")[1],
            },
            "emergentes": {
                "eem_6m": self.v6("EEM"),
                "eem_crb": self.corr("EEM", "CRB")[1],
                "eem_dxy": self.corr("EEM", "DXY")[1],
            },
            "dolar_bloc": {
                "aud_crb": self.corr("FXA", "CRB")[1],
                "cad_crb": self.corr("FXC", "CRB")[1],
            },
            "decoupling": {
                "spy_tlt": self.corr("SPY", "TLT")[1],
            },
            "japon": {
                "n225_6m": self.v6("N225"),
                "tnx_6m": self.v6("TNX"),
                "corr": self.corr("N225", "TNX")[1],
            },
            "post_boom": {
                "spy_6y_total": (self.datos["SPY"].iloc[-1] / self.datos["SPY"].iloc[0] - 1) * 100 if "SPY" in self.datos else None,
            },
            "ancla_oro": {
                "dxy_gold": self.corr("DXY", "GOLD")[1],
                "crb_gold": self.corr("CRB", "GOLD")[1],
            },
        }