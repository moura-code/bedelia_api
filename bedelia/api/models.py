from __future__ import annotations
import uuid
from django.db import models
from django.db.models import Q, F
from django.core.validators import RegexValidator


class Carrera(models.Model):
    """
    Modelo que representa una carrera en la universidad.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre de la Carrera")
    anio_plan = models.CharField(max_length=10, verbose_name="Año del Plan", blank=True, null=True)
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        db_table = 'carreras'
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
        unique_together = ['nombre', 'anio_plan']
        indexes = [
            models.Index(fields=['nombre'], name='idx_carrera_nombre'),
            models.Index(fields=['anio_plan'], name='idx_carrera_anio'),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.anio_plan})" if self.anio_plan else self.nombre


class Curso(models.Model):
    """
    Modelo que representa un curso/materia vigente en la universidad.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_universidad = models.CharField(max_length=50, verbose_name="Código de Universidad")
    codigo_curso = models.CharField(max_length=50, verbose_name="Código de Curso")
    nombre_curso = models.CharField(max_length=255, verbose_name="Nombre del Curso")
    carrera = models.ManyToManyField(Carrera, related_name='cursos', verbose_name="Carreras", blank=True)
    creditos = models.IntegerField(default=0, verbose_name="Créditos")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        db_table = 'cursos'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        unique_together = ['codigo_universidad', 'codigo_curso']
        indexes = [
            models.Index(fields=['codigo_curso'], name='idx_codigo_curso'),
            models.Index(fields=['codigo_universidad'], name='idx_codigo_universidad'),
            models.Index(fields=['activo'], name='idx_curso_activo'),
        ]
    
    def __str__(self):
        return f"{self.codigo_curso} - {self.nombre_curso}"



