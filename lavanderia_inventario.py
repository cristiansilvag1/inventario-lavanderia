#!/usr/bin/env python3
"""
==============================================================================
 SISTEMA DE RECEPCIÓN, DOSIFICACIÓN E INVENTARIO DE INSUMOS DE LAVANDERÍA
 Lavandería Industrial - Procesamiento Textil (Recetas Dinámicas por Programa)
==============================================================================

Descripción:
    - Registro de lotes de prendas por programa de proceso textil:
        * DESENGOME: Humectante, Dispersante, Anti-quiebre
        * STONE: Detergente Concentrado, Anti-quiebre, Suavizante Textil
        * BLEACH: Blanqueador Concentrado, Detergente Concentrado, Anti-quiebre
        * NEUTRALIZADO: Desinfectante/Neutralizante, Suavizante Textil, Anti-quiebre
        * BLANQUEO: Blanqueador Concentrado, Humectante, Detergente, Suavizante
    - Validación de stock disponible con transacciones atómicas (ACID).
    - Descuento automático e historial transaccional.
==============================================================================
"""

import csv
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH_DEFAULT = Path(__file__).parent / "lavanderia.db"

# Constantes de Insumos Químicos
INSUMO_HUMECTANTE = "humectante_g"
INSUMO_DISPERSANTE = "dispersante_g"
INSUMO_ANTIQUIEBRE = "antiquiebre_g"
INSUMO_ENZIMA = "enzima_g"
INSUMO_ENZIMA_LIQUIDA = "enzima_liquida_ml"
INSUMO_ACIDO_ACETICO = "acido_acetico_ml"
INSUMO_JABON = "jabon_g"
INSUMO_DETERGENTE = INSUMO_JABON
INSUMO_CLORO = "cloro_ml"
INSUMO_SODA = "soda_g"
INSUMO_BISULFITO = "bisulfito_g"
INSUMO_OXALICO = "oxalico_g"
INSUMO_SECUESTRANTE = "secuestrante_g"
INSUMO_PEROXIDO = "peroxido_ml"
INSUMO_BLANQUEADOR = "blanqueador_g"
INSUMO_SUAVIZANTE = "suavizante_g"
INSUMO_DESINFECTANTE = "desinfectante_ml"

# Constantes de Programas y Rutas Secuenciales de Lavado
PROGRAMA_COMPLETO = "PROCESO_COMPLETO"
PROGRAMA_STONE_COMPLETO = "PROCESO_STONE_COMPLETO"
PROGRAMA_BLANQUEO_TOTAL = "PROCESO_BLANQUEO_TOTAL"

PROGRAMA_DESENGOME = "DESENGOME"
PROGRAMA_STONE_ENZIMA = "STONE_ENZIMA"
PROGRAMA_STONE_LIQUIDA = "STONE_LIQUIDA"
PROGRAMA_BLEACH = "BLEACH"
PROGRAMA_NEUTRALIZADO = "NEUTRALIZADO"
PROGRAMA_BLANQUEO = "BLANQUEO"

PROGRAMAS_DISPONIBLES = {
    PROGRAMA_COMPLETO: "Proceso Completo Secuencial (5 Pasos)",
    PROGRAMA_STONE_COMPLETO: "Ruta Stone Wash (Desengome ➡️ Stone ➡️ Neutralizado)",
    PROGRAMA_BLANQUEO_TOTAL: "Ruta Blanqueo Total (Desengome ➡️ Bleach ➡️ Neutralizado ➡️ Blanqueo)",
    PROGRAMA_DESENGOME: "Paso 1: Desengome",
    PROGRAMA_STONE_ENZIMA: "Paso 2: Stone - Enzima (Polvo)",
    PROGRAMA_STONE_LIQUIDA: "Paso 2: Stone - Enzima Líquida + Acético",
    PROGRAMA_BLEACH: "Paso 3: Bleach (Clorado)",
    PROGRAMA_NEUTRALIZADO: "Paso 4: Neutralizado",
    PROGRAMA_BLANQUEO: "Paso 5: Blanqueo Óptico"
}

