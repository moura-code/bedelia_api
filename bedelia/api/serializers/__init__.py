"""
Serializers for the API.
"""
from .bedelia import (
    ProgramSerializer,
    ProgramBasicSerializer,
    SubjectSerializer,
    SubjectDetailSerializer,
    SubjectBasicSerializer,
    SubjectAliasSerializer,
    OfferingSerializer,
    OfferingDetailSerializer,
    OfferingBasicSerializer,
    OfferingLinkSerializer,
    RequirementGroupSerializer,
    RequirementGroupTreeSerializer,
    RequirementGroupLinkSerializer,
    RequirementItemSerializer,
    SubjectEquivalenceSerializer,
    DependencyEdgeSerializer,
)

__all__ = [
    'ProgramSerializer',
    'ProgramBasicSerializer',
    'SubjectSerializer',
    'SubjectDetailSerializer',
    'SubjectBasicSerializer',
    'SubjectAliasSerializer',
    'OfferingSerializer',
    'OfferingDetailSerializer',
    'OfferingBasicSerializer',
    'OfferingLinkSerializer',
    'RequirementGroupSerializer',
    'RequirementGroupTreeSerializer',
    'RequirementGroupLinkSerializer',
    'RequirementItemSerializer',
    'SubjectEquivalenceSerializer',
    'DependencyEdgeSerializer',
]

