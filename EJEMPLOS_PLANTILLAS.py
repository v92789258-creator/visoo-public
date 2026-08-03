"""
Ejemplos de uso de la nueva arquitectura refactorizada de plantillas.
Demuestra cómo usar el sistema modular en diferentes escenarios.
"""

# ============================================================================
# EJEMPLO 1: Uso Básico - Generar Boleta con Plantilla del Usuario
# ============================================================================

def ejemplo_generar_boleta_basico():
    """Ejemplo más simple: generar boleta con plantilla guardada del usuario."""
    from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
    
    usuario_id = "user123"
    
    # El generador carga automáticamente la plantilla seleccionada por el usuario
    generador = GeneradorBoletasPlantilla(usuario_id)
    
    datos_boleta = {
        'nombre_optica': 'Óptica Visión Clara',
        'ruc': '20123456789',
        'numero_boleta': 'B-001-00001',
        'fecha': '23/01/2025',
        'cliente': 'Juan Pérez García',
        'dni': '12345678',
        'direccion': 'Av. Principal 123, Lima',
        'productos': [
            {
                'nombre': 'Montura Metal Titanio',
                'cantidad': 1,
                'precio': 150.00,
                'total': 150.00,
            },
            {
                'nombre': 'Lentes Oftálmicos Bifocales',
                'cantidad': 1,
                'precio': 200.00,
                'total': 200.00,
            },
            {
                'nombre': 'Servicio de Ajuste',
                'cantidad': 1,
                'precio': 50.00,
                'total': 50.00,
            },
        ],
        'subtotal': 400.00,
        'descuento': 0.00,
        'igv': 72.00,
        'total': 472.00,
        'monto_letras': 'Cuatrocientos setenta y dos soles',
        'metodo_pago': 'Tarjeta Crédito',
        'vendedor': 'Dr. García López',
    }
    
    # Generar boleta (usa la plantilla guardada del usuario)
    ruta_pdf = generador.generar_boleta(datos_boleta)
    
    print(f"✓ Boleta generada: {ruta_pdf}")
    print(f"  Plantilla utilizada: {generador.plantilla_seleccionada}")
    
    return ruta_pdf


# ============================================================================
# EJEMPLO 2: Generar Boleta con Plantilla Específica
# ============================================================================

def ejemplo_generar_con_plantilla_especifica():
    """Generar boleta con una plantilla específica sin cambiar la preferencia."""
    from utils.plantillas import PlantillaA4
    
    usuario_id = "user123"
    
    # Instanciar directamente la plantilla que queremos
    plantilla_a4 = PlantillaA4(usuario_id)
    
    datos_boleta = {
        'nombre_optica': 'Óptica Visión Clara',
        'ruc': '20123456789',
        'numero_boleta': 'B-001-00002',
        'fecha': '23/01/2025',
        'cliente': 'María López',
        'dni': '87654321',
        'productos': [
            {
                'nombre': 'Lentes Progresivos Premium',
                'cantidad': 1,
                'precio': 350.00,
                'total': 350.00,
            },
        ],
        'subtotal': 350.00,
        'igv': 63.00,
        'total': 413.00,
        'monto_letras': 'Cuatrocientos trece soles',
        'metodo_pago': 'Efectivo',
        'vendedor': 'Dr. García López',
    }
    
    # Generar con esta plantilla específica
    ruta_pdf = plantilla_a4.generar(datos_boleta)
    
    print(f"✓ Boleta A4 generada: {ruta_pdf}")
    
    return ruta_pdf


# ============================================================================
# EJEMPLO 3: Cambiar Plantilla del Usuario
# ============================================================================

def ejemplo_cambiar_plantilla_usuario():
    """Cambiar la plantilla preferida del usuario."""
    from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
    
    usuario_id = "user123"
    generador = GeneradorBoletasPlantilla(usuario_id)
    
    print(f"Plantilla actual: {generador.plantilla_seleccionada}")
    
    # Cambiar a otra plantilla
    generador.guardar_plantilla_seleccionada('a4')
    
    print(f"Plantilla nueva: {generador.plantilla_seleccionada}")
    
    # Las próximas boletas usarán A4
    print("✓ Preferencia guardada. Próximas boletas usarán formato A4")


