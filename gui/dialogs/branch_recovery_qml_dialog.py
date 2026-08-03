import os
import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt5.QtQuickWidgets import QQuickWidget


class BranchRecoveryBridge(QObject):
    recoverRequested = pyqtSignal(str)
    createNewRequested = pyqtSignal()

    @pyqtSlot(str)
    def recoverSelection(self, device_id: str):
        self.recoverRequested.emit(str(device_id or "").strip())

    @pyqtSlot()
    def createNew(self):
        self.createNewRequested.emit()


class BranchRecoveryQmlDialog(QtWidgets.QDialog):
    """
    Modal obligatorio para cuando el plan tiene cupos disponibles y existen sucursales bloqueadas.
    Permite recuperar (activar) una sucursal bloqueada o ir a crear una nueva.
    """

    def __init__(
        self,
        blocked_devices,
        free_slots: int,
        max_sucursales: int,
        active_count: int,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Recuperar sucursal")
        self.setModal(True)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(780, 540)

        self._devices_by_id = {}
        self._selected_device = None
        self._action = None  # "recover" | "create_new"
        self._allow_close = False

        model = self._build_model(blocked_devices)
        if not model:
            raise RuntimeError("No hay sucursales bloqueadas disponibles para recuperar.")

        try:
            free_slots_int = int(free_slots or 0)
        except Exception:
            free_slots_int = 0
        try:
            max_int = int(max_sucursales or 0)
        except Exception:
            max_int = 0
        try:
            active_int = int(active_count or 0)
        except Exception:
            active_int = 0

        title = "Tienes cupos disponibles"
        if free_slots_int == 1:
            title = "Tienes 1 cupo disponible"
        elif free_slots_int > 1:
            title = f"Tienes {free_slots_int} cupos disponibles"

        blocked_count = len(model)
        message = (
            f"Tu plan permite {max_int} sucursal(es). "
            f"Actualmente tienes {active_int} activa(s) y {blocked_count} bloqueada(s).\n\n"
            "Puedes recuperar (activar) una sucursal bloqueada o crear una nueva.\n"
            "Este aviso no se puede cerrar sin elegir una opcion."
        )

        self._bridge = BranchRecoveryBridge(self)
        self._bridge.recoverRequested.connect(self._on_recover_requested)
        self._bridge.createNewRequested.connect(self._on_create_new_requested)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(QtCore.Qt.transparent)

        ctx = self._quick.rootContext()
        ctx.setContextProperty("bridge", self._bridge)
        ctx.setContextProperty("modalTitle", title)
        ctx.setContextProperty("modalMessage", message)
        ctx.setContextProperty("devicesModel", model)
        ctx.setContextProperty("freeSlots", free_slots_int)

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
        # Modal obligatorio: ignorar cancel/reject.
        if self._allow_close:
            super().reject()
        return

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def _resolve_qml_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            qml_path = os.path.join(base_dir, "gui", "qml", "branch_recovery_modal.qml")
        else:
            qml_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "qml", "branch_recovery_modal.qml")
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
            if ciudad:
                main_label = f"{nombre} - {ciudad}"
            else:
                main_label = nombre

            model.append(
                {
                    "id": key,
                    "code": code,
                    "mainLabel": main_label,
                    "statusLabel": "BLOQUEADA",
                    "subLabel": f"Codigo: {code}" if code else "Sin codigo",
                }
            )
            self._devices_by_id[key] = dict(dev)
        return model

    def _on_recover_requested(self, device_id: str):
        key = str(device_id or "").strip()
        selected = self._devices_by_id.get(key)
        if not isinstance(selected, dict):
            return
        self._selected_device = selected
        self._action = "recover"
        self._allow_close = True
        self.accept()

    def _on_create_new_requested(self):
        self._action = "create_new"
        self._allow_close = True
        self.accept()

    def get_result(self):
        return {
            "action": self._action,
            "device": dict(self._selected_device) if isinstance(self._selected_device, dict) else None,
        }

