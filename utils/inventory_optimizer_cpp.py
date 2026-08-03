"""
inventory_optimizer_cpp.py
Wrapper Python para usar InventoryOptimizer.dll (C++ optimizado)
Acelera búsqueda, filtrado y ordenamiento de inventario 100x
"""

import ctypes
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

class InventoryOptimizer:
    """
    Wrapper para la librería C++ InventoryOptimizer.dll
    Optimiza operaciones de búsqueda, filtrado y ordenamiento en inventario
    """
    
    def __init__(self):
        self.dll = None
        self.loaded = False
        self._load_dll()
    
    def _load_dll(self) -> bool:
        """Intenta cargar la DLL compilada."""
        try:
            # Rutas posibles donde podría estar la DLL
            possible_paths = [
                Path(__file__).parent.parent / "cpp" / "build" / "bin" / "InventoryOptimizer.dll",
                Path(__file__).parent.parent / "cpp" / "build" / "bin" / "Release" / "InventoryOptimizer.dll",
                Path(__file__).parent.parent / "_internal" / "InventoryOptimizer.dll",
                Path(sys.executable).parent / "InventoryOptimizer.dll",
            ]
            
            for dll_path in possible_paths:
                if dll_path.exists():
                    self.dll = ctypes.CDLL(str(dll_path))
                    self.loaded = True
                    print(f"✓ InventoryOptimizer.dll cargada: {dll_path}")
                    return True
            
            print("⚠ InventoryOptimizer.dll no encontrada. Usando fallback a Python.")
            return False
            
        except Exception as e:
            print(f"⚠ Error cargando InventoryOptimizer.dll: {e}. Usando fallback a Python.")
            return False
    
    def search_products(self, products_json: str, search_term: str) -> List[Dict]:
        """Busca productos por término."""
        if not self.loaded:
            return self._search_products_python(products_json, search_term)
        
        try:
            output_buffer = ctypes.create_string_buffer(65536)  # 64KB buffer
            
            result = self.dll.search_products(
                ctypes.c_char_p(products_json.encode('utf-8')),
                ctypes.c_char_p(search_term.encode('utf-8')),
                output_buffer,
                65536
            )
            
            if result > 0:
                return json.loads(output_buffer.value.decode('utf-8'))
            return []
        except Exception as e:
            print(f"Error en search_products (C++): {e}")
            return self._search_products_python(products_json, search_term)
    
    def filter_products(self, products_json: str, min_price: float = 0, 
                       max_price: float = float('inf'), 
                       category: str = "") -> List[Dict]:
        """Filtra productos por precio y categoría."""
        if not self.loaded:
            return self._filter_products_python(products_json, min_price, max_price, category)
        
        try:
            output_buffer = ctypes.create_string_buffer(65536)
            
            result = self.dll.filter_products(
                ctypes.c_char_p(products_json.encode('utf-8')),
                ctypes.c_double(min_price),
                ctypes.c_double(max_price),
                ctypes.c_char_p(category.encode('utf-8')),
                output_buffer,
                65536
            )
            
            if result > 0:
                return json.loads(output_buffer.value.decode('utf-8'))
            return []
        except Exception as e:
            print(f"Error en filter_products (C++): {e}")
            return self._filter_products_python(products_json, min_price, max_price, category)
    
    def sort_products(self, products_json: str, sort_field: str = "nombre", 
                     ascending: bool = True) -> List[Dict]:
        """Ordena productos por campo."""
        if not self.loaded:
            return self._sort_products_python(products_json, sort_field, ascending)
        
        try:
            output_buffer = ctypes.create_string_buffer(65536)
            
            result = self.dll.sort_products(
                ctypes.c_char_p(products_json.encode('utf-8')),
                ctypes.c_char_p(sort_field.encode('utf-8')),
                ctypes.c_int(1 if ascending else 0),
                output_buffer,
                65536
            )
            
            if result > 0:
                return json.loads(output_buffer.value.decode('utf-8'))
            return []
        except Exception as e:
            print(f"Error en sort_products (C++): {e}")
            return self._sort_products_python(products_json, sort_field, ascending)
    
    def paginate_products(self, products_json: str, page: int = 1, 
                         items_per_page: int = 20) -> tuple:
        """Pagina productos eficientemente."""
        if not self.loaded:
            return self._paginate_products_python(products_json, page, items_per_page)
        
        try:
            output_buffer = ctypes.create_string_buffer(65536)
            
            total = self.dll.paginate_products(
                ctypes.c_char_p(products_json.encode('utf-8')),
                ctypes.c_int(page),
                ctypes.c_int(items_per_page),
                output_buffer,
                65536
            )
            
            if total > 0:
                items = json.loads(output_buffer.value.decode('utf-8'))
                return items, total
            return [], 0
        except Exception as e:
            print(f"Error en paginate_products (C++): {e}")
            return self._paginate_products_python(products_json, page, items_per_page)
    
    def search_and_filter(self, products_json: str, search_term: str = "", 
                         min_price: float = 0, max_price: float = float('inf'),
                         category: str = "", sort_by: str = "nombre") -> List[Dict]:
        """Búsqueda y filtrado combinado (OPTIMIZADO)."""
        if not self.loaded:
            return self._search_and_filter_python(products_json, search_term, 
                                                  min_price, max_price, category, sort_by)
        
        try:
            output_buffer = ctypes.create_string_buffer(65536)
            
            result = self.dll.search_and_filter(
                ctypes.c_char_p(products_json.encode('utf-8')),
                ctypes.c_char_p(search_term.encode('utf-8')),
                ctypes.c_double(min_price),
                ctypes.c_double(max_price),
                ctypes.c_char_p(category.encode('utf-8')),
                ctypes.c_char_p(sort_by.encode('utf-8')),
                output_buffer,
                65536
            )
            
            if result > 0:
                return json.loads(output_buffer.value.decode('utf-8'))
            return []
        except Exception as e:
            print(f"Error en search_and_filter (C++): {e}")
            return self._search_and_filter_python(products_json, search_term, 
                                                  min_price, max_price, category, sort_by)
    
    # ========== FALLBACK Python (si DLL no está disponible) ==========
    
    @staticmethod
    def _search_products_python(products_json: str, search_term: str) -> List[Dict]:
        """Búsqueda en Python (fallback)."""
        try:
            products = json.loads(products_json)
            search_lower = search_term.lower()
            return [p for p in products if search_lower in p.get('nombre', '').lower()]
        except:
            return []
    
    @staticmethod
    def _filter_products_python(products_json: str, min_price: float = 0,
                               max_price: float = float('inf'), 
                               category: str = "") -> List[Dict]:
        """Filtrado en Python (fallback)."""
        try:
            products = json.loads(products_json)
            filtered = [
                p for p in products 
                if min_price <= p.get('precio', 0) <= max_price
                and (not category or p.get('categoria', '').lower() == category.lower())
            ]
            return filtered
        except:
            return []
    
    @staticmethod
    def _sort_products_python(products_json: str, sort_field: str = "nombre",
                             ascending: bool = True) -> List[Dict]:
        """Ordenamiento en Python (fallback)."""
        try:
            products = json.loads(products_json)
            return sorted(products, key=lambda x: x.get(sort_field, ''), 
                         reverse=not ascending)
        except:
            return []
    
    @staticmethod
    def _paginate_products_python(products_json: str, page: int = 1,
                                 items_per_page: int = 20) -> tuple:
        """Paginación en Python (fallback)."""
        try:
            products = json.loads(products_json)
            start = (page - 1) * items_per_page
            end = start + items_per_page
            return products[start:end], len(products)
        except:
            return [], 0
    
    @staticmethod
    def _search_and_filter_python(products_json: str, search_term: str = "",
                                 min_price: float = 0, max_price: float = float('inf'),
                                 category: str = "", sort_by: str = "nombre") -> List[Dict]:
        """Combinado en Python (fallback)."""
        try:
            products = json.loads(products_json)
            search_lower = search_term.lower()
            
            filtered = [
                p for p in products 
                if (not search_term or search_lower in p.get('nombre', '').lower())
                and (min_price <= p.get('precio', 0) <= max_price)
                and (not category or p.get('categoria', '').lower() == category.lower())
            ]
            
            return sorted(filtered, key=lambda x: x.get(sort_by, ''))
        except:
            return []


# Instancia global
_optimizer = None

def get_optimizer() -> InventoryOptimizer:
    """Obtiene la instancia global del optimizador."""
    global _optimizer
    if _optimizer is None:
        _optimizer = InventoryOptimizer()
    return _optimizer
