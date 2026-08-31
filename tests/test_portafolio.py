# -*- coding: utf-8 -*-
"""Tests basicos para el modulo de portafolio."""
import json
import os
import sys
import unittest
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analisis.portafolio.analizador import (
    MAPEO_TICKER_SENAL,
    SECTOR_A_ETF,
    analizar_cuenta,
    buscar_senal,
    cargar_senales,
    generar_informe,
)
from analisis.portafolio.rebalanceo import (
    TARGETS,
    analisis_rebalanceo,
    categoria,
    generar_informe_rebalanceo,
)
from analisis.portafolio.constructor import (
    ETF_A_SECTOR,
    extraer_candidatos,
    filtrar_por_liquidez,
    metricas_riesgo_retorno,
    optimizar_max_sharpe,
    sectores_beneficiados,
)
from analisis.portafolio.noticias import score_sentiment, analizar_noticias, agregar_score_noticias
from analisis.ejecutivo.noticias_ciclo import (
    DRIVERS,
    CLAIMS,
    temas_detectados,
    verificar_regimen,
)
from analisis.portafolio.backtest_constructor import (
    optimizar_max_sharpe as optimizar_max_sharpe_bt,
    backtest_portafolio,
)
from analisis.portafolio.visualizaciones import (
    plot_cumulative_and_drawdown,
    plot_efficient_frontier,
    plot_weights,
)


CUENTA_MUESTRA = {
    "nombre": "Test",
    "perfil": "Moderado",
    "patrimonio_usd": 10000.0,
    "moneda_base": "ARS",
    "cash": {"USD": 1000.0, "ARS": 500000.0, "USD_C": 0},
    "tenencias": [
        {"ticker": "SPY", "tipo": "cedear", "cantidad": 10, "pp": 1000, "ultimo": 1100,
         "monto_ars": 1100000, "sector": "Benchmark"},
        {"ticker": "MP", "tipo": "cedear", "cantidad": 5, "pp": 100, "ultimo": 120,
         "monto_ars": 60000, "sector": "Materiales"},
    ],
}


class TestAnalizador(unittest.TestCase):

    def test_mapeo_completo(self):
        self.assertIn("SPY", MAPEO_TICKER_SENAL)
        self.assertIn("AMZN", MAPEO_TICKER_SENAL)

    def test_cargar_senales(self):
        senales = cargar_senales()
        self.assertIn("AA1", senales)
        self.assertIn("regla_oro", senales["AA1"])

    def test_buscar_senal(self):
        senales = cargar_senales()
        s = buscar_senal("SPY", senales)
        self.assertIsNotNone(s)
        self.assertEqual(s["ratio"], "SPY/TLT")

    def test_analizar_cuenta_cash_consistente(self):
        senales = cargar_senales()
        contexto = {"cap12": {"resultados": {"etapa_pring": "Stage 4"}},
                    "cap13": {"resultados": {"liderazgo_sectorial_200d": {"XLE": 1.0, "XLK": 0.5, "XLI": 0.1,
                                                                            "XLV": -0.1, "XLF": -0.2, "XLY": -0.3}}}}
        res = analizar_cuenta(CUENTA_MUESTRA, senales, contexto)
        self.assertEqual(res["nombre"], "Test")
        self.assertAlmostEqual(res["patrimonio_usd"], 10000.0)
        # cash debe incluir USD + ARS al TC implicito
        self.assertGreater(res["cash_usd"], 1000.0)
        self.assertGreater(res["tc_implicito"], 0)
        total_pct = sum(f["pct_total"] for f in res["filas"]) + res["cash_pct"]
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_generar_informe(self):
        with TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "portafolio.json")
            out_path = os.path.join(tmp, "out.md")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"fecha_corte": "2026-08-13", "cuentas": [CUENTA_MUESTRA]}, f)
            contexto = {"cap12": {"resultados": {"etapa_pring": "Stage 4"}},
                        "cap13": {"resultados": {"liderazgo_sectorial_200d": {"XLE": 1.0, "XLK": 0.5, "XLI": 0.1,
                                                                                "XLV": -0.1, "XLF": -0.2, "XLY": -0.3}}}}
            texto = generar_informe(json_path, out_path, contexto=contexto)
            self.assertIn("Test", texto)
            self.assertTrue(os.path.exists(out_path))


