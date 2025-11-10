# 🔄 Actualización del Modelo Curso

## 📝 Cambio Realizado

Se agregó el campo `tipo_evaluacion` al modelo `Curso` para manejar que un mismo código de curso puede tener:
- **Curso**: El curso regular
- **Examen**: El examen del curso

### Antes
```python
unique_together = ['codigo_universidad', 'codigo_curso']
```

### Ahora
```python
tipo_evaluacion = models.CharField(
    max_length=10, 
    choices=[('Curso', 'Curso'), ('Examen', 'Examen'), ('', 'No especificado')],
    default='',
    blank=True
)

unique_together = ['codigo_curso', 'tipo_evaluacion']
```

---

## ⚠️ IMPORTANTE: Migración Requerida

### 1️⃣ Eliminar la Migración Anterior (si existe)

Si ya aplicaste las migraciones anteriores, necesitas:

```bash
# Revertir la última migración
python manage.py migrate api zero

# O si tienes datos, hacer un dump primero
python manage.py dumpdata api > backup_data.json
```

### 2️⃣ Eliminar el Archivo de Migración Anterior

```bash
# Windows PowerShell
Remove-Item bedelia\api\migrations\0001_initial.py

# O manualmente borrar:
bedelia/api/migrations/0001_initial.py
```

### 3️⃣ Crear Nueva Migración

```bash
cd bedelia
python manage.py makemigrations
```

**Salida esperada:**
```
Migrations for 'api':
  api/migrations/0001_initial.py
    - Create model Carrera
    - Create model Curso (con tipo_evaluacion)
    - Create model Previa
    - Create model ItemPrevia
    - Create model Posprevia
```

### 4️⃣ Aplicar Migración

```bash
python manage.py migrate
```

**Salida esperada:**
```
Running migrations:
  Applying api.0001_initial... OK
```

---

## 🧪 Verificar el Cambio

```bash
python manage.py shell
```

```python
from api.models import Curso

# Crear curso con tipo Examen
curso_examen = Curso.objects.create(
    codigo_curso='1144',
    nombre_curso='VIBRACIONES Y ONDAS',
    tipo_evaluacion='Examen',
    creditos=10,
    activo=True
)

# Crear curso con tipo Curso
curso_regular = Curso.objects.create(
    codigo_curso='1144',
    nombre_curso='VIBRACIONES Y ONDAS',
    tipo_evaluacion='Curso',
    creditos=10,
    activo=True
)

# Verificar que ambos existen
print(f"Cursos con código 1144: {Curso.objects.filter(codigo_curso='1144').count()}")
# Debe mostrar: 2

# Buscar por tipo
examen = Curso.objects.get(codigo_curso='1144', tipo_evaluacion='Examen')
print(f"Examen: {examen}")

curso = Curso.objects.get(codigo_curso='1144', tipo_evaluacion='Curso')
print(f"Curso: {curso}")
```

---

## 📊 Cambios en el Comando load_bedelia_data

El comando ahora:

1. **Crea cursos sin tipo** desde `credits` (tipo_evaluacion='')
2. **Crea cursos con tipo** desde `previas` (Examen o Curso)
3. **Crea cursos con tipo** desde `posprevias` (Examen o Curso)

### Ejemplo de Datos Resultantes

```
Curso: 1144 - VIBRACIONES Y ONDAS (tipo='')
Curso: 1144 - VIBRACIONES Y ONDAS - Examen (tipo='Examen')
Curso: 1144 - VIBRACIONES Y ONDAS - Curso (tipo='Curso')
```

Todos pueden coexistir porque `unique_together = ['codigo_curso', 'tipo_evaluacion']`

---

## 🚀 Cargar Datos

Después de aplicar las migraciones:

```bash
python manage.py load_bedelia_data --clear --verbose
```

**Esperado:**
- ✅ Sin error `MultipleObjectsReturned`
- ✅ Cursos con diferentes tipos pueden coexistir
- ✅ Previas y posprevias funcionan correctamente

---

## 🔍 Consultas Útiles

### Ver cursos con múltiples tipos

```python
from django.db.models import Count
from api.models import Curso

# Códigos de curso que tienen múltiples tipos
cursos_duplicados = Curso.objects.values('codigo_curso').annotate(
    count=Count('id')
).filter(count__gt=1)

for item in cursos_duplicados[:10]:
    codigo = item['codigo_curso']
    cursos = Curso.objects.filter(codigo_curso=codigo)
    print(f"\n{codigo}:")
    for curso in cursos:
        print(f"  - {curso.tipo_evaluacion or '(sin tipo)'}: {curso.nombre_curso}")
```

### Ver todos los exámenes

```python
examenes = Curso.objects.filter(tipo_evaluacion='Examen')
print(f"Total exámenes: {examenes.count()}")
for examen in examenes[:10]:
    print(f"  {examen.codigo_curso} - {examen.nombre_curso}")
```

### Ver todos los cursos regulares

```python
cursos_regulares = Curso.objects.filter(tipo_evaluacion='Curso')
print(f"Total cursos regulares: {cursos_regulares.count()}")
```

---

## 📝 Resumen de Cambios

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Unicidad** | `codigo_universidad + codigo_curso` | `codigo_curso + tipo_evaluacion` |
| **Tipos permitidos** | N/A | Curso, Examen, '' |
| **Cursos con mismo código** | No permitido | ✅ Permitido (con diferentes tipos) |
| **Error MultipleObjectsReturned** | ❌ Ocurría | ✅ Resuelto |

---

## ✅ Checklist

- [ ] Revertir migraciones anteriores (si existen)
- [ ] Eliminar archivo 0001_initial.py anterior
- [ ] Ejecutar `makemigrations`
- [ ] Aplicar `migrate`
- [ ] Verificar en shell que funciona
- [ ] Ejecutar `load_bedelia_data --clear`
- [ ] Verificar que no hay error MultipleObjectsReturned

---

## 🆘 Problemas Comunes

### Error: "duplicate key value violates unique constraint"

**Causa:** Ya existen cursos duplicados en la BD

**Solución:**
```bash
python manage.py migrate api zero
python manage.py migrate
python manage.py load_bedelia_data --clear
```

### Error: "column tipo_evaluacion does not exist"

**Causa:** Migración no aplicada

**Solución:**
```bash
python manage.py migrate
```

---

**¡Listo para usar!** 🎉

