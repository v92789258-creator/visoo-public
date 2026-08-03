from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


class ProductMigrationDialog(QtWidgets.QDialog):
    def __init__(self, estimated_seconds=12, product_count=0, parent=None):
        super().__init__(parent)
        self._estimated_seconds = max(1, int(estimated_seconds or 1))
        self._product_count = max(0, int(product_count or 0))
        self._elapsed_seconds = 0
        self._finished = False

        self.setWindowTitle("Migrando inventario")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog { background: #ffffff; }
            QLabel#title { font-size: 20px; font-weight: 700; color: #0f172a; }
            QLabel#subtitle { font-size: 13px; color: #475569; }
            QLabel#meta { font-size: 12px; color: #64748b; }
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:disabled { background: #94a3b8; color: #e2e8f0; }
            QProgressBar {
                border: 1px solid #dbe2ea;
                border-radius: 8px;
                background: #f8fafc;
                height: 14px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #2563eb;
                border-radius: 7px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        self.title_label = QtWidgets.QLabel("Hola :D estamos migrando tus datos")
        self.title_label.setObjectName("title")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.subtitle_label = QtWidgets.QLabel(
            "Estamos moviendo tu inventario a una base de datos mas segura. Por favor espera."
        )
        self.subtitle_label.setObjectName("subtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        product_text = f"Productos detectados: {self._product_count}" if self._product_count else "Productos detectados: preparando conteo"
        self.meta_label = QtWidgets.QLabel(product_text)
        self.meta_label.setObjectName("meta")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.note_label = QtWidgets.QLabel("")
        self.note_label.setObjectName("meta")
        self.note_label.setWordWrap(True)
        self.note_label.setVisible(False)
        layout.addWidget(self.note_label)

        self.estimate_label = QtWidgets.QLabel("")
        self.estimate_label.setObjectName("meta")
        self.estimate_label.setWordWrap(True)
        layout.addWidget(self.estimate_label)

        actions = QtWidgets.QHBoxLayout()
        actions.addStretch(1)
        self.close_button = QtWidgets.QPushButton("Cerrar")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setVisible(False)
        actions.addWidget(self.close_button)
        layout.addLayout(actions)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._refresh_estimate_label()
        self._timer.start()

    def _refresh_estimate_label(self):
        if self._finished:
            return
        remaining = max(0, self._estimated_seconds - self._elapsed_seconds)
        elapsed_text = f"{self._elapsed_seconds}s"
        remaining_text = f"{remaining}s" if remaining > 0 else "menos de 1s"
        self.estimate_label.setText(
            f"Tiempo estimado de espera: {self._estimated_seconds}s aprox. | Transcurrido: {elapsed_text} | Restante: {remaining_text}"
        )

    def _tick(self):
        if self._finished:
            return
        self._elapsed_seconds += 1
        self._refresh_estimate_label()

    def mark_finished(self, success=True, detail=""):
        self._finished = True
        self._timer.stop()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        self.title_label.setText("Migracion completada" if success else "Migracion detenida")
        detail = str(detail or "").strip()
        if detail:
            self.subtitle_label.setText(detail)
        elif success:
            self.subtitle_label.setText("Tus productos ya quedaron listos en la base de datos.")
        else:
            self.subtitle_label.setText("No se pudo completar la migracion del inventario.")
        self.estimate_label.setText(
            f"Tiempo total: {self._elapsed_seconds}s"
        )
        self.close_button.setVisible(True)
        self.close_button.setFocus()
