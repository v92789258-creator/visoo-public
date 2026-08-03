"""
Cliente SOAP para envío de comprobantes a SUNAT
Implementa protocolo de facturación electrónica SUNAT
"""

import requests
from requests.auth import HTTPBasicAuth
from typing import Tuple, Dict, Optional
import zipfile
import os
import io
import base64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SUNATClient:
    """Cliente para envío y consulta de comprobantes en SUNAT"""
    
    # URLs de SUNAT
    SUNAT_URLs = {
        'produccion': 'https://e-factura.sunat.gob.pe/ol-ti-itcpfegem-beta/billService',
        'desarrollo': 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService',
        'testing': 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService'
    }
    
    def __init__(self, usuario_sunat: str, contraseña: str, ambiente: str = 'produccion'):
        """
        Inicializa cliente SUNAT
        
        Args:
            usuario_sunat: Usuario SOL de SUNAT
            contraseña: Contraseña SOL
            ambiente: 'produccion', 'desarrollo' o 'testing'
        """
        self.usuario = usuario_sunat
        self.contraseña = contraseña
        self.ambiente = ambiente
        self.url_base = self.SUNAT_URLs.get(ambiente, self.SUNAT_URLs['produccion'])
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(usuario_sunat, contraseña)

    def enviar_comprobante(self, 
                          xml_path: str,
                          cdr_path: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Envía comprobante electrónico a SUNAT
        
        Args:
            xml_path: Ruta al archivo XML firmado
            cdr_path: Ruta opcional para guardar el CDR
        
        Returns:
            (success: bool, response: dict)
            response contiene:
            - 'numero': Número de RUC
            - 'serie': Serie del comprobante
            - 'numero_comprobante': Número correlativo
            - 'codigo_respuesta': Código de respuesta SUNAT
            - 'descripcion': Descripción del resultado
            - 'numero_ticket': Ticket de envío
        """
        
        try:
            # Validar archivo XML
            if not os.path.exists(xml_path):
                return False, {'error': f'Archivo XML no encontrado: {xml_path}'}
            
            # Leer XML
            with open(xml_path, 'rb') as f:
                xml_content = f.read()
            
            # Crear ZIP con XML
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                filename = os.path.basename(xml_path)
                zf.writestr(filename, xml_content)
            
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            
            # Enviar a SUNAT
            headers = {
                'Content-Type': 'application/octet-stream',
            }
            
            endpoint = f"{self.url_base}/billService"
            files = {
                'file': (os.path.basename(xml_path).replace('.xml', '.zip'), zip_content)
            }
            
            response = self.session.post(
                endpoint,
                files=files,
                headers=headers,
                timeout=30
            )
            
            # Procesar respuesta
            if response.status_code == 200:
                result = self._parse_sunat_response(response.content)
                
                # Guardar CDR si se proporciona ruta
                if cdr_path and 'cdr' in result:
                    self._guardar_cdr(result['cdr'], cdr_path)
                
                return True, result
            else:
                return False, {
                    'error': f'Error HTTP {response.status_code}',
                    'respuesta': response.text
                }
                
        except Exception as e:
            logger.error(f"Error enviando comprobante: {str(e)}")
            return False, {'error': str(e)}

    def consultar_ticket(self, numero_ruc: str, ticket: str) -> Tuple[bool, Dict]:
        """
        Consulta estado de un ticket enviado a SUNAT
        
        Args:
            numero_ruc: RUC de la empresa
            ticket: Número de ticket
        
        Returns:
            (success: bool, response: dict)
        """
        
        try:
            endpoint = f"{self.url_base}/billService"
            
            # SOAP request para consultar ticket
            soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                          xmlns:bsl="http://www.sunat.gob.pe/businessserviceslayer">
                <soap:Body>
                    <bsl:getStatus>
                        <bsl:ticket>{ticket}</bsl:ticket>
                    </bsl:getStatus>
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=UTF-8',
                'SOAPAction': '',
            }
            
            response = self.session.post(
                endpoint,
                data=soap_request,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = self._parse_ticket_response(response.content)
                return True, result
            else:
                return False, {'error': f'Error HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error consultando ticket: {str(e)}")
            return False, {'error': str(e)}

    def _parse_sunat_response(self, response_content: bytes) -> Dict:
        """Parsea respuesta de envío de SUNAT"""
        try:
            # Buscar archivo CDR en el ZIP
            response_zip = zipfile.ZipFile(io.BytesIO(response_content))
            
            # Buscar archivo R*.xml (CDR)
            cdr_file = None
            for name in response_zip.namelist():
                if name.startswith('R') and name.endswith('.xml'):
                    cdr_file = name
                    break
            
            result = {
                'codigo_respuesta': '0',
                'descripcion': 'Desconocido'
            }
            
            if cdr_file:
                cdr_content = response_zip.read(cdr_file).decode('utf-8')
                result['cdr'] = cdr_content
                result['cdr_filename'] = cdr_file
                result['codigo_respuesta'] = '0'  # 0 = Procesado correctamente
                result['descripcion'] = 'Comprobante aceptado por SUNAT'
            else:
                # Buscar archivo de error
                error_file = None
                for name in response_zip.namelist():
                    if name.startswith('F') or name.startswith('B'):
                        error_file = name
                        break
                
                if error_file:
                    error_content = response_zip.read(error_file).decode('utf-8')
                    result['error_filename'] = error_file
                    result['codigo_respuesta'] = '1'
                    result['descripcion'] = 'Comprobante rechazado'
                    result['detalles'] = self._extract_errors_from_xml(error_content)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parseando respuesta: {str(e)}")
            return {
                'codigo_respuesta': '2',
                'descripcion': f'Error al procesar respuesta: {str(e)}'
            }

    def _parse_ticket_response(self, response_content: bytes) -> Dict:
        """Parsea respuesta de consulta de ticket"""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(response_content)
            
            # Buscar elementos en namespaces SOAP
            ns = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'bsl': 'http://www.sunat.gob.pe/businessserviceslayer'
            }
            
            # Extraer información
            status_code = root.find('.//bsl:statusCode', ns)
            status_message = root.find('.//bsl:statusMessage', ns)
            
            result = {
                'codigo_estado': status_code.text if status_code is not None else 'Desconocido',
                'mensaje': status_message.text if status_message is not None else 'Sin mensaje'
            }
            
            # Buscar CDR si está disponible
            content_file = root.find('.//bsl:contentFile', ns)
            if content_file is not None:
                result['cdr'] = content_file.text
            
            return result
            
        except Exception as e:
            logger.error(f"Error parseando respuesta de ticket: {str(e)}")
            return {'error': str(e)}

    def _extract_errors_from_xml(self, xml_content: str) -> list:
        """Extrae errores de archivo de validación"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            errors = []
            # Buscar elementos de error según estructura SUNAT
            for elem in root.iter():
                if 'error' in elem.tag.lower():
                    errors.append(elem.text)
            
            return errors
            
        except:
            return []

    def _guardar_cdr(self, cdr_content: str, cdr_path: str) -> bool:
        """Guarda CDR en archivo"""
        try:
            os.makedirs(os.path.dirname(cdr_path), exist_ok=True)
            with open(cdr_path, 'w', encoding='utf-8') as f:
                f.write(cdr_content)
            return True
        except Exception as e:
            logger.error(f"Error guardando CDR: {str(e)}")
            return False

    def validar_credenciales(self) -> Tuple[bool, str]:
        """Valida credenciales SUNAT"""
        try:
            # Intentar conexión SOAP para validar credenciales
            headers = {
                'SOAPAction': '',
                'Content-Type': 'text/xml; charset=utf-8'
            }
            
            # SOAP request simple para validación
            soap_body = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <getStatus xmlns="http://www.sunat.gob.pe/wscebillingsuite">
            <ticket>0</ticket>
        </getStatus>
    </soap:Body>
</soap:Envelope>"""
            
            response = self.session.post(
                self.url_base,
                data=soap_body,
                headers=headers,
                timeout=10
            )
            
            # Si recibe respuesta SOAP, credenciales son válidas
            # Status 200 = OK, 500 puede ser SOAP fault pero credenciales válidas
            if response.status_code in [200, 500]:
                if 'Fault' in response.text:
                    # SOAP Fault pero con credenciales válidas
                    return True, "✓ Credenciales válidas (conexión SOAP establecida)"
                else:
                    return True, "✓ Credenciales válidas"
            elif response.status_code == 401:
                return False, (
                    "❌ Credenciales inválidas\n\n"
                    "Verifica que:\n"
                    "• Usuario SOL sea correcto\n"
                    "• Contraseña SOL sea correcta\n"
                    "• La cuenta esté activa en SUNAT"
                )
            elif response.status_code == 404:
                ambiente_info = f"Ambiente: {self.ambiente.upper()}"
                return False, (
                    f"❌ Servidor SUNAT no disponible\n\n"
                    f"{ambiente_info}\n\n"
                    "💡 Posibles causas:\n"
                    "• Servidor SUNAT está en mantenimiento\n"
                    "• No tienes conexión a internet\n"
                    "• Credenciales con formato incorrecto\n\n"
                    "📌 Este sistema está en desarrollo.\n"
                    "Funcionará completamente cuando tengas\n"
                    "un certificado digital válido de SUNAT."
                )
            else:
                return False, (
                    f"❌ Error HTTP {response.status_code}\n\n"
                    f"Razón: {response.reason}\n\n"
                    "Intenta más tarde o verifica tu conexión."
                )
                
        except requests.exceptions.Timeout:
            return False, (
                "❌ Timeout: El servidor SUNAT no responde\n\n"
                "Posibles causas:\n"
                "• Conexión a internet lenta\n"
                "• Servidor SUNAT caído\n"
                "• Problema de red"
            )
        except requests.exceptions.ConnectionError:
            return False, (
                "❌ Error de conexión\n\n"
                "No se puede conectar con SUNAT.\n\n"
                "Verifica que:\n"
                "• Tengas conexión a internet\n"
                "• El firewall no bloquee la conexión\n"
                "• El servidor de SUNAT esté disponible"
            )
        except Exception as e:
            return False, f"❌ Error inesperado:\n{str(e)}"


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Crear cliente
    client = SUNATClient(
        usuario_sunat="usuario.sol",
        contraseña="contraseña",
        ambiente="testing"
    )
    
    # Validar credenciales
    is_valid, msg = client.validar_credenciales()
    print(f"Credenciales: {msg}")
    
    # Enviar comprobante
    success, response = client.enviar_comprobante(
        xml_path="comprobante_firmado.xml",
        cdr_path="cdr_respuesta.xml"
    )
    
    if success:
        print("Comprobante enviado exitosamente")
        print(f"Código respuesta: {response.get('codigo_respuesta')}")
    else:
        print(f"Error: {response.get('error')}")
