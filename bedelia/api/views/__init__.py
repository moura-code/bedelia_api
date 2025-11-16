"""
Views for the API.
"""
from .materias import (
    MateriaViewSet,
    PlanEstudioViewSet,
    PlanMateriaViewSet,
    UnidadAprobableViewSet,
    RequisitoNodoViewSet,
    RequisitoItemViewSet,
)

__all__ = [
    'MateriaViewSet',
    'PlanEstudioViewSet',
    'PlanMateriaViewSet',
    'UnidadAprobableViewSet',
    'RequisitoNodoViewSet',
    'RequisitoItemViewSet',
]

