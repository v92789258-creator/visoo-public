#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builder rapido para un .exe pequeno que solo prueba el flujo de actualizacion."""

import importlib
import os
import shutil
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "icon.ico"
ENTRY_POINT = BASE_DIR / "update_test_app.py"
DIST_NAME = "VISO_Update_Test"
BUILD_DIR = BASE_DIR / "build" / DIST_NAME
DIST_DIR = BASE_DIR / "dist" / DIST_NAME
SPEC_PATH = BASE_DIR / f"{DIST_NAME}.spec"
CLI_FLAGS = {arg.strip().lower() for arg in sys.argv[1:]}
IS_DEVELOPMENT = "dev" in CLI_FLAGS
CONSOLE_FLAG = "--console" if IS_DEVELOPMENT else "--windowed"


def verify_inputs() -> None:
    if not ENTRY_POINT.exists():
        print(f"ERROR: No se encuentra {ENTRY_POINT}")
        sys.exit(1)
    if not ICON_PATH.exists():
        print(f"ERROR: No se encuentra {ICON_PATH}")
        sys.exit(1)


def remove_path_if_exists(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
            print(f"[OK] Limpiado: {path}")
        elif path.exists():
            path.unlink()
            print(f"[OK] Eliminado: {path}")
    except PermissionError as exc:
        print(f"[ERROR] Archivo/carpeta bloqueado: {path}\n{exc}")
        sys.exit(1)


def cleanup_previous_build() -> None:
    remove_path_if_exists(BUILD_DIR)
    remove_path_if_exists(DIST_DIR)
    remove_path_if_exists(SPEC_PATH)


def build_pyinstaller_args() -> list[str]:
    args = [
        str(ENTRY_POINT),
        "--onedir",
        CONSOLE_FLAG,
        "--clean",
        "-y",
        f"--distpath={BASE_DIR / 'dist'}",
        f"--workpath={BASE_DIR / 'build'}",
        f"--specpath={BASE_DIR}",
        f"--icon={ICON_PATH}",
        f"--name={DIST_NAME}",
        "--noupx",
        "--optimize=1",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=requests",
        "--hidden-import=urllib3",
        "--hidden-import=certifi",
        f"--add-data={BASE_DIR / 'VERSION'}{os.pathsep}.",
    ]
    try:
        importlib.import_module("certifi")
        args.append("--collect-data=certifi")
    except ModuleNotFoundError:
        pass
    return args


def main() -> None:
    print("=" * 72)
    print("COMPILANDO TESTER DE ACTUALIZACION DE VISO")
    print(f"Entrada: {ENTRY_POINT.name}")
    print(f"Salida: dist\\{DIST_NAME}")
    print("=" * 72)
    verify_inputs()
    cleanup_previous_build()

    try:
        pyinstaller_main = importlib.import_module("PyInstaller.__main__")
        pyinstaller_main.run(build_pyinstaller_args())
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise

    exe_path = DIST_DIR / f"{DIST_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Generado: {exe_path}")
        print(f"[OK] Tamano: {size_mb:.1f} MB")
    else:
        print("[AVISO] PyInstaller termino pero no se encontro el .exe esperado.")


if __name__ == "__main__":
    main()
