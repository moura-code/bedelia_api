"""
Read-only viewsets for Materia-related models.
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters import FilterSet, BooleanFilter
from django.db.models import Q

from api.models import (
    Materia,
    PlanEstudio,
    PlanMateria,
    UnidadAprobable,
    PreviaNodo,
    PreviaItem,
    PosPreviaItem,
)
from api.serializers.materias import (
    MateriaSerializer,
    MateriaDetailSerializer,
    PlanEstudioSerializer,
    PlanMateriaSerializer,
    UnidadAprobableSerializer,
    PreviaNodoTreeSerializer,
    PreviaItemSerializer,
    PosPreviaSerializer,
)





@extend_schema_view(
    list=extend_schema(
        summary="Listar todas las materias",
        description="Obtener una lista paginada de todas las materias (cursos/asignaturas). Soporta filtrado por código y estado activo, y búsqueda por código o nombre.",
        tags=["materias"],
        parameters=[
            OpenApiParameter(
                name='codigo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por código de materia (coincidencia exacta)',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo (true/false)',
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Buscar en los campos código y nombre',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Obtener detalles de una materia",
        description="Obtener información detallada sobre una materia específica, incluyendo sus unidades aprobables y cantidad de planes.",
        tags=["materias"],
    ),
)
class MateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset de solo lectura para Materia (Cursos/Asignaturas).
    
    Proporciona acceso a todas las materias en el sistema con capacidades de filtrado y búsqueda.
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
        summary="Listar todos los planes de estudio",
        description="Obtener una lista paginada de todos los planes de estudio. Soporta filtrado por carrera, año y estado activo.",
        tags=["carreras"],
        parameters=[
            OpenApiParameter(
                name='nombre_carrera',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por nombre de carrera',
            ),
            OpenApiParameter(
                name='anio',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por año del plan',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Obtener detalles de un plan de estudio",
        description="Obtener información detallada sobre un plan de estudio específico, incluyendo el nombre de la carrera y la cantidad de materias.",
        tags=["carreras"],
    ),
)
class PlanEstudioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset de solo lectura para PlanEstudio (Planes de Estudio).
    
    Proporciona acceso a todos los planes de estudio con capacidades de filtrado.
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
        summary="Listar todas las relaciones plan-materia",
        description="Obtener una lista paginada de todas las relaciones plan-materia (materias dentro de planes de estudio). Soporta filtrado por plan, materia y estado activo.",
        tags=["planes-materias"],
        parameters=[
            OpenApiParameter(
                name='plan',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por ID de plan (UUID)',
            ),
            OpenApiParameter(
                name='materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por ID de materia (UUID)',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo del plan y la materia (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Obtener detalles de una relación plan-materia",
        description="Obtener información detallada sobre una relación plan-materia específica, incluyendo detalles del plan y la materia.",
        tags=["planes-materias"],
    ),
)
class PlanMateriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset de solo lectura para PlanMateria (Materias dentro de Planes de Estudio).
    
    Proporciona acceso a todas las relaciones plan-materia con capacidades de filtrado.
    """
    queryset = PlanMateria.objects.select_related('plan', 'materia').all().order_by('plan__nombre_carrera', 'plan__anio', 'materia__codigo')
    serializer_class = PlanMateriaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['plan', 'materia', 'activo']
    search_fields = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo', 'materia__nombre']
    ordering_fields = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo', 'fecha_creacion']
    ordering = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo']


