from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QLineEdit, QPushButton, QFrame, QGroupBox,
    QFormLayout, QMessageBox, QFileDialog, QDialog, QGridLayout,
    QDialogButtonBox, QStackedWidget, QScrollArea, QListWidget,
    QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QColor, QPainterPath
import os
import json
import re
import datetime
import platform
import threading


class AnimatedLoader(QWidget):
    """Loader circular animado para carga de datos."""
    def __init__(self, parent=None, size=24):
        super().__init__(parent)
        self.size = size
        self.angle = 0
        self.setFixedSize(size, size)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(50)  # Actualizar cada 50ms
    
    def update_angle(self):
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dibujar círculo de progreso
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(25, 118, 210, 50))  # Azul claro
        painter.drawEllipse(0, 0, self.size, self.size)
        
        # Dibujar arco animado
        from PyQt5.QtGui import QPen
        painter.setPen(QPen(QColor(25, 118, 210), 2))
        painter.setBrush(Qt.NoBrush)
        
        # Dibujar arco de 90 grados
        painter.drawArc(2, 2, self.size - 4, self.size - 4, 
                       self.angle * 16, 90 * 16)
    
    def stop(self):
        """Detiene la animación."""
        self.timer.stop()


class LicenseLoaderThread(QThread):
    """Thread para cargar datos de licencia sin bloquear UI."""
    finished = pyqtSignal(dict)
    
    def __init__(self, username, user_id):
        super().__init__()
        self.username = username
        self.user_id = user_id
    
    def run(self):
        """Ejecuta la carga de datos en background."""
        try:
            from utils.api_handler import verificar_estado_licencia
            
            success, license_data = verificar_estado_licencia(
                username=self.username,
                id_usuario=self.user_id
            )
            
            self.finished.emit({
                'success': success,
                'data': license_data
            })
        except Exception as e:
            self.finished.emit({
                'success': False,
                'data': {'error': str(e)}
            })


class PasswordChangeDialog(QDialog):
    """Diálogo para cambiar la contraseña del usuario."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Cambiar Contraseña")
        self.setWidth(400)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.current_password = QLineEdit()
        self.current_password.setEchoMode(QLineEdit.Password)
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Contraseña Actual:", self.current_password)
        form_layout.addRow("Nueva Contraseña:", self.new_password)
        form_layout.addRow("Confirmar Contraseña:", self.confirm_password)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #FAFAFA;
            }
            QLineEdit:focus {
                background: white;
                border: 2px solid #1976D2;
                padding: 7px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton[text="OK"] {
                background-color: #1976D2;
                color: white;
            }
            QPushButton[text="Cancel"] {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                color: #424242;
            }
        """)

    def validate_and_accept(self):
        if not all([self.current_password.text(), self.new_password.text(), self.confirm_password.text()]):
            QMessageBox.warning(self, "Error", "Por favor complete todos los campos")
            return
        
        if self.new_password.text() != self.confirm_password.text():
            QMessageBox.warning(self, "Error", "Las contraseñas nuevas no coinciden")
            return

        if len(self.new_password.text()) < 8:
            QMessageBox.warning(self, "Error", "La contraseña debe tener al menos 8 caracteres")
            return

        self.accept()


