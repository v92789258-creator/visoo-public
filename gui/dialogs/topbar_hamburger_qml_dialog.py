import os
import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QUrl, pyqtSlot
from PyQt5.QtQuickWidgets import QQuickWidget


class TopbarHamburgerBridge(QObject):
    def __init__(self, dialog):
        super().__init__(dialog)
        self._dialog = dialog

    @pyqtSlot()
    def close(self):
        self._dialog.close()

    @pyqtSlot(str)
    def action(self, action_id: str):
        self._dialog._handle_action(str(action_id or "").strip())

    @pyqtSlot(str)
    def search(self, query: str):
        self._dialog._handle_search(str(query or "").strip())


class TopbarHamburgerQmlDialog(QtWidgets.QDialog):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self._parent_app = parent_app

        self.setModal(True)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.resize(parent_app.width(), parent_app.height())

        self._bridge = TopbarHamburgerBridge(self)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(QtCore.Qt.transparent)

        ctx = self._quick.rootContext()
        ctx.setContextProperty("bridge", self._bridge)

        device_label = str(getattr(parent_app, "device_role_label", "") or "").strip()
        branch_label = str(getattr(parent_app, "selected_branch_label", "") or "").strip()
        ctx.setContextProperty("deviceLabel", device_label)
        ctx.setContextProperty("branchLabel", branch_label)
        ctx.setContextProperty("isMadre", bool(getattr(parent_app, "es_dispositivo_madre", lambda: False)()))

        ctx.setContextProperty("menuModel", self._build_menu_model())

        qml_path = self._resolve_qml_path()
        self._quick.setSource(QUrl.fromLocalFile(qml_path))
        if self._quick.status() == QQuickWidget.Error:
            errors = [str(err.toString()) for err in self._quick.errors()]
            raise RuntimeError("No se pudo cargar QML topbar: " + " | ".join(errors))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._quick)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
            self.close()
            return
        super().keyPressEvent(event)

    def _resolve_qml_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            qml_path = os.path.join(base_dir, "gui", "qml", "topbar_hamburger.qml")
        else:
            qml_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "qml", "topbar_hamburger.qml")
            )
        if not os.path.exists(qml_path):
            raise RuntimeError(f"No existe archivo QML: {qml_path}")
        return qml_path

    def _build_menu_model(self):
        # Keep these ids stable; they are used by QML.
        madre = bool(getattr(self._parent_app, "es_dispositivo_madre", lambda: False)())
        menu = [
            {
                "label": "Inicio",
                "items": [
                    {"id": "inicio_panel", "label": "Panel principal"},
                    {"id": "inicio_config", "label": "Configuracion"},
                ],
            },
            {
                "label": "Inventario",
                "items": [
                    {"id": "inv_ver", "label": "Ver inventario"},
                ],
            },
            {
                "label": "Ventas",
                "items": [
                    {"id": "ven_nueva", "label": "Nueva venta"},
                    {"id": "ven_manual", "label": "Venta manual"},
                    {"id": "ven_deudas", "label": "Historial de deudas"},
                    {"id": "ven_hist", "label": "Historial de ventas"},
                    {"id": "ven_reporte", "label": "Generar reporte"},
                ],
            },
            {
                "label": "Herramientas",
                "items": [
                    {"id": "her_barcode", "label": "Generador de codigos de barras"},
                    {"id": "her_sync", "label": "Centro de sincronizacion"},
                    {"id": "her_trash", "label": "Papelera y recuperacion"},
                ],
            },
        ]

        if madre:
            # Subopciones extra para dispositivo madre.
            menu[1]["items"].extend([
                {"id": "inv_categorias", "label": "Categorias"},
                {"id": "inv_reportes", "label": "Reportes"},
            ])
            menu[3]["items"].extend([
                {"id": "her_audit", "label": "Datos y libro contable"},
                {"id": "her_birthdays", "label": "Cumpleanos"},
            ])

        # Accesos rapidos siempre visibles.
        menu.append({
            "label": "Ir a",
            "items": [
                {"id": "nav_clientes", "label": "Clientes"},
                {"id": "nav_pacientes", "label": "Pacientes"},
                {"id": "nav_calendario", "label": "Calendario"},
            ],
        })
        return menu

    def _handle_search(self, query: str):
        parent = self._parent_app
        fn = getattr(parent, "_global_search_with_text", None)
        if callable(fn) and query:
            self.close()
            fn(query)

    def _handle_action(self, action_id: str):
        parent = self._parent_app

        if action_id == "close":
            self.close()
            return

        if action_id == "open_notifications":
            self.close()
            try:
                parent.toggle_notifications_popup()
            except Exception:
                pass
            return

        if action_id == "manual_backup":
            self.close()
            try:
                parent.manual_backup()
            except Exception:
                pass
            return

        if action_id == "open_profile":
            self.close()
            try:
                parent.mostrar_frame(12)
            except Exception:
                pass
            return

        if action_id == "inicio_panel":
            self.close()
            parent.mostrar_frame(0)
            return
        if action_id == "inicio_config":
            self.close()
            parent.mostrar_frame(10)
            return

        if action_id == "inv_ver":
            self.close()
            parent.mostrar_frame(3)
            return
        if action_id == "inv_categorias":
            self.close()
            try:
                parent.mostrar_frame(16)
            except Exception:
                pass
            return
        if action_id == "inv_reportes":
            self.close()
            try:
                parent.mostrar_frame(14)
            except Exception:
                pass
            return

        if action_id == "ven_nueva":
            self.close()
            parent.mostrar_frame(4)
            return
        if action_id == "ven_manual":
            self.close()
            try:
                parent.ir_a_venta_manual()
            except Exception:
                parent.mostrar_frame(4)
            return
        if action_id == "ven_deudas":
            self.close()
            try:
                parent.ir_a_historial_deudas()
            except Exception:
                pass
            return
        if action_id == "ven_hist":
            self.close()
            try:
                parent.ir_a_historial_ventas()
            except Exception:
                pass
            return
        if action_id == "ven_reporte":
            self.close()
            try:
                parent.ir_a_historial_ventas()
            except Exception:
                pass
            return

        if action_id == "her_barcode":
            self.close()
            try:
                parent.open_barcode_generator()
            except Exception:
                pass
            return
        if action_id == "her_sync":
            self.close()
            try:
                parent.open_sync_center()
            except Exception:
                pass
            return
        if action_id == "her_trash":
            self.close()
            try:
                parent.open_trash_recovery()
            except Exception:
                pass
            return
        if action_id == "her_audit":
            self.close()
            try:
                parent.open_audit_page()
            except Exception:
                pass
            return
        if action_id == "her_birthdays":
            self.close()
            try:
                parent.open_birthdays_page()
            except Exception:
                pass
            return

        if action_id == "nav_clientes":
            self.close()
            try:
                parent.go_to_create_cliente()
            except Exception:
                # Fallback if method not available.
                parent.mostrar_frame(-1)
            return
        if action_id == "nav_pacientes":
            self.close()
            parent.mostrar_frame(1)
            return
        if action_id == "nav_calendario":
            self.close()
            parent.mostrar_frame(6)
            return
