"""
Módulo para crear un envoltorio HTML que mejora la impresión de PDFs en Chrome.
Esto soluciona problemas de márgenes y escala en la impresión.
"""

import os
from pathlib import Path

def create_print_html_wrapper(pdf_path, ancho_mm=80):
    """
    Crea un archivo HTML que envuelve el PDF con CSS de impresión optimizado.
    
    Args:
        pdf_path: Ruta del PDF
        ancho_mm: Ancho en milímetros para configuración de impresión
    
    Returns:
        Ruta del archivo HTML creado
    """
    pdf_path = os.path.abspath(pdf_path)
    pdf_name = os.path.basename(pdf_path)
    html_path = pdf_path.replace('.pdf', '_print.html')
    
    # CSS de impresión optimizado
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boleta - {pdf_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: #f0f0f0;
            font-family: Arial, sans-serif;
        }}
        
        .container {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding: 10px;
            background: #f0f0f0;
        }}
        
        .preview {{
            background: white;
            width: {ancho_mm}mm;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            border-radius: 4px;
        }}
        
        .pdf-container {{
            width: 100%;
            height: auto;
        }}
        
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
            display: block;
        }}
        
        @media print {{
            body {{
                background: white;
                margin: 0;
                padding: 0;
            }}
            
            .container {{
                display: block;
                background: white;
                min-height: auto;
                padding: 0;
                margin: 0;
            }}
            
            .preview {{
                width: {ancho_mm}mm;
                box-shadow: none;
                border-radius: 0;
                page-break-after: avoid;
                margin: 0;
                padding: 0;
            }}
            
            @page {{
                size: {ancho_mm}mm auto;
                margin: 0;
                padding: 0;
            }}
        }}
        
        .info {{
            text-align: center;
            padding: 10px;
            background: white;
            margin-top: 10px;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }}
        
        .info p {{
            margin: 5px 0;
        }}
        
        .print-button {{
            display: block;
            margin: 10px auto;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .print-button:hover {{
            background: #0056b3;
        }}
        
        @media print {{
            .info, .print-button {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="preview">
            <iframe src="file:///{pdf_path}" type="application/pdf"></iframe>
        </div>
    </div>
    
    <div class="info">
        <p><strong>Para imprimir correctamente:</strong></p>
        <p>1. Presiona Ctrl+P</p>
        <p>2. En "Márgenes" selecciona "Ninguno"</p>
        <p>3. En "Escala" asegúrate que sea 100%</p>
        <p>4. Tamaño de papel: {ancho_mm}mm de ancho (automático de alto)</p>
    </div>
    
    <button class="print-button" onclick="window.print()">Imprimir (Ctrl+P)</button>
    
    <script>
        // Auto-open print dialog on load (optional)
        // window.onload = function() {{ setTimeout(function() {{ window.print(); }}, 1000); }};
    </script>
</body>
</html>
"""
    
    # Guardar el HTML
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[HTML] Archivo de impresión creado: {html_path}")
    return html_path


def create_optimized_print_page(pdf_path, ancho_mm=80):
    """
    Crea una página HTML optimizada que muestra el PDF con configuración de impresión correcta.
    Esta es la mejor opción para Chrome.
    """
    pdf_path = os.path.abspath(pdf_path)
    pdf_name = os.path.basename(pdf_path)
    html_path = pdf_path.replace('.pdf', '_view.html')
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{pdf_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            background: #ddd;
            font-family: Arial, sans-serif;
        }}
        
        body {{
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .toolbar {{
            background: #fff;
            padding: 10px;
            border-bottom: 1px solid #ccc;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .toolbar button {{
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .toolbar button:hover {{
            background: #0056b3;
        }}
        
        .info {{
            flex: 0 0 auto;
            background: #fff3cd;
            color: #856404;
            padding: 8px 10px;
            border-bottom: 1px solid #ffc107;
            font-size: 12px;
        }}
        
        .pdf-viewer {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            overflow: auto;
            padding: 10px;
        }}
        
        .pdf-page {{
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            width: {ancho_mm}mm;
            page-break-after: always;
        }}
        
        .pdf-page iframe {{
            width: 100%;
            height: auto;
            border: none;
        }}
        
        @media print {{
            .toolbar, .info {{
                display: none !important;
            }}
            
            html, body {{
                background: white;
                overflow: visible;
                margin: 0;
                padding: 0;
            }}
            
            .pdf-viewer {{
                padding: 0;
                background: white;
            }}
            
            .pdf-page {{
                box-shadow: none;
                page-break-inside: avoid;
            }}
            
            @page {{
                size: {ancho_mm}mm auto;
                margin: 0;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="toolbar">
        <button onclick="window.print()">Imprimir (Ctrl+P)</button>
        <button onclick="location.reload()">Recargar</button>
        <span style="color: #666; font-size: 12px;">Ancho de página: {ancho_mm}mm</span>
    </div>
    
    <div class="info">
        <strong>Instrucciones de impresión:</strong>
        Cuando hagas clic en "Imprimir", en el diálogo:
        1. Márgenes → Selecciona "Ninguno"
        2. Escala → Confirma que sea "100%"
        3. Tamaño de papel → {ancho_mm}mm (ancho automático de alto)
    </div>
    
    <div class="pdf-viewer">
        <div class="pdf-page">
            <iframe src="file:///{pdf_path}" type="application/pdf"></iframe>
        </div>
    </div>
</body>
</html>
"""
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[HTML] Página de visualización creada: {html_path}")
    return html_path
