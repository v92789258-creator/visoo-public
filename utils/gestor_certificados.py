"""
Gestor de Certificados Digitales SUNAT
Maneja ciclo de vida completo de certificados
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class GestorCertificados:
    """Gestor centralizado de certificados digitales"""
    
    def __init__(self, usuario: str, viso_dir: str):
        """
        Inicializa gestor de certificados
        
        Args:
            usuario: Nombre de usuario en VISO
            viso_dir: Directorio base de VISO
        """
        self.usuario = usuario
        self.viso_dir = viso_dir
        self.certs_dir = os.path.join(viso_dir, usuario, 'data', 'certificados')
        self.registro_certs = os.path.join(self.certs_dir, 'registro_certificados.json')
        
        # Crear directorio si no existe
        os.makedirs(self.certs_dir, exist_ok=True)
        
        # Cargar registro
        self.registro = self._cargar_registro()

    def _cargar_registro(self) -> Dict:
        """Carga registro de certificados"""
        if os.path.exists(self.registro_certs):
            try:
                with open(self.registro_certs, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {'certificados': [], 'actual': None}

    def _guardar_registro(self) -> bool:
        """Guarda registro de certificados"""
        try:
            with open(self.registro_certs, 'w', encoding='utf-8') as f:
                json.dump(self.registro, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error guardando registro: {e}")
            return False

    def importar_certificado(self, ruta_cert: str, ruta_clave: str, 
                            contraseña_clave: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Importa certificado y clave privada
        
        Args:
            ruta_cert: Ruta a archivo de certificado
            ruta_clave: Ruta a archivo de clave privada
            contraseña_clave: Contraseña de la clave privada si aplica
        
        Returns:
            (success: bool, info: dict)
        """
        
        try:
            # Validar archivos existen
            if not os.path.exists(ruta_cert):
                return False, {'error': 'Certificado no encontrado'}
            
            if not os.path.exists(ruta_clave):
                return False, {'error': 'Clave privada no encontrada'}
            
            # Leer y validar certificado
            with open(ruta_cert, 'rb') as f:
                cert_data = f.read()
            
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except:
                return False, {'error': 'Formato de certificado inválido'}
            
            # Extraer información del certificado
            ahora = datetime.now()
            es_valido = cert.not_valid_before <= ahora <= cert.not_valid_after
            
            info_cert = self._extraer_info_certificado(cert, ruta_cert, ruta_clave)
            info_cert['es_valido'] = es_valido
            
            # Calcular días faltantes
            dias_faltantes = (cert.not_valid_after - ahora).days
            info_cert['dias_faltantes'] = dias_faltantes
            
            # Generar ID único
            cert_id = f"cert_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            info_cert['id'] = cert_id
            
            # Copiar archivos al directorio de certificados
            nombre_cert = f"{cert_id}_cert.pem"
            nombre_clave = f"{cert_id}_key.pem"
            
            ruta_cert_destino = os.path.join(self.certs_dir, nombre_cert)
            ruta_clave_destino = os.path.join(self.certs_dir, nombre_clave)
            
            import shutil
            shutil.copy2(ruta_cert, ruta_cert_destino)
            shutil.copy2(ruta_clave, ruta_clave_destino)
            
            info_cert['ruta_cert'] = ruta_cert_destino
            info_cert['ruta_clave'] = ruta_clave_destino
            
            # Agregar al registro
            self.registro['certificados'].append(info_cert)
            
            # Si es el primer certificado, hacerlo el actual
            if self.registro['actual'] is None:
                self.registro['actual'] = cert_id
            
            self._guardar_registro()
            
            return True, info_cert
            
        except Exception as e:
            logger.error(f"Error importando certificado: {e}")
            return False, {'error': str(e)}

    def _extraer_info_certificado(self, cert: x509.Certificate, 
                                  ruta_cert: str, ruta_clave: str) -> Dict:
        """Extrae información del certificado"""
        
        # Obtener datos del sujeto
        subject_dict = {}
        for attr in cert.subject:
            oid_name = attr.oid._name
            subject_dict[oid_name] = attr.value
        
        # Obtener datos del emisor
        issuer_dict = {}
        for attr in cert.issuer:
            oid_name = attr.oid._name
            issuer_dict[oid_name] = attr.value
        
        return {
            'fecha_importacion': datetime.now().isoformat(),
            'sujeto': subject_dict,
            'emisor': issuer_dict,
            'numero_serie': str(cert.serial_number),
            'valido_desde': cert.not_valid_before.isoformat(),
            'valido_hasta': cert.not_valid_after.isoformat(),
            'version': f"v{cert.version.value}",
            'tamaño_bytes_cert': os.path.getsize(ruta_cert),
            'tamaño_bytes_clave': os.path.getsize(ruta_clave),
            'fingerprint_sha256': cert.fingerprint(
                __import__('cryptography.hazmat.primitives.hashes', fromlist=['SHA256']).SHA256()
            ).hex()
        }

    def obtener_certificado_actual(self) -> Optional[Dict]:
        """Obtiene información del certificado actualmente en uso"""
        
        cert_id = self.registro.get('actual')
        if not cert_id:
            return None
        
        # Buscar en el registro
        for cert_info in self.registro['certificados']:
            if cert_info.get('id') == cert_id:
                return cert_info
        
        return None

    def listar_certificados(self) -> List[Dict]:
        """Lista todos los certificados importados"""
        
        certs = []
        for cert_info in self.registro['certificados']:
            # Actualizar estado de validez
            try:
                ruta_cert = cert_info.get('ruta_cert')
                if ruta_cert and os.path.exists(ruta_cert):
                    with open(ruta_cert, 'rb') as f:
                        cert_data = f.read()
                    
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                    ahora = datetime.now()
                    es_valido = cert.not_valid_before <= ahora <= cert.not_valid_after
                    
                    cert_info['es_valido'] = es_valido
                    cert_info['dias_faltantes'] = (cert.not_valid_after - ahora).days
            except:
                cert_info['es_valido'] = False
                cert_info['dias_faltantes'] = -1
            
            certs.append(cert_info)
        
        return certs

    def cambiar_certificado_actual(self, cert_id: str) -> Tuple[bool, str]:
        """Cambia el certificado actualmente en uso"""
        
        # Verificar que el certificado existe
        cert_existe = any(c.get('id') == cert_id for c in self.registro['certificados'])
        
        if not cert_existe:
            return False, "Certificado no encontrado"
        
        self.registro['actual'] = cert_id
        
        if self._guardar_registro():
            return True, f"Certificado actual cambiado a {cert_id}"
        else:
            return False, "Error al guardar cambios"

    def eliminar_certificado(self, cert_id: str) -> Tuple[bool, str]:
        """Elimina un certificado del registro"""
        
        # No permitir eliminar el certificado actual
        if self.registro.get('actual') == cert_id:
            return False, "No se puede eliminar el certificado actual en uso"
        
        # Encontrar y eliminar
        for i, cert_info in enumerate(self.registro['certificados']):
            if cert_info.get('id') == cert_id:
                # Eliminar archivos
                try:
                    if os.path.exists(cert_info.get('ruta_cert', '')):
                        os.remove(cert_info['ruta_cert'])
                    if os.path.exists(cert_info.get('ruta_clave', '')):
                        os.remove(cert_info['ruta_clave'])
                except Exception as e:
                    logger.warning(f"Error eliminando archivos de certificado: {e}")
                
                # Eliminar del registro
                del self.registro['certificados'][i]
                self._guardar_registro()
                
                return True, "Certificado eliminado correctamente"
        
        return False, "Certificado no encontrado"

    def verificar_certificados_proximos_vencer(self, dias_alerta: int = 30) -> List[Dict]:
        """
        Verifica certificados que vencerán próximamente
        
        Args:
            dias_alerta: Número de días para alertar
        
        Returns:
            Lista de certificados próximos a vencer
        """
        
        alertas = []
        ahora = datetime.now()
        fecha_limite = ahora + timedelta(days=dias_alerta)
        
        for cert_info in self.registro['certificados']:
            try:
                ruta_cert = cert_info.get('ruta_cert')
                if ruta_cert and os.path.exists(ruta_cert):
                    with open(ruta_cert, 'rb') as f:
                        cert_data = f.read()
                    
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                    
                    # Si vence dentro del período de alerta
                    if ahora <= cert.not_valid_after <= fecha_limite:
                        cert_info['dias_faltantes'] = (cert.not_valid_after - ahora).days
                        alertas.append(cert_info)
            except Exception as e:
                logger.warning(f"Error verificando certificado: {e}")
        
        return alertas

    def obtener_reporte_certificados(self) -> Dict:
        """Genera reporte de estado de certificados"""
        
        certs = self.listar_certificados()
        
        reporte = {
            'fecha_generacion': datetime.now().isoformat(),
            'total_certificados': len(certs),
            'certificado_actual': self.registro.get('actual'),
            'certificados_validos': sum(1 for c in certs if c.get('es_valido', False)),
            'certificados_vencidos': sum(1 for c in certs if not c.get('es_valido', False)),
            'certificados': []
        }
        
        for cert in certs:
            estado = "✓ Válido" if cert.get('es_valido') else "❌ Vencido"
            dias = cert.get('dias_faltantes', 0)
            
            item = {
                'id': cert.get('id'),
                'estado': estado,
                'dias_faltantes': dias,
                'sujeto': cert.get('sujeto', {}).get('common_name', 'N/A'),
                'numero_serie': cert.get('numero_serie'),
                'valido_hasta': cert.get('valido_hasta'),
                'es_actual': cert.get('id') == self.registro.get('actual')
            }
            
            reporte['certificados'].append(item)
        
        return reporte

    def exportar_configuracion_certs(self, archivo_destino: str) -> Tuple[bool, str]:
        """Exporta información de certificados a JSON (sin las claves privadas)"""
        
        try:
            certs_publicos = []
            
            for cert in self.registro['certificados']:
                cert_export = cert.copy()
                # Remover información sensible
                cert_export.pop('ruta_clave', None)
                certs_publicos.append(cert_export)
            
            export_data = {
                'fecha_exportacion': datetime.now().isoformat(),
                'usuario': self.usuario,
                'certificados': certs_publicos,
                'certificado_actual': self.registro.get('actual')
            }
            
            with open(archivo_destino, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True, f"Configuración exportada a {archivo_destino}"
            
        except Exception as e:
            return False, f"Error al exportar: {str(e)}"


# Ejemplo de uso
if __name__ == "__main__":
    gestor = GestorCertificados("usuario1", "C:/VISO")
    
    # Importar certificado
    success, info = gestor.importar_certificado(
        "ruta/a/certificado.pem",
        "ruta/a/clave_privada.key"
    )
    
    if success:
        print(f"Certificado importado: {info['id']}")
    else:
        print(f"Error: {info.get('error')}")
    
    # Listar certificados
    certs = gestor.listar_certificados()
    for cert in certs:
        print(f"- {cert['id']}: {cert.get('sujeto', {}).get('common_name', 'N/A')}")
    
    # Verificar próximos a vencer
    alertas = gestor.verificar_certificados_proximos_vencer(dias_alerta=30)
    if alertas:
        print(f"\nAlerta: {len(alertas)} certificados próximos a vencer")
    
    # Generar reporte
    reporte = gestor.obtener_reporte_certificados()
    print(f"\nReporte: {reporte['total_certificados']} certificados, "
          f"{reporte['certificados_validos']} válidos, "
          f"{reporte['certificados_vencidos']} vencidos")
