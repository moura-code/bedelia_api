# 📝 Changelog - Modelos y Comando de Carga

## ✨ Resumen

Se han creado modelos de Django para representar la estructura completa de cursos, requisitos y dependencias de Bedelia, junto con un comando para cargar los datos desde archivos JSON.

---

## 🗃️ Modelos Creados

### 1. `Carrera`
Representa las carreras universitarias.

**Campos principales:**
- `nombre`: Nombre de la carrera (ej: "INGENIERÍA CIVIL")
- `anio_plan`: Año del plan de estudios (ej: "2021")

**Relaciones:**
- One-to-Many con `Curso`
- One-to-Many con `Previa`

---

### 2. `Curso`
Representa cursos/materias vigentes.

**Campos principales:**
- `codigo_universidad`: Código de la facultad (FING, CENURLN, etc.)
- `codigo_curso`: Código único del curso
- `nombre_curso`: Nombre descriptivo
- `creditos`: Cantidad de créditos
- `activo`: Estado del curso (para soft deletes)

**Relaciones:**
- **ManyToMany** con `Carrera` (un curso puede pertenecer a múltiples carreras)
- One-to-Many con `Previa`
- One-to-Many con `Posprevia`

---

### 3. `Previa`
Estructura de **árbol jerárquico** para requisitos.

**Tipos de nodos:**
- `ALL`: Debe cumplir TODOS los hijos
- `ANY`: Debe cumplir AL MENOS UNO de los hijos
- `NOT`: NO debe tener NINGUNO de los hijos
- `LEAF`: Nodo hoja con items individuales

**Campos principales:**
- `curso`: Curso al que pertenece (solo raíz)
- `tipo`: Tipo de nodo (ALL/ANY/NOT/LEAF)
- `titulo`: Descripción (ej: "debe tener todas")
- `cantidad_requerida`: Para requisitos tipo "N de X"
- `padre`: Auto-relación para construir el árbol
- `orden`: Orden de los hermanos

**Métodos:**
- `es_raiz()`: Verifica si es nodo raíz
- `obtener_hijos()`: Retorna hijos ordenados

---

### 4. `ItemPrevia`
Items individuales en nodos LEAF.

**Campos principales:**
- `previa`: Nodo LEAF al que pertenece
- `fuente`: UCB, EXAMEN, CREDITOS
- `modalidad`: exam, course, ucb_module, credits
- `codigo`: Código del requisito
- `titulo`: Nombre del requisito
- `notas`: Array JSON
- `texto_raw`: Texto original

---

### 5. `Posprevia`
Relaciones inversas (materias que requieren un curso).

**Campos principales:**
- `curso`: Curso que es requisito
- `materia_codigo`: Materia que lo requiere
- `materia_nombre`: Nombre de la materia
- `tipo`: Curso o Examen
- `carrera`, `anio_plan`: Contexto

---

## 🚀 Comando `load_bedelia_data`

### Descripción
Comando de Django para cargar datos desde archivos JSON.

**Ubicación:** `bedelia/api/management/commands/load_bedelia_data.py`

### Uso Básico

```bash
# Dry run (no guarda)
python manage.py load_bedelia_data --dry-run

# Cargar datos
python manage.py load_bedelia_data

# Limpiar y cargar
python manage.py load_bedelia_data --clear --verbose
```

### Archivos Procesados

1. **vigentes_data_backup.json** → Cursos (TODOS los activos)
2. **credits_data_backup.json** → Créditos
3. **previas_data_backup.json** → Requisitos (solo algunos cursos)
4. **posprevias_data_backup.json** → Dependencias inversas

### Características

✅ **Transaccional**: Todo o nada (rollback en errores)  
✅ **Dry-run**: Probar sin guardar  
✅ **Verbose**: Salida detallada  
✅ **Estadísticas**: Resumen completo  
✅ **Manejo de errores**: Continúa ante errores parciales  
✅ **Caché interno**: Optimización de búsquedas  

### Proceso de Carga

1. **Verificación** de archivos JSON
2. **Limpieza** opcional de la base de datos
3. **Carga de carreras y cursos** (con créditos)
4. **Construcción del árbol de previas** (recursivo)
5. **Carga de posprevias**
6. **Estadísticas finales**

---

## 📊 Estructura de Datos

### Relación entre Archivos

```
vigentes.json → TODOS los cursos activos
    ↓
credits.json → Créditos (puede tener más cursos)
    ↓
previas.json → Solo cursos CON requisitos (subset de vigentes)
    ↓
posprevias.json → Dependencias inversas
```

