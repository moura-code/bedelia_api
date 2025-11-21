"""
Serializers for Materia-related models.
"""
from typing import List, Dict, Any
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.models import (
    Materia,
    PlanEstudio,
    PlanMateria,
    UnidadAprobable,
    PreviaNodo,
    PreviaItem,
)


class MateriaSerializer(serializers.ModelSerializer):
    """Serializador básico para el modelo Materia."""
    
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
    """Serializador detallado para Materia con relaciones anidadas."""
    
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
    
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_unidades(self, obj: Materia) -> List[Dict[str, Any]]:
        """Obtener unidades aprobables para esta materia."""
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
    
    @extend_schema_field(serializers.IntegerField())
    def get_planes_count(self, obj: Materia) -> int:
        """Obtener cantidad de planes que incluyen esta materia."""
        return obj.planes.count()


class PlanEstudioSerializer(serializers.ModelSerializer):
    """Serializador para PlanEstudio con información de carrera."""
    
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
    
    @extend_schema_field(serializers.IntegerField())
    def get_materias_count(self, obj: PlanEstudio) -> int:
        """Obtener cantidad de materias en este plan."""
        return obj.materias_plan.count()


class PlanMateriaSerializer(serializers.ModelSerializer):
    """Serializador para PlanMateria (relación plan-materia)."""
    
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
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class PlanEstudioMateriaSerializer(serializers.ModelSerializer):
    """Serializador para PlanEstudio con detalles de materia."""
    
    plan = PlanEstudioSerializer(read_only=True)
    plan_id = serializers.UUIDField(source='plan.id', read_only=True)
    materia = MateriaSerializer(read_only=True)
    materia_id = serializers.UUIDField(source='materia.id', read_only=True)
    materia_codigo = serializers.CharField(source='materia.codigo', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    class Meta:
        model = PlanEstudio
        fields = [
            'id',
            'plan',
            'plan_id',  
            'materia',
            'materia_id',
            'materia_codigo',
            'materia_nombre',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = fields


class UnidadAprobableSerializer(serializers.ModelSerializer):
    """Serializador para UnidadAprobable con información de materia."""
    
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


# ============================================================
# Serializers for Previas (Separate Model)
# ============================================================

class PreviaItemSerializer(serializers.ModelSerializer):
    """Serializador para PreviaItem."""
    
    nodo_id = serializers.UUIDField(source='nodo.id', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    unidad_requerida = UnidadAprobableSerializer(read_only=True)
    unidad_requerida_id = serializers.UUIDField(source='unidad_requerida.id', read_only=True, allow_null=True)
    
    class Meta:
        model = PreviaItem
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


class PreviaNodoSerializer(serializers.ModelSerializer):
    """Serializador básico para PreviaNodo."""
    
    plan_materia_id = serializers.UUIDField(source='plan_materia.id', read_only=True, allow_null=True)
    padre_id = serializers.UUIDField(source='padre.id', read_only=True, allow_null=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    hijos_count = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PreviaNodo
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
    
    @extend_schema_field(serializers.IntegerField())
    def get_hijos_count(self, obj: PreviaNodo) -> int:
        """Obtener cantidad de nodos hijos."""
        return obj.hijos.count()
    
    @extend_schema_field(serializers.IntegerField())
    def get_items_count(self, obj: PreviaNodo) -> int:
        """Obtener cantidad de items (solo para nodos LEAF)."""
        return obj.items.count() if obj.tipo == PreviaNodo.Tipo.LEAF else 0


class PreviaNodoTreeSerializer(serializers.ModelSerializer):
    """Serializador recursivo para estructura de árbol de PreviaNodo."""
    
    plan_materia_id = serializers.UUIDField(source='plan_materia.id', read_only=True, allow_null=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    hijos = serializers.SerializerMethodField()
    items = PreviaItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PreviaNodo
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
    
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_hijos(self, obj: PreviaNodo) -> List[Dict[str, Any]]:
        """Serializar recursivamente nodos hijos."""
        hijos = obj.hijos_ordenados()
        return PreviaNodoTreeSerializer(hijos, many=True).data
