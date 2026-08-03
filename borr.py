import sys
import math
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QFileDialog, QMessageBox, 
                             QFrame, QGroupBox, QRadioButton, QProgressBar, QToolBar,
                             QAction, QSplashScreen, QDesktopWidget, QSpinBox, QSplitter)
from PyQt5.QtGui import (QPixmap, QImage, QColor, QPainter, QPen, QBrush, 
                         QCursor, QIcon, QKeySequence, QFont, QRadialGradient)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QPoint, QRect, QSize, QTimer, QEvent)

# =================================================================================
#  UTILIDADES GRÁFICAS (Iconos generados por código para no depender de archivos)
# =================================================================================
class IconFactory:
    @staticmethod
    def create_icon(shape_type, color):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if shape_type == "folder":
            painter.setBrush(QColor("#f1c40f"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(4, 8, 24, 16)
            painter.drawRect(4, 4, 12, 4)
        elif shape_type == "save":
            painter.setBrush(QColor("#2980b9"))
            painter.drawRect(6, 6, 20, 20)
            painter.setBrush(Qt.white)
            painter.drawRect(10, 6, 12, 10)
        elif shape_type == "wand":
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(8, 24, 24, 8)
            painter.setBrush(Qt.yellow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(22, 6, 6, 6)
        elif shape_type == "eraser":
            painter.setBrush(QColor("#e74c3c"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(8, 8, 16, 16, 4, 4)
            painter.setBrush(Qt.white)
            painter.drawRect(8, 8, 16, 8)
        elif shape_type == "hand":
            painter.setPen(QPen(Qt.white, 2))
            painter.drawRoundedRect(10, 10, 12, 12, 3, 3)
            
        painter.end()
        return QIcon(pixmap)

# =================================================================================
#  LÓGICA MATEMÁTICA (WORKERS)
# =================================================================================
class WorkerMagic(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(QImage)
    
    def __init__(self, img, target_color, tolerance, mode="GLOBAL", seed=None):
        super().__init__()
        self.img = img
        self.target_color = target_color
        self.tolerance = tolerance
        self.mode = mode
        self.seed = seed

    def run(self):
        new_img = self.img.copy()
        new_img = new_img.convertToFormat(QImage.Format_ARGB32)
        w, h = new_img.width(), new_img.height()
        
        threshold = (self.tolerance / 100.0) * 441.67
        tr, tg, tb = self.target_color.red(), self.target_color.green(), self.target_color.blue()
        
        if self.mode == "GLOBAL":
            self._process_global(new_img, w, h, tr, tg, tb, threshold)
        else:
            self._process_flood(new_img, w, h, tr, tg, tb, threshold)
            
        self.finished.emit(new_img)

    def _process_global(self, img, w, h, tr, tg, tb, threshold):
        # Optimización: Acceso a memoria (simulado en Python)
        total = h
        for y in range(h):
            for x in range(w):
                c = img.pixelColor(x, y)
                dist = math.sqrt((c.red()-tr)**2 + (c.green()-tg)**2 + (c.blue()-tb)**2)
                if dist <= threshold:
                    img.setPixelColor(x, y, QColor(0,0,0,0))
            if y % 20 == 0: self.progress.emit(int((y/total)*100))

    def _process_flood(self, img, w, h, tr, tg, tb, threshold):
        sx, sy = self.seed
        if not (0 <= sx < w and 0 <= sy < h): return
        
        visited = set()
        queue = deque([(sx, sy)])
        visited.add((sx, sy))
        
        processed = 0
        while queue:
            cx, cy = queue.popleft()
            img.setPixelColor(cx, cy, QColor(0,0,0,0))
            processed += 1
            if processed % 5000 == 0: self.progress.emit((processed//100)%100)

            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h:
                    if (nx, ny) not in visited:
                        c = img.pixelColor(nx, ny)
                        dist = math.sqrt((c.red()-tr)**2 + (c.green()-tg)**2 + (c.blue()-tb)**2)
                        if dist <= threshold:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
        self.progress.emit(100)

# =================================================================================
#  CANVAS PROFESIONAL
# =================================================================================
class ProCanvas(QWidget):
    color_picked = pyqtSignal(QColor, QPoint)
    
    def __init__(self):
        super().__init__()
        self.img = None
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.mode = "SELECT" # SELECT, ERASE, PAN
        self.brush_size = 20
        self.last_mouse = QPoint()
        self.is_dragging = False
        self.setMouseTracking(True)
        self.bg_pattern = self._create_checker()

    def _create_checker(self):
        pix = QPixmap(32, 32)
        pix.fill(QColor(60, 60, 60))
        pt = QPainter(pix)
        pt.fillRect(0, 0, 16, 16, QColor(40, 40, 40))
        pt.fillRect(16, 16, 16, 16, QColor(40, 40, 40))
        pt.end()
        return pix

    def set_image(self, img):
        self.img = img
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawTiledPixmap(self.rect(), self.bg_pattern) # Fondo Pro
        
        if self.img:
            w, h = self.img.width() * self.scale, self.img.height() * self.scale
            cx = (self.width() - w) / 2 + self.offset.x()
            cy = (self.height() - h) / 2 + self.offset.y()
            dest_rect = QRect(int(cx), int(cy), int(w), int(h))
            
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawImage(dest_rect, self.img)
            
            # Dibujar borde de la imagen
            p.setPen(QPen(QColor(100, 100, 100), 1))
            p.drawRect(dest_rect)

            # Cursor del pincel
            if self.mode == "ERASE":
                # Dibujar círculo del cursor
                m_pos = self.mapFromGlobal(QCursor.pos())
                p.setPen(QPen(Qt.white, 1, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(m_pos, self.brush_size/2, self.brush_size/2)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.mode == "PAN":
                self.is_dragging = True
                self.last_mouse = e.pos()
                self.setCursor(Qt.ClosedHandCursor)
            elif self.mode == "SELECT":
                pos = self._get_img_coords(e.pos())
                if pos:
                    self.color_picked.emit(self.img.pixelColor(pos), pos)
            elif self.mode == "ERASE":
                self.is_dragging = True # Para borrar arrastrando
                self._apply_eraser(e.pos())
        elif e.button() == Qt.MiddleButton:
            self.is_dragging = True
            self.last_mouse = e.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self.is_dragging:
            if self.mode == "PAN" or (e.buttons() & Qt.MiddleButton):
                delta = e.pos() - self.last_mouse
                self.offset += delta
                self.last_mouse = e.pos()
                self.update()
            elif self.mode == "ERASE":
                self._apply_eraser(e.pos())
        
        if self.mode == "ERASE":
            self.update() # Para redibujar el cursor

    def mouseReleaseEvent(self, e):
        self.is_dragging = False
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, e):
        zoom_in = e.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9
        self.scale *= factor
        self.update()

    def _get_img_coords(self, widget_pos):
        if not self.img: return None
        w, h = self.img.width() * self.scale, self.img.height() * self.scale
        cx = (self.width() - w) / 2 + self.offset.x()
        cy = (self.height() - h) / 2 + self.offset.y()
        
        rx = int((widget_pos.x() - cx) / self.scale)
        ry = int((widget_pos.y() - cy) / self.scale)
        
        if 0 <= rx < self.img.width() and 0 <= ry < self.img.height():
            return QPoint(rx, ry)
        return None

    def _apply_eraser(self, widget_pos):
        pos = self._get_img_coords(widget_pos)
        if pos:
            # Dibujar transparencia en la imagen original
            p = QPainter(self.img)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setPen(Qt.NoPen)
            p.setBrush(Qt.black)
            p.drawEllipse(pos, self.brush_size/2, self.brush_size/2)
            p.end()
            self.update()

# =================================================================================
#  INTERFAZ PRINCIPAL
# =================================================================================
class ProRemoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProRemover Studio v1.0")
        self.resize(1280, 800)
        self.setWindowIcon(IconFactory.create_icon("wand", None))
        
        self.history = deque(maxlen=20) # Undo Stack
        self.current_img = None
        self.target_color = QColor(255, 255, 255)
        self.seed_point = QPoint(0,0)
        
        self._init_ui()
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ecf0f1; }
            QToolBar { background: #2c3e50; border-bottom: 2px solid #34495e; spacing: 10px; padding: 5px; }
            QToolButton { background: #34495e; color: white; border-radius: 4px; padding: 6px; }
            QToolButton:hover { background: #2980b9; }
            QToolButton:checked { background: #e67e22; border: 1px solid white; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; font-weight: bold; color: #bdc3c7; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: #bdc3c7; font-size: 12px; }
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:disabled { background-color: #7f8c8d; }
            QSlider::groove:horizontal { height: 6px; background: #2c3e50; border-radius: 3px; }
            QSlider::handle:horizontal { background: #e74c3c; width: 16px; margin: -5px 0; border-radius: 8px; }
            QProgressBar { text-align: center; border: 1px solid #555; border-radius: 4px; color: white; }
            QProgressBar::chunk { background-color: #3498db; }
        """)

    def _init_ui(self):
        # --- Toolbar Superior ---
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_load = QAction(IconFactory.create_icon("folder", None), "Abrir", self)
        act_load.triggered.connect(self.load_image)
        toolbar.addAction(act_load)

        act_save = QAction(IconFactory.create_icon("save", None), "Guardar", self)
        act_save.triggered.connect(self.save_image)
        toolbar.addAction(act_save)
        
        toolbar.addSeparator()

        self.act_select = QAction(IconFactory.create_icon("wand", None), "Seleccionar Color", self)
        self.act_select.setCheckable(True)
        self.act_select.setChecked(True)
        self.act_select.triggered.connect(lambda: self.set_mode("SELECT"))
        toolbar.addAction(self.act_select)

        self.act_erase = QAction(IconFactory.create_icon("eraser", None), "Borrador Manual", self)
        self.act_erase.setCheckable(True)
        self.act_erase.triggered.connect(lambda: self.set_mode("ERASE"))
        toolbar.addAction(self.act_erase)

        self.act_pan = QAction(IconFactory.create_icon("hand", None), "Mover/Zoom", self)
        self.act_pan.setCheckable(True)
        self.act_pan.triggered.connect(lambda: self.set_mode("PAN"))
        toolbar.addAction(self.act_pan)

        # --- Layout Principal ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0)

        # PANEL IZQUIERDO (Opciones)
        panel_opts = QFrame()
        panel_opts.setFixedWidth(280)
        panel_opts.setStyleSheet("background-color: #252525; border-right: 1px solid #444;")
        vbox = QVBoxLayout(panel_opts)

        # 1. Info Color
        gb_color = QGroupBox("Color Objetivo")
        v_col = QVBoxLayout()
        self.lbl_color_sample = QLabel()
        self.lbl_color_sample.setFixedHeight(40)
        self.lbl_color_sample.setStyleSheet("background-color: white; border: 2px solid #555; border-radius: 4px;")
        self.lbl_rgb = QLabel("RGB: ---")
        self.lbl_rgb.setAlignment(Qt.AlignCenter)
        v_col.addWidget(self.lbl_color_sample)
        v_col.addWidget(self.lbl_rgb)
        gb_color.setLayout(v_col)
        vbox.addWidget(gb_color)

        # 2. Config Algoritmo
        gb_algo = QGroupBox("Algoritmo IA (Lógica)")
        v_algo = QVBoxLayout()
        self.rb_global = QRadioButton("Global (Todo similar)")
        self.rb_flood = QRadioButton("Varita Mágica (Contiguo)")
        self.rb_flood.setChecked(True)
        v_algo.addWidget(self.rb_global)
        v_algo.addWidget(self.rb_flood)
        
        v_algo.addWidget(QLabel("Tolerancia / Fuerza:"))
        h_tol = QHBoxLayout()
        self.slider_tol = QSlider(Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(30)
        self.lbl_tol = QLabel("30%")
        self.slider_tol.valueChanged.connect(lambda v: self.lbl_tol.setText(f"{v}%"))
        h_tol.addWidget(self.slider_tol)
        h_tol.addWidget(self.lbl_tol)
        v_algo.addLayout(h_tol)
        
        self.btn_run = QPushButton("⚡ PROCESAR")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("background-color: #d35400; font-size: 14px;")
        self.btn_run.clicked.connect(self.run_process)
        v_algo.addWidget(self.btn_run)
        
        gb_algo.setLayout(v_algo)
        vbox.addWidget(gb_algo)

        # 3. Config Borrador
        gb_brush = QGroupBox("Ajustes Borrador")
        v_brush = QVBoxLayout()
        h_size = QHBoxLayout()
        h_size.addWidget(QLabel("Tamaño:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(5, 100)
        self.spin_size.setValue(20)
        self.spin_size.valueChanged.connect(self.update_brush_size)
        h_size.addWidget(self.spin_size)
        v_brush.addLayout(h_size)
        gb_brush.setLayout(v_brush)
        vbox.addWidget(gb_brush)

        # 4. Deshacer
        self.btn_undo = QPushButton("↩ DESHACER (Ctrl+Z)")
        self.btn_undo.setStyleSheet("background-color: #7f8c8d;")
        self.btn_undo.clicked.connect(self.undo)
        shortcut = QAction(self)
        shortcut.setShortcut(QKeySequence("Ctrl+Z"))
        shortcut.triggered.connect(self.undo)
        self.addAction(shortcut)
        vbox.addWidget(self.btn_undo)

        vbox.addStretch()
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        vbox.addWidget(self.pbar)

        # CANVAS DERECHO
        self.canvas = ProCanvas()
        self.canvas.color_picked.connect(self.update_color_info)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(panel_opts)
        splitter.addWidget(self.canvas)
        splitter.setSizes([280, 1000])
        
        main_layout.addWidget(splitter)

    # --- FUNCIONES LÓGICAS ---
    def set_mode(self, mode):
        self.canvas.mode = mode
        self.act_select.setChecked(mode == "SELECT")
        self.act_erase.setChecked(mode == "ERASE")
        self.act_pan.setChecked(mode == "PAN")

    def update_brush_size(self, val):
        self.canvas.brush_size = val

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir", "", "Imágenes (*.png *.jpg *.jpeg)")
        if path:
            self.current_img = QImage(path)
            self.current_img = self.current_img.convertToFormat(QImage.Format_ARGB32)
            self.canvas.set_image(self.current_img)
            self.history.clear()
            self.save_state()

    def save_image(self):
        if self.current_img:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar", "sin_fondo_pro.png", "PNG (*.png)")
            if path:
                self.current_img.save(path)

    def update_color_info(self, color, pos):
        self.target_color = color
        self.seed_point = pos
        self.lbl_color_sample.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #fff;")
        self.lbl_rgb.setText(f"RGB: {color.red()},{color.green()},{color.blue()}")

    def save_state(self):
        if self.current_img:
            self.history.append(self.current_img.copy())

    def undo(self):
        if len(self.history) > 1: # Mantener siempre el estado actual
            self.history.pop() # Sacar el actual
            prev = self.history[-1] # Ver el anterior
            self.current_img = prev.copy()
            self.canvas.set_image(self.current_img)
        elif len(self.history) == 1:
            QMessageBox.information(self, "Info", "Estado inicial alcanzado.")

    def run_process(self):
        if not self.current_img: return
        self.save_state()
        
        self.pbar.setVisible(True)
        self.pbar.setValue(0)
        self.setEnabled(False) # Bloquear UI
        
        mode = "GLOBAL" if self.rb_global.isChecked() else "FLOOD"
        
        self.worker = WorkerMagic(self.current_img, self.target_color, self.slider_tol.value(), mode, self.seed_point)
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(self.process_finished)
        self.worker.start()

    def process_finished(self, img):
        self.current_img = img
        self.canvas.set_image(self.current_img)
        self.pbar.setVisible(False)
        self.setEnabled(True)
        self.history.append(self.current_img.copy())

# =================================================================================
#  SPLASH SCREEN (PANTALLA DE CARGA)
# =================================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Estilo base profesional

    # Crear Splash Screen
    splash_pix = QPixmap(500, 300)
    splash_pix.fill(QColor(30, 30, 30))
    painter = QPainter(splash_pix)
    painter.setPen(QColor(230, 230, 230))
    painter.setFont(QFont("Arial", 24, QFont.Bold))
    painter.drawText(splash_pix.rect(), Qt.AlignCenter, "PRO REMOVER\nSTUDIO")
    painter.setFont(QFont("Arial", 10))
    painter.setPen(QColor(150, 150, 150))
    painter.drawText(20, 280, "Cargando módulos gráficos...")
    painter.end()

    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.show()
    
    # Simular carga (solo estético)
    import time
    time.sleep(1.5)
    
    window = ProRemoverApp()
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec_())