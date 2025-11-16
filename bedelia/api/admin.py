from django.contrib import admin
from .models import Materia, PlanEstudio, PlanMateria, UnidadAprobable, RequisitoNodo, RequisitoItem


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    """Admin para Materias con búsqueda por código y nombre."""
    list_display = ['codigo', 'nombre', 'creditos', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']


@admin.register(PlanMateria)
class PlanMateriaAdmin(admin.ModelAdmin):
    """Admin para Materias en plan con búsqueda por código y nombre de materia."""
    list_display = ['plan', 'materia', 'fecha_creacion']
    list_filter = ['plan__nombre_carrera', 'plan__anio']
    search_fields = ['materia__codigo', 'materia__nombre']
    ordering = ['plan', 'materia__codigo']
    autocomplete_fields = ['plan', 'materia']


@admin.register(UnidadAprobable)
class UnidadAprobableAdmin(admin.ModelAdmin):
    """Admin para Unidades aprobables con búsqueda por código y nombre."""
    list_display = ['materia', 'tipo', 'codigo_bedelias', 'nombre', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['materia__codigo', 'materia__nombre', 'nombre', 'codigo_bedelias']
    ordering = ['materia__codigo', 'tipo']
    autocomplete_fields = ['materia']


@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    """Admin para Planes de estudio con búsqueda."""
    list_display = ['nombre_carrera', 'anio', 'descripcion', 'activo']
    list_filter = ['nombre_carrera', 'activo']
    search_fields = ['nombre_carrera', 'anio', 'descripcion']
    ordering = ['nombre_carrera', '-anio']


# Registrar los demás modelos con configuración básica
admin.site.register(RequisitoNodo)
admin.site.register(RequisitoItem)