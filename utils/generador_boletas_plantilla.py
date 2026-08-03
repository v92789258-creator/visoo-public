"""
Generador de boletas (PDFs) - Orquestador modular.
Delegador central que coordina la generación de boletas usando plantillas especializadas.

Este módulo es el punto de entrada público para generar boletas. 
Internamente delega el trabajo a módulos especializados en utils/plantillas/

IMPORTANTE: La lógica de generación de PDFs está separada en módulos especializados:
- utils.plantillas.PlantillaPequena  -> Recibos térmicos 80mm x 150mm
- utils.plantillas.PlantillaLarga    -> Recibos térmicos 80mm x 250mm  
- utils.plantillas.PlantillaExtraLarga -> Recibos térmicos 80mm x 400mm con QR
- utils.plantillas.PlantillaA4       -> Facturas profesionales A4

Ver REFACTORIZACION_PLANTILLAS.md para detalles de la arquitectura.
"""

import os
import json
from datetime import datetime
from utils.file_handler import get_user_file_path
from utils.plantillas import (
    PlantillaPequena,
    PlantillaLarga,
    PlantillaExtraLarga,
    PlantillaA4
)


class GeneradorBoletasPlantilla:
    """
    Orquestador central para la generación de boletas.
    
    Carga la preferencia de plantilla del usuario y delega la generación
    a la clase de plantilla correspondiente.
    
    Uso básico:
        >>> generador = GeneradorBoletasPlantilla('usuario_123')
        >>> ruta = generador.generar_boleta(datos_boleta)
        
    O directamente:
        >>> from utils.generador_boletas_plantilla import generar_boleta_con_plantilla
        >>> ruta = generar_boleta_con_plantilla('usuario_123', datos_boleta)
    """
    
    # Mapeo de tipos de plantilla a clases
    PLANTILLAS_DISPONIBLES = {
        'pequeña': PlantillaPequena,
        'larga': PlantillaLarga,
        'extra_larga': PlantillaExtraLarga,
        'a4': PlantillaA4,
    }
    
    # Configuración de referencia (metadatos solo, la lógica está en cada clase)
    PLANTILLAS = {
        'pequeña': {
            'nombre': 'Plantilla Pequeña',
            'descripcion': 'Recibo térmico compacto (80mm x 150mm)',
            'ancho': 80,
            'alto': 150,
            'margen': 5,
            'font_titulo': 10,
            'font_normal': 8,
            'font_pequeño': 6,
            'lineas_por_producto': 2,
            'mostrar_detalles': False,
            'soporte_qr': False,
        },
        'larga': {
            'nombre': 'Plantilla Larga',
            'descripcion': 'Recibo térmico extendido (80mm x 250mm)',
            'ancho': 80,
            'alto': 250,
            'margen': 5,
            'font_titulo': 10,
            'font_normal': 8,
            'font_pequeño': 7,
            'lineas_por_producto': 2,
            'mostrar_detalles': True,
            'soporte_qr': False,
        },
        'extra_larga': {
            'nombre': 'Plantilla Extra Larga',
            'descripcion': 'Recibo térmico completo (80mm x 400mm) con QR',
            'ancho': 80,
            'alto': 400,
            'margen': 4,
            'font_titulo': 10,
            'font_normal': 8,
            'font_pequeño': 6,
            'lineas_por_producto': 2,
            'mostrar_detalles': True,
            'soporte_qr': True,
        },
        'a4': {
            'nombre': 'Plantilla A4',
            'descripcion': 'Factura profesional A4 (210mm x 297mm)',
            'ancho': 210,
            'alto': 297,
            'margen': 10,
            'font_titulo': 14,
            'font_normal': 10,
            'font_pequeño': 8,
            'lineas_por_producto': 1,
            'mostrar_detalles': True,
            'soporte_qr': True,
        }
    }

    def __init__(self, usuario_id):
        """
        Inicializa el generador con el usuario actual.
        
        Args:
            usuario_id (str or int): ID del usuario actual
        """
        self.usuario_id = str(usuario_id)
        self.plantilla_seleccionada = self.cargar_plantilla_seleccionada()
        print(f"[GeneradorBoletasPlantilla] Usuario: {self.usuario_id}, "
              f"Plantilla cargada: {self.plantilla_seleccionada}")
        
    def cargar_plantilla_seleccionada(self):
        """
        Carga la plantilla seleccionada por el usuario.
        
        Lee desde un archivo JSON de configuración del usuario.
        Si el archivo no existe, retorna 'pequeña' como default.
        
        Returns:
            str: Nombre de la plantilla (pequeña, larga, extra_larga, a4)
        """
        try:
            config_path = get_user_file_path(self.usuario_id, "plantilla_config.json")
            print(f"[Plantilla] Intentando cargar: {config_path}")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    plantilla = config.get('plantilla_seleccionada', 'pequeña')
                    print(f"[Plantilla] Archivo encontrado. Plantilla: {plantilla}")
                    return plantilla
            else:
                print(f"[Plantilla] Archivo no encontrado: {config_path}")
        except Exception as e:
            print(f"[WARN] Error cargando plantilla config: {e}")
        
        print(f"[Plantilla] Usando default: pequeña")
        return 'pequeña'
    
    def guardar_plantilla_seleccionada(self, tipo_plantilla):
        """
        Guarda la plantilla seleccionada por el usuario en archivo JSON.
        
        Args:
            tipo_plantilla (str): Tipo de plantilla (pequeña, larga, extra_larga, a4)
            
        Returns:
            bool: True si se guardó correctamente, False en caso de error
            
        Raises:
            ValueError: Si la plantilla no existe en PLANTILLAS
            
        Example:
            >>> generador.guardar_plantilla_seleccionada('a4')
            True
        """
        if tipo_plantilla not in self.PLANTILLAS:
            raise ValueError(f"Plantilla '{tipo_plantilla}' no existe. "
                           f"Disponibles: {list(self.PLANTILLAS.keys())}")
        
        try:
            config_path = get_user_file_path(self.usuario_id, "plantilla_config.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            config = {
                'plantilla_seleccionada': tipo_plantilla,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            self.plantilla_seleccionada = tipo_plantilla
            print(f"[OK] Plantilla '{tipo_plantilla}' guardada correctamente.")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar plantilla: {e}")
            return False
    
    def obtener_config_plantilla(self):
        """
        Retorna la configuración de la plantilla seleccionada.
        
        Retorna un diccionario con metadata sobre la plantilla actual.
        La lógica de generación está en la clase plantilla correspondiente.
        
        Returns:
            dict: Configuración con claves como ancho, alto, margen, fonts, etc.
        """
        return self.PLANTILLAS.get(self.plantilla_seleccionada, 
                                   self.PLANTILLAS['pequeña'])
    
    def generar_boleta(self, datos_boleta, ruta_salida=None, tamano_logo_px=None):
        """
        Genera una boleta en PDF según la plantilla seleccionada.
        
        Método principal que delega el trabajo a la clase de plantilla correspondiente.
        
        Args:
            datos_boleta (dict): Diccionario con datos de la boleta. Debe contener:
                - nombre_optica: Nombre del negocio
                - ruc: RUC de la empresa
                - numero_boleta: Número único de la boleta
                - fecha: Fecha de emisión (str)
                - cliente: Nombre del cliente
                - dni: DNI del cliente
                - productos: Lista de dict con:
                  - nombre: Nombre del producto
                  - cantidad: Cantidad vendida
                  - precio: Precio unitario
                  - total: Precio total (cantidad * precio)
                - subtotal: Subtotal antes de IGV
                - igv: Monto de IGV
                - total: Total a pagar
                - monto_letras: Total en letras (ej: "ciento cincuenta soles")
                - metodo_pago: Forma de pago (Efectivo, Tarjeta, etc)
                - vendedor: Nombre del vendedor
                
            ruta_salida (str, optional): Ruta donde guardar el PDF. Si es None,
                se genera automáticamente en el directorio del usuario.
                
            tamano_logo_px (int, optional): Tamaño del logo en píxeles.
                Si es None, se usa el tamaño default de cada plantilla.
        
        Returns:
            str: Ruta absoluta del PDF generado
            
        Raises:
            ValueError: Si la plantilla seleccionada no existe
            
        Example:
            >>> generador = GeneradorBoletasPlantilla('usuario_123')
            >>> datos = {
            ...     'nombre_optica': 'Mi Óptica',
            ...     'ruc': '20123456789',
            ...     'numero_boleta': 'B-001-00001',
            ...     'cliente': 'Juan Pérez',
            ...     'dni': '12345678',
            ...     'productos': [
            ...         {'nombre': 'Anteojos', 'cantidad': 1, 'precio': 150.00, 'total': 150.00}
            ...     ],
            ...     'subtotal': 150.00,
            ...     'igv': 27.00,
            ...     'total': 177.00,
            ...     'monto_letras': 'ciento setenta y siete soles',
            ...     'metodo_pago': 'Efectivo',
            ...     'vendedor': 'Juan'
            ... }
            >>> ruta = generador.generar_boleta(datos)
            >>> print(f"Boleta generada en: {ruta}")
        """
        print(f"[generar_boleta] Generando con plantilla: {self.plantilla_seleccionada}")
        
        # Obtener la clase de plantilla correspondiente
        clase_plantilla = self.PLANTILLAS_DISPONIBLES.get(
            self.plantilla_seleccionada,
            PlantillaPequena  # Default por si acaso
        )
        
        # Instanciar la plantilla y generar
        generador = clase_plantilla(self.usuario_id)
        generador.tamano_logo_px = tamano_logo_px
        
        return generador.generar(datos_boleta, ruta_salida)


def generar_boleta_con_plantilla(usuario_id, datos_boleta, ruta_salida=None):
    """
    Función helper para generar boletas usando la plantilla del usuario.
    
    Esta es la forma más simple y directa de generar una boleta.
    Se recomienda usarla para llamadas simples desde otros módulos.
    
    Args:
        usuario_id (str or int): ID del usuario
        datos_boleta (dict): Diccionario con datos de la boleta
        ruta_salida (str, optional): Ruta donde guardar el PDF
    
    Returns:
        str: Ruta absoluta del PDF generado
        
    Example:
        >>> from utils.generador_boletas_plantilla import generar_boleta_con_plantilla
        >>> ruta = generar_boleta_con_plantilla('usuario_123', datos_boleta)
        >>> print(f"Boleta generada: {ruta}")
    """
    generador = GeneradorBoletasPlantilla(usuario_id)
    return generador.generar_boleta(datos_boleta, ruta_salida)

