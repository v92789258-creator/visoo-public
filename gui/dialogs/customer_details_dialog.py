"""
Dialogo de detalles de cliente con interfaz PyQt5 pura.
"""

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal

from utils.file_handler import (
    cargar_clientes,
    cargar_etiquetas_clientes,
    guardar_clientes,
    guardar_etiquetas_clientes,
)


class CustomerDetailsDialog(QtWidgets.QDialog):
    """Dialogo para ver y editar detalles de un cliente."""

    cliente_eliminado = pyqtSignal(str)

    def __init__(self, cliente_data, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.cliente_data = dict(cliente_data or {})
        self.username = getattr(parent, "username", None)
        self._dni_original = str(self.cliente_data.get("dni", "")).strip()

        self.can_edit = True
        self.can_delete = True
        if self.parent_app and getattr(self.parent_app, "is_helper", False):
            self.can_edit = bool(self.parent_app.puede_hacer_accion("clientes", "editar"))
            self.can_delete = bool(self.parent_app.puede_hacer_accion("clientes", "eliminar"))

        self.available_tags = cargar_etiquetas_clientes(self.username)
        self.selected_tags = self._normalizar_etiquetas(self.cliente_data.get("etiquetas", []))
        self.form_data = self._build_form_data()

        nombre = str(self.cliente_data.get("nombre", "Cliente") or "Cliente").strip()
        self.setWindowTitle(f"Detalles del Cliente - {nombre}")
        self.setModal(True)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(900, 690)

        self._apply_styles()
        self._build_ui()
        self._load_form_data()
        self._refresh_tags_list()

    def _apply_styles(self):
        self.setObjectName("CustomerDetailsDialog")
        self.setStyleSheet(
            """
            QDialog#CustomerDetailsDialog {
                background: #F4F7FB;
            }
            QFrame#surface {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
            QFrame#headerSurface {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 18px;
            }
            QFrame#metaSurface {
                background: #F8FAFD;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QFrame#sectionCard {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel#eyebrow {
                color: #5B6B81;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }
            QLabel#dialogTitle {
                color: #122033;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#dialogSubtitle {
                color: #667085;
                font-size: 13px;
            }
            QLabel#metaCaption {
                color: #667085;
                font-size: 11px;
            }
            QLabel#metaValue {
                color: #122033;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#statusChipEditable {
                background: #EEF4FF;
                color: #1D4ED8;
                border: 1px solid #C7D7FE;
                border-radius: 12px;
                padding: 6px 12px;
                font-weight: 700;
            }
            QLabel#statusChipReadonly {
                background: #FFF7ED;
                color: #C2410C;
                border: 1px solid #FED7AA;
                border-radius: 12px;
                padding: 6px 12px;
                font-weight: 700;
            }
            QLabel#sectionTitle {
                color: #122033;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#sectionSubtitle {
                color: #667085;
                font-size: 12px;
            }
            QLabel#fieldLabel {
                color: #344054;
                font-size: 12px;
                font-weight: 600;
            }
            QTabWidget::pane {
                border: 0;
                background: transparent;
            }
            QTabBar::tab {
                background: #EEF2F7;
                border: 1px solid #D8E1EC;
                border-bottom: 0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 10px 18px;
                margin-right: 8px;
                color: #42526B;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #1D4ED8;
            }
            QLineEdit, QTextEdit, QListWidget {
                background: #F9FBFD;
                border: 1px solid #D6E0EC;
                border-radius: 10px;
                color: #122033;
                padding: 8px 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QListWidget:focus {
                background: #FFFFFF;
                border: 1px solid #4C84FF;
            }
            QListWidget::item {
                padding: 6px 4px;
            }
            QPushButton {
                min-height: 40px;
                border-radius: 10px;
                padding: 0 18px;
                font-weight: 600;
            }
            QPushButton#primaryButton {
                background: #1D4ED8;
                color: #FFFFFF;
                border: 0;
            }
            QPushButton#primaryButton:disabled {
                background: #A6B8DD;
                color: #FFFFFF;
            }
            QPushButton#secondaryButton {
                background: #FFFFFF;
                color: #344054;
                border: 1px solid #D8E1EC;
            }
            QPushButton#dangerButton {
                background: #FFF5F4;
                color: #B42318;
                border: 1px solid #F3B4AF;
            }
            """
        )

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        main_layout.addWidget(self._build_header())

        content_frame = QtWidgets.QFrame()
        content_frame.setObjectName("surface")
        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabs.addTab(self._wrap_tab_scroll(self._build_info_tab()), "Informacion")
        self.tabs.addTab(self._wrap_tab_scroll(self._build_contact_tab()), "Contacto")
        self.tabs.addTab(self._wrap_tab_scroll(self._build_additional_tab()), "Adicional")
        content_layout.addWidget(self.tabs)

        main_layout.addWidget(content_frame, 1)
        main_layout.addWidget(self._build_footer())

    def _build_header(self):
        frame = QtWidgets.QFrame()
        frame.setObjectName("headerSurface")
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(4)

        eyebrow = QtWidgets.QLabel("Ficha de cliente")
        eyebrow.setObjectName("eyebrow")
        left_col.addWidget(eyebrow)

        title = QtWidgets.QLabel(str(self.cliente_data.get("nombre", "Cliente") or "Cliente"))
        title.setObjectName("dialogTitle")
        title.setWordWrap(True)
        left_col.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Edita la informacion del cliente, revisa sus datos de contacto y guarda los cambios."
            if self.can_edit
            else "Esta ficha esta abierta en modo solo lectura por permisos del usuario."
        )
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)
        left_col.addWidget(subtitle)
        left_col.addStretch(1)

        layout.addLayout(left_col, 1)

        meta_frame = QtWidgets.QFrame()
        meta_frame.setObjectName("metaSurface")
        meta_frame.setFixedWidth(260)
        meta_layout = QtWidgets.QGridLayout(meta_frame)
        meta_layout.setContentsMargins(14, 14, 14, 14)
        meta_layout.setHorizontalSpacing(12)
        meta_layout.setVerticalSpacing(8)

        meta_layout.addWidget(self._make_meta_caption("DNI"), 0, 0)
        meta_layout.addWidget(self._make_meta_caption("Registro"), 0, 1)
        meta_layout.addWidget(
            self._make_meta_value(self.form_data.get("dni") or "Sin DNI"), 1, 0
        )
        meta_layout.addWidget(
            self._make_meta_value(self.form_data.get("fecha_registro") or "Sin fecha"), 1, 1
        )

        layout.addWidget(meta_frame, 0, QtCore.Qt.AlignTop)
        return frame

    def _build_info_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        self.input_nombre = self._make_line_edit("Nombre completo")
        self.input_dni = self._make_line_edit("Documento")
        self.input_genero = self._make_line_edit("Genero")
        self.input_edad = self._make_line_edit("Edad")
        self.input_fecha_nacimiento = self._make_line_edit("dd/mm/aaaa")
        self.input_fecha_registro = self._make_line_edit("dd/mm/aaaa")

        card, body = self._create_section_card(
            "Informacion principal",
            "Datos base para identificar al cliente y mantener su registro ordenado.",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.addWidget(self._wrap_field("Nombre", self.input_nombre), 0, 0)
        grid.addWidget(self._wrap_field("Edad", self.input_edad), 0, 1)
        grid.addWidget(self._wrap_field("DNI", self.input_dni), 1, 0)
        grid.addWidget(self._wrap_field("Fecha nacimiento", self.input_fecha_nacimiento), 1, 1)
        grid.addWidget(self._wrap_field("Genero", self.input_genero), 2, 0)
        grid.addWidget(self._wrap_field("Fecha registro", self.input_fecha_registro), 2, 1)
        body.addLayout(grid)

        layout.addWidget(card)
        layout.addStretch(1)
        return tab

    def _build_contact_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        self.input_telefono = self._make_line_edit("Telefono")
        self.input_correo = self._make_line_edit("Correo")
        self.input_direccion = self._make_line_edit("Direccion")
        self.input_empresa = self._make_line_edit("Empresa")

        card, body = self._create_section_card(
            "Contacto y negocio",
            "Informacion util para seguimiento comercial y comunicacion con el cliente.",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        grid.addWidget(self._wrap_field("Telefono", self.input_telefono), 0, 0)
        grid.addWidget(self._wrap_field("Correo", self.input_correo), 0, 1)
        grid.addWidget(self._wrap_field("Direccion", self.input_direccion), 1, 0)
        grid.addWidget(self._wrap_field("Empresa", self.input_empresa), 1, 1)
        body.addLayout(grid)

        layout.addWidget(card)
        layout.addStretch(1)
        return tab

    def _build_additional_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        self.tags_list = QtWidgets.QListWidget()
        self.tags_list.setMinimumHeight(180)
        self.tags_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tags_list.setDisabled(not self.can_edit)

        self.new_tag_input = self._make_line_edit("Nueva etiqueta")
        self.new_tag_input.returnPressed.connect(self._handle_add_tag)
        self.add_tag_button = QtWidgets.QPushButton("Agregar etiqueta")
        self.add_tag_button.setObjectName("secondaryButton")
        self.add_tag_button.setEnabled(self.can_edit)
        self.add_tag_button.clicked.connect(self._handle_add_tag)

        tags_card, tags_body = self._create_section_card(
            "Etiquetas",
            "Marca contexto comercial o administrativo para organizar mejor al cliente.",
        )
        tags_body.addWidget(self.tags_list)

        tag_row = QtWidgets.QHBoxLayout()
        tag_row.setSpacing(10)
        tag_row.addWidget(self.new_tag_input, 1)
        tag_row.addWidget(self.add_tag_button)
        tags_body.addLayout(tag_row)

        self.input_notas = QtWidgets.QTextEdit()
        self.input_notas.setMinimumHeight(150)
        self.input_notas.setReadOnly(not self.can_edit)

        notes_card, notes_body = self._create_section_card(
            "Notas internas",
            "Apuntes utiles para seguimiento, observaciones o acuerdos con el cliente.",
        )
        notes_body.addWidget(self.input_notas)

        layout.addWidget(tags_card)
        layout.addWidget(notes_card)

        if self.can_delete:
            delete_row = QtWidgets.QHBoxLayout()
            delete_row.addStretch(1)
            self.delete_button = QtWidgets.QPushButton("Eliminar cliente")
            self.delete_button.setObjectName("dangerButton")
            self.delete_button.clicked.connect(self.eliminar_cliente)
            delete_row.addWidget(self.delete_button)
            layout.addLayout(delete_row)

        layout.addStretch(1)
        return tab

    def _build_footer(self):
        frame = QtWidgets.QFrame()
        frame.setObjectName("surface")
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        hint = QtWidgets.QLabel(
            "Los cambios se guardan directamente en la ficha del cliente."
            if self.can_edit
            else "Modo solo lectura. Puedes revisar la informacion, pero no modificarla."
        )
        hint.setObjectName("dialogSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint, 1)

        self.close_button = QtWidgets.QPushButton("Cerrar")
        self.close_button.setObjectName("secondaryButton")
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)

        self.save_button = QtWidgets.QPushButton("Guardar cambios")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setEnabled(self.can_edit)
        self.save_button.clicked.connect(self._save_changes)
        layout.addWidget(self.save_button)

        return frame

    def _wrap_tab_scroll(self, inner_widget: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner_widget)
        return scroll

    def _make_meta_caption(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("metaCaption")
        return label

    def _make_meta_value(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("metaValue")
        label.setWordWrap(True)
        return label

    def _create_section_card(self, title_text, subtitle_text):
        frame = QtWidgets.QFrame()
        frame.setObjectName("sectionCard")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(subtitle_text)
        subtitle.setObjectName("sectionSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        body = QtWidgets.QVBoxLayout()
        body.setSpacing(10)
        layout.addLayout(body)
        return frame, body

    def _wrap_field(self, label_text, editor):
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QtWidgets.QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(editor)
        return wrapper

    def _make_line_edit(self, placeholder=""):
        line = QtWidgets.QLineEdit()
        line.setPlaceholderText(placeholder)
        line.setReadOnly(not self.can_edit)
        return line

    def _load_form_data(self):
        self.input_nombre.setText(self.form_data.get("nombre", ""))
        self.input_dni.setText(self.form_data.get("dni", ""))
        self.input_edad.setText(self.form_data.get("edad", ""))
        self.input_genero.setText(self.form_data.get("genero", ""))
        self.input_fecha_nacimiento.setText(self.form_data.get("fecha_nacimiento", ""))
        self.input_fecha_registro.setText(self.form_data.get("fecha_registro", ""))
        self.input_telefono.setText(self.form_data.get("telefono", ""))
        self.input_correo.setText(self.form_data.get("correo", ""))
        self.input_direccion.setText(self.form_data.get("direccion", ""))
        self.input_empresa.setText(self.form_data.get("empresa", ""))
        self.input_notas.setPlainText(self.form_data.get("notas", ""))

    def _current_selected_tags(self):
        if not hasattr(self, "tags_list"):
            return list(self.selected_tags)

        resultado = []
        for i in range(self.tags_list.count()):
            item = self.tags_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                resultado.append(item.text())
        return self._normalizar_etiquetas(resultado)

    def _refresh_tags_list(self, selected=None):
        if selected is None:
            selected = list(self.selected_tags)
        selected_map = {str(tag).casefold() for tag in selected}

        self.tags_list.clear()
        for tag in self.available_tags:
            item = QtWidgets.QListWidgetItem(str(tag))
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
            item.setFlags(flags)
            item.setCheckState(
                QtCore.Qt.Checked if str(tag).casefold() in selected_map else QtCore.Qt.Unchecked
            )
            self.tags_list.addItem(item)

    def _handle_add_tag(self):
        if not self.can_edit:
            return

        nueva = str(self.new_tag_input.text() or "").strip()
        if not nueva:
            return

        selected = self._current_selected_tags()
        if self.create_tag(nueva):
            selected.append(nueva)
            self.selected_tags = self._normalizar_etiquetas(selected)
            self._refresh_tags_list(self.selected_tags)
            self.new_tag_input.clear()

    def _collect_payload(self):
        return {
            "nombre": self.input_nombre.text(),
            "dni": self.input_dni.text(),
            "edad": self.input_edad.text(),
            "genero": self.input_genero.text(),
            "fecha_nacimiento": self.input_fecha_nacimiento.text(),
            "fecha_registro": self.input_fecha_registro.text(),
            "telefono": self.input_telefono.text(),
            "correo": self.input_correo.text(),
            "direccion": self.input_direccion.text(),
            "empresa": self.input_empresa.text(),
            "notas": self.input_notas.toPlainText(),
            "tags_csv": ", ".join(self._current_selected_tags()),
        }

    def _save_changes(self):
        self.save_customer(self._collect_payload())

    def _build_form_data(self):
        return {
            "nombre": str(self.cliente_data.get("nombre", "") or ""),
            "dni": str(self.cliente_data.get("dni", "") or ""),
            "edad": self._procesar_edad(self.cliente_data.get("edad", "")),
            "genero": str(self.cliente_data.get("genero", "") or ""),
            "fecha_nacimiento": self._formatear_fecha(self.cliente_data.get("fecha_nacimiento", "")),
            "fecha_registro": self._formatear_fecha(self.cliente_data.get("fecha_registro", "")),
            "telefono": str(self.cliente_data.get("telefono", "") or ""),
            "correo": str(self.cliente_data.get("correo", "") or ""),
            "direccion": str(self.cliente_data.get("direccion", "") or ""),
            "empresa": str(self.cliente_data.get("empresa", "") or ""),
            "notas": str(self.cliente_data.get("notas", "") or ""),
        }

    def _procesar_edad(self, edad_valor):
        """Si la edad viene como fecha, la convierte a anos."""
        try:
            if isinstance(edad_valor, (int, float)):
                return str(int(edad_valor))

            edad_str = str(edad_valor or "").strip()
            if not edad_str:
                return ""

            try:
                return str(int(float(edad_str)))
            except ValueError:
                pass

            if any(sep in edad_str for sep in ["-", "/", " "]):
                fecha_obj = self._parse_fecha(edad_str)
                if fecha_obj:
                    hoy = datetime.datetime.now()
                    edad = hoy.year - fecha_obj.year - (
                        (hoy.month, hoy.day) < (fecha_obj.month, fecha_obj.day)
                    )
                    return str(edad)

            return edad_str
        except Exception:
            return str(edad_valor or "")

    def _formatear_fecha(self, fecha_valor):
        if not fecha_valor:
            return ""
        try:
            fecha_str = str(fecha_valor).strip()
            if "/" in fecha_str and len(fecha_str) == 10:
                return fecha_str
            fecha_obj = self._parse_fecha(fecha_str)
            if fecha_obj:
                return fecha_obj.strftime("%d/%m/%Y")
            return fecha_str
        except Exception:
            return str(fecha_valor or "")

    def _parse_fecha(self, fecha_str):
        try:
            txt = str(fecha_str or "").strip()
            if " " in txt:
                txt = txt.split(" ")[0]
            formatos = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
            ]
            for fmt in formatos:
                try:
                    return datetime.datetime.strptime(txt, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _normalizar_etiquetas(self, tags):
        if isinstance(tags, str):
            tags = [p.strip() for p in tags.split(",") if p.strip()]
        if not isinstance(tags, list):
            tags = []

        resultado = []
        vistos = set()
        for tag in tags:
            txt = str(tag or "").strip()
            if not txt:
                continue
            key = txt.casefold()
            if key in vistos:
                continue
            vistos.add(key)
            resultado.append(txt)
        return resultado

    def _parse_tags_csv(self, tags_csv):
        return self._normalizar_etiquetas(str(tags_csv or ""))

    def create_tag(self, tag_text):
        """Crea una etiqueta global para clientes y la persiste."""
        if not self.can_edit:
            QtWidgets.QMessageBox.warning(
                self, "Permiso Denegado", "No tienes permiso para crear etiquetas."
            )
            return False

        nueva = str(tag_text or "").strip()
        if not nueva:
            return False

        if any(t.casefold() == nueva.casefold() for t in self.available_tags):
            QtWidgets.QMessageBox.information(self, "Etiqueta repetida", "Esa etiqueta ya existe.")
            return False

        updated = list(self.available_tags) + [nueva]
        if not guardar_etiquetas_clientes(self.username, updated):
            QtWidgets.QMessageBox.warning(self, "Error", "No se pudo guardar la etiqueta.")
            return False

        self.available_tags = cargar_etiquetas_clientes(self.username)
        return True

    def save_customer(self, payload):
        """Guarda cambios enviados desde el formulario."""
        if not self.can_edit:
            QtWidgets.QMessageBox.warning(
                self, "Permiso Denegado", "No tienes permiso para editar clientes."
            )
            return False

        try:
            nombre = str(payload.get("nombre", "") or "").strip()
            dni = str(payload.get("dni", "") or "").strip()
            if not nombre or not dni:
                QtWidgets.QMessageBox.warning(
                    self, "Campos obligatorios", "Nombre y DNI son obligatorios."
                )
                return False

            clientes = cargar_clientes(self.username)
            idx_obj = -1
            for i, cliente in enumerate(clientes):
                if str(cliente.get("dni", "")).strip() == self._dni_original:
                    idx_obj = i
                    break

            if idx_obj < 0:
                QtWidgets.QMessageBox.warning(
                    self, "Error", "No se encontro el cliente original en la base de datos."
                )
                return False

            for i, cliente in enumerate(clientes):
                if i == idx_obj:
                    continue
                if str(cliente.get("dni", "")).strip() == dni:
                    QtWidgets.QMessageBox.warning(
                        self, "DNI duplicado", f"Ya existe otro cliente con DNI {dni}."
                    )
                    return False

            etiquetas = self._parse_tags_csv(payload.get("tags_csv", ""))
            cliente_actualizado = dict(self.cliente_data)
            cliente_actualizado["nombre"] = nombre
            cliente_actualizado["dni"] = dni
            cliente_actualizado["edad"] = str(payload.get("edad", "") or "").strip()
            cliente_actualizado["genero"] = str(payload.get("genero", "") or "").strip()
            cliente_actualizado["fecha_nacimiento"] = str(
                payload.get("fecha_nacimiento", "") or ""
            ).strip()
            cliente_actualizado["fecha_registro"] = str(
                payload.get("fecha_registro", "") or ""
            ).strip()
            cliente_actualizado["telefono"] = str(payload.get("telefono", "") or "").strip()
            cliente_actualizado["correo"] = str(payload.get("correo", "") or "").strip()
            cliente_actualizado["direccion"] = str(payload.get("direccion", "") or "").strip()
            cliente_actualizado["empresa"] = str(payload.get("empresa", "") or "").strip()
            cliente_actualizado["notas"] = str(payload.get("notas", "") or "").strip()
            cliente_actualizado["etiquetas"] = etiquetas

            clientes[idx_obj] = cliente_actualizado
            guardar_clientes(self.username, clientes)

            self.cliente_data = cliente_actualizado
            self._dni_original = dni
            self.selected_tags = etiquetas

            try:
                from utils.data_cache_manager import get_global_cache

                cache = get_global_cache()
                cache.clear_data_type(self.username, "clientes")
            except Exception:
                pass

            QtWidgets.QMessageBox.information(self, "Exito", "Cambios guardados correctamente.")
            self.accept()
            return True
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Error al guardar cambios: {str(exc)}"
            )
            return False

    def eliminar_cliente(self):
        """Elimina el cliente despues de confirmacion."""
        if not self.can_delete:
            QtWidgets.QMessageBox.warning(
                self, "Permiso Denegado", "No tienes permiso para eliminar clientes."
            )
            return

        nombre = str(self.cliente_data.get("nombre", "Desconocido") or "Desconocido")
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirmar Eliminacion",
            f"Estas seguro de eliminar al cliente '{nombre}'?\n\nEsta accion no se puede deshacer.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            deleted_dni = str(self._dni_original).strip()
            clientes = cargar_clientes(self.username)
            clientes = [
                cliente
                for cliente in clientes
                if str(cliente.get("dni", "")).strip() != deleted_dni
            ]
            guardar_clientes(self.username, clientes)

            try:
                from utils.data_cache_manager import get_global_cache

                cache = get_global_cache()
                cache.clear_data_type(self.username, "clientes")
            except Exception:
                pass

            self.cliente_eliminado.emit(deleted_dni)
            QtWidgets.QMessageBox.information(
                self, "Cliente Eliminado", f"El cliente '{nombre}' fue eliminado."
            )
            self.accept()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"No se pudo eliminar cliente: {str(exc)}"
            )
