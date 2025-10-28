from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    ProgramViewSet,
    SubjectViewSet,
    OfferingViewSet,
    RequirementGroupViewSet,
    RequirementGroupLinkViewSet,
    RequirementItemViewSet,
    SubjectEquivalenceViewSet,
    DependencyEdgeViewSet,
)


router = DefaultRouter()

# Register all viewsets
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'offerings', OfferingViewSet, basename='offering')
router.register(r'requirement-groups', RequirementGroupViewSet, basename='requirementgroup')
router.register(r'requirement-group-links', RequirementGroupLinkViewSet, basename='requirementgrouplink')
router.register(r'requirement-items', RequirementItemViewSet, basename='requirementitem')
router.register(r'subject-equivalences', SubjectEquivalenceViewSet, basename='subjectequivalence')
router.register(r'dependency-edges', DependencyEdgeViewSet, basename='dependencyedge')


urlpatterns = [
    path("", include(router.urls)),
]
