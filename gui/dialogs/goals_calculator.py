"""
Goals calculator based on real user data.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils.file_handler import cargar_productos_dashboard, cargar_ventas_dashboard

logger = logging.getLogger(__name__)

AVAILABLE_GOALS = {
    "ventas_totales": {
        "name": "Ventas Totales",
        "description": "Objetivo de ingresos totales del mes",
        "unit": "S/.",
        "type": "currency",
        "default_target": 10000,
        "configurable": False,
    },
    "margen_ganancia": {
        "name": "Margen de Ganancia",
        "description": "Porcentaje de margen objetivo",
        "unit": "%",
        "type": "percentage",
        "default_target": 40,
        "configurable": False,
    },
    "stock_rotacion": {
        "name": "Stock Rotacion",
        "description": "Rotacion del inventario frente a las ventas",
        "unit": "%",
        "type": "percentage",
        "default_target": 60,
        "configurable": False,
    },
    "venta_promedio": {
        "name": "Venta Promedio",
        "description": "Monto promedio por transaccion",
        "unit": "S/.",
        "type": "currency",
        "default_target": 500,
        "configurable": False,
    },
    "ventas_por_dia": {
        "name": "Ventas por dia",
        "description": "Objetivo de ventas promedio por dia",
        "unit": "S/.",
        "type": "currency",
        "default_target": 300,
        "configurable": True,
        "params": {
            "dias": {"label": "Periodo (dias)", "value": 7, "min": 1, "max": 30},
        },
    },
    "transacciones_por_dia": {
        "name": "Transacciones por dia",
        "description": "Cantidad promedio de transacciones por dia",
        "unit": "transacciones",
        "type": "count",
        "default_target": 5,
        "configurable": True,
        "params": {
            "dias": {"label": "Periodo (dias)", "value": 7, "min": 1, "max": 30},
        },
    },
    "ticket_promedio_minimo": {
        "name": "Ticket minimo",
        "description": "Monto minimo promedio por venta",
        "unit": "S/.",
        "type": "currency",
        "default_target": 75,
        "configurable": True,
        "params": {},
    },
    "productos_vendidos": {
        "name": "Productos Vendidos",
        "description": "Cantidad de unidades vendidas",
        "unit": "unidades",
        "type": "count",
        "default_target": 100,
        "configurable": True,
        "params": {
            "dias": {"label": "Periodo (dias)", "value": 30, "min": 1, "max": 90},
        },
    },
    "clientes_nuevos": {
        "name": "Clientes unicos",
        "description": "Cantidad de clientes diferentes",
        "unit": "clientes",
        "type": "count",
        "default_target": 20,
        "configurable": True,
        "params": {
            "dias": {"label": "Periodo (dias)", "value": 30, "min": 1, "max": 90},
        },
    },
}


class GoalsCalculator:
    """Calcula el progreso real de metas basado en datos del usuario."""

    def __init__(self, username: str):
        self.username = username
        self.config_dir = f"VISO/{username}/config"
        self.goals_file = f"{self.config_dir}/goals.json"
        os.makedirs(self.config_dir, exist_ok=True)

    def get_current_month_start(self) -> datetime:
        today = datetime.now()
        return datetime(today.year, today.month, 1)

    def get_current_month_end(self) -> datetime:
        today = datetime.now()
        if today.month == 12:
            return datetime(today.year + 1, 1, 1) - timedelta(days=1)
        return datetime(today.year, today.month + 1, 1) - timedelta(days=1)

    @staticmethod
    def _parse_sale_date(fecha_str) -> Optional[datetime]:
        if not fecha_str:
            return None

        fecha_texto = str(fecha_str).strip()
        if not fecha_texto:
            return None

        if fecha_texto.endswith("Z"):
            fecha_texto = fecha_texto[:-1]

        formatos = (
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        )
        for fmt in formatos:
            try:
                return datetime.strptime(fecha_texto, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _to_float(value) -> float:
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip().replace("S/", "").replace("$", "").replace(" ", "")
            cleaned = cleaned.replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return 0.0

    def _load_goal_config(self) -> dict:
        if not os.path.exists(self.goals_file):
            return {}
        try:
            with open(self.goals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("No se pudo leer goals.json: %s", exc)
            return {}

    def _get_goal_target(self, goal_id: str, default: float) -> float:
        data = self._load_goal_config()
        targets = data.get("targets", {})
        if isinstance(targets, dict):
            return self._to_float(targets.get(goal_id, default)) or float(default)
        return float(default)

    def _get_goal_params(self, goal_id: str) -> Dict:
        data = self._load_goal_config()
        params = data.get("params", {})
        if isinstance(params, dict):
            value = params.get(goal_id, {})
            if isinstance(value, dict):
                return value
        return {}

    def _load_sales(self) -> List[dict]:
        ventas = cargar_ventas_dashboard(self.username, allow_remote_restore=False) or []
        if isinstance(ventas, dict):
            ventas = list(ventas.values())
        if not isinstance(ventas, list):
            return []
        return [venta for venta in ventas if isinstance(venta, dict)]

    def _load_products(self) -> List[dict]:
        productos = cargar_productos_dashboard(self.username, allow_remote_restore=False) or []
        if isinstance(productos, dict):
            productos = list(productos.values())
        if not isinstance(productos, list):
            return []
        return [producto for producto in productos if isinstance(producto, dict)]

    def _iter_sales_since(self, start_date: datetime) -> List[dict]:
        filtered = []
        for venta in self._load_sales():
            fecha = self._parse_sale_date(venta.get("fecha"))
            if fecha and fecha >= start_date:
                filtered.append(venta)
        return filtered

    @staticmethod
    def _iter_sale_items(venta: dict) -> List[dict]:
        for key in ("items", "productos"):
            items = venta.get(key)
            if isinstance(items, list):
                normalized = [item for item in items if isinstance(item, dict)]
                if normalized:
                    return normalized

        sale_level_name = str(venta.get("producto") or venta.get("nombre") or "").strip()
        if sale_level_name:
            return [{
                "nombre": sale_level_name,
                "cantidad": venta.get("cantidad", 1),
                "total": venta.get("total") or venta.get("subtotal") or 0,
            }]
        return []

    def calculate_ventas_totales(self) -> Tuple[float, float]:
        try:
            ventas_mes = self._iter_sales_since(self.get_current_month_start())
            total_ventas = sum(self._to_float(venta.get("total")) for venta in ventas_mes)
            target = self._get_goal_target(
                "ventas_totales",
                AVAILABLE_GOALS["ventas_totales"]["default_target"],
            )
            return total_ventas, target
        except Exception as exc:
            logger.error("Error calculando ventas totales: %s", exc)
            return 0.0, AVAILABLE_GOALS["ventas_totales"]["default_target"]

    def calculate_margen_ganancia(self) -> Tuple[float, float]:
        try:
            productos = self._load_products()
            if not isinstance(productos, list) or not productos:
                return 0.0, AVAILABLE_GOALS["margen_ganancia"]["default_target"]

            margenes = []
            for prod in productos:
                if not isinstance(prod, dict):
                    continue
                precio = self._to_float(prod.get("venta"))
                costo = self._to_float(prod.get("costo"))
                if precio > 0:
                    margenes.append(((precio - costo) / precio) * 100)

            margen_promedio = sum(margenes) / len(margenes) if margenes else 0.0
            target = self._get_goal_target(
                "margen_ganancia",
                AVAILABLE_GOALS["margen_ganancia"]["default_target"],
            )
            return margen_promedio, target
        except Exception as exc:
            logger.error("Error calculando margen: %s", exc)
            return 0.0, AVAILABLE_GOALS["margen_ganancia"]["default_target"]

    def calculate_stock_rotacion(self) -> Tuple[float, float]:
        try:
            productos = self._load_products()
            if not isinstance(productos, list) or not productos:
                return 0.0, AVAILABLE_GOALS["stock_rotacion"]["default_target"]

            month_start = self.get_current_month_start()
            vendidos_por_nombre = {}
            for venta in self._iter_sales_since(month_start):
                for item in self._iter_sale_items(venta):
                    nombre = str(item.get("nombre") or item.get("producto") or "").strip()
                    if not nombre:
                        continue
                    cantidad = int(self._to_float(item.get("cantidad") or 0))
                    vendidos_por_nombre[nombre] = vendidos_por_nombre.get(nombre, 0) + cantidad

            total_vendido = 0.0
            total_stock = 0.0
            for prod in productos:
                if not isinstance(prod, dict):
                    continue
                nombre = str(prod.get("nombre") or "").strip()
                stock = self._to_float(prod.get("stock"))
                total_stock += stock
                total_vendido += vendidos_por_nombre.get(nombre, 0)

            base = total_vendido + total_stock
            rotacion = (total_vendido / base * 100) if base > 0 else 0.0
            target = self._get_goal_target(
                "stock_rotacion",
                AVAILABLE_GOALS["stock_rotacion"]["default_target"],
            )
            return rotacion, target
        except Exception as exc:
            logger.error("Error calculando rotacion: %s", exc)
            return 0.0, AVAILABLE_GOALS["stock_rotacion"]["default_target"]

    def calculate_venta_promedio(self) -> Tuple[float, float]:
        try:
            ventas_mes = self._iter_sales_since(self.get_current_month_start())
            montos = [self._to_float(venta.get("total")) for venta in ventas_mes if self._to_float(venta.get("total")) > 0]
            venta_promedio = sum(montos) / len(montos) if montos else 0.0
            target = self._get_goal_target(
                "venta_promedio",
                AVAILABLE_GOALS["venta_promedio"]["default_target"],
            )
            return venta_promedio, target
        except Exception as exc:
            logger.error("Error calculando venta promedio: %s", exc)
            return 0.0, AVAILABLE_GOALS["venta_promedio"]["default_target"]

    def calculate_ventas_por_dia(self, dias: int = 7) -> Tuple[float, float]:
        try:
            dias = max(1, int(dias or 1))
            fecha_inicio = datetime.now() - timedelta(days=dias)
            ventas_periodo = sum(
                self._to_float(venta.get("total"))
                for venta in self._iter_sales_since(fecha_inicio)
            )
            promedio_diario = ventas_periodo / dias
            target = self._get_goal_target(
                "ventas_por_dia",
                AVAILABLE_GOALS["ventas_por_dia"]["default_target"],
            )
            return promedio_diario, target
        except Exception as exc:
            logger.error("Error calculando ventas por dia: %s", exc)
            return 0.0, AVAILABLE_GOALS["ventas_por_dia"]["default_target"]

    def calculate_transacciones_por_dia(self, dias: int = 7) -> Tuple[float, float]:
        try:
            dias = max(1, int(dias or 1))
            fecha_inicio = datetime.now() - timedelta(days=dias)
            transacciones = len(self._iter_sales_since(fecha_inicio))
            promedio = transacciones / dias
            target = self._get_goal_target(
                "transacciones_por_dia",
                AVAILABLE_GOALS["transacciones_por_dia"]["default_target"],
            )
            return promedio, target
        except Exception as exc:
            logger.error("Error calculando transacciones por dia: %s", exc)
            return 0.0, AVAILABLE_GOALS["transacciones_por_dia"]["default_target"]

    def calculate_productos_vendidos(self, dias: int = 30) -> Tuple[float, float]:
        try:
            dias = max(1, int(dias or 1))
            fecha_inicio = datetime.now() - timedelta(days=dias)
            total_unidades = 0
            for venta in self._iter_sales_since(fecha_inicio):
                for item in self._iter_sale_items(venta):
                    total_unidades += int(self._to_float(item.get("cantidad") or 0))

            target = self._get_goal_target(
                "productos_vendidos",
                AVAILABLE_GOALS["productos_vendidos"]["default_target"],
            )
            return float(total_unidades), target
        except Exception as exc:
            logger.error("Error calculando productos vendidos: %s", exc)
            return 0.0, AVAILABLE_GOALS["productos_vendidos"]["default_target"]

    def calculate_clientes_unicos(self, dias: int = 30) -> Tuple[float, float]:
        try:
            dias = max(1, int(dias or 1))
            fecha_inicio = datetime.now() - timedelta(days=dias)
            clientes_unicos = set()

            for venta in self._iter_sales_since(fecha_inicio):
                cliente_dni = str(venta.get("paciente_dni") or "").strip()
                if cliente_dni and cliente_dni != "00000000":
                    clientes_unicos.add(cliente_dni)

            target = self._get_goal_target(
                "clientes_nuevos",
                AVAILABLE_GOALS["clientes_nuevos"]["default_target"],
            )
            return float(len(clientes_unicos)), target
        except Exception as exc:
            logger.error("Error calculando clientes unicos: %s", exc)
            return 0.0, AVAILABLE_GOALS["clientes_nuevos"]["default_target"]

    def get_goal_progress(self, goal_id: str, params: Optional[Dict] = None) -> Tuple[float, float, int]:
        try:
            effective_params = dict(self._get_goal_params(goal_id))
            if isinstance(params, dict):
                effective_params.update(params)

            if goal_id == "ventas_totales":
                actual, target = self.calculate_ventas_totales()
            elif goal_id == "margen_ganancia":
                actual, target = self.calculate_margen_ganancia()
            elif goal_id == "stock_rotacion":
                actual, target = self.calculate_stock_rotacion()
            elif goal_id == "venta_promedio":
                actual, target = self.calculate_venta_promedio()
            elif goal_id == "ventas_por_dia":
                actual, target = self.calculate_ventas_por_dia(effective_params.get("dias", 7))
            elif goal_id == "transacciones_por_dia":
                actual, target = self.calculate_transacciones_por_dia(effective_params.get("dias", 7))
            elif goal_id == "productos_vendidos":
                actual, target = self.calculate_productos_vendidos(effective_params.get("dias", 30))
            elif goal_id == "clientes_nuevos":
                actual, target = self.calculate_clientes_unicos(effective_params.get("dias", 30))
            elif goal_id == "ticket_promedio_minimo":
                actual, target = self.calculate_venta_promedio()
                target = self._get_goal_target(
                    "ticket_promedio_minimo",
                    AVAILABLE_GOALS["ticket_promedio_minimo"]["default_target"],
                )
            else:
                actual, target = 0.0, 100.0

            porcentaje = int((actual / target) * 100) if target > 0 else 0
            return actual, target, min(porcentaje, 100)
        except Exception as exc:
            logger.error("Error obteniendo progreso de meta %s: %s", goal_id, exc)
            return 0.0, 100.0, 0

    def get_all_goals_progress(self) -> List[Tuple[str, str, float, float, int]]:
        try:
            data = self._load_goal_config()
            goal_ids = data.get("goals", ["ventas_totales", "margen_ganancia", "venta_promedio"])
            params_map = data.get("params", {}) if isinstance(data.get("params"), dict) else {}

            result = []
            for goal_id in goal_ids:
                if goal_id not in AVAILABLE_GOALS:
                    continue
                goal_info = AVAILABLE_GOALS[goal_id]
                goal_params = params_map.get(goal_id, {}) if isinstance(params_map.get(goal_id, {}), dict) else {}
                actual, target, porcentaje = self.get_goal_progress(goal_id, goal_params)
                result.append((goal_id, goal_info["name"], actual, target, porcentaje))

            return result
        except Exception as exc:
            logger.error("Error obteniendo todas las metas: %s", exc)
            return []


if __name__ == "__main__":
    calculator = GoalsCalculator("alex9121")

    print("[INFO] Progreso de metas:")
    print("=" * 80)

    all_goals = calculator.get_all_goals_progress()
    for goal_id, nombre, actual, target, porcentaje in all_goals:
        goal_info = AVAILABLE_GOALS[goal_id]
        unit = goal_info["unit"]
        print(nombre)
        print(f"  Actual: {actual:.2f} {unit}")
        print(f"  Target: {target:.2f} {unit}")
        print(f"  Progreso: {porcentaje}%")
        print()
