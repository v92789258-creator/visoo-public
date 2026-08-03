"""
GUÍA DE INTEGRACIÓN DE SUNAT EN GENERADOR DE BOLETAS EXISTENTE

Este archivo muestra cómo integrar los módulos SUNAT en el generador
de boletas actual de VISO (generador_boletas_plantilla.py)
"""

# ============================================================================
# PASO 1: IMPORTAR MÓDULOS SUNAT EN generador_boletas_plantilla.py
# ============================================================================

# Agregar estos imports al inicio del archivo:

from utils.generador_boletas_sunat import GeneradorBoletasSUNAT
from utils.configurador_sunat import ConfiguradorSUNAT
from utils.gestor_certificados import GestorCertificados


# ============================================================================
# PASO 2: MODIFICAR LA CLASE GeneradorBoletasPlantilla
# ============================================================================

# En __init__, agregar:

class GeneradorBoletasPlantilla:
    def __init__(self, usuario: str, viso_dir: str):
        # ... código existente ...
        
        # NUEVO: Inicializar módulos SUNAT
        self.configurador_sunat = ConfiguradorSUNAT(usuario, viso_dir)
        self.generador_sunat = GeneradorBoletasSUNAT(usuario, viso_dir)
        self.gestor_certs = GestorCertificados(usuario, viso_dir)
        
        # Verificar si SUNAT está habilitado
        self.sunat_habilitado = self.configurador_sunat.get_estado_configuracion().get('habilitado', False)


# ============================================================================
# PASO 3: MODIFICAR MÉTODO DE GENERACIÓN
# ============================================================================

# Modificar el método que genera boletas (ej. generar_boleta_pdf):

def generar_boleta_pdf(self, datos_boleta: dict, usuario: str, 
                       output_path: str, boleta_id: Optional[str] = None) -> bool:
    """
    Genera boleta PDF con integración opcional a SUNAT
    """
    
    try:
        # ... código existente de generación PDF ...
        
        # NUEVO: Si SUNAT está habilitado, también generar XML
        if self.sunat_habilitado:
            self._generar_boleta_electronica_async(datos_boleta)
        
        return True
        
    except Exception as e:
        logging.error(f"Error generando boleta: {e}")
        return False


# ============================================================================
# PASO 4: AGREGAR MÉTODO ASINCRÓNICO
# ============================================================================

def _generar_boleta_electronica_async(self, datos_boleta: dict):
    """
    Genera boleta electrónica en segundo plano
    Se ejecuta sin bloquear la generación del PDF
    """
    
    import threading
    from datetime import datetime
    
    def generar_xml():
        try:
            # Preparar datos para SUNAT
            datos_sunat = {
                'numero_serie': datos_boleta.get('serie', 'B001'),
                'numero_correlativo': datos_boleta.get('numero', 1),
                'tipo_cliente': '1' if len(datos_boleta.get('dni_cliente', '')) == 8 else '6',
                'numero_cliente': datos_boleta.get('dni_cliente', ''),
                'cliente_nombre': datos_boleta.get('nombre_cliente', ''),
                'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
                'items': self._convertir_items_para_sunat(datos_boleta.get('items', [])),
                'subtotal': float(datos_boleta.get('subtotal', 0)),
                'igv': float(datos_boleta.get('igv', 0)),
                'total': float(datos_boleta.get('total', 0)),
            }
            
            # Validar
            is_valid, errores = self.generador_sunat.validar_boleta(datos_sunat)
            if not is_valid:
                logging.warning(f"Boleta SUNAT inválida: {errores}")
                return
            
            # Generar
            success, result = self.generador_sunat.generar_boleta_electronica(datos_sunat)
            
            if success:
                logging.info(f"Boleta SUNAT generada: {result['xml_path']}")
                if result.get('ticket_numero'):
                    logging.info(f"Ticket SUNAT: {result['ticket_numero']}")
            else:
                logging.error(f"Error SUNAT: {result.get('errores')}")
                
        except Exception as e:
            logging.error(f"Error generando boleta SUNAT: {e}")
    
    # Ejecutar en thread separado
    thread = threading.Thread(target=generar_xml, daemon=True)
    thread.start()


def _convertir_items_para_sunat(self, items: list) -> list:
    """Convierte items de formato VISO a formato SUNAT"""
    
    items_sunat = []
    
    for item in items:
        item_sunat = {
            'descripcion': item.get('producto', 'Producto'),
            'cantidad': int(item.get('cantidad', 1)),
            'precio_unitario': float(item.get('precio_unitario', 0)),
            'total': float(item.get('total', 0)),
            'unidad': 'C62'  # C62 = Unidades
        }
        items_sunat.append(item_sunat)
    
    return items_sunat


# ============================================================================
# PASO 5: AGREGAR MÉTODOS AUXILIARES
# ============================================================================

def obtener_estado_sunat(self) -> dict:
    """Retorna estado actual de configuración SUNAT"""
    return self.configurador_sunat.get_estado_configuracion()


def verificar_certificados_vencimiento(self) -> list:
    """Verifica certificados próximos a vencer"""
    return self.gestor_certs.verificar_certificados_proximos_vencer(dias_alerta=30)