# ============================================================================
# EJEMPLO 4: Listar Plantillas Disponibles
# ============================================================================

def ejemplo_listar_plantillas():
    """Ver todas las plantillas disponibles."""
    from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
    
    generador = GeneradorBoletasPlantilla("user123")
    
    print("Plantillas disponibles:")
    print()
    
    for nombre, config in generador.PLANTILLAS.items():
        print(f"  📄 {nombre.upper()}")
        print(f"     Tamaño: {config['ancho']}mm × {config['alto']}mm")
        print(f"     Margen: {config['margen']}mm")
        print(f"     Detalles: {'Sí' if config['mostrar_detalles'] else 'No'}")
        print()


# ============================================================================
# EJEMPLO 5: Crear Nueva Plantilla Personalizada
# ============================================================================

def ejemplo_crear_plantilla_personalizada():
    """Crear una nueva plantilla personalizada."""
    from utils.plantillas.base import PlantillaBase
    from fpdf import FPDF
    import os
    from datetime import datetime
    
    class PlantillaTransparencia(PlantillaBase):
        """Plantilla especial para comprobantes de transparencia."""
        
        CONFIGURACION = {
            'ancho': 100,
            'alto': 200,
            'margen': 8,
            'font_titulo': 12,
            'font_normal': 9,
            'font_pequeño': 7,
            'lineas_por_producto': 1,
            'mostrar_detalles': True,
        }
        
        def generar(self, datos_boleta, ruta_salida=None):
            """Genera boleta con diseño de transparencia."""
            config = self.CONFIGURACION
            
            pdf = FPDF('P', 'mm', (config['ancho'], config['alto']))
            pdf.add_page()
            pdf.set_margins(config['margen'], config['margen'], config['margen'])
            
            # Encabezado
            pdf.set_font('Helvetica', 'B', config['font_titulo'])
            pdf.cell(0, 10, 'COMPROBANTE', 0, 1, 'C')
            pdf.cell(0, 10, 'TRANSPARENCIA', 0, 1, 'C')
            
            # Datos
            pdf.set_font('Helvetica', '', config['font_normal'])
            pdf.ln(5)
            
            pdf.cell(0, 6, f"Fecha: {datos_boleta.get('fecha', '')}", 0, 1)
            pdf.cell(0, 6, f"Monto: S/{datos_boleta.get('total', 0):.2f}", 0, 1)
            pdf.cell(0, 6, f"Concepto: {datos_boleta.get('nombre_optica', '')}", 0, 1)
            
            # Pie
            pdf.set_font('Helvetica', 'I', config['font_pequeño'])
            pdf.ln(5)
            pdf.cell(0, 4, f"Procesado: {self._obtener_timestamp_actual()}", 0, 1, 'C')
            
            return self._guardar_pdf(pdf, ruta_salida)
    
    # Usar la plantilla
    plantilla = PlantillaTransparencia("user123")
    
    datos = {
        'nombre_optica': 'Óptica Transparencia SA',
        'fecha': '23/01/2025',
        'total': 500.00,
    }
    
    ruta_pdf = plantilla.generar(datos)
    print(f"✓ Plantilla personalizada generada: {ruta_pdf}")
    
    return ruta_pdf


# ============================================================================
# EJEMPLO 6: Usar en Interfaz Gráfica
# ============================================================================

def ejemplo_usar_en_gui():
    """Ejemplo de integración con la interfaz gráfica."""
    from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
    from gui.components import PanelPlantillas, PanelLogo
    
    class VentanaConfiguracion(QMainWindow):
        def __init__(self, username):
            super().__init__()
            self.username = username
            
            # Widget central
            widget_central = QWidget()
            layout = QVBoxLayout(widget_central)
            
            # Panel de plantillas
            self.panel_plantillas = PanelPlantillas(username)
            layout.addWidget(self.panel_plantillas)
            
            # Panel de logo
            self.panel_logo = PanelLogo(username)
            layout.addWidget(self.panel_logo)
            
            layout.addStretch()
            
            self.setCentralWidget(widget_central)
            self.setWindowTitle("Configuración de Plantillas")
            self.resize(900, 600)
    
    print("✓ Integración GUI lista")
    print("  - PanelPlantillas: Selecciona plantilla")
    print("  - PanelLogo: Gestiona logo")


