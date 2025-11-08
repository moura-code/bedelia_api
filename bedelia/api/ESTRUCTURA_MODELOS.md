# Estructura de Modelos - Bedelia API

## 📋 Resumen de Modelos

Los modelos de Django creados representan la estructura de cursos, requisitos (previas) y materias dependientes (posprevias) de la universidad.

### Modelos Principales:

1. **Carrera**: Carreras universitarias con sus planes de estudio
2. **Curso**: Cursos/materias vigentes 
3. **Previa**: Estructura de árbol para representar requisitos
4. **ItemPrevia**: Items individuales dentro de un nodo LEAF
5. **Posprevia**: Materias que dependen de un curso

---

## 🌳 Estructura de Árbol de Previas

### Concepto

Las **previas** de un curso forman un **árbol jerárquico** donde cada nodo puede ser:

- **ALL**: Debe cumplir TODOS los hijos
- **ANY**: Debe cumplir AL MENOS UNO de los hijos  
- **NOT**: NO debe tener NINGUNO de los hijos
- **LEAF**: Nodo hoja que contiene items individuales (ItemPrevia)

### Ejemplo Visual

```
Curso: "1144 - VIBRACIONES Y ONDAS" (Examen)
│
└─── [ALL] debe tener todas
     ├─── [NOT] no debe tener
     │    └─── [LEAF] 1 aprobación/es entre:
     │         ├── Item: FI15 - CREDITOS ASIGNADOS POR REVALIDA (exam)
     │         ├── Item: 1144P - CREDITOS NO ACUM VIBRACIONES Y ONDAS (exam)
     │         └── Item: 1126 - MEC.DE SIST.Y FENOMENOS ONDULATORIOS (exam)
     │
     ├─── [LEAF] 1 aprobación/es entre:
     │    ├── Item: FI15 - CREDITOS ASIGNADOS POR REVALIDA (exam)
     │    ├── Item: 1144P - CREDITOS NO ACUM VIBRACIONES Y ONDAS (exam)
     │    └── Item: 1126 - MEC.DE SIST.Y FENOMENOS ONDULATORIOS (exam)
     │
     └─── [ANY] debe tener alguna
          └─── [ALL] debe tener todas
               └─── [ANY] debe tener alguna
                    ├─── [LEAF] 1 aprobación/es entre:
                    │    ├── Item: 1153P - CREDITOS NO ACUM FISICA 3 (exam)
                    │    ├── Item: 1121 - FISICA GENERAL 2 (exam)
                    │    ├── Item: 1172 - FISICA GENERAL 2 (exam)
                    │    └── Item: 1153 - FISICA 3 (exam)
                    │
                    └─── [LEAF] 2 aprobación/es entre:
                         ├── Item: 1152P - CREDITOS NO ACUM FISICA 2 (exam)
                         ├── Item: 1152 - FISICA 2 (exam)
                         └── Item: 1153 - FISICA 3 (course)
```

### Explicación del Ejemplo

Para poder rendir el **Examen de "1144 - VIBRACIONES Y ONDAS"**, un estudiante debe cumplir:

1. **[ALL]** - Debe cumplir TODAS estas condiciones:
   
   a. **[NOT]** - NO debe tener aprobada ninguna de estas:
      - FI15, 1144P, o 1126
   
   b. **[LEAF]** - Debe tener 1 aprobación entre:
      - FI15, 1144P, o 1126
   
   c. **[ANY]** - Debe cumplir AL MENOS UNA de estas opciones:
      - Opción que a su vez requiere cumplir todo un sub-árbol de requisitos

---

## 🗃️ Estructura de Base de Datos

### Tabla: `carreras`

```
id (UUID)
nombre (varchar)
anio_plan (varchar)
fecha_creacion (datetime)
fecha_modificacion (datetime)
```

### Tabla: `cursos`

```
id (UUID)
codigo_universidad (varchar) - FING, CENURLN, CURE, etc.
codigo_curso (varchar) - 1144, 1267, etc.
nombre_curso (varchar)
creditos (int)
activo (boolean)
fecha_creacion (datetime)
fecha_modificacion (datetime)

Relación ManyToMany con Carrera
```

### Tabla: `previas`

```
id (UUID)
curso_id (FK a Curso) - El curso al que pertenece esta previa
codigo (varchar)
nombre (varchar)
tipo (varchar) - ALL, ANY, NOT, LEAF
titulo (varchar) - Ej: "debe tener todas", "1 aprobación/es entre:"
cantidad_requerida (int)
padre_id (FK a self) - Para construir el árbol
orden (int)
carrera_id (FK a Carrera)
fecha_creacion (datetime)
fecha_modificacion (datetime)
```

