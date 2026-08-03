from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QRectF, QTimer, QPropertyAnimation, QSize
from PyQt5.QtGui import QPixmap, QColor, QPainter, QIcon
from PyQt5.QtSvg import QSvgRenderer
import pathlib


class ProductCard(QWidget):
    clicked = pyqtSignal(dict)
    item_added = pyqtSignal(dict)  # Emitir cuando se agrega al carrito

    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setCursor(Qt.PointingHandCursor)
        self.btn_add_cart = None
        self.loader_rotation = 0
        self.loader_timer = None
        self.stop_timer = None  # Timer para detener el loader
        self.restore_timer = None  # Timer para restaurar el icono
        self.setup_ui()

    def setup_ui(self):

        main = QVBoxLayout(self)
        main.setContentsMargins(4, 4, 4, 4)   # SUPER CORTO

        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setStyleSheet("""
            #card {
                background: #fff;
                border-radius: 10px;
                border: 1px solid #e4e4e4;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 22))
        self.card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ================= IMAGEN =====================
        img_box = QFrame()
        img_box.setFixedHeight(160)
        img_box.setStyleSheet("""
            QFrame {
                background: #f2f2f2;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        img_layout = QVBoxLayout(img_box)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setAlignment(Qt.AlignCenter)

        self.img = QLabel()
        self.img.setFixedSize(145, 145)
        self.img.setScaledContents(True)

        if img := self.product_data.get("image_path"):
            pix = QPixmap(img)
            if not pix.isNull():
                self.img.setPixmap(pix.scaled(145,145, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.img.setStyleSheet("background:#ddd; border-radius:6px;")
            self.img.setText("Sin imagen")
            self.img.setAlignment(Qt.AlignCenter)

        img_layout.addWidget(self.img)

        # ================ INFO COMPACTA ==================
        info = QFrame()
        info.setStyleSheet("padding: 6px;")
        info_layout = QVBoxLayout(info)
        info_layout.setSpacing(2)

        codigo = str(self.product_data.get("codigo", "") or "").strip()
        nombre = str(self.product_data.get("nombre", "Sin nombre") or "Sin nombre").strip()
        titulo = f"{codigo} - {nombre}" if codigo else nombre
        name = QLabel(titulo)
        name.setStyleSheet("font-size:13px; font-weight:600; color:#222;")
        name.setWordWrap(True)
        info_layout.addWidget(name)

        marca = QLabel(f"Marca: {self.product_data.get('marca','N/A')}")
        marca.setStyleSheet("font-size:11px; color:#777;")
        info_layout.addWidget(marca)

        precio_raw = self.product_data.get("venta") or self.product_data.get("precio") or 0
        try:
            precio_val = float(precio_raw)
        except (ValueError, TypeError):
            precio_val = 0.0
        precio = QLabel(f"S/ {precio_val:,.2f}")
        precio.setStyleSheet("font-size:15px; font-weight:700; color:#005eff;")
        info_layout.addWidget(precio)

        # ================ STOCK + BOTÓN ==================
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        stock = self.product_data.get("stock", 0)
        try:
            stock_val = int(float(stock or 0))
        except (ValueError, TypeError):
            stock_val = 0
        stock_lbl = QLabel(f"{stock_val} u.")
        stock_lbl.setStyleSheet("font-size:11px; color:#777;")

        # Indicador mini
        indicator = QLabel()
        indicator.setFixedSize(8, 8)

        if stock_val == 0: col = "#ff3b30"
        elif stock_val < 10: col = "#ffcc00"
        else: col = "#34c759"

        indicator.setStyleSheet(f"background:{col}; border-radius:4px;")

        stock_box = QHBoxLayout()
        stock_box.addWidget(stock_lbl)
        stock_box.addWidget(indicator)
        stock_box.setSpacing(3)

        bottom.addLayout(stock_box)
        bottom.addStretch()

        # ---------- BOTÓN REDONDO CON SVG ----------
        btn = QPushButton()
        btn.setFixedSize(48, 48)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                border-radius: 24px;
                background: transparent;
            }
        """)

        btn.setIcon(self.create_cart_icon())
        btn.setIconSize(QSize(48, 48))
        
        # Guardar referencia y conectar click
        self.btn_add_cart = btn
        self.btn_add_cart.clicked.connect(self.on_add_to_cart_clicked)

        bottom.addWidget(btn)

        info_layout.addLayout(bottom)

        # END
        layout.addWidget(img_box)
        layout.addWidget(info)
        main.addWidget(self.card)

    # =====================================================
    def create_cart_icon(self):
        """Icono negro con SVG blanco centrado"""
        try:
            svg_path = pathlib.Path(__file__).resolve().parent.parent / "icons" / "add_to_cart.svg"

            pix = QPixmap(48, 48)
            pix.fill(Qt.transparent)

            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)

            # Fondo circular
            painter.setBrush(QColor("#191919"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 48, 48)

            renderer = QSvgRenderer(str(svg_path))

            rect = QRectF(12, 12, 24, 24)  # SVG súper centrado
            renderer.render(painter, rect)

            painter.end()
            return QIcon(pix)

        except Exception as e:
            print("Error icono:", e)
            return QIcon()

    # CLICK CARD
    def mousePressEvent(self, e):
        # No interceptar clicks si es en el botón del carrito
        if self.btn_add_cart and self.btn_add_cart.geometry().contains(e.pos()):
            print("[DEBUG] Click interceptado en botón carrito, permitiendo que se propague")
            super().mousePressEvent(e)
            return
        
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.product_data)
        super().mousePressEvent(e)

    def on_add_to_cart_clicked(self):
        """Mostrar loader y luego check"""
        if not hasattr(self, 'btn_add_cart'):
            return
        
        self.show_loader_animation()
    
    def show_loader_animation(self):
        """Muestra el loader circular animado por 1 segundo"""
        if not hasattr(self, 'btn_add_cart'):
            return
        
        self.loader_rotation = 0
        
        # Timer para animar el loader
        self.loader_timer = QTimer()
        self.loader_timer.timeout.connect(self.animate_loader)
        self.loader_timer.start(20)  # Actualizar cada 20ms
        
        # Detener después de 1000ms (1 segundo)
        self.stop_timer = QTimer()
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self.show_check_icon)
        self.stop_timer.start(1000)
    
    def animate_loader(self):
        """Anima el loader rotando"""
        self.loader_rotation = (self.loader_rotation + 6) % 360
        loader_icon = self.create_loader_icon(self.loader_rotation)
        self.btn_add_cart.setIcon(loader_icon)
        self.btn_add_cart.setIconSize(QSize(48, 48))
    
    def create_loader_icon(self, rotation=0):
        """Crea un ícono de loader animado con puntos"""
        pix = QPixmap(48, 48)
        pix.fill(Qt.transparent)
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fondo circular negro
        painter.setBrush(QColor("#191919"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 48, 48)
        
        # Dibujar puntos animados alrededor del círculo
        center_x = 24
        center_y = 24
        radius = 16
        num_dots = 8
        
        for i in range(num_dots):
            angle = (i * 360 / num_dots + rotation) % 360
            angle_rad = angle * 3.14159 / 180
            
            # Posición del punto
            x = center_x + radius * __import__('math').cos(angle_rad)
            y = center_y + radius * __import__('math').sin(angle_rad)
            
            # Opacidad basada en la posición
            opacity = (i + (rotation / 45)) % 8
            opacity = 255 - int((opacity / 8) * 200)
            
            # Dibujar punto
            painter.setBrush(QColor(255, 255, 255, opacity))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x - 2), int(y - 2), 4, 4)
        
        painter.end()
        return QIcon(pix)
    
    def show_check_icon(self):
        """Muestra el ícono de check desde SVG"""
        if self.loader_timer:
            self.loader_timer.stop()
        
        try:
            svg_path = pathlib.Path(__file__).resolve().parent.parent / "icons" / "check.svg"
            
            check_pix = QPixmap(48, 48)
            check_pix.fill(Qt.transparent)
            
            painter = QPainter(check_pix)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Fondo circular negro
            painter.setBrush(QColor("#191919"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 48, 48)
            
            # Renderizar SVG del check
            renderer = QSvgRenderer(str(svg_path))
            rect = QRectF(12, 12, 24, 24)  # Centrado
            renderer.render(painter, rect)
            
            painter.end()
            check_icon = QIcon(check_pix)
            
        except Exception as e:
            print("Error al crear check icon:", e)
            # Fallback: dibujar check manualmente
            check_pix = QPixmap(48, 48)
            check_pix.fill(Qt.transparent)
            painter = QPainter(check_pix)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#191919"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 48, 48)
            pen = painter.pen()
            pen.setColor(QColor("#34c759"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(11, 24, 20, 33)
            painter.drawLine(20, 33, 37, 16)
            painter.end()
            check_icon = QIcon(check_pix)
        
        self.btn_add_cart.setIcon(check_icon)
        self.btn_add_cart.setIconSize(QSize(48, 48))
        
        # Emitir señal para agregar a tabla
        self.item_added.emit(self.product_data)
        
        # Restaurar icon original después de 1.5 segundos
        self.restore_timer = QTimer()
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self.restore_cart_icon)
        self.restore_timer.start(1500)
    
    def restore_cart_icon(self):
        """Restaura el ícono del carrito original"""
        icon = self.create_cart_icon()
        self.btn_add_cart.setIcon(icon)
        self.btn_add_cart.setIconSize(QSize(48, 48))
