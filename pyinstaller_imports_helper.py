"""
Helper de imports - Asegura que PyInstaller incluya todos los módulos necesarios
Este archivo se importa en build_exe.py para forzar la inclusión de módulos
"""

# Asegurar que todos los módulos de GUI se importan
from gui.dialogs import selection_dialogs
from gui.dialogs import paciente_selector_dialog
from gui.dialogs import appointment_dialog
from gui.dialogs import sale_options_dialog

# Asegurar que todos los módulos de pages se importan
from gui.main_window_pages import sales_page
from gui.main_window_pages import customers_page
from gui.main_window_pages import appointments_page

# Asegurar que todos los módulos de utils se importan
from utils import data_cache_manager
from utils import file_handler
from utils import barcode_scanner
from utils import appointments_model
from utils import appointments_stats
from utils import appointments_improvements

# PyQt5 submodules
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtPrintSupport import *
from PyQt5.QtSql import *
from PyQt5.QtNetwork import *

# Otros módulos críticos
import json
import datetime
import traceback
import sys
import os
import functools

print("[IMPORTS_HELPER] Todos los módulos cargados para PyInstaller")
