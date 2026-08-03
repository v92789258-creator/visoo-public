import sys
import os
import datetime
import json
import threading
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout, QLineEdit,
    QDateEdit, QPushButton, QTableWidget, QHeaderView, QMessageBox,
    QAbstractItemView, QComboBox, QTableWidgetItem, QDialog,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDate, QTimer, QThread, pyqtSignal, QVariantAnimation
from PyQt5.QtGui import QMouseEvent, QPainter, QColor, QPen, QPainterPath, QIcon, QPixmap
from utils.file_handler import (
    cargar_clientes, cargar_clientes_dashboard, cargar_clientes_editable, guardar_clientes, buscar_dni_api, 
    cargar_pacientes, guardar_pacientes, crear_directorios_usuario,
    cargar_etiquetas_clientes, guardar_etiquetas_clientes
)
from gui.draggable_title_bar import DraggableTitleBar


class CustomersPageSkeleton(QWidget):
    """Skeleton del layout principal de clientes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._pulse = 0.0
        self._build_ui()
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(950)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._on_anim)
        self._apply_style()
        self.anim.start()

    def _block(self, width=None, height=16, radius=8):
        item = QWidget()
        item.setProperty("skeleton_radius", int(radius))
        item.setFixedHeight(int(height))
        if width:
            item.setFixedWidth(int(width))
        self._blocks.append(item)
        return item

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(20, 20, 20, 0)
        top_layout.setSpacing(20)

        header = QHBoxLayout()
        header.addWidget(self._block(260, 28, 8), 0, Qt.AlignLeft)
        header.addStretch()
        header.addWidget(self._block(220, 42, 10))
        header.addWidget(self._block(96, 42, 10))
        top_layout.addLayout(header)

        search_row = QHBoxLayout()
        search_row.setSpacing(16)
        search_row.addWidget(self._block(0, 42, 10), 1)
        top_layout.addLayout(search_row)

        stats_card = QWidget()
        stats_card.setObjectName("stats_card")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(18, 12, 18, 12)
        stats_layout.setSpacing(0)
        for idx in range(4):
            stat = QWidget()
            stat_layout = QVBoxLayout(stat)
            stat_layout.setContentsMargins(12, 4, 12, 4)
            stat_layout.setSpacing(10)
            stat_layout.addWidget(self._block(110, 14, 6))
            stat_layout.addWidget(self._block(42, 24, 6))
            stats_layout.addWidget(stat, 1)
            if idx < 3:
                divider = QWidget()
                divider.setObjectName("divider")
                divider.setFixedWidth(1)
                stats_layout.addWidget(divider)
                self._blocks.append(divider)
        self._blocks.append(stats_card)
        top_layout.addWidget(stats_card)
        layout.addWidget(top)

        table_card = QWidget()
        table_card.setObjectName("table_card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 20, 20, 20)
        table_layout.setSpacing(0)

        header_row = QWidget()
        header_row.setObjectName("table_header")
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(12, 14, 12, 14)
        header_layout.setSpacing(18)
        for width in (90, 320, 70, 150, 120, 110):
            header_layout.addWidget(self._block(width, 15, 6))
        header_layout.addStretch()
        table_layout.addWidget(header_row)

        for _ in range(7):
            row = QWidget()
            row.setObjectName("table_row")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 16, 12, 16)
            row_layout.setSpacing(18)
            row_layout.addWidget(self._block(86, 14, 6))
            row_layout.addWidget(self._block(360, 14, 6))
            row_layout.addWidget(self._block(56, 14, 6))
            row_layout.addWidget(self._block(140, 14, 6))
            row_layout.addWidget(self._block(110, 14, 6))
            row_layout.addWidget(self._block(120, 32, 8))
            row_layout.addStretch()
            table_layout.addWidget(row)
        self._blocks.append(table_card)
        layout.addWidget(table_card, 1)

    def set_loading_text(self, subtitle="", status=""):
        return

    def _on_anim(self, value):
        try:
            self._pulse = float(value or 0.0)
        except Exception:
            self._pulse = 0.0
        self._apply_style()

    def _apply_style(self):
        base = 228 + int(10 * self._pulse)
        soft = 244 + int(6 * self._pulse)
        self.setStyleSheet(
            f"""
            QWidget#stats_card, QWidget#table_card {{
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 18px;
            }}
            QWidget#table_header {{
                background: rgb({soft},{soft},{soft});
                border-bottom: 1px solid #E5E7EB;
            }}
            QWidget#table_row {{
                background: white;
                border-bottom: 1px solid #EEF2F6;
            }}
            QWidget#divider {{
                background: #E5E7EB;
                border: none;
            }}
            QWidget[skeleton_radius] {{
                background: rgb({base},{base},{base});
                border: none;
                border-radius: 8px;
            }}
            """
        )

# ðŸš€ Worker para streaming de clientes
class CustomerStreamerThread(QThread):
    """Carga clientes en chunks/streaming para no bloquear UI."""
    chunk_ready = pyqtSignal(list)  # Emite chunk de clientes
    stream_finished = pyqtSignal()   # SeÃ±al cuando termina
    error = pyqtSignal(str)          # SeÃ±al de error
    
    def __init__(self, username, chunk_size=50):
        super().__init__()
        self.username = username
        self.chunk_size = chunk_size
    
    def run(self):
        try:
            if self.isInterruptionRequested():
                self.stream_finished.emit()
                return

            clientes = cargar_clientes_dashboard(self.username, allow_remote_restore=False)
            if not clientes:
                clientes = cargar_clientes(self.username)
            
            if not clientes:
                print(f"[INFO] No hay clientes para {self.username}")
                self.stream_finished.emit()
                return
            
            # Ordenar clientes del mÃ¡s reciente al mÃ¡s antiguo
            def parsear_fecha(fecha_str):
                """Parse fecha con mÃºltiples formatos posibles"""
                if not fecha_str:
                    return datetime.datetime(2000, 1, 1)
                
                formatos = [
                    "%d/%m/%Y",                 # 21/01/2026
                    "%Y-%m-%d %H:%M:%S",        # 2019-06-01 00:00:00
                    "%Y-%m-%d",                 # 2019-06-01
                    "%d/%m/%Y %H:%M:%S",        # 21/01/2026 14:30:45
                    "%d/%m/%Y %H:%M",           # 21/01/2026 14:30
                ]
                
                for fmt in formatos:
                    try:
                        return datetime.datetime.strptime(str(fecha_str).strip(), fmt)
                    except ValueError:
                        continue
                
                # Si no coincide ningÃºn formato, retornar fecha mÃ­nima
                return datetime.datetime(2000, 1, 1)
            
            try:
                clientes_ordenados = sorted(
                    clientes, 
                    key=lambda x: parsear_fecha(x.get('fecha_registro', '01/01/2000')), 
                    reverse=True
                )
            except Exception as e:
                print(f"âš ï¸  Error ordenando clientes: {e}")
                clientes_ordenados = clientes
            
            # Emitir en chunks de N clientes
            total = len(clientes_ordenados)
            for i in range(0, total, self.chunk_size):
                if self.isInterruptionRequested():
                    break
                chunk = clientes_ordenados[i:i + self.chunk_size]
                self.chunk_ready.emit(chunk)
                # PequeÃ±o delay para permitir que la UI se actualice
                self.msleep(20)
            
            self.stream_finished.emit()
        except Exception as e:
            print(f"âŒ Error en streaming: {e}")
            self.error.emit(f"Error cargando clientes: {str(e)}")


# ðŸ”„ Worker para auto-refresh de clientes cada 3 segundos
class CustomerRefreshWorker(QThread):
    """Verifica actualizaciones de clientes en background sin bloquear UI."""
    refresh_ready = pyqtSignal(list)  # Emite lista actualizada de clientes
    deletions_detected = pyqtSignal(list)  # Emite IDs de clientes eliminados
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.running = True
    
    def run(self):
        """ActualizaciÃ³n continua cada 1 segundo (local) + remoto cada 5s."""
        from utils.file_handler import cargar_clientes
        local_last_check = 0
        remote_last_check = 0
        
        while self.running:
            try:
                import time
                now = time.time()
                
                # SIEMPRE leer locales cada 1 segundo (sin esperar a remoto)
                if now - local_last_check >= 1.0:
                    clientes_locales = cargar_clientes(self.username)
                    if clientes_locales:
                        self.refresh_ready.emit(clientes_locales)
                    local_last_check = now
                
                # Cada 5 segundos, actualizar desde remoto
                if now - remote_last_check >= 5.0:
                    try:
                        from utils.api_handler import obtener_clientes_remoto
                        from utils.file_handler import get_effective_branch_context

                        ctx = get_effective_branch_context(self.username) or {}
                        branch_code = str(ctx.get("code", "") or "").strip().upper()
                        clientes_remotos = obtener_clientes_remoto(
                            self.username,
                            codigo_dispositivo=branch_code or None
                        )
                        # Evitar que una respuesta vacia del endpoint legacy deje la UI en 0.
                        if isinstance(clientes_remotos, list) and clientes_remotos:
                            self.refresh_ready.emit(clientes_remotos)
                    except Exception:
                        pass
                    remote_last_check = now
                
                # Wait 500ms para no usar CPU
                self.msleep(500)
            except Exception as e:
                # Ignorar errores silenciosamente
                self.msleep(500)
    
    def stop(self):
        """Detiene el worker."""
        self.running = False


# ðŸ’¾ Worker para guardar clientes en background
class CustomerSaveWorker(QThread):
    """Guarda clientes en background sin bloquear UI."""
    save_finished = pyqtSignal(bool, str)  # Emite (Ã©xito, mensaje)
    
    def __init__(self, username, clientes, branch_code: str = ""):
        super().__init__()
        self.username = username
        self.clientes = clientes
        self.branch_code = str(branch_code or "").strip().upper()
    
    def run(self):
        """Guarda los clientes en background."""
        try:
            from utils.file_handler import guardar_clientes
            guardar_clientes(self.username, self.clientes, branch_code=self.branch_code)
            self.save_finished.emit(True, "Cliente guardado correctamente.")
        except Exception as e:
            self.save_finished.emit(False, f"Error guardando cliente: {str(e)}")

NOMBRE_GENERO_RULES = {
    # Nombres Masculinos
    "juan": "Masculino",
    "alex": "Masculino",
    "carlos": "Masculino",
    "luis": "Masculino",
    "miguel": "Masculino",
    "angel": "Masculino",
    "israel": "Masculino",
    "daniel": "Masculino",
    "gabriel": "Masculino",
    "samuel": "Masculino",
    "rafael": "Masculino",
    "manuel": "Masculino",
    "joaquin": "Masculino",
    "benjamin": "Masculino",
    "adrian": "Masculino",
    "ruben": "Masculino",
    "hector": "Masculino",
    "victor": "Masculino",
    "ramon": "Masculino",
    "simon": "Masculino",
    "anderson": "Masculino",
    "brandon": "Masculino",
    "cameron": "Masculino",
    "darwin": "Masculino",
    "edison": "Masculino",
    "hudson": "Masculino",
    "jayden": "Masculino",
    "kevin": "Masculino",
    "martin": "Masculino",
    "nelson": "Masculino",
    "orson": "Masculino",
    "person": "Masculino",
    "quillan": "Masculino",
    "roy": "Masculino",
    "stern": "Masculino",
    "tristan": "Masculino",
    "urban": "Masculino",
    "vernon": "Masculino",
    "watson": "Masculino",
    "xavier": "Masculino",
    "yuri": "Masculino",
    "zeus": "Masculino",
    "aaron": "Masculino",
    "albert": "Masculino",
    "arnold": "Masculino",
    "arthur": "Masculino",
    "austin": "Masculino",
    "august": "Masculino",
    "avery": "Masculino",
    "bailey": "Masculino",
    "ballard": "Masculino",
    "barney": "Masculino",
    "barrett": "Masculino",
    "barry": "Masculino",
    "bart": "Masculino",
    "basil": "Masculino",
    "beau": "Masculino",
    "beauregard": "Masculino",
    "beck": "Masculino",
    "benson": "Masculino",
    "bert": "Masculino",
    "bertrand": "Masculino",
    "billy": "Masculino",
    "blake": "Masculino",
    "blaise": "Masculino",
    "bo": "Masculino",
    "bob": "Masculino",
    "boris": "Masculino",
    "boyd": "Masculino",
    "brad": "Masculino",
    "bradley": "Masculino",
    "brady": "Masculino",
    "brant": "Masculino",
    "brian": "Masculino",
    "brick": "Masculino",
    "britt": "Masculino",
    "brock": "Masculino",
    "broderick": "Masculino",
    "brook": "Masculino",
    "bruce": "Masculino",
    "bruno": "Masculino",
    "bryant": "Masculino",
    "bryce": "Masculino",
    "byrd": "Masculino",
    "byron": "Masculino",
    "cain": "Masculino",
    "calvin": "Masculino",
    "camden": "Masculino",
    "canal": "Masculino",
    "carl": "Masculino",
    "carleton": "Masculino",
    "carlisle": "Masculino",
    "carlton": "Masculino",
    "carmine": "Masculino",
    "carol": "Masculino",
    "carolus": "Masculino",
    "carson": "Masculino",
    "cary": "Masculino",
    "casey": "Masculino",
    "casper": "Masculino",
    "cassidy": "Masculino",
    "cecil": "Masculino",
    "cedar": "Masculino",
    "cedric": "Masculino",
    "chadd": "Masculino",
    "chadwick": "Masculino",
    "chaim": "Masculino",
    "chambers": "Masculino",
    "champ": "Masculino",
    "chandler": "Masculino",
    "chaney": "Masculino",
    "channing": "Masculino",
    "charles": "Masculino",
    "chas": "Masculino",
    "chase": "Masculino",
    "chat": "Masculino",
    "chauncey": "Masculino",
    "chester": "Masculino",
    "chet": "Masculino",
    "chev": "Masculino",
    "chevron": "Masculino",
    "chick": "Masculino",
    "chin": "Masculino",
    "chip": "Masculino",
    "chloe": "Masculino",
    "chris": "Masculino",
    "christ": "Masculino",
    "christian": "Masculino",
    "christie": "Masculino",
    "christofer": "Masculino",
    "christopher": "Masculino",
    "christy": "Masculino",
    "chuck": "Masculino",
    "churchill": "Masculino",
    "cid": "Masculino",
    "cillian": "Masculino",
    "cipriano": "Masculino",
    "clarence": "Masculino",
    "clark": "Masculino",
    "clarke": "Masculino",
    "claud": "Masculino",
    "claude": "Masculino",
    "claudius": "Masculino",
    "claus": "Masculino",
    "clay": "Masculino",
    "clayton": "Masculino",
    "clem": "Masculino",
    "clemens": "Masculino",
    "clement": "Masculino",
    "cletus": "Masculino",
    "cliff": "Masculino",
    "clifford": "Masculino",
    "clifton": "Masculino",
    "clint": "Masculino",
    "clinton": "Masculino",
    "clive": "Masculino",
    "clovis": "Masculino",
    "clyde": "Masculino",
    "coalter": "Masculino",
    "coby": "Masculino",
    "cody": "Masculino",
    "col": "Masculino",
    "cole": "Masculino",
    "coleman": "Masculino",
    "colin": "Masculino",
    "colleen": "Masculino",
    "colley": "Masculino",
    "collier": "Masculino",
    "collin": "Masculino",
    "collis": "Masculino",
    "collins": "Masculino",
    "colten": "Masculino",
    "colton": "Masculino",
    "columbus": "Masculino",
    "colvin": "Masculino",
    "coman": "Masculino",
    "compton": "Masculino",
    "con": "Masculino",
    "conan": "Masculino",
    "conby": "Masculino",
    "conde": "Masculino",
    "conejar": "Masculino",
    "conglton": "Masculino",
    "conlan": "Masculino",
    "conley": "Masculino",
    "connell": "Masculino",
    "conner": "Masculino",
    "connery": "Masculino",
    "connolly": "Masculino",
    "connor": "Masculino",
    "connors": "Masculino",
    "conny": "Masculino",
    "conor": "Masculino",
    "conor": "Masculino",
    "conover": "Masculino",
    "conrader": "Masculino",
    "conrado": "Masculino",
    "conran": "Masculino",
    "conrath": "Masculino",
    "conred": "Masculino",
    "conrey": "Masculino",
    "conrick": "Masculino",
    "conron": "Masculino",
    "conroy": "Masculino",
    "conser": "Masculino",
    "consett": "Masculino",
    "conserv": "Masculino",
    "consider": "Masculino",
    "consol": "Masculino",
    "conson": "Masculino",
    "consort": "Masculino",
    "consover": "Masculino",
    "ronal": "Masculino",
    "ronal": "Masculino",

    "consroe": "Masculino",
    "constance": "Masculino",
    "constans": "Masculino",
    "constant": "Masculino",
    "constante": "Masculino",
    "constantia": "Masculino",
    "constantine": "Masculino",
    "constantinople": "Masculino",
    "constantius": "Masculino",
    "constantine": "Masculino",
    # Nombres Femeninos
    "elizabeth": "Femenino",
    "catherine": "Femenino",
    "margaret": "Femenino",
    "judith": "Femenino",
    "rachel": "Femenino",
    "sophie": "Femenino",
    "michelle": "Femenino",
    "christine": "Femenino",
    "deborah": "Femenino",
    "caroline": "Femenino",
    "helen": "Femenino",
    "dorothy": "Femenino",
    "nancy": "Femenino",
    "frances": "Femenino",
    "gladys": "Femenino",
    "louise": "Femenino",
    "agnes": "Femenino",
    "edith": "Femenino",
    "marie": "Femenino",
    "bernice": "Femenino",
    "beatrice": "Femenino",
    "constance": "Femenino",
    "denise": "Femenino",
    "evelyn": "Femenino",
    "florence": "Femenino",
    "geraldine": "Femenino",
    "hilda": "Femenino",
    "iris": "Femenino",
    "jacqueline": "Femenino",
    "katherine": "Femenino",
    "vivian": "Femenino",
    "alice": "Femenino",
    "barbara": "Femenino",
    "belle": "Femenino",
    "bertha": "Femenino",
    "beverly": "Femenino",
    "blanche": "Femenino",
    "bonnie": "Femenino",
    "brenda": "Femenino",
    "bridget": "Femenino",
    "brittany": "Femenino",
    "brooke": "Femenino",
    "browns": "Femenino",
    "brunhilde": "Femenino",
    "bryn": "Femenino",
    "buffy": "Femenino",
    "caitlin": "Femenino",
    "calista": "Femenino",
    "callie": "Femenino",
    "camelia": "Femenino",
    "camilla": "Femenino",
    "camille": "Femenino",
    "candace": "Femenino",
    "candice": "Femenino",
    "candy": "Femenino",
    "caren": "Femenino",
    "caridad": "Femenino",
    "carina": "Femenino",
    "carla": "Femenino",
    "carlene": "Femenino",
    "carley": "Femenino",
    "carlin": "Femenino",
    "carlisle": "Femenino",
    "carlotta": "Femenino",
    "carmel": "Femenino",
    "carmela": "Femenino",
    "carmelita": "Femenino",
    "carmen": "Femenino",
    "carmilla": "Femenino",
    "carol": "Femenino",
    "carole": "Femenino",
    "carolina": "Femenino",
    "caroline": "Femenino",
    "carolyn": "Femenino",
    "caron": "Femenino",
    "carrie": "Femenino",
    "carroll": "Femenino",
    "carry": "Femenino",
    "carson": "Femenino",
    "carter": "Femenino",
    "carthage": "Femenino",
    "cartney": "Femenino",
    "cary": "Femenino",
    "caryl": "Femenino",
    "casa": "Femenino",
    "casandra": "Femenino",
    "casey": "Femenino",
    "casilda": "Femenino",
    "casilda": "Femenino",
    "casilla": "Femenino",
    "casino": "Femenino",
    "casity": "Femenino",
    "cass": "Femenino",
    "cassandra": "Femenino",
    "cassidy": "Femenino",
    "cassie": "Femenino",
    "cassis": "Femenino",
    "cassiter": "Femenino",
    "cassity": "Femenino",
    "castor": "Femenino",
    "castor": "Femenino",
    "castra": "Femenino",
    "caswell": "Femenino",
    "cat": "Femenino",
    "catalina": "Femenino",
    "catarina": "Femenino",
    "catharine": "Femenino",
    "cathay": "Femenino",
    "cathee": "Femenino",
    "cathel": "Femenino",
    "cathel": "Femenino",
    "cathelin": "Femenino",
    "catherine": "Femenino",
    "catherin": "Femenino",
    "catherina": "Femenino",
    "catheryn": "Femenino",
    "cathey": "Femenino",
    "cathleen": "Femenino",
    "cathren": "Femenino",
    "cathrine": "Femenino",
    "cathy": "Femenino",
    "catiel": "Femenino",
    "catiel": "Femenino",
    "catina": "Femenino",
    "catire": "Femenino",
    "catita": "Femenino",
    "catlin": "Femenino",
    "catlyn": "Femenino",
    "catrice": "Femenino",
    "catriel": "Femenino",
    "catrina": "Femenino",
    "catrine": "Femenino",
    "catriona": "Femenino",
    "catsmeat": "Femenino",
    "cattell": "Femenino",
    "catuvolci": "Femenino",
    "catya": "Femenino",
    "caty": "Femenino",
    "cauda": "Femenino",
    "caudle": "Femenino",
    "caulfield": "Femenino",
    "caura": "Femenino",
    "cauri": "Femenino",
    "causa": "Femenino",
    "causpice": "Femenino",
    "caustal": "Femenino",
    "cautela": "Femenino",
    "cauteres": "Femenino",
    "cauterise": "Femenino",
    "cauterous": "Femenino",
    "cauteryze": "Femenino",
    "cautia": "Femenino",
    "magali": "Femenino",    
    "jhanet": "Femenino",
    "janeth": "Femenino",
    "vivi": "Femenino",
    "cautivant": "Femenino",
    "cautiva": "Femenino",
    "cautivate": "Femenino",
    "cautive": "Femenino",
    "cautivity": "Femenino",
    "cautivo": "Femenino",
    "cava": "Femenino",
    "cavalcade": "Femenino",
    "cavalcanti": "Femenino",
    "cavalcanti": "Femenino",
    "cavalcat": "Femenino",
    "cavalcature": "Femenino",
    "cavalengo": "Femenino",
    "cavalera": "Femenino",
    "cavaleria": "Femenino",
    "cavalerish": "Femenino",
    "cavaleris": "Femenino",
    "cavalerism": "Femenino",
    "cavalery": "Femenino",
    "cavalesse": "Femenino",
    "cavaletta": "Femenino",
    "cavali": "Femenino",
    "cavalier": "Femenino",
    "cavaliera": "Femenino",
    "cavalierism": "Femenino",
    "cavalierly": "Femenino",
    "cavalierness": "Femenino",
    "cavaliers": "Femenino",
    "cavalierss": "Femenino",
    "cavaliery": "Femenino",
    "cavalism": "Femenino",
    "cavality": "Femenino",
    "cavalito": "Femenino",
    "cavalives": "Femenino",
    "cavalla": "Femenino",
    "cavallan": "Femenino",
    "cavallar": "Femenino",
    "cavallari": "Femenino",
    "cavallarol": "Femenino",
    "cavallata": "Femenino",
    "cavallazia": "Femenino",
    "cavallet": "Femenino",
    "cavalletta": "Femenino",
    "cavalletti": "Femenino",
    "cavalletto": "Femenino",
    "cavallezza": "Femenino",
    "cavalliera": "Femenino",
    "cavallierato": "Femenino",
    "cavalliere": "Femenino",
    "cavallieressa": "Femenino",
    "cavallierism": "Femenino",
    "cavallieresco": "Femenino",
    "cavallierith": "Femenino",
    "cavalliers": "Femenino",
    "cavallierit": "Femenino",
    "cavallierito": "Femenino",
    "cavallierizz": "Femenino",
    "cavallino": "Femenino",
    "cavallino": "Femenino",
    "cavallita": "Femenino",
    "cavallite": "Femenino",
    "cavallo": "Femenino",
    "cavallolino": "Femenino",
    "cavallone": "Femenino",
    # Nombres Peruanos Masculinos
    "gonzalo": "Masculino",
    "sebastian": "Masculino",
    "mariano": "Masculino",
    "alejandro": "Masculino",
    "fernando": "Masculino",
    "ricardo": "Masculino",
    "federico": "Masculino",
    "guillermo": "Masculino",
    "humberto": "Masculino",
    "ignacio": "Masculino",
    "javier": "Masculino",
    "jorge": "Masculino",
    "julio": "Masculino",
    "leonardo": "Masculino",
    "lorenzo": "Masculino",
    "luciano": "Masculino",
    "oswaldo": "Masculino",
    "pablo": "Masculino",
    "patricio": "Masculino",
    "quintin": "Masculino",
    "ramiro": "Masculino",
    "raul": "Masculino",
    "rogelio": "Masculino",
    "rolando": "Masculino",
    "romeo": "Masculino",
    "sergio": "Masculino",
    "silvano": "Masculino",
    "socrates": "Masculino",
    "tarcisio": "Masculino",
    "teodoro": "Masculino",
    "tiburcio": "Masculino",
    "timoteo": "Masculino",
    "tobias": "Masculino",
    "tonio": "Masculino",
    "torres": "Masculino",
    "total": "Masculino",
    "tovar": "Masculino",
    "traconis": "Masculino",
    "tranquilo": "Masculino",
    "travail": "Masculino",
    "travers": "Masculino",
    "travieso": "Masculino",
    "trecho": "Masculino",
    "tremolinas": "Masculino",
    "tremont": "Masculino",
    "trenta": "Masculino",
    "tremesino": "Masculino",
    "trigoso": "Masculino",
    "trinidad": "Masculino",
    "trino": "Masculino",
    "tripoli": "Masculino",
    "tristano": "Masculino",
    "triton": "Masculino",
    "triunfo": "Masculino",
    "trivio": "Masculino",
    "troco": "Masculino",
    "troiano": "Masculino",
    "troicas": "Masculino",
    "troila": "Masculino",
    "troilo": "Masculino",
    "trolada": "Masculino",
    "troleon": "Masculino",
    "trolley": "Masculino",
    "trollope": "Masculino",
    "tromba": "Masculino",
    "trombador": "Masculino",
    "trombas": "Masculino",
    "trombato": "Masculino",
    "trombazgo": "Masculino",
    "trombazgo": "Masculino",
    "trombon": "Masculino",
    "tromboncillo": "Masculino",
    "trombonista": "Masculino",
    "trombudo": "Masculino",
    "tromerizo": "Masculino",
    "trometada": "Masculino",
    "trometon": "Masculino",
    "tromicador": "Masculino",
    "tromical": "Masculino",
    "tromicazo": "Masculino",
    "tromiceria": "Masculino",
    "tromicha": "Masculino",
    "tromichador": "Masculino",
    "tromichana": "Masculino",
    "tromichano": "Masculino",
    "tromicharia": "Masculino",
    "tromichata": "Masculino",
    "tromichear": "Masculino",
    "tromichera": "Masculino",
    "tromicheria": "Masculino",
    "tromichero": "Masculino",
    "tromichesco": "Masculino",
    "tromicheta": "Masculino",
    "tromichico": "Masculino",
    "tromichil": "Masculino",
    "tromichilla": "Masculino",
    # Nombres Peruanos Femeninos
    "patricia": "Femenino",
    "gabriela": "Femenino",
    "alejandra": "Femenino",
    "fernanda": "Femenino",
    "ricarda": "Femenino",
    "federica": "Femenino",
    "guillermina": "Femenino",
    "humberta": "Femenino",
    "ignacia": "Femenino",
    "juana": "Femenino",
    "javiera": "Femenino",
    "jorgelina": "Femenino",
    "julia": "Femenino",
    "leonarda": "Femenino",
    "lorena": "Femenino",
    "luciana": "Femenino",
    "oswaldina": "Femenino",
    "paula": "Femenino",
    "patrÃ­cia": "Femenino",
    "quintina": "Femenino",
    "ramirez": "Femenino",
    "raulina": "Femenino",
    "rogeliana": "Femenino",
    "rolanda": "Femenino",
    "romea": "Femenino",
    "sergia": "Femenino",
    "silvana": "Femenino",
    "socrata": "Femenino",
    "tarcisia": "Femenino",
    "teodora": "Femenino",
    "tiburciana": "Femenino",
    "timotea": "Femenino",
    "tobias": "Femenino",
    "tonia": "Femenino",
    "torres": "Femenino",
    "totala": "Femenino",
    "tovara": "Femenino",
    "traconia": "Femenino",
    "tranquila": "Femenino",
    "travail": "Femenino",
    "traversa": "Femenino",
    "traviesa": "Femenino",
    "trecha": "Femenino",
    "tremolinica": "Femenino",
    "tremonta": "Femenino",
    "trenta": "Femenino",
    "tremesina": "Femenino",
    "trigosa": "Femenino",
    "trinidad": "Femenino",
    "trina": "Femenino",
    "tripolia": "Femenino",
    "tristana": "Femenino",
    "tritona": "Femenino",
    "triunfa": "Femenino",
    "trivia": "Femenino",
    "troca": "Femenino",
    "troiana": "Femenino",
    "troica": "Femenino",
    "troila": "Femenino",
    "troilada": "Femenino",
    "troileona": "Femenino",
    "trollea": "Femenino",
    "trollopa": "Femenino",
    "trombada": "Femenino",
    "trombadora": "Femenino",
    "trombas": "Femenino",
    "trombata": "Femenino",
    "trombazga": "Femenino",
    "trombona": "Femenino",
    "tromboncilla": "Femenino",
    "trombonista": "Femenino",
    "trombuda": "Femenino",
    "tromeriza": "Femenino",
    "trometada": "Femenino",
    "trometona": "Femenino",
    "tromicadora": "Femenino",
    "tromicala": "Femenino",
    "tromicaza": "Femenino",
    "tromiceria": "Femenino",
    "tromichana": "Femenino",
    "tromichadora": "Femenino",
    "tromichana": "Femenino",
    "tromichana": "Femenino",
    "tromicharia": "Femenino",
    "tromichata": "Femenino",
    "tromicheara": "Femenino",
    "tromichera": "Femenino",
    "tromicheria": "Femenino",
    "tromichera": "Femenino",
    "tromichesca": "Femenino",
    "tromicheta": "Femenino",
    "tromichica": "Femenino",
    "tromichila": "Femenino",
    "tromichilla": "Femenino",
    # Nombres adicionales populares
    "ronald": "Masculino",
    "ronal": "Masculino",
    "goku": "Masculino",
    "vegeta": "Masculino",
    "gohan": "Masculino",
    "krillin": "Masculino",
    "trunks": "Masculino",
    "buu": "Masculino",
    "frieza": "Masculino",
    "cell": "Masculino",
    "saitama": "Masculino",
    "kazuki": "Masculino",
    "naruto": "Masculino",
    "sasuke": "Masculino",
    "ichigo": "Masculino",
    "luffy": "Masculino",
    "zoro": "Masculino",
    "sanji": "Masculino",
    "tanjiro": "Masculino",
    "rengoku": "Masculino",
    "giyu": "Masculino",
    "shinobu": "Femenino",
    "mitsuri": "Femenino",
    "nezuko": "Femenino",
    "bulma": "Femenino",
    "videl": "Femenino",
    "chi-chi": "Femenino",
    "caulifla": "Femenino",
    "kale": "Femenino",
    "cheelai": "Femenino",
    "ochako": "Femenino",
    "tsuyu": "Femenino",
    "momo": "Femenino",
    "jirou": "Femenino",
    "hagakure": "Femenino",
    "midnight": "Femenino",
}

class DNISearchWorker(QThread):
    """Worker que realiza la bÃºsqueda de DNI en un thread separado"""
    search_completed = pyqtSignal(str, str)  # nombre, fecha_nacimiento
    search_failed = pyqtSignal(str)  # mensaje de error
    
    def __init__(self, dni):
        super().__init__()
        self.dni = dni
    
    def run(self):
        try:
            full_name, birth_date = buscar_dni_api(self.dni)
            if full_name:
                self.search_completed.emit(full_name, birth_date or "")
            else:
                self.search_failed.emit("No se encontrÃ³ informaciÃ³n para ese DNI")
        except Exception as e:
            self.search_failed.emit(f"Error al buscar: {str(e)}")


def _buscar_dni_por_nombres_selenium(nombres, ap_pat, ap_mat):
    """
    Busca posibles DNIs por nombres usando un navegador automatizado (selenium).
    Retorna lista de dicts: {dni, ap_pat, ap_mat, nombres}.
    """
    # Imports lazy para no cargar selenium si el usuario no usa esta opcion.
    import os as _os
    import time as _time

    try:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.service import Service  # type: ignore
        from selenium.webdriver.common.keys import Keys  # type: ignore
        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
    except Exception as e:
        raise RuntimeError("No se encontro selenium/webdriver_manager. Instala dependencias.") from e

    _os.environ.setdefault("WDM_LOG_LEVEL", "0")

    # Cache driver path (webdriver_manager download) to avoid repeated installs.
    global _WDM_DRIVER_PATH
    try:
        _WDM_DRIVER_PATH
    except Exception:
        _WDM_DRIVER_PATH = None
    if _WDM_DRIVER_PATH is None:
        # Best-effort lock using module-level threading.
        try:
            global _WDM_LOCK
            _WDM_LOCK
        except Exception:
            _WDM_LOCK = threading.Lock()
        with _WDM_LOCK:
            if _WDM_DRIVER_PATH is None:
                _WDM_DRIVER_PATH = ChromeDriverManager().install()

    driver_path = _WDM_DRIVER_PATH

    options = webdriver.ChromeOptions()
    # No mostrar ventana del navegador.
    # "new" es recomendado en Chrome moderno; si no existe, Chrome lo ignora.
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-default-apps")
    options.add_argument("--window-size=1024,768")
    options.page_load_strategy = "eager"

    options.add_experimental_option(
        "prefs",
        {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
        },
    )

    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    try:
        try:
            driver.execute_cdp_cmd(
                "Network.setBlockedURLs",
                {
                    "urls": [
                        "*.css*",
                        "*.woff*",
                        "*.ttf*",
                        "*.otf*",
                        "*.png*",
                        "*.jpg*",
                        "*ads*",
                        "*analytics*",
                        "*doubleclick*",
                    ]
                },
            )
            driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass

        driver.get("https://buscardniperu.com/buscar-dni-por-nombres/")

        driver.find_element("name", "ap_pat").send_keys(str(ap_pat or "").upper())
        driver.find_element("name", "ap_mat").send_keys(str(ap_mat or "").upper())
        input_nom = driver.find_element("name", "nombres")
        input_nom.send_keys(str(nombres or "").upper())
        input_nom.send_keys(Keys.ENTER)

        _time.sleep(1.2)

        filas = driver.find_elements("css selector", "table tbody tr")
        results = []
        for fila in filas:
            cols = fila.find_elements("tag name", "td")
            if len(cols) >= 4:
                results.append(
                    {
                        "dni": str(cols[0].text or "").strip(),
                        "ap_pat": str(cols[1].text or "").strip(),
                        "ap_mat": str(cols[2].text or "").strip(),
                        "nombres": str(cols[3].text or "").strip(),
                    }
                )
        return results
    finally:
        try:
            driver.quit()
        except Exception:
            pass


class NameSearchWorker(QThread):
    """Worker para buscar DNI por nombres en thread separado."""

    search_completed = pyqtSignal(list)  # resultados
    search_failed = pyqtSignal(str)  # mensaje de error

    def __init__(self, nombres, ap_pat, ap_mat):
        super().__init__()
        self.nombres = str(nombres or "").strip()
        self.ap_pat = str(ap_pat or "").strip()
        self.ap_mat = str(ap_mat or "").strip()

    def run(self):
        try:
            if not self.nombres or not self.ap_pat or not self.ap_mat:
                self.search_failed.emit("Completa nombres y apellidos antes de buscar.")
                return
            resultados = _buscar_dni_por_nombres_selenium(self.nombres, self.ap_pat, self.ap_mat)
            if resultados:
                self.search_completed.emit(resultados)
            else:
                self.search_failed.emit("No se encontraron resultados.")
        except Exception as e:
            self.search_failed.emit(f"Error buscando por nombres: {e}")


class NameSearchResultsDialog(QDialog):
    """Modal para seleccionar un DNI de la lista de resultados."""

    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resultados por nombres")
        self.setMinimumSize(640, 360)
        self._selected = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        info = QLabel("Selecciona un resultado para usar su DNI:")
        layout.addWidget(info)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["DNI", "AP. PAT", "AP. MAT", "NOMBRES"])
        self.table.setRowCount(0)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        for row, item in enumerate(results or []):
            if not isinstance(item, dict):
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item.get("dni", "") or "")))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item.get("ap_pat", "") or "")))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(item.get("ap_mat", "") or "")))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(item.get("nombres", "") or "")))
            # Guardar payload
            self.table.item(row, 0).setData(Qt.UserRole, dict(item))

        self.table.itemDoubleClicked.connect(lambda _it: self._accept_selected())
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_use = QPushButton("Usar seleccionado")
        btn_use.setStyleSheet("font-weight: 600;")
        btn_use.clicked.connect(self._accept_selected)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_use)
        layout.addLayout(btn_row)

    def _accept_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        it = self.table.item(row, 0)
        if it is None:
            return
        payload = it.data(Qt.UserRole)
        if isinstance(payload, dict):
            self._selected = dict(payload)
            self.accept()

    def selected(self):
        return dict(self._selected) if isinstance(self._selected, dict) else None


class NameSearchDialog(QDialog):
    """Modal para ingresar nombres y buscar DNI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar DNI por nombres")
        self.setMinimumSize(520, 320)
        self._worker = None
        self._results = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        info = QLabel("Ingresa nombres y apellidos. Luego elige el DNI correcto.")
        info.setStyleSheet("color: #555;")
        layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)

        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("Primer nombre")
        self.second_name = QLineEdit()
        self.second_name.setPlaceholderText("Segundo nombre (opcional)")
        self.ap_pat = QLineEdit()
        self.ap_pat.setPlaceholderText("Apellido paterno")
        self.ap_mat = QLineEdit()
        self.ap_mat.setPlaceholderText("Apellido materno")

        form.addRow("Primer nombre:", self.first_name)
        form.addRow("Segundo nombre:", self.second_name)
        form.addRow("Apellido paterno:", self.ap_pat)
        form.addRow("Apellido materno:", self.ap_mat)
        layout.addLayout(form)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #666;")
        layout.addWidget(self.status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        self.btn_search = QPushButton("Buscar")
        self.btn_search.setStyleSheet("font-weight: 600;")
        self.btn_search.clicked.connect(self._start_search)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_search)
        layout.addLayout(btn_row)

    def _start_search(self):
        nombres = f"{self.first_name.text().strip()} {self.second_name.text().strip()}".strip()
        ap_pat = self.ap_pat.text().strip()
        ap_mat = self.ap_mat.text().strip()
        if not nombres or not ap_pat or not ap_mat:
            QMessageBox.warning(self, "Campos incompletos", "Completa primer nombre y apellidos.")
            return

        self.btn_search.setEnabled(False)
        self.status.setText("Buscando... (puede tardar unos segundos)")

        self._worker = NameSearchWorker(nombres, ap_pat, ap_mat)
        self._worker.search_completed.connect(self._on_results)
        self._worker.search_failed.connect(self._on_error)
        self._worker.start()

    def _on_results(self, results):
        self.btn_search.setEnabled(True)
        self.status.setText("")
        self._results = list(results or [])

        dlg = NameSearchResultsDialog(self._results, self)
        if dlg.exec_() == QDialog.Accepted:
            self._selected = dlg.selected()
            if isinstance(self._selected, dict):
                self.accept()

    def _on_error(self, msg):
        self.btn_search.setEnabled(True)
        self.status.setText("")
        QMessageBox.warning(self, "Busqueda por nombres", str(msg or "Error"))

    def selected(self):
        return dict(getattr(self, "_selected", None)) if isinstance(getattr(self, "_selected", None), dict) else None

