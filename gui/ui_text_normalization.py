# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtWidgets

from utils.text_normalizer import maybe_normalize_ui_text


def normalize_widget_texts(root_widget: QtWidgets.QWidget) -> None:
    """
    Corrige mojibake en textos de widgets (tildes/caracteres rotos).
    Diseñado para aplicarse a diálogos y QMessageBox sin tocar la lógica.
    """
    if not isinstance(root_widget, QtWidgets.QWidget):
        return

    def _normalize_get_set(getter, setter):
        try:
            original = getter()
        except Exception:
            return
        if not isinstance(original, str) or not original:
            return
        fixed = maybe_normalize_ui_text(original)
        if fixed != original:
            try:
                setter(fixed)
            except Exception:
                pass

    _normalize_get_set(root_widget.windowTitle, root_widget.setWindowTitle)

    widgets = [root_widget]
    try:
        widgets.extend(root_widget.findChildren(QtWidgets.QWidget))
    except Exception:
        pass

    for widget in widgets:
        if isinstance(widget, (QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
            _normalize_get_set(widget.text, widget.setText)

        if isinstance(widget, QtWidgets.QGroupBox):
            _normalize_get_set(widget.title, widget.setTitle)

        if isinstance(widget, QtWidgets.QLineEdit):
            _normalize_get_set(widget.placeholderText, widget.setPlaceholderText)

        if isinstance(widget, QtWidgets.QComboBox):
            try:
                for i in range(widget.count()):
                    item_text = widget.itemText(i)
                    fixed = maybe_normalize_ui_text(item_text)
                    if fixed != item_text:
                        widget.setItemText(i, fixed)
            except Exception:
                pass

        if isinstance(widget, QtWidgets.QTabWidget):
            try:
                for i in range(widget.count()):
                    tab_text = widget.tabText(i)
                    fixed = maybe_normalize_ui_text(tab_text)
                    if fixed != tab_text:
                        widget.setTabText(i, fixed)
            except Exception:
                pass

        if isinstance(widget, QtWidgets.QTableWidget):
            try:
                for i in range(widget.columnCount()):
                    item = widget.horizontalHeaderItem(i)
                    if item is None:
                        continue
                    txt = item.text()
                    fixed = maybe_normalize_ui_text(txt)
                    if fixed != txt:
                        item.setText(fixed)
            except Exception:
                pass

    try:
        for action in root_widget.findChildren(QtWidgets.QAction):
            txt = action.text()
            fixed = maybe_normalize_ui_text(txt)
            if fixed != txt:
                action.setText(fixed)
    except Exception:
        pass


class DialogTextNormalizer(QtCore.QObject):
    """
    Event filter: normaliza automáticamente los textos cuando un QDialog se muestra.
    """

    def eventFilter(self, obj, event):
        try:
            if (
                isinstance(obj, QtWidgets.QDialog)
                and event is not None
                and event.type() == QtCore.QEvent.Show
            ):
                if not bool(obj.property("_ui_text_normalized")):
                    obj.setProperty("_ui_text_normalized", True)
                    QtCore.QTimer.singleShot(0, lambda o=obj: normalize_widget_texts(o))
        except Exception:
            pass
        return super().eventFilter(obj, event)

