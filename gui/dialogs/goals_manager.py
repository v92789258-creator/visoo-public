"""
Gestor de metas personalizadas del usuario.
"""

import json
import os
from typing import Dict, List, Tuple

AVAILABLE_GOALS = {
    "ventas_totales": {
        "name": "Ventas Totales",
        "description": "Objetivo de ingresos totales del mes",
        "unit": "S/.",
        "default_value": 10000,
    },
    "nuevos_pacientes": {
        "name": "Nuevos Pacientes",
        "description": "Cantidad de nuevos pacientes a atender",
        "unit": "pacientes",
        "default_value": 50,
    },
    "graduaciones": {
        "name": "Graduaciones",
        "description": "Graduaciones realizadas en el mes",
        "unit": "graduaciones",
        "default_value": 30,
    },
    "margen_ganancia": {
        "name": "Margen de Ganancia",
        "description": "Porcentaje de margen objetivo",
        "unit": "%",
        "default_value": 40,
    },
    "stock_rotacion": {
        "name": "Stock Rotacion",
        "description": "Rotacion de inventario",
        "unit": "%",
        "default_value": 60,
    },
    "satisfaccion": {
        "name": "Satisfaccion Clientes",
        "description": "Calificacion promedio de clientes",
        "unit": "pts",
        "default_value": 4.5,
    },
    "retencion": {
        "name": "Retencion Pacientes",
        "description": "Porcentaje de pacientes que regresan",
        "unit": "%",
        "default_value": 75,
    },
    "venta_promedio": {
        "name": "Venta Promedio",
        "description": "Monto promedio por transaccion",
        "unit": "S/.",
        "default_value": 500,
    },
}


class GoalsManager:
    """Gestor de metas personalizadas del usuario."""

    def __init__(self, username: str):
        self.username = username
        self.config_dir = f"VISO/{username}/config"
        self.goals_file = f"{self.config_dir}/goals.json"
        os.makedirs(self.config_dir, exist_ok=True)

    def get_user_goals(self) -> List[Tuple[str, Dict]]:
        try:
            if not os.path.exists(self.goals_file):
                return self._create_default_goals()

            with open(self.goals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            goals = data.get("goals", [])

            result = []
            for goal_id in goals:
                if goal_id in AVAILABLE_GOALS:
                    result.append((goal_id, AVAILABLE_GOALS[goal_id]))

            return result if result else self._create_default_goals()
        except Exception as exc:
            print(f"[ERROR] Error cargando metas: {exc}")
            return self._create_default_goals()

    def _create_default_goals(self) -> List[Tuple[str, Dict]]:
        default_goal_ids = ["ventas_totales", "nuevos_pacientes", "graduaciones"]
        return [(goal_id, AVAILABLE_GOALS[goal_id]) for goal_id in default_goal_ids]

    def get_goal_info(self, goal_id: str) -> Dict:
        return AVAILABLE_GOALS.get(goal_id, {})

    def get_all_available_goals(self) -> List[Tuple[str, str]]:
        return [(goal_id, info["name"]) for goal_id, info in AVAILABLE_GOALS.items()]

    def save_goals(self, goal_ids: List[str]) -> bool:
        try:
            for goal_id in goal_ids:
                if goal_id not in AVAILABLE_GOALS:
                    print(f"[WARNING] Meta desconocida: {goal_id}")
                    return False

            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.goals_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "goals": goal_ids,
                        "max_goals": 3,
                        "goal_details": {
                            goal_id: AVAILABLE_GOALS[goal_id] for goal_id in goal_ids
                        },
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            return True
        except Exception as exc:
            print(f"[ERROR] Error guardando metas: {exc}")
            return False


if __name__ == "__main__":
    manager = GoalsManager("test_user")

    print("[INFO] Metas disponibles:")
    for goal_id, goal_name in manager.get_all_available_goals():
        print(f"  - {goal_name} ({goal_id})")
