"""Módulo para gestionar archivos adjuntos de pacientes (PDFs y fotos)."""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class GestorAdjuntos:
    """Gestor de archivos adjuntos para pacientes."""
    
    def __init__(self, base_dir: str = None):
        """
        Inicializa el gestor de adjuntos.
        
        Args:
            base_dir: Directorio base donde se almacenarán los adjuntos.
                     Si no se especifica, usa ./VISO/adjuntos
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VISO', 'adjuntos')
        
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def get_carpeta_paciente(self, dni: str, nombre: str = None) -> str:
        """
        Obtiene la ruta de la carpeta del paciente.
        
        Si DNI es 00000000, usa DNI + Nombre normalizado para evitar conflictos.
        Si DNI es diferente, usa solo el DNI.
        """
        # Si DNI es 00000000, usar DNI + nombre normalizado
        if dni == '00000000' and nombre:
            nombre_normalizado = self._normalizar_nombre(nombre)
            carpeta_id = f"{dni}_{nombre_normalizado}"
        else:
            carpeta_id = dni
        
        carpeta = os.path.join(self.base_dir, str(carpeta_id))
        os.makedirs(carpeta, exist_ok=True)
        return carpeta
    
    def _normalizar_nombre(self, nombre: str) -> str:
        """Normaliza un nombre para usarlo como identificador de carpeta."""
        import unicodedata
        # Convertir a minúsculas
        nombre = nombre.lower().strip()
        # Remover acentos
        nombre = unicodedata.normalize('NFD', nombre)
        nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
        # Reemplazar espacios con guiones y remover caracteres especiales
        nombre = ''.join(c if c.isalnum() or c == ' ' else '' for c in nombre)
        nombre = nombre.replace(' ', '_')
        return nombre[:50]  # Limitar a 50 caracteres
    
    def adjuntar_archivo(self, dni: str, ruta_archivo: str, nombre_paciente: str = None) -> Dict[str, any]:
        """
        Adjunta un archivo a la carpeta del paciente.
        
        Args:
            dni: DNI del paciente
            ruta_archivo: Ruta completa del archivo a adjuntar
            nombre_paciente: Nombre del paciente (necesario si DNI es 00000000)
            
        Returns:
            Dict con información del archivo adjuntado
        """
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"El archivo no existe: {ruta_archivo}")
        
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        nombre_archivo = os.path.basename(ruta_archivo)
        
        # Agregar timestamp para evitar duplicados
        nombre_base, ext = os.path.splitext(nombre_archivo)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_final = f"{nombre_base}_{timestamp}{ext}"
        
        ruta_destino = os.path.join(carpeta_paciente, nombre_final)
        
        # Copiar archivo
        shutil.copy2(ruta_archivo, ruta_destino)
        
        # Registrar en metadatos
        info = {
            'nombre_original': nombre_archivo,
            'nombre_almacenado': nombre_final,
            'ruta': ruta_destino,
            'tipo': self._obtener_tipo_archivo(ruta_destino),
            'tamaño': os.path.getsize(ruta_destino),
            'fecha_adjunto': datetime.now().isoformat(),
            'fecha_modificacion_original': datetime.fromtimestamp(os.path.getmtime(ruta_archivo)).isoformat()
        }
        
        # IMPORTANTE: Obtener adjuntos existentes y agregar el nuevo
        adjuntos_existentes = self.obtener_adjuntos(dni, nombre_paciente)
        adjuntos_existentes.append(info)
        self._guardar_metadata(dni, adjuntos_existentes, nombre_paciente)
        
        return info
    
    def obtener_adjuntos(self, dni: str, nombre_paciente: str = None) -> List[Dict]:
        """Obtiene la lista de adjuntos de un paciente."""
        metadata_file = os.path.join(self.get_carpeta_paciente(dni, nombre_paciente), '.metadata.json')
        
        if not os.path.exists(metadata_file):
            return []
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al leer metadatos: {e}")
            return []
    
    def eliminar_adjunto(self, dni: str, nombre_almacenado: str, nombre_paciente: str = None) -> bool:
        """Elimina un adjunto del paciente."""
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        ruta_archivo = os.path.join(carpeta_paciente, nombre_almacenado)
        
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            
            # Actualizar metadatos
            adjuntos = self.obtener_adjuntos(dni, nombre_paciente)
            adjuntos = [a for a in adjuntos if a['nombre_almacenado'] != nombre_almacenado]
            self._guardar_metadata(dni, adjuntos, nombre_paciente)
            return True
        
        return False
    
    def descargar_adjunto(self, dni: str, nombre_almacenado: str, ruta_destino: str, nombre_paciente: str = None) -> bool:
        """Descarga un adjunto a una ubicación específica."""
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        ruta_origen = os.path.join(carpeta_paciente, nombre_almacenado)
        
        if os.path.exists(ruta_origen):
            shutil.copy2(ruta_origen, ruta_destino)
            return True
        
        return False
    
    def obtener_ruta_adjunto(self, dni: str, nombre_almacenado: str, nombre_paciente: str = None) -> Optional[str]:
        """Obtiene la ruta completa de un adjunto."""
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        ruta = os.path.join(carpeta_paciente, nombre_almacenado)
        
        if os.path.exists(ruta):
            return ruta
        return None
    
    def _obtener_tipo_archivo(self, ruta: str) -> str:
        """Determina el tipo de archivo (PDF, FOTO, etc.)."""
        ext = os.path.splitext(ruta)[1].lower()
        
        tipos_fotos = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        tipos_documentos = {'.pdf', '.doc', '.docx', '.xlsx', '.xls', '.txt'}
        
        if ext in tipos_fotos:
            return 'FOTO'
        elif ext in tipos_documentos:
            return 'DOCUMENTO'
        else:
            return 'OTRO'
    
    def _guardar_metadata(self, dni: str, adjuntos: List[Dict], nombre_paciente: str = None):
        """Guarda la metadata de adjuntos en un archivo JSON."""
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        metadata_file = os.path.join(carpeta_paciente, '.metadata.json')
        
        # Asegurar que sea una lista
        if isinstance(adjuntos, dict):
            adjuntos = [adjuntos]
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(adjuntos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar metadatos: {e}")
    
    def limpiar_adjuntos_paciente(self, dni: str, nombre_paciente: str = None) -> bool:
        """Elimina toda la carpeta de adjuntos de un paciente."""
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        
        try:
            shutil.rmtree(carpeta_paciente)
            return True
        except Exception as e:
            print(f"Error al limpiar adjuntos: {e}")
            return False
    
    def obtener_estadisticas(self, dni: str, nombre_paciente: str = None) -> Dict:
        """Obtiene estadísticas de los adjuntos del paciente."""
        adjuntos = self.obtener_adjuntos(dni, nombre_paciente)
        carpeta_paciente = self.get_carpeta_paciente(dni, nombre_paciente)
        
        total_archivos = len(adjuntos)
        total_tamaño = sum(a.get('tamaño', 0) for a in adjuntos)
        
        tipos = {}
        for adj in adjuntos:
            tipo = adj.get('tipo', 'OTRO')
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        tamaño_carpeta = self._calcular_tamaño_carpeta(carpeta_paciente)
        
        return {
            'total_archivos': total_archivos,
            'total_tamaño_bytes': total_tamaño,
            'total_tamaño_mb': round(total_tamaño / (1024 * 1024), 2),
            'tamaño_carpeta_mb': round(tamaño_carpeta / (1024 * 1024), 2),
            'por_tipo': tipos
        }
    
    def _calcular_tamaño_carpeta(self, ruta: str) -> int:
        """Calcula el tamaño total de una carpeta en bytes."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(ruta):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total += os.path.getsize(filepath)
        return total
