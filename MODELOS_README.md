# Documentación de Modelos - Sistema Bedelia

## 📚 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura General](#arquitectura-general)
3. [Modelos Core](#modelos-core)
4. [Sistema de Requisitos](#sistema-de-requisitos)
5. [Modelos de Relaciones](#modelos-de-relaciones)
6. [Ejemplos Prácticos](#ejemplos-prácticos)
7. [Flujo de Datos](#flujo-de-datos)
8. [Glosario](#glosario)

---

## Introducción

### ¿Qué es el Sistema Bedelia?

Bedelia es un sistema de gestión académica que modela:
- **Programas** académicos y planes de estudio
- **Materias** y sus características
- **Ofertas** de cursos y exámenes por período
- **Requisitos** jerárquicos y complejos (previaturas)
- **Equivalencias** entre materias
- **Dependencias** para análisis de trayectorias académicas

### Propósito

Este sistema permite:
- ✅ Consultar qué materias puede cursar un estudiante
- ✅ Verificar el cumplimiento de requisitos previos
- ✅ Modelar lógica compleja: "Aprobar 2 de 3 materias" o "NO haber aprobado X"
- ✅ Rastrear qué materias se desbloquean al aprobar una materia (posprevias)
- ✅ Gestionar múltiples planes de estudio y equivalencias

---

## Arquitectura General

### Diagrama de Relaciones

```
Program (Programa)
    ↓ tiene muchas
Subject (Materia) ←→ SubjectAlias
    ↓ tiene muchas
Offering (Oferta de Curso/Examen)
    ↓ tiene muchos
RequirementGroup (Grupo de Requisitos)
    ↓ contiene
    ├─→ RequirementGroupLink (Enlaces padre-hijo)
    └─→ RequirementItem (Items individuales)
            ↓ apunta a
            Subject o Offering

SubjectEquivalence: Subject ←→ Subject
DependencyEdge: materializa las dependencias para consultas rápidas
```

### Jerarquía de Modelos

```
BaseModel (abstracto)
    ├─ Program
    ├─ Subject
    │   └─ SubjectAlias
    ├─ Offering
    │   └─ OfferingLink
    ├─ RequirementGroup
    │   ├─ RequirementGroupLink
    │   └─ RequirementItem
    ├─ SubjectEquivalence
    ├─ DependencyEdge
    └─ AuditSource
```

---

## Modelos Core

### 1. BaseModel (Modelo Base Abstracto)

**Propósito**: Modelo abstracto que proporciona campos comunes a todos los modelos.

**Campos**:
- `id` (UUID): Identificador único universal
- `created_at` (DateTime): Fecha de creación
- `updated_at` (DateTime): Fecha de última actualización

**Uso**: Todos los modelos heredan de BaseModel para tener IDs consistentes y auditoría temporal.

---

### 2. Program (Programa)

**Propósito**: Representa programas académicos o planes de estudio.

**Campos**:
- `name` (CharField): Nombre completo del programa
  - Ejemplo: `"1997 - INGENIERIA EN COMPUTACION"`
- `plan_year` (IntegerField): Año del plan de estudios
  - Ejemplo: `1997`, `2023`

**Relaciones**:
- `subjects` (reversa): Todas las materias asociadas a este programa

**Ejemplos de Uso**:
```python
# Crear un programa
programa = Program.objects.create(
    name="2023 - INGENIERIA ELECTRICA",
    plan_year=2023
)

# Obtener todas las materias de un programa
materias = programa.subjects.all()
```

**Datos Reales**:
```json
{
  "name": "1997 - INGENIERIA EN COMPUTACION",
  "plan_year": 1997
}
```

---

### 3. Subject (Materia)

**Propósito**: Representa materias o cursos canónicos en el sistema.

**Campos**:
- `program` (ForeignKey → Program): Programa al que pertenece
- `code` (CharField): Código de la materia
  - Ejemplo: `"DMA01"`, `"CAL2"`, `"1944"`
- `name` (CharField): Nombre completo de la materia
  - Ejemplo: `"CÁLCULO DIFERENCIAL E INTEGRAL EN UNA VARIABLE"`
- `credits` (DecimalField): Créditos de la materia
  - Ejemplo: `12.00`, `10.00`
- `dept` (CharField): Departamento que dicta la materia
- `description` (TextField): Descripción detallada
- `semester` (IntegerField): Semestre recomendado (1 o 2)

**Relaciones**:
- `program` (ForeignKey): Programa académico
- `offerings` (reversa): Todas las ofertas de esta materia
- `aliases` (reversa): Códigos y nombres alternativos

**Restricciones**:
- Combinación única de `program` + `code`
- `semester` debe ser 1, 2 o null

**Ejemplos de Uso**:
```python
# Buscar una materia por código
calculo = Subject.objects.get(code="DMA01")

# Materias con más de 10 créditos
materias_pesadas = Subject.objects.filter(credits__gte=10)

# Materias de un programa específico
materias_programa = Subject.objects.filter(program=programa)
```

**Datos Reales** (de `credits.json`):
```json
{
  "codigo": "DMA01",
  "nombre": "CÁLCULO DIFERENCIAL E INTEGRAL EN UNA VARIABLE",
  "creditos": "12"
}
```

---

### 4. SubjectAlias (Alias de Materia)

**Propósito**: Almacena códigos y nombres alternativos para materias, útil para matching y scraping.

**Campos**:
- `subject` (ForeignKey → Subject): Materia a la que hace referencia
- `alias_code` (CharField): Código alternativo
- `alias_name` (CharField): Nombre alternativo

**Restricciones**:
- Un alias de código debe ser único por materia
- Un alias de nombre debe ser único por materia

**Casos de Uso**:
- Materias que cambiaron de código entre planes
- Nombres abreviados o variantes
- Integración con sistemas externos

---

### 5. Offering (Oferta)

**Propósito**: Representa una instancia específica de una materia en un período académico determinado.

**Campos**:
- `subject` (ForeignKey → Subject): Materia que se ofrece
- `type` (CharField): Tipo de oferta
  - `"COURSE"`: Curso regular
  - `"EXAM"`: Examen
- `term` (CharField): Período académico
  - Formato: `"2025S1"` (año + S + semestre)
  - Ejemplo: `"2025S1"`, `"2024S2"`
- `section` (CharField): Sección o grupo
- `semester` (IntegerField): Semestre (1, 2 o 3)
- `credits` (DecimalField): Créditos de esta oferta específica
- `is_active` (BooleanField): Si la oferta está activa
- `url_source` (URLField): URL fuente de los datos
- `scraped_at` (DateTime): Cuándo se obtuvieron los datos
- `html_hash` (CharField): Hash del contenido HTML

**Relaciones**:
- `subject` (ForeignKey): Materia ofrecida
- `requirement_groups` (reversa): Grupos de requisitos
- `links` (reversa): Enlaces útiles (syllabus, Moodle, etc.)

**Restricciones**:
- Combinación única: `subject` + `type` + `term` + `section`
- `semester` debe ser 1, 2, 3 o null

**Ejemplos de Uso**:
```python
# Crear una oferta de curso
oferta = Offering.objects.create(
    subject=calculo,
    type="COURSE",
    term="2025S1",
    is_active=True
)

# Ofertas de examen del semestre actual
examenes = Offering.objects.filter(
    type="EXAM",
    term="2025S1",
    is_active=True
)

# Todos los cursos de una materia
cursos = Offering.objects.filter(subject=calculo, type="COURSE")
```

**Diferencia entre COURSE y EXAM**:
- **COURSE**: El curso regular de la materia (asistir a clases)
- **EXAM**: El examen de la materia (solo rendir examen)

---

### 6. OfferingLink (Enlaces de Oferta)

**Propósito**: Almacena enlaces útiles asociados a una oferta.

**Campos**:
- `offering` (ForeignKey → Offering): Oferta relacionada
- `kind` (CharField): Tipo de enlace
  - Ejemplos: `"syllabus"`, `"moodle"`, `"slides"`, `"video"`
- `url` (URLField): URL del recurso
- `title` (CharField): Título para mostrar

**Casos de Uso**:
- Enlace al programa del curso
- Enlace a Moodle
- Enlace a material complementario

---

## Sistema de Requisitos

El sistema de requisitos es la parte más compleja y poderosa de Bedelia. Permite modelar lógica arbitrariamente compleja usando una estructura de árbol.

### Conceptos Clave

#### Estructura de Árbol
Los requisitos se organizan en una estructura jerárquica:
- **Grupos** (nodos internos): contienen lógica (ALL/ANY/NONE)
- **Items** (hojas): apuntan a materias o ofertas específicas
- **Enlaces**: conectan grupos padre-hijo

### 7. RequirementGroup (Grupo de Requisitos)

**Propósito**: Nodos del árbol de requisitos que definen lógica de agrupación.

**Campos**:
- `offering` (ForeignKey → Offering): Oferta a la que aplican estos requisitos
- `scope` (CharField): Alcance/lógica del grupo
  - `"ALL"`: **TODAS** las condiciones deben cumplirse (Y lógico)
  - `"ANY"`: Al menos `min_required` deben cumplirse (O lógico)
  - `"NONE"`: **NINGUNA** debe cumplirse (prohibición)
- `flavor` (CharField): Tipo semántico del grupo
  - `"GENERIC"`: Genérico
  - `"APPROVALS"`: Aprobaciones
  - `"ACTIVITIES"`: Actividades
  - `"COURSE_APPROVED"`: Curso aprobado
  - `"EXAM_APPROVED"`: Examen aprobado
  - Y más...
- `min_required` (IntegerField): Mínimo requerido (solo para `scope="ANY"`)
  - Ejemplo: Si `min_required=2` y hay 3 items, se necesitan aprobar 2 de 3
- `note` (CharField): Notas adicionales
- `order_index` (IntegerField): Orden de visualización

**Relaciones**:
- `offering` (ForeignKey): Oferta a la que pertenece
- `items` (reversa): Items de requisito (hojas)
- `child_links` (reversa): Enlaces a grupos hijos
- `parent_links` (reversa): Enlaces desde grupos padres

**Restricciones**:
- Si `scope="ANY"`, entonces `min_required` debe ser ≥ 1
- Si `scope="ALL"` o `scope="NONE"`, entonces `min_required` debe ser null

**Ejemplos de Uso**:

```python
# Grupo ALL: "Debes aprobar TODAS estas materias"
grupo_all = RequirementGroup.objects.create(
    offering=oferta_calculo2,
    scope="ALL",
    flavor="GENERIC",
    min_required=None  # No aplica para ALL
)

# Grupo ANY: "Debes aprobar 2 de las siguientes materias"
grupo_any = RequirementGroup.objects.create(
    offering=oferta_algebra2,
    scope="ANY",
    flavor="APPROVALS",
    min_required=2  # Aprobar 2 de N
)

# Grupo NONE: "NO debes tener aprobadas estas materias"
grupo_none = RequirementGroup.objects.create(
    offering=oferta_intro,
    scope="NONE",
    flavor="GENERIC",
    min_required=None
)
```

---

### 8. RequirementGroupLink (Enlace de Grupos)

**Propósito**: Conecta grupos padre-hijo para formar la estructura de árbol.

**Campos**:
- `parent_group` (ForeignKey → RequirementGroup): Grupo padre
- `child_group` (ForeignKey → RequirementGroup): Grupo hijo
- `order_index` (IntegerField): Orden del hijo dentro del padre

**Restricciones**:
- Un grupo no puede ser su propio padre (no auto-referencias)
- Combinación única de `parent_group` + `child_group`

**Casos de Uso**:
- Crear requisitos anidados complejos
- "Para aprobar X debes cumplir ALL de (Item1, Item2, ANY de (Item3, Item4))"

---

### 9. RequirementItem (Item de Requisito)

**Propósito**: Nodos hoja del árbol que apuntan a materias u ofertas específicas.

**Campos**:
- `group` (ForeignKey → RequirementGroup): Grupo al que pertenece
- `target_type` (CharField): Tipo de objetivo
  - `"SUBJECT"`: Apunta a una materia (cualquier oferta)
  - `"OFFERING"`: Apunta a una oferta específica
- `target_subject` (ForeignKey → Subject): Materia objetivo (si `target_type="SUBJECT"`)
- `target_offering` (ForeignKey → Offering): Oferta objetivo (si `target_type="OFFERING"`)
- `condition` (CharField): Condición requerida
  - `"APPROVED"`: Debe estar aprobado
  - `"ENROLLED"`: Debe estar inscrito
  - `"CREDITED"`: Debe estar acreditado
- `alt_code` (CharField): Código alternativo si no se resuelve el ID
- `alt_label` (CharField): Etiqueta para mostrar
- `order_index` (IntegerField): Orden dentro del grupo

**Restricciones**:
- Exactamente uno de `target_subject` o `target_offering` debe estar establecido
- Debe coincidir con `target_type`

**Ejemplos de Uso**:

```python
# Requisito: "Aprobar Cálculo 1" (cualquier oferta)
item1 = RequirementItem.objects.create(
    group=grupo,
    target_type="SUBJECT",
    target_subject=calculo1,
    condition="APPROVED",
    alt_label="Cálculo 1"
)

# Requisito: "Estar inscrito en el examen específico de Álgebra 2025S1"
item2 = RequirementItem.objects.create(
    group=grupo,
    target_type="OFFERING",
    target_offering=examen_algebra_2025s1,
    condition="ENROLLED"
)
```

---

## Cómo Funcionan los Requisitos

### Lógica ALL (Y lógico)

**Significado**: **TODAS** las condiciones deben cumplirse.

**Ejemplo Visual**:
```
Requisitos para "Cálculo 2":
└─ ALL
   ├─ Aprobar: Cálculo 1
   ├─ Aprobar: Álgebra Lineal 1
   └─ Tener 30 créditos
```

**Interpretación**: Se deben cumplir las 3 condiciones para cursar Cálculo 2.

### Lógica ANY (O lógico)

**Significado**: Al menos `min_required` condiciones deben cumplirse.

**Ejemplo Visual**:
```
Requisitos para "Proyecto Final":
└─ ANY (min_required=2)
   ├─ Aprobar: Algoritmos Avanzados
   ├─ Aprobar: Sistemas Operativos
   └─ Aprobar: Redes de Computadoras
```

**Interpretación**: Se deben aprobar al menos 2 de las 3 materias listadas.

### Lógica NONE (Prohibición)

**Significado**: **NINGUNA** de las condiciones debe cumplirse (todas deben estar NO cumplidas).

**Ejemplo Visual**:
```
Requisitos para "Introducción a la Programación":
└─ NONE
   └─ Tener aprobado: Programación Avanzada
```

**Interpretación**: NO puedes cursar Intro si ya aprobaste Programación Avanzada (es una materia más básica).

### Ejemplo Complejo: Requisitos Anidados

```
Requisitos para "Tesis de Grado":
└─ ALL
   ├─ Tener 180 créditos
   ├─ Aprobar: Metodología de la Investigación
   └─ ANY (min_required=1)
      ├─ ALL
      │  ├─ Aprobar: Proyecto de Software 1
      │  └─ Aprobar: Proyecto de Software 2
      └─ ALL
         ├─ Aprobar: Investigación en IA 1
         └─ Aprobar: Investigación en IA 2
```

**Interpretación**:
- Debes tener 180 créditos (ALL)
- Y debes aprobar Metodología (ALL)
- Y debes haber completado UNA de las siguientes trayectorias (ANY con min=1):
  - Trayectoria A: Proyecto de Software 1 Y 2
  - Trayectoria B: Investigación en IA 1 Y 2

---

## Modelos de Relaciones

### 10. SubjectEquivalence (Equivalencia de Materias)

**Propósito**: Define relaciones de equivalencia entre materias.

**Campos**:
- `subject_a` (ForeignKey → Subject): Primera materia
- `subject_b` (ForeignKey → Subject): Segunda materia
- `kind` (CharField): Tipo de equivalencia
  - `"FULL"`: Equivalencia total (una reemplaza completamente a la otra)
  - `"PARTIAL"`: Equivalencia parcial
- `note` (CharField): Notas sobre la equivalencia

**Restricciones**:
- Una materia no puede ser equivalente a sí misma

**Casos de Uso**:
- Equivalencias entre planes de estudio
- Reválidas de materias de otras universidades
- Materias que se fusionaron o dividieron

**Ejemplo**:
```python
# "Cálculo 1 (plan 1997)" es equivalente a "Cálculo I (plan 2023)"
equiv = SubjectEquivalence.objects.create(
    subject_a=calculo1_plan1997,
    subject_b=calculoi_plan2023,
    kind="FULL",
    note="Equivalencia entre planes"
)
```

---

### 11. DependencyEdge (Arista de Dependencia)

**Propósito**: Materializa las relaciones de dependencia para consultas rápidas de alcanzabilidad.

**Campos**:
- `from_type` (CharField): Tipo de origen (`"SUBJECT"` o `"OFFERING"`)
- `from_subject` (ForeignKey → Subject): Materia origen (si `from_type="SUBJECT"`)
- `from_offering` (ForeignKey → Offering): Oferta origen (si `from_type="OFFERING"`)
- `to_offering` (ForeignKey → Offering): Oferta destino (que tiene esta dependencia)
- `group` (ForeignKey → RequirementGroup): Grupo de requisito del que proviene
- `kind` (CharField): Tipo de dependencia
  - `"REQUIRES_ALL"`: Requiere todos
  - `"ALTERNATIVE_ANY"`: Alternativa (cualquiera)
  - `"FORBIDDEN_NONE"`: Prohibido
- `condition` (CharField): Condición requerida

**Restricciones**:
- Exactamente uno de `from_subject` o `from_offering` debe estar establecido

**Propósito Especial**:
Este modelo es una **vista materializada** que:
- Se genera a partir de RequirementGroups y RequirementItems
- Permite consultas rápidas del tipo: "¿Qué materias necesito para X?"
- Facilita análisis de grafos de dependencias
- Útil para algoritmos de planificación académica

---

### 12. AuditSource (Fuente de Auditoría)

**Propósito**: Rastrea el scraping y auditoría de páginas fuente.

**Campos**:
- `offering` (ForeignKey → Offering): Oferta asociada
- `url` (URLField): URL de la página scrapeada
- `fetched_at` (DateTime): Cuándo se obtuvo
- `status` (IntegerField): Código HTTP
- `html_checksum` (CharField): Checksum del contenido
- `parsed_ok` (BooleanField): Si el parsing fue exitoso
- `raw_snapshot` (BinaryField): Snapshot del HTML

**Casos de Uso**:
- Auditoría de cambios en los requisitos
- Debugging de problemas de scraping
- Historial de modificaciones

---

## Ejemplos Prácticos

### Ejemplo 1: Requisito Simple

**Caso**: "Para cursar Cálculo 2, debes tener aprobado Cálculo 1"

**Modelado**:
```
Offering: Cálculo 2 - COURSE - 2025S1
└─ RequirementGroup (scope=ALL)
   └─ RequirementItem
      ├─ target_type: SUBJECT
      ├─ target_subject: Cálculo 1
      └─ condition: APPROVED
```

**Código Python**:
```python
# Paso 1: Crear el grupo ALL
grupo = RequirementGroup.objects.create(
    offering=calculo2_course,
    scope="ALL",
    flavor="GENERIC"
)

# Paso 2: Crear el item que apunta a Cálculo 1
RequirementItem.objects.create(
    group=grupo,
    target_type="SUBJECT",
    target_subject=calculo1,
    condition="APPROVED",
    alt_label="Cálculo 1"
)
```

---

### Ejemplo 2: Requisito Compuesto (Aprobar 2 de 3)

**Caso**: "Para cursar Álgebra Avanzada, debes aprobar 2 de: Álgebra 1, Geometría, o Álgebra Lineal"

**Modelado**:
```
Offering: Álgebra Avanzada - COURSE - 2025S1
└─ RequirementGroup (scope=ANY, min_required=2)
   ├─ RequirementItem → Álgebra 1 (APPROVED)
   ├─ RequirementItem → Geometría (APPROVED)
   └─ RequirementItem → Álgebra Lineal (APPROVED)
```

**Código Python**:
```python
grupo = RequirementGroup.objects.create(
    offering=algebra_avanzada,
    scope="ANY",
    flavor="APPROVALS",
    min_required=2  # Necesita 2 de 3
)

for materia in [algebra1, geometria, algebra_lineal]:
    RequirementItem.objects.create(
        group=grupo,
        target_type="SUBJECT",
        target_subject=materia,
        condition="APPROVED"
    )
```

---

### Ejemplo 3: Requisito con Prohibición (NONE)

**Caso**: "Para cursar Introducción a la Programación, NO debes tener aprobado Programación 2"

**Modelado**:
```
Offering: Intro Programación - COURSE - 2025S1
└─ RequirementGroup (scope=NONE)
   └─ RequirementItem → Programación 2 (APPROVED)
```

**Interpretación**: Si tienes aprobado Programación 2, NO puedes cursar Intro (porque sería redundante).

---

### Ejemplo 4: Requisito Complejo Anidado

**Caso**: "Para el Examen de Algoritmos debes cumplir TODO lo siguiente:
- Tener aprobado el Curso de Algoritmos
- Y (aprobar Matemática Discreta O aprobar Lógica)"

**Modelado**:
```
Offering: Algoritmos - EXAM - 2025S1
└─ RequirementGroup (scope=ALL, order=0)
   ├─ RequirementItem → Algoritmos COURSE (APPROVED)
   └─ RequirementGroupLink
      └─ RequirementGroup (scope=ANY, min_required=1, order=1)
         ├─ RequirementItem → Matemática Discreta (APPROVED)
         └─ RequirementItem → Lógica (APPROVED)
```

**Código Python**:
```python
# Grupo raíz: ALL
grupo_all = RequirementGroup.objects.create(
    offering=algoritmos_exam,
    scope="ALL",
    order_index=0
)

# Item: Curso de Algoritmos
RequirementItem.objects.create(
    group=grupo_all,
    target_type="OFFERING",
    target_offering=algoritmos_course,
    condition="APPROVED"
)

# Grupo hijo: ANY
grupo_any = RequirementGroup.objects.create(
    offering=algoritmos_exam,
    scope="ANY",
    min_required=1,
    order_index=1
)

# Enlazar hijo al padre
RequirementGroupLink.objects.create(
    parent_group=grupo_all,
    child_group=grupo_any,
    order_index=1
)

# Items del grupo ANY
for materia in [matematica_discreta, logica]:
    RequirementItem.objects.create(
        group=grupo_any,
        target_type="SUBJECT",
        target_subject=materia,
        condition="APPROVED"
    )
```

---

### Ejemplo 5: Posprevias (Lo Que Desbloqueas)

**Concepto de Posprevias**: Las "posprevias" son la relación inversa a las previaturas. Si Cálculo 1 es previa de Cálculo 2, entonces Cálculo 2 es "posprevia" de Cálculo 1.

**Caso**: "¿Qué materias puedo cursar si apruebo Cálculo 1?"

**Datos en `posprevias.json`**:
```json
{
  "1020": {
    "code": "1020",
    "name": "CALCULO 1",
    "posprevias": [
      {
        "materia_codigo": "1022",
        "materia_nombre": "CALCULO 2",
        "tipo": "Curso"
      },
      {
        "materia_codigo": "1022",
        "materia_nombre": "CALCULO 2",
        "tipo": "Examen"
      }
    ]
  }
}
```

**Modelado**: El comando `load_bedelia` crea automáticamente grupos de requisitos en las ofertas de destino (Cálculo 2) que apuntan a Cálculo 1.

**Consulta**:
```python
# ¿Qué materias se desbloquean si apruebo Cálculo 1?
calculo1 = Subject.objects.get(code="1020")

# Buscar todos los RequirementItems que apuntan a Cálculo 1
items = RequirementItem.objects.filter(
    target_type="SUBJECT",
    target_subject=calculo1,
    condition="APPROVED"
)

# Obtener las ofertas que tienen estos requisitos
ofertas_desbloqueadas = set()
for item in items:
    ofertas_desbloqueadas.add(item.group.offering)

# Resultado: Curso y Examen de Cálculo 2
```

---

## Flujo de Datos

### 1. Carga de Datos desde JSON

El sistema incluye un comando Django `load_bedelia` que importa datos desde tres archivos JSON:

#### Fase 1: credits.json → Program + Subject

**Estructura de `credits.json`**:
```json
[
  {
    "codigo": "DMA01",
    "nombre": "CÁLCULO DIFERENCIAL E INTEGRAL EN UNA VARIABLE",
    "creditos": "12"
  }
]
```

**Proceso**:
1. Se crea un `Program` por defecto (o se detectan programas en los datos)
2. Se crea un `Subject` por cada entrada con código, nombre y créditos

#### Fase 2: requirements.json → Offering + RequirementGroups

**Estructura de `requirements.json`**:
```json
{
  "1944 - ADMINISTRACION GENERAL PARA INGENIEROS": {
    "code": "1944",
    "name": "Examen",
    "requirements": {
      "type": "ALL",
      "children": [
        {
          "type": "LEAF",
          "rule": "min_approvals",
          "required_count": 1,
          "items": [
            {
              "code": "2241",
              "name": "ADMINISTRACION DE EMPRESAS",
              "kind": "examen"
            }
          ]
        }
      ]
    }
  }
}
```

**Proceso**:
1. Se extrae el código de la materia (`1944`)
2. Se determina el tipo de oferta (`Examen` → `EXAM`)
3. Se crea/obtiene la `Offering`
4. Se construye el árbol de `RequirementGroup` recursivamente:
   - Nodos `ALL`/`ANY`/`NONE` → `RequirementGroup`
   - Nodos `LEAF` → `RequirementItem`
   - Se crean `RequirementGroupLink` para conectar padres e hijos

#### Fase 3: posprevias.json → Requisitos Inversos

**Estructura de `posprevias.json`**:
```json
{
  "1944": {
    "code": "1944",
    "name": "ADMINISTRACION GENERAL PARA INGENIEROS",
    "posprevias": [
      {
        "materia_codigo": "1945",
        "materia_nombre": "PRACTICA DE ADMINISTRACION PARA INGENIEROS",
        "tipo": "Examen"
      }
    ]
  }
}
```

**Proceso**:
1. Para cada materia origen (ej: `1944`)
2. Para cada posprevia (ej: `1945`)
3. Se crea/obtiene la `Offering` de la materia destino (`1945`)
4. Se crea un `RequirementGroup` (scope=ANY) en esa oferta
5. Se agrega un `RequirementItem` que apunta a la materia origen (`1944`)

**Resultado**: Si apruebas `1944`, se desbloquea el examen de `1945`.

---

### 2. Consulta de Requisitos vía API

El sistema expone una API REST completa para consultar los datos:

#### Endpoints Principales:

```
GET /api/subjects/              # Listar materias
GET /api/subjects/{id}/         # Detalle de materia (con ofertas)
GET /api/offerings/             # Listar ofertas
GET /api/offerings/{id}/        # Detalle de oferta (con grupos de requisitos)
GET /api/offerings/{id}/requirement_tree/  # Árbol completo de requisitos
GET /api/requirement-groups/    # Listar grupos de requisitos
GET /api/requirement-items/     # Listar items de requisitos
```

#### Ejemplo: Obtener Requisitos de una Materia

```bash
# 1. Buscar la materia
curl "http://localhost:8000/api/subjects/?search=CALCULO"

# 2. Obtener una oferta específica
curl "http://localhost:8000/api/offerings/{offering_id}/"

# 3. Obtener el árbol completo de requisitos
curl "http://localhost:8000/api/offerings/{offering_id}/requirement_tree/"
```

**Respuesta del árbol**:
```json
[
  {
    "id": "uuid-grupo",
    "scope": "ALL",
    "flavor": "GENERIC",
    "min_required": null,
    "items": [
      {
        "target_type": "SUBJECT",
        "target_subject": {
          "code": "DMA01",
          "name": "CÁLCULO..."
        },
        "condition": "APPROVED"
      }
    ],
    "children": []
  }
]
```

---

### 3. Navegar el Árbol de Requisitos

#### Desde Python/Django:

```python
# Obtener una oferta
offering = Offering.objects.get(subject__code="CAL2", type="COURSE")

# Obtener grupos raíz (sin padres)
root_groups = RequirementGroup.objects.filter(
    offering=offering
).exclude(
    id__in=RequirementGroupLink.objects.values_list('child_group_id', flat=True)
)

# Para cada grupo raíz, recorrer recursivamente
def print_tree(group, indent=0):
    print("  " * indent + f"[{group.scope}]")
    
    # Imprimir items
    for item in group.items.all():
        if item.target_subject:
            print("  " * (indent+1) + f"→ {item.target_subject.code}")
    
    # Recorrer hijos
    for link in group.child_links.all():
        print_tree(link.child_group, indent+1)

for group in root_groups:
    print_tree(group)
```

**Salida**:
```
[ALL]
  → DMA01
  [ANY]
    → GAL1
    → AL
```

---

## Glosario

### Términos Académicos

- **Programa**: Plan de estudios o carrera académica
- **Materia**: Curso o asignatura canónica
- **Oferta**: Instancia específica de una materia en un período
- **Requisito (Previa)**: Condición que debe cumplirse antes de cursar algo
- **Posprevia**: Lo que se desbloquea al cumplir un requisito
- **Crédito**: Unidad de medida de carga académica
- **Equivalencia**: Relación de sustitución entre materias
- **Reválida**: Reconocimiento de materias cursadas en otra institución

### Términos del Sistema

- **Scope (Alcance)**: Lógica de un grupo (ALL/ANY/NONE)
- **Flavor (Tipo)**: Categoría semántica de un grupo
- **min_required**: Mínimo necesario en grupos ANY
- **target_type**: Si un item apunta a materia o oferta
- **condition**: Estado requerido (APPROVED/ENROLLED/CREDITED)
- **Árbol de requisitos**: Estructura jerárquica de condiciones
- **Dependency Edge**: Arista materializada para consultas rápidas

### Tipos de Ofertas

- **COURSE**: Curso regular con clases
- **EXAM**: Examen de la materia

### Estados de Requisitos

- **APPROVED**: Aprobado (con nota suficiente)
- **ENROLLED**: Inscrito/Cursando
- **CREDITED**: Acreditado (por equivalencia/reválida)

---

## Casos de Uso Avanzados

### 1. Consultar Trayectoria Académica

```python
# ¿Qué materias puedo cursar si tengo aprobadas X, Y, Z?
materias_aprobadas = Subject.objects.filter(code__in=["DMA01", "GAL1"])

# Buscar ofertas cuyos requisitos están satisfechos
# (Implementación simplificada)
ofertas_disponibles = []
for offering in Offering.objects.filter(is_active=True):
    # Evaluar árbol de requisitos...
    if evaluar_requisitos(offering, materias_aprobadas):
        ofertas_disponibles.append(offering)
```

### 2. Generar Grafo de Dependencias

```python
# Crear un grafo dirigido de todas las dependencias
import networkx as nx

G = nx.DiGraph()

for item in RequirementItem.objects.filter(target_type="SUBJECT"):
    materia_requerida = item.target_subject.code
    materia_destino = item.group.offering.subject.code
    G.add_edge(materia_requerida, materia_destino)

# Análisis
print(f"Materias: {G.number_of_nodes()}")
print(f"Dependencias: {G.number_of_edges()}")

# Camino más corto
camino = nx.shortest_path(G, "DMA01", "TESIS")
print(f"Camino: {' → '.join(camino)}")
```

### 3. Detectar Ciclos en Requisitos

```python
import networkx as nx

# Detectar ciclos
try:
    ciclos = list(nx.find_cycle(G))
    print(f"¡Ciclo detectado!: {ciclos}")
except nx.NetworkXNoCycle:
    print("No hay ciclos (correcto)")
```

---

## Comandos Útiles

### Cargar Datos

```bash
cd bedelia
python manage.py load_bedelia \
    --credits ../data/credits.json \
    --requirements ../data/requirements.json \
    --posprevias ../data/posprevias.json \
    --default-term 2025S1
```

### Consultas desde Django Shell

```bash
python manage.py shell
```

```python
from api.models import *

# Contar registros
print(f"Programas: {Program.objects.count()}")
print(f"Materias: {Subject.objects.count()}")
print(f"Ofertas: {Offering.objects.count()}")
print(f"Grupos: {RequirementGroup.objects.count()}")
print(f"Items: {RequirementItem.objects.count()}")

# Buscar materias
calculo = Subject.objects.filter(name__icontains="CALCULO")
for m in calculo:
    print(f"{m.code}: {m.name} ({m.credits} créditos)")

# Ver requisitos de una oferta
offering = Offering.objects.first()
for group in offering.requirement_groups.all():
    print(f"Grupo {group.scope}:")
    for item in group.items.all():
        print(f"  - {item.alt_label}")
```

---

## Referencias

- **Código fuente de modelos**: `bedelia/api/models.py`
- **Comando de importación**: `bedelia/api/management/commands/load_bedelia.py`
- **API**: `bedelia/api/views/bedelia.py` y `bedelia/api/serializers/bedelia.py`
- **Datos JSON**: `data/credits.json`, `data/requirements.json`, `data/posprevias.json`

---

## Contribuir

Si encuentras errores o quieres mejorar esta documentación:

1. Lee el código fuente en `bedelia/api/models.py`
2. Prueba consultas en Django shell
3. Usa la API REST para verificar comportamientos
4. Revisa los tests (si existen)

---

## Licencia y Contacto

Este sistema fue desarrollado para gestionar la información académica de forma estructurada y consultas eficientes. Para más información, consulta el README principal del proyecto.

---

**Última actualización**: Octubre 2025

