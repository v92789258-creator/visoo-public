# -*- coding: utf-8 -*-
import os
import datetime
import tempfile
import json
import re
import subprocess
import base64
from PyQt5.QtWidgets import QMessageBox
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def _safe_float_payment(value) -> float:
    try:
        if value is None: return 0.0
        text = str(value).replace("S/", "").replace("S/.", "").replace(",", "").strip()
        return float(text)
    except Exception:
        return 0.0

def _graduacion_service_amount(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    return _safe_float_payment(graduacion.get("monto_cobrado", 0))

def _graduacion_items_total(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    total_items, _service_items_total, _product_items_total = _graduacion_items_breakdown(graduacion)
    return total_items

def _graduacion_items_breakdown(graduacion):
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    total_items = 0.0
    service_items_total = 0.0
    product_items_total = 0.0
    for item in graduacion.get("items_venta", []) or []:
        if not isinstance(item, dict):
            continue
        cantidad = _safe_float_payment(item.get("cantidad", 1)) or 1.0
        precio = _safe_float_payment(item.get("precio_unitario", item.get("precio", 0)))
        item_total = _safe_float_payment(item.get("subtotal", item.get("total", precio * cantidad)))
        total_items += item_total
        nombre = str(item.get("producto") or item.get("nombre") or "").strip().lower()
        if "servicio de gradu" in nombre or nombre == "graduacion":
            service_items_total += item_total
        else:
            product_items_total += item_total
    return total_items, service_items_total, product_items_total

def _graduacion_items_include_service(graduacion) -> bool:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    for item in graduacion.get("items_venta", []) or []:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("producto") or item.get("nombre") or "").strip().lower()
        if "servicio de gradu" in nombre or nombre == "graduacion":
            return True
    return False

def _graduacion_total_amount(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    stored_total = _safe_float_payment(graduacion.get("monto_total_venta", 0))
    monto_servicio = _graduacion_service_amount(graduacion)
    total_items, service_items_total, product_items_total = _graduacion_items_breakdown(graduacion)
    if total_items > 0.01:
        if _graduacion_items_include_service(graduacion):
            if monto_servicio > 0.01 and abs(service_items_total - monto_servicio) > 0.05:
                return monto_servicio + product_items_total
            return total_items
        if monto_servicio > 0.01:
            return monto_servicio + total_items
        return total_items
    if stored_total > 0.01:
        return stored_total
    return monto_servicio

def build_contract_number(paciente_data, graduacion, grad_index=None):
    existing = str((graduacion or {}).get("contrato_numero", "") or "").strip()
    if existing:
        return existing

    dni_digits = "".join(filter(str.isdigit, str((paciente_data or {}).get("dni", "") or "")))
    dni_tail = (dni_digits[-3:] if dni_digits else "000").rjust(3, "0")
    seq = (grad_index + 1) if isinstance(grad_index, int) and grad_index >= 0 else 1
    return f"{seq:03d}{dni_tail}"

def resolve_contract_patient_and_graduacion(username, contract_number="", preferred_dni="", raw_grad=None):
    from utils.file_handler import cargar_pacientes

    contract_number = str(contract_number or "").strip()
    preferred_dni = str(preferred_dni or "").strip()
    raw_grad = raw_grad if isinstance(raw_grad, dict) else None

    pacientes = cargar_pacientes(username) or []
    paciente_match = {}
    grad_match = raw_grad
    grad_index = None

    for paciente in pacientes:
        if not isinstance(paciente, dict):
            continue
        dni = str(paciente.get("dni", "") or "").strip()
        historial = paciente.get("historial_graduaciones", []) or []
        for idx, grad in enumerate(historial):
            if not isinstance(grad, dict):
                continue
            same_contract = contract_number and str(grad.get("contrato_numero", "") or "").strip() == contract_number
            same_grad = raw_grad is not None and (grad is raw_grad or grad == raw_grad)
            if not same_contract and not same_grad:
                continue
            if preferred_dni and dni != preferred_dni and same_contract and not same_grad:
                continue
            paciente_match = paciente
            grad_match = grad
            grad_index = idx
            break
        if grad_match is not None and paciente_match:
            break

    if not paciente_match and preferred_dni:
        paciente_match = next(
            (p for p in pacientes if isinstance(p, dict) and str(p.get("dni", "") or "").strip() == preferred_dni),
            {},
        )

    return paciente_match or {}, grad_match or {}, grad_index

def _graduacion_payment_summary(graduacion):
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    monto_total = _graduacion_total_amount(graduacion)
    pagos_originales = graduacion.get("pagos_parciales", []) or []
    pagos_visibles = []
    total_pagado = 0.0

    if isinstance(pagos_originales, list) and pagos_originales:
        for pago in pagos_originales:
            pago = pago if isinstance(pago, dict) else {}
            monto = _safe_float_payment(pago.get("monto", 0))
            total_pagado += monto
            pagos_visibles.append({
                "monto": monto,
                "fecha": str(pago.get("fecha", "") or ""),
                "observacion": str(pago.get("observacion", "") or ""),
            })
    else:
        adelanto = _safe_float_payment(graduacion.get("monto_adelanto", 0))
        if adelanto > 0.01:
            total_pagado = adelanto
            pagos_visibles.append({
                "monto": adelanto,
                "fecha": str(graduacion.get("fecha", "") or ""),
                "observacion": "Adelanto inicial",
            })
        elif str(graduacion.get("estado", "") or "").strip().lower() == "completada" and monto_total > 0:
            total_pagado = monto_total
            pagos_visibles.append({
                "monto": monto_total,
                "fecha": str(graduacion.get("fecha", "") or ""),
                "observacion": "Pago completo registrado",
            })

    saldo = max(0.0, monto_total - total_pagado)
    return {
        "monto_total": monto_total,
        "total_pagado": total_pagado,
        "saldo": saldo,
        "pagos": pagos_visibles,
    }

def _build_contract_products_summary(graduacion):
    items = (graduacion or {}).get("items_venta", []) or []
    names = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre", "") or "").strip()
        if nombre:
            names.append(nombre)
    return names


def _is_contract_annulled(graduacion) -> bool:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    estado_anulacion = str(graduacion.get("estado_anulacion", "") or "").strip().lower()
    return bool(
        graduacion.get("contrato_anulado")
        or graduacion.get("anulado")
        or estado_anulacion == "anulado"
    )


def _find_chrome_executable():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in chrome_paths:
        if os.path.exists(candidate):
            return candidate
    return None


def _build_contract_rendered_html(paciente_data, graduacion, nombre_optica, username, contract_number):
    from utils.file_handler import cargar_datos_optica, get_user_file_path, obtener_ruta_recurso

    template_html_path = os.path.join(os.getcwd(), "DISEÑOSPDF", "contrato.html")
    template_html_path = obtener_ruta_recurso("DISE\u00d1OSPDF", "contrato.html")
    if not os.path.exists(template_html_path):
        raise FileNotFoundError("No se encontró DISEÑOSPDF/contrato.html")

    with open(template_html_path, "r", encoding="utf-8", errors="replace") as tpl_file:
        template_html = tpl_file.read()
    if "Ã" in template_html:
        try:
            template_html = template_html.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            pass

    # Cargar datos de la óptica de forma robusta (preferencia remota para usuarios como NANCY)
    optica_data = {}
    try:
        optica_data = cargar_datos_optica(username, prefer_remote=True) or {}
    except Exception:
        optica_data = {}

    nombre_optica_real = str(optica_data.get("nombre_optica") or nombre_optica or "Mi Óptica").strip()
    slogan_optica = str(optica_data.get("slogan", "") or "").strip()
    direccion_optica = str(optica_data.get("direccion", "") or "").strip()
    correo_optica = str(optica_data.get("correo_electronico", "") or "").strip()
    telefono_optica = str(optica_data.get("whatsapp", "") or "").strip()

    logo_html = ""
    try:
        logo_path = str(get_user_file_path(username, "logo.png"))
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as logo_file:
                logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
            logo_html = (
                f'<img src="data:image/png;base64,{logo_b64}" '
                'style="max-width:120px;max-height:120px;display:block;margin:0 auto 8px;" alt="Logo">'
            )
    except Exception:
        logo_html = ""

    fecha = str(graduacion.get("fecha", "") or datetime.date.today().strftime("%d/%m/%Y"))
    paciente_nombre = str(paciente_data.get("nombre", "") or "N/A")
    paciente_tel = str(paciente_data.get("telefono", "") or "")
    paciente_dir = str(paciente_data.get("direccion", "") or "")
    vendedor = str(graduacion.get("optometra", "") or username or "")
    observacion = str(graduacion.get("observacion", "") or "")
    proxima_cita = str(graduacion.get("proxima_cita", "") or "")

    productos = _build_contract_products_summary(graduacion)
    payment = _graduacion_payment_summary(graduacion)
    total = payment["monto_total"]
    acuenta = payment["total_pagado"]
    saldo = payment["saldo"]

    montura = ""
    cristales = str(graduacion.get("cristales", "") or "").strip()
    resina_text = str(graduacion.get("resina", "") or "").strip()
    color_text = str(graduacion.get("color", "") or "").strip()
    bifocal_text = str(graduacion.get("bifocal_tipo", "") or "").strip()
    multifocal_text = str(graduacion.get("multifocal_tipo", "") or "").strip()
    altura_text = str(graduacion.get("altura", "") or "").strip()

    for nombre in productos:
        lower = nombre.lower()
        if not montura and "montura" in lower:
            montura = nombre
            continue
        if "graduacion" in lower or "servicio" in lower or "motilidad" in lower:
            continue
        if not cristales:
            cristales = nombre

    if not montura and productos:
        montura = productos[0]
    if not cristales and len(productos) > 1:
        cristales = ", ".join(productos[1:3])
    if not multifocal_text:
        multifocal_text = ", ".join(productos[:3]) if productos else ""
    entrega = proxima_cita if proxima_cita and proxima_cita.lower() != "no" else ""

    def esc(value):
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def money(value):
        return f"S/ {float(value or 0):.2f}"

    rendered_html = template_html.replace('<button class="print-btn" onclick="window.print()">Descargar PDF</button>', "")

    if logo_html:
        rendered_html = re.sub(
            r'<div class="empresa">',
            f'{logo_html}<div class="empresa">',
            rendered_html,
            count=1,
        )

    if _is_contract_annulled(graduacion):
        watermark_css = """
        .anulado-watermark{
          position:absolute;
          left:50%;
          top:52%;
          transform:translate(-50%,-50%) rotate(-58deg);
          font-size:96px;
          font-weight:700;
          color:rgba(90,90,90,0.45);
          pointer-events:none;
          z-index:20;
          white-space:nowrap;
        }
        """
        rendered_html = rendered_html.replace("</style>", watermark_css + "\n</style>", 1)
        rendered_html = rendered_html.replace('<div class="contrato">', '<div class="contrato"><div class="anulado-watermark">ANULADO</div>', 1)

    reemplazos = {
        "Bertha Llamocca Aguayo": esc(nombre_optica_real),
        "Venta de Monturas, Gafas de sol, Lentes de Contacto": esc(slogan_optica),
        "Policarbonato en las Mejores Marcas y Repuestos en General": "",
        "LENTES INTELIGENTES - IA": esc(correo_optica),
        "Av. Bolivia N° 982 Int. 118 Galería Guimo - Lima - Lima": esc(direccion_optica),
        "TIENDA PRINCIPAL 140": "",
        "990 314 376 / 952 409 026 / 932 386 703": esc(telefono_optica),
        "N° 005388": f"N° {esc(contract_number)}",
    }
    for old, new in reemplazos.items():
        if old in rendered_html:
            rendered_html = rendered_html.replace(old, new, 1)

    # Limpiar el número de serie si es necesario (mantener 0001 si no hay otro)
    if "0001" in rendered_html:
        rendered_html = rendered_html.replace("0001", "0001", 1)

    if not correo_optica:
        rendered_html = rendered_html.replace("<h2>LENTES INTELIGENTES - IA</h2>", "<h2>&nbsp;</h2>", 1)

    # limpiar líneas extra si faltan datos de encabezado
    rendered_html = rendered_html.replace("<p></p>", "<p>&nbsp;</p>")

    rendered_html = re.sub(
        r'(<div class="label">FECHA:</div>\s*<div class="linea">)(</div>)',
        rf'\g<1>{esc(fecha)}\g<2>',
        rendered_html,
        count=1,
        flags=re.S,
    )
    rendered_html = re.sub(
        r'(<div class="label">Telf:</div>\s*<div class="linea">)(</div>)',
        rf'\g<1>{esc(paciente_tel)}\g<2>',
        rendered_html,
        count=1,
        flags=re.S,
    )
    rendered_html = re.sub(
        r'(<div class="label">Señor \(es\):</div>\s*<div class="linea">)(</div>)',
        rf'\g<1>{esc(paciente_nombre)}\g<2>',
        rendered_html,
        count=1,
        flags=re.S,
    )
    rendered_html = re.sub(
        r'(<div class="label">Dirección:</div>\s*<div class="linea">)(</div>)',
        rf'\g<1>{esc(paciente_dir)}\g<2>',
        rendered_html,
        count=1,
        flags=re.S,
    )
    rendered_html = re.sub(
        r'(<div class="label">Montura:</div>\s*<div class="linea">)(</div>)',
        rf'\g<1>{esc(montura)}\g<2>',
        rendered_html,
        count=1,
        flags=re.S,
    )

    rx_values = [
        str((graduacion.get("lejos_od", {}) or {}).get("esferico") or "—"),
        str((graduacion.get("lejos_od", {}) or {}).get("cilindro") or "—"),
        str((graduacion.get("lejos_od", {}) or {}).get("eje") or "—"),
        str((graduacion.get("lejos_od", {}) or {}).get("distp") or "—"),
        str((graduacion.get("lejos_oi", {}) or {}).get("esferico") or "—"),
        str((graduacion.get("lejos_oi", {}) or {}).get("cilindro") or "—"),
        str((graduacion.get("lejos_oi", {}) or {}).get("eje") or "—"),
        str((graduacion.get("lejos_oi", {}) or {}).get("distp") or "—"),
        str((graduacion.get("cerca_od", {}) or {}).get("esferico") or "—"),
        str((graduacion.get("cerca_od", {}) or {}).get("cilindro") or "—"),
        str((graduacion.get("cerca_od", {}) or {}).get("eje") or "—"),
        str((graduacion.get("cerca_od", {}) or {}).get("distp") or "—"),
        str((graduacion.get("cerca_oi", {}) or {}).get("esferico") or "—"),
        str((graduacion.get("cerca_oi", {}) or {}).get("cilindro") or "—"),
        str((graduacion.get("cerca_oi", {}) or {}).get("eje") or "—"),
        str((graduacion.get("cerca_oi", {}) or {}).get("distp") or "—"),
    ]
    rx_iter = iter(rx_values)
    rendered_html = re.sub(
        r'<tbody>\s*<tr><td></td><td></td><td></td><td></td></tr>\s*<tr><td></td><td></td><td></td><td></td></tr>\s*<tr><td></td><td></td><td></td><td></td></tr>\s*<tr><td></td><td></td><td></td><td></td></tr>\s*</tbody>',
        "<tbody>"
        + "".join(
            f"<tr><td>{esc(next(rx_iter, '—'))}</td><td>{esc(next(rx_iter, '—'))}</td><td>{esc(next(rx_iter, '—'))}</td><td>{esc(next(rx_iter, '—'))}</td></tr>"
            for _ in range(4)
        )
        + "</tbody>",
        rendered_html,
        count=1,
        flags=re.S,
    )

    field_map = {
        "CRISTALES:": cristales,
        "RESINA:": resina_text,
        "COLOR:": color_text,
        "BIFOCALES TIPO:": bifocal_text,
        "ALTURA:": altura_text,
        "MULTIFOCAL TIPO:": multifocal_text,
        "OTROS:": observacion,
        "VENDEDOR:": vendedor,
    }
    for label, value in field_map.items():
        rendered_html = rendered_html.replace(f"{label}</div>\n          <div class=\"linea\"></div>", f"{label}</div>\n          <div class=\"linea\">{esc(value)}</div>", 1)

    rendered_html = rendered_html.replace("ENTREGA</div>\n        <div class=\"linea-solida\"></div>", f"ENTREGA</div>\n        <div class=\"linea-solida\">{esc(entrega)}</div>", 1)
    rendered_html = rendered_html.replace("TOTAL:</div>\n        <div class=\"linea-solida\"></div>", f"TOTAL:</div>\n        <div class=\"linea-solida\">{esc(money(total))}</div>", 1)
    rendered_html = rendered_html.replace("A CTA:</div>\n        <div class=\"linea-solida\"></div>", f"A CTA:</div>\n        <div class=\"linea-solida\">{esc(money(acuenta))}</div>", 1)
    rendered_html = rendered_html.replace("SALDO:</div>\n        <div class=\"linea-solida\"></div>", f"SALDO:</div>\n        <div class=\"linea-solida\">{esc(money(saldo))}</div>", 1)

    return rendered_html

def generar_contrato_pdf_logic(
    paciente_data, 
    graduacion, 
    nombre_optica, 
    username, 
    contract_number,
    parent_widget,
    open_in_browser=False,
    return_pdf_path_only=False,
):
    """
    Lógica compartida para generar el PDF del contrato.
    Extraída de PatientDetailsDialog para ser reutilizable.
    """
    try:
        from utils.file_handler import (
            cargar_configuracion_optica,
            get_user_file_path,
            obtener_ruta_recurso,
            open_pdf_with_chrome,
        )
        from gui.dialogs.pdf_viewer_dialog import PDFViewerDialog

        chrome_exe = _find_chrome_executable()
        template_html_path = os.path.join(os.getcwd(), "DISEÑOSPDF", "contrato.html")
        template_html_path = obtener_ruta_recurso("DISE\u00d1OSPDF", "contrato.html")
        if chrome_exe and os.path.exists(template_html_path):
            rendered_html = _build_contract_rendered_html(
                paciente_data=paciente_data,
                graduacion=graduacion,
                nombre_optica=nombre_optica,
                username=username,
                contract_number=contract_number,
            )
            html_stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            # Sanitizar DNI para el nombre del archivo
            dni_safe = "".join(c for c in str(paciente_data.get('dni', '') or 'paciente') if c.isalnum())
            html_path = os.path.join(
                tempfile.gettempdir(),
                f"contrato_{dni_safe}_{html_stamp}.html"
            )
            pdf_path = os.path.join(
                tempfile.gettempdir(),
                f"contrato_{dni_safe}_{html_stamp}.pdf"
            )
            with open(html_path, "w", encoding="utf-8") as html_file:
                html_file.write(rendered_html)

            subprocess.run(
                [
                    chrome_exe,
                    "--headless=new",
                    "--disable-gpu",
                    "--allow-file-access-from-files",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.abspath(pdf_path)}",
                    os.path.abspath(html_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=90,
            )

            if return_pdf_path_only:
                return pdf_path
            if open_in_browser:
                open_pdf_with_chrome(pdf_path)
            else:
                viewer = PDFViewerDialog(pdf_path, parent_widget)
                viewer.exec_()
            return pdf_path

        optica_cfg = {}
        try:
            optica_cfg = cargar_configuracion_optica(username) or {}
        except Exception:
            optica_cfg = {}

        slogan_optica = str(optica_cfg.get("slogan", "") or "").strip()
        direccion_optica = str(optica_cfg.get("direccion", "") or "").strip()
        correo_optica = str(optica_cfg.get("correo_electronico", "") or "").strip()
        telefono_optica = ""
        try:
            whatsapp_json_path = get_user_file_path(username, "whatsapp.json")
            if whatsapp_json_path.exists():
                with open(whatsapp_json_path, "r", encoding="utf-8") as f:
                    whatsapp_data = json.load(f)
                if isinstance(whatsapp_data, dict):
                    telefono_optica = str(whatsapp_data.get("whatsapp", "") or "").strip()
        except Exception:
            telefono_optica = ""

        fecha = str(graduacion.get("fecha", "") or datetime.date.today().strftime("%d/%m/%Y"))
        paciente_nombre = str(paciente_data.get("nombre", "") or "N/A")
        paciente_dni = str(paciente_data.get("dni", "") or "")
        paciente_tel = str(paciente_data.get("telefono", "") or "")
        paciente_dir = str(paciente_data.get("direccion", "") or "")
        vendedor = str(graduacion.get("optometra", "") or username or "")
        observacion = str(graduacion.get("observacion", "") or "")
        proxima_cita = str(graduacion.get("proxima_cita", "") or "")
        
        productos = _build_contract_products_summary(graduacion)
        payment = _graduacion_payment_summary(graduacion)
        total = payment["monto_total"]
        acuenta = payment["total_pagado"]
        saldo = payment["saldo"]

        montura = ""
        cristales = str(graduacion.get("cristales", "") or "").strip()
        resina_text = str(graduacion.get("resina", "") or "").strip()
        color_text = str(graduacion.get("color", "") or "").strip()
        bifocal_text = str(graduacion.get("bifocal_tipo", "") or "").strip()
        multifocal_text = str(graduacion.get("multifocal_tipo", "") or "").strip()
        altura_text = str(graduacion.get("altura", "") or "").strip()
        
        for nombre in productos:
            lower = nombre.lower()
            if not montura and "montura" in lower:
                montura = nombre
                continue
            if "graduacion" in lower or "servicio" in lower or "motilidad" in lower:
                continue
            if not cristales:
                cristales = nombre

        if not montura and productos:
            montura = productos[0]
        if not cristales and len(productos) > 1:
            cristales = ", ".join(productos[1:3])

        if not multifocal_text:
            multifocal_text = ", ".join(productos[:3]) if productos else ""
        entrega = proxima_cita if proxima_cita and proxima_cita.lower() != "no" else ""

        # Sanitizar DNI para el nombre del archivo
        paciente_dni_safe = "".join(c for c in (paciente_dni or 'paciente') if c.isalnum())
        file_name = f"contrato_{paciente_dni_safe}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), file_name)

        navy = colors.HexColor("#23395B")
        blue = colors.HexColor("#2158B7")
        line = colors.HexColor("#C9D7F0")
        soft = colors.HexColor("#F7FAFF")
        red = colors.HexColor("#BA3D3D")
        gray = colors.HexColor("#6B7280")

        def txt(value, fallback=""):
            value = str(value or "").strip()
            return value if value else fallback

        def money(value):
            return f"S/ {float(value or 0):.2f}"

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ContractTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=33, leading=36, textColor=navy, alignment=1))
        styles.add(ParagraphStyle(name="ContractSub", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13, textColor=gray, alignment=1))
        styles.add(ParagraphStyle(name="BoxTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=20, alignment=1, textColor=blue))
        styles.add(ParagraphStyle(name="SmallGray", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=11, textColor=gray))
        styles.add(ParagraphStyle(name="BigRed", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=red))
        styles.add(ParagraphStyle(name="BoxSeries", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=12, textColor=gray, alignment=1))
        styles.add(ParagraphStyle(name="BoxNumber", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=18, textColor=red, alignment=1))
        styles.add(ParagraphStyle(name="LineLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=11, textColor=blue))
        styles.add(ParagraphStyle(name="LineValue", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=11, textColor=colors.black))
        styles.add(ParagraphStyle(name="SectionHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=navy))
        styles.add(ParagraphStyle(name="MoneyLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=navy, alignment=1))
        styles.add(ParagraphStyle(name="MoneyValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=19, textColor=colors.black, alignment=1))

        def p(text, style): return Paragraph(text or "&nbsp;", styles[style])

        def centered_limited_paragraph(text, style_name, max_width_mm):
            inner = Table([[p(text, style_name)]], colWidths=[max_width_mm * mm])
            inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            table = Table([[inner]], colWidths=[194 * mm])
            table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            return table

        def line_field(label, value, width, label_align="LEFT", value_align="LEFT"):
            table = Table([[p(label, "LineLabel"), p(txt(value) or "&nbsp;", "LineValue")]], colWidths=width)
            table.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEBELOW", (1, 0), (1, 0), 0.7, line), ("ALIGN", (0, 0), (0, 0), label_align), ("ALIGN", (1, 0), (1, 0), value_align)]))
            return table

        contract_annulled = _is_contract_annulled(graduacion)

        def draw_page_frame(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#6CB6FF"))
            canvas.setLineWidth(3.2)
            frame_pad = 2 * mm
            canvas.rect(doc.leftMargin - frame_pad, doc.bottomMargin - frame_pad, A4[0] - doc.leftMargin - doc.rightMargin + (frame_pad * 2), A4[1] - doc.topMargin - doc.bottomMargin + (frame_pad * 2))
            if contract_annulled:
                canvas.saveState()
                try:
                    canvas.setFillAlpha(0.32)
                except Exception:
                    pass
                canvas.setFont("Helvetica-Bold", 62)
                canvas.setFillColor(colors.HexColor("#6B7280"))
                canvas.translate(A4[0] / 2.0, A4[1] / 2.2)
                canvas.rotate(55)
                canvas.drawCentredString(0, 0, "ANULADO")
                canvas.restoreState()
            canvas.restoreState()

        doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=8 * mm)
        story = []

        header_left = [
            p(nombre_optica, "ContractTitle"),
            Spacer(1, 1.5 * mm),
            centered_limited_paragraph(slogan_optica or "&nbsp;", "ContractSub", 150),
            centered_limited_paragraph(direccion_optica or "&nbsp;", "ContractSub", 160),
            centered_limited_paragraph(correo_optica or "&nbsp;", "ContractSub", 140),
            centered_limited_paragraph(telefono_optica or "&nbsp;", "ContractSub", 100),
        ]
        contract_footer = Table([[p("0001", "BoxSeries"), p(f"Nro.&nbsp;&nbsp;{contract_number}", "BoxNumber")]], colWidths=[14 * mm, 42 * mm], rowHeights=[8 * mm])
        contract_footer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"), ("ALIGN", (1, 0), (1, 0), "CENTER")]))
        contract_box = Table([[p("CONTRATO", "BoxTitle")], [contract_footer]], colWidths=[56 * mm], rowHeights=[10 * mm, 10 * mm])
        contract_box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, blue), ("LINEBELOW", (0, 0), (-1, 0), 1, blue), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))

        header = Table([[header_left]], colWidths=[194 * mm])
        header.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header)
        story.append(Spacer(1, 3 * mm))

        contract_row = Table([["", contract_box]], colWidths=[138 * mm, 56 * mm])
        contract_row.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (1, 0), (1, 0), "TOP"),
        ]))
        story.append(contract_row)
        story.append(Spacer(1, 3 * mm))

        line_row_1 = Table([[line_field("FECHA:", fecha, [18 * mm, 46 * mm]), ""]], colWidths=[70 * mm, 124 * mm])
        line_row_1.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(line_row_1)
        story.append(Spacer(1, 1.5 * mm))

        line_row_2 = Table([[line_field("Señor (es):", paciente_nombre, [25 * mm, 104 * mm]), line_field("Telf:", paciente_tel, [12 * mm, 53 * mm])]], colWidths=[129 * mm, 65 * mm])
        line_row_2.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(line_row_2)
        story.append(Spacer(1, 1.5 * mm))

        story.append(line_field("Dirección:", paciente_dir, [22 * mm, 172 * mm]))
        story.append(Spacer(1, 1.5 * mm))
        story.append(line_field("Montura:", montura, [20 * mm, 174 * mm]))
        story.append(Spacer(1, 5 * mm))

        rx_rows = [
            [p("O.D.", "LineLabel"), p("ESF.", "LineLabel"), p("CIL.", "LineLabel"), p("EJE", "LineLabel"), p("D.I.P.", "LineLabel")],
            [p("O.D. lejos", "LineLabel"), p(txt((graduacion.get("lejos_od", {}) or {}).get("esferico")) or "—", "LineValue"), p(txt((graduacion.get("lejos_od", {}) or {}).get("cilindro")) or "—", "LineValue"), p(txt((graduacion.get("lejos_od", {}) or {}).get("eje")) or "—", "LineValue"), p(txt((graduacion.get("lejos_od", {}) or {}).get("distp")) or "—", "LineValue")],
            [p("O.I. lejos", "LineLabel"), p(txt((graduacion.get("lejos_oi", {}) or {}).get("esferico")) or "—", "LineValue"), p(txt((graduacion.get("lejos_oi", {}) or {}).get("cilindro")) or "—", "LineValue"), p(txt((graduacion.get("lejos_oi", {}) or {}).get("eje")) or "—", "LineValue"), p(txt((graduacion.get("lejos_oi", {}) or {}).get("distp")) or "—", "LineValue")],
            [p("O.D. cerca", "LineLabel"), p(txt((graduacion.get("cerca_od", {}) or {}).get("esferico")) or "—", "LineValue"), p(txt((graduacion.get("cerca_od", {}) or {}).get("cilindro")) or "—", "LineValue"), p(txt((graduacion.get("cerca_od", {}) or {}).get("eje")) or "—", "LineValue"), p(txt((graduacion.get("cerca_od", {}) or {}).get("distp")) or "—", "LineValue")],
            [p("O.I. cerca", "LineLabel"), p(txt((graduacion.get("cerca_oi", {}) or {}).get("esferico")) or "—", "LineValue"), p(txt((graduacion.get("cerca_oi", {}) or {}).get("cilindro") ) or "—", "LineValue"), p(txt((graduacion.get("cerca_oi", {}) or {}).get("eje")) or "—", "LineValue"), p(txt((graduacion.get("cerca_oi", {}) or {}).get("distp")) or "—", "LineValue")],
        ]
        rx_table = Table(rx_rows, colWidths=[30 * mm, 41 * mm, 41 * mm, 41 * mm, 41 * mm], rowHeights=[10 * mm] * 5)
        rx_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 0.8, line), ("INNERGRID", (0, 0), (-1, -1), 0.6, line), ("BACKGROUND", (0, 0), (-1, 0), colors.white), ("TEXTCOLOR", (0, 0), (-1, 0), blue), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(rx_table)
        story.append(Spacer(1, 6 * mm))

        work_header = Table([[p("DETALLE DEL TRABAJO", "SectionHeader")]], colWidths=[194 * mm])
        work_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), soft), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("BOX", (0, 0), (-1, -1), 0.6, line)]))
        story.append(work_header)
        story.append(Spacer(1, 1 * mm))
        work_row_1 = Table([[line_field("CRISTALES", cristales, [26 * mm, 56 * mm]), line_field("RESINA", resina_text, [18 * mm, 44 * mm]), line_field("COLOR", color_text, [16 * mm, 34 * mm])]], colWidths=[82 * mm, 62 * mm, 50 * mm])
        work_row_1.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(work_row_1)
        story.append(Spacer(1, 1.5 * mm))
        work_row_2 = Table([[line_field("BIFOCALES TIPO", bifocal_text, [34 * mm, 96 * mm]), line_field("ALTURA", altura_text, [18 * mm, 46 * mm], label_align="CENTER", value_align="CENTER")]], colWidths=[130 * mm, 64 * mm])
        work_row_2.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(work_row_2)
        story.append(Spacer(1, 1.5 * mm))
        story.append(line_field("MULTIFOCAL TIPO", multifocal_text, [34 * mm, 160 * mm]))
        story.append(Spacer(1, 1.5 * mm))
        story.append(line_field("OTROS", observacion, [16 * mm, 178 * mm]))
        story.append(Spacer(1, 1.5 * mm))
        work_row_3 = Table([[line_field("ENTREGA", entrega, [20 * mm, 60 * mm]), line_field("VENDEDOR", vendedor, [24 * mm, 90 * mm])]], colWidths=[80 * mm, 114 * mm])
        work_row_3.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(work_row_3)
        story.append(Spacer(1, 6 * mm))

        summary_header = Table([[p("RESUMEN", "SectionHeader")]], colWidths=[194 * mm])
        summary_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), soft), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("BOX", (0, 0), (-1, -1), 0.6, line)]))
        story.append(summary_header)
        story.append(Spacer(1, 1 * mm))
        summary = Table([[line_field("TOTAL:", money(total), [18 * mm, 44 * mm]), line_field("A CTA:", money(acuenta), [18 * mm, 44 * mm]), line_field("SALDO:", money(saldo), [18 * mm, 44 * mm])]], colWidths=[64 * mm, 64 * mm, 66 * mm])
        summary.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        story.append(summary)

        doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)

        if return_pdf_path_only:
            return pdf_path
        if open_in_browser:
            open_pdf_with_chrome(pdf_path)
        else:
            # NOTA: Evitar llamar a la UI directamente si esto corre en un thread.
            # Los llamadores actuales usan return_pdf_path_only=True para threads.
            viewer = PDFViewerDialog(pdf_path, parent_widget)
            viewer.exec_()
        return pdf_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        # No llamar a QMessageBox aquí para evitar crashes si se ejecuta en un thread.
        # Los llamadores ya capturan esta excepción y la muestran adecuadamente.
        raise e
