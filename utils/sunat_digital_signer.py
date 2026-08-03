"""
Generador de Firmas Digitales para SUNAT
Realiza firmado XML según estándar XmlDsig para comprobantes electrónicos
"""

import xml.etree.ElementTree as ET
from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
from datetime import datetime
from typing import Tuple, Optional
import os


class SUNATDigitalSigner:
    """Realiza firma digital de comprobantes SUNAT según XmlDsig"""
    
    XMLDSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
    
    def __init__(self):
        """Inicializa el generador de firmas"""
        self.backend = default_backend()

    def sign_xml_with_certificate(self, 
                                  xml_content: str,
                                  cert_path: str,
                                  key_path: str,
                                  key_password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Firma un documento XML con certificado digital
        
        Args:
            xml_content: String con el XML a firmar
            cert_path: Ruta al archivo de certificado (.cer o .pem)
            key_path: Ruta a la clave privada (.key o .pfx)
            key_password: Contraseña de la clave privada si es necesaria
        
        Returns:
            (success: bool, signed_xml: str o error_message: str)
        """
        
        try:
            # Cargar certificado
            if not os.path.exists(cert_path):
                return False, f"Certificado no encontrado: {cert_path}"
            
            if not os.path.exists(key_path):
                return False, f"Clave privada no encontrada: {key_path}"
            
            # Parsear XML
            try:
                root = etree.fromstring(xml_content.encode('utf-8'))
            except Exception as e:
                return False, f"XML inválido: {str(e)}"
            
            # Cargar certificado
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                
            try:
                certificate = etree.Certificate(cert_data)
            except:
                # Si es formato PEM
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                certificate = x509.load_pem_x509_certificate(cert_data, self.backend)
            
            # Cargar clave privada
            with open(key_path, 'rb') as f:
                key_data = f.read()
            
            if key_password:
                key_password = key_password.encode()
            
            try:
                private_key = serialization.load_pem_private_key(
                    key_data,
                    password=key_password,
                    backend=self.backend
                )
            except:
                # Intenta con formato PKCS12
                from cryptography.hazmat.primitives.serialization import pkcs12
                try:
                    private_key, loaded_cert, additional_certs = pkcs12.load_key_and_certificates(
                        key_data,
                        key_password,
                        backend=self.backend
                    )
                except Exception as e:
                    return False, f"No se pudo cargar la clave privada: {str(e)}"
            
            # Firmar el XML
            signed_xml = self._add_signature_to_xml(root, private_key, certificate)
            
            return True, etree.tostring(signed_xml, encoding='unicode', pretty_print=True)
            
        except Exception as e:
            return False, f"Error al firmar XML: {str(e)}"

    def _add_signature_to_xml(self, xml_elem, private_key, certificate) -> etree._Element:
        """Añade elemento de firma digital al XML"""
        
        # Crear elemento Signature
        sig_ns = self.XMLDSIG_NS
        signature = etree.Element(f"{{{sig_ns}}}Signature")
        
        # Crear SignedInfo
        signed_info = etree.SubElement(signature, f"{{{sig_ns}}}SignedInfo")
        
        # CanonicalizationMethod
        canon = etree.SubElement(signed_info, f"{{{sig_ns}}}CanonicalizationMethod")
        canon.set("Algorithm", "http://www.w3.org/2001/10/xml-exc-c14n#")
        
        # SignatureMethod
        sig_method = etree.SubElement(signed_info, f"{{{sig_ns}}}SignatureMethod")
        sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")
        
        # Reference
        ref = etree.SubElement(signed_info, f"{{{sig_ns}}}Reference")
        ref.set("URI", "")
        
        # Transforms
        transforms = etree.SubElement(ref, f"{{{sig_ns}}}Transforms")
        transform = etree.SubElement(transforms, f"{{{sig_ns}}}Transform")
        transform.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        
        # DigestMethod
        digest_method = etree.SubElement(ref, f"{{{sig_ns}}}DigestMethod")
        digest_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
        
        # DigestValue
        digest_value = etree.SubElement(ref, f"{{{sig_ns}}}DigestValue")
        xml_digest = self._calculate_digest(xml_elem, "sha1")
        digest_value.text = xml_digest
        
        # Calcular firma
        signed_info_str = etree.tostring(signed_info, method='c14n')
        signature_value = self._sign_data(signed_info_str, private_key)
        
        # SignatureValue
        sig_value = etree.SubElement(signature, f"{{{sig_ns}}}SignatureValue")
        sig_value.text = signature_value
        
        # KeyInfo
        key_info = etree.SubElement(signature, f"{{{sig_ns}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{sig_ns}}}X509Data")
        
        # X509Certificate
        x509_cert = etree.SubElement(x509_data, f"{{{sig_ns}}}X509Certificate")
        cert_b64 = self._get_certificate_b64(certificate)
        x509_cert.text = cert_b64
        
        # --- CORRECCIÓN CRÍTICA PARA SUNAT UBL 2.1 ---
        # La firma DEBE ir dentro de ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent
        ext_ns = "urn:oasis:names:specification:ubl:schema:common:ExtensionComponents-2"
        content_path = f".//{{{ext_ns}}}ExtensionContent"
        extension_content = xml_elem.find(content_path)
        
        if extension_content is not None:
            extension_content.append(signature)
            # logger.info("✅ Firma digital insertada en ExtensionContent")
        else:
            # Fallback: Si no encuentra el contenedor, inserta al inicio (no recomendado)
            xml_elem.insert(0, signature)
            # logger.warning("⚠️ No se encontró ExtensionContent, insertando al inicio")
        
        return xml_elem

    def _calculate_digest(self, elem, algorithm: str) -> str:
        """Calcula el digest de un elemento"""
        elem_str = etree.tostring(elem, method='c14n')
        
        if algorithm == "sha1":
            digest = hashlib.sha1(elem_str).digest()
        elif algorithm == "sha256":
            digest = hashlib.sha256(elem_str).digest()
        else:
            digest = hashlib.sha1(elem_str).digest()
        
        return base64.b64encode(digest).decode('utf-8')

    def _sign_data(self, data: bytes, private_key) -> str:
        """Firma datos con clave privada"""
        try:
            signature = private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error al firmar datos: {str(e)}")

    def _get_certificate_b64(self, certificate) -> str:
        """Obtiene el certificado en base64"""
        try:
            from cryptography import x509
            cert_der = certificate.public_bytes(
                encoding=serialization.Encoding.DER
            )
            return base64.b64encode(cert_der).decode('utf-8')
        except:
            # Si ya es bytes
            if isinstance(certificate, bytes):
                return base64.b64encode(certificate).decode('utf-8')
            return ""

    def verify_certificate(self, cert_path: str) -> Tuple[bool, dict]:
        """
        Verifica validez de certificado
        
        Returns:
            (is_valid: bool, info: dict)
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, self.backend)
            
            info = {
                'subject': dict(x.rfc4514_string().split('=') for x in cert.subject),
                'issuer': dict(x.rfc4514_string().split('=') for x in cert.issuer),
                'not_valid_before': cert.not_valid_before,
                'not_valid_after': cert.not_valid_after,
                'serial_number': str(cert.serial_number),
                'is_valid': datetime.now() > cert.not_valid_before and datetime.now() < cert.not_valid_after
            }
            
            return info['is_valid'], info
            
        except Exception as e:
            return False, {'error': str(e)}


# Ejemplo de uso
if __name__ == "__main__":
    signer = SUNATDigitalSigner()
    
    # Verificar certificado
    is_valid, info = signer.verify_certificate("path/to/certificate.pem")
    print(f"Certificado válido: {is_valid}")
    print(f"Info: {info}")
    
    # Firmar XML
    with open("unsigned.xml", "r") as f:
        xml_content = f.read()
    
    success, result = signer.sign_xml_with_certificate(
        xml_content,
        "path/to/certificate.pem",
        "path/to/private_key.pem",
        "password"
    )
    
    if success:
        with open("signed.xml", "w") as f:
            f.write(result)
        print("XML firmado exitosamente")
    else:
        print(f"Error: {result}")
