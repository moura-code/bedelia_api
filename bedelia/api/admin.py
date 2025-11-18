from django.contrib import admin
from .models import Materia, PlanEstudio, PlanMateria, UnidadAprobable, RequisitoNodo, RequisitoItem


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
admin.site.register(RequisitoNodo)
admin.site.register(RequisitoItem)