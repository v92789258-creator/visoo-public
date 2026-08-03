"""
Generador de Boletas Integrado con SUNAT
Extiende el generador de boletas para incluir emisión electrónica
"""

import os
import json
from datetime import datetime
from typing import Tuple, Dict, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class GeneradorBoletasSUNAT:
    """Generador de boletas con integración SUNAT"""
    
    def __init__(self, usuario: str, viso_dir: str):
        """
        Inicializa generador
        
        Args:
            usuario: Nombre de usuario en VISO
            viso_dir: Directorio base de VISO
        """
        self.usuario = usuario
        self.viso_dir = viso_dir
        self.config_dir = os.path.join(viso_dir, usuario, 'data', 'sunat')
        self.config_file = os.path.join(self.config_dir, 'config_sunat.json')
        
        # Cargar módulos
        try:
            from utils.sunat_ubl_generator import SUNATUBLGenerator
            from utils.sunat_digital_signer import SUNATDigitalSigner
            from utils.sunat_client import SUNATClient
            from utils.configurador_sunat import ConfiguradorSUNAT
            
            self.ubl_generator = SUNATUBLGenerator()
            self.digital_signer = SUNATDigitalSigner()
            self.configurador = ConfiguradorSUNAT(usuario, viso_dir)
        except ImportError as e:
            logger.warning(f"Módulos SUNAT no disponibles: {e}")
            self.ubl_generator = None
            self.digital_signer = None
            self.configurador = None

    def _formatear_numero_boleta(self, serie, correlativo) -> str:
        serie_str = str(serie or "B001")
        if isinstance(correlativo, int):
            corr_str = f"{correlativo:08d}"
        else:
            corr_txt = str(correlativo or "")
            try:
                corr_str = f"{int(corr_txt):08d}"
            except Exception:
                corr_str = corr_txt.zfill(8)
        return f"{serie_str}{corr_str}"

    def generar_boleta_electronica(self, datos_boleta: Dict, enviar_a_sunat: Optional[bool] = None) -> Tuple[bool, Dict]:
        """
        Genera boleta electrónica completa para SUNAT
        
        Args:
            datos_boleta: Dict con datos de la boleta
                - numero_serie: Serie (B001, etc)
                - numero_correlativo: Número correlativo
                - tipo_cliente: 1=DNI, 6=RUC
                - numero_cliente: DNI o RUC del cliente
                - cliente_nombre: Nombre del cliente
                - fecha_emision: Fecha formato YYYY-MM-DD
                - items: Lista de items con precio unitario, cantidad, descripción
                - subtotal: Subtotal antes de IGV
                - igv: Monto del IGV
                - total: Total final
                - direccion_entrega: Dirección de entrega
        
        Returns:
            (success: bool, result: dict)
            result contiene:
            - xml_path: Ruta al archivo XML firmado
            - ticket_numero: Número de ticket (si se envió a SUNAT)
            - cdr_path: Ruta al CDR (si se procesó)
            - codigo_respuesta: Código de respuesta SUNAT
            - errores: Lista de errores si los hay
        """
        
        result = {
            'success': False,
            'xml_path': None,
            'ticket_numero': None,
            'cdr_path': None,
            'codigo_respuesta': None,
            'errores': []
        }
        
        try:
            # Verificar que SUNAT esté habilitado
            estado_config = self.configurador.get_estado_configuracion()
            if not estado_config.get('habilitado'):
                result['errores'].append("Emisión electrónica no está habilitada")
                return False, result
            
            # Validar configuración necesaria
            if not estado_config.get('tiene_certificado'):
                result['errores'].append("Certificado digital no cargado")
                return False, result
            
            if not estado_config.get('certificado_valido'):
                result['errores'].append("Certificado digital no válido")
                return False, result
            
            # Complementar datos de la boleta
            datos_boleta['ruc'] = estado_config.get('ruc', '')
            datos_boleta['razon_social'] = estado_config.get('razon_social', '')
            datos_boleta['moneda'] = 'PEN'
            datos_boleta['descripcion'] = 'Venta de productos'
            
            # 1. Generar XML UBL 2.1
            xml_content = self.ubl_generator.generar_boleta_xml(datos_boleta)
            
            # 2. Guardar XML sin firmar
            xml_dir = os.path.join(self.config_dir, 'comprobantes', datetime.now().strftime('%Y%m'))
            os.makedirs(xml_dir, exist_ok=True)
            
            numero_boleta = self._formatear_numero_boleta(
                datos_boleta.get('numero_serie', 'B001'),
                datos_boleta.get('numero_correlativo', '1')
            )
            xml_path_sin_firmar = os.path.join(xml_dir, f"{numero_boleta}_sin_firmar.xml")
            
            with open(xml_path_sin_firmar, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # 3. Firmar XML digitalmente
            cert_path = self.configurador.config.get('certificado_path')
            key_path = self.configurador.config.get('clave_privada_path')
            
            if not cert_path or not key_path:
                result['errores'].append("Certificado o clave privada no configurados")
                return False, result
            
            success, signed_xml = self.digital_signer.sign_xml_with_certificate(
                xml_content,
                cert_path,
                key_path
            )
            
            if not success:
                result['errores'].append(f"Error al firmar XML: {signed_xml}")
                return False, result
            
            # 4. Guardar XML firmado
            xml_path_firmado = os.path.join(xml_dir, f"{numero_boleta}.xml")
            with open(xml_path_firmado, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
            
            result['xml_path'] = xml_path_firmado
            
            # 5. Enviar a SUNAT (automático o manual)
            should_send = self.configurador.config.get('enviar_automaticamente')
            if enviar_a_sunat is not None:
                should_send = bool(enviar_a_sunat)

            if should_send:
                try:
                    usuario_sol, contraseña = self.configurador.get_credenciales_sunat()
                    ambiente = self.configurador.config.get('ambiente', 'testing')
                    
                    from utils.sunat_client import SUNATClient
                    client = SUNATClient(usuario_sol, contraseña, ambiente)
                    
                    # Determinar ruta CDR
                    cdr_path = None
                    if self.configurador.config.get('guardar_cdr'):
                        cdr_path = os.path.join(xml_dir, f"{numero_boleta}_CDR.xml")
                    
                    # Enviar comprobante
                    send_success, send_result = client.enviar_comprobante(xml_path_firmado, cdr_path)
                    
                    if send_success:
                        result['ticket_numero'] = send_result.get('numero_ticket')
                        result['cdr_path'] = cdr_path
                        result['codigo_respuesta'] = send_result.get('codigo_respuesta')
                    else:
                        result['errores'].append(f"Error al enviar a SUNAT: {send_result.get('error')}")
                        
                except Exception as e:
                    result['errores'].append(f"Error en conexión SUNAT: {str(e)}")
                    logger.error(f"Error enviando a SUNAT: {e}")
            
            result['success'] = True
            return True, result
            
        except Exception as e:
            result['errores'].append(f"Error general: {str(e)}")
            logger.error(f"Error generando boleta SUNAT: {e}")
            return False, result

    def generar_boleta_local(self, datos_boleta: Dict) -> Tuple[bool, Dict]:
        """
        Genera boleta local sin envío a SUNAT
        (para uso cuando SUNAT no está habilitado)
        """
        result = {
            'success': False,
            'xml_path': None,
            'errores': []
        }
        
        try:
            # Complementar datos
            config_general = self._cargar_config_general()
            datos_boleta['ruc'] = config_general.get('ruc', '')
            datos_boleta['razon_social'] = config_general.get('razon_social', '')
            datos_boleta['moneda'] = 'PEN'
            
            # Generar XML
            xml_content = self.ubl_generator.generar_boleta_xml(datos_boleta)
            
            # Guardar
            xml_dir = os.path.join(self.viso_dir, self.usuario, 'data', 'boletas_xml', datetime.now().strftime('%Y%m'))
            os.makedirs(xml_dir, exist_ok=True)
            
            numero_boleta = self._formatear_numero_boleta(
                datos_boleta.get('numero_serie', 'B001'),
                datos_boleta.get('numero_correlativo', '1')
            )
            xml_path = os.path.join(xml_dir, f"{numero_boleta}.xml")
            
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            result['success'] = True
            result['xml_path'] = xml_path
            return True, result
            
        except Exception as e:
            result['errores'].append(f"Error: {str(e)}")
            return False, result

    def _cargar_config_general(self) -> Dict:
        """Carga configuración general de la empresa"""
        try:
            config_path = os.path.join(self.viso_dir, self.usuario, 'data', 'configuracion_optica.txt')
            datos = {}
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            datos[k] = v
            
            return datos
        except:
            return {}

    def obtener_proximo_numero(self, tipo_comprobante: str = 'boleta') -> str:
        """
        Obtiene próximo número de comprobante
        
        Args:
            tipo_comprobante: 'boleta' o 'factura'
        
        Returns:
            Número formateado
        """
        return self.configurador.generar_proximo_numero(tipo_comprobante)

    def validar_boleta(self, datos_boleta: Dict) -> Tuple[bool, list]:
        """
        Valida que los datos de boleta sean correctos
        
        Returns:
            (is_valid: bool, errores: list)
        """
        errores = []
        
        # Validaciones básicas
        if not datos_boleta.get('numero_serie'):
            errores.append("Serie no especificada")
        
        if not datos_boleta.get('numero_correlativo'):
            errores.append("Número correlativo no especificado")
        
        if not datos_boleta.get('cliente_nombre'):
            errores.append("Nombre del cliente no especificado")
        
        if not datos_boleta.get('items') or len(datos_boleta['items']) == 0:
            errores.append("Sin items en la boleta")
        
        # Validar items
        total_calculado = Decimal('0')
        for item in datos_boleta.get('items', []):
            if not item.get('descripcion'):
                errores.append("Item sin descripción")
            
            if not item.get('precio_unitario'):
                errores.append("Item sin precio unitario")
            
            if not item.get('cantidad'):
                errores.append("Item sin cantidad")
            
            total_item = Decimal(str(item.get('precio_unitario', 0))) * Decimal(str(item.get('cantidad', 0)))
            total_calculado += total_item
        
        # Validar totales
        if total_calculado > 0:
            subtotal = Decimal(str(datos_boleta.get('subtotal', 0)))
            if subtotal != total_calculado:
                errores.append(f"Subtotal no coincide (esperado: {total_calculado}, actual: {subtotal})")
        
        return len(errores) == 0, errores


# Ejemplo de uso
if __name__ == "__main__":
    generador = GeneradorBoletasSUNAT("usuario1", "C:/VISO")
    
    datos_boleta = {
        'numero_serie': 'B001',
        'numero_correlativo': '000001',
        'tipo_cliente': '1',
        'numero_cliente': '12345678',
        'cliente_nombre': 'JUAN PEREZ RODRIGUEZ',
        'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
        'items': [
            {
                'descripcion': 'Lentes oftálmicos',
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
    
    # Validar
    is_valid, errores = generador.validar_boleta(datos_boleta)
    if not is_valid:
        print(f"Errores: {errores}")
    else:
        print("Boleta válida")
        
        # Generar
        success, result = generador.generar_boleta_electronica(datos_boleta)
        if success:
            print(f"Boleta generada: {result['xml_path']}")
        else:
            print(f"Errores: {result['errores']}")
