"""
Read-only viewsets for Materia-related models.
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from api.models import (
    Materia,
    PlanEstudio,
    PlanMateria,
    UnidadAprobable,
    RequisitoNodo,
    RequisitoItem,
)
from api.serializers.materias import (
    MateriaSerializer,
    MateriaDetailSerializer,
    PlanEstudioSerializer,
    PlanMateriaSerializer,
    UnidadAprobableSerializer,
    RequisitoNodoSerializer,
    RequisitoNodoTreeSerializer,
    RequisitoItemSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List all materias",
        description="Retrieve a paginated list of all materias (courses/subjects). Supports filtering by code and active status, and searching by code or name.",
        tags=["materias"],
        parameters=[
            OpenApiParameter(
                name='codigo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by materia code (exact match)',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter by active status (true/false)',
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search in codigo and nombre fields',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get materia details",
        description="Retrieve detailed information about a specific materia, including its unidades aprobables and plan count.",
        tags=["materias"],
    ),
)
class MateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Materia (Courses/Subjects).
    
    Provides access to all materias in the system with filtering and search capabilities.
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


@extend_schema_view(
    list=extend_schema(
        summary="List all study plans",
        description="Retrieve a paginated list of all study plans (planes de estudio). Supports filtering by carrera, year, and active status.",
        tags=["planes-estudio"],
        parameters=[
            OpenApiParameter(
                name='nombre_carrera',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by carrera name',
            ),
            OpenApiParameter(
                name='anio',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by plan year',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter by active status (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get study plan details",
        description="Retrieve detailed information about a specific study plan, including carrera name and materia count.",
        tags=["planes-estudio"],
    ),
)
class PlanEstudioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for PlanEstudio (Study Plans).
    
    Provides access to all study plans with filtering capabilities.
    """
    queryset = PlanEstudio.objects.all().order_by('nombre_carrera', 'anio')
    serializer_class = PlanEstudioSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nombre_carrera', 'anio', 'activo']
    search_fields = ['nombre_carrera', 'anio', 'descripcion']
    ordering_fields = ['nombre_carrera', 'anio', 'fecha_creacion']
    ordering = ['nombre_carrera', 'anio']


@extend_schema_view(
    list=extend_schema(
        summary="List all plan-materia relationships",
        description="Retrieve a paginated list of all plan-materia relationships (materias within study plans). Supports filtering by plan, materia, and obligatorio status.",
        tags=["planes-materias"],
        parameters=[
            OpenApiParameter(
                name='plan',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by plan ID (UUID)',
            ),
            OpenApiParameter(
                name='materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by materia ID (UUID)',
            ),
            OpenApiParameter(
                name='obligatorio',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter by obligatorio status (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get plan-materia relationship details",
        description="Retrieve detailed information about a specific plan-materia relationship, including plan and materia details.",
        tags=["planes-materias"],
    ),
)
class PlanMateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for PlanMateria (Materias within Study Plans).
    
    Provides access to all plan-materia relationships with filtering capabilities.
    """
    queryset = PlanMateria.objects.select_related('plan', 'materia').all().order_by('plan__nombre_carrera', 'plan__anio', 'materia__codigo')
    serializer_class = PlanMateriaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['plan', 'materia', 'obligatorio']
    search_fields = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo', 'materia__nombre']
    ordering_fields = ['semestre_sugerido', 'fecha_creacion']
    ordering = ['plan__nombre_carrera', 'plan__anio', 'semestre_sugerido']


@extend_schema_view(
    list=extend_schema(
        summary="List all unidades aprobables",
        description="Retrieve a paginated list of all unidades aprobables (approvable units). Supports filtering by materia, tipo, and active status.",
        tags=["unidades-aprobables"],
        parameters=[
            OpenApiParameter(
                name='materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by materia ID (UUID)',
            ),
            OpenApiParameter(
                name='tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by tipo: MATERIA, CURSO, GRUPO, EXAMEN',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter by active status (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get unidad aprobable details",
        description="Retrieve detailed information about a specific unidad aprobable, including materia information.",
        tags=["unidades-aprobables"],
    ),
)
class UnidadAprobableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for UnidadAprobable (Approvable Units).
    
    Provides access to all unidades aprobables with filtering capabilities.
    """
    queryset = UnidadAprobable.objects.select_related('materia').all().order_by('materia__codigo', 'tipo')
    serializer_class = UnidadAprobableSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['materia', 'tipo', 'activo']
    search_fields = ['materia__codigo', 'materia__nombre', 'codigo_bedelias', 'nombre']
    ordering_fields = ['materia__codigo', 'tipo', 'fecha_creacion']
    ordering = ['materia__codigo', 'tipo']


@extend_schema_view(
    list=extend_schema(
        summary="List all requisito nodos",
        description="Retrieve a paginated list of all requisito nodos (requirement tree nodes). Supports filtering by plan_materia, tipo, padre, and root_only option.",
        tags=["requisitos"],
        parameters=[
            OpenApiParameter(
                name='plan_materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by plan_materia ID (UUID)',
            ),
            OpenApiParameter(
                name='tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by tipo: ROOT, AND, OR, LEAF',
            ),
            OpenApiParameter(
                name='padre',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by parent node ID (UUID)',
            ),
            OpenApiParameter(
                name='root_only',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter to show only root nodes (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get requisito nodo details",
        description="Retrieve detailed information about a specific requisito nodo. Use tree=true query parameter to get the full tree structure with nested hijos and items.",
        tags=["requisitos"],
        parameters=[
            OpenApiParameter(
                name='tree',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Return full tree structure with nested hijos and items (true/false)',
            ),
        ],
    ),
)
class RequisitoNodoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for RequisitoNodo (Requirement Tree Nodes).
    
    Provides access to all requisito nodos with filtering capabilities.
    Supports tree view for retrieving full requirement tree structures.
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


@extend_schema_view(
    list=extend_schema(
        summary="List all requisito items",
        description="Retrieve a paginated list of all requisito items (requirement items within leaf nodes). Supports filtering by nodo and tipo.",
        tags=["requisitos"],
        parameters=[
            OpenApiParameter(
                name='nodo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by requisito nodo ID (UUID)',
            ),
            OpenApiParameter(
                name='tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by tipo: UNIDAD, TEXTO',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get requisito item details",
        description="Retrieve detailed information about a specific requisito item, including nodo and unidad_requerida information.",
        tags=["requisitos"],
    ),
)
class RequisitoItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for RequisitoItem (Requirement Items).
    
    Provides access to all requisito items with filtering capabilities.
    Items are associated with LEAF type requisito nodos.
    """
    queryset = RequisitoItem.objects.select_related('nodo', 'unidad_requerida').all().order_by('nodo', 'orden')
    serializer_class = RequisitoItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nodo', 'tipo']
    search_fields = ['texto']
    ordering_fields = ['orden', 'fecha_creacion']
    ordering = ['nodo', 'orden']

