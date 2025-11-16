from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views.materias import (
    MateriaViewSet,
    PlanEstudioViewSet,
    PlanMateriaViewSet,
    UnidadAprobableViewSet,
    RequisitoNodoViewSet,
    RequisitoItemViewSet,
)

router = DefaultRouter()

# Register all viewsets
router.register(r'materias', MateriaViewSet, basename='materia')
router.register(r'planes-estudio', PlanEstudioViewSet, basename='plan-estudio')
router.register(r'planes-materias', PlanMateriaViewSet, basename='plan-materia')
router.register(r'unidades-aprobables', UnidadAprobableViewSet, basename='unidad-aprobable')
router.register(r'requisitos-nodos', RequisitoNodoViewSet, basename='requisito-nodo')
router.register(r'requisitos-items', RequisitoItemViewSet, basename='requisito-item')

urlpatterns = [
    path("", include(router.urls)),
]