class Previa(models.Model):
    """
    Modelo que representa las previas (requisitos) de un curso.
    Estructura de árbol donde cada nodo puede ser:
    - ALL: debe cumplir TODOS los hijos
    - ANY: debe cumplir AL MENOS UNO de los hijos
    - NOT: NO debe tener NINGUNO de los hijos
    - LEAF: nodo hoja que contiene items individuales
    """
    TIPO_NODO_CHOICES = [
        ('ALL', 'Debe tener todas'),
        ('ANY', 'Debe tener alguna'),
        ('NOT', 'No debe tener'),
        ('LEAF', 'Hoja (items individuales)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Un curso puede tener múltiples nodos previas (el árbol completo)
    curso = models.ForeignKey(
        'Curso', 
        on_delete=models.CASCADE, 
        related_name='previas',
        verbose_name="Curso",
        null=True,
        blank=True
    )
    
    # Información del nodo
    codigo = models.CharField(max_length=255, verbose_name="Código", blank=True)
    nombre = models.CharField(max_length=255, verbose_name="Nombre", blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_NODO_CHOICES, verbose_name="Tipo")
    titulo = models.CharField(max_length=500, blank=True, null=True, verbose_name="Título")
    cantidad_requerida = models.IntegerField(default=0, verbose_name="Cantidad Requerida")
    
    # Para construir el árbol de requisitos
    # Los nodos ALL, ANY, NOT tienen hijos (otras previas)
    # Los nodos LEAF tienen items (ItemPrevia)
    padre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        related_name='hijos',
        null=True,
        blank=True,
        verbose_name="Nodo Padre"
    )
    orden = models.IntegerField(default=0, verbose_name="Orden")
    
    # Para identificar a qué carrera/plan pertenece esta previa
    carrera = models.ForeignKey(
        Carrera,
        on_delete=models.SET_NULL,
        related_name='previas',
        verbose_name="Carrera",
        null=True,
        blank=True
    )
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        db_table = 'previas'
        verbose_name = 'Previa'
        verbose_name_plural = 'Previas'
        indexes = [
            models.Index(fields=['curso'], name='idx_previa_curso'),
            models.Index(fields=['padre'], name='idx_previa_padre'),
            models.Index(fields=['tipo'], name='idx_previa_tipo'),
            models.Index(fields=['carrera'], name='idx_previa_carrera'),
        ]
    
    def __str__(self):
        if self.codigo:
            return f"{self.codigo} - {self.nombre} ({self.tipo})"
        return f"{self.titulo or 'Nodo'} ({self.tipo})"
    
    def es_raiz(self):
        """Retorna True si este nodo es la raíz del árbol (no tiene padre)"""
        return self.padre is None
    
    def obtener_hijos(self):
        """Retorna todos los hijos de este nodo ordenados"""
        return self.hijos.all().order_by('orden')


class ItemPrevia(models.Model):
    """
    Modelo que representa los items individuales dentro de una previa (nodo LEAF).
    Cada item representa un requisito específico (ej: UCB aprobada, Examen aprobado, etc.)
    """
    FUENTE_CHOICES = [
        ('UCB', 'UCB'),
        ('EXAMEN', 'Examen'),
        ('CREDITOS', 'Créditos'),
        ('OTRO', 'Otro'),
    ]
    
    MODALIDAD_CHOICES = [
        ('exam', 'Examen'),
        ('course', 'Curso'),
        ('ucb_module', 'Módulo UCB'),
        ('credits', 'Créditos'),
        ('other', 'Otra'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Este item pertenece a un nodo LEAF de previa
    previa = models.ForeignKey(
        'Previa', 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Previa (nodo LEAF)"
    )
    
    # Información del item
    fuente = models.CharField(max_length=50, verbose_name="Fuente")
    modalidad = models.CharField(max_length=50, verbose_name="Modalidad")
    codigo = models.CharField(max_length=50, verbose_name="Código")
    titulo = models.CharField(max_length=500, verbose_name="Título")
    notas = models.JSONField(default=list, blank=True, verbose_name="Notas")
    texto_raw = models.TextField(blank=True, verbose_name="Texto Raw")
    orden = models.IntegerField(default=0, verbose_name="Orden")
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        db_table = 'items_previa'
        verbose_name = 'Item de Previa'
        verbose_name_plural = 'Items de Previa'
        ordering = ['orden']
        indexes = [
            models.Index(fields=['previa', 'orden'], name='idx_item_previa_orden'),
            models.Index(fields=['codigo'], name='idx_item_codigo'),
            models.Index(fields=['modalidad'], name='idx_item_modalidad'),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.titulo} ({self.modalidad})"


class Posprevia(models.Model):
    """
    Modelo que representa las posprevias (materias que requieren un curso como requisito).
    """
    TIPO_CHOICES = [
        ('Curso', 'Curso'),
        ('Examen', 'Examen'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curso = models.ForeignKey(
        'Curso', 
        on_delete=models.CASCADE, 
        related_name='posprevias',
        verbose_name="Curso"
    )
    codigo = models.CharField(max_length=50, verbose_name="Código")
    nombre = models.CharField(max_length=255, verbose_name="Nombre")
    
    # Información de la materia que tiene como requisito este curso
    anio_plan = models.CharField(max_length=10, verbose_name="Año del Plan")
    carrera = models.CharField(max_length=255, verbose_name="Carrera")
    fecha = models.CharField(max_length=20, verbose_name="Fecha")
    descripcion = models.TextField(verbose_name="Descripción")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    materia_codigo = models.CharField(max_length=50, verbose_name="Código de Materia")
    materia_nombre = models.CharField(max_length=255, verbose_name="Nombre de Materia")
    materia_full = models.CharField(max_length=255, verbose_name="Materia Completa")
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        db_table = 'posprevias'
        verbose_name = 'Posprevia'
        verbose_name_plural = 'Posprevias'
        indexes = [
            models.Index(fields=['curso'], name='idx_posprevia_curso'),
            models.Index(fields=['codigo'], name='idx_posprevia_codigo'),
            models.Index(fields=['materia_codigo'], name='idx_posprevia_materia_codigo'),
            models.Index(fields=['carrera', 'anio_plan'], name='idx_posprevia_carrera_anio'),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre} → {self.materia_codigo}"


