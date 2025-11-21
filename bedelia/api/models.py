from __future__ import annotations

import uuid
from django.db import models


# ============================================================
# Núcleo académico
# ============================================================

class PlanEstudio(models.Model):
    """
    Plan de estudios de una carrera (ej: Ing. en Computación 2010, 2020, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_carrera = models.CharField(max_length=255, verbose_name="Nombre de la carrera", db_index=True)
    anio = models.CharField(max_length=10, verbose_name="Año del plan")
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "planes_estudio"
        verbose_name = "Plan de estudio"
        verbose_name_plural = "Planes de estudio"
        unique_together = ("nombre_carrera", "anio")
        indexes = [
            models.Index(fields=["nombre_carrera", "anio"], name="idx_plan_carrera_anio"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre_carrera} - Plan {self.anio}"
    
class Materia(models.Model):
    """
    Materia lógica: Programación 1, Programación 2, etc.
    Independiente de la carrera/plan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50, db_index=True, verbose_name="Código")
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la materia")
    creditos = models.IntegerField(default=0, verbose_name="Créditos de referencia")
    activo = models.BooleanField(default=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "materias"
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        unique_together = ("codigo",)

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"

class PlanMateria(models.Model):
    """
    Relación entre un Plan de Estudio y una Materia.
    Representa que una materia específica está incluida en un plan de estudio específico.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        PlanEstudio,
        on_delete=models.CASCADE,
        related_name="materias_plan",
        verbose_name="Plan de estudio"
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name="planes",
        verbose_name="Materia"
    )
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plan_materias"
        verbose_name = "Plan-Materia"
        verbose_name_plural = "Plan-Materias"
        unique_together = ("plan", "materia")
        indexes = [
            models.Index(fields=["plan"], name="idx_plan_materia_plan"),
            models.Index(fields=["materia"], name="idx_plan_materia_materia"),
        ]

    def __str__(self) -> str:
        return f"{self.plan} :: {self.materia}"

class UnidadAprobable(models.Model):
    """
    Algo que el estudiante puede aprobar y que puede ser pedido como previa.
    Ejemplos:
    - Curso de Programación 1
    - Examen de Programación 1
    - Módulo/UCB específico, etc.
    """

    class Tipo(models.TextChoices):
        CURSO = "CURSO", "Curso"
        EXAMEN = "EXAMEN", "Examen"
        UCB = "UCB", "Módulo/UCB"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name="unidades")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, verbose_name="Tipo de unidad")
    codigo_bedelias = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Código Bedelías / identificador externo",
    )
    nombre = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre descriptivo (opcional)",
    )

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "unidades_aprobables"
        verbose_name = "Unidad aprobable"
        verbose_name_plural = "Unidades aprobables"
        indexes = [
            models.Index(fields=["materia"], name="idx_unidad_materia"),
            models.Index(fields=["tipo"], name="idx_unidad_tipo"),
        ]

    def __str__(self) -> str:
        base = f"{self.materia.codigo} - {self.get_tipo_display()}"
        if self.codigo_bedelias:
            base += f" ({self.codigo_bedelias})"
        return base
    
class PosPreviaItem(models.Model):
    """
    Condición concreta asociada a un nodo LEAF de posprevias.
    Representa una PlanMateria específica que requiere esta materia como prerequisito.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Descripción / texto auxiliar",
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name="posprevias",
        verbose_name="Materia",
    )
    plan_estudio = models.ForeignKey(
        PlanEstudio,
        on_delete=models.CASCADE,
        related_name="posprevias_plan_estudio",
        verbose_name="Plan de estudio",
    )
    unidades_dependientes = models.ManyToManyField(
        UnidadAprobable,

        related_name="posprevias_unidades_dependientes",
        verbose_name="Unidades dependientes",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.materia} :: {self.materia_dependiente} :: {self.descripcion}"

# ============================================================
# Unidades aprobables (Curso / Examen / etc.)
# ============================================================


