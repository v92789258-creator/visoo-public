from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem


class CreatePatientPageUiHelpersMixin:
    def mostrar_tabla_clientes(self):
        from utils.file_handler import cargar_clientes

        clientes = cargar_clientes(self.username)
        if not hasattr(self, "clientes_table"):
            self.clientes_table = QTableWidget()
            self.clientes_table.setColumnCount(2)
            self.clientes_table.setHorizontalHeaderLabels(["DNI", "Nombre"])
            self.clientes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.clientes_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.clientes_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.layout().addWidget(self.clientes_table)
        self.clientes_table.setRowCount(0)
        for row, cliente in enumerate(clientes):
            self.clientes_table.insertRow(row)
            self.clientes_table.setItem(row, 0, QTableWidgetItem(cliente.get("dni", "")))
            self.clientes_table.setItem(row, 1, QTableWidgetItem(cliente.get("nombre", "")))

    def resizeEvent(self, event):
        width = self.width()
        if width < 600:
            font_size = 11
            title_size = 16
            padding = 6
        elif width < 1000:
            font_size = 13
            title_size = 20
            padding = 12
        else:
            font_size = 15
            title_size = 26
            padding = 20

        font = self.font()
        font.setPointSize(font_size)
        self.setFont(font)

        if hasattr(self, "findChild"):
            title_label = self.findChild(QLabel)
            if title_label:
                title_font = title_label.font()
                title_font.setPointSize(title_size)
                title_label.setFont(title_font)

        if hasattr(self, "layout") and self.layout():
            self.layout().setContentsMargins(padding, padding, padding, padding)

        super().resizeEvent(event)

    def update_lejos_from_cerca(self, cerca_widgets, eye=None):
        adic_key = f"adicmedia_{eye}" if eye else "adicmedia_OD"
        adic_str = cerca_widgets[adic_key].text().replace(",", ".").strip()

        if eye:
            esferico_cerca_str = cerca_widgets[f"esferico_{eye}"].text().replace(",", ".").strip()
            if self.lejos_form_widgets and f"esferico_{eye}" in self.lejos_form_widgets:
                lejos_esf_widget = self.lejos_form_widgets[f"esferico_{eye}"]
                if esferico_cerca_str and adic_str:
                    try:
                        esferico_cerca = float(esferico_cerca_str)
                        adic = float(adic_str)
                        esferico_lejos = esferico_cerca + adic
                        nuevo_esf = f"{esferico_lejos:.2f}"
                        lejos_esf_widget.blockSignals(True)
                        lejos_esf_widget.setText(nuevo_esf)
                        lejos_esf_widget.blockSignals(False)
                    except ValueError:
                        pass

        if adic_str and self.lejos_form_widgets and "distp" in self.lejos_form_widgets and "distp" in cerca_widgets:
            dip_cerca_str = cerca_widgets["distp"].text().replace(",", ".").strip()
            if dip_cerca_str:
                try:
                    dip_cerca = float(dip_cerca_str)
                    dip_lejos = dip_cerca - 2
                    nuevo_dip = f"{dip_lejos:.2f}"
                    self.lejos_form_widgets["distp"].blockSignals(True)
                    self.lejos_form_widgets["distp"].setText(nuevo_dip)
                    self.lejos_form_widgets["distp"].blockSignals(False)
                except ValueError:
                    pass

    def update_cerca_from_lejos(self, lejos_widgets, eye=None):
        if not eye:
            return

        esferico_lejos_str = lejos_widgets[f"esferico_{eye}"].text().replace(",", ".").strip()
        adic_str = lejos_widgets[f"adicmedia_{eye}"].text().replace(",", ".").strip()

        if self.cerca_form_widgets and f"esferico_{eye}" in self.cerca_form_widgets:
            cerca_esf_widget = self.cerca_form_widgets[f"esferico_{eye}"]
            if esferico_lejos_str and adic_str:
                try:
                    esferico_lejos = float(esferico_lejos_str)
                    adic = float(adic_str)
                    esferico_cerca = esferico_lejos + adic
                    nuevo_esf = f"{esferico_cerca:.2f}"
                    cerca_esf_widget.blockSignals(True)
                    cerca_esf_widget.setText(nuevo_esf)
                    cerca_esf_widget.blockSignals(False)
                except ValueError:
                    pass

    def _default_motilidad_versiones(self):
        keys = ("arriba", "izq_arriba", "der_arriba", "izq_abajo", "der_abajo", "abajo")
        return {"od": {k: False for k in keys}, "oi": {k: False for k in keys}}

    def _normalize_motilidad_versiones(self, data):
        base = self._default_motilidad_versiones()
        if not isinstance(data, dict):
            return base
        for eye in ("od", "oi"):
            eye_data = data.get(eye, {})
            if not isinstance(eye_data, dict):
                continue
            for key in base[eye]:
                base[eye][key] = bool(eye_data.get(key, False))
        return base

    def create_svg_icon(self, svg_str, size=24):
        from PyQt5.QtGui import QIcon, QPainter, QPixmap
        from PyQt5.QtSvg import QSvgRenderer

        pixmap = QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        renderer = QSvgRenderer(svg_str.encode())
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def create_loader_icon(self, rotation=0):
        from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.translate(size // 2, size // 2)
        painter.rotate(rotation)
        painter.translate(-(size // 2), -(size // 2))
        rect = QtCore.QRect(2, 2, size - 4, size - 4)
        painter.drawArc(rect, 0, 270 * 16)
        painter.end()
        return QIcon(pixmap)

    def create_check_icon(self):
        svg_str = """
            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <path d="M5 12l5 5L19 7"/>
            </svg>
        """
        return self.create_svg_icon(svg_str, 24)

    def create_x_icon(self):
        svg_str = """
            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <path d="M6 6l12 12M18 6L6 18"/>
            </svg>
        """
        return self.create_svg_icon(svg_str, 24)

    def start_loader_animation(self):
        if not self.btn_buscar_dni:
            return
        self.loader_rotation = 0
        self.btn_buscar_dni.setEnabled(False)
        if self.loader_timer:
            self.loader_timer.stop()
        self.loader_timer = QTimer()
        self.loader_timer.timeout.connect(self.update_loader_animation)
        self.loader_timer.start(30)

    def update_loader_animation(self):
        if not self.btn_buscar_dni:
            return
        self.loader_rotation = (self.loader_rotation + 10) % 360
        self.btn_buscar_dni.setIcon(self.create_loader_icon(self.loader_rotation))

    def stop_loader_animation(self, success=True):
        if not self.btn_buscar_dni:
            return
        if self.loader_timer:
            self.loader_timer.stop()
            self.loader_timer = None
        self.btn_buscar_dni.setIcon(self.create_check_icon() if success else self.create_x_icon())
        self.btn_buscar_dni.setEnabled(True)
        QTimer.singleShot(2000, self.restore_search_icon)

    def restore_search_icon(self):
        if not self.btn_buscar_dni:
            return
        original_icon = self.create_svg_icon(
            """
            <svg viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="1.5">
                <circle cx="9" cy="9" r="6" fill="none"/>
                <path d="M15 15l6 6"/>
            </svg>
        """,
            24,
        )
        self.btn_buscar_dni.setIcon(original_icon)
        self.btn_buscar_dni.setEnabled(True)
