QSS_STYLE = """
/* Variables globales */
* {
    font-family: 'Segoe UI', 'Open Sans', sans-serif;
}

/* Estilo base moderno */
QWidget {
    background-color: transparent;
}

QLineEdit, QComboBox {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px 20px;
    background: white;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus {
    background: white;
    border: 2px solid #2196F3;
}

QLineEdit:hover, QComboBox:hover {
    background: white;
    border: 1px solid #2196F3;
}

QPushButton {
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1E88E5);
    color: white;
    min-height: 20px;
}

QPushButton:hover {
    background: #2196F3;
    border: 1px solid #1E88E5;
}

QPushButton:pressed {
    background: #1E88E5;
    padding: 13px 25px 11px 23px;
}

/* Contenedores con bordes */
QGroupBox {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    background: white;
    margin-top: 1em;
    padding: 20px;
}

QGroupBox::title {
    color: #424242;
    padding: 0 15px;
    font-weight: bold;
}

/* Tabla con bordes sutiles */
QTableWidget {
    background: white;
    border: none;
    border-radius: 12px;
}

QTableWidget::item {
    padding: 12px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

QTableWidget::item:selected {
    background-color: rgba(33, 150, 243, 0.1);
    color: #424242;
}

QHeaderView::section {
    background-color: white;
    padding: 16px;
    border: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    font-weight: bold;
    color: #424242;
}

/* ScrollBars minimalistas */
QScrollBar:vertical, QScrollBar:horizontal {
    border: none;
    background: #F5F5F5;
    width: 6px;
    height: 6px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #BDBDBD;
    min-height: 24px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* Header principal con gradiente mejorado */
#HeaderFrame {
    background: #2196F3;
    border: none;
    padding: 15px 25px;
    min-height: 75px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

#HeaderFrame QLabel {
    color: white;
}

#LogoLabel {
    padding: 10px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    margin: 0 5px;
}

#UserLabel {
    color: #E3F2FD !important;
    font-size: 14px;
    padding: 10px 20px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 25px;
    margin: 0 10px;
}

/* Barra de búsqueda */
QLineEdit {
    background: rgba(255, 255, 255, 0.95);
    border: 2px solid transparent;
    border-radius: 25px;
    padding: 10px 20px;
    font-size: 14px;
    min-width: 250px;
    color: #37474F;
}

QLineEdit:focus {
    background: white;
    border: 2px solid #2196F3;
}

/* Botones con diseño moderno */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #2196F3,
                              stop:1 #1976D2);
    color: white;
    border: none;
    border-radius: 25px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #1E88E5,
                              stop:1 #1565C0);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #1565C0,
                              stop:1 #0D47A1);
    padding: 13px 23px 11px 25px;
}

#logoutButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #E91E63,
                              stop:1 #C2185B);
}

#logoutButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #D81B60,
                              stop:1 #AD1457);
}

#searchButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                              stop:0 #1E88E5,
                              stop:1 #1565C0);
    border-radius: 25px;
    min-width: 120px;
    font-weight: bold;
}

/* Contenido principal con fondo suave */
QWidget#MainContent {
    background: #F5F5F5;
}

/* Páginas del stacked widget con sombra suave */
QStackedWidget > QWidget {
    background: #F5F5F5;
    padding: 25px;
}

/* Toolbar lateral moderna */
QToolBar {
    background: #FFFFFF;
    border-right: 1px solid rgba(0,0,0,0.08);
    spacing: 12px;
    padding: 20px 10px;
}

/* Tablas */
QTableWidget {
    background-color: white;
    gridline-color: #E0E0E0;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    selection-background-color: #E3F2FD;
    selection-color: #1565C0;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #F5F5F5;
}

QTableWidget::item:selected {
    background-color: #E3F2FD;
    color: #1565C0;
}

QHeaderView::section {
    background-color: #F5F5F5;
    padding: 12px;
    border: none;
    font-weight: bold;
    color: #616161;
}

/* Scroll bars modernas */
QScrollBar:vertical {
    border: none;
    background: #F5F5F5;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #F5F5F5;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #BDBDBD;
    min-width: 30px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* ComboBox moderna */
QComboBox {
    padding: 8px 15px;
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    background: white;
    min-width: 150px;
}

QComboBox:hover {
    border-color: #2196F3;
}

QComboBox:focus {
    border-color: #2196F3;
    background: #E3F2FD;
}

QComboBox::drop-down {
    border: none;
    width: 25px;
}

QComboBox::down-arrow {
    image: url(images/down-arrow.png);
    width: 12px;
    height: 12px;
}

/* DateEdit moderna */
QDateEdit {
    padding: 8px 15px;
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    background: white;
    min-width: 150px;
}

QDateEdit:hover {
    border-color: #2196F3;
}

QDateEdit:focus {
    border-color: #2196F3;
    background: #E3F2FD;
}

/* GroupBox moderna */
QGroupBox {
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 1em;
    padding: 15px;
    background: white;
}

QGroupBox::title {
    color: #1565C0;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    background: white;
}
}

QToolBar QToolButton {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 12px;
    margin: 2px;
}

QToolBar QToolButton:hover {
    background: #E3F2FD;
}

QToolBar QToolButton:pressed {
    background: #BBDEFB;
}

QToolBar QToolButton:checked {
    background: #2196F3;
}

QToolBar QToolButton:checked QIcon {
    fill: white;
}

/* Separadores del toolbar */
QToolBar::separator {
    background: #E0E0E0;
    width: 1px;
    height: 1px;
    margin: 8px 12px;
}

/* Tablas */
QTableView, QTableWidget {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 10px;
    padding: 4px;
}

QTableView::item, QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #F5F5F5;
}

QTableView::item:selected, QTableWidget::item:selected {
    background: #E3F2FD;
    color: #1565C0;
}

QHeaderView::section {
    background: #F5F5F5;
    color: #37474F;
    font-weight: 600;
    padding: 12px;
    border: none;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F5F5F5;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #9E9E9E;
}

/* Menús */
QMenu {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    padding: 8px 0;
}

QMenu::item {
    padding: 8px 24px;
}

QMenu::item:selected {
    background: #E3F2FD;
    color: #1565C0;
}

/* GroupBox */
QGroupBox {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 10px;
    margin-top: 12px;
    padding: 20px;
}

QGroupBox::title {
    color: #1565C0;
    font-weight: 600;
    font-size: 14px;
}

/* ComboBox */
QComboBox {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    padding: 8px 16px;
    min-width: 150px;
}

QComboBox:hover {
    border-color: #90CAF9;
}

QComboBox:focus {
    border-color: #2196F3;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

/* SpinBox */
QSpinBox, QDoubleSpinBox {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    padding: 8px 16px;
    min-width: 100px;
}

/* DateEdit */
QDateEdit {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    padding: 8px 16px;
    min-width: 150px;
}

/* Tooltips */
QToolTip {
    background: #424242;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}
	QMainWindow, QWidget#MainContent {
		background-color: #f7f7f7;
	}
	#SidebarContainer {
		background-color: #e0e0e0;
		border-right: 2px solid #cccccc;
	}
	#SidebarMenu QPushButton {
		background-color: #f7f7f7;
		border: 1px solid #cccccc;
		border-radius: 6px;
		color: #222;
		margin-bottom: 6px;
	}
	#SidebarMenu QPushButton:hover {
		background-color: #d0d0d0;
		color: #0078d7;
	}
	#SidebarMenu QPushButton:checked {
		background-color: #0078d7;
		color: #fff;
	}
	/* Botones por defecto: borde visible y efecto hover */
	QPushButton {
		background-color: #d4d4d4; /* gris más oscuro para mejor contraste */
		color: #000000; /* negro puro */
		border: 2px solid #666666; /* borde grueso y oscuro */
		border-radius: 8px;
		padding: 8px 16px; /* más padding horizontal */
		font-size: 14px; /* texto más grande */
		min-height: 32px; /* botón más alto */
		font-weight: 600; /* negrita */
		letter-spacing: 0.3px; /* mejor legibilidad */
	}

	QPushButton:hover {
		background-color: #c0c0c0; /* gris más oscuro en hover */
		border: 2px solid #2196F3; /* borde azul grueso */
		color: #1565C0; /* azul oscuro */
	}

	QPushButton:pressed {
		background-color: #a0a0a0; /* gris muy oscuro al presionar */
		border: 2px solid #1976D2;
		color: #000000; /* negro al presionar también */
		padding-top: 9px; /* pequeño efecto de presionado */
	}    /* Botones primarios (ej. submit) mantienen gradiente pero con borde */
    QPushButton[primary="true"] {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
        color: white;
        border: 1px solid rgba(0,0,0,0.08);
    }

    QPushButton[primary="true"]:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E88E5, stop:1 #1565C0);
        border: 1px solid rgba(0,0,0,0.12);
    }

    QGroupBox {
        border: 1px solid #cccccc;
        border-radius: 8px;
        background-color: #fff;
        margin-top: 8px;
    }

    QLabel {
        color: #222;
    }

"""