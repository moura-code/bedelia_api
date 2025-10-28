"""
Serializers for Bedelia models.
"""
from rest_framework import serializers
from api.models import (
    Program, Subject, SubjectAlias, Offering, OfferingLink,
    RequirementGroup, RequirementGroupLink, RequirementItem,
    SubjectEquivalence, DependencyEdge
)


# ============================================================================
# Basic Serializers (for nested references)
# ============================================================================

class ProgramBasicSerializer(serializers.ModelSerializer):
    """Basic program info for nested references."""
    
    class Meta:
        model = Program
        fields = ['id', 'name', 'plan_year']


class SubjectBasicSerializer(serializers.ModelSerializer):
    """Basic subject info for nested references."""
    
    class Meta:
        model = Subject
        fields = ['id', 'code', 'name', 'credits']


class OfferingBasicSerializer(serializers.ModelSerializer):
    """Basic offering info for nested references."""
    subject = SubjectBasicSerializer(read_only=True)
    
    class Meta:
        model = Offering
        fields = ['id', 'subject', 'type', 'term', 'section', 'credits', 'is_active']


# ============================================================================
# Full Serializers
# ============================================================================

class ProgramSerializer(serializers.ModelSerializer):
    """Full program serializer."""
    
    class Meta:
        model = Program
        fields = ['id', 'name', 'plan_year', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubjectAliasSerializer(serializers.ModelSerializer):
    """Subject alias serializer."""
    
    class Meta:
        model = SubjectAlias
        fields = ['id', 'alias_code', 'alias_name']


class SubjectSerializer(serializers.ModelSerializer):
    """Subject serializer with basic info."""
    program = ProgramBasicSerializer(read_only=True)
    
    class Meta:
        model = Subject
        fields = [
            'id', 'program', 'code', 'name', 'credits', 'dept', 
            'description', 'semester', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubjectDetailSerializer(SubjectSerializer):
    """Subject serializer with nested offerings and aliases."""
    offerings = OfferingBasicSerializer(many=True, read_only=True)
    aliases = SubjectAliasSerializer(many=True, read_only=True)
    
    class Meta(SubjectSerializer.Meta):
        fields = SubjectSerializer.Meta.fields + ['offerings', 'aliases']


class OfferingLinkSerializer(serializers.ModelSerializer):
    """Offering link serializer."""
    
    class Meta:
        model = OfferingLink
        fields = ['id', 'kind', 'url', 'title']


class RequirementItemSerializer(serializers.ModelSerializer):
    """Requirement item serializer with target details."""
    target_subject = SubjectBasicSerializer(read_only=True)
    target_offering = OfferingBasicSerializer(read_only=True)
    
    class Meta:
        model = RequirementItem
        fields = [
            'id', 'target_type', 'target_subject', 'target_offering',
            'condition', 'alt_code', 'alt_label', 'order_index'
        ]
        read_only_fields = ['id']


class RequirementGroupLinkSerializer(serializers.ModelSerializer):
    """Requirement group link serializer (references only)."""
    
    class Meta:
        model = RequirementGroupLink
        fields = ['id', 'parent_group', 'child_group', 'order_index']
        read_only_fields = ['id']


class RequirementGroupSerializer(serializers.ModelSerializer):
    """Requirement group serializer with items and child links."""
    items = RequirementItemSerializer(many=True, read_only=True)
    child_links = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementGroup
        fields = [
            'id', 'scope', 'flavor', 'min_required', 'note', 'order_index',
            'items', 'child_links'
        ]
        read_only_fields = ['id']
    
    def get_child_links(self, obj):
        """Get child groups with their IDs."""
        links = obj.child_links.select_related('child_group').order_by('order_index')
        return [{'child_group_id': link.child_group.id, 'order_index': link.order_index} for link in links]


class OfferingSerializer(serializers.ModelSerializer):
    """Offering serializer with basic info."""
    subject = SubjectBasicSerializer(read_only=True)
    
    class Meta:
        model = Offering
        fields = [
            'id', 'subject', 'type', 'term', 'section', 'semester', 
            'credits', 'is_active', 'url_source', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OfferingDetailSerializer(OfferingSerializer):
    """Offering serializer with nested requirement groups and links."""
    requirement_groups = RequirementGroupSerializer(many=True, read_only=True)
    links = OfferingLinkSerializer(many=True, read_only=True)
    
    class Meta(OfferingSerializer.Meta):
        fields = OfferingSerializer.Meta.fields + ['requirement_groups', 'links']


class SubjectEquivalenceSerializer(serializers.ModelSerializer):
    """Subject equivalence serializer."""
    subject_a = SubjectBasicSerializer(read_only=True)
    subject_b = SubjectBasicSerializer(read_only=True)
    
    class Meta:
        model = SubjectEquivalence
        fields = [
            'id', 'subject_a', 'subject_b', 'kind', 'note', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DependencyEdgeSerializer(serializers.ModelSerializer):
    """Dependency edge serializer."""
    source_offering = OfferingBasicSerializer(read_only=True)
    target_offering = OfferingBasicSerializer(read_only=True)
    
    class Meta:
        model = DependencyEdge
        fields = [
            'id', 'source_offering', 'target_offering', 'dep_kind', 
            'note', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# Nested Tree Serializer (for full requirement tree)
# ============================================================================

class RequirementGroupTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for requirement group trees."""
    items = RequirementItemSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementGroup
        fields = [
            'id', 'scope', 'flavor', 'min_required', 'note', 'order_index',
            'items', 'children'
        ]
    
    def get_children(self, obj):
        """Recursively get child groups."""
        child_links = obj.child_links.select_related('child_group').prefetch_related(
            'child_group__items',
            'child_group__items__target_subject',
            'child_group__items__target_offering',
            'child_group__items__target_offering__subject'
        ).order_by('order_index')
        
        children = [link.child_group for link in child_links]
        return RequirementGroupTreeSerializer(children, many=True, context=self.context).data

