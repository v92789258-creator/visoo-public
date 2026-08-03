"""
Módulo de plantillas de boletas.
Contiene generadores para diferentes formatos de boletas.
"""

from .base import PlantillaBase
from .pequena import PlantillaPequena
from .larga import PlantillaLarga
from .extra_larga import PlantillaExtraLarga
from .a4 import PlantillaA4

__all__ = [
    'PlantillaBase',
    'PlantillaPequena',
    'PlantillaLarga',
    'PlantillaExtraLarga',
    'PlantillaA4',
]
