"""
Gestor de Configuración SUNAT
Maneja credenciales, certificados y configuración para emisión electrónica
"""

import os
import json
from typing import Dict, Tuple, Optional
from pathlib import Path
import hashlib
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from datetime import datetime


class ConfiguradorSUNAT:
    """Gestor central de configuración SUNAT"""
    
    def __init__(self, usuario: str, viso_dir: str):
        """
        Inicializa el configurador
        
        Args:
            usuario: Nombre de usuario en VISO
            viso_dir: Directorio base de VISO
        """
        self.usuario = usuario
        self.viso_dir = viso_dir
        self.config_dir = os.path.join(viso_dir, usuario, 'data', 'sunat')
        self.certs_dir = os.path.join(self.config_dir, 'certificados')
        self.config_file = os.path.join(self.config_dir, 'config_sunat.json')
        
        # Crear directorios si no existen
        os.makedirs(self.certs_dir, exist_ok=True)
        
        # Cargar configuración existente
        self.config = self._cargar_config()

    def _cargar_config(self) -> Dict:
        """Carga configuración desde archivo"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return self._config_default()

    def _config_default(self) -> Dict:
        """Retorna configuración por defecto"""
        return {
            'habilitado': False,
            'ambiente': 'testing',  # testing, produccion
            'usuario_sol': '',
            'contraseña_sol_encriptada': '',
            'ruc': '',
            'razon_social': '',
            'certificado_path': '',
            'clave_privada_path': '',
            'numero_serie_inicio': {
                'factura': 'F001',
                'boleta': 'B001'
            },
            'numero_correlativo_actual': {
                'factura': 0,
                'boleta': 0
            },
            'enviar_automaticamente': False,
            'guardar_cdr': True,
            'respaldo_automatico': True,
            'fecha_creacion': datetime.now().isoformat(),
            'fecha_ultima_sincronizacion': None
        }

    def guardar_config(self) -> Tuple[bool, str]:
        """Guarda configuración a archivo"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True, "Configuración guardada"
        except Exception as e:
            return False, f"Error al guardar: {str(e)}"

    def set_credenciales_sunat(self, usuario_sol: str, contraseña: str) -> Tuple[bool, str]:
        """
        Configura credenciales SUNAT
        
        Args:
            usuario_sol: Usuario SOL
            contraseña: Contraseña SOL
        
        Returns:
            (success: bool, message: str)
        """
        try:
            self.config['usuario_sol'] = usuario_sol
            self.config['contraseña_sol_encriptada'] = self._encriptar(contraseña)
            
            success, msg = self.guardar_config()
            return success, "Credenciales configuradas" if success else msg
        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_credenciales_sunat(self) -> Tuple[Optional[str], Optional[str]]:
        """Obtiene credenciales guardadas"""
        usuario = self.config.get('usuario_sol')
        contraseña_enc = self.config.get('contraseña_sol_encriptada')
        
        if contraseña_enc:
            contraseña = self._desencriptar(contraseña_enc)
            return usuario, contraseña
        
        return usuario, None

    def subir_certificado(self, cert_path: str, clave_privada_path: str) -> Tuple[bool, str]:
        """
        Sube certificado y clave privada a configuración
        
        Args:
            cert_path: Ruta a archivo .cer o .pem
            clave_privada_path: Ruta a archivo de clave privada
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Validar que existan los archivos
            if not os.path.exists(cert_path):
                return False, "Certificado no encontrado"
            
            if not os.path.exists(clave_privada_path):
                return False, "Clave privada no encontrada"
            
            # Copiar archivos a directorio de configuración
            cert_dest = os.path.join(self.certs_dir, f"certificado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pem")
            key_dest = os.path.join(self.certs_dir, f"clave_privada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.key")
            
            import shutil
            shutil.copy2(cert_path, cert_dest)
            shutil.copy2(clave_privada_path, key_dest)
            
            # Verificar certificado
            is_valid, info = self._verificar_certificado(cert_dest)
            if not is_valid:
                return False, f"Certificado inválido: {info.get('error', 'Desconocido')}"
            
            # Guardar rutas en configuración
            self.config['certificado_path'] = cert_dest
            self.config['clave_privada_path'] = key_dest
            self.config['certificado_info'] = info
            
            success, msg = self.guardar_config()
            return success, msg
            
        except Exception as e:
            return False, f"Error al subir certificado: {str(e)}"

    def get_certificado_actual(self) -> Optional[Dict]:
        """Obtiene información del certificado actual"""
        cert_path = self.config.get('certificado_path')
        
        if cert_path and os.path.exists(cert_path):
            is_valid, info = self._verificar_certificado(cert_path)
            return {
                'valido': is_valid,
                'path': cert_path,
                'info': info
            }
        
        return None

    def _verificar_certificado(self, cert_path: str) -> Tuple[bool, Dict]:
        """Verifica validez de certificado"""
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            ahora = datetime.now()
            es_valido = cert.not_valid_before <= ahora <= cert.not_valid_after
            
            # Extraer información
            subject_dict = {}
            for attr in cert.subject:
                subject_dict[attr.oid._name] = attr.value
            
            info = {
                'valido': es_valido,
                'sujeto': subject_dict,
                'emitido_por': str(cert.issuer),
                'valido_desde': cert.not_valid_before.isoformat(),
                'valido_hasta': cert.not_valid_after.isoformat(),
                'numero_serie': str(cert.serial_number)
            }
            
            return es_valido, info
            
        except Exception as e:
            return False, {'error': str(e)}

    def set_datos_empresa(self, ruc: str, razon_social: str, direccion: str, 
                         departamento: str, provincia: str, distrito: str) -> Tuple[bool, str]:
        """Configura datos de la empresa"""
        try:
            self.config['ruc'] = ruc
            self.config['razon_social'] = razon_social
            self.config['direccion'] = direccion
            self.config['departamento'] = departamento
            self.config['provincia'] = provincia
            self.config['distrito'] = distrito
            
            success, msg = self.guardar_config()
            return success, msg
        except Exception as e:
            return False, f"Error: {str(e)}"

    def habilitar_emision_electronica(self, habilitar: bool = True) -> Tuple[bool, str]:
        """Habilita o deshabilita emisión electrónica"""
        # Validar que esté todo configurado
        if habilitar:
            validaciones = [
                ('usuario_sol', 'Usuario SOL no configurado'),
                ('ruc', 'RUC no configurado'),
                ('certificado_path', 'Certificado no cargado'),
                ('clave_privada_path', 'Clave privada no cargada'),
            ]
            
            for campo, mensaje in validaciones:
                if not self.config.get(campo):
                    return False, mensaje
            
            # Verificar que el certificado sea válido
            is_valid, info = self._verificar_certificado(self.config['certificado_path'])
            if not is_valid:
                return False, f"Certificado no válido: {info.get('error', 'Desconocido')}"
        
        self.config['habilitado'] = habilitar
        success, msg = self.guardar_config()
        return success, f"Emisión electrónica {'habilitada' if habilitar else 'deshabilitada'}"

    def generar_proximo_numero(self, tipo: str = 'boleta') -> str:
        """
        Genera próximo número de comprobante
        
        Args:
            tipo: 'factura' o 'boleta'
        
        Returns:
            Número de comprobante formateado
        """
        numero_actual = self.config['numero_correlativo_actual'].get(tipo, 0)
        numero_nuevo = numero_actual + 1
        self.config['numero_correlativo_actual'][tipo] = numero_nuevo
        self.guardar_config()
        
        serie = self.config['numero_serie_inicio'].get(tipo, 'B001')
        return f"{serie}{numero_nuevo:08d}"

    def _encriptar(self, texto: str) -> str:
        """Encripta texto (simple, para producción usar mejor método)"""
        return hashlib.sha256(texto.encode()).hexdigest()[:20]

    def _desencriptar(self, hash_texto: str) -> Optional[str]:
        """Desencripta - nota: esto es placeholder, usar mejor sistema"""
        # Para producción, usar cryptography.fernet
        return None

    def get_estado_configuracion(self) -> Dict:
        """Retorna estado actual de la configuración"""
        return {
            'habilitado': self.config.get('habilitado', False),
            'tiene_ruc': bool(self.config.get('ruc')),
            'tiene_credenciales': bool(self.config.get('usuario_sol')),
            'tiene_certificado': bool(self.config.get('certificado_path')) and os.path.exists(
                self.config.get('certificado_path', '')
            ),
            'certificado_valido': self._verificar_certificado(
                self.config.get('certificado_path', '')
            )[0] if self.config.get('certificado_path') else False,
            'ambiente': self.config.get('ambiente', 'testing'),
            'razon_social': self.config.get('razon_social', ''),
            'numero_boleta_actual': self.config.get('numero_correlativo_actual', {}).get('boleta', 0),
        }

    def exportar_configuracion(self, archivo_destino: str) -> Tuple[bool, str]:
        """Exporta configuración a archivo (sin credenciales)"""
        try:
            config_exportar = self.config.copy()
            # Remover información sensible
            config_exportar.pop('contraseña_sol_encriptada', None)
            config_exportar.pop('certificado_path', None)
            config_exportar.pop('clave_privada_path', None)
            
            with open(archivo_destino, 'w', encoding='utf-8') as f:
                json.dump(config_exportar, f, indent=2, ensure_ascii=False)
            
            return True, f"Configuración exportada a {archivo_destino}"
        except Exception as e:
            return False, f"Error al exportar: {str(e)}"


# Ejemplo de uso
if __name__ == "__main__":
    configurador = ConfiguradorSUNAT("usuario1", "C:/VISO")
    
    # Configurar credenciales
    success, msg = configurador.set_credenciales_sunat("usuario.sol", "contraseña")
    print(f"Credenciales: {msg}")
    
    # Configurar datos empresa
    success, msg = configurador.set_datos_empresa(
        ruc="20131312955",
        razon_social="OPTICA TEST S.A.C.",
        direccion="Av. Principal 123",
        departamento="LIMA",
        provincia="LIMA",
        distrito="LIMA"
    )
    print(f"Datos empresa: {msg}")
    
    # Ver estado
    estado = configurador.get_estado_configuracion()
    print(f"Estado: {estado}")
