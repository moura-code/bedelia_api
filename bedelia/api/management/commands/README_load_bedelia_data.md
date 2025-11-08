# Comando `load_bedelia_data`

Comando de Django para cargar datos de Bedelia desde archivos JSON a la base de datos.

## 📋 Descripción

Este comando importa los 4 archivos JSON de la carpeta `data/`:

1. **vigentes_data_backup.json**: Cursos vigentes (TODOS los cursos activos)
2. **credits_data_backup.json**: Créditos de los cursos
3. **previas_data_backup.json**: Requisitos (estructura de árbol jerárquica)
4. **posprevias_data_backup.json**: Materias que dependen de un curso

### ⚠️ Importante

- **vigentes** contiene TODOS los cursos activos
- **credits** contiene los créditos (puede tener cursos adicionales no en vigentes)
- **previas** contiene SOLO los cursos que tienen requisitos (NO todos los cursos)
- Es normal que haya cursos sin previas

## 🚀 Uso Básico

### Carga Normal

```bash
python manage.py load_bedelia_data
```

### Con Opciones

```bash
# Modo dry-run (no guarda en la base de datos)
python manage.py load_bedelia_data --dry-run

# Modo verbose (muestra detalles)
python manage.py load_bedelia_data --verbose

# Limpiar base de datos antes de cargar
python manage.py load_bedelia_data --clear

# Combinar opciones
python manage.py load_bedelia_data --clear --verbose
```

### Especificar Rutas de Archivos

```bash
python manage.py load_bedelia_data \
    --vigentes=data/vigentes_data_backup.json \
    --credits=data/credits_data_backup.json \
    --previas=data/previas_data_backup.json \
    --posprevias=data/posprevias_data_backup.json
```

## 📊 Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--vigentes` | Ruta al archivo de cursos vigentes | `data/vigentes_data_backup.json` |
| `--credits` | Ruta al archivo de créditos | `data/credits_data_backup.json` |
| `--previas` | Ruta al archivo de requisitos | `data/previas_data_backup.json` |
| `--posprevias` | Ruta al archivo de posprevias | `data/posprevias_data_backup.json` |
| `--dry-run` | Procesar sin guardar en DB | `False` |
| `--verbose` | Salida detallada | `False` |
| `--clear` | Limpiar DB antes de cargar | `False` |

## 🔄 Proceso de Carga

El comando ejecuta los siguientes pasos:

### 1. Verificación de Archivos
Verifica que todos los archivos JSON existan.

### 2. Limpieza (opcional)
Si se usa `--clear`, elimina todos los datos existentes:
- Posprevias
- Items de Previa
- Previas
- Cursos
- Carreras

### 3. Carga de Carreras y Cursos
Lee `vigentes_data_backup.json` y `credits_data_backup.json`:
- Crea carreras únicas
- Crea cursos con sus créditos
- Asocia cursos con carreras (relación ManyToMany)

### 4. Carga de Previas (Requisitos)
Lee `previas_data_backup.json`:
- Construye el árbol jerárquico de requisitos
- Crea nodos con tipos: ALL, ANY, NOT, LEAF
- Crea items individuales para nodos LEAF
- Mantiene las relaciones padre-hijo

### 5. Carga de Posprevias
Lee `posprevias_data_backup.json`:
- Asocia cada curso con las materias que lo requieren
- Almacena información detallada de cada dependencia

## 📈 Estadísticas

Al finalizar, el comando muestra:

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
⚠️  Advertencias:        12
============================================================
```

### Interpretación

- **Carreras creadas**: Número de carreras únicas cargadas
- **Cursos creados**: Total de cursos activos (todos en vigentes)
- **Previas creadas**: Total de nodos en los árboles de requisitos
- **Items creados**: Items individuales en los nodos LEAF
- **Posprevias creadas**: Relaciones de dependencia inversa
- **Cursos con previas**: Cursos que tienen requisitos definidos
- **Cursos sin previas**: Cursos que NO tienen requisitos (normal)

## 🌳 Estructura de Previas

Las previas se cargan como un árbol jerárquico:

```
Curso: "1144 - VIBRACIONES Y ONDAS"
│
└─── [ALL] debe tener todas
     ├─── [NOT] no debe tener
     │    └─── [LEAF] 1 aprobación/es entre:
     │         ├── Item: FI15 (exam)
     │         ├── Item: 1144P (exam)
     │         └── Item: 1126 (exam)
     │
     └─── [LEAF] 1 aprobación/es entre:
          └── Item: ...
```

### Tipos de Nodos

- **ALL**: Debe cumplir TODOS los hijos
- **ANY**: Debe cumplir AL MENOS UNO de los hijos
- **NOT**: NO debe tener NINGUNO de los hijos
- **LEAF**: Contiene items individuales (ItemPrevia)

## ⚠️ Advertencias y Errores

El comando maneja errores y muestra:

- **Advertencias**: Cursos no encontrados en referencias
- **Errores**: Problemas al procesar previas

Los errores no detienen el proceso completo.

## 💾 Transaccionalidad

- Todo el proceso se ejecuta en una **transacción atómica**
- Si hay un error crítico, se hace **rollback** automático
- En modo `--dry-run`, siempre se hace rollback al final

## 🔍 Ejemplos de Uso

### Verificar Datos sin Guardar

```bash
python manage.py load_bedelia_data --dry-run --verbose
```

### Carga Completa desde Cero

```bash
# Paso 1: Limpiar y cargar
python manage.py load_bedelia_data --clear --verbose

# Paso 2: Verificar en Django shell
python manage.py shell
>>> from api.models import Carrera, Curso, Previa
>>> Carrera.objects.count()
45
>>> Curso.objects.count()
1234
```

### Actualización Incremental

```bash
# Sin --clear, solo agrega o actualiza
python manage.py load_bedelia_data --verbose
```

## 🐛 Troubleshooting

### Error: Archivo no encontrado

```
❌ Archivo no encontrado: data/vigentes_data_backup.json
```

**Solución**: Verificar que los archivos JSON estén en la carpeta `data/`

### Error: Curso no encontrado

```
⚠️  Curso no encontrado: ABC123
```

**Causa**: Una posprevia referencia un curso que no existe en vigentes
**Solución**: Normal, se registra como advertencia y continúa

### Error de transacción

Si hay errores de base de datos, el comando hace rollback automático y no deja datos inconsistentes.

## 📝 Notas

1. **Performance**: La carga puede tomar varios minutos dependiendo del tamaño de los datos
2. **Memoria**: Los archivos JSON grandes se cargan completamente en memoria
3. **Caché**: El comando usa cachés internos para optimizar la búsqueda de carreras y cursos
4. **Relaciones**: Las relaciones ManyToMany se crean correctamente
5. **UUIDs**: Los IDs son UUIDs generados automáticamente

## 🔗 Ver También

- [ESTRUCTURA_MODELOS.md](../../ESTRUCTURA_MODELOS.md): Documentación de los modelos
- [models.py](../../models.py): Definición de los modelos