**Clave importante**: 
- `padre_id = NULL` → Nodo raíz del árbol
- `tipo = LEAF` → Este nodo tiene ItemPrevias
- `tipo = ALL/ANY/NOT` → Este nodo tiene otros nodos Previa como hijos

### Tabla: `items_previa`

```
id (UUID)
previa_id (FK a Previa) - Solo a nodos tipo LEAF
fuente (varchar) - UCB, EXAMEN, CREDITOS, OTRO
modalidad (varchar) - exam, course, ucb_module, credits, other
codigo (varchar)
titulo (varchar)
notas (JSON)
texto_raw (text)
orden (int)
fecha_creacion (datetime)
fecha_modificacion (datetime)
```

### Tabla: `posprevias`

```
id (UUID)
curso_id (FK a Curso)
codigo (varchar)
nombre (varchar)
anio_plan (varchar)
carrera (varchar)
fecha (varchar)
descripcion (text)
tipo (varchar) - Curso, Examen
materia_codigo (varchar)
materia_nombre (varchar)
materia_full (varchar)
fecha_creacion (datetime)
fecha_modificacion (datetime)
```

---

## 🔗 Relaciones entre Modelos

```
Carrera (1) ←→ (N) Curso
Curso (1) ←→ (N) Previa
Previa (1) ←→ (N) Previa (auto-relación padre-hijo)
Previa (1) ←→ (N) ItemPrevia (solo cuando Previa.tipo = LEAF)
Curso (1) ←→ (N) Posprevia
```

---

## 💡 Métodos Útiles en el Modelo Previa

### `es_raiz()`
Retorna `True` si el nodo es la raíz del árbol (no tiene padre).

```python
previa_raiz = Previa.objects.get(curso=mi_curso, padre=None)
if previa_raiz.es_raiz():
    print("Este es el nodo raíz")
```

### `obtener_hijos()`
Retorna todos los nodos hijos ordenados.

```python
hijos = previa_nodo.obtener_hijos()
for hijo in hijos:
    print(f"Hijo: {hijo.tipo} - {hijo.titulo}")
```

---

## 📊 Consultas Comunes

### Obtener el árbol completo de previas de un curso

```python
# Obtener nodo raíz
raiz = Previa.objects.filter(curso=curso, padre=None).first()

# Recorrer el árbol recursivamente
def recorrer_arbol(nodo, nivel=0):
    indent = "  " * nivel
    print(f"{indent}[{nodo.tipo}] {nodo.titulo}")
    
    if nodo.tipo == 'LEAF':
        for item in nodo.items.all():
            print(f"{indent}  - {item.codigo}: {item.titulo}")
    else:
        for hijo in nodo.obtener_hijos():
            recorrer_arbol(hijo, nivel + 1)

recorrer_arbol(raiz)
```

### Obtener todos los cursos de una carrera

```python
from bedelia.api.models import Carrera, Curso

carrera = Carrera.objects.get(nombre="INGENIERÍA CIVIL", anio_plan="2021")
cursos = carrera.cursos.filter(activo=True)
```

### Obtener las posprevias de un curso

```python
curso = Curso.objects.get(codigo_curso="1144")
posprevias = curso.posprevias.all()
for posprevia in posprevias:
    print(f"{posprevia.materia_codigo} - {posprevia.materia_nombre}")
```

---

## 🚀 Próximos Pasos

1. Crear migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

2. Registrar modelos en el admin (opcional):
```python
# bedelia/api/admin.py
from django.contrib import admin
from .models import Carrera, Curso, Previa, ItemPrevia, Posprevia

admin.site.register(Carrera)
admin.site.register(Curso)
admin.site.register(Previa)
admin.site.register(ItemPrevia)
admin.site.register(Posprevia)
```

3. Crear serializers para la API REST
4. Implementar vistas y endpoints
5. Cargar datos desde los archivos JSON de la carpeta `data/`

---

## 📝 Notas Importantes

- **UUIDs**: Todos los modelos usan UUIDs como clave primaria para mejor escalabilidad
- **Timestamps**: Todos los modelos tienen `fecha_creacion` y `fecha_modificacion` automáticos
- **Índices**: Se han creado índices en campos frecuentemente consultados
- **Soft Delete**: El campo `activo` en `Curso` permite hacer "soft deletes"
- **Árbol recursivo**: La estructura de `Previa` permite árboles de cualquier profundidad

