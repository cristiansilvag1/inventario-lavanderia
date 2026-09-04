#!/usr/bin/env python3
"""
==============================================================================
 SUITE DE PRUEBAS UNITARIAS - LAVANDERÍA INDUSTRIAL (RECETAS POR PROGRAMA)
==============================================================================
"""

import csv
import tempfile
import unittest
from pathlib import Path

from lavanderia_inventario import (
    INSUMO_ACIDO_ACETICO,
    INSUMO_ANTIQUIEBRE,
    INSUMO_BISULFITO,
    INSUMO_BLANQUEADOR,
    INSUMO_CLORO,
    INSUMO_DESINFECTANTE,
    INSUMO_DETERGENTE,
    INSUMO_DISPERSANTE,
    INSUMO_ENZIMA,
    INSUMO_ENZIMA_LIQUIDA,
    INSUMO_HUMECTANTE,
    INSUMO_JABON,
    INSUMO_OXALICO,
    INSUMO_PEROXIDO,
    INSUMO_SECUESTRANTE,
    INSUMO_SODA,
    INSUMO_SUAVIZANTE,
    PROGRAMA_BLEACH,
    PROGRAMA_BLANQUEO,
    PROGRAMA_DESENGOME,
    PROGRAMA_NEUTRALIZADO,
    PROGRAMA_STONE_ENZIMA,
    PROGRAMA_STONE_LIQUIDA,
    actualizar_stock_minimo,
    anular_lote_transaccional,
    calcular_dosificacion,
    exportar_historial_csv,
    get_connection,
    inicializar_base_datos,
    obtener_alertas_stock,
    obtener_historial,
    obtener_stock_dict,
    procesar_lote_transaccional,
    reabastecer_stock,
)


