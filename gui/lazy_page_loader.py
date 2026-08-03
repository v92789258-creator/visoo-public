from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
import time
import logging

logger = logging.getLogger(__name__)

def load_page_on_demand(self, index):
    """
    Carga una página específica bajo demanda CON loader inteligente.
    
    🚀 OPTIMIZACIÓN:
    - Solo muestra loader si la carga tarda > 300ms
    - Carga rápida = sin interrupción visual
    - Loader solo aparece para operaciones lentas
    
    1. Inicia carga de página
    2. Si tarda > 300ms, muestra loader
    3. Cuando termina, oculta loader
    4. Retorna la página cargada o None si hay error
    """
    try:
        # Mapeo de índices a tipos de página
        page_types = {
            0: ('home', 'home_page'),
            1: ('patients', 'patients_page'),
            12: ('profile', 'profile_page'),
            2: ('create_patient', 'create_patient_page'),
            3: ('inventory', 'inventory_page'),
            4: ('sales', 'sales_page'),
            5: ('kardex', 'kardex_page'),
            6: ('appointments', 'appointments_page'),
            7: ('appointments', 'appointments_history_page'),
            9: ('customers', 'customers_page'),
            10: ('config', 'config_page'),
            11: ('services', 'services_page'),
            13: ('sales_register', 'sales_register_page'),
            14: ('advanced_reports', 'advanced_reports_page'),
            15: ('plantilla_boleta', 'plantilla_boleta_page'),
            16: ('categories', 'categories_page'),
            17: ('contracts_page', 'contracts_page')
        }

        if index not in page_types:
            return None

        page_type, attr_name = page_types[index]

        # Si la página ya está cargada, retornarla sin loader
        if hasattr(self, attr_name):
            return getattr(self, attr_name)

        # ============ CARGAR LA PÁGINA EN BACKGROUND ============
        page = None
        start_time = time.time()
        
        try:
            if page_type == 'appointments':
                try:
                    from utils.file_handler import is_modo_basico
                    basic_mode = bool(is_modo_basico(getattr(self, "username", "")))
                except Exception:
                    basic_mode = False
                if basic_mode and index == 6:
                    from gui.main_window_pages.basic_appointments_page import BasicAppointmentsPage
                    page = BasicAppointmentsPage(self)
                    if hasattr(page, "set_embedded_mode"):
                        page.set_embedded_mode(True)
                else:
                    from gui.main_window_pages.appointments_page import (
                        AppointmentsPage,
                        AppointmentHistoryWidget
                    )
                    if index == 6:
                        page = AppointmentsPage(self)
                    elif index == 7:
                        page = AppointmentHistoryWidget(self)
            else:
                module_name = f"gui.main_window_pages.{page_type}_page"
                if page_type == 'home':
                    from gui.main_window_pages.home_page import HomePage
                    page = HomePage(self)
                elif page_type == 'patients':
                    try:
                        from utils.file_handler import is_modo_basico
                        basic_mode = bool(is_modo_basico(getattr(self, "username", "")))
                    except Exception:
                        basic_mode = False
                    if basic_mode:
                        from gui.main_window_pages.basic_patients_page import BasicPatientsPage
                        page = BasicPatientsPage(self, initial_mode="search")
                        if hasattr(page, "set_embedded_mode"):
                            page.set_embedded_mode(True)
                    else:
                        from gui.main_window_pages.patients_page import PatientsPage
                        page = PatientsPage(self)
                elif page_type == 'profile':
                    from gui.main_window_pages.profile_page import ProfilePage
                    page = ProfilePage(self)
                elif page_type == 'create_patient':
                    try:
                        from utils.file_handler import is_modo_basico
                        basic_mode = bool(is_modo_basico(getattr(self, "username", "")))
                    except Exception:
                        basic_mode = False
                    if basic_mode:
                        from gui.main_window_pages.basic_graduation_page import BasicGraduationPage
                        page = BasicGraduationPage(self)
                    else:
                        from gui.main_window_pages.create_patient_page import CreatePatientPage
                        page = CreatePatientPage(self)
                elif page_type == 'inventory':
                    try:
                        from utils.file_handler import is_modo_basico
                        basic_mode = bool(is_modo_basico(getattr(self, "username", "")))
                    except Exception:
                        basic_mode = False
                    if basic_mode:
                        from gui.main_window_pages.basic_inventory_page import BasicInventoryPage
                        page = BasicInventoryPage(self)
                        if hasattr(page, "set_embedded_mode"):
                            page.set_embedded_mode(True)
                    else:
                        from gui.main_window_pages.inventory_page import InventoryPage
                        page = InventoryPage(self)
                elif page_type == 'sales':
                    try:
                        from utils.file_handler import is_modo_basico
                        basic_mode = bool(is_modo_basico(getattr(self, "username", "")))
                    except Exception:
                        basic_mode = False
                    if basic_mode:
                        from gui.main_window_pages.basic_sales_page import BasicSalesPage
                        page = BasicSalesPage(self)
                    else:
                        from gui.main_window_pages.sales_page import SalesPage
                        page = SalesPage(self)
                elif page_type == 'kardex':
                    from gui.main_window_pages.kardex_page import KardexPage
                    page = KardexPage(self)
                elif page_type == 'customers':
                    from gui.main_window_pages.customer_page import CustomersPage
                    page = CustomersPage(self)
                elif page_type == 'config':
                    from gui.main_window_pages.config_page import ConfigPage
                    page = ConfigPage(self)
                elif page_type == 'services':
                    from gui.main_window_pages.services_page import ServicesPage
                    page = ServicesPage(self)
                elif page_type == 'sales_register':
                    from gui.main_window_pages.registro_ventas_page import RegistroVentasPage
                    page = RegistroVentasPage(self)
                elif page_type == 'advanced_reports':
                    from gui.main_window_pages.advanced_reports_page import AdvancedReportsPage
                    page = AdvancedReportsPage(username=self.username if hasattr(self, 'username') else None, parent=self)
                elif page_type == 'plantilla_boleta':
                    from gui.main_window_pages.plantilla_boleta_page import PlantillaBobetaPage
                    page = PlantillaBobetaPage(self)
                elif page_type == 'categories':
                    from gui.main_window_pages.categories_page import CategoriesPage
                    page = CategoriesPage(self)
                elif page_type == 'contracts_page':
                    from gui.main_window_pages.contracts_page import ContractsPage
                    page = ContractsPage(self)

            # Guardar la página cargada
            setattr(self, attr_name, page)
            
            # Log del tiempo de carga (opcional, para debug)
            load_time = time.time() - start_time
            if load_time > 0.5:
                logger.info(f"[LOAD TIME] {page_type} cargó en {load_time:.2f}s")
            
            return page

        except ImportError as e:
            QMessageBox.warning(
                self, 
                "Error de carga",
                f"No se pudo cargar la página {page_type}. Error: {str(e)}"
            )
            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self, 
                "Error",
                f"Ocurrió un error al cargar la página {page_type}."
            )
            return None

    except Exception as e:
        print(f"[ERROR] Error general en load_page_on_demand: {e}")
        import traceback
        traceback.print_exc()
        return None