class EditLicenseDatesDialog(QDialog):
    """Diálogo para editar las fechas de inicio y vencimiento de la licencia."""
    def __init__(self, parent=None, start_date="", end_date=""):
        super().__init__(parent)
        self.start_date_str = start_date
        self.end_date_str = end_date
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Editar Fechas de Licencia")
        self.setWidth(400)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        
        # Campo para fecha de inicio (formato: YYYY-MM-DD)
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("YYYY-MM-DD")
        self.start_date_input.setText(self.start_date_str if self.start_date_str != "Nunca" else "")
        
        # Campo para fecha de vencimiento (formato: YYYY-MM-DD)
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("YYYY-MM-DD")
        self.end_date_input.setText(self.end_date_str if self.end_date_str != "Nunca" else "")

        form_layout.addRow("Fecha de Inicio:", self.start_date_input)
        form_layout.addRow("Fecha de Vencimiento:", self.end_date_input)

        layout.addLayout(form_layout)

        # Información de ayuda
        info_label = QLabel("Formato: YYYY-MM-DD (ej: 2025-12-02)")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #FAFAFA;
            }
            QLineEdit:focus {
                background: white;
                border: 2px solid #1976D2;
                padding: 7px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton[text="OK"] {
                background-color: #1976D2;
                color: white;
            }
            QPushButton[text="Cancel"] {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                color: #424242;
            }
        """)

    def setWidth(self, width):
        self.setGeometry(0, 0, width, 300)

    def validate_and_accept(self):
        start_date = self.start_date_input.text().strip()
        end_date = self.end_date_input.text().strip()

        if not start_date or not end_date:
            QMessageBox.warning(self, "Error", "Por favor complete ambas fechas")
            return

        # Validar formato de fechas
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            
            if start >= end:
                QMessageBox.warning(self, "Error", "La fecha de inicio debe ser anterior a la fecha de vencimiento")
                return
        except ValueError:
            QMessageBox.warning(self, "Error", "Formato de fecha inválido. Use YYYY-MM-DD")
            return

        self.accept()


class ProfilePage(QWidget):
    """Página principal de perfil de usuario con datos reales."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.user_id = getattr(parent, 'user_id', None)
        self.username = getattr(parent, 'username', None)
        
        # Inicializar variables de datos
        self.active_sessions = []
        self.last_password_change = "Nunca"
        self.password_changes_count = 0
        self.license_type = "Plus"
        self.license_start = "Nunca"
        self.license_end = "Nunca"
        self.license_end_info = "Información no disponible"
        self.license_users = "1/1"
        self.license_status = "Activa"
        self.sidebar_buttons = []
        
        self.setup_ui()
        self.load_user_data()

    def setup_ui(self):
        """Configura la interfaz de usuario principal."""
        self.setObjectName("profileRoot")
        self.setStyleSheet("""
            QWidget#profileRoot {
                background-color: #F4F7FB;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Panel lateral
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Contenido principal
        self.stacked_widget = QStackedWidget()
        
        # Página 0: Mi Perfil
        profile_page = self._create_profile_page()
        self.stacked_widget.addWidget(profile_page)
        
        # Página 1: Seguridad
        security_page = self._create_security_page()
        self.stacked_widget.addWidget(security_page)
        
        # Página 2: Licencia
        license_page = self._create_license_page()
        self.stacked_widget.addWidget(license_page)
        
        main_layout.addWidget(self.stacked_widget, stretch=1)

    def _nav_button_style(self, active=False):
        if active:
            return """
                QPushButton {
                    background-color: #E9F2FF;
                    color: #1859B8;
                    border: 1px solid #CFE0F7;
                    border-radius: 16px;
                    padding: 14px 16px;
                    text-align: left;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E2EEFF;
                }
            """

        return """
            QPushButton {
                background-color: transparent;
                color: #425466;
                border: 1px solid transparent;
                border-radius: 16px;
                padding: 14px 16px;
                text-align: left;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F3F7FD;
                border-color: #E1E9F4;
                color: #1F2A37;
            }
        """

    def _action_button_style(self, variant="primary"):
        styles = {
            "primary": """
                QPushButton {
                    background-color: #2C7BE5;
                    color: white;
                    border: none;
                    border-radius: 14px;
                    padding: 12px 18px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1E68D2;
                }
            """,
            "secondary": """
                QPushButton {
                    background-color: #EEF4FF;
                    color: #2458A6;
                    border: 1px solid #D8E4F6;
                    border-radius: 14px;
                    padding: 12px 18px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E4EEFC;
                }
            """,
            "warning": """
                QPushButton {
                    background-color: #FFF5E8;
                    color: #B56100;
                    border: 1px solid #F2D5A8;
                    border-radius: 14px;
                    padding: 12px 18px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #FFEDD1;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #FFF1F1;
                    color: #C23D4B;
                    border: 1px solid #F3D3D8;
                    border-radius: 14px;
                    padding: 12px 18px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #FFE8EA;
                }
            """,
        }
        return styles.get(variant, styles["primary"])

    def _apply_line_edit_style(self, field, readonly=False, invalid=False):
        background = "#F1F5F9" if readonly else ("#FFF4F4" if invalid else "#FFFFFF")
        border = "#E39CA5" if invalid else "#D7E2EE"
        text_color = "#7A8797" if readonly else "#1F2937"
        focus_border = "#D85A68" if invalid else "#2C7BE5"
        field.setMinimumHeight(46)
        field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {background};
                color: {text_color};
                border: 1px solid {border};
                border-radius: 14px;
                padding: 0 14px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                background-color: #FFFFFF;
                border: 2px solid {focus_border};
                padding: 0 13px;
            }}
        """)

    def _create_avatar_pixmap(self, size=88, image_path=None):
        avatar = QPixmap(size, size)
        avatar.fill(Qt.transparent)

        painter = QPainter(avatar)
        painter.setRenderHint(QPainter.Antialiasing)

        clip_path = QPainterPath()
        clip_path.addEllipse(0, 0, size, size)
        painter.setClipPath(clip_path)

        if image_path and os.path.exists(image_path):
            source = QPixmap(image_path)
            if not source.isNull():
                scaled = source.scaled(
                    size, size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                x = (size - scaled.width()) // 2
                y = (size - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                return avatar

        painter.setClipping(False)
        painter.setBrush(QColor("#2C7BE5"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)

        initial = (self.username or "U").strip()[:1].upper() or "U"
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(18, size // 3))
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(avatar.rect(), Qt.AlignCenter, initial)
        painter.end()
        return avatar

    def _create_info_chip(self, title, value):
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background-color: #F7FAFE;
                border: 1px solid #E0EAF5;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(chip)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #728197; font-size: 10px; font-weight: 600;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("color: #132238; font-size: 13px; font-weight: 700;")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        return chip, value_label

    def _create_form_field(self, title, field, helper_text=""):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #344256; font-size: 11px; font-weight: 700;")
        layout.addWidget(title_label)
        layout.addWidget(field)

        if helper_text:
            helper_label = QLabel(helper_text)
            helper_label.setStyleSheet("color: #7A8797; font-size: 10px;")
            helper_label.setWordWrap(True)
            layout.addWidget(helper_label)

        return container

    def _filter_sidebar_sections(self, text):
        query = (text or "").strip().lower()
        visible_buttons = 0
        for btn in self.sidebar_buttons:
            label = (btn.property("section_name") or btn.text()).lower()
            is_visible = not query or query in label
            btn.setVisible(is_visible)
            if is_visible:
                visible_buttons += 1

        if hasattr(self, "sidebar_empty_label"):
            self.sidebar_empty_label.setVisible(bool(query) and visible_buttons == 0)

    def _handle_logout(self):
        response = QMessageBox.question(
            self,
            "Confirmar cierre de sesión",
            "¿Estás seguro de querer cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if response != QMessageBox.Yes:
            return

        try:
            import shutil
            from utils.file_handler import SESION_FILE, VISO_DATA_DIR

            if self.parent_app is not None:
                setattr(self.parent_app, "_explicit_logout", True)

            sesion_file_path = str(SESION_FILE)
            if os.path.exists(sesion_file_path):
                try:
                    os.remove(sesion_file_path)
                except Exception:
                    try:
                        shutil.rmtree(os.path.dirname(sesion_file_path))
                        os.makedirs(os.path.dirname(sesion_file_path), exist_ok=True)
                    except Exception:
                        pass

            username_file = os.path.join(VISO_DATA_DIR, '.last_username')
            if os.path.exists(username_file):
                os.remove(username_file)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cerrar sesión: {e}")
            return

        try:
            from utils.sync_manager import get_sync_manager
            get_sync_manager().stop_auto_sync()
        except Exception:
            pass

        try:
            from gui.login_window import LoginWindow
            login_window = LoginWindow()
            app = QApplication.instance()
            if app is not None:
                app._viso_login_window = login_window
            login_window.show()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir el inicio de sesión: {e}")
            return

        if self.parent_app is not None:
            self.parent_app.close()
        else:
            self.window().close()

    def _create_sidebar(self):
        """Crea el panel lateral con navegación."""
        sidebar = QFrame()
        sidebar.setObjectName("profileSidebar")
        sidebar.setStyleSheet("""
            QFrame#profileSidebar {
                background-color: #FBFCFE;
                border-right: 1px solid #E3EBF5;
            }
        """)
        sidebar.setMaximumWidth(260)
        sidebar.setMinimumWidth(240)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0E5CCB,
                    stop: 1 #2C7BE5
                );
                border-radius: 24px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 20, 18, 18)
        header_layout.setSpacing(8)
        
        self.profile_image_label = QLabel()
        self.profile_image_label.setFixedSize(88, 88)
        self.profile_image_label.setAlignment(Qt.AlignCenter)
        self.profile_image_label.setCursor(Qt.PointingHandCursor)
        self.profile_image_label.mousePressEvent = self.change_profile_image
        self.profile_image_label.setStyleSheet("QLabel { background: transparent; }")
        self.profile_image_label.setPixmap(self._create_avatar_pixmap(size=88))
        
        self.username_label = QLabel(self.username or "Usuario")
        self.username_label.setStyleSheet("""
            QLabel {
                font-weight: 700;
                color: white;
                font-size: 16px;
            }
        """)
        self.username_label.setAlignment(Qt.AlignCenter)

        role_label = QLabel("Cuenta principal")
        role_label.setAlignment(Qt.AlignCenter)
        role_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.86);
                font-size: 11px;
                font-weight: 500;
            }
        """)

        id_badge = QLabel(f"ID {self.user_id or '--'}")
        id_badge.setAlignment(Qt.AlignCenter)
        id_badge.setStyleSheet("""
            QLabel {
                color: #EAF2FF;
                background-color: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 12px;
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 700;
            }
        """)

        photo_hint = QLabel("Haz clic en la foto para cambiarla")
        photo_hint.setAlignment(Qt.AlignCenter)
        photo_hint.setWordWrap(True)
        photo_hint.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.78);
                font-size: 10px;
            }
        """)
        
        header_layout.addWidget(self.profile_image_label, alignment=Qt.AlignCenter)
        header_layout.addWidget(self.username_label)
        header_layout.addWidget(role_label)
        header_layout.addWidget(id_badge, alignment=Qt.AlignCenter)
        header_layout.addWidget(photo_hint)
        
        layout.addWidget(header)
        
        section_label = QLabel("Secciones")
        section_label.setStyleSheet("color: #6B7A90; font-size: 11px; font-weight: 700;")
        layout.addWidget(section_label)

        self.sidebar_search = QLineEdit()
        self.sidebar_search.setPlaceholderText("Buscar secciones")
        self.sidebar_search.textChanged.connect(self._filter_sidebar_sections)
        self.sidebar_search.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #DCE6F2;
                border-radius: 14px;
                padding: 0 14px;
                min-height: 42px;
                color: #1F2A37;
            }
            QLineEdit:focus {
                border: 2px solid #2C7BE5;
                padding: 0 13px;
            }
        """)
        layout.addWidget(self.sidebar_search)
        
        nav_container = QFrame()
        nav_container.setStyleSheet("QFrame { background: transparent; }")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 4, 0, 0)
        nav_layout.setSpacing(6)

        options = [
            ("Mi Perfil", 0),
            ("Seguridad", 1),
            ("Licencia", 2),
        ]
        
        for option_text, page_index in options:
            btn = QPushButton(option_text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("section_name", option_text.lower())
            btn.setMinimumHeight(46)
            btn.setStyleSheet(self._nav_button_style(active=False))
            btn.clicked.connect(lambda checked, idx=page_index, b=btn: self._switch_page(idx, b))
            self.sidebar_buttons.append(btn)
            nav_layout.addWidget(btn)

        self.sidebar_empty_label = QLabel("No hay coincidencias")
        self.sidebar_empty_label.setVisible(False)
        self.sidebar_empty_label.setAlignment(Qt.AlignCenter)
        self.sidebar_empty_label.setStyleSheet("color: #92A0B2; font-size: 11px; padding: 10px 0;")
        nav_layout.addWidget(self.sidebar_empty_label)

        layout.addWidget(nav_container)
        
        layout.addStretch()
        
        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(self._action_button_style("danger"))
        logout_btn.clicked.connect(self._handle_logout)
        layout.addWidget(logout_btn)

        if self.sidebar_buttons:
            self._update_sidebar_buttons(self.sidebar_buttons[0])
        
        return sidebar

    def _switch_page(self, index, button):
        """Cambia la página del widget apilado."""
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setCurrentIndex(index)
            self._update_sidebar_buttons(button)

    def _update_sidebar_buttons(self, selected_button):
        """Actualiza el estilo de los botones de navegación."""
        for btn in self.sidebar_buttons:
            btn.setStyleSheet(self._nav_button_style(active=btn == selected_button))

    def _create_profile_page(self):
        """Crea la página: Mi Perfil."""
        page = QWidget()
        page.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        
        hero = QFrame()
        hero.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E1EAF4;
                border-radius: 24px;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 24, 26, 24)
        hero_layout.setSpacing(20)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(6)

        eyebrow = QLabel("Centro de cuenta")
        eyebrow.setStyleSheet("color: #2C7BE5; font-size: 11px; font-weight: 700;")
        hero_left.addWidget(eyebrow)

        title = QLabel("Mi Perfil")
        title.setStyleSheet("QLabel { font-size: 28px; font-weight: 800; color: #132238; }")
        hero_left.addWidget(title)

        desc = QLabel("Administra tu información personal y de negocio desde una sola vista.")
        desc.setStyleSheet("color: #6F7E90; font-size: 12px;")
        desc.setWordWrap(True)
        hero_left.addWidget(desc)
        hero_left.addStretch()

        hero_layout.addLayout(hero_left, stretch=3)

        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(10)

        username_chip, self.hero_username_value = self._create_info_chip("Usuario", self.username or "No disponible")
        user_id_chip, self.hero_id_value = self._create_info_chip("ID", str(self.user_id) if self.user_id else "No disponible")
        business_chip, self.hero_business_value = self._create_info_chip("Óptica", "Sin configurar")

        chips_layout.addWidget(username_chip)
        chips_layout.addWidget(user_id_chip)
        chips_layout.addWidget(business_chip)
        hero_layout.addLayout(chips_layout, stretch=4)

        layout.addWidget(hero)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        basic_card = self._create_card("Datos de la cuenta", "Información principal de acceso y contacto.")
        basic_grid = QGridLayout()
        basic_grid.setHorizontalSpacing(16)
        basic_grid.setVerticalSpacing(16)
        
        self.nombre_input = QLineEdit()
        self.email_input = QLineEdit()
        self.id_input = QLineEdit()
        
        self.nombre_input.setReadOnly(True)
        self.nombre_input.setCursor(Qt.ForbiddenCursor)
        self.id_input.setReadOnly(True)
        self.id_input.setCursor(Qt.ForbiddenCursor)

        self._apply_line_edit_style(self.nombre_input, readonly=True)
        self._apply_line_edit_style(self.id_input, readonly=True)
        self._apply_line_edit_style(self.email_input)

        basic_grid.addWidget(
            self._create_form_field("ID de usuario", self.id_input, "Identificador interno protegido."),
            0, 0
        )
        basic_grid.addWidget(
            self._create_form_field("Nombre de usuario", self.nombre_input, "Este dato no se puede editar desde esta vista."),
            0, 1
        )
        basic_grid.addWidget(
            self._create_form_field("Correo electrónico", self.email_input, "Se usa para recordatorios y notificaciones."),
            1, 0, 1, 2
        )
        basic_card[1].addLayout(basic_grid)
        scroll_layout.addWidget(basic_card[0])
        
        business_card = self._create_card("Información del negocio", "Datos visibles para tu operación diaria.")
        business_grid = QGridLayout()
        business_grid.setHorizontalSpacing(16)
        business_grid.setVerticalSpacing(16)
        
        self.optica_input = QLineEdit()
        self.telefono_input = QLineEdit()
        self._apply_line_edit_style(self.optica_input)
        self._apply_line_edit_style(self.telefono_input)
        
        business_grid.addWidget(
            self._create_form_field("Nombre de óptica", self.optica_input, "Aparece en reportes y documentos del sistema."),
            0, 0
        )
        business_grid.addWidget(
            self._create_form_field("Teléfono", self.telefono_input, "Formato recomendado: solo números o prefijo internacional."),
            0, 1
        )
        business_card[1].addLayout(business_grid)
        scroll_layout.addWidget(business_card[0])
        
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E1EAF4;
                border-radius: 20px;
            }
        """)
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(22, 18, 22, 18)
        actions_layout.setSpacing(16)

        actions_info = QLabel("Guarda solo cuando termines de revisar tus datos de contacto y negocio.")
        actions_info.setWordWrap(True)
        actions_info.setStyleSheet("color: #6F7E90; font-size: 11px;")
        actions_layout.addWidget(actions_info, stretch=1)

        save_btn = QPushButton("Guardar cambios")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setMinimumWidth(220)
        save_btn.setStyleSheet(self._action_button_style("primary"))
        save_btn.clicked.connect(self.save_changes)
        actions_layout.addWidget(save_btn, alignment=Qt.AlignRight)
        scroll_layout.addWidget(actions_card)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return page

    def _create_security_page(self):
        """Crea la página: Seguridad."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("Seguridad")
        title.setStyleSheet("QLabel { font-size: 26px; font-weight: 800; color: #132238; }")
        layout.addWidget(title)
        
        desc = QLabel("Protege tu cuenta y gestiona tus sesiones activas")
        desc.setStyleSheet("color: #6F7E90; font-size: 12px;")
        layout.addWidget(desc)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # Tarjeta: Gestión de Contraseña
        pwd_card = self._create_card("Gestión de contraseña")
        pwd_layout = QVBoxLayout()
        
        pwd_info = QLabel(f"Última vez cambiada: {self.last_password_change}")
        pwd_info.setStyleSheet("color: #666; font-size: 11px;")
        if self.password_changes_count > 0:
            pwd_info.setText(f"Última vez cambiada: {self.last_password_change}\nTotal de cambios: {self.password_changes_count}")
        pwd_layout.addWidget(pwd_info)
        
        change_pwd_btn = QPushButton("Cambiar Contraseña")
        change_pwd_btn.setCursor(Qt.PointingHandCursor)
        change_pwd_btn.setStyleSheet(self._action_button_style("primary"))
        change_pwd_btn.clicked.connect(self.change_password)
        pwd_layout.addWidget(change_pwd_btn)
        
        pwd_card[1].addLayout(pwd_layout)
        scroll_layout.addWidget(pwd_card[0])
        
        # Tarjeta: Sesiones Activas (solo si hay sesiones)
        if self.active_sessions:
            sessions_card = self._create_card("Sesiones activas")
            sessions_layout = QVBoxLayout()
            
            for session in self.active_sessions:
                session_frame = QFrame()
                session_frame.setStyleSheet("""
                    QFrame {
                        background: #F7FAFE;
                        border: 1px solid #E4ECF5;
                        border-radius: 16px;
                        padding: 12px;
                    }
                """)
                session_layout = QVBoxLayout(session_frame)
                session_layout.setContentsMargins(0, 0, 0, 0)
                
                device_label = QLabel(session.get('device', 'Dispositivo'))
                device_label.setStyleSheet("font-weight: 600; color: #2C2C2C; font-size: 11px;")
                session_layout.addWidget(device_label)
                
                info_text = f"{session.get('location', 'Local')} | IP: {session.get('ip', '127.0.0.1')} | {session.get('last_active', 'Ahora')}"
                info_label = QLabel(info_text)
                info_label.setStyleSheet("color: #666; font-size: 10px;")
                session_layout.addWidget(info_label)
                
                sessions_layout.addWidget(session_frame)
            
            sessions_card[1].addLayout(sessions_layout)
            scroll_layout.addWidget(sessions_card[0])
        
        # Tarjeta: Autenticación de Dos Factores
        tfa_card = self._create_card("Autenticación de dos factores")
        tfa_layout = QHBoxLayout()
        
        tfa_label = QLabel("Estado:")
        tfa_label.setStyleSheet("font-weight: 600; color: #2C2C2C;")
        tfa_layout.addWidget(tfa_label)
        
        tfa_badge = QLabel("Activo")
        tfa_badge.setStyleSheet("""
            background-color: #E5F6EA;
            color: #257A45;
            border-radius: 10px;
            padding: 5px 10px;
            font-weight: 700;
            font-size: 11px;
        """)
        tfa_layout.addWidget(tfa_badge)
        tfa_layout.addStretch()
        
        tfa_card[1].addLayout(tfa_layout)
        scroll_layout.addWidget(tfa_card[0])
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return page

    def _create_license_page(self):
        """Crea la página: Licencia."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("Licencia")
        title.setStyleSheet("QLabel { font-size: 26px; font-weight: 800; color: #132238; }")
        layout.addWidget(title)
        
        desc = QLabel("Información sobre tu plan de licencia actual")
        desc.setStyleSheet("color: #6F7E90; font-size: 12px;")
        layout.addWidget(desc)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # Tarjeta: Estado Actual
        status_card = self._create_card("Estado Actual")
        status_layout = QHBoxLayout()
        
        self.license_status_label = QLabel("Licencia activa")
        self.license_status_label.setStyleSheet("""
            color: #257A45;
            background-color: #E5F6EA;
            border-radius: 11px;
            padding: 6px 10px;
            font-weight: 700;
            font-size: 11px;
        """)
        status_layout.addWidget(self.license_status_label)
        status_layout.addStretch()
        
        status_card[1].addLayout(status_layout)
        scroll_layout.addWidget(status_card[0])
        
        # Tarjeta: Detalles del Plan
        details_card = self._create_card("Detalles del Plan")
        form = QFormLayout()
        form.setSpacing(12)
        
        # Crear labels que se actualizarán dinámicamente
        self.type_label = QLabel(self.license_type)
        self.start_label = QLabel(self.license_start)
        self.end_label = QLabel(self.license_end)
        users_label = QLabel(self.license_users)
        
        form.addRow("Tipo de Plan:", self.type_label)
        form.addRow("Fecha de Inicio:", self.start_label)
        form.addRow("Fecha de Vencimiento:", self.end_label)
        form.addRow("Usuarios:", users_label)
        
        # Fila con loader y información de vencimiento
        expiration_container = QWidget()
        expiration_layout = QHBoxLayout(expiration_container)
        expiration_layout.setContentsMargins(0, 0, 0, 0)
        
        self.expiration_info_label = QLabel(self.license_end_info)
        self.expiration_info_label.setStyleSheet("font-weight: 600; color: #D32F2F; font-size: 11px;")
        self.expiration_info_label.setWordWrap(True)
        
        # Crear y guardar referencia al loader
        self.license_loader = AnimatedLoader(expiration_container, size=20)
        self.license_loader.hide()  # Ocultado por defecto
        
        expiration_layout.addWidget(self.expiration_info_label)
        expiration_layout.addWidget(self.license_loader)
        expiration_layout.addStretch()
        
        form.addRow("", expiration_container)
        
        details_card[1].addLayout(form)
        scroll_layout.addWidget(details_card[0])
        
        # Tarjeta: Acciones
        actions_card = self._create_card("Acciones")
        actions_layout = QVBoxLayout()
        
        renew_btn = QPushButton("Renovar licencia")
        renew_btn.setCursor(Qt.PointingHandCursor)
        renew_btn.setStyleSheet(self._action_button_style("primary"))
        actions_layout.addWidget(renew_btn)
        
        update_dates_btn = QPushButton("Actualizar fechas")
        update_dates_btn.setCursor(Qt.PointingHandCursor)
        update_dates_btn.setStyleSheet(self._action_button_style("secondary"))
        update_dates_btn.clicked.connect(self.on_update_dates_clicked)
        actions_layout.addWidget(update_dates_btn)
        
        cert_btn = QPushButton("Descargar certificado")
        cert_btn.setCursor(Qt.PointingHandCursor)
        cert_btn.setStyleSheet(self._action_button_style("warning"))
        cert_btn.clicked.connect(self.download_certificate)
        actions_layout.addWidget(cert_btn)
        
        actions_card[1].addLayout(actions_layout)
        scroll_layout.addWidget(actions_card[0])
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return page

    def _create_card(self, title="", subtitle=""):
        """Factory para crear tarjetas con título."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E1EAF4;
                border-radius: 22px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        
        if title or subtitle:
            header_layout = QVBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(4)

            title_label = QLabel(title)
            title_label.setStyleSheet("QLabel { font-weight: 700; color: #132238; font-size: 14px; }")
            header_layout.addWidget(title_label)

            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setWordWrap(True)
                subtitle_label.setStyleSheet("QLabel { color: #7A8797; font-size: 11px; }")
                header_layout.addWidget(subtitle_label)

            layout.addLayout(header_layout)
        
        return (card, layout)

    def load_user_data(self):
        """Carga todos los datos reales del usuario."""
        self.load_profile_image()
        self.load_license_data()
        self.load_sessions()
        self.load_password_info()
        
        # Cargar datos del usuario desde JSON
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            usuarios_path = os.path.join(base_dir, "VISO", ".usuarios.json")
            
            if os.path.exists(usuarios_path):
                with open(usuarios_path, 'r', encoding='utf-8') as f:
                    usuarios = json.load(f)
                    if self.user_id in usuarios:
                        user_data = usuarios[self.user_id]
                        self.username = user_data.get('username', self.username)
                        self.id_input.setText(str(self.user_id))
                        self.nombre_input.setText(user_data.get('username', ''))
                        self.email_input.setText(user_data.get('email', ''))
                        self.optica_input.setText(user_data.get('optica', ''))
                        self.telefono_input.setText(user_data.get('telefono', ''))
                        if hasattr(self, 'username_label'):
                            self.username_label.setText(user_data.get('username', self.username or 'Usuario'))
                        if hasattr(self, 'hero_username_value'):
                            self.hero_username_value.setText(user_data.get('username', self.username or 'No disponible'))
                        if hasattr(self, 'hero_id_value'):
                            self.hero_id_value.setText(str(self.user_id))
                        if hasattr(self, 'hero_business_value'):
                            self.hero_business_value.setText(user_data.get('optica', '') or "Sin configurar")
                        self.load_profile_image()
        except Exception as e:
            print(f"Error cargando datos de usuario: {e}")
        
        self.setup_validation()

    def load_profile_image(self):
        """Carga la imagen de perfil del usuario."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            image_path = os.path.join(base_dir, "VISO", "profile_images", f"{self.user_id}.png")
            self.profile_image_label.setPixmap(self._create_avatar_pixmap(size=88, image_path=image_path))
        except Exception as e:
            print(f"Error cargando imagen de perfil: {e}")

    def change_profile_image(self, event):
        """Permite cambiar la imagen de perfil al hacer clic."""
        try:
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar imagen de perfil",
                "",
                "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*)"
            )
            
            if not filepath:
                return
            
            # Copiar la imagen a la carpeta de perfiles
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            profile_dir = os.path.join(base_dir, "VISO", "profile_images")
            
            # Crear directorio si no existe
            os.makedirs(profile_dir, exist_ok=True)
            
            # Guardar imagen con el nombre del usuario
            dest_path = os.path.join(profile_dir, f"{self.user_id}.png")
            
            # Cargar la imagen seleccionada
            original_pixmap = QPixmap(filepath)
            if original_pixmap.isNull():
                QMessageBox.warning(self, "Error", "No se pudo cargar la imagen")
                return
            
            # Guardar como PNG
            original_pixmap.save(dest_path, "PNG")
            
            # Recargar la imagen en el label
            self.load_profile_image()
            
            QMessageBox.information(self, "Éxito", "Imagen de perfil actualizada correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cambiar imagen: {e}")

    def load_license_data(self):
        """Carga información de licencia desde servidor remoto en un thread separado."""
        try:
            # Mostrar loader si existe
            if hasattr(self, 'license_loader'):
                self.license_loader.show()
            
            # Crear y ejecutar thread de carga
            self.license_thread = LicenseLoaderThread(
                username=self.username,
                user_id=self.user_id
            )
            self.license_thread.finished.connect(self._on_license_data_loaded)
            self.license_thread.start()
            
        except Exception as e:
            print(f"Error iniciando carga de licencia: {e}")
            self.license_start = "Error"
            self.license_end = "Error"

    def _on_license_data_loaded(self, result):
        """Callback cuando los datos de licencia se han cargado."""
        try:
            # Ocultar loader
            if hasattr(self, 'license_loader'):
                self.license_loader.stop()
                self.license_loader.hide()
            
            success = result.get('success', False)
            license_data = result.get('data', {})
            
            if success and license_data:
                if not license_data.get('licencia_vigente', False):
                    # Licencia expirada - pero dejar que el mainwindow.mostrar_frame lo maneje
                    print(f"[PERFIL] Detectada licencia expirada")
                    self.license_status = "Expirada"
                    self.license_start = license_data.get('fecha_inicio', 'Desconocida')
                    self.license_end = license_data.get('fecha_vencimiento', 'Desconocida')
                    dias_restantes = license_data.get('dias_restantes', 0)
                    self.license_type = license_data.get('plan_type', 'Desconocido')
                    # No mostrar diálogo aquí - el mainwindow ya lo mostró
                    # Solo actualizar la UI para que se vea que está expirada
                    self._calculate_expiration_info(self.license_end, dias_restantes)
                    
                elif not license_data.get('tiene_licencia', False):
                    # Sin licencia
                    print(f"[PERFIL] Detectado: Sin licencia")
                    self.license_status = "Sin Licencia"
                    self.license_type = "Ninguno"
                    # No mostrar diálogo aquí - el mainwindow ya lo mostró
                else:
                    # Licencia válida y vigente
                    self.license_status = "Activa"
                    self.license_start = license_data.get('fecha_inicio', 'Desconocida')
                    self.license_end = license_data.get('fecha_vencimiento', 'Desconocida')
                    dias_restantes = license_data.get('dias_restantes', 0)
                    self.license_type = license_data.get('plan_type', 'Plus')
                    
                    # Calcular información de vencimiento
                    self._calculate_expiration_info(self.license_end, dias_restantes)
            else:
                # Error al conectar - usar valores por defecto
                self.license_status = "Desconocido"
                self.license_start = "Desconocida"
                self.license_end = "Desconocida"
            
            # Refrescar los labels en la UI
            self._refresh_license_labels()
                
        except Exception as e:
            print(f"Error procesando datos de licencia: {e}")
            # Ocultar loader en caso de error
            if hasattr(self, 'license_loader'):
                self.license_loader.stop()
                self.license_loader.hide()
            # Valores por defecto si hay error
            self.license_start = "No disponible"
            self.license_end = "No disponible"
            # Actualizar labels incluso si hay error
            self._refresh_license_labels()

    def _calculate_expiration_info(self, fecha_vencimiento: str, dias_restantes: int):
        """Calcula el día de la semana y la información de vencimiento."""
        try:
            from datetime import datetime, timedelta
            
            # Validar que la fecha no sea "Nunca", "Desconocida" o vacía
            if not fecha_vencimiento or fecha_vencimiento in ["Nunca", "No asignada", "Desconocida"]:
                self.license_end_info = "Información no disponible"
                return
            
            # Parsear la fecha - intentar con diferentes formatos
            fecha = None
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    fecha = datetime.strptime(fecha_vencimiento, fmt)
                    break
                except ValueError:
                    continue
            
            if fecha is None:
                self.license_end_info = "Información no disponible"
                return
            
            # Diccionarios para traducción
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            
            # Obtener día de la semana
            dia_semana = dias_semana[fecha.weekday()]
            
            # Calcular si vence esta semana
            hoy = datetime.now().date()
            fin_semana = hoy + timedelta(days=(6 - hoy.weekday()))  # Próximo domingo
            fecha_obj = fecha.date()
            
            if dias_restantes <= 0:
                self.license_end_info = f"Licencia vencida ({fecha_vencimiento})"
            elif fecha_obj <= fin_semana and fecha_obj >= hoy:
                self.license_end_info = f"Se vence {dia_semana} ({fecha_vencimiento}) en {dias_restantes} días"
            else:
                self.license_end_info = f"Se vence {dia_semana} ({fecha_vencimiento}) y quedan {dias_restantes} días"
                
        except Exception as e:
            print(f"Error calculando info de vencimiento: {e}")
            self.license_end_info = f"Vencimiento: {fecha_vencimiento}"

    def _refresh_license_labels(self):
        """Actualiza los labels de licencia con los nuevos datos después de cargar desde API."""
        try:
            # Actualizar los labels si existen (fueron creados en _create_license_page)
            if hasattr(self, 'type_label'):
                self.type_label.setText(self.license_type)
            if hasattr(self, 'start_label'):
                self.start_label.setText(self.license_start)
            if hasattr(self, 'end_label'):
                self.end_label.setText(self.license_end)
            if hasattr(self, 'expiration_info_label'):
                self.expiration_info_label.setText(self.license_end_info)
            if hasattr(self, 'license_status_label'):
                status_text = (self.license_status or "Desconocido").strip()
                palette = {
                    "Activa": ("#257A45", "#E5F6EA"),
                    "Expirada": ("#B5474F", "#FFF1F1"),
                    "Sin Licencia": ("#A66A00", "#FFF5E8"),
                }
                text_color, background = palette.get(status_text, ("#5C6B7A", "#F2F5F8"))
                self.license_status_label.setText(status_text)
                self.license_status_label.setStyleSheet(f"""
                    color: {text_color};
                    background-color: {background};
                    border-radius: 11px;
                    padding: 6px 10px;
                    font-weight: 700;
                    font-size: 11px;
                """)
        except Exception as e:
            print(f"Error actualizando labels de licencia: {e}")

    def load_sessions(self):
        """Carga sesiones activas desde archivo."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            sesion_path = os.path.join(base_dir, "VISO", "sesion.txt")
            
            if os.path.exists(sesion_path):
                with open(sesion_path, 'r', encoding='utf-8') as f:
                    current_user = f.read().strip()
                    if current_user == str(self.user_id):
                        system = platform.system()
                        if system == "Windows":
                            device_name = "Windows"
                        elif system == "Darwin":
                            device_name = "Mac"
                        elif system == "Linux":
                            device_name = "Linux"
                        else:
                            device_name = "Dispositivo"
                        
                        self.active_sessions.append({
                            'device': f"Este Dispositivo - {device_name}",
                            'location': 'Local',
                            'ip': '127.0.0.1',
                            'last_active': 'Ahora mismo'
                        })
                        return
            
            # Si no hay sesión activa, solo dejar lista vacía (sin sesión por defecto)
        except Exception as e:
            print(f"Error cargando sesiones: {e}")

    def load_password_info(self):
        """Carga información de cambios de contraseña."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_dir = os.path.join(base_dir, "VISO", "temp", "password_logs")
            log_file = os.path.join(log_dir, f"{self.user_id}_password.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        self.password_changes_count = len(lines)
                        self.last_password_change = lines[-1].strip()
        except Exception as e:
            print(f"Error cargando información de contraseña: {e}")

    def setup_validation(self):
        """Configura validación en tiempo real."""
        self.email_input.textChanged.connect(self._validate_email)
        self.telefono_input.textChanged.connect(self._validate_phone)

    def _validate_email(self):
        """Valida el formato de correo electrónico."""
        email = self.email_input.text()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if email and not re.match(pattern, email):
            self._apply_line_edit_style(self.email_input, invalid=True)
        else:
            self._apply_line_edit_style(self.email_input)

    def _validate_phone(self):
        """Valida el formato de teléfono."""
        phone = self.telefono_input.text()
        pattern = r'^\+?[0-9]{8,15}$'
        
        if phone and not re.match(pattern, phone):
            self._apply_line_edit_style(self.telefono_input, invalid=True)
        else:
            self._apply_line_edit_style(self.telefono_input)

    def save_changes(self):
        """Guarda cambios de perfil en JSON."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            usuarios_path = os.path.join(base_dir, "VISO", ".usuarios.json")
            
            if os.path.exists(usuarios_path):
                with open(usuarios_path, 'r', encoding='utf-8') as f:
                    usuarios = json.load(f)
                
                if self.user_id in usuarios:
                    usuarios[self.user_id]['username'] = self.nombre_input.text()
                    usuarios[self.user_id]['email'] = self.email_input.text()
                    usuarios[self.user_id]['optica'] = self.optica_input.text()
                    usuarios[self.user_id]['telefono'] = self.telefono_input.text()
                
                with open(usuarios_path, 'w', encoding='utf-8') as f:
                    json.dump(usuarios, f, indent=2, ensure_ascii=False)

                if hasattr(self, 'hero_business_value'):
                    self.hero_business_value.setText(self.optica_input.text().strip() or "Sin configurar")
                
                QMessageBox.information(self, "Éxito", "Los cambios se han guardado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar cambios: {e}")

    def change_password(self):
        """Abre diálogo para cambiar contraseña."""
        dialog = PasswordChangeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                usuarios_path = os.path.join(base_dir, "VISO", ".usuarios.json")
                
                if os.path.exists(usuarios_path):
                    with open(usuarios_path, 'r', encoding='utf-8') as f:
                        usuarios = json.load(f)
                    
                    if self.user_id in usuarios:
                        stored_pwd = usuarios[self.user_id].get('password', '')
                        if dialog.current_password.text() == stored_pwd:
                            usuarios[self.user_id]['password'] = dialog.new_password.text()
                            
                            with open(usuarios_path, 'w', encoding='utf-8') as f:
                                json.dump(usuarios, f, indent=2, ensure_ascii=False)
                            
                            self._save_password_change_log()
                            self.load_password_info()
                            
                            QMessageBox.information(self, "Éxito", "Contraseña cambiad correctamente.")
                        else:
                            QMessageBox.warning(self, "Error", "Contraseña actual incorrecta.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cambiar contraseña: {e}")

    def _save_password_change_log(self):
        """Registra el cambio de contraseña en log."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_dir = os.path.join(base_dir, "VISO", "temp", "password_logs")
            
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{self.user_id}_password.log")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Cambio realizado el: {timestamp}\n")
        except Exception as e:
            print(f"Error guardando log de contraseña: {e}")

    def on_update_dates_clicked(self):
        """Recarga los datos de licencia desde la base de datos."""
        try:
            from PyQt5.QtWidgets import QMessageBox
            
            # Mostrar mensaje de carga
            QMessageBox.information(self, "Actualizando", "Recargando datos de licencia desde el servidor...")
            
            # Recargar datos desde la BD
            self.load_license_data()
            
            # Mensaje de éxito
            QMessageBox.information(
                self, 
                "Actualizado", 
                f"Datos actualizados correctamente\n\nDías restantes: {self._get_dias_restantes()}"
            )
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error al actualizar datos: {str(e)}")
    
    def _get_dias_restantes(self):
        """Calcula días restantes de la licencia."""
        try:
            from datetime import datetime
            fecha_fin = datetime.strptime(self.license_end, '%Y-%m-%d')
            hoy = datetime.now()
            dias = (fecha_fin - hoy).days
            return max(0, dias)
        except:
            return 0


    def download_certificate(self):
        """Descarga el certificado de licencia en PDF."""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Diálogo para seleccionar ubicación de descarga
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Descargar Certificado de Licencia",
                f"Certificado_VISO_{self.user_id}.pdf",
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Generar certificado PDF
            self._generate_certificate_pdf(file_path)
            
            QMessageBox.information(self, "Éxito", f"Certificado descargado exitosamente en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al descargar certificado: {e}")

    def _generate_certificate_pdf(self, file_path):
        """Genera un PDF con el certificado de licencia."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from datetime import datetime
            
            # Crear documento PDF
            doc = SimpleDocTemplate(file_path, pagesize=letter,
                                   rightMargin=0.75*inch, leftMargin=0.75*inch,
                                   topMargin=0.75*inch, bottomMargin=0.75*inch)
            
            # Container para los elementos
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1565C0'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#2C2C2C'),
                spaceAfter=12,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#424242'),
                spaceAfter=6
            )
            
            # Encabezado
            title = Paragraph("CERTIFICADO DE LICENCIA", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.2*inch))
            
            # Subtítulo
            subtitle = Paragraph("VISO - Sistema de Gestión Óptica", ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#1565C0'),
                alignment=TA_CENTER,
                spaceAfter=12
            ))
            elements.append(subtitle)
            elements.append(Spacer(1, 0.3*inch))
            
            # Información de la licencia
            elements.append(Paragraph("INFORMACIÓN DEL CERTIFICADO", heading_style))
            
            # Tabla con datos
            data = [
                ['Campo', 'Valor'],
                ['ID de Usuario', str(self.user_id)],
                ['Nombre de Usuario', self.nombre_input.text() or 'N/A'],
                ['Correo Electrónico', self.email_input.text() or 'N/A'],
                ['Óptica', self.optica_input.text() or 'N/A'],
                ['Tipo de Plan', self.license_type],
                ['Fecha de Inicio', self.license_start],
                ['Fecha de Vencimiento', self.license_end],
                ['Usuarios Autorizados', self.license_users],
                ['Estado de Licencia', self.license_status],
                ['Fecha de Emisión', datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
            ]
            
            table = Table(data, colWidths=[2.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565C0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Términos y condiciones
            elements.append(Paragraph("TÉRMINOS Y VALIDEZ", heading_style))
            terms_text = """
            Este certificado acredita que la licencia de VISO indicada arriba es válida y activa. 
            El usuario autorizado tiene derecho a utilizar el software VISO de acuerdo con los términos 
            y condiciones especificados en el acuerdo de licencia. Este certificado es válido únicamente 
            durante el período especificado en la sección de fechas. Cualquier modificación o falsificación 
            de este documento anula su validez.
            """
            elements.append(Paragraph(terms_text, normal_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Pie de página
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#999999'),
                alignment=TA_CENTER,
                spaceAfter=0
            )
            elements.append(Spacer(1, 0.3*inch))
            footer_text = f"Certificado generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}<br/>VISO v4.2.0 - Sistema de Gestión Óptica"
            elements.append(Paragraph(footer_text, footer_style))
            
            # Construir PDF
            doc.build(elements)
            
        except ImportError:
            # Si reportlab no está instalado, crear un PDF simple con PyPDF2 o generar un documento de texto
            self._generate_certificate_txt(file_path)
        except Exception as e:
            print(f"Error generando PDF: {e}")
            raise

    def _generate_certificate_txt(self, file_path):
        """Genera un certificado en formato texto si reportlab no está disponible."""
        try:
            # Cambiar extensión a .txt si es necesario
            if file_path.endswith('.pdf'):
                file_path = file_path.replace('.pdf', '.txt')
            
            from datetime import datetime
            
            content = f"""