class TestRebalanceo(unittest.TestCase):

    def test_categoria(self):
        self.assertEqual(categoria("Tecnologia"), "Tecnologia")
        self.assertEqual(categoria("Desconocido"), "Otros")

    def test_targets_suman_cien(self):
        for perfil, targets in TARGETS.items():
            self.assertAlmostEqual(sum(targets.values()), 1.0, places=2,
                                   msg="%s no suma 100%%" % perfil)

    def test_analisis_rebalanceo(self):
        senales = cargar_senales()
        contexto = {"cap12": {"resultados": {"etapa_pring": "Stage 4"}},
                    "cap13": {"resultados": {"liderazgo_sectorial_200d": {"XLE": 1.0, "XLK": 0.5, "XLI": 0.1,
                                                                            "XLV": -0.1, "XLF": -0.2, "XLY": -0.3}}}}
        res = analisis_rebalanceo(CUENTA_MUESTRA, senales, contexto)
        self.assertEqual(res["perfil"], "Moderado")
        self.assertAlmostEqual(res["patrimonio_usd"], 10000.0)
        self.assertTrue(len(res["sectores"]) > 0)
        # Con tolerancia default puede no haber operaciones; forzamos baja tolerancia para validar logica
        res2 = analisis_rebalanceo(CUENTA_MUESTRA, senales, contexto, tolerancia=0.005)
        self.assertTrue(any(op["ticker"] in ("SPY", "MP") for op in res2["operaciones"]))

    def test_generar_informe_rebalanceo(self):
        with TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "portafolio.json")
            out_path = os.path.join(tmp, "out.md")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"fecha_corte": "2026-08-13", "cuentas": [CUENTA_MUESTRA]}, f)
            contexto = {"cap12": {"resultados": {"etapa_pring": "Stage 4"}},
                        "cap13": {"resultados": {"liderazgo_sectorial_200d": {"XLE": 1.0, "XLK": 0.5, "XLI": 0.1,
                                                                                "XLV": -0.1, "XLF": -0.2, "XLY": -0.3}}}}
            texto = generar_informe_rebalanceo(json_path, out_path, contexto=contexto)
            self.assertIn("Plan de Rebalanceo", texto)
            self.assertTrue(os.path.exists(out_path))


class TestConstructor(unittest.TestCase):

    def test_etf_a_sector(self):
        self.assertEqual(ETF_A_SECTOR["XLE"], "Energía")
        self.assertEqual(ETF_A_SECTOR["XLK"], "Tecnología")

    def test_sectores_beneficiados(self):
        contexto = {"cap13": {"resultados": {"liderazgo_sectorial_200d": {"XLE": 1.0, "XLK": 0.5, "XLI": 0.1,
                                                                            "XLV": -0.1, "XLF": -0.2, "XLY": -0.3}}}}
        sectores = sectores_beneficiados(contexto, top_n=3)
        self.assertEqual(len(sectores), 3)
        self.assertIn("Energía", sectores)

    def test_extraer_candidatos(self):
        unificado = {
            "sectores": {
                "Energía": {
                    "industrias": {
                        "Oil": [
                            {"ticker": "XOM", "tipo": "cedear", "moneda": "ARS", "pais": "EE.UU.", "nombre": "Exxon"},
                            {"ticker": "XOMD", "tipo": "cedear", "moneda": "USD", "pais": "EE.UU.", "nombre": "Exxon USD"},
                        ]
                    },
                    "etfs": [],
                }
            }
        }
        cands = extraer_candidatos(unificado, ["Energía"])
        self.assertIn("XOM.BA", [c["ticker_ars"] for c in cands["Energía"]["ars"]])
        self.assertIn("XOM", [c["ticker_usd"] for c in cands["Energía"]["usd"]])

    def test_metricas_riesgo_retorno(self):
        s = pd.Series([100 * (1 + 0.001 * i + np.random.normal(0, 0.01)) for i in range(50)])
        m = metricas_riesgo_retorno(s, risk_free_annual=0.0, factor=252)
        self.assertIsNotNone(m)
        self.assertGreater(m["volatilidad_annual"], 0)
        self.assertTrue(np.isfinite(m["sharpe"]))

    def test_optimizar_max_sharpe(self):
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100)
        rets = pd.DataFrame({
            "A": np.random.normal(0.001, 0.02, 100),
            "B": np.random.normal(0.0005, 0.015, 100),
            "C": np.random.normal(0.0002, 0.01, 100),
        }, index=dates)
        opt = optimizar_max_sharpe(rets, risk_free_annual=0.0)
        self.assertIsNotNone(opt)
        self.assertEqual(len(opt["pesos"]), 3)
        self.assertAlmostEqual(sum(opt["pesos"]), 1.0, places=4)
        self.assertTrue(all(w >= -1e-6 for w in opt["pesos"]))
        self.assertEqual(len(opt["tickers"]), 3)


class TestNoticias(unittest.TestCase):

    def test_score_sentiment_positivo(self):
        self.assertEqual(score_sentiment("Apple reports strong earnings and profit growth"), 1)

    def test_score_sentiment_negativo(self):
        self.assertEqual(score_sentiment("Company misses estimates and warns of recession"), -1)

    def test_score_sentiment_neutro(self):
        self.assertEqual(score_sentiment("The stock opened at ten dollars today"), 0)

    def test_agregar_score_noticias(self):
        df = pd.DataFrame({"ticker": ["AAPL"], "nombre": ["Apple"]})
        df_out = agregar_score_noticias(df, max_items=5, verbose=False)
        self.assertIn("news_score", df_out.columns)
        self.assertIn("news_count", df_out.columns)
        self.assertEqual(len(df_out), 1)


