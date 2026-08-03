"""
Dialogo para configurar metas del usuario.
"""

import json
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


GOAL_ORDER = [
    "ventas_totales",
    "margen_ganancia",
    "venta_promedio",
    "stock_rotacion",
    "ventas_por_dia",
    "transacciones_por_dia",
    "ticket_promedio_minimo",
    "productos_vendidos",
    "clientes_nuevos",
]

THEME = {
    "bg_app": "#F3F6FA",
    "card_bg": "#FFFFFF",
    "card_bg_active": "#F8FBFF",
    "accent": "#0F172A",
    "text_main": "#0F172A",
    "text_dim": "#64748B",
    "border": "#D9E2EC",
    "border_active": "#93C5FD",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "primary_pressed": "#1E40AF",
    "muted_bg": "#E5EAF1",
    "muted_hover": "#D5DDE8",
}


class GoalsConfigDialog(QDialog):
    """Dialogo para configurar metas personalizadas."""

    goals_saved = pyqtSignal(list)

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.max_goals = 6
        self.selected_goals = {}
        self.goal_params = {}
        self.checkboxes = {}
        self.target_inputs = {}
        self.param_inputs = {}
        self.goal_cards = {}

        self.setWindowTitle("Configurar Metas")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setFixedSize(760, 820)
        self.setModal(True)
        self.setStyleSheet(self._build_stylesheet())

        self.init_ui()
        self.load_saved_goals()

    def _build_stylesheet(self) -> str:
        return f"""
            QDialog {{
                background-color: {THEME['bg_app']};
            }}
            QFrame#HeaderCard {{
                background-color: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                border-radius: 16px;
            }}
            QLabel#HeaderTitle {{
                color: {THEME['accent']};
                font-size: 24px;
                font-weight: 700;
            }}
            QLabel#HeaderSubtitle {{
                color: {THEME['text_dim']};
                font-size: 12px;
            }}
            QLabel#CounterBadge {{
                background-color: #EAF2FF;
                color: {THEME['primary']};
                border: 1px solid #BFDBFE;
                border-radius: 11px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QScrollArea#GoalsScroll {{
                background: transparent;
                border: none;
            }}
            QWidget#GoalsScrollContent {{
                background: transparent;
            }}
            QFrame#GoalCard {{
                background-color: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                border-radius: 14px;
            }}
            QFrame#GoalCard[active="true"] {{
                background-color: {THEME['card_bg_active']};
                border: 1px solid {THEME['border_active']};
            }}
            QCheckBox {{
                color: {THEME['text_main']};
                spacing: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {THEME['card_bg']};
                border: 2px solid {THEME['border']};
                border-radius: 5px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {THEME['primary']};
                border: 2px solid {THEME['primary']};
                border-radius: 5px;
            }}
            QLabel#GoalDescription {{
                color: {THEME['text_dim']};
                font-size: 11px;
            }}
            QLabel#GoalTag {{
                background-color: #F1F5F9;
                color: {THEME['text_dim']};
                border: 1px solid {THEME['border']};
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }}
            QLabel#FieldLabel {{
                color: {THEME['text_dim']};
                font-size: 11px;
                font-weight: 600;
            }}
            QSpinBox, QDoubleSpinBox {{
                min-height: 34px;
                padding: 4px 10px;
                background-color: {THEME['card_bg']};
                color: {THEME['text_main']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
            }}
            QSpinBox:disabled, QDoubleSpinBox:disabled {{
                background-color: #F8FAFC;
                color: #94A3B8;
            }}
            QPushButton#CancelButton {{
                min-height: 42px;
                border: none;
                border-radius: 10px;
                background-color: {THEME['muted_bg']};
                color: {THEME['text_main']};
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#CancelButton:hover {{
                background-color: {THEME['muted_hover']};
            }}
            QPushButton#SaveButton {{
                min-height: 42px;
                border: none;
                border-radius: 10px;
                background-color: {THEME['primary']};
                color: white;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#SaveButton:hover {{
                background-color: {THEME['primary_hover']};
            }}
            QPushButton#SaveButton:pressed {{
                background-color: {THEME['primary_pressed']};
            }}
        """

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(6)

        title = QLabel("Selecciona tus metas")
        title.setObjectName("HeaderTitle")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))

        subtitle = QLabel(
            f"Elige hasta {self.max_goals} metas activas y ajusta los objetivos segun tu operacion."
        )
        subtitle.setObjectName("HeaderSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header_card)

        counter_row = QHBoxLayout()
        counter_row.setContentsMargins(0, 0, 0, 0)

        helper_label = QLabel("Activa solo las metas que realmente vas a seguir.")
        helper_label.setObjectName("HeaderSubtitle")

        self.counter_label = QLabel()
        self.counter_label.setObjectName("CounterBadge")
        self._refresh_counter()

        counter_row.addWidget(helper_label)
        counter_row.addStretch()
        counter_row.addWidget(self.counter_label)
        main_layout.addLayout(counter_row)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("GoalsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        goals_container = QWidget()
        goals_container.setObjectName("GoalsScrollContent")
        goals_layout = QVBoxLayout(goals_container)
        goals_layout.setContentsMargins(2, 2, 2, 2)
        goals_layout.setSpacing(14)
        self.goals_layout = goals_layout

        for goal_id in GOAL_ORDER:
            self.goals_layout.addWidget(self._create_goal_card(goal_id))

        self.goals_layout.addStretch()
        self.scroll.setWidget(goals_container)
        main_layout.addWidget(self.scroll, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Guardar Metas")
        save_btn.setObjectName("SaveButton")
        save_btn.clicked.connect(self.save_goals)

        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        main_layout.addLayout(buttons_layout)

    def _create_goal_card(self, goal_id: str) -> QWidget:
        goal_info = self._get_goal_info(goal_id)
        goal_name = goal_info.get("name", goal_id)

        card = QFrame()
        card.setObjectName("GoalCard")
        card.setProperty("active", False)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        checkbox = QCheckBox(goal_name)
        checkbox.stateChanged.connect(lambda _, gid=goal_id: self.on_goal_toggled(gid))

        tag = QLabel(goal_info.get("unit", ""))
        tag.setObjectName("GoalTag")

        top_row.addWidget(checkbox)
        top_row.addStretch()
        if goal_info.get("unit"):
            top_row.addWidget(tag)
        card_layout.addLayout(top_row)

        description = QLabel(goal_info.get("description", ""))
        description.setObjectName("GoalDescription")
        description.setWordWrap(True)
        card_layout.addWidget(description)

        target_input = self._create_target_input(goal_info)
        self.target_inputs[goal_id] = target_input

        card_layout.addLayout(
            self._create_field_row(
                f"Objetivo ({goal_info.get('unit', '')})",
                target_input,
            )
        )

        if goal_info.get("configurable") and goal_info.get("params"):
            self.param_inputs[goal_id] = {}
            for param_name, param_config in goal_info["params"].items():
                param_spin = QSpinBox()
                param_spin.setMinimum(int(param_config.get("min", 1)))
                param_spin.setMaximum(int(param_config.get("max", 100)))
                param_spin.setValue(int(param_config.get("value", 1)))
                param_spin.setFixedWidth(150)
                param_spin.setEnabled(False)

                self.param_inputs[goal_id][param_name] = param_spin
                card_layout.addLayout(
                    self._create_field_row(
                        str(param_config.get("label", param_name)),
                        param_spin,
                    )
                )

        self.checkboxes[goal_id] = checkbox
        self.goal_cards[goal_id] = card
        self._set_goal_inputs_enabled(goal_id, False)
        return card

    def _create_target_input(self, goal_info: dict):
        goal_type = goal_info.get("type", "count")
        default_target = goal_info.get("default_target", 0)

        if goal_type in ("count", "currency"):
            spin = QSpinBox()
            spin.setMaximum(999999)
            spin.setValue(int(default_target))
        else:
            spin = QDoubleSpinBox()
            spin.setMaximum(9999.99)
            spin.setDecimals(2)
            spin.setValue(float(default_target))

        spin.setFixedWidth(150)
        spin.setEnabled(False)
        return spin

    def _create_field_row(self, label_text: str, field_widget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(28, 0, 0, 0)
        row.setSpacing(10)

        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        label.setMinimumWidth(130)

        row.addWidget(label)
        row.addWidget(field_widget, 0, Qt.AlignLeft)
        row.addStretch()
        return row

    def _set_goal_inputs_enabled(self, goal_id: str, enabled: bool):
        target_input = self.target_inputs.get(goal_id)
        if target_input is not None:
            target_input.setEnabled(enabled)

        for param_input in self.param_inputs.get(goal_id, {}).values():
            param_input.setEnabled(enabled)

    def _set_goal_card_active(self, goal_id: str, active: bool):
        card = self.goal_cards.get(goal_id)
        if card is None:
            return

        card.setProperty("active", bool(active))
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()

    def _collect_goal_params(self, goal_id: str) -> dict:
        params = {}
        for param_name, param_input in self.param_inputs.get(goal_id, {}).items():
            params[param_name] = param_input.value()
        return params

    def _refresh_counter(self):
        selected_count = len(self.selected_goals)
        self.counter_label.setText(f"Metas activas: {selected_count}/{self.max_goals}")

    def _get_goal_info(self, goal_id: str) -> dict:
        from gui.dialogs.goals_calculator import AVAILABLE_GOALS as CALC_GOALS

        if goal_id in CALC_GOALS:
            return CALC_GOALS[goal_id]

        return {
            "name": goal_id,
            "description": "",
            "unit": "",
            "type": "count",
            "default_target": 0,
            "configurable": False,
            "params": {},
        }

    def on_goal_toggled(self, goal_id: str):
        checkbox = self.checkboxes[goal_id]
        target_input = self.target_inputs[goal_id]

        if checkbox.isChecked():
            if goal_id not in self.selected_goals and len(self.selected_goals) >= self.max_goals:
                QMessageBox.warning(
                    self,
                    "Limite de metas",
                    f"Solo puedes seleccionar {self.max_goals} metas como maximo.",
                    QMessageBox.Ok,
                )
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
                return

            self.selected_goals[goal_id] = target_input.value()
            self.goal_params[goal_id] = self._collect_goal_params(goal_id)
            self._set_goal_inputs_enabled(goal_id, True)
            self._set_goal_card_active(goal_id, True)
        else:
            self.selected_goals.pop(goal_id, None)
            self.goal_params.pop(goal_id, None)
            self._set_goal_inputs_enabled(goal_id, False)
            self._set_goal_card_active(goal_id, False)

        self._refresh_counter()

    def load_saved_goals(self):
        try:
            config_dir = f"VISO/{self.username}/config"
            os.makedirs(config_dir, exist_ok=True)

            config_file = f"{config_dir}/goals.json"
            if not os.path.exists(config_file):
                return

            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            goal_ids = data.get("goals", [])
            targets = data.get("targets", {})
            params_map = data.get("params", {})

            for goal_id in goal_ids:
                if goal_id not in self.checkboxes:
                    continue

                checkbox = self.checkboxes[goal_id]
                target_input = self.target_inputs[goal_id]
                saved_target = targets.get(goal_id, target_input.value())
                saved_params = params_map.get(goal_id, {}) if isinstance(params_map, dict) else {}

                checkbox.blockSignals(True)
                checkbox.setChecked(True)
                checkbox.blockSignals(False)

                target_input.setValue(saved_target)
                self.selected_goals[goal_id] = saved_target

                for param_name, param_input in self.param_inputs.get(goal_id, {}).items():
                    param_input.setValue(int(saved_params.get(param_name, param_input.value())))

                self.goal_params[goal_id] = self._collect_goal_params(goal_id)
                self._set_goal_inputs_enabled(goal_id, True)
                self._set_goal_card_active(goal_id, True)

            self._refresh_counter()
        except Exception as exc:
            print(f"[ERROR] Error cargando metas: {exc}")

    def save_goals(self):
        if len(self.selected_goals) == 0:
            QMessageBox.warning(
                self,
                "Metas requeridas",
                "Debes seleccionar al menos una meta.",
                QMessageBox.Ok,
            )
            return

        try:
            targets = {}
            params = {}
            for goal_id in list(self.selected_goals.keys()):
                targets[goal_id] = self.target_inputs[goal_id].value()
                params[goal_id] = self._collect_goal_params(goal_id)

            config_dir = f"VISO/{self.username}/config"
            os.makedirs(config_dir, exist_ok=True)
            config_file = f"{config_dir}/goals.json"

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "goals": list(targets.keys()),
                        "targets": targets,
                        "params": params,
                        "max_goals": self.max_goals,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            QMessageBox.information(
                self,
                "Metas guardadas",
                "La configuracion de metas fue actualizada correctamente.",
                QMessageBox.Ok,
            )
            self.goals_saved.emit(list(targets.keys()))
            self.accept()
        except Exception as exc:
            print(f"[ERROR] Error guardando metas: {exc}")
            QMessageBox.critical(
                self,
                "Error",
                "No se pudieron guardar las metas.",
                QMessageBox.Ok,
            )
