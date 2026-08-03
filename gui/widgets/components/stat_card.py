"""
Stat card components for the dashboard.
"""

import os

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)


THEME = {
    "bg_app": "#F3F6FB",
    "card_bg": "#FFFFFF",
    "card_hover": "#F8FAFC",
    "card_border": "#E2E8F0",
    "accent": "#0F172A",
    "text_main": "#172033",
    "text_dim": "#64748B",
    "border": "#E2E8F0",
    "border_hover": "#CBD5E1",
    "icon_bg": "#EFF5FF",
    "primary": "#2563EB",
    "success": "#16A34A",
}


class ClickableLabel(QLabel):
    """Clickable label used as a secondary action."""

    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_style(hovered=False)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

    def _apply_style(self, hovered=False):
        bg = THEME["card_hover"] if hovered else THEME["card_bg"]
        border = THEME["border_hover"] if hovered else THEME["border"]
        self.setStyleSheet(
            f"""
            padding: 10px 12px;
            background-color: {bg};
            color: {THEME['accent']};
            border: 1px solid {border};
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            """
        )

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(hovered=False)
        super().leaveEvent(event)


class ClickableTrendLabel(QLabel):
    """Trend chip that can behave like a lightweight action."""

    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interactive = False
        self.setCursor(Qt.ArrowCursor)

    def setInteractive(self, enabled: bool):
        self._interactive = bool(enabled)
        self.setCursor(Qt.PointingHandCursor if self._interactive else Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if self._interactive and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ModernStatCard(QFrame):
    """Premium-looking metric card for the dashboard."""

    trend_clicked = pyqtSignal()

    def __init__(self, title, value, icon, trend="", parent=None):
        super().__init__(parent)
        self.setObjectName("ModernStatCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(118)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.original_title = title
        self.original_value = value
        self.original_trend = trend
        self._trend_color = THEME["success"]
        self._icon_bg = "#EEF4FF"
        self._icon_border = "#D7E5FF"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        self.icon_frame = QFrame()
        self.icon_frame.setObjectName("ModernStatCardIcon")
        self.icon_frame.setFixedSize(68, 68)
        icon_layout = QVBoxLayout(self.icon_frame)
        icon_layout.setContentsMargins(10, 10, 10, 10)
        icon_layout.setSpacing(0)
        icon_layout.setAlignment(Qt.AlignCenter)

        if os.path.exists(str(icon)):
            svg_widget = QSvgWidget(str(icon))
            svg_widget.setFixedSize(40, 40)
            icon_layout.addWidget(svg_widget, alignment=Qt.AlignCenter)
        else:
            icon_box = QLabel(str(icon or ""))
            icon_box.setAlignment(Qt.AlignCenter)
            icon_box.setFont(QFont("Segoe UI", 20, QFont.Bold))
            icon_box.setStyleSheet(
                f"background: transparent; color: {THEME['accent']}; border: none;"
            )
            icon_layout.addWidget(icon_box, alignment=Qt.AlignCenter)

        layout.addWidget(self.icon_frame)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        info_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_title = QLabel(str(title).upper())
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.lbl_title.setStyleSheet(
            f"color: {THEME['text_dim']}; border: none; background: transparent;"
        )

        self.lbl_value = QLabel(str(value))
        self.lbl_value.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.lbl_value.setStyleSheet(
            f"color: {THEME['accent']}; border: none; background: transparent;"
        )

        self.lbl_trend = ClickableTrendLabel(str(trend or ""))
        self.lbl_trend.setWordWrap(True)
        self.lbl_trend.clicked.connect(self.trend_clicked.emit)
        self._apply_trend_style()

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_value)
        info_layout.addWidget(self.lbl_trend)

        layout.addLayout(info_layout, 1)

        self.action_chip = QLabel("Ver")
        self.action_chip.setObjectName("ModernStatCardAction")
        self.action_chip.setAlignment(Qt.AlignCenter)
        self.action_chip.setFixedHeight(28)
        self.action_chip.setMinimumWidth(44)
        layout.addWidget(self.action_chip, alignment=Qt.AlignTop)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(26)
        self.shadow.setColor(QColor(15, 23, 42, 18))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)

        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self.adjust_font_sizes)
        self.resize_timer.setSingleShot(True)

        self._apply_card_style(hovered=False)

    def _apply_card_style(self, hovered=False):
        bg = THEME["card_hover"] if hovered else THEME["card_bg"]
        border = THEME["border_hover"] if hovered else THEME["card_border"]
        icon_bg = "#E6F0FF" if hovered else self._icon_bg
        self.setStyleSheet(
            f"""
            QFrame#ModernStatCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            QFrame#ModernStatCardIcon {{
                background: {icon_bg};
                border: 1px solid {self._icon_border};
                border-radius: 18px;
            }}
            QLabel#ModernStatCardAction {{
                color: {THEME['primary']};
                background: #F8FBFF;
                border: 1px solid #D7E5FF;
                border-radius: 14px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 10px;
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(100)

    def adjust_font_sizes(self):
        available_width = self.width() - 150

        if available_width < 150:
            self.lbl_title.setFont(QFont("Segoe UI", 7, QFont.Bold))
            self.lbl_value.setFont(QFont("Segoe UI", 16, QFont.Bold))
        elif available_width < 200:
            self.lbl_title.setFont(QFont("Segoe UI", 7, QFont.Bold))
            self.lbl_value.setFont(QFont("Segoe UI", 18, QFont.Bold))
        else:
            self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
            self.lbl_value.setFont(QFont("Segoe UI", 22, QFont.Bold))

    def enterEvent(self, event):
        self._apply_card_style(hovered=True)
        self.shadow.setBlurRadius(32)
        self.shadow.setColor(QColor(15, 23, 42, 24))
        self.shadow.setOffset(0, 10)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_card_style(hovered=False)
        self.shadow.setBlurRadius(26)
        self.shadow.setColor(QColor(15, 23, 42, 18))
        self.shadow.setOffset(0, 8)
        super().leaveEvent(event)

    def setValue(self, val):
        self.lbl_value.setText(str(val))

    def _apply_trend_style(self):
        trend_qcolor = QColor(self._trend_color)
        red, green, blue, _ = trend_qcolor.getRgb()
        self.lbl_trend.setStyleSheet(
            "border: none; "
            f"color: {self._trend_color}; "
            f"background: rgba({red}, {green}, {blue}, 18); "
            "font-size: 10px; font-weight: 700; "
            "padding: 5px 8px; border-radius: 10px;"
        )

    def setTrend(self, trend_text, color=None):
        self.lbl_trend.setText(str(trend_text or ""))
        if color:
            self._trend_color = color
        self._apply_trend_style()

    def setTrendInteractive(self, enabled: bool):
        try:
            self.lbl_trend.setInteractive(bool(enabled))
        except Exception:
            pass
