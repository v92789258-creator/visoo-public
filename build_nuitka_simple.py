#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builder onefile rapido para VISO usando Nuitka.

Objetivo:
- Mantener un unico .exe
- Reducir el costo de arranque en usos repetidos
- Mostrar splash nativo del bootloader antes de que cargue Python

Uso:
    python build_nuitka_simple.py
    python build_nuitka_simple.py dev
    python build_nuitka_simple.py nocache
    python build_nuitka_simple.py compressed
    python build_nuitka_simple.py nopdf

Notas:
- Con `onefile` el primer arranque siempre tendra costo de extraccion.
- Con cache activada, los arranques siguientes evitan re-extraer todo.
- En PCs lentas conviene dejar cache activada y sin compresion onefile.
"""

import os
import shutil
import subprocess
import sys
import tempfile


def load_version(base_dir: str, default: str = "4.2.5") -> str:
    version_path = os.path.join(base_dir, ".version")
    try:
        if os.path.exists(version_path):
            with open(version_path, "r", encoding="utf-8") as fh:
                value = str(fh.read() or "").strip()
            if value:
                return value
    except Exception:
        pass
    return default


def add_if_exists(cmd: list[str], flag: str, path: str) -> None:
    if os.path.exists(path):
        cmd.append(f"{flag}={path}")


def add_data_dir_if_exists(cmd: list[str], base_dir: str, name: str) -> None:
    path = os.path.join(base_dir, name)
    if os.path.isdir(path):
        cmd.append(f"--include-data-dir={path}={name}")


def add_data_file_if_exists(cmd: list[str], path: str, target_name: str) -> None:
    if os.path.isfile(path):
        cmd.append(f"--include-data-files={path}={target_name}")


def build_clean_icon(source_icon: str) -> str:
    """
    Reempaqueta el .ico para evitar crashes de postprocesado en Nuitka
    con iconos mal formados o con estructuras que Windows tolera pero Nuitka no.
    """
    if not os.path.isfile(source_icon):
        return source_icon

    try:
        from PIL import Image

        cleaned_icon = os.path.join(tempfile.gettempdir(), "viso_nuitka_clean_icon.ico")
        with Image.open(source_icon) as image:
            image.save(
                cleaned_icon,
                format="ICO",
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
            )
        return cleaned_icon if os.path.isfile(cleaned_icon) else source_icon
    except Exception as exc:
        print(f"[AVISO] No se pudo limpiar icon.ico para Nuitka: {exc}")
        return source_icon


def main() -> int:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    main_file = os.path.join(base_dir, "main.py")
    output_dir = os.path.join(base_dir, "dist_nuitka_fast")
    icon_path = os.path.join(base_dir, "icon.ico")
    splash_path = os.path.join(base_dir, "splash.png")
    version = load_version(base_dir)
    effective_icon_path = build_clean_icon(icon_path)

    cli_flags = {arg.lower() for arg in sys.argv[1:]}
    is_development = "dev" in cli_flags
    disable_cache = "nocache" in cli_flags
    prefer_compressed = "compressed" in cli_flags
    disable_pdf_support = "nopdf" in cli_flags or "nofitz" in cli_flags

    console_mode = "force" if is_development else "disable"
    tempdir_spec = (
        r"%TEMP%/VISO_%PID%_%TIME%"
        if disable_cache
        else r"%CACHE_DIR%/VISO/%VERSION%"
    )
    cache_mode = "temporary" if disable_cache else "cached"

    if os.path.exists(output_dir):
        print(f"[LIMPIEZA] Eliminando {output_dir} ...")
        shutil.rmtree(output_dir, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        f"--output-dir={output_dir}",
        "--output-filename=VISO.exe",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--windows-console-mode={console_mode}",
        "--python-flag=no_site",
        "--enable-plugins=pyqt5",
        "--include-package=PyQt5",
        "--include-package=core",
        "--include-package=gui",
        "--include-package=utils",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=pandas",
        "--company-name=VISO",
        "--product-name=VISO",
        f"--file-version={version}",
        f"--product-version={version}",
        f"--onefile-tempdir-spec={tempdir_spec}",
        f"--onefile-cache-mode={cache_mode}",
    ]

    if not prefer_compressed:
        cmd.append("--onefile-no-compression")

    if disable_pdf_support:
        cmd.extend([
            "--nofollow-import-to=fitz",
            "--nofollow-import-to=pymupdf",
        ])

    add_if_exists(cmd, "--windows-icon-from-ico", effective_icon_path)
    add_if_exists(cmd, "--onefile-windows-splash-screen-image", splash_path)

    add_data_dir_if_exists(cmd, base_dir, "data")
    add_data_dir_if_exists(cmd, base_dir, "images")
    add_data_dir_if_exists(cmd, base_dir, "ext")

    add_data_file_if_exists(cmd, os.path.join(base_dir, ".version"), ".version")
    add_data_file_if_exists(cmd, os.path.join(base_dir, "icon.ico"), "icon.ico")
    add_data_file_if_exists(cmd, os.path.join(base_dir, "splash.png"), "splash.png")
    add_data_file_if_exists(cmd, os.path.join(base_dir, "INICIAR.PNG"), "INICIAR.PNG")

    cmd.append(main_file)

    print("\n[BUILD NUITKA FAST-START]")
    print(f"  Version: {version}")
    print(f"  Modo consola: {console_mode}")
    print(f"  Cache onefile: {'NO' if disable_cache else 'SI'}")
    print(f"  Cache mode: {cache_mode}")
    print(f"  Compresion onefile: {'SI' if prefer_compressed else 'NO'}")
    print(f"  Soporte PDF/PyMuPDF: {'NO' if disable_pdf_support else 'SI'}")
    print(f"  Tempdir spec: {tempdir_spec}")
    print("  Salida: dist_nuitka_fast\\VISO.exe")
    print("")

    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode != 0:
        print("\n[ERROR] Fallo la compilacion con Nuitka.")
        print("Si necesitas volver a PyInstaller: python build_exe_optimized.py")
        return int(result.returncode or 1)

    exe_path = os.path.join(output_dir, "VISO.exe")
    print("\n[OK] Compilacion completada.")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"[EXE] {exe_path}")
        print(f"[SIZE] {size_mb:.1f} MB")
    print("")
    print("Esperado:")
    print("- Primer arranque: aun puede tardar por extraccion inicial.")
    print("- Arranques siguientes: mucho mas rapidos por cache persistente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
