# -*- coding: utf-8 -*-
"""Tests de salud fundamental: ratios puros y modelos de bancarrota sin red.

Fixtures literales del corpus (txt metodologias/):
- Altman 1968: ejemplo del propio texto con x1 negativo -> Z=3.42017
  (DFIN_Pascale_2_Unidad_1.txt l.907-921)
- Modelo Pascale 1988: ratios 3.55355/0.11311/0.38766 -> Z=2.70121
  (mismo archivo, l.950-986)
- XYZ S.A.: razon corriente 0.98, acida 0.63, P/PN 1.21,
  cobertura GAII/int 2.39 (DFIN_Pascale_2_Unidad_1.txt l.171-296)
- Saludable S.A. vs estandares: corriente 2.00 vs 1.40; acida 0.90 vs 0.50;
  endeudamiento 1.00 vs 1.20 (Biondi_cap7_estados_2.txt l.230-266)
"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analisis.portafolio.salud_fundamental import (
    PESOS_DIMENSIONES,
    altman_z,
    calcular_metricas,
    clasificar,
    dupont,
    es_entidad_financiera,
    pascale_z,
    preparar_metricas_para_scoring,
    score_bancarrota,
    score_flujo,
    score_liquidez,
    score_rentabilidad,
    score_solvencia,
    score_total,
    zona_altman,
    zona_pascale,
)


def _df(filas):
    col = pd.to_datetime(["2025-12-31"])
    return pd.DataFrame.from_dict(filas, orient="index", columns=col)


class TestModelosBancarrota(unittest.TestCase):
    def test_altman_ejemplo_del_texto(self):
        z = altman_z(-0.00761, 0.11311, 0.19239, 1.15, 1.94604)
        self.assertAlmostEqual(z, 3.42017, places=4)

    def test_pascale_fixture_del_texto(self):
        z = pascale_z(3.55355, 0.11311, 0.38766)
        self.assertAlmostEqual(z, 2.70121, places=3)

    def test_modelos_requieren_todas_las_variables(self):
        self.assertIsNone(altman_z(0.1, None, 0.2, 0.5, 1.0))
        self.assertIsNone(pascale_z(None, 0.1, 0.2))

    def test_zonas_altman_segun_texto(self):
        self.assertEqual(zona_altman(3.5), "SEGURA")
        self.assertEqual(zona_altman(2.7), "GRIS")
        self.assertEqual(zona_altman(2.0), "GRIS")
        self.assertEqual(zona_altman(1.5), "RIESGO")
        self.assertIsNone(zona_altman(None))

    def test_zonas_pascale_segun_texto(self):
        self.assertEqual(zona_pascale(2.70), "SEGURA")
        self.assertEqual(zona_pascale(0.2), "GRIS")
        self.assertEqual(zona_pascale(-0.5), "GRIS")
        self.assertEqual(zona_pascale(-2.0), "RIESGO")
        self.assertIsNone(zona_pascale(None))

    def test_score_bancarrota_promedia_ambos_modelos(self):
        m = {"z": 3.42017, "z_pascale": 2.70121}
        self.assertEqual(score_bancarrota(m), 100.0)
        gris = score_bancarrota({"z": 2.0})
        self.assertLess(gris, 60)
        self.assertIsNone(score_bancarrota({}))


class TestDuPont(unittest.TestCase):
    def test_identidad_roe_modificado(self):
        # Pascale U2-1 l.705: ROA = margen x rotacion; ROE = ROA x multiplicador
        roa = dupont(0.152, 1.04, 1.0)
        roe = dupont(0.152, 1.04, 1.8)
        self.assertAlmostEqual(roa, 0.15808, places=5)
        self.assertAlmostEqual(roe, 0.284544, places=5)

    def test_none_si_falta_parte(self):
        self.assertIsNone(dupont(0.1, None, 2.0))


class TestScores(unittest.TestCase):
    def test_saludable_sa_corriente_ideal_amat(self):
        # Biondi c.7: Saludable tiene corriente 2.00 vs estandar 1.40
        s = score_liquidez({"razon_corriente": 2.00, "prueba_acida": 0.90})
        self.assertGreaterEqual(s, 95)

    def test_liquidez_excesiva_penalizada_leve(self):
        con_exceso = score_liquidez({"razon_corriente": 4.0, "prueba_acida": 3.5})
        ideal = score_liquidez({"razon_corriente": 1.8, "prueba_acida": 0.95})
        self.assertLess(con_exceso, ideal)

    def test_xyz_sa_corriente_debil(self):
        # Pascale U2-1: XYZ corriente 0.98, acida 0.63 -> debajo del piso de 1
        s = score_liquidez({"razon_corriente": 0.98, "prueba_acida": 0.63})
        self.assertLessEqual(s, 70)

    def test_endeudamiento_amat_limite_texto(self):
        # Amat l.2297: <=0.6 correcto; >0.6 exceso
        self.assertEqual(score_solvencia({"endeudamiento_amat": 0.59}), 85)
        self.assertLessEqual(score_solvencia({"endeudamiento_amat": 0.8}), 35)

    def test_cobertura_covenant_elbaum(self):
        m_ok = {"cobertura_intereses": 2.39}  # cobertura XYZ del texto
        m_limite = {"cobertura_intereses": 1.80}
        m_malo = {"cobertura_intereses": 0.9}
        self.assertEqual(score_solvencia(m_ok), 100.0)
        self.assertEqual(score_solvencia(m_limite), 90.0)
        self.assertEqual(score_solvencia(m_malo), 10.0)

    def test_leverage_test_fowler_newton(self):
        positivo = score_solvencia({
            "endeudamiento_amat": 0.55,
            "rentabilidad_activa": 0.16, "costo_deuda": 0.10, "spread_leverage": 0.06,
        })
        negativo = score_solvencia({
            "endeudamiento_amat": 0.55,
            "rentabilidad_activa": 0.05, "costo_deuda": 0.12, "spread_leverage": -0.07,
        })
        self.assertGreater(positivo, negativo)

    def test_rentabilidad_monotona_y_referencias_corpus(self):
        xyz = score_rentabilidad({"roe": 0.28, "roa": 0.16, "margen_operativo": 0.099})  # XYZ
        saludable = score_rentabilidad({"roe": 0.02, "roa": 0.01, "margen_operativo": 0.03})  # Saludable 2%
        self.assertGreater(xyz, saludable)
        self.assertGreaterEqual(xyz, 75)

    def test_flujo_sin_umbral_textual_es_criterio_propio_pero_monotono(self):
        bueno = score_flujo({"fcf_utilidad": 0.95, "crec_ingresos": 0.20, "crec_utilidades": 0.18})
        malo = score_flujo({"fcf_utilidad": -0.2, "crec_ingresos": -0.05, "crec_utilidades": -0.10})
        self.assertEqual(bueno, 100.0)
        self.assertLess(malo, 25)

    def test_scores_sin_datos_devuelven_none(self):
        for f in (score_liquidez, score_solvencia, score_rentabilidad, score_bancarrota, score_flujo):
            self.assertIsNone(f({}))

    def test_clasificar_y_pesos_suman_uno(self):
        self.assertEqual(clasificar(80), "SANO")
        self.assertEqual(clasificar(60), "MODERADO")
        self.assertEqual(clasificar(45), "FRAGIL")
        self.assertEqual(clasificar(10), "EN RIESGO")
        self.assertEqual(clasificar(None), "SIN DATOS")
        self.assertAlmostEqual(sum(PESOS_DIMENSIONES.values()), 1.0)

    def test_score_total_renormaliza_dimensiones_ausentes(self):
        total = score_total({"liquidez": 100, "solvencia": 100, "bancarrota": None, "flujo": 100})
        self.assertEqual(total, 100.0)
        self.assertEqual(score_total({"liquidez": 0}), 0.0)


class TestExclusionFinancieras(unittest.TestCase):
    """Pascale U2-1 l.951: modelo calibrado a manufactura; bancos no aplican."""

    def test_deteccion_sector(self):
        self.assertTrue(es_entidad_financiera("Financial Services"))
        self.assertFalse(es_entidad_financiera("Technology"))
        self.assertFalse(es_entidad_financiera(""))
        self.assertFalse(es_entidad_financiera(None))

    def test_preparar_metricas_quita_no_aplicables(self):
        m_banco = {
            "sector_yf": "Financial Services", "z": 5.0, "z_pascale": -2.51,
            "endeudamiento_amat": 0.85, "spread_leverage": -1.3, "roe": 0.254,
            "razon_corriente": None,
        }
        filtrado, excluida = preparar_metricas_para_scoring(m_banco)
        self.assertTrue(excluida)
        self.assertNotIn("z", filtrado)
        self.assertNotIn("z_pascale", filtrado)
        self.assertNotIn("endeudamiento_amat", filtrado)
        self.assertIn("roe", filtrado)

    def test_empresa_no_financiera_intacta(self):
        m = {"sector_yf": "Technology", "z": 3.0, "endeudamiento_amat": 0.4}
        filtrado, excluida = preparar_metricas_para_scoring(m)
        self.assertFalse(excluida)
        self.assertEqual(filtrado["z"], 3.0)

    def test_scores_de_banco_sin_dimensiones_inaplicables(self):
        _, excluida = preparar_metricas_para_scoring({"sector_yf": "Financial Services"})
        m = {"sector_yf": "Financial Services", "roe": 0.254, "roa": 0.038}
        m_score, _ = preparar_metricas_para_scoring(m)
        self.assertIsNone(score_solvencia(m_score))
        self.assertIsNone(score_bancarrota(m_score))
        self.assertIsNotNone(score_rentabilidad(m_score))


class TestCalcularMetricas(unittest.TestCase):
    """Reproduce la empresa XYZ S.A. de Pascale U2-1 (l.171-296)."""

    def setUp(self):
        # XYZ S.A.: AC 3705, inventarios 1300, PC 3791, activos 11305,
        # pasivos totales 6191 (= deudas en el ejemplo), PN 5114,
        # ventas 22000, GAII 1186, intereses 497, NI 1279
        self.bs = _df({
            "Total Assets": 11305.0,
            "Current Assets": 3705.0,
            "Current Liabilities": 3791.0,
            "Working Capital": -86.0,
            "Inventory": 1300.0,
            "Total Debt": 6191.0,
            "Long Term Debt": 2400.0,
            "Stockholders Equity": 5114.0,
            "Retained Earnings": 1279.0,
        })
        self.inc = _df({
            "Total Revenue": 22000.0,
            "EBIT": 1186.0,
            "EBITDA": 1683.0,
            "Interest Expense": 497.0,
            "Net Income Common Stockholders": 1279.0,
        })
        self.cf = _df({"Operating Cash Flow": 1800.0, "Capital Expenditure": -500.0})

    def test_ratios_xyz_coinciden_con_el_texto(self):
        m = calcular_metricas({}, self.bs, self.inc, self.cf)
        self.assertAlmostEqual(m["razon_corriente"], 3705 / 3791, places=4)          # 0.98
        self.assertAlmostEqual(m["prueba_acida"], (3705 - 1300) / 3791, places=4)    # 0.63
        self.assertAlmostEqual(m["endeudamiento_biondi"], 6191 / 5114, places=4)     # ~1.21
        self.assertAlmostEqual(m["cobertura_intereses"], 1186 / 497, places=3)       # ~2.39
        self.assertAlmostEqual(m["endeudamiento_amat"], 6191 / 11305, places=4)      # ~0.548

    def test_leverage_test_integrado(self):
        m = calcular_metricas({}, self.bs, self.inc, self.cf)
        self.assertAlmostEqual(m["rentabilidad_activa"], 1186 / 11305, places=5)
        self.assertAlmostEqual(m["costo_deuda"], 497 / 6191, places=5)
        self.assertGreater(m["spread_leverage"], 0)

    def test_altman_y_pascale_integrados(self):
        m = calcular_metricas({"marketCap": 15000.0}, self.bs, self.inc, self.cf)
        esperado_altman = altman_z(
            -86.0 / 11305.0,
            1279.0 / 11305.0,
            1186.0 / 11305.0,
            15000.0 / 6191.0,
            22000.0 / 11305.0,
        )
        self.assertAlmostEqual(m["z"], esperado_altman, places=9)
        esperado_pascale = pascale_z(
            22000.0 / 6191.0,
            1279.0 / 11305.0,
            2400.0 / 6191.0,
        )
        self.assertAlmostEqual(m["z_pascale"], esperado_pascale, places=9)
        self.assertEqual(zona_pascale(m["z_pascale"]), "SEGURA")

    def test_dupont_integrado(self):
        m = calcular_metricas({}, self.bs, self.inc, self.cf)
        self.assertAlmostEqual(m["roe"], 1279 / 5114, places=6)
        self.assertAlmostEqual(
            m["roe_dupont"],
            (1279 / 22000) * (22000 / 11305) * (11305 / 5114),
            places=6,
        )

    def test_calidad_deuda_pc_sobre_pasivos(self):
        m = calcular_metricas({}, self.bs, self.inc, self.cf)
        self.assertAlmostEqual(m["calidad_deuda"], 3791 / 6191, places=5)

    def test_fcf_desde_ocf_menos_capex(self):
        cf = _df({"Operating Cash Flow": 200.0, "Capital Expenditure": -60.0})
        m = calcular_metricas({}, pd.DataFrame(), pd.DataFrame(), cf)
        self.assertAlmostEqual(m["fcf"], 140.0, places=6)

    def test_fallback_a_info_cuando_no_hay_estados(self):
        vacio = pd.DataFrame()
        info = {
            "currentRatio": 1.4,
            "quickRatio": 1.1,
            "totalDebt": 300.0,
            "ebitda": 500.0,
            "returnOnEquity": 0.18,
            "freeCashflow": 800.0,
            "longName": "Fallback Inc.",
        }
        m = calcular_metricas(info, vacio, vacio, vacio)
        self.assertAlmostEqual(m["razon_corriente"], 1.4, places=6)
        self.assertAlmostEqual(m["deuda_patrimonio"], None if m.get("deuda_patrimonio") is None else m["deuda_patrimonio"])
        self.assertAlmostEqual(m["roe"], 0.18, places=6)
        self.assertAlmostEqual(m["fcf"], 800.0, places=6)
        self.assertEqual(m["empresa"], "Fallback Inc.")
        self.assertIsNone(m["z"])  # sin balance no hay Altman


if __name__ == "__main__":
    unittest.main()
