<!-- 27b64259-6e77-47f2-8c4c-c75f62bf182b 98289065-e01d-4c93-ba5f-059593ef2107 -->
# Plan: Translate Swagger Documentation to Spanish

## Scope

- ✅ Full Swagger UI translation (SPECTACULAR_SETTINGS, view docstrings, parameter descriptions)
- ✅ Keep model code in English (only public-facing API docs)
- ✅ Leave admin interface in English

## Files to Modify

### 1. `bedelia/config/settings.py`

Translate SPECTACULAR_SETTINGS (lines 219-275):

- `TITLE`: "API de Bedelia"
- `DESCRIPTION`: Full Spanish description of the API, explaining:
- Carreras → Programas de grado académico
- Materias → Cursos/asignaturas
- Planes de Estudio → Planes de estudio
- Unidades Aprobables → Unidades aprobables
- Requisitos → Árbol de requisitos previos
- `TAGS`: Translate all 8 tag names and descriptions
- `SERVERS`: Description to Spanish

### 2. `bedelia/api/views/materias.py`

Translate all API documentation (lines 63-767):

- **MateriaViewSet**: Summary, description, parameters (código, activo, search)
- **PlanEstudioViewSet**: Summary, description, parameters (nombre_carrera, anio, activo)
- **PlanMateriaViewSet**: Summary, description, parameters
- **UnidadAprobableViewSet**: Summary, description, parameters (materia, tipo, activo)
- **RequisitoNodoViewSet**: Summary, description, parameters (plan_materia, tipo, padre, root_only, tree)
- **RequisitoItemViewSet**: Summary, description, parameters (nodo, tipo, activo)
- **PreviasViewSet**: Complex description with required/optional parameters
- **PosPreviasViewSet**: Complex description with required/optional parameters

### 3. `bedelia/api/serializers/materias.py`

Translate serializer docstrings (lines 17-249):

- All class docstrings for serializers
- Method docstrings (get_unidades, get_planes_count, etc.)

## Translation Strategy

- Use standard Spanish terminology for university/academic contexts
- Maintain technical accuracy
- Keep parameter names in code unchanged (only translate descriptions)
- Preserve all technical details and examples

### To-dos

- [ ] Translate SPECTACULAR_SETTINGS in settings.py
- [ ] Translate all viewset documentation in views/materias.py
- [ ] Translate serializer docstrings in serializers/materias.py