@extend_schema_view(
    list=extend_schema(
        summary="Listar todas las unidades aprobables",
        description="Obtener una lista paginada de todas las unidades aprobables. Soporta filtrado por materia, tipo y estado activo.",
        tags=["unidades-aprobables"],
        parameters=[
            OpenApiParameter(
                name='materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por ID de materia (UUID)',
            ),
            OpenApiParameter(
                name='tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por tipo: MATERIA, CURSO, GRUPO, EXAMEN',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Obtener detalles de una unidad aprobable",
        description="Obtener información detallada sobre una unidad aprobable específica, incluyendo información de la materia.",
        tags=["unidades-aprobables"],
    ),
)
class UnidadAprobableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset de solo lectura para UnidadAprobable (Unidades Aprobables).
    
    Proporciona acceso a todas las unidades aprobables con capacidades de filtrado.
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
        summary="Listar todos los nodos de requisitos",
        description="Obtener una lista paginada de todos los nodos de requisitos (nodos del árbol de requisitos). Soporta filtrado por plan_materia, tipo, padre, opción root_only y estado activo.",
        tags=["requisitos"],
        parameters=[
            OpenApiParameter(
                name='plan_materia',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por ID de plan_materia (UUID)',
            ),
            OpenApiParameter(
                name='tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por tipo: ALL, ANY, NOT, LEAF',
            ),
            OpenApiParameter(
                name='padre',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por ID de nodo padre (UUID)',
            ),
            OpenApiParameter(
                name='root_only',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar para mostrar solo nodos raíz (true/false)',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo del plan y la materia de plan_materia (true/false)',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Obtener detalles de un nodo de requisito",
        description="Obtener información detallada sobre un nodo de requisito específico. La estructura del árbol se devuelve unificada con el campo 'children' que contiene sub-nodos o items según el tipo.",
        tags=["requisitos"],
    ),
)




@extend_schema_view(
    list=extend_schema(
        summary="Obtener previas (requisitos previos) para una PlanMateria",
        description="""
        Obtener todos los requisitos previos (previas) para una PlanMateria dada.
        
        Parámetros requeridos:
        O bien:
        - plan_id: UUID del plan de estudio
        O bien:
        - plan_year: Año del plan de estudio
        - plan_name: Nombre del plan de estudio/carrera
        
        Identificación de PlanMateria (al menos uno requerido):
        - plan_materia_id: UUID de la PlanMateria
        - plan_materia_code: Código de la materia en el plan
        - plan_materia_name: Nombre de la materia en el plan
        
        Filtros opcionales:
        - unidad_tipo: Filtrar por tipo de unidad aprobable (CURSO, EXAMEN, UCB, OTRO)
        - activo: Filtrar por estado activo (true/false)
        """,
        tags=["previas"],
        parameters=[
            OpenApiParameter(
                name='plan_materia_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='UUID de PlanMateria (proporciona información tanto del plan como de la materia)',
            ),
            OpenApiParameter(
                name='plan_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='UUID del plan de estudio (alternativa a plan_name/plan_year)',
            ),
            OpenApiParameter(
                name='plan_year',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Año del plan de estudio (requerido si no se proporciona plan_id)',
            ),
            OpenApiParameter(
                name='plan_name',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Nombre del plan de estudio/carrera (requerido si no se proporciona plan_id)',
            ),
            OpenApiParameter(
                name='materia_code',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Código de la materia (ej., "1944")',
                required=True,
            ),
            OpenApiParameter(
                name='unidad_tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Tipo de la UnidadAprobable: CURSO, EXAMEN, UCB, o OTRO',
                required=True,
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo (true/false)',
            ),
        ],
    ),
)
class PreviasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Obtener previas para una UnidadAprobable específica.
    
    Ejemplo: Para obtener previas de "EXAMEN de la materia 1944 en INGENIERÍA CIVIL 2021":
    /api/previas/?plan_year=2021&plan_name=INGENIERÍA CIVIL&materia_code=1944&unidad_tipo=EXAMEN
    """
    serializer_class = PreviaNodoTreeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['orden', 'fecha_creacion']
    ordering = ['orden']
    
    def get_queryset(self):
        """Build queryset based on query parameters."""
        # Get parameters
        plan_materia_id = self.request.query_params.get('plan_materia_id')
        plan_id = self.request.query_params.get('plan_id')
        plan_year = self.request.query_params.get('plan_year')
        plan_name = self.request.query_params.get('plan_name')
        materia_code = self.request.query_params.get('materia_code')
        unidad_tipo = self.request.query_params.get('unidad_tipo')
        activo = self.request.query_params.get('activo')
        
        # Validate required parameters
        if not unidad_tipo:
            raise ValidationError({
                'unidad_tipo': 'Este parámetro es requerido. Valores válidos: CURSO, EXAMEN, UCB, OTRO'
            })
        
        # Step 1: Find the PlanEstudio
        # Option A: Use plan_materia_id to get both plan and materia
        if plan_materia_id:
            plan_materia = PlanMateria.objects.filter(id=plan_materia_id).first()
            if not plan_materia:
                raise ValidationError({
                    'plan_materia_id': f'No se encontró PlanMateria con id={plan_materia_id}'
                })
            
            plans = PlanEstudio.objects.filter(id=plan_materia.plan.id)
            # Override materia_code if not provided or different
            if not materia_code:
                materia_code = plan_materia.materia.codigo
            elif materia_code != plan_materia.materia.codigo:
                # materia_code doesn't match plan_materia's materia
                raise ValidationError({
                    'materia_code': f'El código de materia {materia_code} no coincide con la materia de la PlanMateria (código {plan_materia.materia.codigo})'
                })
        # Option B: Use plan_id or plan_year+plan_name
        else:
            if not materia_code:
                raise ValidationError({
                    'materia_code': 'Este parámetro es requerido cuando no se proporciona plan_materia_id'
                })
            
            plan_filter = Q()
            if plan_id:
                plan_filter = Q(id=plan_id)
            elif plan_year and plan_name:
                plan_filter = Q(anio=plan_year, nombre_carrera__icontains=plan_name)
            else:
                raise ValidationError({
                    'plan_id': 'Debe proporcionar plan_id o ambos plan_year y plan_name'
                })
            
            plans = PlanEstudio.objects.filter(plan_filter)
        
        # Apply activo filter if not already filtered by plan_materia_id
        if activo is not None and not plan_materia_id:
            activo_bool = activo.lower() in ('true', '1', 'yes')
            plans = plans.filter(activo=activo_bool)
        
        if not plans.exists():
            if plan_id:
                raise ValidationError({
                    'plan_id': f'No se encontró PlanEstudio con id={plan_id}'
                })
            elif plan_year and plan_name:
                raise ValidationError({
                    'plan_year/plan_name': f'No se encontró PlanEstudio con año={plan_year} y nombre que contenga "{plan_name}"'
                })
            else:
                raise ValidationError({
                    'plan': 'No se encontró ningún plan de estudio con los parámetros especificados'
                })
        
        # Step 2: Find PlanMateria for this materia in these plans
        pm_filter = Q(
            plan__in=plans,
            materia__codigo=materia_code
        )
        
        if activo is not None:
            activo_bool = activo.lower() in ('true', '1', 'yes')
            pm_filter &= Q(materia__activo=activo_bool)
        
        plan_materias = PlanMateria.objects.filter(pm_filter)
        if not plan_materias.exists():
            plan_info = f"{plans.first().nombre_carrera} {plans.first().anio}" if plans.exists() else "desconocido"
            raise ValidationError({
                'materia_code': f'No se encontró la materia con código {materia_code} en el plan {plan_info}'
            })
        
        # Step 3: Verify that an UnidadAprobable exists with this tipo for this materia
        # This ensures the materia is actually offered as this tipo
        unidad_exists = UnidadAprobable.objects.filter(
            materia__codigo=materia_code,
            tipo=unidad_tipo
        ).exists()
        
        if not unidad_exists:
            raise ValidationError({
                'unidad_tipo': f'La materia {materia_code} no tiene una unidad aprobable de tipo {unidad_tipo}'
            })
        
        # Step 4: Get the RequisitoNodos for these PlanMaterias
        queryset = PreviaNodo.objects.select_related(
            'plan_materia__plan',
            'plan_materia__materia',
            'padre'
        ).prefetch_related(
            'hijos',
            'items__unidad_requerida__materia'
        ).filter(
            plan_materia__in=plan_materias,
            padre__isnull=True,  # Only root nodes
            unidad_tipo=unidad_tipo  # Filter by unidad tipo to separate CURSO/EXAMEN requirements
        )

        # Step 5: Validate that there's only one root node per plan_materia and unidad_tipo
        # Due to data loading issues, multiple root nodes may exist for the same plan_materia/unidad_tipo
        # If multiple exist, prioritize ALL type roots (most complete structure), then by creation date
        validated_roots = []
        for plan_materia in plan_materias:
            roots_for_pm = [node for node in queryset if node.plan_materia_id == plan_materia.id]

            if not roots_for_pm:
                continue

            if len(roots_for_pm) == 1:
                # Only one root, use it
                validated_roots.append(roots_for_pm[0])
            else:
                # Multiple roots, prioritize ALL type, then by creation date
                all_roots = [root for root in roots_for_pm if root.tipo == 'ALL']
                if all_roots:
                    # Use the oldest ALL root (most likely the correct one)
                    validated_roots.append(min(all_roots, key=lambda x: x.fecha_creacion))
                else:
                    # No ALL root, use the oldest root
                    validated_roots.append(min(roots_for_pm, key=lambda x: x.fecha_creacion))

        # Return validated roots as a queryset
        if validated_roots:
            root_ids = [root.id for root in validated_roots]
            queryset = PreviaNodo.objects.select_related(
                'plan_materia__plan',
                'plan_materia__materia',
                'padre'
            ).prefetch_related(
                'hijos',
                'items__unidad_requerida__materia'
            ).filter(id__in=root_ids)
        else:
            # No valid roots found
            queryset = PreviaNodo.objects.none()

        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="Obtener posprevias (cursos dependientes) para una materia",
        description="""
        Obtener todos los cursos que requieren la materia especificada como requisito previo,
        con información del plan de estudio al que pertenecen.

        Parámetros requeridos:
        - materia_code: Código de la materia (ej., "1944")

        Filtros opcionales:
        - unidad_tipo: Filtrar por tipo de unidad dependiente (CURSO, EXAMEN, UCB, OTRO)
        - activo: Filtrar por estado activo de los planes (true/false)

        La respuesta incluye información detallada de cada curso dependiente:
        - anio_plan, carrera: Información del plan
        - tipo: Tipo de unidad (CURSO, EXAMEN, etc.)
        - materia_codigo, materia_nombre: Información del curso dependiente
        """,
        tags=["posprevias"],
        parameters=[
            OpenApiParameter(
                name='materia_code',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Código de la materia (requerido)',
                required=True,
            ),
            OpenApiParameter(
                name='unidad_tipo',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filtrar por tipo de unidad dependiente (CURSO, EXAMEN, UCB, OTRO)',
            ),
            OpenApiParameter(
                name='activo',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo de los planes (true/false)',
            ),
        ],
    ),
)
class PosPreviasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Viewset para obtener posprevias (cursos dependientes) para una materia dada.

    Dada una materia (por materia_code), devuelve todos los cursos que requieren
    esa materia como requisito previo, con información del plan al que pertenecen.
    """
    serializer_class = PosPreviaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['fecha_creacion']
    ordering = ['plan_estudio__nombre_carrera', 'plan_estudio__anio']
    pagination_class = None  # Disable pagination for this endpoint

    def get_queryset(self):
        """Build queryset based on query parameters."""
        # Get parameters
        materia_code = self.request.query_params.get('materia_code')

        # Validate required parameters
        if not materia_code:
            return PosPreviaItem.objects.none()

        # Find the source materia
        try:
            materia = Materia.objects.get(codigo=materia_code)
        except Materia.DoesNotExist:
            return PosPreviaItem.objects.none()

        # Find all PosPreviaItem records for this materia
        queryset = PosPreviaItem.objects.filter(materia=materia).select_related('plan_estudio').prefetch_related('unidades_dependientes__materia')

        # Optional: Filter by unidad_tipo
        unidad_tipo = self.request.query_params.get('unidad_tipo')
        if unidad_tipo:
            queryset = queryset.filter(unidades_dependientes__tipo=unidad_tipo)

        # Optional: Filter by active status
        activo = self.request.query_params.get('activo')
        if activo is not None:
            activo_bool = activo.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(plan_estudio__activo=activo_bool)

        return queryset.order_by('plan_estudio__nombre_carrera', 'plan_estudio__anio')

    def list(self, request, *args, **kwargs):
        """Override list to flatten unidades_dependientes into separate entries."""
        queryset = self.get_queryset()

        # Flatten the data - each unidad_dependiente becomes a separate entry
        flattened_data = []
        for posprevia_item in queryset:
            for unidad in posprevia_item.unidades_dependientes.all():
                entry = {
                    'posprevia_item': posprevia_item,
                    'unidad_dependiente': unidad,
                    'plan_estudio': posprevia_item.plan_estudio,
                    'materia_dependiente': unidad.materia,
                }
                flattened_data.append(entry)

        # Serialize the flattened data
        serializer = self.get_serializer(flattened_data, many=True)
        return Response(serializer.data)