# ============================================================================
# EJEMPLO 7: Procesamiento por Lotes
# ============================================================================

def ejemplo_generar_lote_boletas():
    """Generar múltiples boletas en un lote."""
    from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
    
    usuario_id = "user123"
    generador = GeneradorBoletasPlantilla(usuario_id)
    
    # Datos de 3 boletas
    boletas = [
        {
            'nombre_optica': 'Óptica Visión',
            'numero_boleta': 'B-001-00001',
            'cliente': 'Cliente 1',
            'total': 100.00,
            'productos': [{'nombre': 'Producto 1', 'cantidad': 1, 'precio': 100, 'total': 100}],
            'subtotal': 100.00,
            'monto_letras': 'Cien soles',
        },
        {
            'nombre_optica': 'Óptica Visión',
            'numero_boleta': 'B-001-00002',
            'cliente': 'Cliente 2',
            'total': 200.00,
            'productos': [{'nombre': 'Producto 2', 'cantidad': 2, 'precio': 100, 'total': 200}],
            'subtotal': 200.00,
            'monto_letras': 'Doscientos soles',
        },
        {
            'nombre_optica': 'Óptica Visión',
            'numero_boleta': 'B-001-00003',
            'cliente': 'Cliente 3',
            'total': 150.00,
            'productos': [{'nombre': 'Producto 3', 'cantidad': 1, 'precio': 150, 'total': 150}],
            'subtotal': 150.00,
            'monto_letras': 'Ciento cincuenta soles',
        },
    ]
    
    archivos_generados = []
    
    for i, datos_boleta in enumerate(boletas, 1):
        try:
            ruta = generador.generar_boleta(datos_boleta)
            archivos_generados.append(ruta)
            print(f"✓ Boleta {i}/3 generada: {ruta}")
        except Exception as e:
            print(f"✗ Error en boleta {i}: {e}")
    
    print(f"\nResumen: {len(archivos_generados)}/{len(boletas)} boletas generadas")
    
    return archivos_generados


# ============================================================================
# EJEMPLO 8: Manejo de Errores
# ============================================================================

def ejemplo_manejo_errores():
    """Ejemplo de manejo robusto de errores."""
    from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
    
    usuario_id = "user123"
    
    try:
        generador = GeneradorBoletasPlantilla(usuario_id)
        
        # Cambiar a plantilla inválida
        generador.guardar_plantilla_seleccionada('plantilla_inexistente')
        
    except ValueError as e:
        print(f"✗ Plantilla inválida: {e}")
    
    try:
        # Generar con datos incompletos
        datos_incompletos = {'nombre_optica': 'Óptica'}
        
        generador = GeneradorBoletasPlantilla(usuario_id)
        ruta = generador.generar_boleta(datos_incompletos)
        
    except Exception as e:
        print(f"✗ Error al generar boleta: {e}")


# ============================================================================
# EJECUTOR DE EJEMPLOS
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("EJEMPLOS DE USO - ARQUITECTURA REFACTORIZADA DE PLANTILLAS")
    print("=" * 70)
    print()
    
    # Ejemplo 1
    print("📌 EJEMPLO 1: Generar boleta básica")
    print("-" * 70)
    try:
        ejemplo_generar_boleta_basico()
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Ejemplo 4
    print("📌 EJEMPLO 4: Listar plantillas")
    print("-" * 70)
    ejemplo_listar_plantillas()
    
    # Ejemplo 3
    print("📌 EJEMPLO 3: Cambiar plantilla")
    print("-" * 70)
    ejemplo_cambiar_plantilla_usuario()
    print()
    
    # Ejemplo 5
    print("📌 EJEMPLO 5: Crear plantilla personalizada")
    print("-" * 70)
    try:
        ejemplo_crear_plantilla_personalizada()
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    print("=" * 70)
    print("✓ Ejemplos completados")
    print("=" * 70)