RUTAS_PROCESOS = {
    PROGRAMA_COMPLETO: [PROGRAMA_DESENGOME, PROGRAMA_STONE_LIQUIDA, PROGRAMA_BLEACH, PROGRAMA_NEUTRALIZADO, PROGRAMA_BLANQUEO],
    PROGRAMA_STONE_COMPLETO: [PROGRAMA_DESENGOME, PROGRAMA_STONE_LIQUIDA, PROGRAMA_NEUTRALIZADO],
    PROGRAMA_BLANQUEO_TOTAL: [PROGRAMA_DESENGOME, PROGRAMA_BLEACH, PROGRAMA_NEUTRALIZADO, PROGRAMA_BLANQUEO],
}

# Definición de Recetas Específicas de Químicos por Programa (Porcentaje s.p.m. = sobre peso de mercancía en kg)
RECETAS_PROGRAMAS = {
    PROGRAMA_DESENGOME: {
        INSUMO_HUMECTANTE: {"nombre": "Humectante", "unidad": "g", "porcentaje_spm": 0.25, "dosis_60kg": 150},
        INSUMO_DISPERSANTE: {"nombre": "Dispersante", "unidad": "g", "porcentaje_spm": 0.35, "dosis_60kg": 210},
        INSUMO_ANTIQUIEBRE: {"nombre": "Anti-quiebre", "unidad": "g", "porcentaje_spm": 0.20, "dosis_60kg": 120},
    },
    PROGRAMA_STONE_ENZIMA: {
        INSUMO_ENZIMA: {"nombre": "Enzima (Polvo)", "unidad": "g", "porcentaje_spm": 0.80, "dosis_60kg": 480},
    },
    PROGRAMA_STONE_LIQUIDA: {
        INSUMO_ENZIMA_LIQUIDA: {"nombre": "Enzima Líquida", "unidad": "ml", "porcentaje_spm": 0.50, "dosis_60kg": 300},
        INSUMO_ACIDO_ACETICO: {"nombre": "Ácido Acético", "unidad": "ml", "porcentaje_spm": 0.25, "dosis_60kg": 150},
    },
    PROGRAMA_BLEACH: {
        INSUMO_CLORO: {"nombre": "Cloro Concentrado", "unidad": "ml", "porcentaje_spm": 0.50, "dosis_60kg": 300},
        INSUMO_SODA: {"nombre": "Soda Cáustica", "unidad": "g", "porcentaje_spm": 0.25, "dosis_60kg": 150},
    },
    PROGRAMA_NEUTRALIZADO: {
        INSUMO_HUMECTANTE: {"nombre": "Humectante", "unidad": "g", "porcentaje_spm": 0.20, "dosis_60kg": 120},
        INSUMO_DISPERSANTE: {"nombre": "Dispersante", "unidad": "g", "porcentaje_spm": 0.25, "dosis_60kg": 150},
        INSUMO_BISULFITO: {"nombre": "Bisulfito de Sodio", "unidad": "g", "porcentaje_spm": 0.35, "dosis_60kg": 210},
        INSUMO_OXALICO: {"nombre": "Ácido Oxálico", "unidad": "g", "porcentaje_spm": 0.25, "dosis_60kg": 150},
    },
    PROGRAMA_BLANQUEO: {
        INSUMO_JABON: {"nombre": "Jabón", "unidad": "g", "porcentaje_spm": 0.40, "dosis_60kg": 240},
        INSUMO_DISPERSANTE: {"nombre": "Dispersante", "unidad": "g", "porcentaje_spm": 0.25, "dosis_60kg": 150},
        INSUMO_SECUESTRANTE: {"nombre": "Secuestrante", "unidad": "g", "porcentaje_spm": 0.20, "dosis_60kg": 120},
        INSUMO_SODA: {"nombre": "Soda Cáustica", "unidad": "g", "porcentaje_spm": 0.35, "dosis_60kg": 210},
        INSUMO_PEROXIDO: {"nombre": "Peróxido de Hidrógeno", "unidad": "ml", "porcentaje_spm": 0.50, "dosis_60kg": 300},
        INSUMO_BLANQUEADOR: {"nombre": "Blanqueador Óptico", "unidad": "g", "porcentaje_spm": 0.65, "dosis_60kg": 390},
    }
}

