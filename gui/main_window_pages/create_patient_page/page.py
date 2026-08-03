from PyQt5.QtWidgets import QWidget

from .navigation import CreatePatientPageNavigationMixin
from .patient_actions import CreatePatientPagePatientActionsMixin
from .sales import CreatePatientPageSalesMixin
from .ui_helpers import CreatePatientPageUiHelpersMixin
from .ui_setup import CreatePatientPageUiSetupMixin


class CreatePatientPage(
    CreatePatientPageUiHelpersMixin,
    CreatePatientPageUiSetupMixin,
    CreatePatientPagePatientActionsMixin,
    CreatePatientPageNavigationMixin,
    CreatePatientPageSalesMixin,
    QWidget,
):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, "username", None)
        self.lejos_form_widgets = {}
        self.cerca_form_widgets = {}
        self.loader_rotation = 0
        self.loader_timer = None
        self.btn_buscar_dni = None
        self.search_worker = None
        self.items_venta = []
        self.print_worker = None
        self.motilidad_versiones = self._default_motilidad_versiones()
        self._modo_edicion_graduacion = False
        self._graduacion_edit_index = None
        self._prefilled_contrato_numero = ""
        self._graduacion_payment_prefill = {}
        self._extra_contract_fields = self._default_extra_contract_fields()
        self._grad_nav_pos_by_widget = {}
        self._grad_nav_grid = {}
        self._grad_nav_sequence = []
        self.setup_ui()
