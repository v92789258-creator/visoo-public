# utils/generador_expediente.py

import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

from utils.file_handler import VISO_DIR

COLORES = {
    "azul": "#1E56B3",
    "azul_claro": "#D9EAFB",
    "teal": "#18A0C9",
    "gris_texto": "#233142",
    "gris_linea": "#C9D6E3",
    "gris_fondo": "#F5F8FB",
    "marron": "#8B7355",
    "marron_claro": "#F3E7D7",
    "amarillo": "#FFF7D9",
    "blanco": "#FFFFFF",
}


def _clean_text(value, fallback="N/A"):
    text = str(value or "").strip()
    return text if text else fallback


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="OpticaTitle",
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=25,
        textColor=colors.HexColor(COLORES["azul"]),
        alignment=1,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="OpticaSubtitle",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(COLORES["teal"]),
        alignment=1,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12,
        textColor=colors.HexColor(COLORES["azul"]),
        alignment=1,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=12,
        textColor=colors.white,
        leftIndent=8,
        rightIndent=8,
    ))
    styles.add(ParagraphStyle(
        name="SubTitle",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor(COLORES["gris_texto"]),
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="Cell",
        fontName="Helvetica",
        fontSize=8.3,
        leading=10,
        textColor=colors.HexColor(COLORES["gris_texto"]),
    ))
    styles.add(ParagraphStyle(
        name="CellCenter",
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        textColor=colors.HexColor(COLORES["gris_texto"]),
        alignment=1,
    ))
    styles.add(ParagraphStyle(
        name="HeadCell",
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=9,
        textColor=colors.white,
        alignment=1,
    ))
    styles.add(ParagraphStyle(
        name="Foot",
        fontName="Helvetica",
        fontSize=7,
        leading=8,
        textColor=colors.HexColor("#607080"),
        alignment=1,
    ))
    return styles


def _section_bar(title, styles):
    table = Table([[Paragraph(title, styles["SectionTitle"])]], colWidths=[7.25 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLORES["azul"])),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _rx_value(data, side, key):
    return _clean_text(((data or {}).get(side, {}) or {}).get(key), "-")


