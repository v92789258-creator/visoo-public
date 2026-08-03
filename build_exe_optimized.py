#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builder optimizado para VISO.exe con PyInstaller onefile.

Objetivo:
- Mantener un build completo por defecto.
- Permitir un perfil mas rapido para PCs lentas sin meter extras pesados.
- Evitar duplicar paquetes completos dentro del .exe.

Uso:
    python build_exe_optimized.py
    python build_exe_optimized.py dev
    python build_exe_optimized.py small
    python build_exe_optimized.py faststart
    python build_exe_optimized.py faststart noexcel nopdf noreports nothermal
    python build_exe_optimized.py legacydata

Flags:
    dev          -> consola visible
    small/upx    -> usa UPX si existe, exe mas chico pero arranque mas lento
    faststart    -> recorta extras pesados para abrir mas rapido
    legacydata   -> empaqueta datos como antes
    noqml        -> quita dialogs QML
    nopdf        -> quita PyMuPDF / visor PDF
    noreports    -> quita reportlab / expediente PDF / algunos reportes PDF
    noexcel      -> quita xlsxwriter / exportes Excel
    nothermal    -> quita python-escpos / impresion termica
    withpdf / withreports / withexcel / withthermal -> fuerzan esas funciones
"""

import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "icon.ico"
MAIN_PY = BASE_DIR / "main.py"
SPLASH_PATH = BASE_DIR / "splash.png"
RUNTIME_TMPDIR = r"%LOCALAPPDATA%\VISO_tmp"


CLI_FLAGS = {arg.strip().lower() for arg in sys.argv[1:]}


def feature_enabled(enable_flag: str, disable_flag: str, faststart_default: bool) -> bool:
    if enable_flag in CLI_FLAGS:
        return True
    if disable_flag in CLI_FLAGS:
        return False
    if FAST_START:
        return faststart_default
    return True


IS_DEVELOPMENT = "dev" in CLI_FLAGS
PREFER_SMALL_EXE = "small" in CLI_FLAGS or "upx" in CLI_FLAGS
USE_LEGACY_DATA = "legacydata" in CLI_FLAGS or "fulldata" in CLI_FLAGS
FAST_START = "faststart" in CLI_FLAGS or "lite" in CLI_FLAGS or "rapido" in CLI_FLAGS

if "full" in CLI_FLAGS or "allfeatures" in CLI_FLAGS or "fullfeatures" in CLI_FLAGS:
    FAST_START = False

ENABLE_QML = "noqml" not in CLI_FLAGS
ENABLE_PDF = feature_enabled("withpdf", "nopdf", False)
ENABLE_REPORTS = feature_enabled("withreports", "noreports", False)
ENABLE_EXCEL = feature_enabled("withexcel", "noexcel", False)
ENABLE_THERMAL = feature_enabled("withthermal", "nothermal", False)

CONSOLE_FLAG = "--console" if IS_DEVELOPMENT else "--windowed"


def print_banner() -> None:
    print("\n" + "=" * 72)
    print("COMPILANDO VISO A .EXE (OPTIMIZADO PARA ONEFILE)")
    print(f"  Modo: {'DESARROLLO' if IS_DEVELOPMENT else 'PRODUCCION'}")
    print(f"  Perfil: {'FASTSTART' if FAST_START else 'COMPLETO'}")
    print("=" * 72)
    print(f"  PDF/PyMuPDF: {'SI' if ENABLE_PDF else 'NO'}")
    print(f"  Reportes PDF: {'SI' if ENABLE_REPORTS else 'NO'}")
    print(f"  Excel: {'SI' if ENABLE_EXCEL else 'NO'}")
    print(f"  Impresion termica: {'SI' if ENABLE_THERMAL else 'NO'}")
    print(f"  QML: {'SI' if ENABLE_QML else 'NO'}")
    print("=" * 72 + "\n")


def verify_inputs() -> None:
    if not ICON_PATH.exists():
        print(f"ERROR: No se encuentra el archivo icon.ico en {ICON_PATH}")
        sys.exit(1)
    if not MAIN_PY.exists():
        print(f"ERROR: No se encuentra main.py en {MAIN_PY}")
        sys.exit(1)

    print(f"[OK] Icono encontrado: {ICON_PATH}")
    print(f"[OK] Main encontrado: {MAIN_PY}")


def _drive_label(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive or resolved.anchor
    return drive.rstrip("\\/") or str(resolved)


def _free_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024 * 1024 * 1024)


def verify_build_disk_space() -> None:
    temp_dir = Path(tempfile.gettempdir())
    build_drive = _drive_label(BASE_DIR)
    temp_drive = _drive_label(temp_dir)

    minimum_gb = 4.5 if FAST_START else 7.0
    if PREFER_SMALL_EXE:
        minimum_gb += 0.5

    paths_to_check = {build_drive: BASE_DIR, temp_drive: temp_dir}
    lowest_free_gb = min(_free_gb(path) for path in paths_to_check.values())

    print(
        f"[INFO] Espacio libre detectado: "
        + ", ".join(
            f"{label}={_free_gb(path):.2f} GB" for label, path in paths_to_check.items()
        )
    )
    print(f"[INFO] Espacio minimo recomendado para este build: {minimum_gb:.1f} GB")

    if lowest_free_gb < minimum_gb:
        print(
            "\n[ERROR] Espacio insuficiente para compilar el .exe onefile.\n"
            f"Libera espacio en disco antes de continuar. Recomendado: al menos {minimum_gb:.1f} GB libres.\n"
            "Sugerencias:\n"
            "  - Borra carpetas build/dist antiguas si no las necesitas.\n"
            "  - Vacia la papelera y archivos temporales de Windows.\n"
            "  - Mueve videos/instaladores pesados fuera de C:.\n"
        )
        sys.exit(1)


def resolve_upx_flag() -> str:
    upx_available = shutil.which("upx") is not None
    use_upx = bool(upx_available and PREFER_SMALL_EXE)

    if use_upx:
        print("[OK] UPX habilitado (exe mas chico, arranque mas lento)")
        return ""

    if upx_available:
        print("[OK] UPX disponible, pero desactivado para priorizar arranque")
    else:
        print("[AVISO] UPX no disponible (seguimos sin compresion extra)")
    return "--noupx"


def build_excluded_modules() -> list[str]:
    excluded = [
        # Ciencia de datos / ML
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "sklearn",
        "tensorflow",
        "keras",
        "torch",
        "torchvision",
        "torchaudio",
        "matplotlib",
        "matplotlib.pyplot",
        "matplotlib.backends",
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.figure",
        "matplotlib.patches",

        # Testing / docs / tooling
        "pytest",
        "nose",
        "sphinx",
        "doctest",
        "setuptools",
        "pip",
        "wheel",
        "jupyter",
        "notebook",
        "ipython",
        "IPython",
        "jedi",

        # GUI ajenas
        "tkinter",
        "Tkinter",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",

        # Otros no usados
        "curses",
        "pydoc",
        "PyQt5.QtWebEngine",
        "PyQt5.QtWebEngineCore",
        "PyQt5.QtWebEngineWidgets",
    ]

    if not ENABLE_QML:
        excluded.extend(
            [
                "PyQt5.QtQml",
                "PyQt5.QtQuick",
                "PyQt5.QtQuickWidgets",
            ]
        )

    if not ENABLE_PDF:
        excluded.extend(
            [
                "fitz",
                "pymupdf",
                "pymupdf.table",
                "pymupdf.utils",
                "pymupdf_fonts",
            ]
        )

    if not ENABLE_REPORTS:
        excluded.extend(
            [
                "reportlab",
                "reportlab.lib",
                "reportlab.lib.pagesizes",
                "reportlab.lib.styles",
                "reportlab.lib.units",
                "reportlab.pdfgen",
                "reportlab.platypus",
                "reportlab.platypus.tables",
            ]
        )

    if not ENABLE_EXCEL:
        excluded.append("xlsxwriter")

    if not ENABLE_THERMAL:
        excluded.extend(
            [
                "escpos",
                "escpos.printer",
                "escpos.capabilities",
            ]
        )

    return excluded


def build_hidden_imports() -> list[str]:
    hidden = [
        # PyQt esencial
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtSvg",
        "PyQt5.QtPrintSupport",
        "PyQt5.QtSql",
        "PyQt5.QtNetwork",

        # Red / certificados
        "requests",
        "urllib3",
        "certifi",

        # Core de boletas / QR (se usan bastante en ventas)
        "qrcode",
        "fpdf",

        # Paginas cargadas por importlib en async_page_loader
        "gui.main_window_pages.home_page",
        "gui.main_window_pages.patients_page",
        "gui.main_window_pages.create_patient_page",
        "gui.main_window_pages.inventory_page",
        "gui.main_window_pages.sales_page",
        "gui.main_window_pages.kardex_page",
        "gui.main_window_pages.appointments_page",
        "gui.main_window_pages.customer_page",
        "gui.main_window_pages.config_page",
        "gui.main_window_pages.services_page",
        "gui.main_window_pages.registro_ventas_page",
        "gui.main_window_pages.advanced_reports_page",
        "gui.main_window_pages.plantilla_boleta_page",
        "gui.main_window_pages.categories_page",
        "gui.main_window_pages.profile_page",
    ]

    if ENABLE_QML:
        hidden.extend(
            [
                "PyQt5.QtQml",
                "PyQt5.QtQuick",
                "PyQt5.QtQuickWidgets",
                "gui.dialogs.branch_quota_qml_dialog",
                "gui.dialogs.branch_recovery_qml_dialog",
                "gui.dialogs.topbar_hamburger_qml_dialog",
            ]
        )

    if ENABLE_PDF:
        hidden.extend(
            [
                "fitz",
                "pymupdf",
                "gui.dialogs.pdf_viewer_dialog",
            ]
        )

    if ENABLE_REPORTS:
        hidden.extend(
            [
                "reportlab",
                "reportlab.lib",
                "reportlab.lib.pagesizes",
                "reportlab.lib.styles",
                "reportlab.lib.units",
                "reportlab.pdfgen",
                "reportlab.platypus",
                "reportlab.platypus.tables",
            ]
        )

    if ENABLE_EXCEL:
        hidden.append("xlsxwriter")

    if ENABLE_THERMAL:
        hidden.extend(
            [
                "escpos",
                "escpos.printer",
                "escpos.capabilities",
                "utils.escpos_thermal_printer",
            ]
        )

    # Quitar duplicados sin perder orden
    return list(dict.fromkeys(hidden))


def add_data_item(args: list[str], src_relative: str, dest_relative: str) -> None:
    src_path = BASE_DIR / src_relative
    if src_path.exists():
        args.append(f"--add-data={src_path}{os.pathsep}{dest_relative}")
        print(f"  [OK] {src_relative} -> {dest_relative}")
    else:
        print(f"  [NO ENCONTRADO] {src_relative}")


def build_data_items() -> list[tuple[str, str]]:
    minimal_data_items = [
        ("data", "data"),
        ("images", "images"),
        ("gui/icons", "gui/icons"),
        ("utils/img", "utils/img"),
        ("utils/lan/templates", "utils/lan/templates"),
        ("DISEÑOSPDF", "DISEÑOSPDF"),
        ("guia.html", "."),
        ("icon.ico", "."),
        ("splash.png", "."),
        ("INICIAR.PNG", "."),
    ]

    if ENABLE_QML:
        minimal_data_items.append(("gui/qml", "gui/qml"))

    legacy_data_items = [
        ("gui", "gui"),
        ("utils", "utils"),
        ("data", "data"),
        ("images", "images"),
        ("DISEÑOSPDF", "DISEÑOSPDF"),
        ("guia.html", "."),
        ("icon.ico", "."),
        ("splash.png", "."),
        ("INICIAR.PNG", "."),
        ("sesion.gif", "."),
        ("ext", "ext"),
        ("cpp", "cpp"),
    ]

    return legacy_data_items if USE_LEGACY_DATA else minimal_data_items


def build_pyinstaller_args() -> list[str]:
    args = [
        str(MAIN_PY),
        "--onedir",
        CONSOLE_FLAG,
        f"--icon={ICON_PATH}",
        "--name=VISO",
        "-y",
        "--clean",
        f"--runtime-tmpdir={RUNTIME_TMPDIR}",
        "--optimize=1",
    ]

    upx_flag = resolve_upx_flag()
    if upx_flag:
        args.append(upx_flag)

    for module_name in build_excluded_modules():
        args.append(f"--exclude-module={module_name}")

    for hidden_import in build_hidden_imports():
        args.append(f"--hidden-import={hidden_import}")

    for src, dest in build_data_items():
        add_data_item(args, src, dest)

    if SPLASH_PATH.exists():
        args.append(f"--splash={SPLASH_PATH}")
        print("  [OK] Splash de bootloader: splash.png")
    else:
        print("  [NO ENCONTRADO] splash.png para splash del bootloader")

    # Solo recolectar los datos de python-escpos (capabilities, perfiles).
    # Antes se duplicaba el paquete completo con --add-data=escpos.
    if ENABLE_THERMAL:
        try:
            importlib.import_module("escpos")
            args.append("--collect-data=escpos")
            print("  [OK] Datos de escpos (sin duplicar el paquete completo)")
        except ModuleNotFoundError:
            print("  [NO] escpos no disponible en el entorno actual")

    # Certifi suele necesitar su bundle de certificados en runtime.
    try:
        importlib.import_module("certifi")
        args.append("--collect-data=certifi")
    except ModuleNotFoundError:
        pass

    return args


def print_summary() -> None:
    print("\n" + "=" * 72)
    print("CONFIGURACION FINAL")
    print(f"  Modo consola: {'SI' if IS_DEVELOPMENT else 'NO'}")
    print(f"  UPX: {'SI' if PREFER_SMALL_EXE else 'NO'}")
    print(f"  Runtime tmpdir: {RUNTIME_TMPDIR}")
    print(f"  Datos extra: {'LEGACY/FULL' if USE_LEGACY_DATA else 'MINIMAL'}")
    print(f"  Perfil rapido: {'SI' if FAST_START else 'NO'}")
    print("=" * 72 + "\n")


def main() -> None:
    print_banner()
    verify_inputs()
    verify_build_disk_space()
    args = build_pyinstaller_args()
    print_summary()

    try:
        pyinstaller_main = importlib.import_module("PyInstaller.__main__")
        pyinstaller_main.run(args)
        print("\n" + "=" * 72)
        print("[EXITO] COMPILACION EXITOSA")
        print("=" * 72)
        exe_path = BASE_DIR / "dist" / "VISO.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\nArchivo generado: {exe_path}")
            print(f"Tamanio: {size_mb:.1f} MB")
    except SystemExit as e:
        if e.code == 0:
            print("\n" + "=" * 72)
            print("[EXITO] COMPILACION EXITOSA")
            print("=" * 72)
        else:
            print(f"\n[ERROR] Compilacion fallida (exit code: {e.code})")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        if isinstance(e, OSError) and getattr(e, "errno", None) == 28:
            print(
                "\n[AYUDA] PyInstaller se quedo sin espacio al empaquetar el .exe.\n"
                "Libera varios GB en C: y vuelve a ejecutar el build."
            )
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
