# 🚀 Guía de Configuración - Bedelia API

Esta guía te ayudará a configurar y cargar los datos de Bedelia en la base de datos.

## 📋 Pre-requisitos

- Python 3.8+
- Django instalado
- Base de datos configurada (PostgreSQL, MySQL, o SQLite)
- Archivos JSON en la carpeta `data/`

## 🗂️ Estructura de Archivos

```
bedelia_api/
├── data/
│   ├── vigentes_data_backup.json      # Cursos vigentes (TODOS)
│   ├── credits_data_backup.json       # Créditos de cursos
│   ├── previas_data_backup.json       # Requisitos (solo algunos cursos)
│   └── posprevias_data_backup.json    # Dependencias inversas
├── bedelia/
│   ├── api/
│   │   ├── models.py                  # Modelos: Carrera, Curso, Previa, etc.
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── load_bedelia_data.py        # Comando principal
│   │   │       ├── README_load_bedelia_data.md # Documentación
│   │   │       ├── verify_data.py              # Script de verificación
│   │   │       └── test_load.sh                # Script de pruebas
│   │   └── ESTRUCTURA_MODELOS.md      # Documentación de modelos
```

## 🔧 Paso a Paso

### 1️⃣ Crear Migraciones

```bash
cd bedelia
python manage.py makemigrations
```

**Salida esperada:**
```
Migrations for 'api':
  api/migrations/0001_initial.py
    - Create model Carrera
    - Create model Curso
    - Create model Previa
    - Create model ItemPrevia
    - Create model Posprevia
```

### 2️⃣ Aplicar Migraciones

```bash
python manage.py migrate
```

**Salida esperada:**
```
Running migrations:
  Applying api.0001_initial... OK
```

### 3️⃣ Verificar Archivos JSON

```bash
# Verificar que existan los archivos
ls -lh data/*.json
```

Deberías ver:
```
-rw-r--r-- 1 user user  21M credits_data_backup.json
-rw-r--r-- 1 user user 592M posprevias_data_backup.json
-rw-r--r-- 1 user user 120M previas_data_backup.json
-rw-r--r-- 1 user user 9.5M vigentes_data_backup.json
```

### 4️⃣ Probar en Modo Dry-Run (Recomendado)

Primero, ejecuta el comando en modo dry-run para verificar que todo funcione sin guardar datos:

```bash
python manage.py load_bedelia_data --dry-run --verbose
```

Esto te mostrará:
- Qué datos se cargarían
- Estadísticas de cada paso
- Advertencias o errores
- **NO guardará nada en la base de datos**

### 5️⃣ Cargar Datos Reales

Una vez que el dry-run funcione correctamente:

```bash
python manage.py load_bedelia_data --clear --verbose
```

**Opciones:**
- `--clear`: Limpia la base de datos antes de cargar (recomendado para primera vez)
- `--verbose`: Muestra detalles del proceso

**⏱️ Tiempo estimado:** 5-15 minutos dependiendo del tamaño de los datos

### 6️⃣ Verificar Datos Cargados

Después de cargar, verifica la integridad:

```bash
python manage.py shell < bedelia/api/management/commands/verify_data.py
```

O manualmente en el shell:

```bash
python manage.py shell
```

```python
from api.models import Carrera, Curso, Previa, ItemPrevia, Posprevia

# Contar registros
print(f"Carreras: {Carrera.objects.count()}")
print(f"Cursos: {Curso.objects.count()}")
print(f"Previas: {Previa.objects.count()}")
print(f"Items: {ItemPrevia.objects.count()}")
print(f"Posprevias: {Posprevia.objects.count()}")

# Ver ejemplo de curso con previas
curso = Curso.objects.filter(previas__isnull=False).first()
print(f"\nEjemplo: {curso}")
print(f"Previas: {curso.previas.count()}")
```

## 📊 Estadísticas Esperadas

Después de cargar, deberías ver algo como:

```
============================================================
📊 ESTADÍSTICAS
============================================================
🎓 Carreras creadas:    45
📚 Cursos creados:      1,234
🌳 Previas creadas:     5,678
📝 Items creados:       12,345
🔗 Posprevias creadas:  8,901
ℹ️  567 cursos con previas, 667 cursos sin previas (de 1,234 totales)
============================================================
```

## 🎯 Datos Importantes

### Estructura de Datos

