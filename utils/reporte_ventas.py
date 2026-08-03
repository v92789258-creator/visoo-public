import os
import sys
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

# Carga la ruta de los recursos.
# Esta función es necesaria para que el programa funcione correctamente.
def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, funciona para desarrollo y para PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def generar_expediente_pdf(paciente_data):
    """
    Genera un expediente completo del paciente en formato PDF.

    Incluye:
    - Datos personales del paciente.
    - Historial de graduaciones detallado por cada visita.
    - Observaciones clínicas.
    """
    
    # Define la ruta donde se guardará el PDF.
    output_dir = resource_path("VISO/reportes/expedientes")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"expediente_{paciente_data['dni']}_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)

    # Configuración del documento PDF.
    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, fontName='Helvetica-Bold', alignment=1))
    styles.add(ParagraphStyle(name='HeadingStyle', fontSize=14, fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='NormalStyle', fontSize=10, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='DataStyle', fontSize=10, fontName='Helvetica-Bold'))

    # Título del documento.
    elements.append(Paragraph("Expediente Clínico del Paciente", styles['TitleStyle']))
    elements.append(Spacer(1, 0.2*inch))

    # Información del Paciente.
    elements.append(Paragraph("<b>Datos Personales</b>", styles['HeadingStyle']))
    paciente_info = [
        [Paragraph(f"<b>DNI:</b> {paciente_data.get('dni', 'N/A')}", styles['NormalStyle']),
         Paragraph(f"<b>Nombre:</b> {paciente_data.get('nombre', 'N/A')}", styles['NormalStyle'])],
        [Paragraph(f"<b>Fecha de Nacimiento:</b> {paciente_data.get('fecha_nacimiento', 'N/A')}", styles['NormalStyle']),
         Paragraph(f"<b>Edad:</b> {paciente_data.get('edad', 'N/A')}", styles['NormalStyle'])],
        [Paragraph(f"<b>Género:</b> {paciente_data.get('genero', 'N/A')}", styles['NormalStyle']),
         Paragraph(f"<b>Fecha de Registro:</b> {paciente_data.get('fecha', 'N/A')}", styles['NormalStyle'])],
    ]
    table_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])
    info_table = Table(paciente_info, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(table_style)
    elements.append(info_table)
    elements.append(Spacer(1, 0.2*inch))

    # Historial de Graduaciones.
    elements.append(Paragraph("<b>Historial de Graduaciones</b>", styles['HeadingStyle']))
    historial = paciente_data.get('historial_graduaciones', [])
    if historial:
        for i, graduacion in enumerate(historial):
            elements.append(Paragraph(f"<u>Visita {i+1} - {graduacion.get('fecha', 'N/A')}</u>", styles['NormalStyle']))
            elements.append(Paragraph(f"<b>Optómetra:</b> {graduacion.get('optometra', 'N/A')}", styles['NormalStyle']))
            elements.append(Paragraph(f"<b>Próxima Cita:</b> {graduacion.get('proxima_cita', 'N/A')}", styles['NormalStyle']))
            
            # Tabla de graduaciones (Visión de Lejos).
            elements.append(Paragraph("<b>Graduación de Lejos:</b>", styles['NormalStyle']))
            lejos_data = [
                ['', 'Esférico', 'Cilindro', 'Eje', 'A.V', 'D.P', 'Prisma', 'Adición'],
                ['OD', graduacion['lejos_od'].get('esferico', ''), graduacion['lejos_od'].get('cilindro', ''),
                 graduacion['lejos_od'].get('eje', ''), graduacion['lejos_od'].get('av', ''),
                 graduacion['lejos_od'].get('distp', ''), graduacion['lejos_od'].get('prisma', ''),
                 graduacion['lejos_od'].get('adicmedia', '')],
                ['OI', graduacion['lejos_oi'].get('esferico', ''), graduacion['lejos_oi'].get('cilindro', ''),
                 graduacion['lejos_oi'].get('eje', ''), graduacion['lejos_oi'].get('av', ''),
                 graduacion['lejos_oi'].get('distp', ''), graduacion['lejos_oi'].get('prisma', ''),
                 graduacion['lejos_oi'].get('adicmedia', '')]
            ]
            table_style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e7ee6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ])
            lejos_table = Table(lejos_data, colWidths=[0.5*inch, 1*inch, 1*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch])
            lejos_table.setStyle(table_style)
            elements.append(lejos_table)

            # Revisa si la observación está vacía.
            observacion = graduacion.get('observacion', '').strip()
            if observacion:
                elements.append(Paragraph(f"<b>Observación:</b> {observacion}", styles['NormalStyle']))
            else:
                elements.append(Paragraph("<b>Observación:</b> No hay observaciones", styles['NormalStyle']))
            
            elements.append(Spacer(1, 0.2*inch))
    else:
        elements.append(Paragraph("<i>No hay historial de graduaciones registrado.</i>", styles['NormalStyle']))
    
    # Construir el PDF.
    doc.build(elements)
    
    return filepath