def habilitar_sunat(self, usuario_sol: str, contraseña: str) -> tuple:
    """Habilita SUNAT (llamar desde UI)"""
    return self.configurador_sunat.habilitar_emision_electronica(True)


def deshabilitar_sunat(self) -> tuple:
    """Deshabilita SUNAT"""
    return self.configurador_sunat.habilitar_emision_electronica(False)


# ============================================================================
# PASO 6: AGREGACIÓN EN PÁGINA DE VENTAS
# ============================================================================

# En la página de ventas (sales_tab.py), agregar indicador de SUNAT:

def actualizar_estado_sunat(self):
    """Actualiza indicador de estado SUNAT en la UI"""
    
    estado = self.generador_boletas.obtener_estado_sunat()
    
    if estado.get('habilitado'):
        # Mostrar botón verde con ícono
        self.label_sunat_status.setText("✓ SUNAT Activo")
        self.label_sunat_status.setStyleSheet("color: #4caf50; font-weight: bold;")
    else:
        # Mostrar botón gris
        self.label_sunat_status.setText("○ SUNAT Inactivo")
        self.label_sunat_status.setStyleSheet("color: #999; font-weight: bold;")
    
    # Verificar certificados próximos a vencer
    alertas = self.generador_boletas.verificar_certificados_vencimiento()
    if alertas:
        for cert in alertas:
            if cert.get('dias_faltantes') < 7:
                # Mostrar alerta urgente
                self.mostrar_alerta(f"⚠️ Certificado vence en {cert['dias_faltantes']} días")


# ============================================================================
# PASO 7: CONFIGURACIÓN EN requirements.txt
# ============================================================================

# Asegurarse que existan las siguientes librerías:
# lxml>=4.9.2
# cryptography>=39.0.0
# requests>=2.28.0


# ============================================================================
# PASO 8: FLUJO COMPLETO EN VENTA
# ============================================================================

# El flujo de una venta con SUNAT habilitado sería:

"""
1. Usuario ingresa datos de venta en sales_tab
2. Usuario hace clic en "Generar Boleta"
3. GeneradorBoletasPlantilla.generar_boleta_pdf():
   - Genera PDF (como antes)
   - Inicia thread asincrónico para XML/SUNAT
4. Thread asincrónico:
   - Genera XML UBL 2.1
   - Firma digitalmente
   - Envía a SUNAT
   - Recibe CDR
   - Guarda localmente
5. Usuario puede ver:
   - Boleta PDF descargada
   - Estado de envío a SUNAT
   - Número de ticket
"""


# ============================================================================
# PASO 9: MANEJO DE ERRORES
# ============================================================================

def registrar_error_sunat(self, error: str, datos_boleta: dict):
    """Registra errores de SUNAT para auditoría"""
    
    import json
    from datetime import datetime
    
    log_file = os.path.join(
        self.viso_dir, 
        self.usuario, 
        'data', 
        'sunat', 
        'errores_sunat.json'
    )
    
    error_entry = {
        'timestamp': datetime.now().isoformat(),
        'error': error,
        'boleta': datos_boleta.get('numero'),
        'cliente': datos_boleta.get('cliente_nombre')
    }
    
    try:
        # Cargar errores anteriores
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                errores = json.load(f)
        else:
            errores = []
        
        # Agregar nuevo error
        errores.append(error_entry)
        
        # Guardar
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(errores, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        logging.error(f"No se pudo registrar error SUNAT: {e}")


# ============================================================================
# PASO 10: TESTING
# ============================================================================

# Test básico en environment de desarrollo:

if __name__ == "__main__":
    # Usar ambiente de testing
    configurador = ConfiguradorSUNAT("test_user", "C:/VISO")
    
    # Cambiar a testing
    configurador.config['ambiente'] = 'testing'
    configurador.guardar_config()
    
    # Generar boleta de prueba
    generador = GeneradorBoletasSUNAT("test_user", "C:/VISO")
    
    datos_prueba = {
        'numero_serie': 'B001',
        'numero_correlativo': '000001',
        'tipo_cliente': '1',
        'numero_cliente': '12345678',
        'cliente_nombre': 'PRUEBA SUNAT',
        'fecha_emision': '2026-01-23',
        'items': [
            {
                'descripcion': 'Producto de prueba',
                'cantidad': 1,
                'precio_unitario': 100.00,
                'total': 100.00,
                'unidad': 'C62'
            }
        ],
        'subtotal': 100.00,
        'igv': 18.00,
        'total': 118.00
    }
    
    success, result = generador.generar_boleta_electronica(datos_prueba)
    print(f"Resultado: {success}")
    print(f"Detalles: {result}")

"""
NOTAS IMPORTANTES:

1. El envío a SUNAT se realiza de forma asincrónica para NO bloquear
   la generación del PDF

2. Los errores de SUNAT se registran pero no impiden la emisión local

3. El usuario puede monitorear el estado en un panel de "Envíos SUNAT"

4. Los CDRs se guardan automáticamente cuando SUNAT los devuelve

5. La validación de certificados es automática cada vez que se inicia
   la aplicación

6. Se pueden generar reportes de emisión para auditoria

7. Todo es compatible con la versión actual de VISO
"""