1. **Vigentes**: Contiene TODOS los cursos activos
2. **Credits**: Contiene los créditos (puede tener cursos adicionales)
3. **Previas**: Solo los cursos con requisitos (NO todos)
4. **Posprevias**: Relaciones inversas de dependencia

### Es Normal Que:

✅ Haya cursos sin previas (muchos cursos no tienen requisitos)  
✅ Algunos cursos tengan 0 créditos  
✅ Haya advertencias sobre cursos no encontrados en posprevias  
✅ El proceso tome varios minutos  

### NO es Normal Que:

❌ Todos los cursos tengan previas  
❌ Haya errores de integridad de base de datos  
❌ Falten todos los archivos JSON  

## 🔄 Actualizar Datos

Para actualizar con datos nuevos:

```bash
# Opción 1: Limpiar y recargar todo
python manage.py load_bedelia_data --clear --verbose

# Opción 2: Actualización incremental (agrega/actualiza)
python manage.py load_bedelia_data --verbose
```

## 🐛 Solución de Problemas

### Problema: "Archivo no encontrado"

**Solución:**
```bash
# Verificar rutas
ls data/*.json

# O especificar rutas manualmente
python manage.py load_bedelia_data \
    --vigentes=data/vigentes_data_backup.json \
    --credits=data/credits_data_backup.json \
    --previas=data/previas_data_backup.json \
    --posprevias=data/posprevias_data_backup.json
```

### Problema: "Out of memory"

**Solución:**
- Aumentar memoria disponible
- Procesar en lotes (modificar el comando)
- Usar base de datos más eficiente (PostgreSQL)

### Problema: "Integrity error"

**Solución:**
```bash
# Limpiar base de datos y reintentar
python manage.py load_bedelia_data --clear
```

### Problema: El proceso se congela

**Solución:**
- Verificar que la base de datos esté respondiendo
- Revisar logs de Django
- Ejecutar con `--verbose` para ver en qué paso se detiene

## 📚 Consultas Útiles

### Ver todas las carreras

```python
from api.models import Carrera
for c in Carrera.objects.all():
    print(f"{c.nombre} ({c.anio_plan})")
```

### Ver cursos de una carrera

```python
from api.models import Carrera
carrera = Carrera.objects.get(nombre="INGENIERÍA CIVIL")
cursos = carrera.cursos.filter(activo=True)
print(f"Cursos: {cursos.count()}")
```

### Ver árbol de previas de un curso

```python
from api.models import Curso, Previa

curso = Curso.objects.get(codigo_curso="1144")
previas_raiz = curso.previas.filter(padre__isnull=True)

for previa in previas_raiz:
    print(f"Previa raíz: {previa}")
    for hijo in previa.obtener_hijos():
        print(f"  - {hijo.tipo}: {hijo.titulo}")
```

### Ver posprevias (materias que requieren un curso)

```python
curso = Curso.objects.get(codigo_curso="1061")
posprevias = curso.posprevias.all()
print(f"Materias que requieren {curso}:")
for p in posprevias:
    print(f"  - {p.materia_codigo}: {p.materia_nombre}")
```

## 🧪 Scripts de Prueba

### Test rápido

```bash
bash bedelia/api/management/commands/test_load.sh
```

### Verificación completa

```bash
python manage.py shell < bedelia/api/management/commands/verify_data.py
```

## 📖 Documentación Adicional

- [ESTRUCTURA_MODELOS.md](bedelia/api/ESTRUCTURA_MODELOS.md): Explicación detallada de los modelos
- [README_load_bedelia_data.md](bedelia/api/management/commands/README_load_bedelia_data.md): Documentación del comando
- [models.py](bedelia/api/models.py): Código fuente de los modelos

## ✅ Checklist Final

- [ ] Migraciones creadas y aplicadas
- [ ] Archivos JSON verificados
- [ ] Comando ejecutado en dry-run
- [ ] Datos cargados exitosamente
- [ ] Verificación completada
- [ ] Estadísticas correctas
- [ ] Sin errores de integridad

## 🆘 Ayuda

Si tienes problemas:

1. Revisa los logs con `--verbose`
2. Prueba con `--dry-run` primero
3. Verifica que los archivos JSON sean válidos
4. Asegúrate de que la base de datos esté funcionando
5. Consulta la documentación en los archivos README

---

**¡Listo para comenzar! 🚀**

