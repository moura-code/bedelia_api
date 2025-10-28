"""
ViewSets for Bedelia models.
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch

from api.models import (
    Program, Subject, SubjectAlias, Offering, OfferingLink,
    RequirementGroup, RequirementGroupLink, RequirementItem,
    SubjectEquivalence, DependencyEdge
)
from api.serializers.bedelia import (
    ProgramSerializer,
    SubjectSerializer, SubjectDetailSerializer,
    OfferingSerializer, OfferingDetailSerializer,
    RequirementGroupSerializer, RequirementGroupTreeSerializer,
    RequirementGroupLinkSerializer,
    RequirementItemSerializer,
    SubjectEquivalenceSerializer,
    DependencyEdgeSerializer,
)


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Program model.
    
    list: Get all programs
    retrieve: Get a specific program by ID
    
    Filtering:
    - plan_year: Filter by plan year
    - name: Filter by name (case-insensitive contains)
    """
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['plan_year']
    search_fields = ['name']
    ordering_fields = ['plan_year', 'name', 'created_at']
    ordering = ['plan_year', 'name']


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Subject model.
    
    list: Get all subjects
    retrieve: Get a specific subject with full details (offerings, aliases)
    
    Filtering:
    - program: Filter by program ID
    - code: Filter by subject code (case-insensitive contains)
    - credits: Filter by credits (exact match)
    - credits__gte: Filter by minimum credits
    - credits__lte: Filter by maximum credits
    
    Search:
    - Search in code and name fields
    
    Ordering:
    - code, name, credits, created_at
    """
    queryset = Subject.objects.select_related('program').prefetch_related(
        'offerings', 'offerings__subject', 'aliases'
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'program': ['exact'],
        'code': ['exact', 'icontains'],
        'credits': ['exact', 'gte', 'lte'],
        'semester': ['exact'],
    }
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'credits', 'created_at']
    ordering = ['code']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        return SubjectSerializer


class OfferingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Offering model.
    
    list: Get all offerings
    retrieve: Get a specific offering with full requirement groups
    
    Filtering:
    - subject: Filter by subject ID
    - type: Filter by offering type (COURSE or EXAM)
    - term: Filter by term (exact match)
    - is_active: Filter by active status
    - credits__gte: Filter by minimum credits
    - credits__lte: Filter by maximum credits
    
    Search:
    - Search in subject code and name
    
    Custom actions:
    - requirement_tree: Get the full recursive requirement tree for an offering
    """
    queryset = Offering.objects.select_related('subject', 'subject__program').prefetch_related(
        'requirement_groups',
        'requirement_groups__items',
        'requirement_groups__items__target_subject',
        'requirement_groups__items__target_offering',
        'links'
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'subject': ['exact'],
        'type': ['exact'],
        'term': ['exact', 'icontains'],
        'section': ['exact'],
        'semester': ['exact'],
        'is_active': ['exact'],
        'credits': ['exact', 'gte', 'lte'],
    }
    search_fields = ['subject__code', 'subject__name', 'term']
    ordering_fields = ['term', 'created_at', 'credits']
    ordering = ['-term', 'subject__code']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return OfferingDetailSerializer
        return OfferingSerializer
    
    @action(detail=True, methods=['get'])
    def requirement_tree(self, request, pk=None):
        """
        Get the full recursive requirement tree for this offering.
        
        Returns all requirement groups in a nested tree structure.
        """
        offering = self.get_object()
        
        # Get root requirement groups (those that are not children of any other group)
        root_groups = RequirementGroup.objects.filter(
            offering=offering
        ).exclude(
            id__in=RequirementGroupLink.objects.values_list('child_group_id', flat=True)
        ).prefetch_related(
            'items',
            'items__target_subject',
            'items__target_offering',
            'items__target_offering__subject',
            'child_links',
            'child_links__child_group'
        ).order_by('order_index')
        
        serializer = RequirementGroupTreeSerializer(root_groups, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_by_requirements(self, request):
        """
        Search offerings by requirement patterns.
        
        Query params:
        - requires_subject: Subject code that must be in requirements
        - min_credits: Minimum total credits required
        - scope: Filter by requirement group scope (ALL/ANY/NONE)
        """
        queryset = self.get_queryset()
        
        requires_subject = request.query_params.get('requires_subject')
        if requires_subject:
            queryset = queryset.filter(
                requirement_groups__items__target_subject__code__icontains=requires_subject
            ).distinct()
        
        min_credits = request.query_params.get('min_credits')
        if min_credits:
            try:
                min_credits = float(min_credits)
                queryset = queryset.filter(credits__gte=min_credits)
            except (ValueError, TypeError):
                pass
        
        scope = request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(requirement_groups__scope=scope).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RequirementGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for RequirementGroup model.
    
    list: Get all requirement groups
    retrieve: Get a specific requirement group with items and child links
    
    Filtering:
    - offering: Filter by offering ID
    - scope: Filter by scope (ALL/ANY/NONE)
    - flavor: Filter by flavor
    - min_required: Filter by min_required value
    """
    queryset = RequirementGroup.objects.select_related('offering', 'offering__subject').prefetch_related(
        'items',
        'items__target_subject',
        'items__target_offering',
        'child_links',
        'child_links__child_group'
    )
    serializer_class = RequirementGroupSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'offering': ['exact'],
        'scope': ['exact'],
        'flavor': ['exact'],
        'min_required': ['exact', 'gte', 'lte'],
    }
    ordering_fields = ['order_index', 'created_at']
    ordering = ['offering', 'order_index']


class RequirementGroupLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for RequirementGroupLink model.
    
    list: Get all requirement group links
    retrieve: Get a specific link
    
    Filtering:
    - parent_group: Filter by parent group ID
    - child_group: Filter by child group ID
    """
    queryset = RequirementGroupLink.objects.select_related(
        'parent_group', 'child_group',
        'parent_group__offering', 'child_group__offering'
    )
    serializer_class = RequirementGroupLinkSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['parent_group', 'child_group']
    ordering_fields = ['order_index', 'created_at']
    ordering = ['parent_group', 'order_index']


class RequirementItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for RequirementItem model.
    
    list: Get all requirement items
    retrieve: Get a specific requirement item
    
    Filtering:
    - group: Filter by requirement group ID
    - target_type: Filter by target type (SUBJECT/OFFERING)
    - target_subject: Filter by target subject ID
    - target_offering: Filter by target offering ID
    - condition: Filter by condition (APPROVED/ENROLLED/CREDITED)
    """
    queryset = RequirementItem.objects.select_related(
        'group', 'group__offering',
        'target_subject', 'target_subject__program',
        'target_offering', 'target_offering__subject'
    )
    serializer_class = RequirementItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'group': ['exact'],
        'target_type': ['exact'],
        'target_subject': ['exact'],
        'target_offering': ['exact'],
        'condition': ['exact'],
    }
    search_fields = ['alt_code', 'alt_label']
    ordering_fields = ['order_index', 'created_at']
    ordering = ['group', 'order_index']


class SubjectEquivalenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SubjectEquivalence model.
    
    list: Get all subject equivalences
    retrieve: Get a specific equivalence
    
    Filtering:
    - subject_a: Filter by subject A ID
    - subject_b: Filter by subject B ID
    - kind: Filter by equivalence kind (FULL/PARTIAL)
    """
    queryset = SubjectEquivalence.objects.select_related(
        'subject_a', 'subject_a__program',
        'subject_b', 'subject_b__program'
    )
    serializer_class = SubjectEquivalenceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['subject_a', 'subject_b', 'kind']
    ordering_fields = ['created_at']
    ordering = ['subject_a__code', 'subject_b__code']


class DependencyEdgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for DependencyEdge model.
    
    list: Get all dependency edges
    retrieve: Get a specific dependency edge
    
    Filtering:
    - source_offering: Filter by source offering ID
    - target_offering: Filter by target offering ID
    - dep_kind: Filter by dependency kind
    """
    queryset = DependencyEdge.objects.select_related(
        'source_offering', 'source_offering__subject',
        'target_offering', 'target_offering__subject'
    )
    serializer_class = DependencyEdgeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source_offering', 'target_offering', 'dep_kind']
    ordering_fields = ['created_at']
    ordering = ['source_offering', 'target_offering']

