from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QToolButton, QFrame


class RibbonGroup(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName('RibbonGroup')
        self.setStyleSheet('''
        QFrame#RibbonGroup {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 8px;
            padding: 8px;
            margin: 4px;
        }
        QLabel { 
            color: #424242;
            font-weight: 600;
            font-size: 11px;
            margin-top: 4px;
        }
        ''')
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        self.tools_layout = QHBoxLayout()
        v.addLayout(self.tools_layout)
        self.title_label = QLabel(title)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(self.title_label)

    def add_tool(self, widget):
        self.tools_layout.addWidget(widget)


class RibbonHeader(QWidget):
    """Un header tipo 'ribbon' simple, con grupos y botones grandes.

    Integrarlo debajo del header principal para dar la sensación tipo Word/Excel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('RibbonHeader')
        self.setMinimumHeight(92)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Layout principal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Grupo Clipboard
        grp_clip = RibbonGroup('Portapapeles', self)
        for name in (('Cortar', '✂'), ('Copiar', '📋'), ('Pegar', '📌')):
            btn = QToolButton()
            btn.setText(f"{name[1]}\n{name[0]}")
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedSize(68, 58)
            grp_clip.add_tool(btn)
        layout.addWidget(grp_clip)

        # Grupo Fuente
        grp_font = RibbonGroup('Fuente', self)
        for name in (('Negrita', 'B'), ('Cursiva', 'I'), ('Subrayado', 'U')):
            btn = QToolButton()
            btn.setText(name[1])
            btn.setToolTip(name[0])
            btn.setCheckable(True)
            btn.setFixedSize(42, 34)
            grp_font.add_tool(btn)
        layout.addWidget(grp_font)

        # Grupo Alineación
        grp_align = RibbonGroup('Párrafo', self)
        for name in (('Izquierda', '↤'), ('Centro', '↔'), ('Derecha', '↦')):
            btn = QToolButton()
            btn.setText(name[1])
            btn.setToolTip(name[0])
            btn.setFixedSize(42, 34)
            grp_align.add_tool(btn)
        layout.addWidget(grp_align)

        # Grupo Documento (acciones)
        grp_doc = RibbonGroup('Documento', self)
        for name in (('Guardar', '💾'), ('Imprimir', '🖨')):
            btn = QToolButton()
            btn.setText(f"{name[1]} {name[0]}")
            btn.setFixedSize(92, 38)
            grp_doc.add_tool(btn)
        layout.addWidget(grp_doc)

        layout.addStretch()

        # Estilo ligero para que combine con QSS del proyecto
        self.setStyleSheet('''
        QWidget#RibbonHeader { 
            background: #ffffff; 
            border-bottom: 1px solid #e8eef8;
        }
        QToolButton { 
            font-size: 12px;
            border: none;
            border-radius: 6px;
            color: #424242;
            background: transparent;
        }
        QToolButton:hover {
            background: rgba(33, 150, 243, 0.1);
        }
        QToolButton:pressed {
            background: rgba(33, 150, 243, 0.2);
        }
        QToolButton:checked {
            background: rgba(33, 150, 243, 0.15);
            color: #2196F3;
            font-weight: bold;
        }
        ''')