class PreviaNodo(models.Model):
    """
    Nodo del árbol lógico de previas (prerequisites).
    Este modelo almacena solo los REQUISITOS PREVIOS que una materia necesita.
    
    Tipo:
    - ALL: deben cumplirse todos los hijos
    - ANY: deben cumplirse al menos 'cantidad_minima' hijos (por defecto 1)
    - NOT: no debe cumplirse ninguno de los hijos
    - LEAF: nodo hoja, sus condiciones se expresan en PreviaItem
    """

    class Tipo(models.TextChoices):
        ALL = "ALL", "Debe cumplir todas"
        ANY = "ANY", "Debe cumplir alguna"
        NOT = "NOT", "No debe cumplir"
        LEAF = "LEAF", "Condición hoja"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relación con PlanMateria (solo para nodos raíz)
    plan_materia = models.ForeignKey(
        "PlanMateria",
        on_delete=models.CASCADE,
        related_name="previas",
        null=True,
        blank=True,
        verbose_name="Materia en plan a la que aplica",
    )

    tipo = models.CharField(max_length=10, choices=Tipo.choices, verbose_name="Tipo de nodo")

    padre = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="hijos",
        null=True,
        blank=True,
        verbose_name="Nodo padre",
    )
    unidad_tipo = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Tipo de unidad",
        help_text="Tipo de UnidadAprobable al que aplican estos requisitos",
        choices=UnidadAprobable.Tipo.choices,
    )
    # Para ANY: mínimo de hijos verdaderos (si es null, se asume 1)
    cantidad_minima = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Cantidad mínima (para ANY)",
    )

    orden = models.IntegerField(default=0)
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Descripción / texto auxiliar",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "previas_nodos"
        verbose_name = "Nodo de previa"
        verbose_name_plural = "Nodos de previas"
        ordering = ["orden"]
        indexes = [
            models.Index(fields=["plan_materia"], name="idx_previa_plan_materia"),
            models.Index(fields=["padre"], name="idx_previa_padre"),
            models.Index(fields=["tipo"], name="idx_previa_tipo"),
            models.Index(fields=["plan_materia", "unidad_tipo"], name="idx_req_pm_unidad"),
      ]
  

    def __str__(self) -> str:
        if self.plan_materia and self.es_raiz():
            return f"Previa Root {self.tipo} :: {self.plan_materia}"
        return f"Previa {self.tipo} (id={self.id})"

    def es_raiz(self) -> bool:
        return self.padre is None

    def hijos_ordenados(self):
        return self.hijos.all().order_by("orden")

class PreviaItem(models.Model):
    """
    Condición concreta asociada a un nodo LEAF de previas.
    Puede ser:
    - UNIDAD: aprobar una unidad específica (curso/examen/ucb)
    - CREDITOS: tener al menos X créditos
    - TEXTO: condición libre no estructurada (fallback)
    """

    class TipoItem(models.TextChoices):
        UNIDAD = "UNIDAD", "Unidad aprobable específica"
        CREDITOS = "CREDITOS", "Créditos mínimos"
        TEXTO = "TEXTO", "Condición libre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nodo = models.ForeignKey(
        PreviaNodo,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Nodo LEAF",
    )

    tipo = models.CharField(max_length=20, choices=TipoItem.choices, verbose_name="Tipo de condición")

    # Si tipo == UNIDAD
    unidad_requerida = models.ForeignKey(
        UnidadAprobable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="como_previa",
        verbose_name="Unidad requerida",
    )

    # Si tipo == CREDITOS
    creditos_minimos = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Créditos mínimos requeridos",
    )

    # Si tipo == TEXTO (o nota adicional)
    texto = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Descripción textual",
    )

    orden = models.IntegerField(default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "previas_items"
        verbose_name = "Item de previa"
        verbose_name_plural = "Items de previas"
        ordering = ["orden"]
        indexes = [
            models.Index(fields=["nodo", "orden"], name="idx_previa_item_nodo_orden"),
        ]

    def __str__(self) -> str:
        if self.tipo == self.TipoItem.UNIDAD and self.unidad_requerida:
            return f"[UNIDAD] {self.unidad_requerida}"
        if self.tipo == self.TipoItem.CREDITOS and self.creditos_minimos is not None:
            return f"[CREDITOS] ≥ {self.creditos_minimos}"
        return f"[{self.tipo}] {self.texto or self.id}"


# ============================================================
# Posprevias (Dependents) - Separate Model
# ============================================================