# Configuración Inicial de Inventario Completo
INSUMOS_INICIALES = [
    {"insumo": INSUMO_HUMECTANTE, "nombre_display": "Humectante", "unidad": "g", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_DISPERSANTE, "nombre_display": "Dispersante", "unidad": "g", "cantidad": 25000.0, "stock_minimo": 2500.0},
    {"insumo": INSUMO_ANTIQUIEBRE, "nombre_display": "Anti-quiebre", "unidad": "g", "cantidad": 15000.0, "stock_minimo": 1500.0},
    {"insumo": INSUMO_ENZIMA, "nombre_display": "Enzima (Polvo)", "unidad": "g", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_ENZIMA_LIQUIDA, "nombre_display": "Enzima Líquida", "unidad": "ml", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_ACIDO_ACETICO, "nombre_display": "Ácido Acético", "unidad": "ml", "cantidad": 15000.0, "stock_minimo": 1500.0},
    {"insumo": INSUMO_CLORO, "nombre_display": "Cloro Concentrado", "unidad": "ml", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_SODA, "nombre_display": "Soda Cáustica", "unidad": "g", "cantidad": 30000.0, "stock_minimo": 3000.0},
    {"insumo": INSUMO_BISULFITO, "nombre_display": "Bisulfito de Sodio", "unidad": "g", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_OXALICO, "nombre_display": "Ácido Oxálico", "unidad": "g", "cantidad": 15000.0, "stock_minimo": 1500.0},
    {"insumo": INSUMO_JABON, "nombre_display": "Jabón", "unidad": "g", "cantidad": 50000.0, "stock_minimo": 5000.0},
    {"insumo": INSUMO_SECUESTRANTE, "nombre_display": "Secuestrante", "unidad": "g", "cantidad": 15000.0, "stock_minimo": 1500.0},
    {"insumo": INSUMO_PEROXIDO, "nombre_display": "Peróxido de Hidrógeno", "unidad": "ml", "cantidad": 25000.0, "stock_minimo": 2500.0},
    {"insumo": INSUMO_BLANQUEADOR, "nombre_display": "Blanqueador Óptico", "unidad": "g", "cantidad": 20000.0, "stock_minimo": 2000.0},
    {"insumo": INSUMO_SUAVIZANTE, "nombre_display": "Suavizante Textil", "unidad": "g", "cantidad": 30000.0, "stock_minimo": 3000.0},
]


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path if db_path is not None else DB_PATH_DEFAULT
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def inicializar_base_datos(db_path: Optional[Path] = None) -> None:
    """Crea y limpia el esquema de base de datos para los insumos químicos y recetas por programa."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Tabla inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            insumo TEXT PRIMARY KEY,
            nombre_display TEXT NOT NULL DEFAULT '',
            cantidad REAL NOT NULL CHECK (cantidad >= 0),
            unidad TEXT NOT NULL,
            stock_minimo REAL NOT NULL DEFAULT 0.0 CHECK (stock_minimo >= 0)
        );
    """)

    valid_insumos = [item["insumo"] for item in INSUMOS_INICIALES]
    cursor.execute(f"""
        DELETE FROM inventario 
        WHERE insumo NOT IN ({','.join(['?']*len(valid_insumos))});
    """, valid_insumos)

    # Asegurar que existan todos los insumos
    for item in INSUMOS_INICIALES:
        cursor.execute("""
            INSERT INTO inventario (insumo, nombre_display, cantidad, unidad, stock_minimo)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(insumo) DO UPDATE SET
                nombre_display = excluded.nombre_display,
                unidad = excluded.unidad;
        """, (
            item["insumo"], item["nombre_display"], item["cantidad"],
            item["unidad"], item["stock_minimo"]
        ))

    # 2. Tabla lotes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_lote TEXT NOT NULL UNIQUE,
            cliente TEXT NOT NULL,
            peso_kg REAL NOT NULL CHECK (peso_kg > 0),
            programa TEXT NOT NULL DEFAULT 'DESENGOME',
            humectante_g REAL NOT NULL DEFAULT 0.0,
            dispersante_g REAL NOT NULL DEFAULT 0.0,
            antiquiebre_g REAL NOT NULL DEFAULT 0.0,
            enzima_g REAL NOT NULL DEFAULT 0.0,
            enzima_liquida_ml REAL NOT NULL DEFAULT 0.0,
            acido_acetico_ml REAL NOT NULL DEFAULT 0.0,
            detergente_g REAL NOT NULL DEFAULT 0.0,
            suavizante_g REAL NOT NULL DEFAULT 0.0,
            blanqueador_g REAL NOT NULL DEFAULT 0.0,
            desinfectante_ml REAL NOT NULL DEFAULT 0.0,
            insumos_json TEXT NOT NULL DEFAULT '{}',
            fecha_hora TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PROCESADO'
        );
    """)

    # Migraciones seguras para bases de datos existentes
    cursor.execute("PRAGMA table_info(lotes);")
    columnas = [row[1] for row in cursor.fetchall()]
    cols_to_add = [
        ("humectante_g", "REAL NOT NULL DEFAULT 0.0"),
        ("dispersante_g", "REAL NOT NULL DEFAULT 0.0"),
        ("antiquiebre_g", "REAL NOT NULL DEFAULT 0.0"),
        ("enzima_g", "REAL NOT NULL DEFAULT 0.0"),
        ("enzima_liquida_ml", "REAL NOT NULL DEFAULT 0.0"),
        ("acido_acetico_ml", "REAL NOT NULL DEFAULT 0.0"),
        ("insumos_json", "TEXT NOT NULL DEFAULT '{}'")
    ]
    for col_name, col_def in cols_to_add:
        if col_name not in columnas:
            cursor.execute(f"ALTER TABLE lotes ADD COLUMN {col_name} {col_def};")

    conn.commit()
    conn.close()


def obtener_stock(db_path: Optional[Path] = None) -> List[dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT insumo, nombre_display, cantidad, unidad, stock_minimo
        FROM inventario
        ORDER BY rowid ASC;
    """)
    filas = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return filas


