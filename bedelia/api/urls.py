from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views.materias import (
    MateriaViewSet,
    PlanEstudioViewSet,
    PlanMateriaViewSet,
    UnidadAprobableViewSet,
    PreviasViewSet,
    PosPreviasViewSet,
)

router = DefaultRouter()

# Register all viewsets
router.register(r'materias', MateriaViewSet, basename='materia')
router.register(r'planes-estudio', PlanEstudioViewSet, basename='plan-estudio')
router.register(r'planes-materias', PlanMateriaViewSet, basename='plan-materia')
router.register(r'unidades-aprobables', UnidadAprobableViewSet, basename='unidad-aprobable')
router.register(r'previas', PreviasViewSet, basename='previas')
router.register(r'posprevias', PosPreviasViewSet, basename='posprevias')

urlpatterns = [
    path("", include(router.urls)),
]
