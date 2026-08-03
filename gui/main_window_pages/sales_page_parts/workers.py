from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal

from utils.file_handler import cargar_pacientes, cargar_ventas


class DNISearchWorker(QObject):
    """Worker que ejecuta la búsqueda de DNI en un thread separado."""

    finished = pyqtSignal()
    success = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, dni):
        super().__init__()
        self.dni = dni

    def run(self):
        """Busca el DNI en la API."""
        try:
            import requests

            if not self.dni or len(self.dni) != 8 or not self.dni.isdigit():
                self.error.emit("Ingrese un DNI válido de 8 dígitos.")
                return

            if self.dni == "00000000":
                self.error.emit("cliente_generico")
                return

            url = f"https://boletaspe.com/buscar_dni.php?dni={self.dni}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()

            if data.get("nombres") and data.get("apellidos"):
                self.success.emit(data)
            else:
                self.error.emit("El DNI no está registrado en RENIEC.")

        except requests.exceptions.Timeout:
            self.error.emit("Timeout: La conexión tardó demasiado.")
        except requests.exceptions.ConnectionError:
            self.error.emit("No se pudo conectar a boletaspe.com. Verifique su conexión.")
        except requests.exceptions.HTTPError as e:
            self.error.emit(f"Error HTTP {e.response.status_code}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()


class DebtLoadWorker(QObject):
    finished = pyqtSignal(list, list, str)

    def __init__(self, username):
        super().__init__()
        self._username = username

    @QtCore.pyqtSlot()
    def run(self):
        try:
            ventas = cargar_ventas(self._username)
            if not isinstance(ventas, list):
                ventas = []
            try:
                pacientes = cargar_pacientes(self._username)
            except Exception:
                pacientes = []
            if not isinstance(pacientes, list):
                pacientes = []
            self.finished.emit(ventas, pacientes, "")
        except Exception as e:
            self.finished.emit([], [], str(e))
