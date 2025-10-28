"""
Views for the API.
"""
from .bedelia import (
    ProgramViewSet,
    SubjectViewSet,
    OfferingViewSet,
    RequirementGroupViewSet,
    RequirementGroupLinkViewSet,
    RequirementItemViewSet,
    SubjectEquivalenceViewSet,
    DependencyEdgeViewSet,
)

__all__ = [
    'ProgramViewSet',
    'SubjectViewSet',
    'OfferingViewSet',
    'RequirementGroupViewSet',
    'RequirementGroupLinkViewSet',
    'RequirementItemViewSet',
    'SubjectEquivalenceViewSet',
    'DependencyEdgeViewSet',
]

