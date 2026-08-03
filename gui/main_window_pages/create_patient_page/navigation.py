from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLineEdit


class CreatePatientPageNavigationMixin:
    def setup_graduacion_keyboard_navigation(self):
        self._grad_nav_pos_by_widget = {}
        self._grad_nav_grid = {}
        self._grad_nav_sequence = []

        row_map = {
            ("lejos", "OD"): 0,
            ("lejos", "OI"): 1,
            ("cerca", "OD"): 2,
            ("cerca", "OI"): 3,
        }
        field_columns = [
            ("esferico", 1),
            ("cilindro", 2),
            ("eje", 3),
            ("av", 4),
            ("distp", 5),
            ("adicmedia", 6),
            ("prisma", 7),
        ]

        for vision_name, vision_widgets in [("lejos", self.lejos_form_widgets), ("cerca", self.cerca_form_widgets)]:
            for eye in ("OD", "OI"):
                row = row_map[(vision_name, eye)]
                for field_name, col in field_columns:
                    key = "distp" if field_name == "distp" else f"{field_name}_{eye}"
                    widget = vision_widgets.get(key)
                    if not isinstance(widget, QLineEdit):
                        continue
                    self._grad_nav_pos_by_widget[widget] = (row, col)
                    self._grad_nav_grid[(row, col)] = widget
                    widget.installEventFilter(self)

        self._grad_nav_sequence = [
            self._grad_nav_grid[(row, col)]
            for row in range(4)
            for col in range(1, 8)
            if (row, col) in self._grad_nav_grid
        ]

    def _find_row_target_widget(self, target_row, current_col):
        row_cols = [col for (row, col) in self._grad_nav_grid.keys() if row == target_row]
        if not row_cols:
            return None
        if current_col in row_cols:
            return self._grad_nav_grid.get((target_row, current_col))
        nearest_col = min(row_cols, key=lambda c: (abs(c - current_col), c))
        return self._grad_nav_grid.get((target_row, nearest_col))

    def _get_next_grad_widget(self, current_widget, key):
        if current_widget not in self._grad_nav_pos_by_widget:
            return None
        row, col = self._grad_nav_pos_by_widget[current_widget]
        if key in (Qt.Key_Right, Qt.Key_Left):
            if current_widget not in self._grad_nav_sequence:
                return None
            idx = self._grad_nav_sequence.index(current_widget)
            next_idx = idx + 1 if key == Qt.Key_Right else idx - 1
            if 0 <= next_idx < len(self._grad_nav_sequence):
                return self._grad_nav_sequence[next_idx]
            return None
        if key == Qt.Key_Up and row > 0:
            return self._find_row_target_widget(row - 1, col)
        if key == Qt.Key_Down and row < 3:
            return self._find_row_target_widget(row + 1, col)
        return None

    def eventFilter(self, obj, event):
        if (
            event.type() == QtCore.QEvent.KeyPress
            and isinstance(obj, QLineEdit)
            and obj in self._grad_nav_pos_by_widget
        ):
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                no_keypad_mods = event.modifiers() & ~Qt.KeypadModifier
                if no_keypad_mods != Qt.NoModifier:
                    return super().eventFilter(obj, event)
                if key == Qt.Key_Left and obj.cursorPosition() > 0 and not obj.hasSelectedText():
                    return super().eventFilter(obj, event)
                if key == Qt.Key_Right and obj.cursorPosition() < len(obj.text()) and not obj.hasSelectedText():
                    return super().eventFilter(obj, event)
                target = self._get_next_grad_widget(obj, key)
                if target:
                    target.setFocus(Qt.OtherFocusReason)
                    target.selectAll()
                    return True
        return super().eventFilter(obj, event)

    def create_graduacion_widgets(self, layout, start_row, vision_type):
        widgets = {}
        headers = ["Ojo", "Esferico", "Cilindro", "Eje", "A.V", "DIP", "Adicion", "Prisma"]
        for i, header in enumerate(headers):
            label = QLabel(f"<b>{header}</b>")
            label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            layout.addWidget(label, start_row, i)

        eyes = ["OD", "OI"]
        for i, eye in enumerate(eyes):
            eye_label = QLabel(f"<b>{eye}</b>")
            eye_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            layout.addWidget(eye_label, start_row + i + 1, 0)

            widgets[f"esferico_{eye}"] = QLineEdit()
            widgets[f"esferico_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widgets[f"cilindro_{eye}"] = QLineEdit()
            widgets[f"cilindro_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widgets[f"eje_{eye}"] = QLineEdit()
            widgets[f"eje_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            def format_eje(text, widget=widgets[f"eje_{eye}"]):
                t = text.strip().replace("°", "")
                if t:
                    try:
                        float(t)
                        widget.blockSignals(True)
                        widget.setText(f"{t}°")
                        widget.blockSignals(False)
                    except ValueError:
                        pass

            widgets[f"eje_{eye}"].textChanged.connect(lambda text, w=widgets[f"eje_{eye}"]: format_eje(text, w))
            widgets[f"av_{eye}"] = QLineEdit()
            widgets[f"av_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widgets[f"adicmedia_{eye}"] = QLineEdit()
            widgets[f"adicmedia_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widgets[f"prisma_{eye}"] = QLineEdit()
            widgets[f"prisma_{eye}"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            if eye == "OD":
                widgets["distp"] = QLineEdit()
                widgets["distp"].setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                layout.addWidget(widgets["distp"], start_row + i + 1, 5)

            layout.addWidget(widgets[f"esferico_{eye}"], start_row + i + 1, 1)
            layout.addWidget(widgets[f"cilindro_{eye}"], start_row + i + 1, 2)
            layout.addWidget(widgets[f"eje_{eye}"], start_row + i + 1, 3)
            layout.addWidget(widgets[f"av_{eye}"], start_row + i + 1, 4)
            layout.addWidget(widgets[f"adicmedia_{eye}"], start_row + i + 1, 6)
            layout.addWidget(widgets[f"prisma_{eye}"], start_row + i + 1, 7)

            if vision_type == "lejos":
                widgets[f"adicmedia_{eye}"].setHidden(False)
                if layout.itemAtPosition(start_row + i + 1, 6) and layout.itemAtPosition(start_row + i + 1, 6).widget():
                    layout.itemAtPosition(start_row + i + 1, 6).widget().setHidden(False)
                widgets[f"prisma_{eye}"].setHidden(False)
                if layout.itemAtPosition(start_row + i + 1, 7) and layout.itemAtPosition(start_row + i + 1, 7).widget():
                    layout.itemAtPosition(start_row + i + 1, 7).widget().setHidden(False)
                widgets[f"esferico_{eye}"].textChanged.connect(
                    lambda text, w=widgets, e=eye: self.update_cerca_from_lejos(w, e)
                )
                widgets[f"adicmedia_{eye}"].textChanged.connect(
                    lambda text, w=widgets, e=eye: self.update_cerca_from_lejos(w, e)
                )
            else:
                widgets[f"adicmedia_{eye}"].setHidden(False)
                if layout.itemAtPosition(start_row + i + 1, 6) and layout.itemAtPosition(start_row + i + 1, 6).widget():
                    layout.itemAtPosition(start_row + i + 1, 6).widget().setHidden(False)
                widgets[f"prisma_{eye}"].setHidden(False)
                if layout.itemAtPosition(start_row + i + 1, 7) and layout.itemAtPosition(start_row + i + 1, 7).widget():
                    layout.itemAtPosition(start_row + i + 1, 7).widget().setHidden(False)

        return widgets
