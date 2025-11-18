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
    PreviasViewSet,
    PosPreviasViewSet,
)

__all__ = [
    'MateriaViewSet',
    'PlanEstudioViewSet',
    'PlanMateriaViewSet',
    'UnidadAprobableViewSet',
    'RequisitoNodoViewSet',
    'RequisitoItemViewSet',
    'PreviasViewSet',
    'PosPreviasViewSet',
]