def _rx_table(title, header_color, left_fill, graduacion, styles, side_prefix):
    rows = [
        [
            Paragraph("<b>VISTA</b>", styles["HeadCell"]),
            Paragraph("<b>ESF</b>", styles["HeadCell"]),
            Paragraph("<b>CIL</b>", styles["HeadCell"]),
            Paragraph("<b>EJE</b>", styles["HeadCell"]),
            Paragraph("<b>A.V</b>", styles["HeadCell"]),
            Paragraph("<b>D.P</b>", styles["HeadCell"]),
            Paragraph("<b>PRISM</b>", styles["HeadCell"]),
            Paragraph("<b>ADIC</b>", styles["HeadCell"]),
        ]
    ]

    if side_prefix == "lejos":
        od = graduacion.get("lejos_od", {}) or {}
        oi = graduacion.get("lejos_oi", {}) or {}
        rows.extend([
            [
                Paragraph("<b>OD</b>", styles["CellCenter"]),
                Paragraph(_clean_text(od.get("esferico"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("cilindro"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("eje"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("av"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("distp"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("prisma"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("adicmedia"), "-"), styles["CellCenter"]),
            ],
            [
                Paragraph("<b>OI</b>", styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("esferico"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("cilindro"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("eje"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("av"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("distp"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("prisma"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("adicmedia"), "-"), styles["CellCenter"]),
            ],
        ])
    else:
        od = graduacion.get("cerca_od", {}) or {}
        oi = graduacion.get("cerca_oi", {}) or {}
        ol = graduacion.get("cerca_ol", {}) or {}
        rows.extend([
            [
                Paragraph("<b>OD</b>", styles["CellCenter"]),
                Paragraph(_clean_text(od.get("esferico"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("cilindro"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("eje"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("av"), "-"), styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph(_clean_text(od.get("prisma"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(od.get("adicmedia"), "-"), styles["CellCenter"]),
            ],
            [
                Paragraph("<b>OI</b>", styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("esferico"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("cilindro"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("eje"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("av"), "-"), styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("prisma"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(oi.get("adicmedia"), "-"), styles["CellCenter"]),
            ],
            [
                Paragraph("<b>OL</b>", styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph("-", styles["CellCenter"]),
                Paragraph(_clean_text(ol.get("distp"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(ol.get("prisma"), "-"), styles["CellCenter"]),
                Paragraph(_clean_text(ol.get("adicmedia"), "-"), styles["CellCenter"]),
            ],
        ])

    table = Table(rows, colWidths=[0.74 * inch, 0.79 * inch, 0.79 * inch, 0.72 * inch, 0.67 * inch, 0.67 * inch, 0.73 * inch, 0.74 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor(left_fill)),
        ("BACKGROUND", (1, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, colors.HexColor(COLORES["gris_fondo"])]),
        ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor(COLORES["gris_linea"])),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return [
        Paragraph(f"<b>{title}</b>", styles["SubTitle"]),
        Spacer(1, 0.03 * inch),
        table,
    ]


def generar_expediente_pdf(paciente_data, nombre_optica, username):
    if not username:
        output_dir = VISO_DIR / "reportes" / "expedientes"
    else:
        output_dir = VISO_DIR / username / "expedientes"
    os.makedirs(str(output_dir), exist_ok=True)

    filename = f"expediente_{paciente_data['dni']}_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(str(output_dir), filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.55 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )
    styles = _build_styles()
    elements = []

    top_rule = Table([[""]], colWidths=[7.25 * inch])
    top_rule.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(COLORES["azul"])),
    ]))
    elements.append(top_rule)
    elements.append(Spacer(1, 0.08 * inch))

    header = Table([
        [Paragraph(_clean_text(nombre_optica, "Mi Optica"), styles["OpticaTitle"])],
        [Paragraph("CONSULTORIO OFTALMOLOGICO", styles["OpticaSubtitle"])],
        [Paragraph("EXPEDIENTE DEL PACIENTE", styles["DocTitle"])],
    ], colWidths=[7.25 * inch])
    header.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.12 * inch))

    divider = Table([[""]], colWidths=[7.25 * inch])
    divider.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor(COLORES["azul"])),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(_section_bar("INFORMACION DEL PACIENTE", styles))
    elements.append(Spacer(1, 0.06 * inch))

    info_table = Table([
        [
            Paragraph(f"<b>DNI:</b><br/>{_clean_text(paciente_data.get('dni'))}", styles["Cell"]),
            Paragraph(f"<b>NOMBRE:</b><br/>{_clean_text(paciente_data.get('nombre'))}", styles["Cell"]),
            Paragraph(f"<b>EDAD:</b><br/>{_clean_text(paciente_data.get('edad'))}", styles["Cell"]),
        ],
        [
            Paragraph(f"<b>F. NACIMIENTO:</b><br/>{_clean_text(paciente_data.get('fecha_nacimiento'))}", styles["Cell"]),
            Paragraph(f"<b>GENERO:</b><br/>{_clean_text(paciente_data.get('genero'))}", styles["Cell"]),
            Paragraph(f"<b>F. REGISTRO:</b><br/>{_clean_text(paciente_data.get('fecha'))}", styles["Cell"]),
        ],
    ], colWidths=[2.42 * inch, 2.42 * inch, 2.41 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLORES["azul_claro"])),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor(COLORES["azul"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.16 * inch))

    elements.append(_section_bar("HISTORIAL DE GRADUACIONES", styles))
    elements.append(Spacer(1, 0.06 * inch))

    historial = paciente_data.get("historial_graduaciones", []) or []
    if historial:
        for idx, graduacion in enumerate(historial, start=1):
            header_row = Table([
                [
                    Paragraph(f"<b>Visita #{idx}</b>", styles["Cell"]),
                    Paragraph(f"Fecha: {_clean_text(graduacion.get('fecha'), '-')}", styles["Cell"]),
                    Paragraph(f"Optometra: {_clean_text(graduacion.get('optometra'), '-')}", styles["Cell"]),
                ]
            ], colWidths=[1.25 * inch, 2.35 * inch, 3.65 * inch])
            header_row.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLORES["gris_fondo"])),
                ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor(COLORES["gris_linea"])),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(header_row)
            elements.append(Spacer(1, 0.05 * inch))

            elements.extend(_rx_table("VISION DE LEJOS", COLORES["azul"], "#EAF2FB", graduacion, styles, "lejos"))
            elements.append(Spacer(1, 0.08 * inch))
            elements.extend(_rx_table("VISION DE CERCA", COLORES["marron"], COLORES["marron_claro"], graduacion, styles, "cerca"))
            elements.append(Spacer(1, 0.08 * inch))

            observacion = _clean_text(graduacion.get("observacion"), "")
            if observacion:
                obs = Table([[Paragraph(f"<b>OBSERVACIONES:</b> {observacion}", styles["Cell"])]], colWidths=[7.25 * inch])
                obs.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLORES["amarillo"])),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]))
                elements.append(obs)
                elements.append(Spacer(1, 0.05 * inch))

            elements.append(Paragraph(f"<b>Proxima Cita:</b> {_clean_text(graduacion.get('proxima_cita'), 'None')}", styles["Cell"]))
            elements.append(Spacer(1, 0.13 * inch))
    else:
        empty_table = Table([[Paragraph("No hay historial de graduaciones registrado.", styles["CellCenter"])]], colWidths=[7.25 * inch])
        empty_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLORES["gris_fondo"])),
            ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor(COLORES["gris_linea"])),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(empty_table)

    elements.append(Spacer(1, 0.18 * inch))
    bottom_rule = Table([[""]], colWidths=[7.25 * inch])
    bottom_rule.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor(COLORES["azul"])),
    ]))
    elements.append(bottom_rule)
    elements.append(Spacer(1, 0.08 * inch))

    generado = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    footer = Table([
        [
            Paragraph(f"Generado: {generado}", styles["Foot"]),
            Paragraph("Estado: Documento Oficial", styles["Foot"]),
            Paragraph("Confidencial: SI", styles["Foot"]),
        ]
    ], colWidths=[2.42 * inch, 2.41 * inch, 2.42 * inch])
    footer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLORES["gris_fondo"])),
        ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor(COLORES["gris_linea"])),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(footer)

    try:
        doc.build(elements)
    except Exception as e:
        raise RuntimeError(f"Error al construir el PDF del expediente: {e}")

    return str(filepath)
