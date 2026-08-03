from PyQt5.QtCore import QThread, pyqtSignal

from utils.file_handler import buscar_dni_api


def predecir_genero_por_nombre(nombre: str) -> str:
    """Heuristica local simple para predecir genero sin servicios externos."""
    if not nombre:
        return "No especificado"
    try:
        primer = nombre.strip().split()[0].lower()
    except Exception:
        return "No especificado"

    if primer.endswith("a") and len(primer) > 1:
        return "Femenino"
    if primer.endswith(("o", "e", "i", "r", "s", "n")):
        return "Masculino"
    return "No especificado"


class SearchDNIWorker(QThread):
    """Worker para ejecutar la busqueda de DNI en otro hilo."""

    finished = pyqtSignal(str, str, bool)
    error = pyqtSignal(str)

    def __init__(self, dni):
        super().__init__()
        self.dni = dni

    def run(self):
        try:
            full_name, birth_date_str = buscar_dni_api(self.dni)
            self.finished.emit(full_name or "", birth_date_str or "", bool(full_name))
        except Exception as e:
            self.error.emit(str(e))


class PrintTicketWorker(QThread):
    """Worker para generar e imprimir el ticket de pago en partes sin bloquear la UI."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    success = pyqtSignal(str)

    def __init__(self, venta_data, paciente_nombre, nombre_optica, username, printer_name, receipt_width=80):
        super().__init__()
        self.venta_data = venta_data
        self.paciente_nombre = paciente_nombre
        self.nombre_optica = nombre_optica
        self.username = username
        self.printer_name = printer_name
        self.receipt_width = receipt_width
        self._is_running = True

    def stop(self):
        self._is_running = False
        if self.isRunning():
            self.wait(2000)

    def run(self):
        try:
            if not self._is_running:
                return

            from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
            from utils.printer_handler import print_boleta

            generador = GeneradorBoletasPlantilla(self.username)
            productos = []
            subtotal = 0

            for item in self.venta_data.get("items", []):
                if not self._is_running:
                    return

                # Obtener nombre y montos de forma segura
                nombre_p = str(item.get("producto") or item.get("nombre") or "Producto").strip()
                precio_u = float(item.get("precio_unitario", item.get("precio", 0)) or 0)
                subtotal_item = float(item.get("subtotal", item.get("total", precio_u)) or 0)

                productos.append(
                    {
                        "nombre": nombre_p,
                        "cantidad": int(item.get("cantidad", 1) or 1),
                        "precio": precio_u,
                        "total": subtotal_item,
                    }
                )

            # USAR LOS VALORES YA ALMACENADOS PARA EVITAR INFLACIÓN
            total = float(self.venta_data.get("total", 0) or 0)
            subtotal = float(self.venta_data.get("subtotal", total / 1.18) or 0)
            igv = float(self.venta_data.get("igv", total - subtotal) or 0)

            datos_boleta = {
                "nombre_optica": self.nombre_optica,
                "ruc": "12345678901",
                "direccion": "Direccion no configurada",
                "numero_boleta": str(self.venta_data.get("numero_boleta") or self.venta_data.get("id", "S/N")),
                "fecha": self.venta_data.get("fecha", ""),
                "cliente": self.paciente_nombre,
                "productos": productos,
                "subtotal": subtotal,
                "igv": igv,
                "total": total,
                "metodo_pago": str(self.venta_data.get("metodo_pago", "Efectivo")),
                "pie_pagina": "Gracias por su compra",
            }

            if not self._is_running:
                return

            pdf_path = generador.generar_boleta(datos_boleta)
            if not pdf_path:
                self.error.emit("No se pudo generar el ticket de pago")
                return

            if not self._is_running:
                return

            success, message = print_boleta(pdf_path, self.printer_name)
            if success:
                self.success.emit("Ticket de pago impreso correctamente")
            else:
                self.error.emit(f"El ticket se genero pero no se pudo imprimir:\n{message}")
        except Exception as e:
            if self._is_running:
                import traceback

                error_msg = f"Error al generar/imprimir el ticket:\n{str(e)}\n\n{traceback.format_exc()}"
                self.error.emit(error_msg)
        finally:
            self.finished.emit()
