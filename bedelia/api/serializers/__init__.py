"""
Serializers for the API.
"""
from .materias import (
    MateriaSerializer,
    MateriaDetailSerializer,
    PlanEstudioSerializer,
    PlanMateriaSerializer,
    UnidadAprobableSerializer,
    RequisitoNodoSerializer,
    RequisitoNodoTreeSerializer,
    RequisitoItemSerializer,
)

__all__ = [
    'MateriaSerializer',
    'MateriaDetailSerializer',
    'PlanEstudioSerializer',
    'PlanMateriaSerializer',
    'UnidadAprobableSerializer',
    'RequisitoNodoSerializer',
    'RequisitoNodoTreeSerializer',
    'RequisitoItemSerializer',
]

