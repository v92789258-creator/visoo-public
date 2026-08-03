from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from gui.dialogs.frame_sale_dialog import FrameSaleDialog

from .motilidad import MotilidadDialog
from .workers import PrintTicketWorker


class CreatePatientPageSalesMixin:
    def _replace_items_venta(self, items):
        self.items_venta = [dict(item) for item in (items or []) if isinstance(item, dict)]
        if hasattr(self, "_update_multi_metodo_pago_grad_state"):
            self._update_multi_metodo_pago_grad_state()

    def _generar_ticket_pago_parcial(self, nombre, dni, fecha, monto_adelanto, optometra):
        try:
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog

            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QtWidgets.QDialog.Accepted:
                return

            printer_name = printer_dialog.get_selected_printer()
            if not printer_name:
                QMessageBox.warning(self, "Error", "Por favor selecciona una impresora valida")
                return

            venta = {
                "paciente_dni": dni,
                "paciente_nombre": nombre,
                "fecha": fecha,
                "monto_cobrado": str(monto_adelanto),
                "optometra": optometra,
                "subtotal": str(monto_adelanto),
                "total": str(monto_adelanto),
                "items": [
                    {
                        "producto": "Adelanto de Graduacion",
                        "descripcion": "Pago en Partes",
                        "precio": monto_adelanto,
                        "cantidad": 1,
                        "subtotal": monto_adelanto,
                    }
                ],
            }

            nombre_optica = "Mi Optica"
            if hasattr(self.parent_app, "home_page") and hasattr(self.parent_app.home_page, "nombre_optica_label"):
                try:
                    txt = (
                        self.parent_app.home_page.nombre_optica_label.text()
                        .replace("Bienvenido al Sistema de Gestion de ", "")
                        .strip()
                    )
                    if txt:
                        nombre_optica = txt
                except Exception:
                    pass

            username = getattr(self.parent_app, "username", "default_user")
            try:
                from gui.dialogs.receipt_size_dialog import ReceiptSizeDialog

                size_dialog = ReceiptSizeDialog(username, self.parent_app)
                if size_dialog.exec_() != ReceiptSizeDialog.Accepted:
                    return
                receipt_width = size_dialog.get_selected_width()
            except Exception as e:
                import traceback

                print(f"[WARNING] Error al abrir configuracion de tamano: {e}\n{traceback.format_exc()}")
                receipt_width = 80

            if hasattr(self, "print_worker") and self.print_worker is not None:
                try:
                    if self.print_worker.isRunning():
                        print("[DEBUG] Deteniendo print_worker anterior...")
                        self.print_worker.stop()
                except Exception as e:
                    print(f"[WARN] Error deteniendo worker anterior: {e}")

            self.print_worker = PrintTicketWorker(venta, nombre, nombre_optica, username, printer_name, receipt_width)
            self.print_worker.success.connect(self._on_print_success)
            self.print_worker.error.connect(self._on_print_error)
            self.print_worker.finished.connect(self._on_print_finished)
            self.print_worker.start()
        except Exception as e:
            import traceback

            print(f"[ERROR] Error al preparar impresion:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Error al preparar la impresion:\n{str(e)}")

    def _on_print_success(self, message):
        QMessageBox.information(self, "Exito", message)

    def _on_print_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)

    def _on_print_finished(self):
        print("[DEBUG] Print worker finished")

    def closeEvent(self, event):
        try:
            if hasattr(self, "print_worker") and self.print_worker is not None and self.print_worker.isRunning():
                print("[DEBUG] Deteniendo print_worker en closeEvent...")
                self.print_worker.stop()
                self.print_worker.wait(2000)
        except Exception as e:
            print(f"[WARN] Error limpiando print_worker: {e}")
        super().closeEvent(event)

    def agregar_item_venta(self, item_data):
        codigo = item_data.get("codigo", "")
        nombre = item_data.get("nombre", "")
        precio_unitario = float(item_data.get("precio_unitario", 0) or 0)
        cantidad = int(item_data.get("cantidad", 0) or 0)
        total = float(item_data.get("total", 0) or 0)

        existente = None
        for item in self.items_venta:
            same_codigo = bool(codigo) and item.get("codigo") == codigo
            same_nombre_precio = (
                not codigo and item.get("nombre") == nombre and float(item.get("precio_unitario", 0) or 0) == precio_unitario
            )
            if same_codigo or same_nombre_precio:
                existente = item
                break

        if existente:
            stock_maximo = int(existente.get("stock_original", item_data.get("stock_original", 0)) or 0)
            nueva_cantidad = int(existente.get("cantidad", 0) or 0) + cantidad
            if stock_maximo > 0 and nueva_cantidad > stock_maximo:
                QMessageBox.warning(
                    self,
                    "Stock Insuficiente",
                    f"No puedes agregar '{nombre}' porque excede el stock disponible ({stock_maximo}).",
                )
                return
            existente["cantidad"] = int(existente.get("cantidad", 0) or 0) + cantidad
            existente["total"] = float(existente.get("total", 0) or 0) + total
            QMessageBox.information(
                self,
                "Producto Actualizado",
                f"Se actualizo '{nombre}' en la venta.\nCantidad total: {existente['cantidad']}\nTotal acumulado: S/ {existente['total']:.2f}",
            )
            if hasattr(self, "_update_multi_metodo_pago_grad_state"):
                self._update_multi_metodo_pago_grad_state()
            return

        self.items_venta.append(item_data)
        if hasattr(self, "_update_multi_metodo_pago_grad_state"):
            self._update_multi_metodo_pago_grad_state()
        QMessageBox.information(
            self,
            "Producto Agregado",
            f"Producto '{nombre}' agregado a la venta.\nCantidad: {cantidad}\nTotal: S/ {total:.2f}",
        )

    def seleccionar_producto(self):
        dni = "".join(filter(str.isdigit, self.entry_dni.text().strip() or ""))
        nombre = self.entry_paciente.text().strip()
        optometra = self.optometra_combo.currentText() if self.optometra_combo.count() > 0 else None

        if not dni or len(dni) != 8:
            QMessageBox.warning(self, "Validacion", "Por favor ingresa un DNI valido.")
            return
        if not nombre:
            QMessageBox.warning(self, "Validacion", "Por favor ingresa el nombre del paciente.")
            return
        if not optometra or optometra == "Sin Optometras":
            QMessageBox.warning(self, "Validacion", "Por favor selecciona un optometra.")
            return

        try:
            if hasattr(self, "btn_vender_montura") and self.btn_vender_montura is not None:
                self.btn_vender_montura.setEnabled(False)

            dialog = FrameSaleDialog(
                paciente_dni=dni,
                paciente_nombre=nombre,
                optometra=optometra,
                username=self.username,
                parent=self,
                preselected_items=list(self.items_venta or []),
            )
            dialog.selection_finalized.connect(self._replace_items_venta)
            dialog.exec_()
        finally:
            if hasattr(self, "btn_vender_montura") and self.btn_vender_montura is not None:
                self.btn_vender_montura.setEnabled(True)

    def abrir_ventana_motilidad(self):
        dialog = MotilidadDialog(self)
        data_actual = self._normalize_motilidad_versiones(self.motilidad_versiones)
        dialog.od_widget.set_values(data_actual.get("od", {}))
        dialog.oi_widget.set_values(data_actual.get("oi", {}))
        dialog.sync_modo_desde_valores()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.motilidad_versiones = self._normalize_motilidad_versiones(dialog.valores)
