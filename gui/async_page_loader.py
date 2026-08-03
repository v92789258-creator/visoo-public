# -*- coding: utf-8 -*-

import traceback
import importlib
from typing import Optional, Tuple

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


# Páginas que suelen congelar por import grande + init pesado.
# Incluimos Home (0) porque el dashboard importa varios componentes pesados.
ASYNC_PAGE_INDICES = {0, 1, 3, 4, 5, 9}  # 0=Inicio, 1=Pacientes, 3=Inventario, 4=Ventas, 5=Kardex, 9=Clientes


def _get_page_import_spec(index: int) -> Optional[Tuple[str, str, str]]:
    """
    Retorna (module_name, class_name, ctor_kind)
    ctor_kind:
      - "parent": cls(parent)
      - "username_parent": cls(username=..., parent=parent)
    """
    specs = {
        0: ("gui.main_window_pages.home_page", "HomePage", "parent"),
        1: ("gui.main_window_pages.patients_page", "PatientsPage", "parent"),
        2: ("gui.main_window_pages.create_patient_page", "CreatePatientPage", "parent"),
        3: ("gui.main_window_pages.inventory_page", "InventoryPage", "parent"),
        4: ("gui.main_window_pages.sales_page", "SalesPage", "parent"),
        5: ("gui.main_window_pages.kardex_page", "KardexPage", "parent"),
        6: ("gui.main_window_pages.appointments_page", "AppointmentsPage", "parent"),
        7: ("gui.main_window_pages.appointments_page", "AppointmentHistoryWidget", "parent"),
        9: ("gui.main_window_pages.customer_page", "CustomersPage", "parent"),
        10: ("gui.main_window_pages.config_page", "ConfigPage", "parent"),
        11: ("gui.main_window_pages.services_page", "ServicesPage", "parent"),
        13: ("gui.main_window_pages.registro_ventas_page", "RegistroVentasPage", "parent"),
        14: ("gui.main_window_pages.advanced_reports_page", "AdvancedReportsPage", "username_parent"),
        15: ("gui.main_window_pages.plantilla_boleta_page", "PlantillaBobetaPage", "parent"),
        16: ("gui.main_window_pages.categories_page", "CategoriesPage", "parent"),
        12: ("gui.main_window_pages.profile_page", "ProfilePage", "parent"),
        17: ("gui.main_window_pages.contracts_page", "ContractsPage", "parent"),
    }
    return specs.get(index)


class LoadingPage(QtWidgets.QWidget):
    def __init__(self, title: str = "Cargando...", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingPage")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #172b4d;")

        self.subtitle_label = QtWidgets.QLabel(subtitle)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #5e6c84;")

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(320)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

    def set_status(self, subtitle: str) -> None:
        try:
            self.subtitle_label.setText(subtitle or "")
        except Exception:
            pass


class AsyncPageImportWorker(QtCore.QThread):
    """
    Importa el módulo en background (para que el click no se congele).
    La instanciación del QWidget SIEMPRE se hace en el thread principal.
    """

    page_imported = QtCore.pyqtSignal(int, str, str, str, str)  # index, module, class, ctor_kind, error

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = int(index)

    def run(self):
        spec = _get_page_import_spec(self.index)
        if not spec:
            self.page_imported.emit(self.index, "", "", "", f"Índice de página inválido: {self.index}")
            return

        module_name, class_name, ctor_kind = spec
        try:
            importlib.import_module(module_name)
            self.page_imported.emit(self.index, module_name, class_name, ctor_kind, "")
        except Exception as e:
            err = f"{e}"
            try:
                err = f"{err}\n{traceback.format_exc()}"
            except Exception:
                pass
            self.page_imported.emit(self.index, module_name, class_name, ctor_kind, err)