def obtener_stock_dict(db_path: Optional[Path] = None) -> Dict[str, float]:
    filas = obtener_stock(db_path)
    return {f["insumo"]: f["cantidad"] for f in filas}


def obtener_alertas_stock(db_path: Optional[Path] = None) -> List[dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT insumo, nombre_display, cantidad, unidad, stock_minimo
        FROM inventario
        WHERE cantidad <= stock_minimo;
    """)
    alertas = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return alertas


def reabastecer_stock(insumo: str, cantidad_sumar: float, db_path: Optional[Path] = None) -> bool:
    if cantidad_sumar <= 0:
        return False
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventario
        SET cantidad = cantidad + ?
        WHERE insumo = ?;
    """, (cantidad_sumar, insumo))
    modificados = cursor.rowcount
    conn.commit()
    conn.close()
    return modificados > 0


def actualizar_stock_minimo(insumo: str, nuevo_minimo: float, db_path: Optional[Path] = None) -> bool:
    if nuevo_minimo < 0:
        return False
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventario
        SET stock_minimo = ?
        WHERE insumo = ?;
    """, (nuevo_minimo, insumo))
    modificados = cursor.rowcount
    conn.commit()
    conn.close()
    return modificados > 0


def calcular_dosificacion(peso_kg: float, programa: str = PROGRAMA_COMPLETO) -> Dict[str, dict]:
    """
    Calcula la dosificación requerida para los insumos específicos de un programa, ruta secuencial
    o lista de pasos de lavado. Suma los porcentajes e insumos consumidos en cada etapa.
    """
    if peso_kg <= 0:
        return {}

    prog_upper = programa.upper().strip() if programa else PROGRAMA_COMPLETO

    if "," in prog_upper:
        pasos = [p.strip() for p in prog_upper.split(",") if p.strip()]
    elif prog_upper in RUTAS_PROCESOS:
        pasos = RUTAS_PROCESOS[prog_upper]
    elif prog_upper in RECETAS_PROGRAMAS:
        pasos = [prog_upper]
    else:
        pasos = RUTAS_PROCESOS[PROGRAMA_COMPLETO]

    dosificacion = {}
    for paso in pasos:
        receta = RECETAS_PROGRAMAS.get(paso, {})
        for insumo_key, spec in receta.items():
            pct = spec.get("porcentaje_spm", 0.0)
            if insumo_key not in dosificacion:
                dosificacion[insumo_key] = {
                    "cantidad": 0.0,
                    "porcentaje_spm": 0.0,
                    "dosis_por_kg": 0.0,
                    "nombre": spec["nombre"],
                    "unidad": spec["unidad"]
                }
            
            dosificacion[insumo_key]["porcentaje_spm"] += pct
            dosificacion[insumo_key]["dosis_por_kg"] += round(pct * 10.0, 2)

    for insumo_key, info in dosificacion.items():
        pct_total = info["porcentaje_spm"]
        if info["unidad"] in ("ml", "L"):
            info["cantidad"] = round(peso_kg * pct_total * 10.0, 1)
        else:
            info["cantidad"] = int(round(peso_kg * pct_total * 10.0))

    return dosificacion


def obtener_historial(cliente_filtro: Optional[str] = None, db_path: Optional[Path] = None) -> List[dict]:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT id_lote, cliente, peso_kg, programa, humectante_g, dispersante_g, antiquiebre_g, 
               detergente_g, suavizante_g, blanqueador_g, desinfectante_ml, insumos_json, fecha_hora, estado
        FROM lotes
    """
    params = []

    if cliente_filtro:
        query += " WHERE cliente LIKE ?"
        params.append(f"%{cliente_filtro}%")

    query += " ORDER BY id DESC;"

    cursor.execute(query, params)
    filas = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for f in filas:
        try:
            f["insumos_dict"] = json.loads(f.get("insumos_json", "{}"))
        except Exception:
            f["insumos_dict"] = {}

    return filas


