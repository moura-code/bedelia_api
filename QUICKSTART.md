# ⚡ Quick Start - Bedelia API

Guía rápida para poner en marcha los modelos y cargar datos en menos de 5 minutos.

## 🚀 Inicio Rápido (3 comandos)

```bash
# 1. Crear y aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# 2. Verificar con dry-run (opcional pero recomendado)
python manage.py load_bedelia_data --dry-run

# 3. Cargar datos
python manage.py load_bedelia_data --clear --verbose
```

¡Listo! 🎉

---

## 📋 Lo que acabas de crear

```
Estructura de Base de Datos:
├── carreras          (45 registros aprox)
├── cursos            (1,200+ registros)
├── previas           (5,000+ nodos de árbol)
├── items_previa      (10,000+ items)
└── posprevias        (8,000+ relaciones)
```

---

## 🧪 Verificar que funciona

```bash
python manage.py shell
```

```python
from api.models import Carrera, Curso, Previa

# Ver totales
print(f"Carreras: {Carrera.objects.count()}")
print(f"Cursos: {Curso.objects.count()}")
print(f"Previas: {Previa.objects.count()}")

# Ver ejemplo
curso = Curso.objects.first()
print(f"\nEjemplo: {curso}")
print(f"Créditos: {curso.creditos}")
print(f"Carreras: {curso.carrera.count()}")
```

**Salida esperada:**
```
Carreras: 45
Cursos: 1234
Previas: 5678

Ejemplo: 1267 - TALLER REPR. Y COM. GRAFICA
Créditos: 5
Carreras: 2
```

---

## 📚 Consultas Útiles

### Ver todas las carreras
```python
from api.models import Carrera
for c in Carrera.objects.all()[:10]:
    print(f"- {c.nombre} ({c.anio_plan})")
```

### Buscar un curso
```python
from api.models import Curso
curso = Curso.objects.filter(codigo_curso="1144").first()
print(curso.nombre_curso)
print(f"Créditos: {curso.creditos}")
```

### Ver árbol de previas
```python
curso = Curso.objects.get(codigo_curso="1144")
previas_raiz = curso.previas.filter(padre__isnull=True)
for previa in previas_raiz:
    print(f"Tipo: {previa.tipo}")
    print(f"Título: {previa.titulo}")
```

### Ver posprevias (qué materias requieren este curso)
```python
curso = Curso.objects.get(codigo_curso="1061")
posprevias = curso.posprevias.all()[:5]
for p in posprevias:
    print(f"- {p.materia_nombre}")
```

---

## 🎯 Datos Clave

### Estructura de Archivos JSON

- ✅ **vigentes**: TODOS los cursos activos
- ✅ **credits**: Créditos de los cursos  
- ⚠️ **previas**: Solo cursos CON requisitos (NO todos)
- ✅ **posprevias**: Dependencias inversas

### Es Normal

✅ Que haya cursos sin previas  
✅ Que el proceso tome 3-5 minutos  
✅ Ver advertencias sobre cursos no encontrados  

### NO es Normal

❌ Que todos los cursos tengan previas  
❌ Errores de base de datos  
❌ Que falten archivos JSON  

---

## 🔄 Actualizar Datos

```bash
# Borrar todo y recargar
python manage.py load_bedelia_data --clear

# Actualización incremental (solo nuevos/modificados)
python manage.py load_bedelia_data
```

---

## 🐛 Problemas Comunes

### "Archivo no encontrado"
```bash
# Verificar que los archivos existan
ls data/*.json
```

### "Out of memory"
- Usar PostgreSQL en lugar de SQLite
- Aumentar memoria disponible
- Cerrar otras aplicaciones

### "Integrity error"
```bash
# Limpiar y reintentar
python manage.py load_bedelia_data --clear
```

---

## 📖 Más Información

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Guía completa paso a paso
- [CHANGELOG_MODELS.md](CHANGELOG_MODELS.md) - Detalles de implementación
- [bedelia/api/ESTRUCTURA_MODELOS.md](bedelia/api/ESTRUCTURA_MODELOS.md) - Documentación de modelos
- [bedelia/api/management/commands/README_load_bedelia_data.md](bedelia/api/management/commands/README_load_bedelia_data.md) - Documentación del comando

---

## 🆘 Ayuda Rápida

```bash
# Ver ayuda del comando
python manage.py load_bedelia_data --help

# Probar sin guardar
python manage.py load_bedelia_data --dry-run --verbose

# Ver qué se cargó
python manage.py shell < bedelia/api/management/commands/verify_data.py
```

---

**¡Ya estás listo para usar la API! 🚀**

Siguiente paso: Crear serializers y endpoints REST → Ver [TODO.md](TODO.md)

