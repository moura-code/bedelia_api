"""
Serializers for Materia-related models.
"""
from rest_framework import serializers

from api.models import (
    Materia,
    PlanEstudio,
    PlanMateria,
    UnidadAprobable,
    RequisitoNodo,
    RequisitoItem,
)


class MateriaSerializer(serializers.ModelSerializer):
    """Basic serializer for Materia model."""
    
    class Meta:
        model = Materia
        fields = [
            'id',
            'codigo',
            'nombre',
            'creditos',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class MateriaDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Materia with nested relationships."""
    
    unidades = serializers.SerializerMethodField()
    planes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Materia
        fields = [
            'id',
            'codigo',
            'nombre',
            'creditos',
            'activo',
            'unidades',
            'planes_count',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields
    
    def get_unidades(self, obj):
        """Get unidades aprobables for this materia."""
        unidades = obj.unidades.all()
        return [
            {
                'id': str(u.id),
                'tipo': u.tipo,
                'tipo_display': u.get_tipo_display(),
                'codigo_bedelias': u.codigo_bedelias,
                'nombre': u.nombre,
                'activo': u.activo,
            }
            for u in unidades
        ]
    
    def get_planes_count(self, obj):
        """Get count of plans that include this materia."""
        return obj.planes.count()


class PlanEstudioSerializer(serializers.ModelSerializer):
    """Serializer for PlanEstudio with carrera info."""
    
    materias_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanEstudio
        fields = [
            'id',
            'nombre_carrera',
            'anio',
            'descripcion',
            'activo',
            'materias_count',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields
    
    def get_materias_count(self, obj):
        """Get count of materias in this plan."""
        return obj.materias_plan.count()


class PlanMateriaSerializer(serializers.ModelSerializer):
    """Serializer for PlanMateria with plan and materia details."""
    
    plan = PlanEstudioSerializer(read_only=True)
    plan_id = serializers.UUIDField(source='plan.id', read_only=True)
    materia = MateriaSerializer(read_only=True)
    materia_id = serializers.UUIDField(source='materia.id', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    
    class Meta:
        model = PlanMateria
        fields = [
            'id',
            'plan',
            'plan_id',
            'materia',
            'materia_id',
            'materia_codigo',
            'materia_nombre',
            'obligatorio',
            'semestre_sugerido',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class UnidadAprobableSerializer(serializers.ModelSerializer):
    """Serializer for UnidadAprobable with materia info."""
    
    materia = MateriaSerializer(read_only=True)
    materia_id = serializers.UUIDField(source='materia.id', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = UnidadAprobable
        fields = [
            'id',
            'materia',
            'materia_id',
            'materia_codigo',
            'materia_nombre',
            'tipo',
            'tipo_display',
            'codigo_bedelias',
            'nombre',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class RequisitoItemSerializer(serializers.ModelSerializer):
    """Serializer for RequisitoItem."""
    
    nodo_id = serializers.UUIDField(source='nodo.id', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    unidad_requerida = UnidadAprobableSerializer(read_only=True)
    unidad_requerida_id = serializers.UUIDField(source='unidad_requerida.id', read_only=True, allow_null=True)
    
    class Meta:
        model = RequisitoItem
        fields = [
            'id',
            'nodo_id',
            'tipo',
            'tipo_display',
            'unidad_requerida',
            'unidad_requerida_id',
            'creditos_minimos',
            'texto',
            'orden',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class RequisitoNodoSerializer(serializers.ModelSerializer):
    """Basic serializer for RequisitoNodo."""
    
    plan_materia_id = serializers.UUIDField(source='plan_materia.id', read_only=True, allow_null=True)
    padre_id = serializers.UUIDField(source='padre.id', read_only=True, allow_null=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    hijos_count = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RequisitoNodo
        fields = [
            'id',
            'plan_materia_id',
            'tipo',
            'tipo_display',
            'padre_id',
            'cantidad_minima',
            'orden',
            'descripcion',
            'hijos_count',
            'items_count',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields
    
    def get_hijos_count(self, obj):
        """Get count of child nodes."""
        return obj.hijos.count()
    
    def get_items_count(self, obj):
        """Get count of items (only for LEAF nodes)."""
        return obj.items.count() if obj.tipo == RequisitoNodo.Tipo.LEAF else 0


class RequisitoNodoTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for RequisitoNodo tree structure."""
    
    plan_materia_id = serializers.UUIDField(source='plan_materia.id', read_only=True, allow_null=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    hijos = serializers.SerializerMethodField()
    items = RequisitoItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = RequisitoNodo
        fields = [
            'id',
            'plan_materia_id',
            'tipo',
            'tipo_display',
            'cantidad_minima',
            'orden',
            'descripcion',
            'hijos',
            'items',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields
    
    def get_hijos(self, obj):
        """Recursively serialize child nodes."""
        hijos = obj.hijos_ordenados()
        return RequisitoNodoTreeSerializer(hijos, many=True).data

