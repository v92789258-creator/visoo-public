import os
import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt5.QtQuickWidgets import QQuickWidget


class BranchQuotaBridge(QObject):
    confirmRequested = pyqtSignal(str)
    cancelRequested = pyqtSignal()

    @pyqtSlot(str)
    def confirmSelection(self, device_id: str):
        self.confirmRequested.emit(str(device_id or "").strip())

    @pyqtSlot()
    def cancel(self):
        self.cancelRequested.emit()


class BranchQuotaQmlDialog(QtWidgets.QDialog):
    def __init__(self, devices, overflow: int, max_sucursales: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccion de sucursal")
        self.setModal(True)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(760, 520)

        self._selected_device = None
        self._devices_by_id = {}
        self._allow_close = False

        model = self._build_model(devices)
        if not model:
            raise RuntimeError("No hay sucursales disponibles para seleccionar.")

        overflow_count = max(1, int(overflow or 1))
        max_count = max(0, int(max_sucursales or 0))

        title = "Una tienda fue eliminada de tu plan"
        if overflow_count > 1:
            title = f"{overflow_count} tiendas exceden tu nuevo plan"

        message = (
            f"Tu plan permite {max_count} sucursal(es). "
            "Selecciona la sucursal que quieres quitar de funcionamiento. "
            "Este aviso no se puede cerrar sin elegir una opcion."
        )

        self._bridge = BranchQuotaBridge(self)
        self._bridge.confirmRequested.connect(self._on_confirm_requested)
        self._bridge.cancelRequested.connect(self.reject)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(QtCore.Qt.transparent)

        ctx = self._quick.rootContext()
        ctx.setContextProperty("bridge", self._bridge)
        ctx.setContextProperty("modalTitle", title)
        ctx.setContextProperty("modalMessage", message)
        ctx.setContextProperty("devicesModel", model)

        qml_path = self._resolve_qml_path()
        self._quick.setSource(QUrl.fromLocalFile(qml_path))
        if self._quick.status() == QQuickWidget.Error:
            errors = [str(err.toString()) for err in self._quick.errors()]
            raise RuntimeError(f"No se pudo cargar QML: {' | '.join(errors)}")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._quick)

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()

    def reject(self):
        if self._allow_close:
            super().reject()
            return
        # Modal obligatorio: ignorar cancel/reject.
        return

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def _resolve_qml_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            qml_path = os.path.join(base_dir, "gui", "qml", "branch_quota_modal.qml")
        else:
            qml_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "qml", "branch_quota_modal.qml")
            )

        if not os.path.exists(qml_path):
            raise RuntimeError(f"No existe archivo QML: {qml_path}")
        return qml_path

    def _build_model(self, devices):
        model = []
        for dev in (devices or []):
            if not isinstance(dev, dict):
                continue

            device_id = str(dev.get("id", "")).strip()
            code = str(dev.get("codigo_dispositivo", "")).strip().upper()
            key = device_id or code
            if not key:
                continue

            nombre = str(dev.get("nombre_optica", "Sucursal")).strip() or "Sucursal"
            ciudad = str(dev.get("ciudad", "")).strip()
            estado = str(dev.get("estado", "activo")).strip().lower()
            estado_label = "ACTIVA" if estado != "bloqueado" else "BLOQUEADA"

            if ciudad:
                main_label = f"{nombre} - {ciudad}"
            else:
                main_label = nombre

            model.append(
                {
                    "id": key,
                    "code": code,
                    "mainLabel": main_label,
                    "statusLabel": estado_label,
                    "subLabel": f"Codigo: {code}" if code else "Sin codigo",
                }
            )
            self._devices_by_id[key] = dict(dev)

        return model

    def _on_confirm_requested(self, device_id: str):
        key = str(device_id or "").strip()
        selected = self._devices_by_id.get(key)
        if not isinstance(selected, dict):
            return
        self._selected_device = selected
        self._allow_close = True
        self.accept()

    def get_selected_device(self):
        return dict(self._selected_device) if isinstance(self._selected_device, dict) else None
