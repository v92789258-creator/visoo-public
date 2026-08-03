#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App minima para probar el flujo de actualizacion externa de VISO."""

import json
import os
import re
import subprocess
import sys
from urllib.parse import urlparse

import requests
from PyQt5 import QtCore, QtWidgets


UPDATE_INFO_URL = "https://api.yhana.cloud/v.json"


def load_local_version(default: str = "0.0.0") -> str:
    base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    candidates = [
        os.path.join(base_dir, "VERSION"),
        os.path.join(base_dir, ".version"),
        os.path.join(os.path.dirname(base_dir), "VERSION"),
        os.path.join(os.path.dirname(base_dir), ".version"),
    ]
    for path in candidates:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as fh:
                value = str(fh.read() or "").strip()
            if value:
                return value
        except Exception:
            continue
    return default


def parse_version_tuple(value):
    nums = re.findall(r"\d+", str(value or "").strip())
    return tuple(int(n) for n in nums) if nums else tuple()


def is_remote_version_newer(local_version: str, remote_version: str) -> bool:
    local_t = parse_version_tuple(local_version)
    remote_t = parse_version_tuple(remote_version)
    if not local_t or not remote_t:
        return str(remote_version or "").strip() != str(local_version or "").strip()
    max_len = max(len(local_t), len(remote_t))
    return remote_t + (0,) * (max_len - len(remote_t)) > local_t + (0,) * (max_len - len(local_t))


def parse_update_manifest_text(raw_text):
    text = str(raw_text or "").lstrip("\ufeff").strip()
    if not text:
        raise ValueError("Respuesta vacia en v.json")
    try:
        data = json.loads(text)
    except Exception:
        data = {}
        body = text.strip().strip("{}").strip()
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = str(key or "").strip().strip("\"' ")
            value = str(value or "").strip().rstrip(",").strip()
            if not key:
                continue
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            data[key] = value
    if not isinstance(data, dict):
        raise ValueError("v.json no es un objeto JSON")
    return data


class UpdateTestWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.local_version = load_local_version("0.0.0")
        self.setWindowTitle("Prueba de actualizacion VISO")
        self.resize(560, 260)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("Tester de actualizacion externa")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        self.info_label = QtWidgets.QLabel(
            f"Version local detectada: {self.local_version}\nURL: {UPDATE_INFO_URL}"
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 15px;")
        layout.addWidget(self.info_label)

        self.status_label = QtWidgets.QLabel("Listo para verificar.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 15px; color: #1f2937;")
        layout.addWidget(self.status_label)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_check = QtWidgets.QPushButton("Buscar actualizacion")
        self.btn_check.setStyleSheet(
            "QPushButton {background:#1d4ed8; color:white; font-size:16px; font-weight:700; "
            "padding:12px 20px; border:none; border-radius:10px;}"
            "QPushButton:disabled {background:#93c5fd;}"
        )
        self.btn_check.clicked.connect(self.check_for_updates)
        btn_row.addWidget(self.btn_check)

        self.btn_close = QtWidgets.QPushButton("Cerrar")
        self.btn_close.setStyleSheet(
            "QPushButton {background:#e5e7eb; color:#111827; font-size:16px; font-weight:700; "
            "padding:12px 20px; border:none; border-radius:10px;}"
        )
        self.btn_close.clicked.connect(self.close)
        btn_row.addWidget(self.btn_close)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

    def _set_busy(self, busy: bool, text: str = ""):
        self.btn_check.setDisabled(busy)
        self.btn_close.setDisabled(busy)
        self.btn_check.setText("Verificando..." if busy else "Buscar actualizacion")
        if text:
            self.status_label.setText(text)
        QtWidgets.QApplication.processEvents()

    def check_for_updates(self):
        self._set_busy(True, "Consultando servidor...")
        try:
            response = requests.get(UPDATE_INFO_URL, timeout=15)
            response.raise_for_status()
            data = parse_update_manifest_text(response.text)
            remote_version = str(
                data.get("V")
                or data.get("v")
                or data.get("version")
                or data.get("latest_version")
                or data.get("app_version")
                or ""
            ).strip()
            download_url = str(
                data.get("enlace")
                or data.get("download_url")
                or data.get("exe_url")
                or data.get("url")
                or data.get("link")
                or ""
            ).strip()
            if not remote_version:
                raise ValueError("El servidor no envio la version remota.")

            if not is_remote_version_newer(self.local_version, remote_version):
                self._set_busy(False, f"No hay actualizacion. Local={self.local_version} Remota={remote_version}")
                QtWidgets.QMessageBox.information(
                    self,
                    "Actualizacion",
                    f"No hay actualizacion disponible.\n\nVersion local: {self.local_version}\nVersion remota: {remote_version}"
                )
                return

            self._set_busy(False, f"Actualizacion encontrada: {remote_version}")
            answer = QtWidgets.QMessageBox.question(
                self,
                "Actualizacion disponible",
                f"Version local: {self.local_version}\nVersion remota: {remote_version}\n\nDeseas descargar y reemplazar este ejecutable de prueba?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if answer == QtWidgets.QMessageBox.Yes:
                self.start_external_update_flow(download_url, remote_version)
        except Exception as exc:
            self._set_busy(False, f"Error verificando actualizacion: {exc}")
            QtWidgets.QMessageBox.warning(self, "Actualizacion", f"No se pudo verificar la actualizacion:\n{exc}")

    def get_current_binary_path(self) -> str:
        return os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])

    def can_self_update_current_runtime(self) -> bool:
        target_file_path = self.get_current_binary_path()
        return bool(getattr(sys, "frozen", False)) and target_file_path.lower().endswith(".exe")

    def build_update_helper_bat(self, downloaded_file_path, target_file_path):
        app_dir = os.path.dirname(target_file_path)
        helper_path = os.path.join(app_dir, "Actualizacion VISO.bat")
        helper_lines = [
            "@echo off",
            "setlocal enableextensions",
            f"set \"SOURCE_FILE={os.path.normpath(downloaded_file_path)}\"",
            f"set \"TARGET_FILE={os.path.normpath(target_file_path)}\"",
            f"set \"TARGET_PID={os.getpid()}\"",
            "",
            ":waitclose",
            "tasklist /FI \"PID eq %TARGET_PID%\" | find \"%TARGET_PID%\" >nul",
            "if not errorlevel 1 (",
            "    timeout /t 1 /nobreak >nul",
            "    goto waitclose",
            ")",
            "",
            ":deleteold",
            "if exist \"%TARGET_FILE%\" (",
            "    del /F /Q \"%TARGET_FILE%\" >nul 2>&1",
            "    timeout /t 1 /nobreak >nul",
            "    goto deleteold",
            ")",
            "",
            "copy /Y \"%SOURCE_FILE%\" \"%TARGET_FILE%\" >nul",
            "if exist \"%TARGET_FILE%\" (",
            "    start \"\" \"%TARGET_FILE%\"",
            ")",
            "exit /b 0",
        ]
        with open(helper_path, "w", encoding="utf-8", newline="\r\n") as bat_file:
            bat_file.write("\r\n".join(helper_lines) + "\r\n")
        return helper_path

    def validate_downloaded_executable(self, downloaded_file_path):
        if not os.path.exists(downloaded_file_path):
            raise ValueError("La descarga no existe.")
        file_size = os.path.getsize(downloaded_file_path)
        if file_size <= 0:
            raise ValueError("La descarga llego vacia.")
        with open(downloaded_file_path, "rb") as downloaded_file:
            signature = downloaded_file.read(2)
        if signature != b"MZ":
            raise ValueError(
                "El archivo descargado no es un ejecutable Windows valido.\n"
                "Se bloqueo el reemplazo para proteger el sistema."
            )

    def download_update_file(self, download_url, remote_version):
        if not download_url:
            raise ValueError("El servidor no envio el enlace de descarga.")
        parsed = urlparse(download_url)
        file_name = os.path.basename(parsed.path or "").strip() or f"update_test_{remote_version or 'nuevo'}.bin"
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        destination_path = os.path.join(downloads_dir, file_name)
        base_name, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(destination_path):
            destination_path = os.path.join(downloads_dir, f"{base_name}_{counter}{ext or '.bin'}")
            counter += 1

        response = requests.get(download_url, timeout=30, stream=True)
        response.raise_for_status()
        with open(destination_path, "wb") as downloaded_file:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    downloaded_file.write(chunk)
        return destination_path

    def start_external_update_flow(self, download_url, remote_version):
        if not self.can_self_update_current_runtime():
            raise ValueError("Este tester solo debe auto-actualizarse cuando este compilado como .exe.")

        target_file_path = self.get_current_binary_path()
        if not os.path.exists(target_file_path):
            raise ValueError(f"No se encontro el ejecutable actual:\n{target_file_path}")

        self._set_busy(True, "Descargando archivo de actualizacion...")
        try:
            downloaded_file_path = self.download_update_file(download_url, remote_version)
            self.validate_downloaded_executable(downloaded_file_path)
            helper_bat_path = self.build_update_helper_bat(downloaded_file_path, target_file_path)
        finally:
            self._set_busy(False)

        answer = QtWidgets.QMessageBox.question(
            self,
            "Actualizacion lista",
            "La descarga termino.\n\nSe cerrara este tester para ejecutar 'Actualizacion VISO.bat' y reemplazar este .exe.\n\nContinuar?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return

        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", helper_bat_path],
            cwd=os.path.dirname(helper_bat_path) or None,
        )
        QtCore.QTimer.singleShot(200, self.close)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = UpdateTestWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