### Importante

- ⚠️ **NO todos los cursos tienen previas** (es normal)
- ✅ Todos los cursos activos están en `vigentes`
- ✅ Los créditos pueden tener cursos no en vigentes
- ✅ Un curso puede pertenecer a múltiples carreras

---

## 📁 Archivos Creados

### Código
```
bedelia/api/models.py                           # Modelos principales
bedelia/api/management/commands/
    load_bedelia_data.py                        # Comando de carga
    verify_data.py                              # Script de verificación
    test_load.sh                                # Script de pruebas
```

### Documentación
```
bedelia/api/ESTRUCTURA_MODELOS.md               # Guía de modelos
bedelia/api/management/commands/
    README_load_bedelia_data.md                 # Guía del comando
SETUP_GUIDE.md                                  # Guía de configuración
CHANGELOG_MODELS.md                             # Este archivo
```

---

## 🔧 Migraciones

### Crear migraciones
```bash
python manage.py makemigrations
```

### Aplicar migraciones
```bash
python manage.py migrate
```

---

## 🧪 Testing

### Test básico
```bash
bash bedelia/api/management/commands/test_load.sh
```

### Verificación de datos
```bash
python manage.py shell < bedelia/api/management/commands/verify_data.py
```

### En Django shell
```python
from api.models import Carrera, Curso, Previa

# Ver estadísticas
print(f"Carreras: {Carrera.objects.count()}")
print(f"Cursos: {Curso.objects.count()}")
print(f"Previas: {Previa.objects.count()}")

# Ejemplo de árbol de previas
curso = Curso.objects.filter(previas__isnull=False).first()
raiz = curso.previas.filter(padre__isnull=True).first()
print(f"\nÁrbol de previas para {curso}:")
print(f"Raíz: {raiz.tipo} - {raiz.titulo}")
for hijo in raiz.obtener_hijos():
    print(f"  - {hijo.tipo}: {hijo.titulo}")
```

---

## 🎯 Próximos Pasos Sugeridos

1. ✅ **Modelos creados**
2. ✅ **Comando de carga implementado**
3. ⏳ **Serializers** para API REST
4. ⏳ **Views y endpoints**
5. ⏳ **Admin de Django** configurado
6. ⏳ **Tests unitarios**
7. ⏳ **API documentation** (Swagger/OpenAPI)

---

## 📝 Notas de Implementación

### Decisiones de Diseño

1. **UUIDs**: Usados como PK para mejor escalabilidad y distribución
2. **Árbol recursivo**: `Previa.padre` permite estructuras jerárquicas de cualquier profundidad
3. **ManyToMany Carrera-Curso**: Un curso puede estar en múltiples carreras
4. **Soft deletes**: Campo `activo` en `Curso` en lugar de borrado físico
5. **JSON field**: `ItemPrevia.notas` usa JSONField para flexibilidad
6. **Timestamps**: Todos los modelos tienen `fecha_creacion` y `fecha_modificacion`

### Optimizaciones

- **Índices**: Agregados en campos frecuentemente consultados
- **select_related/prefetch_related**: Sugeridos en queries complejas
- **Caché**: Implementado en el comando de carga
- **Transacciones**: Todo el proceso de carga es transaccional

### Manejo de Errores

- **Advertencias**: Para datos inconsistentes (no detienen el proceso)
- **Errores**: Para problemas críticos (hacen rollback)
- **Dry-run**: Para validar antes de cargar

---

## 📚 Referencias

- **Django Models**: https://docs.djangoproject.com/en/stable/topics/db/models/
- **Management Commands**: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
- **Tree Structures**: https://django-mptt.readthedocs.io/ (para optimización futura)

---

## ✅ Validación

### Checklist de Implementación

- [x] Modelo `Carrera` creado
- [x] Modelo `Curso` creado
- [x] Modelo `Previa` con estructura de árbol
- [x] Modelo `ItemPrevia` creado
- [x] Modelo `Posprevia` creado
- [x] Comando `load_bedelia_data` implementado
- [x] Manejo de archivos JSON
- [x] Construcción recursiva de árboles
- [x] Transaccionalidad
- [x] Dry-run mode
- [x] Verbose mode
- [x] Estadísticas
- [x] Documentación completa
- [x] Scripts de verificación
- [x] Sin errores de linting

---

**Versión:** 1.0  
**Fecha:** 2025-11-08  
**Estado:** ✅ Completo y funcional