class LoaderSVG(QWidget):
    """Widget que muestra un loader circular animado, checkmark o error en SVG"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotation = 0
        self.state = "hidden"  # hidden, loading, success, error
        self.setFixedSize(24, 24)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        
    def start_loading(self):
        self.state = "loading"
        self.rotation = 0
        self.timer.start(30)
        self.show()
        self.update()
    
    def show_success(self):
        self.timer.stop()
        self.state = "success"
        self.show()
        self.update()
        # Mostrar checkmark por 1.5 segundos y luego ocultarse
        QTimer.singleShot(1500, self.hide)
    
    def show_error(self):
        self.timer.stop()
        self.state = "error"
        self.show()
        self.update()
        # Mostrar error por 2 segundos y luego ocultarse
        QTimer.singleShot(2000, self.hide)
    
    def rotate(self):
        self.rotation = (self.rotation + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.state == "success":
            # Dibujar checkmark en verde
            painter.setPen(QPen(QColor("#2a8659"), 2.5))
            painter.drawPath(self.get_checkmark_path())
        elif self.state == "error":
            # Dibujar X en rojo
            painter.setPen(QPen(QColor("#d32f2f"), 2.5))
            painter.drawPath(self.get_error_path())
        elif self.state == "loading":
            # Dibujar loader rotatorio
            painter.save()
            painter.translate(12, 12)
            painter.rotate(self.rotation)
            painter.translate(-12, -12)
            
            # CÃ­rculo externo (fondo)
            painter.setPen(QPen(QColor("#e0e0e0"), 2))
            painter.drawEllipse(2, 2, 20, 20)
            
            # CÃ­rculo interno (rotatorio)
            painter.setPen(QPen(QColor("#2a8659"), 2))
            painter.drawArc(2, 2, 20, 20, 0, 90 * 16)
            
            painter.restore()
    
    def get_checkmark_path(self):
        path = QPainterPath()
        # Checkmark shape
        path.moveTo(6, 12)
        path.lineTo(10, 16)
        path.lineTo(18, 8)
        return path
    
    def get_error_path(self):
        path = QPainterPath()
        # X shape (error)
        path.moveTo(6, 6)
        path.lineTo(18, 18)
        path.moveTo(18, 6)
        path.lineTo(6, 18)
        return path


class CustomerTagSelectionDialog(QDialog):
    """Dialogo para seleccionar multiples etiquetas de cliente."""
    def __init__(self, available_tags, selected_tags=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Etiquetas")
        self.setMinimumWidth(360)
        self.available_tags = [str(t).strip() for t in (available_tags or []) if str(t).strip()]
        selected_set = {str(t).strip().casefold() for t in (selected_tags or []) if str(t).strip()}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        info = QLabel("Marca una o varias etiquetas para este cliente:")
        info.setStyleSheet("color: #616161; font-size: 12px;")
        layout.addWidget(info)

        self.list_tags = QListWidget()
        self.list_tags.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_tags.setStyleSheet("""
            QListWidget {
                border: 1px solid #d0d0d0;
                background: white;
                padding: 4px;
            }
        """)
        for tag in self.available_tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if tag.casefold() in selected_set else Qt.Unchecked)
            self.list_tags.addItem(item)
        layout.addWidget(self.list_tags)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet("font-weight: 600;")
        btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

    def selected_tags(self):
        tags = []
        for i in range(self.list_tags.count()):
            item = self.list_tags.item(i)
            if item.checkState() == Qt.Checked:
                tags.append(item.text().strip())
        return tags


class CustomerTagManagerDialog(QDialog):
    """Dialogo para crear/eliminar etiquetas de clientes."""
    tags_updated = pyqtSignal(list)

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self._protected_defaults = {"falta pagar", "pagado"}
        self._tags = []
        self.setWindowTitle("Gestionar Etiquetas de Clientes")
        self.setMinimumWidth(420)
        self.setup_ui()
        self._reload_tags()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Etiquetas disponibles")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #212121;")
        layout.addWidget(title)

        self.list_tags = QListWidget()
        self.list_tags.setStyleSheet("""
            QListWidget {
                border: 1px solid #d0d0d0;
                background: white;
                padding: 4px;
            }
        """)
        layout.addWidget(self.list_tags)

        input_row = QHBoxLayout()
        self.entry_new_tag = QLineEdit()
        self.entry_new_tag.setPlaceholderText("Ejemplo: VIP, Deuda alta, Seguimiento")
        self.entry_new_tag.returnPressed.connect(self._add_tag)
        btn_add = QPushButton("Agregar Etiqueta")
        btn_add.clicked.connect(self._add_tag)
        input_row.addWidget(self.entry_new_tag)
        input_row.addWidget(btn_add)
        layout.addLayout(input_row)

        help_label = QLabel("Las etiquetas por defecto 'Falta pagar' y 'Pagado' no se pueden eliminar.")
        help_label.setStyleSheet("color: #757575; font-size: 11px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        btn_row = QHBoxLayout()
        btn_delete = QPushButton("Eliminar Seleccionada")
        btn_delete.clicked.connect(self._delete_selected_tag)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _reload_tags(self):
        self._tags = cargar_etiquetas_clientes(self.username)
        self.list_tags.clear()
        for tag in self._tags:
            self.list_tags.addItem(tag)

    def _add_tag(self):
        new_tag = self.entry_new_tag.text().strip()
        if not new_tag:
            return

        if any(t.casefold() == new_tag.casefold() for t in self._tags):
            QMessageBox.information(self, "Etiqueta repetida", "Esa etiqueta ya existe.")
            return

        updated = list(self._tags) + [new_tag]
        if not guardar_etiquetas_clientes(self.username, updated):
            QMessageBox.warning(self, "Error", "No se pudo guardar la nueva etiqueta.")
            return

        self.entry_new_tag.clear()
        self._reload_tags()
        self.tags_updated.emit(list(self._tags))

    def _delete_selected_tag(self):
        item = self.list_tags.currentItem()
        if item is None:
            QMessageBox.information(self, "Selecciona una etiqueta", "Primero selecciona una etiqueta para eliminar.")
            return

        tag = item.text().strip()
        if tag.casefold() in self._protected_defaults:
            QMessageBox.information(self, "No permitido", "No puedes eliminar las etiquetas por defecto.")
            return

        updated = [t for t in self._tags if t.casefold() != tag.casefold()]
        if not guardar_etiquetas_clientes(self.username, updated):
            QMessageBox.warning(self, "Error", "No se pudo eliminar la etiqueta.")
            return

        self._reload_tags()
        self.tags_updated.emit(list(self._tags))


class NewCustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.dni_search_worker = None  # Worker para bÃºsqueda de DNI
        self.save_worker = None  # Worker para guardar clientes
        self.available_tags = []
        self.selected_tags = []
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowCloseButtonHint)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Nuevo Cliente")
        self.setGeometry(100, 100, 600, 650)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        
        layout = main_layout
        
        # Estilos minimalista
        style_label = "color: #1a1a1a; font-weight: 600; font-size: 12px;"
        style_input = """QLineEdit, QDateEdit {
            padding: 10px;
            border: 1px solid #d0d0d0;
            border-radius: 0px;
            background-color: white;
            font-size: 12px;
            color: #1a1a1a;
        }
        QLineEdit:focus, QDateEdit:focus {
            border: 1px solid #2a2a2a;
        }
        QDateEdit::down-arrow {
            image: none;
        }"""
        style_combo = """QComboBox {
            padding: 10px;
            border: 1px solid #d0d0d0;
            border-radius: 0px;
            background-color: white;
            font-size: 12px;
            color: #1a1a1a;
        }
        QComboBox::drop-down {
            border: none;
        }"""
        style_btn_search = """QPushButton {
            padding: 10px 15px;
            background-color: #2a8659;
            color: white;
            border: none;
            border-radius: 0px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #1f6043;
        }"""
        style_btn_cancel = """QPushButton {
            padding: 10px 20px;
            background-color: #f5f5f5;
            color: #1a1a1a;
            border: 1px solid #d0d0d0;
            border-radius: 0px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #efefef;
        }"""
        style_btn_save = """QPushButton {
            padding: 10px 20px;
            background-color: #2a2a2a;
            color: white;
            border: none;
            border-radius: 0px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #1a1a1a;
        }"""
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # DNI con botÃ³n de bÃºsqueda
        dni_label = QLabel("DNI:")
        dni_label.setStyleSheet(style_label)
        layout.addWidget(dni_label)
        
        dni_container = QWidget()
        dni_layout = QHBoxLayout(dni_container)
        dni_layout.setContentsMargins(0, 0, 0, 0)
        dni_layout.setSpacing(10)
        
        self.nuevo_dni_entry = QLineEdit()
        self.nuevo_dni_entry.setPlaceholderText("Ingrese DNI")
        self.nuevo_dni_entry.setStyleSheet(style_input)
        dni_layout.addWidget(self.nuevo_dni_entry)
        
        btn_search = QPushButton("Buscar")
        btn_search.setObjectName("searchButton")
        btn_search.clicked.connect(self.search_customer_by_dni)
        btn_search.setFixedWidth(80)
        btn_search.setStyleSheet(style_btn_search)
        dni_layout.addWidget(btn_search)
        
        layout.addWidget(dni_container)

        # Opcion alternativa: buscar DNI por nombres (abre modal).
        btn_name_search = QPushButton("¿No sabes su DNI? Buscar por nombres")
        btn_name_search.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            f = btn_name_search.font()
            f.setUnderline(True)
            btn_name_search.setFont(f)
        except Exception:
            pass
        btn_name_search.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #1565C0;
                text-align: left;
                padding: 2px 0px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #0D47A1;
            }
        """)
        btn_name_search.clicked.connect(self.open_name_search_modal)
        layout.addWidget(btn_name_search)
        
        # Nombre con loader
        name_label = QLabel("Nombre completo:")
        name_label.setStyleSheet(style_label)
        layout.addWidget(name_label)
        
        name_container = QWidget()
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(10)
        
        self.customer_name_entry = QLineEdit()
        self.customer_name_entry.setPlaceholderText("Nombre completo")
        self.customer_name_entry.setStyleSheet(style_input)
        self.customer_name_entry.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.customer_name_entry)
        
        # Loader SVG
        self.name_loader = LoaderSVG()
        self.name_loader.hide()
        name_layout.addWidget(self.name_loader)
        name_layout.addStretch()
        
        layout.addWidget(name_container)
        
        # Fecha de nacimiento y gÃ©nero
        details_container = QWidget()
        details_layout = QGridLayout(details_container)
        details_layout.setSpacing(12)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        birth_label = QLabel("Fecha de nacimiento:")
        birth_label.setStyleSheet(style_label)
        details_layout.addWidget(birth_label, 0, 0)
        
        self.customer_birth_date_entry = QDateEdit(calendarPopup=True)
        self.customer_birth_date_entry.setDate(QDate.currentDate())
        self.customer_birth_date_entry.setStyleSheet(style_input)
        details_layout.addWidget(self.customer_birth_date_entry, 1, 0)
        
        gender_label = QLabel("GÃ©nero:")
        gender_label.setStyleSheet(style_label)
        details_layout.addWidget(gender_label, 0, 1)
        
        self.customer_gender_combo = QComboBox()
        self.customer_gender_combo.addItems(["Masculino", "Femenino"])
        self.customer_gender_combo.setStyleSheet(style_combo)
        details_layout.addWidget(self.customer_gender_combo, 1, 1)
        
        layout.addWidget(details_container)
        
        # Email (Opcional)
        email_label = QLabel("Correo electrÃ³nico (Opcional):")
        email_label.setStyleSheet(style_label)
        layout.addWidget(email_label)
        
        self.customer_email_entry = QLineEdit()
        self.customer_email_entry.setPlaceholderText("correo@ejemplo.com")
        self.customer_email_entry.setStyleSheet(style_input)
        layout.addWidget(self.customer_email_entry)
        
        # TelÃ©fono (Opcional)
        phone_label = QLabel("TelÃ©fono (Opcional):")
        phone_label.setStyleSheet(style_label)
        layout.addWidget(phone_label)
        
        self.customer_phone_entry = QLineEdit()
        self.customer_phone_entry.setPlaceholderText("NÃºmero de celular o telÃ©fono")
        self.customer_phone_entry.setStyleSheet(style_input)
        layout.addWidget(self.customer_phone_entry)


        # Etiquetas del cliente
        tags_label = QLabel("Etiquetas:")
        tags_label.setStyleSheet(style_label)
        layout.addWidget(tags_label)

        tags_row = QWidget()
        tags_row_layout = QHBoxLayout(tags_row)
        tags_row_layout.setContentsMargins(0, 0, 0, 0)
        tags_row_layout.setSpacing(8)

        self.customer_tags_entry = QLineEdit()
        self.customer_tags_entry.setReadOnly(True)
        self.customer_tags_entry.setPlaceholderText("Sin etiquetas")
        self.customer_tags_entry.setStyleSheet(style_input)
        tags_row_layout.addWidget(self.customer_tags_entry, 1)

        btn_select_tags = QPushButton("Seleccionar")
        btn_select_tags.setFixedWidth(100)
        btn_select_tags.clicked.connect(self.open_tags_selector)
        tags_row_layout.addWidget(btn_select_tags)

        btn_manage_tags = QPushButton("Gestionar")
        btn_manage_tags.setFixedWidth(100)
        btn_manage_tags.clicked.connect(self.open_tags_manager)
        tags_row_layout.addWidget(btn_manage_tags)

        layout.addWidget(tags_row)

        self._load_available_tags(select_default=True)
        
        layout.addSpacing(10)
        
        # Botones
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(style_btn_cancel)
        button_layout.addWidget(btn_cancel)
        
        self.save_button = QPushButton("Guardar")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save_customer)
        self.save_button.setStyleSheet(style_btn_save)
        button_layout.addWidget(self.save_button)
        
        layout.addWidget(button_container)
        
    def search_customer_by_dni(self):
        raw_dni = self.nuevo_dni_entry.text().strip()
        if not raw_dni:
            QMessageBox.warning(self, "Advertencia", "Por favor, ingresa un DNI antes de buscar.")
            return
        
        # Mostrar loader y limpiar el campo
        self.customer_name_entry.clear()
        self.name_loader.show()
        self.name_loader.start_loading()
        
        # Desactivar el botÃ³n durante la bÃºsqueda
        search_button = None
        for child in self.findChildren(QPushButton):
            if child.text() == "Buscar":
                search_button = child
                child.setEnabled(False)
                break
        
        # Crear y conectar el worker
        self.dni_search_worker = DNISearchWorker(raw_dni)
        self.dni_search_worker.search_completed.connect(
            lambda name, birth_date: self.on_search_completed(name, birth_date, search_button)
        )
        self.dni_search_worker.search_failed.connect(
            lambda error_msg: self.on_search_failed(error_msg, search_button)
        )
        self.dni_search_worker.start()

    def open_name_search_modal(self):
        """Permite buscar DNI si el usuario solo conoce nombres/apellidos."""
        dialog = NameSearchDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        selected = dialog.selected()
        if not isinstance(selected, dict):
            return

        dni = str(selected.get("dni", "") or "").strip()
        nombres = str(selected.get("nombres", "") or "").strip()
        ap_pat = str(selected.get("ap_pat", "") or "").strip()
        ap_mat = str(selected.get("ap_mat", "") or "").strip()

        full_name = f"{nombres} {ap_pat} {ap_mat}".strip()
        if dni:
            self.nuevo_dni_entry.setText(dni)
        if full_name:
            self.customer_name_entry.setText(full_name)
            try:
                self.auto_detect_gender(full_name)
            except Exception:
                pass
            try:
                self.name_loader.show_success()
            except Exception:
                pass
    
    def on_search_completed(self, full_name, birth_date, search_button):
        """Maneja el resultado exitoso de la bÃºsqueda"""
        if full_name:
            self.customer_name_entry.setText(full_name)
            self.auto_detect_gender(full_name)
            
            if birth_date:
                try:
                    birth_qdate = QDate.fromString(birth_date, "yyyy-MM-dd")
                    self.customer_birth_date_entry.setDate(birth_qdate)
                except Exception:
                    self.customer_birth_date_entry.setDate(QDate.currentDate())
            else:
                self.customer_birth_date_entry.setDate(QDate.currentDate())
            
            # Mostrar checkmark de Ã©xito
            self.name_loader.show_success()
        else:
            self.customer_name_entry.setText("")
            # Mostrar error
            self.name_loader.show_error()
            QMessageBox.information(self, "Sin resultados", "No se encontrÃ³ informaciÃ³n para ese DNI.")
        
        if search_button:
            search_button.setEnabled(True)
    
    def on_search_failed(self, error_msg, search_button):
        """Maneja el error de la bÃºsqueda"""
        self.customer_name_entry.setText("")
        self.name_loader.show_error()
        QMessageBox.warning(self, "Error", error_msg)
        if search_button:
            search_button.setEnabled(True)
    
    def auto_detect_gender(self, nombre):
        """Detecta automÃ¡ticamente el gÃ©nero basÃ¡ndose en el primer nombre"""
        if nombre:
            # Obtener el primer nombre
            palabras = nombre.strip().split()
            if palabras:
                primer_nombre = palabras[0].lower()
                
                # Primero verificar si estÃ¡ en las reglas definidas
                if primer_nombre in NOMBRE_GENERO_RULES:
                    genero = NOMBRE_GENERO_RULES[primer_nombre]
                    self.customer_gender_combo.setCurrentText(genero)
                else:
                    # Si no estÃ¡ en las reglas, usar la regla de la Ãºltima letra
                    ultima_letra = primer_nombre[-1].lower()
                    if ultima_letra == 'a':
                        self.customer_gender_combo.setCurrentText("Femenino")
                    elif ultima_letra == 'o':
                        self.customer_gender_combo.setCurrentText("Masculino")
    
    def on_name_changed(self, nombre):
        """Se ejecuta mientras se escribe el nombre para actualizar el gÃ©nero automÃ¡ticamente"""
        self.auto_detect_gender(nombre)
            
    def _refresh_tags_display(self):
        txt = ", ".join(self.selected_tags) if self.selected_tags else "Sin etiquetas"
        self.customer_tags_entry.setText(txt)

    def _load_available_tags(self, select_default=False):
        tags = cargar_etiquetas_clientes(self.username)
        self.available_tags = list(tags)

        seleccion_actual = {str(t).strip().casefold() for t in self.selected_tags}
        self.selected_tags = [t for t in self.available_tags if t.casefold() in seleccion_actual]

        if select_default and not self.selected_tags and self.available_tags:
            default_tag = next((t for t in self.available_tags if t.casefold() == "falta pagar"), self.available_tags[0])
            self.selected_tags = [default_tag]

        self._refresh_tags_display()

    def open_tags_selector(self):
        self._load_available_tags(select_default=False)
        dialog = CustomerTagSelectionDialog(self.available_tags, self.selected_tags, self)
        if dialog.exec_() == QDialog.Accepted:
            self.selected_tags = dialog.selected_tags()
            self._refresh_tags_display()

    def open_tags_manager(self):
        dialog = CustomerTagManagerDialog(self.username, self)
        dialog.tags_updated.connect(lambda _tags: self._load_available_tags(select_default=False))
        dialog.exec_()
        self._load_available_tags(select_default=False)

    def save_customer(self):
        dni = self.nuevo_dni_entry.text().strip()
        nombre = self.customer_name_entry.text().strip()
        birth_date = self.customer_birth_date_entry.date().toString("yyyy-MM-dd")
        genero = self.customer_gender_combo.currentText()
        hoy = datetime.datetime.now()

        if not dni or not nombre:
            QMessageBox.warning(self, "Advertencia", "Por favor, completa todos los campos obligatorios.")
            return

        # Calcular edad
        try:
            birth_dt = datetime.datetime.strptime(birth_date, "%Y-%m-%d")
            edad = hoy.year - birth_dt.year - ((hoy.month, hoy.day) < (birth_dt.month, birth_dt.day))
        except Exception:
            edad = ""

        clientes_visibles = cargar_clientes_dashboard(self.parent_app.username, allow_remote_restore=False)
        clientes = cargar_clientes_editable(self.parent_app.username)

        # Validar duplicados
        if any(str(cliente.get("dni", "")).strip() == dni for cliente in clientes_visibles):
            QMessageBox.warning(self, "Duplicado", f"Ya existe un cliente con el DNI {dni}.")
            return

        etiquetas = [str(t).strip() for t in self.selected_tags if str(t).strip()]
        if not etiquetas:
            defaults = cargar_etiquetas_clientes(self.username)
            fallback = next((t for t in defaults if str(t).strip().casefold() == "falta pagar"), None)
            etiquetas = [fallback] if fallback else []

        nuevo_cliente = {
            "dni": dni,
            "nombre": nombre,
            "fecha_nacimiento": birth_date,
            "edad": edad,
            "genero": genero,
            "fecha_registro": hoy.strftime("%d/%m/%Y"),
            "etiquetas": etiquetas,
        }
        
        clientes.append(nuevo_cliente)

        branch_code_for_sync = ""
        try:
            main_app = getattr(self.parent_app, "parent_app", None)
            if main_app is not None and hasattr(main_app, "es_dispositivo_madre"):
                if bool(main_app.es_dispositivo_madre()):
                    branch_code_for_sync = str(getattr(main_app, "selected_branch_code", "") or "").strip().upper()
                    if not branch_code_for_sync:
                        branch_code_for_sync = "__GLOBAL__"
        except Exception:
            branch_code_for_sync = ""

        # ðŸ’¾ Guardar en thread separado para no bloquear UI
        self.save_worker = CustomerSaveWorker(self.parent_app.username, clientes, branch_code=branch_code_for_sync)
        self.save_worker.save_finished.connect(self._on_save_finished)
        self.save_worker.start()
        
        # Deshabilitar botÃ³n y mostrar mensaje
        self.save_button.setEnabled(False)
        self.save_button.setText("Guardando...")
    
    def _on_save_finished(self, success, mensaje):
        """Slot que se ejecuta cuando termina de guardar."""
        if self.save_button:
            self.save_button.setEnabled(True)
            self.save_button.setText("Guardar")
        
        if success:
            # Limpiar el cache global para que se refresque el diÃ¡logo de selecciÃ³n
            try:
                from utils.data_cache_manager import get_global_cache
                cache = get_global_cache()
                cache.clear_data_type(self.username, 'clientes')
            except Exception:
                pass
            QMessageBox.information(self, "Ã‰xito", mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", mensaje)


class CustomersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.clientes_filtrados = []
        self.filter_active = False
        self.streamer_thread = None  # Thread para streaming de clientes
        self.refresh_worker = None  # Worker para auto-refresh
        self.all_clientes = []  # Cache de todos los clientes
        self._customers_loading = False
        self._customers_loader_active = False
        self.customers_content_stack = None
        self.customers_loading_page = None
        self.customers_loading_status = None
        self.customers_loading_subtitle = None
        self._table_render_timer = None
        self._table_render_rows = []
        self._table_render_index = 0
        self._table_render_batch_size = 8
        self._stream_table_preview_started = False
        self._filter_debounce_timer = QTimer(self)
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.timeout.connect(self.apply_filters)
        self._customer_search_cache = {}
        self._add_to_patient_icon = None
        
        # PaginaciÃ³n
        self.current_page = 0
        self.items_per_page = 100
        
        self.setup_ui()
        self._add_to_patient_icon = self.create_add_person_icon_small()
        # Cargar clientes con streaming cuando se inicializa
        QTimer.singleShot(100, self.load_customers_streaming)
        
        # ðŸ”„ Iniciar worker de auto-refresh en thread separado
        QTimer.singleShot(500, self._start_refresh_worker)

    def apply_filters(self):
        search_text = self.search_box.text().strip().lower()
        self.filter_active = bool(search_text)
        
        # Usar clientes cacheados (cargados via streaming)
        if self.all_clientes:
            clientes = self.all_clientes
        elif self._customers_loading:
            clientes = []
        else:
            clientes = cargar_clientes_dashboard(self.username, allow_remote_restore=False)
        
        if not self.filter_active:
            self.clientes_filtrados = []
        else:
            # Filtra por texto de busqueda en nombre, DNI o etiquetas.
            # Soporta etiquetas en lista (nuevo) o string (datos antiguos).
            self.clientes_filtrados = []
            for cliente in clientes:
                searchable_text = self._get_customer_searchable_text(cliente)
                if search_text in searchable_text:
                    self.clientes_filtrados.append(cliente)
        
        # Resetear a pagina 0 cuando se filtra
        self.current_page = 0
        
        self.update_customers_table()
        self.update_stats()

    def _schedule_apply_filters(self, _text=""):
        """Debounce del buscador para no repintar la tabla en cada tecla."""
        self._filter_debounce_timer.start(180)

    def _get_customer_searchable_text(self, cliente):
        """Devuelve un texto cacheado para filtrar rapido por nombre, dni y etiquetas."""
        if not isinstance(cliente, dict):
            return ""

        cache_key = (
            str(cliente.get('dni', '') or '').strip().lower(),
            str(cliente.get('nombre', '') or '').strip().lower(),
            json.dumps(cliente.get('etiquetas', []), ensure_ascii=False, sort_keys=True, default=str),
        )

        cached = self._customer_search_cache.get(cache_key)
        if cached is not None:
            return cached

        raw_tags = cliente.get('etiquetas', [])
        if isinstance(raw_tags, list):
            tags_text = ', '.join(str(t).strip().lower() for t in raw_tags if str(t).strip())
        elif isinstance(raw_tags, str):
            tags_text = raw_tags.lower()
        else:
            tags_text = ''

        searchable_text = " ".join(
            [
                str(cliente.get('nombre', '') or '').lower(),
                str(cliente.get('dni', '') or '').lower(),
                tags_text,
            ]
        ).strip()
        self._customer_search_cache[cache_key] = searchable_text
        return searchable_text

    def update_stats(self):
        """Actualiza los widgets de estadÃ­sticas con datos en tiempo real."""
        if self.all_clientes:
            clientes = self.all_clientes
        elif self._customers_loading:
            clientes = []
        else:
            clientes = cargar_clientes_dashboard(self.username, allow_remote_restore=False)
        total_clientes = len(clientes)
        clientes_hoy = len([c for c in clientes if c.get('fecha_registro') == datetime.datetime.now().strftime("%d/%m/%Y")])
        
        pacientes = cargar_pacientes(self.username)
        total_pacientes = len(pacientes)
        
        conversion_rate = f"{(total_pacientes/total_clientes*100):.1f}%" if total_clientes > 0 else "0%"
        
        # Actualizar los labels de los widgets
        if hasattr(self, 'stat_clientes_label'):
            self.stat_clientes_label.setText(str(total_clientes))
        if hasattr(self, 'stat_hoy_label'):
            self.stat_hoy_label.setText(str(clientes_hoy))
        if hasattr(self, 'stat_pacientes_label'):
            self.stat_pacientes_label.setText(str(total_pacientes))
        if hasattr(self, 'stat_conversion_label'):
            self.stat_conversion_label.setText(conversion_rate)

    def _set_stats_loading_state(self, is_loading: bool):
        value = "..." if is_loading else "0"
        if hasattr(self, 'stat_clientes_label'):
            self.stat_clientes_label.setText(value)
        if hasattr(self, 'stat_hoy_label'):
            self.stat_hoy_label.setText(value)
        if hasattr(self, 'stat_pacientes_label'):
            self.stat_pacientes_label.setText(value)
        if hasattr(self, 'stat_conversion_label'):
            self.stat_conversion_label.setText("..." if is_loading else "0%")

    def _build_customers_loading_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.customers_loading_subtitle = None
        self.customers_loading_status = None
        self.customers_loading_skeleton = CustomersPageSkeleton(page)
        layout.addWidget(self.customers_loading_skeleton)
        return page

    def _show_internal_customers_loader(self, subtitle: str = ""):
        self._customers_loader_active = True
        self._set_stats_loading_state(True)
        if hasattr(self, "customers_loading_skeleton") and self.customers_loading_skeleton is not None:
            self.customers_loading_skeleton.set_loading_text(
                str(subtitle or "Preparando lista y estadisticas en segundo plano..."),
                "Leyendo clientes y pacientes..."
            )
        if self.customers_loading_subtitle is not None and subtitle:
            self.customers_loading_subtitle.setText(str(subtitle))
        if self.customers_loading_status is not None:
            self.customers_loading_status.setText("Leyendo clientes y pacientes...")
        if self.customers_content_stack is not None and self.customers_loading_page is not None:
            self.customers_content_stack.setCurrentWidget(self.customers_loading_page)

    def _hide_internal_customers_loader(self):
        self._customers_loader_active = False
        if self.customers_content_stack is not None and hasattr(self, "_customers_main_scroll"):
            self.customers_content_stack.setCurrentWidget(self._customers_main_scroll)

    def setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Contenedor superior para tÃ­tulo, botÃ³n y estadÃ­sticas
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setSpacing(20)
        
        # Contenedor para tÃ­tulo y botÃ³n en la misma lÃ­nea
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # TÃ­tulo con nuevo diseÃ±o
        title = QLabel("Gestion de Clientes")
        title.setObjectName("pageTitle")
        title.setStyleSheet("""
            QLabel {
                font-size: 25px;
                color: #212121;
                padding: 0px;
                font-weight: normal;
                background-color: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title, 1)
        
        # Barra de bÃºsqueda en el centro
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar por nombre, DNI o etiqueta...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #2a2a2a;
                background-color: white;
            }
        """)
        self.search_box.textChanged.connect(self._schedule_apply_filters)
        header_layout.addWidget(self.search_box, 4)
        
        # Agregar espacio entre bÃºsqueda y botÃ³n
        header_layout.addStretch()
        
        # BotÃ³n para agregar nuevo cliente
        btn_add_new = QPushButton("Agregar Cliente Nuevo")
        btn_add_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_new.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        btn_add_new.clicked.connect(self.show_new_customer_dialog)
        # ðŸ›¡ï¸ VERIFICAR PERMISO: Deshabilitar botÃ³n si no tiene 'crear' en clientes
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('clientes', 'crear'):
                btn_add_new.setEnabled(False)
                btn_add_new.setToolTip("No tienes permiso para agregar clientes")
        header_layout.addWidget(btn_add_new, 1)


        # Boton para gestionar etiquetas
        btn_manage_tags = QPushButton("Etiquetas")
        btn_manage_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manage_tags.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #1a1a1a;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 10px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        """)
        btn_manage_tags.clicked.connect(self.show_manage_tags_dialog)
        header_layout.addWidget(btn_manage_tags)
        
        # Agregar el contenedor de encabezado al layout principal
        top_layout.addWidget(header_container)
        
        # Panel de estadÃ­sticas
        stats_container = QWidget()
        stats_container.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                border: 1px solid #E6EAF0;
                border-radius: 18px;
            }
        """)
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(18, 12, 18, 12)
        stats_layout.setSpacing(0)

        # FunciÃ³n para crear un widget de estadÃ­stica
        def create_stat_widget(title, value, icon_color):
            widget = QWidget()
            widget.setMinimumHeight(88)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            widget.setStyleSheet("""
                QWidget {
                    background: transparent;
                    border: none;
                }
            """)

            layout = QVBoxLayout(widget)
            layout.setContentsMargins(14, 10, 14, 10)
            layout.setSpacing(6)

            header = QWidget()
            header.setStyleSheet("background: transparent; border: none;")
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(8)

            icon = QLabel()
            icon.setFixedSize(10, 10)
            icon.setStyleSheet(f"""
                background-color: {icon_color};
                border-radius: 5px;
                border: none;
            """)
            header_layout.addWidget(icon, alignment=Qt.AlignVCenter)

            title_label = QLabel(title)
            title_label.setStyleSheet("""
                color: #6B7280;
                font-size: 11px;
                font-weight: 600;
                border: none;
                background: transparent;
            """)
            header_layout.addWidget(title_label, alignment=Qt.AlignVCenter)
            header_layout.addStretch()

            value_label = QLabel(str(value))
            value_label.setStyleSheet("""
                font-size: 26px;
                font-weight: 700;
                color: #111827;
                border: none;
                background: transparent;
            """)

            layout.addWidget(header)
            layout.addWidget(value_label)
            layout.addStretch()
            return widget, value_label

        def create_stat_divider():
            divider = QWidget()
            divider.setFixedWidth(1)
            divider.setMinimumHeight(56)
            divider.setStyleSheet("""
                QWidget {
                    background: #E8EDF3;
                    border: none;
                }
            """)
            return divider
        
        # Inicializar estadisticas en estado ligero; se rellenan cuando termina la carga.
        total_clientes = "..."
        clientes_hoy = "..."
        total_pacientes = "..."
        conversion_rate = "..."
        
        # Agregar widgets de estadÃ­sticas y guardar referencias a los labels de valor
        stat_clientes, self.stat_clientes_label = create_stat_widget("Total Clientes", total_clientes, "#2196F3")
        stat_hoy, self.stat_hoy_label = create_stat_widget("Nuevos Hoy", clientes_hoy, "#4CAF50")
        stat_pacientes, self.stat_pacientes_label = create_stat_widget("Total Pacientes", total_pacientes, "#FFC107")
        stat_conversion, self.stat_conversion_label = create_stat_widget("Tasa ConversiÃ³n", conversion_rate, "#9C27B0")
        
        stats_layout.addWidget(stat_clientes)
        stats_layout.addWidget(create_stat_divider())
        stats_layout.addWidget(stat_hoy)
        stats_layout.addWidget(create_stat_divider())
        stats_layout.addWidget(stat_pacientes)
        stats_layout.addWidget(create_stat_divider())
        stats_layout.addWidget(stat_conversion)
        
        top_layout.addWidget(stats_container)
        
        main_layout.addWidget(top_container)
        
        # Container principal con scroll
        main_scroll = QtWidgets.QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._customers_main_scroll = main_scroll
        
        # Container para la tabla
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(0)
        main_scroll.setWidget(content_container)
        
        # Panel para la tabla
        right_panel = QWidget()
        right_panel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Botones de acciÃ³n en la parte superior
        btn_layout_top = QHBoxLayout()
        
        # BotÃ³n "Convertir Todos"
        self.btn_convert_all = QPushButton("Convertir Todos")
        self.btn_convert_all.setFixedWidth(120)
        self.btn_convert_all.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.btn_convert_all.clicked.connect(self.convertir_todos_a_pacientes)
        
        btn_layout_top.addWidget(self.btn_convert_all)
        btn_layout_top.addStretch()
        right_layout.addLayout(btn_layout_top)
        
        # Container para la tabla con scroll propio
        table_scroll = QtWidgets.QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Tabla de clientes con nuevo diseÃ±o
        self.customers_table = QTableWidget()
        self.customers_table.setObjectName("customersTable")
        self.customers_table.setColumnCount(6)
        self.customers_table.setHorizontalHeaderLabels(["DNI", "Nombre", "Edad", "Etiquetas", "Fecha Registro", "Acciones"])
        
        # Estilo para la tabla
        self.customers_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                gridline-color: #F5F5F5;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F5F5F5;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #212121;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 12px;
                border: none;
                font-weight: bold;
                color: #616161;
            }
            QTableWidget::item:hover {
                background-color: #F5F5F5;
            }
        """)
        
        # Configurar anchos de columna
        self.customers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # DNI
        self.customers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre
        self.customers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Edad
        self.customers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Etiquetas
        self.customers_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Fecha
        self.customers_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Acciones
        
        # Establecer anchos especÃ­ficos
        self.customers_table.setColumnWidth(0, 100)  # DNI
        self.customers_table.setColumnWidth(2, 60)   # Edad
        self.customers_table.setColumnWidth(3, 180)  # Etiquetas
        self.customers_table.setColumnWidth(4, 120)  # Fecha
        self.customers_table.setColumnWidth(5, 120)  # Acciones
        
        self.customers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)  # Seleccionar filas completas
        self.customers_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)  # MÃºltiple selecciÃ³n
        self.customers_table.verticalHeader().setVisible(True)  # Mostrar header vertical con checkboxes
        self.customers_table.setWordWrap(True)
        self.customers_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.customers_table.setAlternatingRowColors(True)
        self.customers_table.setShowGrid(True)
        
        # Conectar doble clic para abrir detalles
        self.customers_table.doubleClicked.connect(self.abrir_detalles_cliente_doble_clic)
        # Click simple en columna "Etiquetas" para editar etiquetas del cliente
        self.customers_table.cellClicked.connect(self.on_customer_cell_clicked)
        
        # Ajustar altura de las filas
        self.customers_table.verticalHeader().setDefaultSectionSize(50)
        
        # Crear panel de paginaciÃ³n
        pagination_container = QWidget()
        pagination_layout = QHBoxLayout(pagination_container)
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        pagination_layout.setSpacing(10)
        
        # BotÃ³n Anterior
        self.btn_prev_page = QPushButton("â† Anterior")
        self.btn_prev_page.setFixedHeight(35)
        self.btn_prev_page.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #1a1a1a;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #efefef;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999999;
                border: 1px solid #e0e0e0;
            }
        """)
        self.btn_prev_page.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.btn_prev_page)
        
        # Label de pÃ¡gina actual
        self.pagination_label = QLabel("PÃ¡gina 1")
        self.pagination_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pagination_label.setStyleSheet("color: #616161; font-weight: 600;")
        pagination_layout.addWidget(self.pagination_label)
        
        # BotÃ³n Siguiente
        self.btn_next_page = QPushButton("Siguiente â†’")
        self.btn_next_page.setFixedHeight(35)
        self.btn_next_page.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #1a1a1a;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #efefef;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999999;
                border: 1px solid #e0e0e0;
            }
        """)
        self.btn_next_page.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.btn_next_page)
        
        table_scroll.setWidget(self.customers_table)
        right_layout.addWidget(table_scroll)
        right_layout.addWidget(pagination_container)
        
        self.pagination_label.setText("Cargando clientes...")
        self.btn_prev_page.setEnabled(False)
        self.btn_next_page.setEnabled(False)
        
        # AÃ±adir el panel al contenedor
        content_layout.addWidget(right_panel)
        
        # Stack con loader interno + contenido real
        self.customers_content_stack = QtWidgets.QStackedWidget()
        self.customers_loading_page = self._build_customers_loading_page()
        self.customers_content_stack.addWidget(self.customers_loading_page)
        self.customers_content_stack.addWidget(main_scroll)
        self.customers_content_stack.setCurrentWidget(self.customers_loading_page)

        # AÃ±adir stack principal al layout
        main_layout.addWidget(self.customers_content_stack)

    def _procesar_edad_para_tabla(self, edad_valor):
        """Procesa el valor de edad para mostrar correctamente en tabla: si es fecha, calcula aÃ±os."""
        try:
            if not edad_valor:
                return ''
            
            # Si ya es un nÃºmero, devolverlo
            if isinstance(edad_valor, (int, float)):
                return str(int(edad_valor))
            
            edad_str = str(edad_valor).strip()
            
            # Intentar convertirlo a int
            try:
                return str(int(float(edad_str)))
            except ValueError:
                pass
            
            # Si parece una fecha, calcular la edad
            if any(sep in edad_str for sep in ['-', '/', ' ']):
                fecha_obj = self._parse_fecha_tabla(edad_str)
                if fecha_obj:
                    hoy = datetime.datetime.now()
                    edad = hoy.year - fecha_obj.year - ((hoy.month, hoy.day) < (fecha_obj.month, fecha_obj.day))
                    return str(edad)
            
            return edad_str
        except Exception as e:
            print(f"Error al procesar edad: {e}")
            return str(edad_valor)
    
    def _parse_fecha_tabla(self, fecha_str):
        """Intenta parsear una fecha en mÃºltiples formatos."""
        try:
            # Eliminar la hora si estÃ¡ incluida
            if ' ' in fecha_str:
                fecha_str = fecha_str.split(' ')[0]
            
            # Formatos a intentar
            formatos = [
                '%Y-%m-%d',  # 1948-10-18
                '%d/%m/%Y',  # 18/10/1948
                '%d-%m-%Y',  # 18-10-1948
                '%m/%d/%Y',  # 10/18/1948
                '%Y/%m/%d',  # 1948/10/18
            ]
            
            for formato in formatos:
                try:
                    return datetime.datetime.strptime(fecha_str, formato)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None

    def _render_cliente_tags(self, cliente):
        etiquetas = cliente.get('etiquetas', [])
        if isinstance(etiquetas, str):
            etiquetas = [etiquetas]
        if not isinstance(etiquetas, list):
            return "Sin etiqueta"

        etiquetas_limpias = []
        vistos = set()
        for tag in etiquetas:
            txt = str(tag or "").strip()
            if not txt:
                continue
            key = txt.casefold()
            if key in vistos:
                continue
            vistos.add(key)
            etiquetas_limpias.append(txt)

        return ", ".join(etiquetas_limpias) if etiquetas_limpias else "Sin etiqueta"

    def _normalizar_etiquetas(self, tags):
        resultado = []
        vistos = set()
        for tag in tags or []:
            txt = str(tag or "").strip()
            if not txt:
                continue
            key = txt.casefold()
            if key in vistos:
                continue
            vistos.add(key)
            resultado.append(txt)
        return resultado

    def on_customer_cell_clicked(self, row, column):
        # Columna 3 = Etiquetas
        if column != 3:
            return

        item_dni = self.customers_table.item(row, 0)
        if item_dni is None:
            return

        dni = item_dni.text().strip()
        if not dni:
            return

        self.edit_customer_tags(dni)

    def edit_customer_tags(self, dni):
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('clientes', 'editar'):
                QMessageBox.warning(self, "Permiso Denegado", "No tienes permiso para editar etiquetas de clientes.")
                return

        clientes = self.all_clientes if self.all_clientes else cargar_clientes(self.username)
        idx_cliente = -1
        for idx, cliente in enumerate(clientes):
            if str(cliente.get('dni', '')).strip() == dni:
                idx_cliente = idx
                break

        if idx_cliente < 0:
            QMessageBox.warning(self, "Cliente no encontrado", "No se encontro el cliente seleccionado.")
            return

        cliente = clientes[idx_cliente]
        tags_disponibles = cargar_etiquetas_clientes(self.username)
        tags_actuales = cliente.get('etiquetas', [])
        if isinstance(tags_actuales, str):
            tags_actuales = [p.strip() for p in tags_actuales.split(',') if p.strip()]
        elif not isinstance(tags_actuales, list):
            tags_actuales = []

        dialog = CustomerTagSelectionDialog(tags_disponibles, tags_actuales, self)
        nombre_cliente = str(cliente.get('nombre', 'Cliente') or 'Cliente').strip()
        dialog.setWindowTitle(f"Etiquetas - {nombre_cliente}")
        if dialog.exec_() != QDialog.Accepted:
            return

        cliente['etiquetas'] = self._normalizar_etiquetas(dialog.selected_tags())
        clientes[idx_cliente] = cliente
        guardar_clientes(self.username, clientes)

        self.all_clientes = clientes
        self.apply_filters()

    def update_customers_table(self):
        """Actualiza la tabla de clientes con paginaciÃ³n (100 por pÃ¡gina)."""
        self._cancel_table_render()
        self.customers_table.setRowCount(0)
        self.customers_table.clearSpans()
        
        # Usar cache si estÃ¡ disponible, sino cargar y actualizar cache
        if not self.all_clientes:
            if self._customers_loading:
                self._update_pagination_controls(0)
                return
            # Recargar desde archivo
            clientes = cargar_clientes_dashboard(self.username, allow_remote_restore=False)
            self.all_clientes = clientes
        else:
            clientes = self.clientes_filtrados if self.filter_active else self.all_clientes
        
        # Ordenar clientes del mÃ¡s reciente al mÃ¡s antiguo
        try:
            clientes_ordenados = sorted(clientes, key=lambda x: datetime.datetime.strptime(x.get('fecha_registro', '01/01/2000'), "%d/%m/%Y"), reverse=True)
        except Exception:
            clientes_ordenados = clientes
        
        # Calcular paginaciÃ³n
        total_clientes = len(clientes_ordenados)
        total_pages = (total_clientes + self.items_per_page - 1) // self.items_per_page
        
        # Validar pÃ¡gina actual
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)
        
        # Calcular Ã­ndices para la pÃ¡gina actual
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        clientes_pagina = clientes_ordenados[start_idx:end_idx]
        self._update_pagination_controls(total_pages)
        self._schedule_table_render(clientes_pagina)

    def _schedule_table_render(self, clientes_pagina):
        self._table_render_rows = list(clientes_pagina)
        self._table_render_index = 0
        if not self._table_render_rows:
            return

        self.customers_table.setRowCount(len(self._table_render_rows))

        self._table_render_timer = QTimer(self)
        self._table_render_timer.setSingleShot(False)
        self._table_render_timer.timeout.connect(self._render_table_batch)
        self._table_render_timer.start(0)

    def _cancel_table_render(self):
        timer = getattr(self, "_table_render_timer", None)
        self._table_render_timer = None
        self._table_render_rows = []
        self._table_render_index = 0
        try:
            if timer is not None:
                timer.stop()
                timer.deleteLater()
        except Exception:
            pass

    def _render_table_batch(self):
        if not self._table_render_rows:
            self._cancel_table_render()
            return

        end_index = min(
            self._table_render_index + self._table_render_batch_size,
            len(self._table_render_rows),
        )

        self.customers_table.setUpdatesEnabled(False)
        try:
            for row_index in range(self._table_render_index, end_index):
                cliente = self._table_render_rows[row_index]
                self._insert_customer_row(row_index, cliente)
        finally:
            self.customers_table.setUpdatesEnabled(True)

        self._table_render_index = end_index
        if self._table_render_index >= len(self._table_render_rows):
            self._cancel_table_render()

    def _insert_customer_row(self, row_index, cliente):
        dni_item = QtWidgets.QTableWidgetItem(cliente.get('dni', ''))
        dni_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.customers_table.setItem(row_index, 0, dni_item)

        nombre_item = QtWidgets.QTableWidgetItem(cliente.get('nombre', ''))
        self.customers_table.setItem(row_index, 1, nombre_item)

        edad_procesada = self._procesar_edad_para_tabla(cliente.get('edad', ''))
        edad_item = QtWidgets.QTableWidgetItem(edad_procesada)
        edad_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.customers_table.setItem(row_index, 2, edad_item)

        tags_item = QtWidgets.QTableWidgetItem(self._render_cliente_tags(cliente))
        self.customers_table.setItem(row_index, 3, tags_item)

        fecha_item = QtWidgets.QTableWidgetItem(cliente.get('fecha_registro', ''))
        fecha_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.customers_table.setItem(row_index, 4, fecha_item)

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(5, 2, 5, 2)

        btn_add_to_patients = QPushButton()
        btn_add_to_patients.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_to_patients.setFixedSize(36, 36)
        btn_add_to_patients.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(41, 134, 89, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(41, 134, 89, 0.25);
            }
        """)

        btn_add_to_patients.setIcon(self._add_to_patient_icon or self.create_add_person_icon_small())
        btn_add_to_patients.setIconSize(QtCore.QSize(24, 24))
        btn_add_to_patients.setToolTip("Agregar como paciente")
        btn_add_to_patients.clicked.connect(lambda _, c=cliente: self.add_to_patients(c))
        action_layout.addWidget(btn_add_to_patients)

        self.customers_table.setCellWidget(row_index, 5, action_widget)

    def _update_pagination_controls(self, total_pages):
        """Actualiza los botones de paginaciÃ³n y el label."""
        # Validar pÃ¡gina actual
        if total_pages == 0:
            self.current_page = 0
            total_pages = 1
        elif self.current_page >= total_pages:
            self.current_page = total_pages - 1
        
        # Actualizar label
        self.pagination_label.setText(f"PÃ¡gina {self.current_page + 1} de {total_pages}")
        
        # Habilitar/deshabilitar botones
        self.btn_prev_page.setEnabled(self.current_page > 0)
        self.btn_next_page.setEnabled(self.current_page < total_pages - 1)

    def prev_page(self):
        """Ir a la pÃ¡gina anterior."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_customers_table()

    def next_page(self):
        """Ir a la siguiente pÃ¡gina."""
        # Calcular nÃºmero total de pÃ¡ginas
        clientes = self.clientes_filtrados if self.filter_active else self.all_clientes
        total_pages = (len(clientes) + self.items_per_page - 1) // self.items_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_customers_table()

    def show_manage_tags_dialog(self):
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('clientes', 'editar'):
                QMessageBox.warning(self, "Permiso Denegado", "No tienes permiso para gestionar etiquetas de clientes.")
                return

        dialog = CustomerTagManagerDialog(self.username, self)
        dialog.tags_updated.connect(lambda _tags: self.apply_filters())
        dialog.exec_()

    def show_new_customer_dialog(self):
        # ðŸ›¡ï¸ VERIFICAR PERMISO: Solo puede crear si tiene permiso 'crear' en clientes
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('clientes', 'crear'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para crear nuevos clientes."
                )
                return
        
        dialog = NewCustomerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Solo refrescar la vista actual sin recargar todos los clientes
            self.refresh_clientes()  # Actualizar tabla con nuevo cliente
    
    def refresh_clientes(self):
        """Actualiza la tabla de clientes sin hacer reinicio completo."""
        try:
            clientes = cargar_clientes_dashboard(self.username, allow_remote_restore=False)
            self.all_clientes = clientes
            self.current_page = 0
            self.update_customers_table()
            self.update_stats()
            print(f"âœ“ Tabla de clientes refrescada con {len(clientes)} clientes")
        except Exception as e:
            print(f"âŒ Error refrescando clientes: {e}")
    
    def convertir_todos_a_pacientes(self):
        """Convierte todos los clientes a pacientes de una vez."""
        try:
            todos_los_clientes = cargar_clientes(self.username)
            
            # Confirmar con el usuario
            reply = QMessageBox.question(
                self,
                "Confirmar ConversiÃ³n",
            f"¿Deseas convertir todos los {len(todos_los_clientes)} clientes a pacientes?\n\nLos que ya sean pacientes serán omitidos.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Crear diÃ¡logo con progreso mejorado
                progress_dialog = QDialog(self)
                progress_dialog.setWindowTitle("Convirtiendo Clientes")
                progress_dialog.setGeometry(200, 200, 550, 360)
                progress_dialog.setModal(True)
                progress_dialog.setStyleSheet("""
                    QDialog {
                        background-color: #f5f5f5;
                    }
                """)
                
                layout = QVBoxLayout()
                layout.setContentsMargins(20, 20, 20, 20)
                layout.setSpacing(15)
                
                # Etiqueta de progreso
                label_progress = QLabel("Iniciando conversiÃ³n...")
                label_progress.setStyleSheet("""
                    font-size: 13px;
                    font-weight: bold;
                    color: #333;
                """)
                layout.addWidget(label_progress)
                
                # Barra de progreso mejorada
                progress_bar = QtWidgets.QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(0)
                progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #ddd;
                        border-radius: 5px;
                        background-color: #fff;
                        height: 30px;
                    }
                    QProgressBar::chunk {
                        background-color: #4CAF50;
                        border-radius: 3px;
                    }
                """)
                layout.addWidget(progress_bar)
                
                # Label de contador
                label_count = QLabel(f"0 / {len(todos_los_clientes)} clientes")
                label_count.setStyleSheet("""
                    font-size: 11px;
                    color: #666;
                """)
                layout.addWidget(label_count)
                
                # Widget del loader animado
                loader_widget = self._create_animated_loader()
                layout.addWidget(loader_widget)
                
                # Layout para botones de control
                buttons_layout = QHBoxLayout()
                buttons_layout.setSpacing(10)
                
                btn_pause = QPushButton("Pausar")
                btn_pause.setFixedWidth(100)
                btn_pause.setStyleSheet("""
                    QPushButton {
                        background-color: #FFC107;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #FFB300;
                    }
                    QPushButton:pressed {
                        background-color: #FF9800;
                    }
                """)
                
                btn_cancel = QPushButton("Cancelar")
                btn_cancel.setFixedWidth(100)
                btn_cancel.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                    QPushButton:pressed {
                        background-color: #b71c1c;
                    }
                """)
                
                buttons_layout.addStretch()
                buttons_layout.addWidget(btn_pause)
                buttons_layout.addWidget(btn_cancel)
                layout.addLayout(buttons_layout)
                
                progress_dialog.setLayout(layout)
                
                # Thread para la conversiÃ³n
                from PyQt5.QtCore import QThread, pyqtSignal
                
                # Variables de control
                control_state = {'paused': False, 'cancelled': False}
                
                class ConversionWorker(QThread):
                    progress_update = pyqtSignal(int, int)  # actual, total
                    finished = pyqtSignal(int, int)  # convertidos, omitidos
                    error = pyqtSignal(str)
                    
                    def __init__(self, clientes, username):
                        super().__init__()
                        self.clientes = clientes
                        self.username = username
                    
                    def run(self):
                        try:
                            pacientes = cargar_pacientes(self.username)
                            convertidos = 0
                            omitidos = 0
                            
                            for idx, cliente in enumerate(self.clientes):
                                # Verificar si se cancelÃ³
                                if control_state['cancelled']:
                                    print("â›” ConversiÃ³n cancelada por el usuario")
                                    break
                                
                                # Verificar si estÃ¡ pausado
                                while control_state['paused']:
                                    self.msleep(100)
                                
                                # Emitir progreso
                                self.progress_update.emit(idx + 1, len(self.clientes))
                                
                                dni = cliente.get('dni', '').strip()
                                
                                # Permitir duplicados de DNI 00000000 (pacientes sin DNI identificado)
                                # Pero para otros DNIs, verificar que no existan duplicados
                                if dni != '00000000' and any(p.get('dni') == dni for p in pacientes):
                                    omitidos += 1
                                else:
                                    nuevo_paciente = {
                                        'dni': dni,
                                        'nombre': cliente.get('nombre', ''),
                                        'edad': cliente.get('edad', ''),
                                        'fecha_registro': datetime.datetime.now().strftime('%d/%m/%Y'),
                                        'email': cliente.get('email', ''),
                                        'telefono': cliente.get('telefono', '')
                                    }
                                    pacientes.append(nuevo_paciente)
                                    convertidos += 1
                                
                                # PequeÃ±o delay para que la UI se actualice
                                self.msleep(5)
                            
                            # Guardar todos de una vez si se convirtiÃ³ algo
                            if convertidos > 0:
                                guardar_pacientes(self.username, pacientes)
                            
                            self.finished.emit(convertidos, omitidos)
                        except Exception as e:
                            self.error.emit(str(e))
                
                # Crear worker
                worker = ConversionWorker(todos_los_clientes, self.username)
                
                # Timer para animar el loader
                loader_timer = QTimer()
                loader_frames = [
                    "â ‹", "â ™", "â ¹", "â ¸", "â ¼", "â ´", "â ¦", "â §", "â ‡", "â "
                ]
                loader_index = [0]
                
                def animate_loader():
                    if hasattr(loader_widget, 'findChild'):
                        loader_label = loader_widget.findChild(QLabel, "loader_animation")
                        if loader_label:
                            loader_label.setText(loader_frames[loader_index[0] % len(loader_frames)])
                            loader_index[0] += 1
                
                loader_timer.timeout.connect(animate_loader)
                loader_timer.start(100)
                
                def update_progress(actual, total):
                    porcentaje = int((actual / total) * 100)
                    progress_bar.setValue(porcentaje)
                    label_progress.setText(f"Convirtiendo clientes... {porcentaje}%")
                    label_count.setText(f"{actual} / {total} clientes")
                
                def on_pause_clicked():
                    if control_state['paused']:
                        control_state['paused'] = False
                        btn_pause.setText("Pausar")
                        btn_pause.setStyleSheet("""
                            QPushButton {
                                background-color: #FFC107;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                padding: 8px;
                                font-weight: bold;
                                font-size: 11px;
                            }
                            QPushButton:hover {
                                background-color: #FFB300;
                            }
                            QPushButton:pressed {
                                background-color: #FF9800;
                            }
                        """)
                        loader_timer.start()
                    else:
                        control_state['paused'] = True
                        btn_pause.setText("Reanudar")
                        btn_pause.setStyleSheet("""
                            QPushButton {
                                background-color: #4CAF50;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                padding: 8px;
                                font-weight: bold;
                                font-size: 11px;
                            }
                            QPushButton:hover {
                                background-color: #45a049;
                            }
                            QPushButton:pressed {
                                background-color: #3d8b40;
                            }
                        """)
                        loader_timer.stop()
                
                def on_cancel_clicked():
                    control_state['cancelled'] = True
                    btn_cancel.setEnabled(False)
                    btn_pause.setEnabled(False)
                
                def conversion_finished(convertidos, omitidos):
                    loader_timer.stop()
                    progress_dialog.accept()
                    
                    if control_state['cancelled']:
                        mensaje = f"â¸ï¸ ConversiÃ³n pausada\n\nâœ“ {convertidos} cliente(s) convertido(s)\n({omitidos} ya eran pacientes)"
                    else:
                        mensaje = f"âœ“ {convertidos} cliente(s) convertido(s) a paciente(s)"
                        if omitidos > 0:
                            mensaje += f"\n({omitidos} ya eran pacientes)"
                    
                    QMessageBox.information(self, "ConversiÃ³n Completada", mensaje)
                
                def conversion_error(error):
                    loader_timer.stop()
                    progress_dialog.accept()
                    QMessageBox.critical(self, "Error", f"Error durante la conversiÃ³n: {error}")
                
                # Conectar signals de botones
                btn_pause.clicked.connect(on_pause_clicked)
                btn_cancel.clicked.connect(on_cancel_clicked)
                
                # Conectar signals de worker
                worker.progress_update.connect(update_progress)
                worker.finished.connect(conversion_finished)
                worker.error.connect(conversion_error)
                
                # Iniciar worker
                worker.start()
                
                # Mostrar diÃ¡logo
                progress_dialog.exec_()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar clientes: {str(e)}")
    
    def _create_animated_loader(self):
        """Crea un widget con loader animado para mostrar progreso visual."""
        loader_widget = QWidget()
        loader_layout = QHBoxLayout()
        loader_layout.setContentsMargins(0, 10, 0, 10)
        loader_layout.setSpacing(10)
        
        # Loader de caracteres
        loader_label = QLabel("â ‹")
        loader_label.setObjectName("loader_animation")
        loader_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        """)
        loader_label.setAlignment(Qt.AlignCenter)
        loader_layout.addWidget(loader_label)
        
        # Texto "Procesando..."
        text_label = QLabel("Procesando...")
        text_label.setStyleSheet("""
            font-size: 12px;
            color: #666;
        """)
        loader_layout.addWidget(text_label)
        
        loader_layout.addStretch()
        loader_widget.setLayout(loader_layout)
        
        return loader_widget
    
    def _seleccionar_filas_paginas(self, paginas, clientes_por_pagina, convertir_a_pacientes=False, clientes_ordenados=None):
        """Selecciona todas las filas de las pÃ¡ginas especificadas y opcionalmente convierte a pacientes."""
        clientes_a_convertir = []
        
        # Recolectar clientes de las pÃ¡ginas seleccionadas
        if clientes_ordenados:
            for pagina in paginas:
                inicio = (pagina - 1) * clientes_por_pagina
                fin = min(pagina * clientes_por_pagina, len(clientes_ordenados))
                
                # Agregar clientes de esta pÃ¡gina
                for idx in range(inicio, fin):
                    if idx < len(clientes_ordenados):
                        clientes_a_convertir.append(clientes_ordenados[idx])
                
                # Seleccionar filas en la tabla (solo las que estÃ©n visibles)
                for row in range(inicio, min(fin, self.customers_table.rowCount())):
                    self.customers_table.selectRow(row)
        
        # Convertir a pacientes si se seleccionÃ³
        if convertir_a_pacientes and clientes_a_convertir:
            self._convertir_multiples_a_pacientes(clientes_a_convertir)
        else:
            print(f"âœ“ Seleccionadas filas de {len(paginas)} pÃ¡gina{'s' if len(paginas) > 1 else ''}")
    
    def _convertir_multiples_a_pacientes(self, clientes):
        """Convierte mÃºltiples clientes a pacientes, omitiendo los que ya existen."""
        try:
            pacientes = cargar_pacientes(self.username)
            
            convertidos = 0
            omitidos = 0
            
            for cliente in clientes:
                # Verificar que no exista ya
                existe = any(p.get('dni') == cliente.get('dni') for p in pacientes)
                
                if not existe:
                    # Crear paciente con datos del cliente
                    nuevo_paciente = {
                        'dni': cliente.get('dni', ''),
                        'nombre': cliente.get('nombre', ''),
                        'edad': cliente.get('edad', ''),
                        'fecha_registro': datetime.datetime.now().strftime('%d/%m/%Y'),
                        'email': cliente.get('email', ''),
                        'telefono': cliente.get('telefono', '')
                    }
                    pacientes.append(nuevo_paciente)
                    convertidos += 1
                else:
                    omitidos += 1
            
            if convertidos > 0:
                guardar_pacientes(self.username, pacientes)
            
            # Mensaje solo si se convirtieron algunos
            if convertidos > 0:
                mensaje = f"âœ“ {convertidos} cliente(s) convertido(s) a paciente(s)"
                if omitidos > 0:
                    mensaje += f"\n({omitidos} ya eran pacientes)"
                QMessageBox.information(self, "Ã‰xito", mensaje)
            elif omitidos > 0:
                # Si todos ya eran pacientes, no mostrar mensaje de error
                print(f"â„¹ï¸ {omitidos} cliente(s) ya existÃ­an como pacientes")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al convertir a pacientes: {str(e)}")
    
    def add_to_patients(self, cliente):
        # ðŸ›¡ï¸ VERIFICAR PERMISO: Requiere 'crear' en pacientes para convertir cliente a paciente
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('pacientes', 'crear'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para crear pacientes desde clientes."
                )
                return
        
        pacientes = cargar_pacientes(self.username)
        dni = cliente.get('dni', '00000000')
        nombre = cliente.get('nombre', 'Sin nombre')
        
        # Permitir duplicados de DNI 00000000 (pacientes sin DNI identificado)
        # Pero para otros DNIs, verificar que no existan duplicados
        if dni != '00000000' and any(p.get('dni') == dni for p in pacientes):
            QMessageBox.warning(self, "Advertencia", "Este cliente ya es un paciente. Puedes encontrarlo en 'Historial de Pacientes'.")
            return
        
        # Crear el nuevo paciente
        nuevo_paciente = {
            "dni": dni,
            "nombre": nombre,
            "fecha": cliente.get('fecha_registro', ''),
            "edad": cliente.get('edad', ''),
            "genero": cliente.get('genero', ''),
            "fecha_nacimiento": cliente.get('fecha_nacimiento', ''),
            "historial_graduaciones": []
        }
        
        pacientes.append(nuevo_paciente)
        guardar_pacientes(self.username, pacientes)
        QMessageBox.information(self, "Ã‰xito", f"Cliente {nombre} aÃ±adido como paciente.")
        
        # Actualizar tabla de clientes
        try:
            self.update_customers_table()
        except Exception:
            pass
        
        # Refrescar la pÃ¡gina de Pacientes si estÃ¡ cargada en la app
        try:
            if hasattr(self.parent_app, 'patients_page') and self.parent_app.patients_page is not None:
                try:
                    self.parent_app.patients_page.load_patients()
                except Exception:
                    pass
        except Exception:
            pass
        
        # ðŸŽ¯ REDIRECCIONAR A PACIENTES Y ABRIR MODAL CON EL NUEVO PACIENTE
        try:
            # Redirigir a la pÃ¡gina de pacientes (Ã­ndice 1)
            self.parent_app.mostrar_frame(1)
            
            # Usar QTimer para asegurar que la pÃ¡gina se ha cargado antes de abrir el modal
            from PyQt5.QtCore import QTimer
            def abrir_modal_paciente():
                try:
                    # Acceder a la pÃ¡gina de pacientes y mostrar los detalles del nuevo paciente
                    if hasattr(self.parent_app, 'patients_page') and self.parent_app.patients_page is not None:
                        self.parent_app.patients_page.show_details(nuevo_paciente)
                except Exception as e:
                    print(f"Error al abrir modal del paciente: {e}")
            
            # Esperar 300ms para que la pÃ¡gina se cargue
            QTimer.singleShot(300, abrir_modal_paciente)
        except Exception as e:
            print(f"Error al redirigir a pacientes: {e}")
    
    def abrir_detalles_cliente_doble_clic(self):
        """Abre ventana de detalles al hacer doble clic en una fila de cliente."""
        selected_rows = self.customers_table.selectedItems()
        if not selected_rows:
            return
        
        row_index = selected_rows[0].row()
        dni = self.customers_table.item(row_index, 0).text()
        self.abrir_detalles_cliente(dni)
    
    def abrir_detalles_cliente(self, dni):
        """Abre un diÃ¡logo con los detalles del cliente."""
        # Si hay streaming en curso, cancelarlo para evitar que inserte filas viejas.
        self._cancel_customers_streaming()
        clientes = cargar_clientes(self.username)
        cliente_data = next((c for c in clientes if c.get('dni') == dni), None)
        
        if cliente_data:
            from gui.dialogs.customer_details_dialog import CustomerDetailsDialog
            dialog = CustomerDetailsDialog(cliente_data, self.parent_app)
            # Conectar signal para refrescar tabla si se elimina cliente
            try:
                dialog.cliente_eliminado.connect(self._on_cliente_eliminado)
            except:
                pass
            dialog.exec_()
            
            # Limpiar cache para forzar recarga de datos actualizados
            self.all_clientes = []
            self.update_customers_table()
        else:
            QMessageBox.warning(self, "Error", "No se encontraron los datos del cliente.")
    
    def _reload_customers_after_delete(self, deleted_dni=""):
        """Recarga clientes tras una eliminacion, intentando refresco HTTP sin revivir el cliente borrado."""
        deleted_dni = str(deleted_dni or "").strip()
        clientes_locales = cargar_clientes(self.username)
        clientes_actualizados = list(clientes_locales) if isinstance(clientes_locales, list) else []

        try:
            from utils.api_handler import obtener_clientes_remoto
            from utils.file_handler import get_effective_branch_context

            ctx = get_effective_branch_context(self.username) or {}
            branch_code = str(ctx.get("code", "") or "").strip().upper()
            clientes_remotos = obtener_clientes_remoto(
                self.username,
                codigo_dispositivo=branch_code or None
            )
            if isinstance(clientes_remotos, list) and clientes_remotos:
                clientes_merged = list(clientes_remotos)
                remotos_dni = {
                    str(cliente.get("dni", "")).strip()
                    for cliente in clientes_remotos
                    if isinstance(cliente, dict)
                }

                for cliente_local in clientes_locales:
                    if not isinstance(cliente_local, dict):
                        continue
                    dni_local = str(cliente_local.get("dni", "")).strip()
                    if deleted_dni and dni_local == deleted_dni:
                        continue
                    if dni_local not in remotos_dni:
                        clientes_merged.append(cliente_local)

                clientes_actualizados = clientes_merged
        except Exception as e:
            print(f"[Clientes] No se pudo refrescar por HTTP tras eliminar cliente: {e}")

        if deleted_dni:
            clientes_actualizados = [
                cliente
                for cliente in clientes_actualizados
                if str(cliente.get("dni", "")).strip() != deleted_dni
            ]

        self.all_clientes = clientes_actualizados
        self.current_page = 0

        if getattr(self, "filter_active", False):
            self.apply_filters()
        else:
            self.update_customers_table()
            self.update_stats()

    def _on_cliente_eliminado(self, deleted_dni=""):
        """Se ejecuta cuando se elimina un cliente en el diÃ¡logo."""
        try:
            self._cancel_customers_streaming()
            self._reload_customers_after_delete(deleted_dni)
        except Exception as e:
            print(f"Error al refrescar tabla despuÃ©s de eliminaciÃ³n: {e}")

    def _cancel_customers_streaming(self):
        """Detiene/ignora cualquier carga por streaming en curso."""
        t = getattr(self, "streamer_thread", None)
        # Soltar referencia primero: los slots ignoraran señales antiguas.
        self.streamer_thread = None
        try:
            if t is not None and t.isRunning():
                t.requestInterruption()
                t.wait(300)
        except Exception:
            pass
    
    # ðŸš€ STREAMING: Carga de clientes por chunks
    def load_customers_streaming(self):
        # ðŸ›¡ï¸ VERIFICAR PERMISO: Solo carga si tiene 'ver' en clientes
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('clientes', 'ver'):
                self.customers_table.setRowCount(0)
                self._customers_loading = False
                self._hide_internal_customers_loader()
                return
        """Inicia la carga de clientes en background con streaming."""
        # Si ya estÃ¡ cargando, ignora la llamada
        if self.streamer_thread is not None and self.streamer_thread.isRunning():
            print("[INFO] Ya hay una carga de clientes en progreso")
            return
        
        # Si ya estÃ¡ cargado, ignora
        if self.all_clientes:
            print("[INFO] Clientes ya cargados, usando cache")
            self.update_customers_table()
            self.update_stats()
            return
        
        # Limpiar tabla
        self.customers_table.setRowCount(0)
        self.all_clientes = []
        self._customers_loading = True
        self._stream_table_preview_started = False
        self._customers_loader_active = False
        self.pagination_label.setText("Cargando clientes...")
        self.btn_prev_page.setEnabled(False)
        self.btn_next_page.setEnabled(False)
        self._show_internal_customers_loader("Preparando lista y estadisticas en segundo plano...")
        
        # Mostrar loader
        self._show_customers_loader()
        
        # Iniciar streaming en thread separado
        self.streamer_thread = CustomerStreamerThread(self.username, chunk_size=50)
        self.streamer_thread.chunk_ready.connect(self._on_chunk_ready)
        self.streamer_thread.stream_finished.connect(self._on_streaming_finished)
        self.streamer_thread.error.connect(self._on_streaming_error)
        self.streamer_thread.finished.connect(self.streamer_thread.deleteLater)
        self.streamer_thread.start()
    
    def _show_customers_loader(self):
        """Muestra un loader animado bonito centrado en la tabla de clientes."""
        if self.customers_content_stack is not None:
            self._show_internal_customers_loader("Preparando lista y estadisticas en segundo plano...")
            return

        # Limpiar tabla
        self.customers_table.setRowCount(0)
        self.customers_table.clearSpans()
        self._customers_loader_active = True
        
        # Crear widget contenedor para el loader
        loader_widget = QWidget()
        loader_layout = QVBoxLayout(loader_widget)
        loader_layout.setAlignment(Qt.AlignCenter)
        loader_layout.setSpacing(15)
        loader_layout.setContentsMargins(0, 0, 0, 0)
        
        # ðŸŽ¨ Crear SVG animado genÃ©rico
        svg_code = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <defs>
                <style>
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                    .spinner {
                        animation: spin 1.5s linear infinite;
                        transform-origin: 50px 50px;
                    }
                </style>
            </defs>
            <g class="spinner">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#f0f0f0" stroke-width="5"/>
                <path d="M 50 10 A 40 40 0 0 1 80 20" fill="none" stroke="#2a8659" stroke-width="5" stroke-linecap="round"/>
                <path d="M 80 20 A 40 40 0 0 1 90 50" fill="none" stroke="#2a8659" stroke-width="5" stroke-linecap="round" opacity="0.6"/>
            </g>
        </svg>'''
        
        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5 import QtGui, QtCore
        from PyQt5.QtGui import QPainter
        
        pixmap = QtGui.QPixmap(120, 120)
        pixmap.fill(QtCore.Qt.transparent)
        renderer = QSvgRenderer(svg_code.encode())
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        loader_icon = QLabel()
        loader_icon.setPixmap(pixmap)
        loader_icon.setAlignment(Qt.AlignCenter)
        loader_icon.setFixedSize(120, 120)
        
        loader_layout.addStretch()
        loader_layout.addWidget(loader_icon, alignment=Qt.AlignCenter)
        loader_layout.addStretch()
        
        # Agregar a la tabla como celda centrada
        self.customers_table.setCentralWidget(loader_widget) if hasattr(self.customers_table, 'setCentralWidget') else None
        
        # Si no tiene setCentralWidget, usar un workaround
        if not hasattr(self.customers_table, 'setCentralWidget'):
            # Insertar fila ficticia con el loader
            self.customers_table.insertRow(0)
            cell_widget = QWidget()
            cell_layout = QVBoxLayout(cell_widget)
            cell_layout.addWidget(loader_icon, alignment=Qt.AlignCenter)
            self.customers_table.setCellWidget(0, 0, cell_widget)
            self.customers_table.setSpan(0, 0, 1, 6)  # Ocupar todas las columnas

    def _maybe_render_streaming_preview(self):
        """Pinta la primera pagina apenas existe un chunk util."""
        if not self.all_clientes:
            return

        visible_target = min(len(self.all_clientes), int(self.items_per_page or 100))
        current_rows = int(self.customers_table.rowCount() or 0)
        needs_first_preview = not self._stream_table_preview_started
        needs_more_visible_rows = (
            not self.filter_active
            and self.current_page == 0
            and current_rows < visible_target
        )

        if not (needs_first_preview or needs_more_visible_rows):
            return

        self._stream_table_preview_started = True
        self._hide_internal_customers_loader()

        if self.filter_active:
            self.apply_filters()
        else:
            self.update_customers_table()
    
    def _on_chunk_ready(self, chunk):
        """Callback cuando un chunk de clientes estÃ¡ listo."""
        # Ignorar señales de threads antiguos/cancelados.
        try:
            if self.sender() is not getattr(self, "streamer_thread", None):
                return
        except Exception:
            pass
        # Agregar el chunk a la lista total
        self.all_clientes.extend(chunk)

        if self.customers_loading_subtitle is not None:
            self.customers_loading_subtitle.setText(
                f"Se cargaron {len(self.all_clientes)} clientes. Preparando tabla..."
            )
        self.pagination_label.setText(f"Cargando clientes... {len(self.all_clientes)}")

        print(f"âœ“ Cargados {len(self.all_clientes)} clientes...")
        self._maybe_render_streaming_preview()
    
    def _on_streaming_finished(self):
        """Callback cuando termina el streaming."""
        active_thread = getattr(self, "streamer_thread", None)
        try:
            if self.sender() is not active_thread:
                return
        except Exception:
            pass
        self.streamer_thread = None
        self._customers_loading = False
        print(f"âœ“ Streaming finalizado: {len(self.all_clientes)} clientes cargados")
        
        # Si no hay clientes, mostrar mensaje
        if len(self.all_clientes) == 0:
            self._hide_internal_customers_loader()
            self.customers_table.setRowCount(0)
            self.customers_table.clearSpans()
            empty_label = QLabel("No hay clientes registrados. Presiona 'Agregar Cliente Nuevo' para crear uno.")
            empty_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #666;
                    padding: 40px;
                    background: white;
                    text-align: center;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setWordWrap(True)
            # Insertar fila para mostrar el mensaje
            self.customers_table.insertRow(0)
            self.customers_table.setCellWidget(0, 0, empty_label)
            self.customers_table.setSpan(0, 0, 1, 6)
            self._update_pagination_controls(0)
            self.update_stats()
        else:
            self._hide_internal_customers_loader()
            self.update_customers_table()
            self.update_stats()
        
        # Esconder loader
        try:
            current_widget = self.parent().parent() if self.parent() else None
            if current_widget and hasattr(current_widget, 'hide_loader'):
                current_widget.hide_loader()
        except Exception:
            pass
    
    def _on_streaming_error(self, error_msg):
        """Callback en caso de error."""
        active_thread = getattr(self, "streamer_thread", None)
        try:
            if self.sender() is not active_thread:
                return
        except Exception:
            pass
        self.streamer_thread = None
        self._customers_loading = False
        self._hide_internal_customers_loader()
        self.customers_table.setRowCount(0)
        self.customers_table.clearSpans()
        self._update_pagination_controls(0)
        print(f"âŒ {error_msg}")
        
        # Esconder loader
        try:
            current_widget = self.parent().parent() if self.parent() else None
            if current_widget and hasattr(current_widget, 'hide_loader'):
                current_widget.hide_loader()
        except Exception:
            pass
    
    def create_add_person_icon_small(self):
        """Crea un Ã­cono SVG pequeÃ±o de persona con plus"""
        from PyQt5.QtSvg import QSvgRenderer
        
        svg_data = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <!-- Cabeza del usuario -->
            <circle cx="12" cy="5" r="2.5" fill="#2a8659" stroke="#2a8659" stroke-width="0.5"/>
            
            <!-- Cuerpo del usuario -->
            <path d="M 9 8 Q 9 7 12 7 Q 15 7 15 8 L 15 13 Q 15 14 12 14 Q 9 14 9 13 Z" fill="none" stroke="#2a8659" stroke-width="1"/>
            
            <!-- Plus vertical -->
            <line x1="16" y1="12" x2="16" y2="20" stroke="#2a8659" stroke-width="1.2" stroke-linecap="round"/>
            
            <!-- Plus horizontal -->
            <line x1="12" y1="16" x2="20" y2="16" stroke="#2a8659" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
        """
        
        pixmap = QPixmap(24, 24)
        pixmap.fill(QtCore.Qt.transparent)
        
        renderer = QSvgRenderer(svg_data.encode())
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    def _start_refresh_worker(self):
        """
        âš ï¸ DESACTIVADO: Auto-refresh en background
        
        Antes causaba actualizaciones constantes cada 10 segundos
        Ahora solo se actualiza cuando el usuario lo solicita explÃ­citamente
        """
        pass  # No hacer nada - auto-refresh desactivado
    
    def _on_refresh_data(self, clientes_remotos):
        """Slot que recibe datos actualizados del worker (en thread principal)."""
        try:
            if clientes_remotos is None:
                return
            
            # MERGE inteligente: no descartar clientes locales nuevos
            clientes_locales = cargar_clientes(self.username)
            clientes_merged = []
            
            # Primero, agregar todos los remotos (datos mÃ¡s recientes)
            clientes_merged.extend(clientes_remotos)
            
            # Luego, agregar clientes locales que NO estÃ¡n en remoto
            # (son nuevos, aÃºn no sincronizados)
            remotos_dni = set(c.get('dni', '') for c in clientes_remotos)
            
            for c_local in clientes_locales:
                if c_local.get('dni', '') not in remotos_dni:
                    # Este cliente es nuevo/local, agregarlo
                    clientes_merged.append(c_local)
            
            # Actualizar cache si cambiÃ³
            if clientes_merged != self.all_clientes:
                # IMPORTANTE: Guardar el merged en el archivo local
                # para que persista cuando refresquemos despuÃ©s
                from utils.file_handler import guardar_clientes
                guardar_clientes(self.username, clientes_merged)
                
                self.all_clientes = clientes_merged
                self.apply_filters()  # Actualiza tabla en UI
        except Exception as e:
            pass  # Silenciosamente ignorar errores

    def _auto_refresh_clientes(self):
        """Actualiza los clientes automÃ¡ticamente (MERGE local + remoto, sin eliminar clientes nuevos no sincronizados)."""
        try:
            # Si estÃ¡ cargando, no actualizar
            if self.streamer_thread and self.streamer_thread.isRunning():
                return
            
            # Cargar clientes LOCALES (lo que el usuario tiene)
            clientes_locales = cargar_clientes(self.username)
            
            # Intentar obtener del remoto
            clientes_remotos = None
            try:
                from utils.api_handler import obtener_clientes_remoto
                from utils.file_handler import get_effective_branch_context

                ctx = get_effective_branch_context(self.username) or {}
                branch_code = str(ctx.get("code", "") or "").strip().upper()
                clientes_remotos = obtener_clientes_remoto(
                    self.username,
                    codigo_dispositivo=branch_code or None
                )
                if not (isinstance(clientes_remotos, list) and clientes_remotos):
                    clientes_remotos = None
            except Exception:
                pass
            
            # ESTRATEGIA DE MERGE (no descartar clientes locales):
            # 1. Si no hay remotos, usar locales (sin internet)
            # 2. Si hay remotos, hacer MERGE inteligente:
            #    - Tomar remotos como "verdad"
            #    - Mantener clientes locales que NO estÃ¡n en remoto (todavÃ­a no sincronizados)
            #    - Eliminar SOLO si explÃ­citamente fue borrado en remoto
            
            if clientes_remotos is None:
                # Sin conexiÃ³n: usar locales
                clientes_merged = clientes_locales
            else:
                # Hacer MERGE: remoto + locales no sincronizados
                clientes_merged = []
                
                # Primero, agregar todos los remotos (datos mÃ¡s recientes)
                clientes_merged.extend(clientes_remotos)
                
                # Luego, agregar clientes locales que NO estÃ¡n en remoto
                # (son nuevos, aÃºn no sincronizados)
                remotos_dni = set(c.get('dni', '') for c in clientes_remotos)
                
                for c_local in clientes_locales:
                    if c_local.get('dni', '') not in remotos_dni:
                        # Este cliente es nuevo/local, agregarlo
                        clientes_merged.append(c_local)
            
            # Actualizar cache si cambiÃ³
            if clientes_merged != self.all_clientes:
                # IMPORTANTE: Guardar el merged en el archivo local
                # para que persista cuando refresquemos despuÃ©s
                from utils.file_handler import guardar_clientes
                guardar_clientes(self.username, clientes_merged)
                
                self.all_clientes = clientes_merged
                self.apply_filters()  # Actualiza tabla en UI
        except Exception as e:
            pass  # Silenciosamente ignorar errores
    
    def cleanup(self):
        """Limpia recursos cuando se cierra la pÃ¡gina."""
        self._cancel_table_render()
        try:
            self._filter_debounce_timer.stop()
        except Exception:
            pass
        # Detener worker de refresh
        if self.refresh_worker:
            self.refresh_worker.stop()
            self.refresh_worker.quit()
            self.refresh_worker.wait(500)
        
        # Detener thread de streaming
        if self.streamer_thread and self.streamer_thread.isRunning():
            self.streamer_thread.quit()
            self.streamer_thread.wait()

    def closeEvent(self, event):
        try:
            self.cleanup()
        except Exception:
            pass
        super().closeEvent(event)

