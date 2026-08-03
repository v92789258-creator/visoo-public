from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QCheckBox, QWidget


class MotilidadEyeWidget(QWidget):
    """Widget de un ojo para motilidad: ejes + 6 casillas alrededor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(236, 198)
        self.setStyleSheet(
            """
            QWidget {
                background: #F8FAFC;
                border: 1px solid #D9E1EC;
                border-radius: 12px;
            }
        """
        )
        self.campos = {}
        self._crear_campos()

    def _crear_campo(self, key, x, y):
        campo = QCheckBox(self)
        campo.setObjectName(f"motilidad_{key}")
        campo.setText("")
        campo.setFixedSize(34, 34)
        campo.move(x, y)
        campo.setStyleSheet(
            """
            QCheckBox {
                background: transparent;
                padding-left: 5px;
                padding-top: 5px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 4px;
                border: 1px solid #9FB0C5;
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background: #1F7AE0;
                border: 1px solid #1565C0;
            }
        """
        )
        self.campos[key] = campo

    def _crear_campos(self):
        self._crear_campo("arriba", 101, 24)
        self._crear_campo("izq_arriba", 34, 64)
        self._crear_campo("der_arriba", 170, 64)
        self._crear_campo("izq_abajo", 34, 106)
        self._crear_campo("der_abajo", 170, 106)
        self._crear_campo("abajo", 101, 148)

    def get_values(self):
        return {k: v.isChecked() for k, v in self.campos.items()}

    def set_values(self, values):
        values = values or {}
        for key, checkbox in self.campos.items():
            checkbox.setChecked(bool(values.get(key, False)))

    def clear_values(self):
        for checkbox in self.campos.values():
            checkbox.setChecked(False)

    def any_checked(self):
        return any(checkbox.isChecked() for checkbox in self.campos.values())

    def set_interactive(self, enabled):
        for checkbox in self.campos.values():
            checkbox.setEnabled(bool(enabled))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor("#8EA1B8"), 2)
        painter.setPen(pen)
        center_x = self.width() // 2
        center_y = self.height() // 2
        margin = 24
        painter.drawLine(margin, margin, self.width() - margin, self.height() - margin)
        painter.drawLine(self.width() - margin, margin, margin, self.height() - margin)
        painter.drawLine(margin, center_y, self.width() - margin, center_y)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#6D819A")))
        painter.drawEllipse(QtCore.QPoint(center_x, center_y), 4, 4)


class MotilidadDialog(QtWidgets.QDialog):
    """Ventana de motilidad (versiones)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motilidad")
        self.setModal(True)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(620, 430)
        self.valores = {"od": {}, "oi": {}}
        self._modo_ambos = False
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("Motilidad / Versiones")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #191919;")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Marca las posiciones observadas para OD y OI.")
        subtitle.setStyleSheet("font-size: 12px; color: #5F6B7A;")
        layout.addWidget(subtitle)

        self.toggle_modo = QtWidgets.QCheckBox("Usar los mismos valores para ambos ojos")
        self.toggle_modo.toggled.connect(self._on_toggle_modo)
        layout.addWidget(self.toggle_modo)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(16)

        od_group = QtWidgets.QGroupBox("OD")
        od_layout = QtWidgets.QVBoxLayout(od_group)
        self.od_widget = MotilidadEyeWidget()
        od_layout.addWidget(self.od_widget, 0, QtCore.Qt.AlignCenter)

        oi_group = QtWidgets.QGroupBox("OI")
        oi_layout = QtWidgets.QVBoxLayout(oi_group)
        self.oi_widget = MotilidadEyeWidget()
        oi_layout.addWidget(self.oi_widget, 0, QtCore.Qt.AlignCenter)

        content.addWidget(od_group)
        content.addWidget(oi_group)
        layout.addLayout(content)

        self.od_sync_connections = []
        for checkbox in self.od_widget.campos.values():
            conn = checkbox.toggled.connect(self._sync_od_to_oi_if_needed)
            self.od_sync_connections.append(conn)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        clear_btn = QtWidgets.QPushButton("Limpiar")
        clear_btn.clicked.connect(self._clear_all)
        buttons.addButton(clear_btn, QtWidgets.QDialogButtonBox.ResetRole)

        layout.addWidget(buttons)

    def _clear_all(self):
        self.od_widget.clear_values()
        self.oi_widget.clear_values()

    def _on_toggle_modo(self, checked):
        self._modo_ambos = bool(checked)
        self.sync_modo_desde_valores()

    def _sync_od_to_oi_if_needed(self):
        if not self._modo_ambos:
            return
        self.oi_widget.set_values(self.od_widget.get_values())

    def sync_modo_desde_valores(self):
        self.oi_widget.set_interactive(not self._modo_ambos)
        if self._modo_ambos:
            self.oi_widget.set_values(self.od_widget.get_values())

    def accept(self):
        if self._modo_ambos:
            self.oi_widget.set_values(self.od_widget.get_values())
        self.valores = {
            "od": self.od_widget.get_values(),
            "oi": self.oi_widget.get_values(),
        }
        super().accept()
