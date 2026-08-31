# -*- coding: utf-8 -*-
"""Clase base para todos los capitulos del libro de Murphy."""
import numpy as np
from core.corr import corr_lag, best_lag
from core.data import load
from core.ratio import ratio_series, window_stats


class CapituloBase:
    """Plantilla reutilizable para aplicar un capitulo de Murphy.

    Uso tipico:
        cap = CapituloX(periodo="6y")
        res = cap.run()
        cap.texto()          # imprime el analisis formateado
    """
    TITULO = ""
    TICKERS = {}  # sobrescribir en cada hija: {"clave": "TICKER"}

    def __init__(self, periodo="6y", verbose=False):
        self.periodo = periodo
        self.verbose = verbose
        self.datos = {}
        self.resultados = {}

    def cargar(self):
        """Carga todos los tickers definidos en TICKERS."""
        self.datos = {}
        for clave, ticker in self.TICKERS.items():
            try:
                self.datos[clave] = load(ticker, period=self.periodo)
            except Exception as e:
                self.datos[clave] = None
                if self.verbose:
                    print("  [!] %s (%s): %s" % (clave, ticker, e))
        return self

    def run(self):
        """Carga datos, ejecuta el analisis y devuelve resultados."""
        self.cargar()
        self.resultados = self._limpia(self.ejecutar())
        return self.resultados

    def _limpia(self, obj):
        """Convierte np.float64 / np.bool_ a tipos nativos de Python."""
        if isinstance(obj, dict):
            return {k: self._limpia(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._limpia(x) for x in obj]
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    def ejecutar(self):
        """Sobrescribir en cada hija. Debe devolver un dict con hallazgos."""
        raise NotImplementedError

    def texto(self):
        """Imprime el titulo y los resultados de forma legible."""
        print("\n" + "=" * 80)
        print(" %s" % self.TITULO)
        print("=" * 80)
        for k, v in self.resultados.items():
            if isinstance(v, dict):
                print("\n-- %s" % k)
                for kk, vv in v.items():
                    print("  %s: %s" % (kk, vv))
            else:
                print("  %s: %s" % (k, v))

    # helpers comunes -----------------------------------------------------
    def variacion(self, clave, dias=126):
        s = self.datos.get(clave)
        if s is None or len(s) <= dias:
            return None
        return (s.iloc[-1] / s.iloc[-dias] - 1) * 100.0

    def v6(self, clave):
        return self.variacion(clave, 126)

    def v1y(self, clave):
        return self.variacion(clave, 252)

    def precio(self, clave):
        s = self.datos.get(clave)
        return None if s is None else float(s.iloc[-1])

    def corr(self, a, b, max_lag=21):
        if a not in self.datos or b not in self.datos:
            return None, None
        return best_lag(corr_lag(self.datos[a], self.datos[b], max_lag=max_lag))

    def ratio_slope(self, num, den, w=200):
        if num not in self.datos or den not in self.datos:
            return None
        r = ratio_series(self.datos[num], self.datos[den])
        st = window_stats(r, w)
        return None if st is None else float(st["slope"])

    def ratio_stats(self, num, den, w=200):
        if num not in self.datos or den not in self.datos:
            return None
        r = ratio_series(self.datos[num], self.datos[den])
        st = window_stats(r, w)
        return st

    def signo_slope(self, slope):
        if slope is None:
            return "n/a"
        if slope > 2:
            return "alcista"
        if slope < -2:
            return "bajista"
        return "plano"

    def etiqueta(self, cond, si="SI", no="NO"):
        return si if cond else no