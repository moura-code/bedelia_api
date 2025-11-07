"""
ViewSets for Bedelia models.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch, Count
from typing import Set, List, Dict

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from api.models import (
    Program, Subject, SubjectAlias, Offering, OfferingLink,
    RequirementGroup, RequirementGroupLink, RequirementItem,
    SubjectEquivalence, DependencyEdge, OfferingType, TargetType, GroupScope
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


@extend_schema(tags=['programs'])
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
    
    @extend_schema(
        tags=['programs'],
        summary="Get program statistics",
        description="Returns detailed statistics about a program including total subjects, credits, and offerings",
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a program."""
        program = self.get_object()
        
        # Get all subjects in this program
        subjects = Subject.objects.filter(programs=program)
        total_subjects = subjects.count()
        
        # Calculate total credits
        total_credits = sum(
            float(s.credits) for s in subjects if s.credits
        )
        
        # Get active offerings
        active_offerings = Offering.objects.filter(
            subject__programs=program,
            is_active=True
        ).distinct()
        
        # Count by type
        course_offerings = active_offerings.filter(type=OfferingType.COURSE).count()
        exam_offerings = active_offerings.filter(type=OfferingType.EXAM).count()
        
        # Count by semester
        semester_1 = active_offerings.filter(semester=1).count()
        semester_2 = active_offerings.filter(semester=2).count()
        
        # Get unique terms
        unique_terms = active_offerings.exclude(term__isnull=True).values_list('term', flat=True).distinct()
        
        return Response({
            'program': ProgramSerializer(program).data,
            'statistics': {
                'total_subjects': total_subjects,
                'total_credits': round(total_credits, 2),
                'active_offerings': {
                    'total': active_offerings.count(),
                    'courses': course_offerings,
                    'exams': exam_offerings,
                },
                'by_semester': {
                    'semester_1': semester_1,
                    'semester_2': semester_2,
                },
                'available_terms': sorted(unique_terms),
            }
        })
    
    @extend_schema(
        tags=['programs', 'smart'],
        summary="Compare two programs",
        description="Compare subjects between two programs",
        parameters=[
            OpenApiParameter(
                name='other_program_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='ID of the program to compare with',
                required=True
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """Compare this program with another program."""
        program = self.get_object()
        other_program_id = request.query_params.get('other_program_id')
        
        if not other_program_id:
            return Response(
                {'error': 'other_program_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_program = Program.objects.get(id=other_program_id)
        except Program.DoesNotExist:
            return Response(
                {'error': 'Other program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get subjects for both programs
        program_subjects = set(Subject.objects.filter(programs=program).values_list('code', flat=True))
        other_subjects = set(Subject.objects.filter(programs=other_program).values_list('code', flat=True))
        
        # Calculate differences
        only_in_program = program_subjects - other_subjects
        only_in_other = other_subjects - program_subjects
        in_both = program_subjects & other_subjects
        
        return Response({
            'program_1': ProgramSerializer(program).data,
            'program_2': ProgramSerializer(other_program).data,
            'comparison': {
                'only_in_program_1': list(only_in_program),
                'only_in_program_2': list(only_in_other),
                'in_both': list(in_both),
                'counts': {
                    'program_1_total': len(program_subjects),
                    'program_2_total': len(other_subjects),
                    'only_in_program_1': len(only_in_program),
                    'only_in_program_2': len(only_in_other),
                    'in_both': len(in_both),
                }
            }
        })


@extend_schema(tags=['subjects'])
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
    queryset = Subject.objects.prefetch_related(
        'programs', 'offerings', 'offerings__subject', 'aliases'
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'programs': ['exact'],
        'code': ['exact', 'icontains'],
        'credits': ['exact', 'gte', 'lte'],
    }
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name', 'credits', 'created_at']
    ordering = ['code']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        return SubjectSerializer
    
    @extend_schema(
        tags=['subjects', 'smart'],
        summary="Get available courses based on completed courses",
        description="Returns all courses that can be taken given a list of completed courses",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'completed_codes': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of completed subject codes',
                        'example': ['1020', '1061', '1411']
                    },
                    'program_id': {
                        'type': 'string',
                        'format': 'uuid',
                        'description': 'Optional: Filter by specific program',
                        'nullable': True
                    },
                    'only_active': {
                        'type': 'boolean',
                        'description': 'Only return active offerings',
                        'default': False
                    },
                    'offering_type': {
                        'type': 'string',
                        'enum': ['COURSE', 'EXAM'],
                        'default': 'COURSE'
                    }
                },
                'required': ['completed_codes']
            }
        },
        examples=[
            OpenApiExample(
                'Basic usage',
                value={
                    'completed_codes': ['1020', 'GAL1', '1411'],
                    'only_active': True
                }
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def available_courses(self, request):
        """Get all courses available to take based on completed courses."""
        completed_codes = request.data.get('completed_codes', [])
        program_id = request.data.get('program_id')
        only_active = request.data.get('only_active', False)
        offering_type = request.data.get('offering_type', 'COURSE')
        
        if not isinstance(completed_codes, list):
            return Response(
                {'error': 'completed_codes must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get completed subjects
        completed_subjects = set(Subject.objects.filter(code__in=completed_codes).values_list('id', flat=True))
        
        # Get all offerings (optionally filtered)
        offerings_query = Offering.objects.select_related('subject').prefetch_related(
            'requirement_groups__items__target_subject'
        )
        
        if program_id:
            offerings_query = offerings_query.filter(subject__programs__id=program_id)
        
        if only_active:
            offerings_query = offerings_query.filter(is_active=True)
        
        offerings_query = offerings_query.filter(type=offering_type)
        
        # Check which offerings have all requirements met
        available_offerings = []
        
        for offering in offerings_query:
            if self._check_requirements_met(offering, completed_subjects):
                available_offerings.append(offering)
        
        # Serialize the offerings
        serializer = OfferingSerializer(available_offerings, many=True)
        
        return Response({
            'available_offerings': serializer.data,
            'completed_count': len(completed_codes),
            'available_count': len(available_offerings),
        })
    
    @extend_schema(
        tags=['subjects', 'smart'],
        summary="Check what courses are unlocked by completing specific courses",
        description="Returns all courses that become available after completing the given courses (PosPrevias)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'course_codes': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Courses you want to check',
                        'example': ['CDIV', 'GAL1']
                    },
                    'program_id': {
                        'type': 'string',
                        'format': 'uuid',
                        'description': 'Optional: Filter by specific program',
                        'nullable': True
                    },
                    'only_active': {
                        'type': 'boolean',
                        'description': 'Only return active offerings',
                        'default': False
                    }
                },
                'required': ['course_codes']
            }
        },
        examples=[
            OpenApiExample(
                'Check CDIV unlocks',
                value={
                    'course_codes': ['CDIV'],
                    'only_active': True
                }
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def unlocked_by(self, request):
        """Get all courses that would be unlocked by completing given courses."""
        course_codes = request.data.get('course_codes', [])
        program_id = request.data.get('program_id')
        only_active = request.data.get('only_active', False)
        
        if not isinstance(course_codes, list):
            return Response(
                {'error': 'course_codes must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not course_codes:
            return Response({
                'input_courses': [],
                'unlocked_offerings': [],
                'unlocked_count': 0,
            })
        
        # Find subjects by codes
        subjects = Subject.objects.filter(code__in=course_codes)
        if program_id:
            subjects = subjects.filter(programs__id=program_id)
        
        subject_ids = set(subjects.values_list('id', flat=True))
        
        # Find requirement items that reference these subjects
        unlocking_items = RequirementItem.objects.filter(
            target_type=TargetType.SUBJECT,
            target_subject_id__in=subject_ids
        ).select_related('group__offering', 'group__offering__subject')
        
        unlocked_offerings_ids = set()
        for item in unlocking_items:
            unlocked_offerings_ids.add(item.group.offering.id)
        
        # Get the offerings
        unlocked_offerings = Offering.objects.filter(
            id__in=unlocked_offerings_ids
        ).select_related('subject')
        
        if only_active:
            unlocked_offerings = unlocked_offerings.filter(is_active=True)
        
        serializer = OfferingSerializer(unlocked_offerings, many=True)
        
        return Response({
            'input_courses': list(course_codes),
            'unlocked_offerings': serializer.data,
            'unlocked_count': len(unlocked_offerings),
        })
    
    @extend_schema(
        tags=['subjects'],
        summary="Get prerequisites chain for a subject",
        description="Returns all prerequisites recursively for a subject in a clear format",
        parameters=[
            OpenApiParameter(
                name='code',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Subject code',
                required=True
            ),
            OpenApiParameter(
                name='program_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Optional: Filter by program',
                required=False
            ),
            OpenApiParameter(
                name='offering_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['COURSE', 'EXAM'],
                description='Offering type to check',
                required=False
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def prerequisites(self, request):
        """Get all prerequisites for a subject."""
        code = request.query_params.get('code')
        program_id = request.query_params.get('program_id')
        offering_type = request.query_params.get('offering_type', 'COURSE')
        
        if not code:
            return Response(
                {'error': 'code query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find subject
        subjects = Subject.objects.filter(code__iexact=code)
        if program_id:
            subjects = subjects.filter(programs__id=program_id)
        
        subject = subjects.first()
        if not subject:
            return Response(
                {'error': f'Subject with code {code} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get offerings for this subject
        offerings = Offering.objects.filter(
            subject=subject,
            type=offering_type
        ).order_by('-term').first()
        
        if not offerings:
            return Response({
                'subject': SubjectSerializer(subject).data,
                'prerequisites': [],
                'message': f'No {offering_type} offerings found for this subject'
            })
        
        # Get all prerequisites recursively
        def get_prerequisites(offering, visited=None):
            if visited is None:
                visited = set()
            
            if offering.id in visited:
                return []
            
            visited.add(offering.id)
            prerequisites = []
            
            # Get requirement groups
            root_groups = offering.requirement_groups.filter(
                child_links__isnull=True
            ).prefetch_related(
                'items__target_subject',
                'items__target_offering__subject'
            )
            
            for group in root_groups:
                # Get direct subject requirements
                for item in group.items.filter(target_type=TargetType.SUBJECT):
                    if item.target_subject:
                        prereq_subject = item.target_subject
                        prerequisites.append({
                            'code': prereq_subject.code,
                            'name': prereq_subject.name,
                            'credits': float(prereq_subject.credits) if prereq_subject.credits else None,
                            'level': 1,
                        })
                        
                        # Get prerequisites of prerequisites
                        prereq_offerings = Offering.objects.filter(
                            subject=prereq_subject,
                            type=offering_type
                        ).order_by('-term').first()
                        
                        if prereq_offerings:
                            sub_prereqs = get_prerequisites(prereq_offerings, visited)
                            for sub_prereq in sub_prereqs:
                                sub_prereq['level'] = sub_prereq.get('level', 1) + 1
                                if sub_prereq not in prerequisites:
                                    prerequisites.append(sub_prereq)
            
            return prerequisites
        
        prereqs = get_prerequisites(offerings)
        
        # Deduplicate by code
        seen = set()
        unique_prereqs = []
        for prereq in prereqs:
            if prereq['code'] not in seen:
                seen.add(prereq['code'])
                unique_prereqs.append(prereq)
        
        return Response({
            'subject': SubjectSerializer(subject).data,
            'offering': OfferingSerializer(offerings).data,
            'prerequisites': unique_prereqs,
            'total_prerequisites': len(unique_prereqs),
        })
    
    @action(detail=False, methods=['post'])
    def unlocked_by(self, request):
        """Get all courses that would be unlocked by completing given courses."""
        course_codes = request.data.get('course_codes', [])
        program_id = request.data.get('program_id')
        only_active = request.data.get('only_active', False)
        
        if not isinstance(course_codes, list):
            return Response(
                {'error': 'course_codes must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get subjects for these codes
        subjects = Subject.objects.filter(code__in=course_codes)
        
        if program_id:
            subjects = subjects.filter(programs__id=program_id)
        
        # Find all requirement items that target these subjects
        requirement_items = RequirementItem.objects.filter(
            target_type=TargetType.SUBJECT,
            target_subject__in=subjects
        ).select_related('group', 'group__offering', 'group__offering__subject')
        
        # Get the offerings that have these requirements
        unlocked_offerings_ids = set()
        for item in requirement_items:
            unlocked_offerings_ids.add(item.group.offering.id)
        
        # Get the offerings
        unlocked_offerings = Offering.objects.filter(
            id__in=unlocked_offerings_ids
        ).select_related('subject')
        
        if only_active:
            unlocked_offerings = unlocked_offerings.filter(is_active=True)
        
        serializer = OfferingSerializer(unlocked_offerings, many=True)
        
        return Response({
            'input_courses': list(course_codes),
            'unlocked_offerings': serializer.data,
            'unlocked_count': len(unlocked_offerings),
        })
    
    def _check_requirements_met(self, offering: Offering, completed_subject_ids: Set) -> bool:
        """Check if all requirements for an offering are met."""
        # Get all root requirement groups (those not linked as children)
        root_groups = offering.requirement_groups.filter(
            child_links__isnull=True
        )
        
        if not root_groups.exists():
            # No requirements, always available
            return True
        
        # Check each root group
        for group in root_groups:
            if not self._check_group_satisfied(group, completed_subject_ids):
                return False
        
        return True
    
    def _check_group_satisfied(self, group: RequirementGroup, completed_subject_ids: Set) -> bool:
        """Recursively check if a requirement group is satisfied."""
        items = group.items.all()
        child_links = RequirementGroupLink.objects.filter(parent_group=group).select_related('child_group')
        
        satisfied_items = []
        
        # Check direct requirement items
        for item in items:
            if item.target_type == TargetType.SUBJECT and item.target_subject_id in completed_subject_ids:
                satisfied_items.append(item)
        
        # Check child groups
        satisfied_children = []
        for link in child_links:
            if self._check_group_satisfied(link.child_group, completed_subject_ids):
                satisfied_children.append(link.child_group)
        
        total_satisfied = len(satisfied_items) + len(satisfied_children)
        total_requirements = items.count() + child_links.count()
        
        # Apply group logic
        if group.scope == GroupScope.ALL:
            return total_satisfied == total_requirements
        elif group.scope == GroupScope.ANY:
            min_required = group.min_required or 1
            return total_satisfied >= min_required
        elif group.scope == GroupScope.NONE:
            return total_satisfied == 0
        
        return False


@extend_schema(tags=['offerings'])
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
    - by_term: Get active offerings by term
    - search_by_requirements: Search offerings by requirement patterns
    """
    queryset = Offering.objects.select_related('subject').prefetch_related(
        'subject__programs',
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
    
    @extend_schema(
        tags=['offerings'],
        summary="Get active offerings by term",
        description="Get all active offerings for a specific academic term",
        parameters=[
            OpenApiParameter(
                name='term',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Academic term (e.g., 2025S1, 2024S2)',
                required=True
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['COURSE', 'EXAM'],
                description='Offering type',
                required=False
            ),
            OpenApiParameter(
                name='program_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Optional: Filter by program',
                required=False
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def by_term(self, request):
        """Get all active offerings for a specific term."""
        term = request.query_params.get('term')
        offering_type = request.query_params.get('type')
        program_id = request.query_params.get('program_id')
        
        if not term:
            return Response(
                {'error': 'term query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            term=term,
            is_active=True
        )
        
        if offering_type:
            queryset = queryset.filter(type=offering_type)
        
        if program_id:
            queryset = queryset.filter(subject__programs__id=program_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'term': term,
            'total_offerings': queryset.count(),
            'offerings': serializer.data
        })
    
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
    - from_offering: Filter by source offering ID
    - to_offering: Filter by target offering ID
    - kind: Filter by dependency kind
    """
    queryset = DependencyEdge.objects.select_related(
        'from_offering', 'from_offering__subject',
        'to_offering', 'to_offering__subject',
        'from_subject', 'group'
    )
    serializer_class = DependencyEdgeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['from_offering', 'to_offering', 'kind', 'from_type', 'from_subject']
    ordering_fields = ['created_at']
    ordering = ['to_offering', 'kind']


# =============================================================================
# Custom Function-Based Views
# =============================================================================

@extend_schema(
    tags=['smart'],
    summary="Get intelligent course recommendations",
    description="""
    Get personalized course recommendations based on completed courses.
    
    Recommendations are prioritized based on:
    - **High**: Unlocks 5+ courses
    - **Medium**: Unlocks 2-4 courses  
    - **Low**: Unlocks 0-1 courses
    - **Future**: Missing only 1 requirement
    """,
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'completed_codes': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of completed subject codes',
                    'example': ['1020', 'GAL1', '1411', '1321']
                },
                'program_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'nullable': True
                },
                'max_results': {
                    'type': 'integer',
                    'default': 10,
                    'description': 'Maximum recommendations to return'
                },
                'only_active': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Only include active offerings'
                },
                'semester': {
                    'type': 'integer',
                    'enum': [1, 2],
                    'nullable': True,
                    'description': 'Filter by semester'
                }
            },
            'required': ['completed_codes']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'completed_count': {'type': 'integer'},
                'recommendations': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'offering': {'type': 'object'},
                            'priority': {'type': 'string', 'enum': ['high', 'medium', 'low', 'future']},
                            'missing_requirements': {'type': 'integer'},
                            'unlocks_count': {'type': 'integer'},
                            'reason': {'type': 'string'}
                        }
                    }
                },
                'total_available': {'type': 'integer'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'First semester recommendations',
            value={
                'completed_codes': ['1020', 'GAL1', '1411'],
                'only_active': True,
                'semester': 1,
                'max_results': 5
            }
        )
    ]
)
@api_view(['POST'])
def course_recommendations(request):
    """Get personalized course recommendations based on completed courses."""
    completed_codes = request.data.get('completed_codes', [])
    program_id = request.data.get('program_id')
    max_results = request.data.get('max_results', 10)
    only_active = request.data.get('only_active', True)
    semester = request.data.get('semester')
    
    if not isinstance(completed_codes, list):
        return Response(
            {'error': 'completed_codes must be a list'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get completed subject IDs
    completed_subjects = set(Subject.objects.filter(code__in=completed_codes).values_list('id', flat=True))
    
    # Get all course offerings
    offerings_query = Offering.objects.select_related('subject').prefetch_related(
        'requirement_groups__items__target_subject',
        'subject__programs'
    ).filter(type=OfferingType.COURSE)
    
    if program_id:
        offerings_query = offerings_query.filter(subject__programs__id=program_id)
    
    if only_active:
        offerings_query = offerings_query.filter(is_active=True)
    
    if semester:
        offerings_query = offerings_query.filter(semester=semester)
    
    # Score each offering
    recommendations = []
    
    for offering in offerings_query:
        # Skip if already completed
        if offering.subject_id in completed_subjects:
            continue
        
        # Check requirements
        missing_reqs = _count_missing_requirements(offering, completed_subjects)
        
        if missing_reqs == 0:
            # Can take now - calculate how many courses this unlocks
            unlocks_count = _count_unlocked_courses(offering.subject_id, offerings_query)
            
            # Determine priority
            if unlocks_count >= 5:
                priority = "high"
            elif unlocks_count >= 2:
                priority = "medium"
            else:
                priority = "low"
            
            recommendations.append({
                'offering': OfferingSerializer(offering).data,
                'priority': priority,
                'missing_requirements': 0,
                'unlocks_count': unlocks_count,
                'reason': f'Available now - unlocks {unlocks_count} other course(s)'
            })
        elif missing_reqs == 1:
            # Almost ready
            recommendations.append({
                'offering': OfferingSerializer(offering).data,
                'priority': 'future',
                'missing_requirements': missing_reqs,
                'unlocks_count': _count_unlocked_courses(offering.subject_id, offerings_query),
                'reason': 'Only 1 requirement missing'
            })
    
    # Sort by priority and unlocks count
    priority_order = {'high': 0, 'medium': 1, 'low': 2, 'future': 3}
    recommendations.sort(key=lambda x: (priority_order[x['priority']], -x['unlocks_count']))
    
    return Response({
        'completed_count': len(completed_codes),
        'recommendations': recommendations[:max_results],
        'total_available': len([r for r in recommendations if r['missing_requirements'] == 0]),
    })


@extend_schema(
    tags=['smart'],
    summary="Find pathway to reach a target course",
    description="Returns the list of courses you need to complete before you can take a target course",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'target_code': {
                    'type': 'string',
                    'description': 'Subject code of the course you want to take',
                    'example': '1911'
                },
                'completed_codes': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of completed subject codes',
                    'example': ['1020', 'GAL1', '1411']
                },
                'program_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'nullable': True,
                    'description': 'Optional: Filter by specific program'
                }
            },
            'required': ['target_code']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'target_course': {'type': 'object'},
                'completed_courses': {'type': 'array', 'items': {'type': 'string'}},
                'pathway': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'string'},
                            'name': {'type': 'string'},
                            'credits': {'type': 'number'}
                        }
                    }
                },
                'total_missing': {'type': 'integer'},
                'can_take_now': {'type': 'boolean'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'Path to Bases de Datos',
            value={
                'target_code': '1911',
                'completed_codes': ['1020', 'GAL1', '1411'],
            }
        )
    ]
)
@api_view(['POST'])
def course_pathway(request):
    """Suggest an optimal course pathway to reach a target course."""
    target_code = request.data.get('target_code')
    completed_codes = request.data.get('completed_codes', [])
    program_id = request.data.get('program_id')
    
    if not target_code:
        return Response(
            {'error': 'target_code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get target subject
    try:
        target_subject = Subject.objects.get(code=target_code)
    except Subject.DoesNotExist:
        return Response(
            {'error': f'Subject with code {target_code} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get target offering
    offering_query = Offering.objects.filter(
        subject=target_subject,
        type=OfferingType.COURSE
    )
    
    if program_id:
        offering_query = offering_query.filter(subject__programs__id=program_id)
    
    target_offering = offering_query.first()
    
    if not target_offering:
        return Response(
            {'error': f'No offering found for {target_code}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get completed subject IDs
    completed_subjects = set(Subject.objects.filter(code__in=completed_codes).values_list('id', flat=True))
    
    # Find missing requirements
    pathway = _build_course_pathway(target_offering, completed_subjects)
    
    return Response({
        'target_course': SubjectSerializer(target_subject).data,
        'completed_courses': list(completed_codes),
        'pathway': pathway,
        'total_missing': len(pathway),
        'can_take_now': len(pathway) == 0,
    })


def _count_missing_requirements(offering: Offering, completed_subject_ids: Set) -> int:
    """Count how many requirements are still missing for an offering."""
    root_groups = offering.requirement_groups.filter(child_links__isnull=True)
    
    if not root_groups.exists():
        return 0
    
    total_missing = 0
    
    for group in root_groups:
        total_missing += _count_group_missing(group, completed_subject_ids)
    
    return total_missing


def _count_group_missing(group: RequirementGroup, completed_subject_ids: Set) -> int:
    """Count missing requirements in a group."""
    items = group.items.all()
    child_links = RequirementGroupLink.objects.filter(parent_group=group)
    
    satisfied_count = 0
    total_count = items.count() + child_links.count()
    
    # Check items
    for item in items:
        if item.target_type == TargetType.SUBJECT and item.target_subject_id in completed_subject_ids:
            satisfied_count += 1
    
    # Check children
    for link in child_links:
        if _count_group_missing(link.child_group, completed_subject_ids) == 0:
            satisfied_count += 1
    
    # Calculate missing based on scope
    if group.scope == GroupScope.ALL:
        return total_count - satisfied_count
    elif group.scope == GroupScope.ANY:
        min_required = group.min_required or 1
        missing = max(0, min_required - satisfied_count)
        return missing
    elif group.scope == GroupScope.NONE:
        return satisfied_count  # Should be 0 for NONE
    
    return total_count - satisfied_count


def _count_unlocked_courses(subject_id, all_offerings_query) -> int:
    """Count how many courses would be unlocked by completing this subject."""
    # Find all requirement items that target this subject
    unlocking_items = RequirementItem.objects.filter(
        target_type=TargetType.SUBJECT,
        target_subject_id=subject_id
    ).select_related('group__offering')
    
    unlocked_offerings = set()
    for item in unlocking_items:
        unlocked_offerings.add(item.group.offering_id)
    
    return len(unlocked_offerings)


def _build_course_pathway(target_offering: Offering, completed_subject_ids: Set) -> List[Dict]:
    """Build a pathway of courses needed to reach the target."""
    pathway = []
    
    # Get all requirement items for this offering
    root_groups = target_offering.requirement_groups.all()
    
    for group in root_groups:
        missing = _extract_missing_from_group(group, completed_subject_ids)
        pathway.extend(missing)
    
    # Deduplicate
    seen_codes = set()
    unique_pathway = []
    for item in pathway:
        if item['code'] not in seen_codes:
            seen_codes.add(item['code'])
            unique_pathway.append(item)
    
    return unique_pathway


def _extract_missing_from_group(group: RequirementGroup, completed_subject_ids: Set) -> List[Dict]:
    """Extract missing subjects from a requirement group."""
    missing = []
    
    # Check items
    for item in group.items.all():
        if item.target_type == TargetType.SUBJECT:
            if item.target_subject_id not in completed_subject_ids:
                missing.append({
                    'code': item.target_subject.code,
                    'name': item.target_subject.name,
                    'credits': float(item.target_subject.credits) if item.target_subject.credits else 0,
                })
    
    # Check child groups
    child_links = RequirementGroupLink.objects.filter(parent_group=group).select_related('child_group')
    for link in child_links:
        missing.extend(_extract_missing_from_group(link.child_group, completed_subject_ids))
    
    return missing


@extend_schema(
    tags=['smart'],
    summary="Get semester planning suggestions",
    description="Get recommended courses for a specific semester based on completed courses and semester availability",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'completed_codes': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of completed subject codes',
                    'example': ['1020', 'GAL1', '1411']
                },
                'semester': {
                    'type': 'integer',
                    'enum': [1, 2],
                    'description': 'Semester to plan for (1 or 2)',
                    'required': True
                },
                'program_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'nullable': True,
                    'description': 'Optional: Filter by specific program'
                },
                'only_active': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Only include active offerings'
                },
                'max_results': {
                    'type': 'integer',
                    'default': 20,
                    'description': 'Maximum courses to return'
                }
            },
            'required': ['completed_codes', 'semester']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'semester': {'type': 'integer'},
                'completed_count': {'type': 'integer'},
                'available_courses': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'offering': {'type': 'object'},
                            'unlocks_count': {'type': 'integer'}
                        }
                    }
                },
                'total_available': {'type': 'integer'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'Plan first semester',
            value={
                'completed_codes': ['1020', 'GAL1'],
                'semester': 1,
                'only_active': True,
                'max_results': 10
            }
        )
    ]
)
@api_view(['POST'])
def semester_planning(request):
    """Get recommended courses for a specific semester."""
    completed_codes = request.data.get('completed_codes', [])
    semester = request.data.get('semester')
    program_id = request.data.get('program_id')
    only_active = request.data.get('only_active', True)
    max_results = request.data.get('max_results', 20)
    
    if semester not in [1, 2]:
        return Response(
            {'error': 'semester must be 1 or 2'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find completed subjects
    subjects = Subject.objects.filter(code__in=completed_codes)
    if program_id:
        subjects = subjects.filter(programs__id=program_id)
    completed_subjects = set(subjects.values_list('id', flat=True))
    
    # Get offerings for the specified semester
    offerings_query = Offering.objects.select_related('subject').prefetch_related(
        'requirement_groups__items__target_subject',
        'subject__programs'
    ).filter(
        type=OfferingType.COURSE,
        semester=semester
    )
    
    if program_id:
        offerings_query = offerings_query.filter(subject__programs__id=program_id)
    
    if only_active:
        offerings_query = offerings_query.filter(is_active=True)
    
    # Find available courses for this semester
    available_courses = []
    for offering in offerings_query:
        if offering.subject_id in completed_subjects:
            continue
        
        missing_reqs = _count_missing_requirements(offering, completed_subjects)
        if missing_reqs == 0:
            unlocks_count = _count_unlocked_courses(offering.subject_id, offerings_query)
            available_courses.append({
                'offering': OfferingSerializer(offering).data,
                'unlocks_count': unlocks_count,
            })
    
    # Sort by unlocks count
    available_courses.sort(key=lambda x: x['unlocks_count'], reverse=True)
    
    return Response({
        'semester': semester,
        'completed_count': len(completed_codes),
        'available_courses': available_courses[:max_results],
        'total_available': len(available_courses),
    })


@extend_schema(
    tags=['smart'],
    summary="Track progress through a program",
    description="Calculate progress metrics for a program based on completed courses",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'completed_codes': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of completed subject codes',
                    'example': ['1020', 'GAL1', '1411', '1321']
                },
                'program_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Program ID to track progress for',
                    'required': True
                }
            },
            'required': ['completed_codes', 'program_id']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'program': {'type': 'object'},
                'progress': {
                    'type': 'object',
                    'properties': {
                        'subjects': {
                            'type': 'object',
                            'properties': {
                                'completed': {'type': 'integer'},
                                'total': {'type': 'integer'},
                                'remaining': {'type': 'integer'},
                                'percentage': {'type': 'number'}
                            }
                        },
                        'credits': {
                            'type': 'object',
                            'properties': {
                                'completed': {'type': 'number'},
                                'total': {'type': 'number'},
                                'remaining': {'type': 'number'},
                                'percentage': {'type': 'number'}
                            }
                        },
                        'available_courses': {'type': 'integer'}
                    }
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            'Track progress',
            value={
                'completed_codes': ['1020', 'GAL1', '1411', '1321', '1911'],
                'program_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
def program_progress(request):
    """Track progress through a program."""
    completed_codes = request.data.get('completed_codes', [])
    program_id = request.data.get('program_id')
    
    if not program_id:
        return Response(
            {'error': 'program_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        program = Program.objects.get(id=program_id)
    except Program.DoesNotExist:
        return Response(
            {'error': 'Program not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all subjects in the program
    program_subjects = Subject.objects.filter(programs=program)
    total_subjects = program_subjects.count()
    
    # Calculate total credits in program
    total_credits = sum(
        float(s.credits) for s in program_subjects if s.credits
    )
    
    # Find completed subjects in this program
    completed_subjects = Subject.objects.filter(
        code__in=completed_codes,
        programs=program
    )
    completed_count = completed_subjects.count()
    
    # Calculate completed credits
    completed_credits = sum(
        float(s.credits) for s in completed_subjects if s.credits
    )
    
    # Calculate percentages
    subject_percentage = (completed_count / total_subjects * 100) if total_subjects > 0 else 0
    credit_percentage = (completed_credits / total_credits * 100) if total_credits > 0 else 0
    
    # Get available courses
    completed_subject_ids = set(completed_subjects.values_list('id', flat=True))
    available_offerings = Offering.objects.filter(
        subject__programs=program,
        type=OfferingType.COURSE,
        is_active=True
    ).exclude(subject_id__in=completed_subject_ids)
    
    available_count = 0
    for offering in available_offerings:
        if _count_missing_requirements(offering, completed_subject_ids) == 0:
            available_count += 1
    
    return Response({
        'program': ProgramSerializer(program).data,
        'progress': {
            'subjects': {
                'completed': completed_count,
                'total': total_subjects,
                'remaining': total_subjects - completed_count,
                'percentage': round(subject_percentage, 2),
            },
            'credits': {
                'completed': round(completed_credits, 2),
                'total': round(total_credits, 2),
                'remaining': round(total_credits - completed_credits, 2),
                'percentage': round(credit_percentage, 2),
            },
            'available_courses': available_count,
        }
    })

