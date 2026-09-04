#!/usr/bin/env python3
"""
==============================================================================
 SERVIDOR WEB Y API REST - LAVANDERÍA INDUSTRIAL (VERSIÓN INICIAL ESTABLE)
==============================================================================
"""

import json
import mimetypes
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lavanderia_inventario import (
    PROGRAMAS_DISPONIBLES,
    actualizar_stock_minimo,
    anular_lote_transaccional,
    calcular_dosificacion,
    exportar_historial_csv,
    inicializar_base_datos,
    obtener_alertas_stock,
    obtener_historial,
    obtener_stock,
    procesar_lote_transaccional,
    reabastecer_stock,
)

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"
PORT = 8085


class LavanderiaHTTPRequestHandler(BaseHTTPRequestHandler):

    def _responder_json(self, datos: dict, status: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _responder_archivo(self, ruta_archivo: Path) -> None:
        if not ruta_archivo.exists() or not ruta_archivo.is_file():
            self.send_error(404, "Archivo no encontrado")
            return

        mime_type, _ = mimetypes.guess_type(str(ruta_archivo))
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()

            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type or "json" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)
        except Exception as e:
            self.send_error(500, f"Error leyendo archivo: {e}")

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        ruta = parsed_url.path
        query = parse_qs(parsed_url.query)

        if ruta == "/api/stock":
            stock = obtener_stock()
            alertas = obtener_alertas_stock()
            self._responder_json({
                "exito": True,
                "stock": stock,
                "alertas": alertas
            })
            return

        elif ruta == "/api/programas":
            self._responder_json({"exito": True, "programas": PROGRAMAS_DISPONIBLES})
            return

        elif ruta == "/api/dosificacion":
            peso = float(query.get("peso", [0])[0])
            programa = query.get("programa", ["DESENGOME"])[0]
            dosificacion = calcular_dosificacion(peso, programa) if peso > 0 else {}
            self._responder_json({"exito": True, "dosificacion": dosificacion})
            return

        elif ruta == "/api/historial":
            cliente = query.get("cliente", [None])[0]
            historial = obtener_historial(cliente_filtro=cliente)
            self._responder_json({"exito": True, "historial": historial})
            return

        elif ruta == "/api/exportar":
            temp_csv = BASE_DIR / "historial_exportado.csv"
            exito, msg = exportar_historial_csv(temp_csv)
            if not exito or not temp_csv.exists():
                self._responder_json({"exito": False, "mensaje": msg}, status=400)
                return

            with open(temp_csv, "rb") as f:
                contenido = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=historial_lotes.csv")
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)
            return

        if ruta == "/" or ruta == "/index.html":
            self._responder_archivo(WEB_DIR / "index.html")
        else:
            self._responder_archivo(self._resolver_ruta_segura(ruta))

    def _resolver_ruta_segura(self, ruta: str) -> Path:
        """Resuelve una ruta pedida por el cliente y garantiza que quede dentro de WEB_DIR."""
        rel_path = ruta.lstrip("/")
        candidato = (WEB_DIR / rel_path).resolve()
        web_dir_resuelto = WEB_DIR.resolve()
        if web_dir_resuelto not in candidato.parents and candidato != web_dir_resuelto:
            # Intento de salir del directorio web/ (path traversal): no servir nada.
            return web_dir_resuelto / "__no_existe__"
        return candidato

    def do_POST(self) -> None:
        ruta = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))

        if content_length > 0:
            cuerpo_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(cuerpo_bytes.decode("utf-8"))
            except Exception:
                payload = {}
        else:
            payload = {}

        if ruta == "/api/lotes":
            id_lote = payload.get("id_lote", "").strip().upper()
            cliente = payload.get("cliente", "").strip()
            peso_kg = float(payload.get("peso_kg", 0))
            programa = payload.get("programa", "PROCESO_COMPLETO").strip().upper()

            if not id_lote or not cliente or peso_kg <= 0:
                self._responder_json({
                    "exito": False,
                    "mensaje": "Todos los campos son requeridos (ID, Cliente, Peso mayor a 0)."
                }, status=200)
                return

            exito, msg, faltantes = procesar_lote_transaccional(id_lote, cliente, peso_kg, programa)
            alertas = obtener_alertas_stock()
            self._responder_json({
                "exito": exito,
                "mensaje": msg,
                "faltantes": faltantes,
                "alertas": alertas
            }, status=200)
            return

        elif ruta == "/api/stock/reabastecer":
            insumo = payload.get("insumo")
            cantidad = float(payload.get("cantidad", 0))

            if not insumo or cantidad <= 0:
                self._responder_json({"exito": False, "mensaje": "Insumo y cantidad positiva requeridos."}, status=200)
                return

            exito = reabastecer_stock(insumo, cantidad)
            self._responder_json({
                "exito": exito,
                "mensaje": f"Se agregaron {cantidad} al insumo '{insumo}'." if exito else "No se pudo actualizar el stock."
            }, status=200)
            return

        elif ruta == "/api/stock/minimo":
            insumo = payload.get("insumo")
            nuevo_minimo = float(payload.get("nuevo_minimo", 0))

            if not insumo or nuevo_minimo < 0:
                self._responder_json({"exito": False, "mensaje": "Insumo y stock mínimo válido requeridos."}, status=200)
                return

            exito = actualizar_stock_minimo(insumo, nuevo_minimo)
            self._responder_json({
                "exito": exito,
                "mensaje": f"Stock mínimo actualizado para '{insumo}'." if exito else "Error al actualizar."
            }, status=200)
            return

        elif ruta == "/api/lotes/anular":
            id_lote = payload.get("id_lote", "").strip().upper()
            if not id_lote:
                self._responder_json({"exito": False, "mensaje": "Se requiere ID de lote."}, status=200)
                return

            exito, msg = anular_lote_transaccional(id_lote)
            self._responder_json({"exito": exito, "mensaje": msg}, status=200)
            return

        else:
            self._responder_json({"exito": False, "mensaje": "Endpoint no encontrado."}, status=404)


def iniciar_servidor(puerto: int = PORT) -> None:
    inicializar_base_datos()
    if not WEB_DIR.exists():
        WEB_DIR.mkdir(parents=True, exist_ok=True)

    server_address = ("0.0.0.0", puerto)
    httpd = HTTPServer(server_address, LavanderiaHTTPRequestHandler)
    print("=" * 65)
    print(f" 🧺 SERVIDOR WEB DE LAVANDERÍA INDUSTRIAL CORRIENDO")
    print(f"  👉 Abre en tu navegador: http://localhost:{puerto}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    iniciar_servidor(puerto)