class TestNoticiasCiclo(unittest.TestCase):

    def test_drivers_definidos(self):
        self.assertTrue(len(DRIVERS) > 0)
        self.assertTrue(all(d["ticker"] for d in DRIVERS))
        self.assertTrue(all(d["dimension"] for d in DRIVERS))

    def test_temas_detectados_tasas(self):
        temas = temas_detectados("Fed signals hawkish stance as 10-year treasury yields jump")
        self.assertIn("tasas", temas)

    def test_temas_detectados_multitema(self):
        temas = temas_detectados("Gold rises on dollar weakness and geopolitical war risk")
        self.assertIn("oro", temas)
        self.assertIn("dolar", temas)
        self.assertIn("geopolitica", temas)

    def test_temas_detectados_vacio(self):
        self.assertEqual(temas_detectados(""), [])

    def test_verificar_regimen_confirma(self):
        df = pd.DataFrame({
            "ticker": ["^TNX"],
            "dimension": ["tasas"],
            "sentimiento": [1],
            "temas": ["tasas,inflacion"],
        })
        ctx = {"cap3": {"resultados": {"shock_tasas": {"alerta_1994": True}}}}
        coh = verificar_regimen(df, ctx)
        fila = coh[coh["claim"].str.contains("Shock de tasas")].iloc[0]
        self.assertEqual(fila["activo"], "SI")
        self.assertIn("CONFIRMA", fila["veredicto"])

    def test_claim_estado_inactivo(self):
        df = pd.DataFrame({"ticker": [], "dimension": [], "sentimiento": [], "temas": []})
        ctx = {"cap3": {"resultados": {"shock_tasas": {"alerta_1994": False}}}}
        coh = verificar_regimen(df, ctx)
        fila = coh[coh["claim"].str.contains("Shock de tasas")].iloc[0]
        self.assertEqual(fila["activo"], "NO")


class TestBacktest(unittest.TestCase):

    def test_optimizar_max_sharpe(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100)
        rets = pd.DataFrame({
            "A": np.random.normal(0.001, 0.02, 100),
            "B": np.random.normal(0.0005, 0.015, 100),
        }, index=dates)
        pesos = optimizar_max_sharpe_bt(rets, risk_free_annual=0.0)
        self.assertIsNotNone(pesos)
        self.assertIn("A", pesos)
        self.assertIn("B", pesos)
        self.assertAlmostEqual(sum(pesos.values()), 1.0, places=4)

    def test_backtest_portafolio_sintetico(self):
        np.random.seed(7)
        dates = pd.date_range("2024-01-01", periods=200)
        prices = pd.DataFrame({
            "A": 100 * (1 + np.random.normal(0.0008, 0.015, 200)).cumprod(),
            "B": 100 * (1 + np.random.normal(0.0003, 0.01, 200)).cumprod(),
            "SPY": 100 * (1 + np.random.normal(0.0005, 0.012, 200)).cumprod(),
        }, index=dates)
        # No podemos mockear yfinance facilmente; testeamos la logica con retornos directos
        from analisis.portafolio.backtest_constructor import optimizar_max_sharpe
        mid = 150
        rets_train = prices.iloc[:mid].pct_change().dropna()
        rets_test = prices.iloc[mid:].pct_change().dropna()
        pesos = optimizar_max_sharpe(rets_train[["A", "B"]], risk_free_annual=0.0)
        self.assertIsNotNone(pesos)
        w = np.array([pesos["A"], pesos["B"]])
        pf_rets = rets_test[["A", "B"]].dot(w)
        self.assertEqual(len(pf_rets), len(rets_test))


class TestVisualizaciones(unittest.TestCase):

    def test_plot_efficient_frontier(self):
        np.random.seed(1)
        rets = pd.DataFrame({
            "A": np.random.normal(0.001, 0.02, 100),
            "B": np.random.normal(0.0005, 0.015, 100),
        })
        with TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "frontier.png")
            ok = plot_efficient_frontier(rets, {"A": 0.6, "B": 0.4}, out)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 0)

    def test_plot_weights(self):
        with TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "weights.png")
            ok = plot_weights({"A": 0.7, "B": 0.25, "C": 0.05}, out)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(out))

    def test_plot_cumulative_and_drawdown(self):
        np.random.seed(2)
        dates = pd.date_range("2024-01-01", periods=60)
        pf = pd.Series(np.random.normal(0.0005, 0.01, 60), index=dates)
        bm = pd.Series(np.random.normal(0.0004, 0.009, 60), index=dates)
        with TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "cumdd.png")
            ok = plot_cumulative_and_drawdown(pf, bm, out)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()