def procesar_lote_transaccional(
    id_lote: str, cliente: str, peso_kg: float, programa: str = PROGRAMA_DESENGOME, db_path: Optional[Path] = None
) -> Tuple[bool, str, Dict[str, float]]:
    if peso_kg <= 0:
        return False, "El peso del lote debe ser un número positivo mayor a cero.", {}

    prog = programa.upper().strip() if programa else ""
    if prog not in PROGRAMAS_DISPONIBLES:
        return False, f"Programa '{programa}' no es válido. Programas disponibles: {', '.join(PROGRAMAS_DISPONIBLES)}.", {}

    dosis_map = calcular_dosificacion(peso_kg, prog)

    conn = get_connection(db_path)

    try:
        conn.execute("BEGIN IMMEDIATE TRANSACTION;")
        cursor = conn.cursor()

        # Validar si ya existe el ID de lote
        cursor.execute("SELECT 1 FROM lotes WHERE id_lote = ?;", (id_lote,))
        if cursor.fetchone() is not None:
            conn.rollback()
            conn.close()
            return False, f"El ID de lote '{id_lote}' ya existe.", {}

        # Obtener stock actual
        stock = obtener_stock_dict(db_path)
        faltantes = {}

        for insumo_key, info in dosis_map.items():
            cant_req = info["cantidad"]
            cant_actual = stock.get(insumo_key, 0.0)
            if cant_actual < cant_req:
                faltantes[info["nombre"]] = round(cant_req - cant_actual, 1)

        if faltantes:
            conn.rollback()
            conn.close()
            return False, "Stock insuficiente para procesar el lote.", faltantes

        # Descontar existencias aplicables
        insumos_guardados = {}
        for insumo_key, info in dosis_map.items():
            cant_req = info["cantidad"]
            cursor.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE insumo = ?;", (cant_req, insumo_key))
            insumos_guardados[insumo_key] = cant_req

        # Registrar lote con los insumos específicos consumidos
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insumos_json_str = json.dumps(insumos_guardados, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO lotes (
                id_lote, cliente, peso_kg, programa, 
                humectante_g, dispersante_g, antiquiebre_g, 
                detergente_g, suavizante_g, blanqueador_g, desinfectante_ml, 
                insumos_json, fecha_hora, estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROCESADO');
        """, (
            id_lote, cliente, peso_kg, prog,
            insumos_guardados.get(INSUMO_HUMECTANTE, 0.0),
            insumos_guardados.get(INSUMO_DISPERSANTE, 0.0),
            insumos_guardados.get(INSUMO_ANTIQUIEBRE, 0.0),
            insumos_guardados.get(INSUMO_JABON, 0.0),
            insumos_guardados.get(INSUMO_SUAVIZANTE, 0.0),
            insumos_guardados.get(INSUMO_BLANQUEADOR, 0.0),
            insumos_guardados.get(INSUMO_DESINFECTANTE, 0.0),
            insumos_json_str, fecha_hora
        ))

        conn.commit()
        conn.close()
        return True, f"Lote '{id_lote}' (Programa {prog}) registrado y procesado con éxito.", {}

    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        return False, f"Error de integridad en la base de datos: {e}", {}
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error inesperado al procesar lote: {e}", {}


def anular_lote_transaccional(id_lote: str, db_path: Optional[Path] = None) -> Tuple[bool, str]:
    conn = get_connection(db_path)

    try:
        conn.execute("BEGIN IMMEDIATE TRANSACTION;")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_lote, humectante_g, dispersante_g, antiquiebre_g, 
                   detergente_g, suavizante_g, blanqueador_g, desinfectante_ml, insumos_json, estado
            FROM lotes
            WHERE id_lote = ?;
        """, (id_lote,))
        lote = cursor.fetchone()

        if lote is None:
            conn.rollback()
            conn.close()
            return False, f"El lote '{id_lote}' no fue encontrado."

        if lote["estado"] == "ANULADO":
            conn.rollback()
            conn.close()
            return False, f"El lote '{id_lote}' ya se encuentra anulado."

        # Reintegrar stock de los insumos consumidos
        try:
            insumos_dict = json.loads(lote["insumos_json"] or "{}")
        except Exception:
            insumos_dict = {}

        if not insumos_dict:
            insumos_dict = {
                INSUMO_HUMECTANTE: lote["humectante_g"],
                INSUMO_DISPERSANTE: lote["dispersante_g"],
                INSUMO_ANTIQUIEBRE: lote["antiquiebre_g"],
                INSUMO_JABON: lote["jabon_g"],
                INSUMO_SUAVIZANTE: lote["suavizante_g"],
                INSUMO_BLANQUEADOR: lote["blanqueador_g"],
                INSUMO_DESINFECTANTE: lote["desinfectante_ml"],
            }

        for insumo_key, cantidad in insumos_dict.items():
            if cantidad > 0:
                cursor.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE insumo = ?;", (cantidad, insumo_key))

        cursor.execute("UPDATE lotes SET estado = 'ANULADO' WHERE id_lote = ?;", (id_lote,))

        conn.commit()
        conn.close()
        return True, f"El lote '{id_lote}' fue anulado con éxito. Se reintegraron los insumos al inventario."

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error al anular el lote: {e}"


def exportar_historial_csv(ruta_salida: Path, cliente_filtro: Optional[str] = None, db_path: Optional[Path] = None) -> Tuple[bool, str]:
    try:
        historial = obtener_historial(cliente_filtro=cliente_filtro, db_path=db_path)
        if not historial:
            return False, "No hay lotes para exportar."

        with open(ruta_salida, mode="w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow([
                "ID Lote", "Cliente", "Peso (kg)", "Programa",
                "Humectante (g)", "Dispersante (g)", "Anti-quiebre (g)",
                "Detergente (g)", "Suavizante (g)", "Blanqueador (g)", "Desinfectante (ml)",
                "Fecha/Hora", "Estado"
            ])
            for h in historial:
                escritor.writerow([
                    h["id_lote"], h["cliente"], f"{h['peso_kg']:.2f}", h.get("programa", "DESENGOME"),
                    f"{h.get('humectante_g', 0):.0f}", f"{h.get('dispersante_g', 0):.0f}", f"{h.get('antiquiebre_g', 0):.0f}",
                    f"{h['detergente_g']:.0f}", f"{h['suavizante_g']:.0f}",
                    f"{h.get('blanqueador_g', 0):.0f}", f"{h.get('desinfectante_ml', 0):.0f}",
                    h["fecha_hora"], h["estado"]
                ])

        return True, f"Historial exportado exitosamente a: {ruta_salida.resolve()}"
    except Exception as e:
        return False, f"Error al exportar a CSV: {e}"


if __name__ == "__main__":
    inicializar_base_datos()
    print("Base de datos inicializada correctamente con recetas dinámicas por programa de lavado.")
