"""Small client for looking up Peruvian RUC data."""

import json
import os
import time
from typing import Dict, Optional, Tuple

import requests


API_URL = "https://dniruc.apisperu.com/api/v1/ruc"
# Set SUNAT_DEFAULT_TOKEN locally when SUNAT access is enabled.
DEFAULT_TOKEN = os.getenv("SUNAT_DEFAULT_TOKEN", "")


def consultar_ruc(ruc: str, token: Optional[str] = None) -> Tuple[bool, Dict]:
    """Query SUNAT data for an 11-digit RUC."""
    token = token or DEFAULT_TOKEN
    ruc_clean = ruc.replace("-", "").replace(" ", "")
    if not ruc_clean.isdigit() or len(ruc_clean) != 11:
        return False, {"error": "RUC debe tener 11 dígitos"}
    if not token:
        return False, {"error": "Configura SUNAT_DEFAULT_TOKEN para consultar SUNAT"}

    try:
        response = requests.get(
            f"{API_URL}/{ruc_clean}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            return True, response.json()
        if response.status_code == 404:
            return False, {"error": "RUC no encontrado"}
        if response.status_code == 401:
            return False, {"error": "Token inválido o expirado"}
        return False, {"error": f"Error API: {response.status_code}"}
    except requests.exceptions.Timeout:
        return False, {"error": "Timeout: API no responde (>10s)"}
    except requests.exceptions.ConnectionError:
        return False, {"error": "Error de conexión: verificar internet"}
    except json.JSONDecodeError:
        return False, {"error": "Respuesta JSON inválida"}
    except Exception as exc:
        return False, {"error": f"Error: {exc}"}


def validar_ruc_formato(ruc: str) -> bool:
    """Return whether a value has the expected 11-digit RUC format."""
    ruc_clean = ruc.replace("-", "").replace(" ", "")
    return ruc_clean.isdigit() and len(ruc_clean) == 11


def formatear_ruc(ruc: str) -> str:
    """Format an 11-digit RUC as XX-XXXXXX-XX."""
    ruc_clean = ruc.replace("-", "").replace(" ", "")
    return f"{ruc_clean[:2]}-{ruc_clean[2:8]}-{ruc_clean[8:]}" if len(ruc_clean) == 11 else ruc


def extraer_datos_relevantes(respuesta_sunat: Dict) -> Dict:
    """Keep the SUNAT fields used by the optical-management UI."""
    return {
        "ruc": respuesta_sunat.get("ruc", ""),
        "razonSocial": respuesta_sunat.get("razonSocial", ""),
        "nombreComercial": respuesta_sunat.get("nombreComercial") or respuesta_sunat.get("razonSocial", ""),
        "estado": respuesta_sunat.get("estado", ""),
        "condicion": respuesta_sunat.get("condicion", ""),
        "direccion": respuesta_sunat.get("direccion", ""),
        "departamento": respuesta_sunat.get("departamento", ""),
        "provincia": respuesta_sunat.get("provincia", ""),
        "distrito": respuesta_sunat.get("distrito", ""),
        "ubigeo": respuesta_sunat.get("ubigeo", ""),
        "consultado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
