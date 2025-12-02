from django.contrib import admin
from .models import Materia, PlanEstudio, PlanMateria, UnidadAprobable,PreviaNodo, PreviaItem


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    """Admin para Materias con búsqueda por código y nombre."""
    list_display = ['id', 'codigo', 'nombre', 'creditos', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']



@admin.register(UnidadAprobable)
class UnidadAprobableAdmin(admin.ModelAdmin):
    """Admin para Unidades aprobables con búsqueda por código y nombre."""
    list_display = ['id', 'materia', 'tipo', 'codigo_bedelias', 'nombre', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['materia__codigo', 'materia__nombre', 'nombre', 'codigo_bedelias']
    ordering = ['materia__codigo', 'tipo']
    autocomplete_fields = ['materia']


@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    """Admin para Planes de estudio con búsqueda."""
    list_display = ['id', 'nombre_carrera', 'anio', 'descripcion', 'activo']
    list_filter = ['nombre_carrera', 'activo']
    search_fields = ['nombre_carrera', 'anio', 'descripcion']
    ordering = ['nombre_carrera', '-anio']


@admin.register(PlanMateria)
class PlanMateriaAdmin(admin.ModelAdmin):
    """Admin para relaciones Plan-Materia."""
    list_display = ['id', 'plan', 'materia', 'activo']
    list_filter = ['activo', 'plan__nombre_carrera']
    search_fields = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo', 'materia__nombre']
    ordering = ['plan__nombre_carrera', 'plan__anio', 'materia__codigo']
    autocomplete_fields = ['plan', 'materia']


# Registrar los demás modelos con configuración básica
@admin.register(PreviaNodo)
class PreviaNodoAdmin(admin.ModelAdmin):
    """Admin para nodos de previas con búsqueda."""
    list_display = ['id', 'plan_materia', 'tipo', 'padre', 'unidad_tipo', 'descripcion']
    list_filter = ['tipo', 'unidad_tipo']
    search_fields = ['id', 'plan_materia__plan__nombre_carrera', 'plan_materia__materia__codigo', 'plan_materia__materia__nombre', 'tipo', 'descripcion']
    ordering = ['plan_materia__plan__nombre_carrera', 'orden']


@admin.register(PreviaItem)
class PreviaItemAdmin(admin.ModelAdmin):
    """Admin para items de previas con búsqueda."""
    list_display = ['id', 'nodo', 'tipo', 'unidad_requerida', 'creditos_minimos', 'texto']
    list_filter = ['tipo']
    search_fields = ['id', 'nodo__plan_materia__plan__nombre_carrera', 'nodo__plan_materia__materia__codigo', 'texto', 'unidad_requerida__materia__codigo']
    ordering = ['nodo__plan_materia__plan__nombre_carrera', 'orden']