class TestLavanderiaInventario(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_lavanderia.db"
        inicializar_base_datos(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()
    def test_calcular_dosificacion_desengome(self):
        dosis_des = calcular_dosificacion(60.0, PROGRAMA_DESENGOME)
        self.assertIn(INSUMO_HUMECTANTE, dosis_des)
        self.assertIn(INSUMO_DISPERSANTE, dosis_des)
        self.assertIn(INSUMO_ANTIQUIEBRE, dosis_des)

        self.assertEqual(dosis_des[INSUMO_HUMECTANTE]["cantidad"], 150)
        self.assertEqual(dosis_des[INSUMO_DISPERSANTE]["cantidad"], 210)
        self.assertEqual(dosis_des[INSUMO_ANTIQUIEBRE]["cantidad"], 120)

    def test_stone_enzima_polvo_solo_enzima(self):
        dosis_stone = calcular_dosificacion(60.0, PROGRAMA_STONE_ENZIMA)
        self.assertIn(INSUMO_ENZIMA, dosis_stone)
        self.assertNotIn(INSUMO_ANTIQUIEBRE, dosis_stone)
        self.assertNotIn(INSUMO_ACIDO_ACETICO, dosis_stone)

        self.assertEqual(dosis_stone[INSUMO_ENZIMA]["cantidad"], 480)

    def test_stone_enzima_liquida_y_acetico_sin_antiquiebre(self):
        dosis_stone_liq = calcular_dosificacion(60.0, PROGRAMA_STONE_LIQUIDA)
        self.assertIn(INSUMO_ENZIMA_LIQUIDA, dosis_stone_liq)
        self.assertIn(INSUMO_ACIDO_ACETICO, dosis_stone_liq)
        self.assertNotIn(INSUMO_ANTIQUIEBRE, dosis_stone_liq)

        self.assertEqual(dosis_stone_liq[INSUMO_ENZIMA_LIQUIDA]["cantidad"], 300)
        self.assertEqual(dosis_stone_liq[INSUMO_ACIDO_ACETICO]["cantidad"], 150)

    def test_bleach_cloro_y_soda(self):
        dosis_bleach = calcular_dosificacion(60.0, PROGRAMA_BLEACH)
        self.assertIn(INSUMO_CLORO, dosis_bleach)
        self.assertIn(INSUMO_SODA, dosis_bleach)
        self.assertNotIn(INSUMO_ANTIQUIEBRE, dosis_bleach)
        self.assertNotIn(INSUMO_JABON, dosis_bleach)

        self.assertEqual(dosis_bleach[INSUMO_CLORO]["cantidad"], 300)
        self.assertEqual(dosis_bleach[INSUMO_SODA]["cantidad"], 150)

    def test_neutralizado_receta(self):
        dosis_neutro = calcular_dosificacion(60.0, PROGRAMA_NEUTRALIZADO)
        self.assertIn(INSUMO_HUMECTANTE, dosis_neutro)
        self.assertIn(INSUMO_DISPERSANTE, dosis_neutro)
        self.assertIn(INSUMO_BISULFITO, dosis_neutro)
        self.assertIn(INSUMO_OXALICO, dosis_neutro)
        self.assertNotIn(INSUMO_ANTIQUIEBRE, dosis_neutro)

    def test_blanqueo_receta(self):
        dosis_blanq = calcular_dosificacion(60.0, PROGRAMA_BLANQUEO)
        self.assertIn(INSUMO_JABON, dosis_blanq)
        self.assertIn(INSUMO_DISPERSANTE, dosis_blanq)
        self.assertIn(INSUMO_SECUESTRANTE, dosis_blanq)
        self.assertIn(INSUMO_SODA, dosis_blanq)
        self.assertIn(INSUMO_PEROXIDO, dosis_blanq)
        self.assertIn(INSUMO_BLANQUEADOR, dosis_blanq)

    def test_inicializacion_db_15_insumos(self):
        stock = obtener_stock_dict(self.db_path)
        self.assertIn(INSUMO_HUMECTANTE, stock)
        self.assertIn(INSUMO_DISPERSANTE, stock)
        self.assertIn(INSUMO_ANTIQUIEBRE, stock)
        self.assertIn(INSUMO_ENZIMA, stock)
        self.assertIn(INSUMO_ENZIMA_LIQUIDA, stock)
        self.assertIn(INSUMO_ACIDO_ACETICO, stock)
        self.assertIn(INSUMO_CLORO, stock)
        self.assertIn(INSUMO_SODA, stock)
        self.assertIn(INSUMO_BISULFITO, stock)
        self.assertIn(INSUMO_OXALICO, stock)
        self.assertIn(INSUMO_JABON, stock)
        self.assertIn(INSUMO_SECUESTRANTE, stock)
        self.assertIn(INSUMO_PEROXIDO, stock)
        self.assertIn(INSUMO_BLANQUEADOR, stock)
        self.assertIn(INSUMO_SUAVIZANTE, stock)
        self.assertEqual(len(stock), 15)

    def test_procesar_lote_exito(self):
        exito, msg, faltantes = procesar_lote_transaccional("LOTE-101", "Textiles Plaza", 60.0, PROGRAMA_DESENGOME, self.db_path)
        self.assertTrue(exito)
        self.assertEqual(faltantes, {})

        stock_post = obtener_stock_dict(self.db_path)
        self.assertEqual(stock_post[INSUMO_HUMECTANTE], 19850.0) # 20000 - 150
        self.assertEqual(stock_post[INSUMO_DISPERSANTE], 24790.0) # 25000 - 210
        self.assertEqual(stock_post[INSUMO_ANTIQUIEBRE], 14880.0) # 15000 - 120

    def test_procesar_lote_stone_liquida(self):
        exito, msg, faltantes = procesar_lote_transaccional("LOTE-STONE-01", "Jeans Co", 60.0, PROGRAMA_STONE_LIQUIDA, self.db_path)
        self.assertTrue(exito)
        self.assertEqual(faltantes, {})

        stock_post = obtener_stock_dict(self.db_path)
        self.assertEqual(stock_post[INSUMO_ENZIMA_LIQUIDA], 19700.0) # 20000 - 300
        self.assertEqual(stock_post[INSUMO_ACIDO_ACETICO], 14850.0)   # 15000 - 150
        self.assertEqual(stock_post[INSUMO_ANTIQUIEBRE], 15000.0)    # No se consume antiquiebre en STONEE

    def test_stock_insuficiente(self):
        exito, msg, faltantes = procesar_lote_transaccional("LOTE-GRANDE", "Hospital Central", 60000.0, PROGRAMA_DESENGOME, self.db_path)
        self.assertFalse(exito)
        self.assertIn("Stock insuficiente", msg)
        self.assertIn("Humectante", faltantes)

    def test_anular_lote_y_restituir_stock(self):
        stock_inicial = obtener_stock_dict(self.db_path)

        procesar_lote_transaccional("LOTE-TEMP", "Restaurante Mar", 60.0, PROGRAMA_STONE_LIQUIDA, self.db_path)
        exito_anula, msg_anula = anular_lote_transaccional("LOTE-TEMP", self.db_path)
        self.assertTrue(exito_anula)

        stock_restablecido = obtener_stock_dict(self.db_path)
        for key in stock_inicial:
            self.assertEqual(stock_restablecido[key], stock_inicial[key])

    def test_exportar_csv(self):
        procesar_lote_transaccional("LOTE-CSV-1", "Cliente CSV", 60.0, PROGRAMA_STONE_LIQUIDA, self.db_path)

        csv_file = Path(self.temp_dir.name) / "reporte.csv"
        exito, msg = exportar_historial_csv(csv_file, db_path=self.db_path)
        self.assertTrue(exito)
        self.assertTrue(csv_file.exists())

        with open(csv_file, encoding="utf-8") as f:
            reader = list(csv.reader(f))
            self.assertGreater(len(reader), 1)
            self.assertEqual(reader[0][0], "ID Lote")
            self.assertIn("Programa", reader[0])
            self.assertIn("Humectante (g)", reader[0])
            self.assertIn("Dispersante (g)", reader[0])


if __name__ == "__main__":
    unittest.main()
