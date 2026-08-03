from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget


def show_all_sales_history(page):
    page._show_all_sales_requested = True

    try:
        if hasattr(page, "payment_method_combo") and page.payment_method_combo is not None:
            page.payment_method_combo.blockSignals(True)
            try:
                index_todos = page.payment_method_combo.findData("todos")
                if index_todos >= 0:
                    page.payment_method_combo.setCurrentIndex(index_todos)
            finally:
                page.payment_method_combo.blockSignals(False)
    except Exception:
        pass

    all_sales = getattr(page, "_all_sales", None)
    if isinstance(all_sales, list) and all_sales:
        try:
            page.empty_message.setVisible(False)
            page.sales_table.setVisible(True)
        except Exception:
            pass
        page.update_sales_history_table(all_sales)
        page._show_all_sales_requested = False
        return

    page._reload_sales()


def build_payment_filter(page):
    payment_filter = QWidget()
    payment_filter.setStyleSheet(
        """
        QWidget {
            background: white;
            border-radius: 10px;
            padding: 15px;
        }
        QLabel {
            color: #495057;
            font-weight: bold;
            font-size: 12px;
        }
        QComboBox {
            padding: 8px 10px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            min-width: 200px;
            background: white;
            color: #333333;
            font-size: 12px;
            font-weight: 500;
        }
        QComboBox:focus {
            border: 2px solid #0d6efd;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        """
    )
    payment_filter_layout = QHBoxLayout(payment_filter)
    payment_filter_layout.setSpacing(15)
    payment_filter_layout.addWidget(QLabel("Filtrar por Metodo de Pago:"))

    page.payment_method_combo = QComboBox()
    page.payment_method_combo.currentTextChanged.connect(page._on_payment_method_changed)
    try:
        from utils.file_handler import cargar_metodos_pago

        metodos_pago = cargar_metodos_pago(page.username)
        page.payment_method_combo.addItem("Todos", "todos")
        if metodos_pago:
            for metodo in metodos_pago:
                page.payment_method_combo.addItem(str(metodo), str(metodo).lower())
    except Exception:
        page.payment_method_combo.addItem("Todos", "todos")

    payment_filter_layout.addWidget(page.payment_method_combo)

    page.btn_all_sales = QPushButton("ALL")
    page.btn_all_sales.setToolTip("Mostrar todas las ventas y servicios de graduacion de la nube")
    page.btn_all_sales.setStyleSheet(
        """
        QPushButton {
            background: #111827;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        QPushButton:hover {
            background: #1f2937;
        }
        QPushButton:pressed {
            background: #0f172a;
        }
        """
    )
    page.btn_all_sales.clicked.connect(page.show_all_sales_history)
    payment_filter_layout.addWidget(page.btn_all_sales)
    payment_filter_layout.addStretch()
    return payment_filter
