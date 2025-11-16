"""
Read-only viewsets for Materia-related models.
"""
from rest_framework import viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from api.models import (
    Carrera,
    Materia,
    PlanEstudio,
    PlanMateria,
    UnidadAprobable,
    RequisitoNodo,
    RequisitoItem,
)
from api.serializers.materias import (
    CarreraSerializer,
    MateriaSerializer,
    MateriaDetailSerializer,
    PlanEstudioSerializer,
    PlanMateriaSerializer,
    UnidadAprobableSerializer,
    RequisitoNodoSerializer,
    RequisitoNodoTreeSerializer,
    RequisitoItemSerializer,
)


class CarreraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Carrera.
    
    list: List all carreras
    retrieve: Get a specific carrera
    """
    queryset = Carrera.objects.all().order_by('nombre')
    serializer_class = CarreraSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'fecha_creacion']
    ordering = ['nombre']


class MateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Materia.
    
    list: List all materias with filtering and search
    retrieve: Get a specific materia with detailed information
    """
    queryset = Materia.objects.all().order_by('codigo')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['codigo', 'activo']
    search_fields = ['codigo', 'nombre']
    ordering_fields = ['codigo', 'nombre', 'creditos', 'fecha_creacion']
    ordering = ['codigo']
    
    def get_serializer_class(self):
        """Use detail serializer for retrieve, basic for list."""
        if self.action == 'retrieve':
            return MateriaDetailSerializer
        return MateriaSerializer


class PlanEstudioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for PlanEstudio.
    
    list: List all study plans with filtering
    retrieve: Get a specific study plan
    """
    queryset = PlanEstudio.objects.select_related('carrera').all().order_by('carrera__nombre', 'anio')
    serializer_class = PlanEstudioSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['carrera', 'anio', 'activo']
    search_fields = ['carrera__nombre', 'anio', 'descripcion']
    ordering_fields = ['anio', 'fecha_creacion']
    ordering = ['carrera__nombre', 'anio']


class PlanMateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for PlanMateria.
    
    list: List all plan-materia relationships with filtering
    retrieve: Get a specific plan-materia relationship
    """
    queryset = PlanMateria.objects.select_related('plan', 'materia').all().order_by('plan__carrera__nombre', 'plan__anio', 'materia__codigo')
    serializer_class = PlanMateriaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['plan', 'materia', 'obligatorio']
    search_fields = ['plan__carrera__nombre', 'plan__anio', 'materia__codigo', 'materia__nombre']
    ordering_fields = ['semestre_sugerido', 'fecha_creacion']
    ordering = ['plan__carrera__nombre', 'plan__anio', 'semestre_sugerido']


class UnidadAprobableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for UnidadAprobable.
    
    list: List all unidades aprobables with filtering
    retrieve: Get a specific unidad aprobable
    """
    queryset = UnidadAprobable.objects.select_related('materia').all().order_by('materia__codigo', 'tipo')
    serializer_class = UnidadAprobableSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['materia', 'tipo', 'activo']
    search_fields = ['materia__codigo', 'materia__nombre', 'codigo_bedelias', 'nombre']
    ordering_fields = ['materia__codigo', 'tipo', 'fecha_creacion']
    ordering = ['materia__codigo', 'tipo']


class RequisitoNodoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for RequisitoNodo.
    
    list: List all requisito nodos with filtering
    retrieve: Get a specific requisito nodo (can use tree serializer via query param)
    """
    queryset = RequisitoNodo.objects.select_related('plan_materia', 'padre').prefetch_related('hijos', 'items').all().order_by('orden')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['plan_materia', 'tipo', 'padre']
    search_fields = ['descripcion']
    ordering_fields = ['orden', 'fecha_creacion']
    ordering = ['orden']
    
    def get_serializer_class(self):
        """Use tree serializer if tree=true query param, otherwise basic serializer."""
        if self.action == 'retrieve':
            tree = self.request.query_params.get('tree', '').lower() == 'true'
            if tree:
                return RequisitoNodoTreeSerializer
        return RequisitoNodoSerializer
    
    def list(self, request, *args, **kwargs):
        """List all nodos, optionally filtered to root nodes only."""
        root_only = request.query_params.get('root_only', '').lower() == 'true'
        queryset = self.filter_queryset(self.get_queryset())
        
        if root_only:
            queryset = queryset.filter(padre__isnull=True)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RequisitoItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for RequisitoItem.
    
    list: List all requisito items with filtering
    retrieve: Get a specific requisito item
    """
    queryset = RequisitoItem.objects.select_related('nodo', 'unidad_requerida').all().order_by('nodo', 'orden')
    serializer_class = RequisitoItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nodo', 'tipo']
    search_fields = ['texto']
    ordering_fields = ['orden', 'fecha_creacion']
    ordering = ['nodo', 'orden']