╔════════════════════════════════════════════════════════════════════╗
║           CERTIFICADO DE LICENCIA - VISO v4.2.0                   ║
║              Sistema de Gestión Óptica                            ║
╚════════════════════════════════════════════════════════════════════╝

INFORMACIÓN DEL CERTIFICADO:
────────────────────────────────────────────────────────────────────
ID de Usuario:                 {self.user_id}
Nombre de Usuario:             {self.nombre_input.text() or 'N/A'}
Correo Electrónico:            {self.email_input.text() or 'N/A'}
Óptica:                        {self.optica_input.text() or 'N/A'}
────────────────────────────────────────────────────────────────────

DETALLES DE LA LICENCIA:
────────────────────────────────────────────────────────────────────
Tipo de Plan:                  {self.license_type}
Fecha de Inicio:               {self.license_start}
Fecha de Vencimiento:          {self.license_end}
Usuarios Autorizados:          {self.license_users}
Estado de la Licencia:         {self.license_status}
────────────────────────────────────────────────────────────────────

TÉRMINOS Y VALIDEZ:
────────────────────────────────────────────────────────────────────
Este certificado acredita que la licencia de VISO indicada arriba es 
válida y activa. El usuario autorizado tiene derecho a utilizar el 
software VISO de acuerdo con los términos y condiciones especificados 
en el acuerdo de licencia. Este certificado es válido únicamente 
durante el período especificado en la sección de fechas.

────────────────────────────────────────────────────────────────────
Fecha de Emisión:              {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Certificado Generado:          {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}
VISO v4.2.0
════════════════════════════════════════════════════════════════════
"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"Error generando certificado de texto: {e}")
            raise

    def closeEvent(self, event):
        try:
            if hasattr(self, 'license_loader') and self.license_loader is not None:
                try:
                    self.license_loader.stop()
                except Exception:
                    pass
            if hasattr(self, 'license_thread') and self.license_thread is not None:
                try:
                    if self.license_thread.isRunning():
                        self.license_thread.quit()
                        self.license_thread.wait(800)
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)
