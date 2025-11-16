"""
Comando de Django para cargar datos de Bedelia desde archivos JSON a la base de datos.

Este comando importa los archivos JSON de la carpeta data/:
- credits_data_backup.json: Carreras, planes de estudio, materias y relaciones plan-materia
- vigentes_data_backup.json: Cursos vigentes (para marcar materias como activas)
- previas_data_backup.json: Previas (requisitos/prerequisitos) de cada materia
- posprevias_data_backup.json: Posprevias (qué cursos requieren este curso como prerrequisito)

El comando procesa los datos en el siguiente orden:
1. Extrae y crea carreras únicas desde las claves "CARRERA_ANIO"
2. Extrae y crea planes de estudio (carrera + año)
3. Extrae y crea materias únicas (deduplicadas por código)
4. Crea relaciones PlanMateria (qué materias están en cada plan)
5. Marca materias como activas según vigentes_data
6. Carga previas (requisitos) creando UnidadAprobable, RequisitoNodo y RequisitoItem
7. Procesa posprevias (valida y completa relaciones de requisitos inversos)

Uso:
    python manage.py load_bedelia_data
    python manage.py load_bedelia_data --dry-run
    python manage.py load_bedelia_data --verbose
    python manage.py load_bedelia_data --clear
    python manage.py load_bedelia_data --skip-previas  # Omitir carga de previas
    python manage.py load_bedelia_data --skip-posprevias  # Omitir carga de posprevias
    python manage.py load_bedelia_data --credits ../data/credits_data_backup.json --vigentes ../data/vigentes_data_backup.json --previas ../data/previas_data_backup.json --posprevias ../data/posprevias_data_backup.json
"""
import json
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import (
    Materia, PlanEstudio, PlanMateria,
    UnidadAprobable, RequisitoNodo, RequisitoItem
)


class Command(BaseCommand):
    """Cargar datos de Bedelia desde archivos JSON."""
    
    help = 'Importar carreras, planes de estudio y materias de Bedelia desde archivos JSON'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--credits',
            type=str,
            default='../data/credits_data_backup.json',
            help='Ruta al archivo credits_data_backup.json'
        )
        parser.add_argument(
            '--vigentes',
            type=str,
            default='../data/vigentes_data_backup.json',
            help='Ruta al archivo vigentes_data_backup.json'
        )
        parser.add_argument(
            '--previas',
            type=str,
            default='../data/previas_data_backup.json',
            help='Ruta al archivo previas_data_backup.json'
        )
        parser.add_argument(
            '--skip-previas',
            action='store_true',
            help='Omitir la carga de previas (requisitos)'
        )
        parser.add_argument(
            '--posprevias',
            type=str,
            default='../data/posprevias_data_backup.json',
            help='Ruta al archivo posprevias_data_backup.json'
        )
        parser.add_argument(
            '--skip-posprevias',
            action='store_true',
            help='Omitir la carga de posprevias'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Procesar sin guardar en la base de datos'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Habilitar salida detallada'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar todas las carreras, planes y materias antes de cargar'
        )
        parser.add_argument(
            '--errors-file',
            type=str,
            default='load_bedelia_errors.json',
            help='Ruta del archivo donde guardar los errores detallados (JSON)'
        )
        parser.add_argument(
            '--errors-text-file',
            type=str,
            default=None,
            help='Ruta del archivo donde guardar los errores en formato texto (opcional)'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = False
        self.dry_run = False
        
        # Estadísticas
        self.stats = {
            'planes_creados': 0,
            'plan_materias_creadas': 0,
            'materias_creadas': 0,
            'materias_actualizadas': 0,
            'materias_marcadas_activas': 0,
            'materias_totales': 0,
            'unidades_creadas': 0,
            'requisitos_nodos_creados': 0,
            'requisitos_items_creados': 0,
            'posprevias_procesadas': 0,
            'posprevias_validadas': 0,
            'errors': 0,
        }
        
        # Lista de errores para mostrar detalles
        # Estructura: {
        #   'type': str,           # Tipo de error (categoría)
        #   'item': str,            # Item afectado (identificador)
        #   'message': str,          # Mensaje de error corto
        #   'full_message': str,     # Mensaje completo (opcional)
        #   'context': dict,        # Contexto adicional (opcional)
        #   'timestamp': str,       # Timestamp del error
        #   'stage': str            # Etapa del procesamiento
        # }
        self.error_list = []
        
        # Cachés para evitar consultas repetidas
        self.plan_cache: Dict[str, PlanEstudio] = {}
        self.materia_cache: Dict[str, Materia] = {}
        
        # Track current processing stage for error context
        self.current_stage = 'initialization'
    
    def handle(self, *args, **options):
        """Punto de entrada principal del comando."""
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔄 Modo DRY RUN - No se guardará nada en la base de datos'))
        
        # Verificar archivos
        credits_path = Path(options['credits'])
        vigentes_path = Path(options['vigentes'])
        previas_path = Path(options['previas']) if not options['skip_previas'] else None
        posprevias_path = Path(options['posprevias']) if not options['skip_posprevias'] else None
        
        if not credits_path.exists():
            raise CommandError(f'❌ Archivo no encontrado: {credits_path}')
        
        if not vigentes_path.exists():
            raise CommandError(f'❌ Archivo no encontrado: {vigentes_path}')
        
        if previas_path and not previas_path.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Archivo de previas no encontrado: {previas_path}'))
            self.stdout.write(self.style.WARNING('   Continuando sin cargar previas...'))
            previas_path = None
        
        if posprevias_path and not posprevias_path.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Archivo de posprevias no encontrado: {posprevias_path}'))
            self.stdout.write(self.style.WARNING('   Continuando sin cargar posprevias...'))
            posprevias_path = None
        
        try:
            with transaction.atomic():
                # Limpiar base de datos si se solicita
                if options['clear']:
                    self.clear_database()
                
                # Cargar datos
                self.stdout.write('📖 Cargando archivos JSON...')
                credits_data = self.load_json(credits_path)
                vigentes_data = self.load_json(vigentes_path)
                previas_data = self.load_json(previas_path) if previas_path else {}
                posprevias_data = self.load_json(posprevias_path) if posprevias_path else {}
                
                # Paso 1: Crear carreras y planes de estudio
                self.current_stage = 'carreras_y_planes'
                self.stdout.write('🎓 Procesando carreras y planes de estudio desde credits_data...')
                self.process_carreras_y_planes(credits_data)
                
                # Paso 2: Extraer y crear materias desde credits
                self.current_stage = 'materias'
                self.stdout.write('📚 Procesando materias desde credits_data...')
                self.process_materias(credits_data)
                
                # Paso 3: Crear relaciones PlanMateria
                self.current_stage = 'plan_materias'
                self.stdout.write('🔗 Creando relaciones plan-materia...')
                self.process_plan_materias(credits_data)
                
                # Paso 4: Marcar materias activas desde vigentes
                self.current_stage = 'marcar_activas'
                self.stdout.write('✅ Marcando materias activas desde vigentes_data...')
                self.mark_active_materias(vigentes_data)
                
                # Paso 5: Cargar previas (requisitos) si está disponible
                if previas_data:
                    self.current_stage = 'previas'
                    self.stdout.write('📋 Procesando previas (requisitos) desde previas_data...')
                    self.process_previas(previas_data)
                else:
                    self.stdout.write('⏭️  Saltando carga de previas (archivo no disponible o --skip-previas)')
                
                # Paso 6: Procesar posprevias (validar y completar previas) si está disponible
                if posprevias_data:
                    self.current_stage = 'posprevias'
                    self.stdout.write('🔄 Procesando posprevias (validación de requisitos inversos)...')
                    self.process_posprevias(posprevias_data)
                else:
                    self.stdout.write('⏭️  Saltando carga de posprevias (archivo no disponible o --skip-posprevias)')
                
                # Si es dry-run, hacer rollback
                if self.dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING('🔙 Rollback aplicado (dry-run)'))
            
            # Mostrar estadísticas
            self.print_stats()
            
            # Exportar errores a archivos si hay errores
            if self.error_list:
                errors_file_path = Path(options.get('errors_file', 'load_bedelia_errors.json'))
                self.export_errors_to_json(errors_file_path)
                
                errors_text_file = options.get('errors_text_file')
                if errors_text_file:
                    self.export_errors_to_text(Path(errors_text_file))
            
            if not self.dry_run:
                self.stdout.write(self.style.SUCCESS('✅ Datos cargados exitosamente!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()
            raise
    
    def clear_database(self):
        """Limpiar todas las carreras, planes, materias y previas de la base de datos."""
        self.stdout.write(self.style.WARNING('🗑️  Limpiando base de datos...'))
        
        if not self.dry_run:
            # Eliminar en orden de dependencias (hijos primero)
            requisitos_items_count = RequisitoItem.objects.count()
            RequisitoItem.objects.all().delete()
            
            requisitos_nodos_count = RequisitoNodo.objects.count()
            RequisitoNodo.objects.all().delete()
            
            unidades_count = UnidadAprobable.objects.count()
            UnidadAprobable.objects.all().delete()
            
            plan_materias_count = PlanMateria.objects.count()
            PlanMateria.objects.all().delete()
            
            planes_count = PlanEstudio.objects.count()
            PlanEstudio.objects.all().delete()
            
            materias_count = Materia.objects.count()
            Materia.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ {requisitos_items_count} items de requisitos, '
                f'{requisitos_nodos_count} nodos de requisitos, '
                f'{unidades_count} unidades aprobables, '
                f'{plan_materias_count} plan-materias, {planes_count} planes, '
                f'{materias_count} materias eliminadas'
            ))
        else:
            requisitos_items_count = RequisitoItem.objects.count()
            requisitos_nodos_count = RequisitoNodo.objects.count()
            unidades_count = UnidadAprobable.objects.count()
            plan_materias_count = PlanMateria.objects.count()
            planes_count = PlanEstudio.objects.count()
            materias_count = Materia.objects.count()
            self.stdout.write(self.style.SUCCESS(
                f'✅ {requisitos_items_count} items de requisitos, '
                f'{requisitos_nodos_count} nodos de requisitos, '
                f'{unidades_count} unidades aprobables, '
                f'{plan_materias_count} plan-materias, {planes_count} planes, '
                f'{materias_count} materias serían eliminadas (dry-run)'
            ))
    
    def load_json(self, path: Path) -> Dict:
        """Cargar archivo JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def parse_carrera_plan(self, carrera_plan: str) -> tuple:
        """
        Parsear string 'CARRERA_ANIO' a (carrera, anio).
        
        Ejemplos:
        - "INGENIERÍA CIVIL_2021" -> ("INGENIERÍA CIVIL", "2021")
        - "DOCTOR EN INGENIERIA_2013" -> ("DOCTOR EN INGENIERIA", "2013")
        """
        parts = carrera_plan.rsplit('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return carrera_plan, None
    
    def add_error(self, error_type: str, item: str, message: str, 
                  full_message: Optional[str] = None, context: Optional[Dict] = None):
        """
        Agregar un error estructurado a la lista de errores.
        
        Args:
            error_type: Tipo/categoría del error
            item: Identificador del item afectado
            message: Mensaje de error corto
            full_message: Mensaje completo (opcional)
            context: Contexto adicional como diccionario (opcional)
        """
        error = {
            'type': error_type,
            'item': item,
            'message': message,
            'full_message': full_message or message,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'stage': self.current_stage
        }
        self.error_list.append(error)
        self.stats['errors'] += 1
    
    def normalize_string(self, text: str) -> str:
        """
        Normalizar string removiendo acentos y convirtiendo a mayúsculas.
        Útil para comparar nombres de carreras que pueden tener o no acentos.
        """
        if not text:
            return ""
        # Normalizar a NFD (decomposed form) y remover diacríticos
        normalized = unicodedata.normalize('NFD', text.upper().strip())
        # Filtrar solo caracteres que no son diacríticos
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    def find_plan_by_carrera_name(self, nombre_carrera: str, anio: str) -> Optional[PlanEstudio]:
        """
        Buscar plan por nombre de carrera usando comparación flexible.
        Maneja variaciones en acentos, abreviaciones y nombres parciales.
        """
        if not nombre_carrera or not anio:
            return None
        
        nombre_normalized = self.normalize_string(nombre_carrera)
        
        # 1. Intentar búsqueda exacta (con y sin acentos)
        plan = PlanEstudio.objects.filter(nombre_carrera=nombre_carrera, anio=anio).first()
        if plan:
            return plan
        
        # 2. Buscar comparando sin acentos (coincidencia exacta normalizada)
        for plan in PlanEstudio.objects.filter(anio=anio):
            if self.normalize_string(plan.nombre_carrera) == nombre_normalized:
                return plan
        
        # 3. Buscar por palabras clave principales (más preciso que contención simple)
        # Extraer palabras significativas (más de 3 caracteres) del nombre buscado
        palabras_buscadas = [p for p in nombre_normalized.split() if len(p) > 3]
        
        if len(palabras_buscadas) >= 2:  # Si hay al menos 2 palabras significativas
            mejor_coincidencia = None
            mejor_puntaje = 0
            for plan in PlanEstudio.objects.filter(anio=anio):
                plan_normalized = self.normalize_string(plan.nombre_carrera)
                # Contar cuántas palabras del nombre buscado están en el plan
                palabras_encontradas = sum(1 for palabra in palabras_buscadas if palabra in plan_normalized)
                # Requerir que al menos todas las palabras menos una estén presentes
                if palabras_encontradas > mejor_puntaje and palabras_encontradas >= len(palabras_buscadas) - 1:
                    mejor_puntaje = palabras_encontradas
                    mejor_coincidencia = plan
            
            if mejor_coincidencia:
                return mejor_coincidencia
        
        # 4. Buscar por palabra única significativa (útil para casos como "AGRIMENSURA")
        if len(palabras_buscadas) == 1:
            palabra_clave = palabras_buscadas[0]
            if len(palabra_clave) >= 6:  # Solo si la palabra clave es suficientemente larga
                for plan in PlanEstudio.objects.filter(anio=anio):
                    plan_normalized = self.normalize_string(plan.nombre_carrera)
                    if palabra_clave in plan_normalized:
                        return plan
        
        # 5. Buscar si el nombre normalizado está contenido en algún plan
        # (útil para abreviaciones como "AGRIMENSURA" -> "INGENIERÍA EN AGRIMENSURA")
        # Solo si el nombre buscado tiene al menos 6 caracteres para evitar coincidencias muy cortas
        if len(nombre_normalized) >= 6:
            for plan in PlanEstudio.objects.filter(anio=anio):
                plan_normalized = self.normalize_string(plan.nombre_carrera)
                # Preferir cuando el nombre buscado está contenido en el plan (abreviación)
                if nombre_normalized in plan_normalized:
                    return plan
                # También considerar cuando el plan está contenido en el nombre buscado
                elif plan_normalized in nombre_normalized and len(plan_normalized) >= 8:
                    return plan
        
        return None
    
    def get_or_create_plan(self, nombre_carrera: str, anio: str) -> PlanEstudio:
        """Obtener o crear un plan de estudio."""
        cache_key = f"{nombre_carrera}_{anio}"
        
        if cache_key in self.plan_cache:
            return self.plan_cache[cache_key]
        
        try:
            if self.dry_run:
                plan = PlanEstudio(nombre_carrera=nombre_carrera, anio=anio)
            else:
                plan, created = PlanEstudio.objects.get_or_create(
                    nombre_carrera=nombre_carrera,
                    anio=anio,
                    defaults={}
                )
                if created:
                    self.stats['planes_creados'] += 1
                    if self.verbose:
                        self.stdout.write(f'       ✨ Nuevo plan: {nombre_carrera} - {anio}')
            
            self.plan_cache[cache_key] = plan
            return plan
        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"Error creando/obteniendo plan '{nombre_carrera} - {anio}': {str(e)}"
            self.error_list.append({
                'type': 'plan',
                'item': f"{nombre_carrera} - {anio}",
                'message': str(e),
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            # Re-raise para que el proceso falle si es crítico
            raise
    
    def get_or_create_materia(self, codigo: str, nombre: str, creditos: int) -> Materia:
        """Obtener o crear una materia."""
        if codigo in self.materia_cache:
            return self.materia_cache[codigo]
        
        if self.dry_run:
            materia = Materia(codigo=codigo, nombre=nombre, creditos=creditos, activo=False)
        else:
            materia, created = Materia.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'creditos': creditos,
                    'activo': False,
                }
            )
            if created:
                self.stats['materias_creadas'] += 1
            else:
                # Actualizar si es necesario
                updated = False
                if materia.nombre != nombre and nombre:
                    materia.nombre = nombre
                    updated = True
                if materia.creditos != creditos and creditos > 0:
                    materia.creditos = creditos
                    updated = True
                if updated:
                    materia.save()
                    self.stats['materias_actualizadas'] += 1
        
        self.materia_cache[codigo] = materia
        return materia
    
    def process_carreras_y_planes(self, credits_data: Dict):
        """
        Procesar planes de estudio desde credits_data.
        
        Extrae planes únicos de las claves "CARRERA_ANIO".
        """
        planes_set: Set[tuple] = set()  # (carrera_nombre, anio)
        
        total_programs = len(credits_data)
        
        # Primera pasada: extraer planes únicos
        for idx, (carrera_plan, cursos) in enumerate(credits_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            carrera_nombre, anio = self.parse_carrera_plan(carrera_plan)
            
            if carrera_nombre and anio:
                planes_set.add((carrera_nombre, anio))
        
        self.stdout.write(f'     📊 {len(planes_set)} planes únicos encontrados')
        
        # Crear planes de estudio
        self.stdout.write('     💾 Guardando planes de estudio en la base de datos...')
        for carrera_nombre, anio in sorted(planes_set):
            self.get_or_create_plan(carrera_nombre, anio)
        
        self.stdout.write(
            f'     ✅ {self.stats["planes_creados"]} planes creados'
        )
    
    def process_materias(self, credits_data: Dict):
        """
        Procesar materias desde credits_data.
        
        Estructura de credits_data:
        {
            "CARRERA_PLAN": {
                "codigo_nombre": {
                    "codigo": "CIM40",
                    "nombre": "ELECTROMAGNETÍSMO CIM",
                    "creditos": "10"
                }
            }
        }
        
        Se deduplican las materias por código (codigo es único).
        """
        # Diccionario para almacenar materias únicas por código
        materias_dict: Dict[str, Dict] = {}
        
        total_programs = len(credits_data)
        processed_items = 0
        
        # Primera pasada: extraer todas las materias únicas
        for idx, (carrera_plan, cursos) in enumerate(credits_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            for codigo_nombre, curso_data in cursos.items():
                codigo = curso_data.get('codigo', '').strip()
                nombre = curso_data.get('nombre', '').strip()
                creditos_str = curso_data.get('creditos', '0')
                
                if not codigo:
                    continue
                
                # Convertir créditos a int
                try:
                    creditos = int(creditos_str)
                except (ValueError, TypeError):
                    creditos = 0
                    if self.verbose:
                        self.stdout.write(
                            self.style.WARNING(f'       ⚠️  Créditos inválidos para {codigo}: "{creditos_str}"')
                        )
                
                # Si ya existe, usar la primera ocurrencia (o podemos actualizar si el nombre es mejor)
                if codigo not in materias_dict:
                    materias_dict[codigo] = {
                        'codigo': codigo,
                        'nombre': nombre,
                        'creditos': creditos,
                    }
                else:
                    # Si el nombre está vacío pero tenemos uno nuevo, actualizar
                    if not materias_dict[codigo]['nombre'] and nombre:
                        materias_dict[codigo]['nombre'] = nombre
                    # Si los créditos son 0 pero tenemos uno nuevo, actualizar
                    if materias_dict[codigo]['creditos'] == 0 and creditos > 0:
                        materias_dict[codigo]['creditos'] = creditos
                
                processed_items += 1
        
        self.stdout.write(f'     📊 {processed_items} items procesados, {len(materias_dict)} materias únicas encontradas')
        
        # Segunda pasada: crear o actualizar materias en la base de datos
        self.stdout.write('     💾 Guardando materias en la base de datos...')
        
        for idx, (codigo, materia_data) in enumerate(materias_dict.items(), 1):
            if self.verbose and idx % 100 == 0:
                self.stdout.write(f'       [{idx}/{len(materias_dict)}] Procesando: {codigo}')
            
            try:
                self.get_or_create_materia(
                    codigo=materia_data['codigo'],
                    nombre=materia_data['nombre'],
                    creditos=materia_data['creditos']
                )
            except Exception as e:
                self.stats['errors'] += 1
                error_msg = f"Error procesando materia {materia_data['codigo']}: {str(e)}"
                self.error_list.append({
                    'type': 'materia',
                    'item': materia_data['codigo'],
                    'message': str(e),
                    'full_message': error_msg
                })
                if self.verbose:
                    self.stdout.write(
                        self.style.ERROR(f'       ❌ {error_msg}')
                    )
        
        self.stats['materias_totales'] = len(materias_dict)
        self.stdout.write(
            f'     ✅ {self.stats["materias_creadas"]} materias creadas, '
            f'{self.stats["materias_actualizadas"]} actualizadas'
        )
    
    def process_plan_materias(self, credits_data: Dict):
        """
        Crear relaciones PlanMateria desde credits_data.
        
        Crea las relaciones entre planes de estudio y materias.
        """
        total_programs = len(credits_data)
        processed_relations = 0
        
        self.stdout.write('     💾 Guardando relaciones plan-materia en la base de datos...')
        
        for idx, (carrera_plan, cursos) in enumerate(credits_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            carrera_nombre, anio = self.parse_carrera_plan(carrera_plan)
            
            if not carrera_nombre or not anio:
                continue
            
            # Obtener plan
            plan = self.get_or_create_plan(carrera_nombre, anio)
            
            # Crear relaciones PlanMateria para cada materia en este plan
            for codigo_nombre, curso_data in cursos.items():
                codigo = curso_data.get('codigo', '').strip()
                
                if not codigo:
                    continue
                
                try:
                    # Obtener materia
                    materia = self.get_or_create_materia(
                        codigo=codigo,
                        nombre=curso_data.get('nombre', '').strip(),
                        creditos=int(curso_data.get('creditos', '0') or '0')
                    )
                    
                    # Crear relación PlanMateria
                    if self.dry_run:
                        # En dry-run, solo contar
                        try:
                            PlanMateria.objects.get(plan=plan, materia=materia)
                        except PlanMateria.DoesNotExist:
                            self.stats['plan_materias_creadas'] += 1
                    else:
                        plan_materia, created = PlanMateria.objects.get_or_create(
                            plan=plan,
                            materia=materia
                        )
                        if created:
                            self.stats['plan_materias_creadas'] += 1
                            processed_relations += 1
                
                except Exception as e:
                    self.stats['errors'] += 1
                    error_msg = f"Error creando relación plan-materia: {carrera_plan} - {codigo}: {str(e)}"
                    self.error_list.append({
                        'type': 'plan_materia',
                        'item': f"{carrera_plan} - {codigo}",
                        'message': str(e),
                        'full_message': error_msg
                    })
                    if self.verbose:
                        self.stdout.write(
                            self.style.ERROR(f'       ❌ {error_msg}')
                        )
        
        self.stdout.write(
            f'     ✅ {self.stats["plan_materias_creadas"]} relaciones plan-materia creadas'
        )
    
    def mark_active_materias(self, vigentes_data: Dict):
        """
        Marcar como activas las materias que aparecen en vigentes_data.
        
        Estructura de vigentes_data:
        {
            "CARRERA_PLAN": {
                "course_code": {
                    "university_code": "FING",
                    "course_code": "1267",
                    "course_name": "TALLER REPR. Y COM. GRAFICA"
                }
            }
        }
        """
        # Extraer todos los códigos activos
        codigos_activos: Set[str] = set()
        
        total_programs = len(vigentes_data)
        
        for idx, (carrera_plan, cursos) in enumerate(vigentes_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            for course_code_key, curso_data in cursos.items():
                course_code = curso_data.get('course_code', '').strip()
                if course_code:
                    codigos_activos.add(course_code)
        
        self.stdout.write(f'     📊 {len(codigos_activos)} códigos únicos encontrados en vigentes')
        
        # Marcar materias como activas
        if self.dry_run:
            # En dry-run, contar cuántas se marcarían como activas
            materias_a_activar = Materia.objects.filter(codigo__in=codigos_activos, activo=False).count()
            self.stats['materias_marcadas_activas'] = materias_a_activar
            self.stdout.write(f'     ✅ {materias_a_activar} materias serían marcadas como activas (dry-run)')
        else:
            # Actualizar materias activas
            updated_count = Materia.objects.filter(
                codigo__in=codigos_activos,
                activo=False
            ).update(activo=True)
            
            self.stats['materias_marcadas_activas'] = updated_count
            self.stdout.write(f'     ✅ {updated_count} materias marcadas como activas')
            
            # También marcar como inactivas las que no están en vigentes pero estaban activas
            # (opcional, comentado por ahora)
            # materias_inactivadas = Materia.objects.filter(
            #     activo=True
            # ).exclude(codigo__in=codigos_activos).update(activo=False)
            # if materias_inactivadas > 0:
            #     self.stdout.write(f'     📜 {materias_inactivadas} materias marcadas como inactivas')
    
    def process_previas(self, previas_data: Dict):
        """
        Procesar previas (requisitos) desde previas_data.
        
        Estructura esperada:
        {
            "CARRERA_ANIO": {
                "CODIGO - NOMBRE": {
                    "code": "CODIGO",
                    "name": "Examen" | "Curso" | etc,
                    "requirements": {
                        "type": "ALL" | "ANY" | "NOT" | "LEAF",
                        "title": "...",
                        "children": [...],
                        "items": [...],
                        "required_count": 1
                    }
                }
            }
        }
        """
        total_plans = len(previas_data)
        processed_courses = 0
        
        for idx, (carrera_plan, courses) in enumerate(previas_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_plans}] Procesando plan: {carrera_plan}')
            
            carrera_nombre, anio = self.parse_carrera_plan(carrera_plan)
            if not carrera_nombre or not anio:
                continue
            
            # Obtener plan
            try:
                plan = self.get_or_create_plan(carrera_nombre, anio)
            except Exception as e:
                error_msg = f"Error obteniendo plan para {carrera_plan}: {str(e)}"
                self.add_error(
                    'previas_plan',
                    carrera_plan,
                    str(e),
                    full_message=error_msg,
                    context={'carrera_plan': carrera_plan}
                )
                continue
            
            # Procesar cada curso del plan
            for course_key, course_data in courses.items():
                try:
                    self._process_course_previas(plan, course_key, course_data)
                    processed_courses += 1
                except Exception as e:
                    error_msg = f"Error procesando previas para {course_key}: {str(e)}"
                    self.add_error(
                        'previas_curso',
                        f"{carrera_plan} - {course_key}",
                        str(e),
                        full_message=error_msg,
                        context={'carrera_plan': carrera_plan, 'course_key': course_key}
                    )
                    if self.verbose:
                        self.stdout.write(
                            self.style.ERROR(f'       ❌ Error en {course_key}: {str(e)}')
                        )
        
        self.stdout.write(
            f'     ✅ {processed_courses} cursos procesados, '
            f'{self.stats["unidades_creadas"]} unidades creadas, '
            f'{self.stats["requisitos_nodos_creados"]} nodos de requisitos creados'
        )
    
    def _process_course_previas(self, plan: PlanEstudio, course_key: str, course_data: Dict):
        """Procesar las previas de un curso específico."""
        course_code = course_data.get('code', '').strip()
        course_name = course_data.get('name', '').strip()
        requirements = course_data.get('requirements')
        
        if not course_code or not requirements:
            return
        
        # Buscar o crear PlanMateria
        try:
            # Extraer código de materia (puede ser "CODIGO - NOMBRE" o solo "CODIGO")
            materia_codigo = course_code.split(' - ')[0].strip() if ' - ' in course_code else course_code
            
            materia = Materia.objects.filter(codigo=materia_codigo).first()
            if not materia:
                error_msg = f"Materia {materia_codigo} no encontrada, saltando previas"
                self.add_error(
                    'previas_materia_no_encontrada',
                    f"{plan} - {course_code}",
                    error_msg,
                    context={'plan': str(plan), 'course_code': course_code, 'materia_codigo': materia_codigo}
                )
                if self.verbose:
                    self.stdout.write(self.style.WARNING(f'       ⚠️  {error_msg}'))
                return
            
            plan_materia, _ = PlanMateria.objects.get_or_create(
                plan=plan,
                materia=materia
            )
        except Exception as e:
            error_msg = f"No se pudo obtener PlanMateria para {course_code}: {str(e)}"
            self.add_error(
                'previas_plan_materia',
                f"{plan} - {course_code}",
                str(e),
                full_message=error_msg,
                context={'plan': str(plan), 'course_code': course_code}
            )
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Crear UnidadAprobable para este curso
        try:
            unidad_tipo = self._map_name_to_tipo(course_name)
            unidad = self._get_or_create_unidad(
                materia=materia,
                tipo=unidad_tipo,
                codigo_bedelias=course_code,
                nombre=course_name
            )
        except Exception as e:
            error_msg = f"Error creando UnidadAprobable para {course_code}: {str(e)}"
            self.add_error(
                'previas_unidad',
                f"{plan} - {course_code}",
                str(e),
                full_message=error_msg,
                context={'plan': str(plan), 'course_code': course_code, 'course_name': course_name}
            )
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Procesar árbol de requisitos
        if requirements:
            try:
                self._process_requirements_tree(plan_materia, requirements, parent_nodo=None)
            except Exception as e:
                error_msg = f"Error procesando árbol de requisitos para {course_code}: {str(e)}"
                self.add_error(
                    'previas_arbol',
                    f"{plan} - {course_code}",
                    str(e),
                    full_message=error_msg,
                    context={'plan': str(plan), 'course_code': course_code, 'requirements': str(requirements)[:200]}
                )
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
    
    def _map_name_to_tipo(self, name: str) -> UnidadAprobable.Tipo:
        """Mapear nombre a tipo de UnidadAprobable."""
        name_lower = name.lower()
        if 'examen' in name_lower:
            return UnidadAprobable.Tipo.EXAMEN
        elif 'curso' in name_lower:
            return UnidadAprobable.Tipo.CURSO
        elif 'ucb' in name_lower or 'módulo' in name_lower:
            return UnidadAprobable.Tipo.UCB
        else:
            return UnidadAprobable.Tipo.OTRO
    
    def _get_or_create_unidad(self, materia: Materia, tipo: UnidadAprobable.Tipo, 
                              codigo_bedelias: str, nombre: str) -> UnidadAprobable:
        """Obtener o crear UnidadAprobable."""
        if self.dry_run:
            return UnidadAprobable(
                materia=materia,
                tipo=tipo,
                codigo_bedelias=codigo_bedelias,
                nombre=nombre
            )
        
        unidad, created = UnidadAprobable.objects.get_or_create(
            materia=materia,
            tipo=tipo,
            codigo_bedelias=codigo_bedelias,
            defaults={'nombre': nombre}
        )
        
        if created:
            self.stats['unidades_creadas'] += 1
        
        return unidad
    
    def _process_requirements_tree(self, plan_materia: PlanMateria, node_data: Dict, 
                                   parent_nodo: RequisitoNodo = None, orden: int = 0):
        """Procesar recursivamente el árbol de requisitos."""
        node_type = node_data.get('type', 'LEAF')
        title = node_data.get('title', '')
        required_count = node_data.get('required_count', 1)
        
        # Mapear tipo
        tipo_map = {
            'ALL': RequisitoNodo.Tipo.ALL,
            'ANY': RequisitoNodo.Tipo.ANY,
            'NOT': RequisitoNodo.Tipo.NOT,
            'LEAF': RequisitoNodo.Tipo.LEAF,
        }
        tipo = tipo_map.get(node_type, RequisitoNodo.Tipo.LEAF)
        
        # Crear nodo
        if self.dry_run:
            nodo = RequisitoNodo(
                plan_materia=plan_materia if parent_nodo is None else None,
                tipo=tipo,
                padre=parent_nodo,
                cantidad_minima=required_count if tipo == RequisitoNodo.Tipo.ANY else None,
                orden=orden,
                descripcion=title
            )
        else:
            # Buscar nodo existente o crear uno nuevo
            # Usar filtros para encontrar nodos similares
            filters = {
                'tipo': tipo,
                'padre': parent_nodo,
            }
            if parent_nodo is None:
                filters['plan_materia'] = plan_materia
            else:
                filters['plan_materia__isnull'] = True
            
            nodo = RequisitoNodo.objects.filter(**filters).first()
            
            if not nodo:
                nodo = RequisitoNodo.objects.create(
                    plan_materia=plan_materia if parent_nodo is None else None,
                    tipo=tipo,
                    padre=parent_nodo,
                    cantidad_minima=required_count if tipo == RequisitoNodo.Tipo.ANY else None,
                    orden=orden,
                    descripcion=title
                )
                self.stats['requisitos_nodos_creados'] += 1
            else:
                # Actualizar si es necesario
                updated = False
                if nodo.descripcion != title and title:
                    nodo.descripcion = title
                    updated = True
                if nodo.orden != orden:
                    nodo.orden = orden
                    updated = True
                if tipo == RequisitoNodo.Tipo.ANY and nodo.cantidad_minima != required_count:
                    nodo.cantidad_minima = required_count
                    updated = True
                if updated:
                    nodo.save()
        
        # Si es LEAF, procesar items
        if node_type == 'LEAF':
            items = node_data.get('items', [])
            for item_idx, item_data in enumerate(items):
                try:
                    self._process_requisito_item(nodo, item_data, item_idx)
                except Exception as e:
                    error_msg = f"Error procesando item de requisito: {str(e)}"
                    self.add_error(
                        'previas_item',
                        f"{plan_materia} - item {item_idx}",
                        str(e),
                        full_message=error_msg,
                        context={'plan_materia': str(plan_materia), 'item_idx': item_idx, 'item_data': str(item_data)[:200]}
                    )
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
        
        # Procesar hijos recursivamente
        children = node_data.get('children', [])
        for child_idx, child_data in enumerate(children):
            try:
                self._process_requirements_tree(plan_materia, child_data, parent_nodo=nodo, orden=child_idx)
            except Exception as e:
                error_msg = f"Error procesando nodo hijo: {str(e)}"
                self.add_error(
                    'previas_nodo_hijo',
                    f"{plan_materia} - hijo {child_idx}",
                    str(e),
                    full_message=error_msg,
                    context={'plan_materia': str(plan_materia), 'child_idx': child_idx, 'child_data': str(child_data)[:200]}
                )
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
    
    def _process_requisito_item(self, nodo: RequisitoNodo, item_data: Dict, orden: int):
        """Procesar un item de requisito (LEAF)."""
        modality = item_data.get('modality', '')
        code = item_data.get('code', '').strip()
        title = item_data.get('title', '').strip()
        raw = item_data.get('raw', '')
        
        # Determinar tipo de item
        if modality in ['ucb_module', 'course', 'exam', 'course_enrollment']:
            try:
                # Buscar materia y crear unidad
                materia = Materia.objects.filter(codigo=code).first()
                if materia:
                    # Determinar tipo de unidad
                    if modality == 'ucb_module':
                        unidad_tipo = UnidadAprobable.Tipo.UCB
                    elif modality in ['exam', 'course_enrollment']:
                        unidad_tipo = UnidadAprobable.Tipo.EXAMEN
                    else:
                        unidad_tipo = UnidadAprobable.Tipo.CURSO
                    
                    unidad = self._get_or_create_unidad(
                        materia=materia,
                        tipo=unidad_tipo,
                        codigo_bedelias=code,
                        nombre=title
                    )
                    
                    # Crear RequisitoItem de tipo UNIDAD
                    if self.dry_run:
                        item = RequisitoItem(
                            nodo=nodo,
                            tipo=RequisitoItem.TipoItem.UNIDAD,
                            unidad_requerida=unidad,
                            orden=orden
                        )
                    else:
                        item, created = RequisitoItem.objects.get_or_create(
                            nodo=nodo,
                            tipo=RequisitoItem.TipoItem.UNIDAD,
                            unidad_requerida=unidad,
                            defaults={'orden': orden}
                        )
                        if created:
                            self.stats['requisitos_items_creados'] += 1
                    return
            except Exception as e:
                # Si falla al crear como UNIDAD, continuar y crear como TEXTO
                if self.verbose:
                    self.stdout.write(
                        self.style.WARNING(f'       ⚠️  Error creando item UNIDAD para {code}: {str(e)}, usando TEXTO')
                    )
        
        # Si no se pudo crear como UNIDAD, crear como TEXTO
        try:
            texto = raw or title or f"{code} - {title}"
            if self.dry_run:
                item = RequisitoItem(
                    nodo=nodo,
                    tipo=RequisitoItem.TipoItem.TEXTO,
                    texto=texto,
                    orden=orden
                )
            else:
                item, created = RequisitoItem.objects.get_or_create(
                    nodo=nodo,
                    tipo=RequisitoItem.TipoItem.TEXTO,
                    texto=texto,
                    defaults={'orden': orden}
                )
                if created:
                    self.stats['requisitos_items_creados'] += 1
        except Exception as e:
            # Re-raise para que se capture en el nivel superior
            error_msg = f"Error creando RequisitoItem TEXTO: {str(e)}"
            raise Exception(error_msg)
    
    def process_posprevias(self, posprevias_data: Dict):
        """
        Procesar posprevias (requisitos inversos) desde posprevias_data.
        
        Posprevias muestran qué cursos requieren este curso como prerrequisito.
        Esto se usa para validar y completar los datos de previas.
        
        Estructura esperada:
        {
            "CARRERA_ANIO": {
                "CODIGO": {
                    "code": "CODIGO",
                    "name": "NOMBRE",
                    "posprevias": [
                        {
                            "anio_plan": "1997",
                            "carrera": "INGENIERIA CIVIL",
                            "fecha": "01/01/1997",
                            "descripcion": "...",
                            "tipo": "Curso" | "Examen",
                            "materia_codigo": "2311",
                            "materia_nombre": "...",
                            "materia_full": "2311-..."
                        }
                    ]
                }
            }
        }
        """
        total_plans = len(posprevias_data)
        processed_courses = 0
        
        for idx, (carrera_plan, courses) in enumerate(posprevias_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_plans}] Procesando plan: {carrera_plan}')
            
            carrera_nombre, anio = self.parse_carrera_plan(carrera_plan)
            if not carrera_nombre or not anio:
                continue
            
            # Obtener plan
            try:
                plan = self.get_or_create_plan(carrera_nombre, anio)
            except Exception as e:
                self.stats['errors'] += 1
                self.error_list.append({
                    'type': 'posprevias_plan',
                    'item': carrera_plan,
                    'message': str(e),
                    'full_message': f"Error obteniendo plan para {carrera_plan}: {str(e)}"
                })
                continue
            
            # Procesar cada curso del plan
            for course_code, course_data in courses.items():
                try:
                    posprevias = course_data.get('posprevias', [])
                    if not posprevias:
                        continue
                    
                    self._process_course_posprevias(plan, course_code, course_data, posprevias)
                    processed_courses += 1
                    self.stats['posprevias_procesadas'] += len(posprevias)
                except Exception as e:
                    self.stats['errors'] += 1
                    self.error_list.append({
                        'type': 'posprevias_curso',
                        'item': f"{carrera_plan} - {course_code}",
                        'message': str(e),
                        'full_message': f"Error procesando posprevias para {course_code}: {str(e)}"
                    })
                    if self.verbose:
                        self.stdout.write(
                            self.style.ERROR(f'       ❌ Error en {course_code}: {str(e)}')
                        )
        
        self.stdout.write(
            f'     ✅ {processed_courses} cursos procesados, '
            f'{self.stats["posprevias_procesadas"]} posprevias encontradas, '
            f'{self.stats["posprevias_validadas"]} relaciones validadas/creadas'
        )
    
    def _process_course_posprevias(self, source_plan: PlanEstudio, source_course_code: str, 
                                   course_data: Dict, posprevias: list):
        """
        Procesar posprevias de un curso.
        
        Para cada posprevia, valida que existe la relación de requisito correspondiente.
        Si no existe, intenta crearla.
        """
        # Buscar materia fuente
        materia_fuente = Materia.objects.filter(codigo=source_course_code).first()
        if not materia_fuente:
            error_msg = f"Materia fuente {source_course_code} no encontrada"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_materia_fuente',
                'item': f"{source_plan} - {source_course_code}",
                'message': error_msg,
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.WARNING(f'       ⚠️  {error_msg}'))
            return
        
        # Obtener o crear PlanMateria fuente
        try:
            plan_materia_fuente, _ = PlanMateria.objects.get_or_create(
                plan=source_plan,
                materia=materia_fuente
            )
        except Exception as e:
            error_msg = f"Error obteniendo PlanMateria fuente para {source_course_code}: {str(e)}"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_plan_materia_fuente',
                'item': f"{source_plan} - {source_course_code}",
                'message': str(e),
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Crear UnidadAprobable para la materia fuente si no existe
        try:
            course_name = course_data.get('name', '')
            unidad_tipo = self._map_name_to_tipo(course_name)
            unidad_fuente = self._get_or_create_unidad(
                materia=materia_fuente,
                tipo=unidad_tipo,
                codigo_bedelias=source_course_code,
                nombre=course_name
            )
        except Exception as e:
            error_msg = f"Error creando UnidadAprobable fuente para {source_course_code}: {str(e)}"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_unidad_fuente',
                'item': f"{source_plan} - {source_course_code}",
                'message': str(e),
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Procesar cada posprevia
        for posprevia in posprevias:
            try:
                self._validate_or_create_posprevia_relationship(
                    plan_materia_fuente,
                    unidad_fuente,
                    posprevia
                )
                self.stats['posprevias_validadas'] += 1
            except Exception as e:
                error_msg = f"Error validando posprevia: {str(e)}"
                self.stats['errors'] += 1
                self.error_list.append({
                    'type': 'posprevias_validacion',
                    'item': f"{source_course_code} -> {posprevia.get('materia_codigo', '?')}",
                    'message': str(e),
                    'full_message': error_msg
                })
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
    
    def _validate_or_create_posprevia_relationship(self, plan_materia_fuente: PlanMateria,
                                                   unidad_fuente: UnidadAprobable,
                                                   posprevia: Dict):
        """
        Validar o crear la relación de requisito inversa.
        
        Si curso A tiene posprevia B, entonces curso B debe tener previa A.
        """
        carrera_nombre = posprevia.get('carrera', '').strip()
        anio_plan = posprevia.get('anio_plan', '').strip()
        materia_codigo = posprevia.get('materia_codigo', '').strip()
        materia_nombre = posprevia.get('materia_nombre', '').strip()
        tipo = posprevia.get('tipo', '').strip()
        
        if not carrera_nombre or not anio_plan or not materia_codigo:
            return
        
        # Buscar plan destino usando comparación sin acentos
        # Intentar encontrar el plan exacto primero
        plan_destino = self.find_plan_by_carrera_name(carrera_nombre, anio_plan)
        
        # Si no se encuentra el plan exacto, intentar encontrar cualquier plan de esa carrera
        # (útil cuando los datos de posprevias referencian planes antiguos que no existen)
        if not plan_destino:
            # Buscar por nombre de carrera normalizado
            nombre_normalized = self.normalize_string(carrera_nombre)
            for plan in PlanEstudio.objects.all():
                if self.normalize_string(plan.nombre_carrera) == nombre_normalized:
                    plan_destino = plan
                    break
            
            # Si aún no se encuentra, buscar cualquier plan con el nombre contenido
            if not plan_destino and len(nombre_normalized) >= 6:
                for plan in PlanEstudio.objects.all():
                    plan_normalized = self.normalize_string(plan.nombre_carrera)
                    if nombre_normalized in plan_normalized or plan_normalized in nombre_normalized:
                        plan_destino = plan
                        break
            
            # Si aún no se encuentra, tomar el más reciente de cualquier carrera con nombre similar
            if not plan_destino:
                plan_destino = PlanEstudio.objects.filter(
                    nombre_carrera__icontains=carrera_nombre[:20] if len(carrera_nombre) > 20 else carrera_nombre
                ).order_by('-anio').first()
        
        if not plan_destino:
            error_msg = f"Plan destino {carrera_nombre} {anio_plan} no encontrado (ni ningún otro plan para esa carrera)"
            self.add_error(
                'posprevias_plan_destino',
                f"{unidad_fuente.materia.codigo} -> {materia_codigo} ({carrera_nombre} {anio_plan})",
                error_msg,
                context={'carrera_nombre': carrera_nombre, 'anio_plan': anio_plan, 'materia_codigo': materia_codigo}
            )
            if self.verbose:
                self.stdout.write(self.style.WARNING(f'       ⚠️  {error_msg}'))
            return
        
        # Si usamos un plan diferente al solicitado, registrar una advertencia
        if plan_destino.anio != anio_plan:
            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(
                        f'       ⚠️  Plan {carrera_nombre} {anio_plan} no encontrado, '
                        f'usando plan {plan_destino.anio} en su lugar'
                    )
                )
        
        # Buscar materia destino
        materia_destino = Materia.objects.filter(codigo=materia_codigo).first()
        if not materia_destino:
            error_msg = f"Materia destino {materia_codigo} no encontrada"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_materia_destino',
                'item': f"{unidad_fuente.materia.codigo} -> {materia_codigo}",
                'message': error_msg,
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.WARNING(f'       ⚠️  {error_msg}'))
            return
        
        # Obtener o crear PlanMateria destino
        try:
            plan_materia_destino, _ = PlanMateria.objects.get_or_create(
                plan=plan_destino,
                materia=materia_destino
            )
        except Exception as e:
            error_msg = f"Error obteniendo PlanMateria destino: {str(e)}"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_plan_materia_destino',
                'item': f"{unidad_fuente.materia.codigo} -> {materia_codigo}",
                'message': str(e),
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Crear UnidadAprobable destino si no existe
        try:
            unidad_tipo_destino = UnidadAprobable.Tipo.CURSO if 'curso' in tipo.lower() else UnidadAprobable.Tipo.EXAMEN
            unidad_destino = self._get_or_create_unidad(
                materia=materia_destino,
                tipo=unidad_tipo_destino,
                codigo_bedelias=materia_codigo,
                nombre=materia_nombre
            )
        except Exception as e:
            error_msg = f"Error creando UnidadAprobable destino: {str(e)}"
            self.stats['errors'] += 1
            self.error_list.append({
                'type': 'posprevias_unidad_destino',
                'item': f"{unidad_fuente.materia.codigo} -> {materia_codigo}",
                'message': str(e),
                'full_message': error_msg
            })
            if self.verbose:
                self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
            return
        
        # Verificar si ya existe la relación de requisito
        # Buscar si plan_materia_destino tiene un RequisitoNodo raíz que requiera unidad_fuente
        root_nodos = RequisitoNodo.objects.filter(
            plan_materia=plan_materia_destino,
            padre__isnull=True
        )
        
        # Buscar en los items de requisitos si ya existe la relación
        found = False
        for root_nodo in root_nodos:
            # Buscar recursivamente en el árbol
            if self._check_unidad_in_tree(root_nodo, unidad_fuente):
                found = True
                break
        
        # Si no existe, crear la relación
        if not found and not self.dry_run:
            try:
                # Crear un nodo LEAF con el requisito
                leaf_nodo = RequisitoNodo.objects.create(
                    plan_materia=None,  # No es raíz
                    tipo=RequisitoNodo.Tipo.LEAF,
                    padre=None,  # Se conectará al root
                    descripcion=f"Requisito validado desde posprevias"
                )
                self.stats['requisitos_nodos_creados'] += 1
                
                # Si no hay root, crear uno
                if not root_nodos.exists():
                    root_nodo = RequisitoNodo.objects.create(
                        plan_materia=plan_materia_destino,
                        tipo=RequisitoNodo.Tipo.ALL,
                        padre=None,
                        descripcion="Requisitos"
                    )
                    self.stats['requisitos_nodos_creados'] += 1
                else:
                    root_nodo = root_nodos.first()
                
                # Conectar leaf al root
                leaf_nodo.padre = root_nodo
                leaf_nodo.save()
                
                # Crear RequisitoItem
                RequisitoItem.objects.create(
                    nodo=leaf_nodo,
                    tipo=RequisitoItem.TipoItem.UNIDAD,
                    unidad_requerida=unidad_fuente,
                    orden=0
                )
                self.stats['requisitos_items_creados'] += 1
                
                if self.verbose:
                    self.stdout.write(
                        f'       ✨ Creada relación: {materia_destino.codigo} requiere {unidad_fuente.materia.codigo}'
                    )
            except Exception as e:
                error_msg = f"Error creando relación de requisito desde posprevias: {str(e)}"
                self.stats['errors'] += 1
                self.error_list.append({
                    'type': 'posprevias_crear_relacion',
                    'item': f"{materia_destino.codigo} -> {unidad_fuente.materia.codigo}",
                    'message': str(e),
                    'full_message': error_msg
                })
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'       ❌ {error_msg}'))
                raise  # Re-raise para que se capture en el nivel superior
    
    def _check_unidad_in_tree(self, nodo: RequisitoNodo, unidad: UnidadAprobable) -> bool:
        """Verificar recursivamente si una unidad está en el árbol de requisitos."""
        if nodo.tipo == RequisitoNodo.Tipo.LEAF:
            # Verificar items
            items = RequisitoItem.objects.filter(nodo=nodo, unidad_requerida=unidad)
            if items.exists():
                return True
        
        # Verificar hijos recursivamente
        for hijo in nodo.hijos.all():
            if self._check_unidad_in_tree(hijo, unidad):
                return True
        
        return False
    
    def print_stats(self):
        """Imprimir estadísticas finales."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('📊 ESTADÍSTICAS FINALES'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'📋 Planes de estudio creados:   {self.stats["planes_creados"]}')
        self.stdout.write(f'🔗 Relaciones plan-materia:     {self.stats["plan_materias_creadas"]}')
        self.stdout.write(f'📚 Materias totales procesadas: {self.stats["materias_totales"]}')
        self.stdout.write(f'✨ Materias creadas:            {self.stats["materias_creadas"]}')
        self.stdout.write(f'🔄 Materias actualizadas:        {self.stats["materias_actualizadas"]}')
        self.stdout.write(f'✅ Materias marcadas como activas: {self.stats["materias_marcadas_activas"]}')
        self.stdout.write(f'📦 Unidades aprobables creadas:   {self.stats["unidades_creadas"]}')
        self.stdout.write(f'🌳 Nodos de requisitos creados:  {self.stats["requisitos_nodos_creados"]}')
        self.stdout.write(f'📝 Items de requisitos creados:  {self.stats["requisitos_items_creados"]}')
        self.stdout.write(f'🔄 Posprevias procesadas:         {self.stats["posprevias_procesadas"]}')
        self.stdout.write(f'✅ Posprevias validadas:          {self.stats["posprevias_validadas"]}')
        
        if not self.dry_run:
            # Contar en la base de datos
            planes_count = PlanEstudio.objects.count()
            plan_materias_count = PlanMateria.objects.count()
            materias_activas = Materia.objects.filter(activo=True).count()
            materias_inactivas = Materia.objects.filter(activo=False).count()
            unidades_count = UnidadAprobable.objects.count()
            requisitos_nodos_count = RequisitoNodo.objects.count()
            requisitos_items_count = RequisitoItem.objects.count()
            
            self.stdout.write('')
            self.stdout.write('   En base de datos:')
            self.stdout.write(f'   📋 Planes:                  {planes_count}')
            self.stdout.write(f'   🔗 Plan-Materias:           {plan_materias_count}')
            self.stdout.write(f'   ✅ Materias activas:         {materias_activas}')
            self.stdout.write(f'   📜 Materias inactivas:      {materias_inactivas}')
            self.stdout.write(f'   📦 Unidades aprobables:      {unidades_count}')
            self.stdout.write(f'   🌳 Nodos de requisitos:     {requisitos_nodos_count}')
            self.stdout.write(f'   📝 Items de requisitos:     {requisitos_items_count}')
            self.stdout.write(f'   🔄 Posprevias procesadas:   {self.stats["posprevias_procesadas"]}')
        
        if self.stats['errors'] > 0:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'❌ Errores encontrados:     {self.stats["errors"]}'))
            self.stdout.write('')
            self.print_error_details()
        
        self.stdout.write('=' * 70 + '\n')
    
    def print_error_details(self):
        """Mostrar detalles de los errores encontrados."""
        if not self.error_list:
            return
        
        self.stdout.write(self.style.WARNING('📋 DETALLES DE ERRORES:'))
        self.stdout.write('-' * 70)
        
        # Agrupar errores por tipo
        errors_by_type = {}
        for error in self.error_list:
            error_type = error['type']
            if error_type not in errors_by_type:
                errors_by_type[error_type] = []
            errors_by_type[error_type].append(error)
        
        # Contar total de tipos de errores únicos
        all_error_messages = set()
        
        # Mostrar resumen por tipo
        for error_type, errors in errors_by_type.items():
            self.stdout.write(f'\n🔸 Errores de tipo "{error_type}": {len(errors)}')
            
            # Agrupar por mensaje de error (errores similares)
            errors_by_message = {}
            for error in errors:
                msg = error['message']
                all_error_messages.add(msg)
                if msg not in errors_by_message:
                    errors_by_message[msg] = []
                errors_by_message[msg].append(error['item'])
            
            # Mostrar cada tipo de error con ejemplos
            for msg, items in list(errors_by_message.items())[:10]:  # Máximo 10 tipos diferentes
                items_count = len(items)
                examples = items[:3]  # Primeros 3 ejemplos
                examples_str = ', '.join(examples)
                if items_count > 3:
                    examples_str += f' ... y {items_count - 3} más'
                
                self.stdout.write(f'   ❌ {msg}')
                self.stdout.write(f'      Afecta: {examples_str}')
                if items_count > 3:
                    self.stdout.write(f'      (Total: {items_count} items afectados)')
            
            # Si hay más de 10 tipos de errores en este tipo, mostrar advertencia
            if len(errors_by_message) > 10:
                self.stdout.write(f'   ⚠️  Hay {len(errors_by_message)} tipos diferentes de errores en esta categoría.')
        
        # Si hay muchos tipos de errores únicos, mostrar advertencia general
        if len(all_error_messages) > 10:
            self.stdout.write(f'\n⚠️  Hay {len(all_error_messages)} tipos diferentes de errores en total. Use --verbose para ver todos los detalles.')
        
        # Mostrar los primeros 5 errores completos como ejemplos
        self.stdout.write('\n📝 Primeros errores detallados:')
        for error in self.error_list[:5]:
            self.stdout.write(f'   • [{error["type"]}] {error["item"]}: {error["message"]}')
        
        if len(self.error_list) > 5:
            self.stdout.write(f'   ... y {len(self.error_list) - 5} errores más')
            self.stdout.write('   Use --verbose para ver todos los errores durante el procesamiento.')
        
        self.stdout.write('-' * 70)
    
    def export_errors_to_json(self, file_path: Path):
        """
        Exportar errores a un archivo JSON estructurado.
        
        Args:
            file_path: Ruta del archivo JSON donde guardar los errores
        """
        try:
            # Agrupar errores por tipo para análisis
            errors_by_type = defaultdict(list)
            for error in self.error_list:
                errors_by_type[error['type']].append(error)
            
            # Agrupar por mensaje dentro de cada tipo
            errors_summary = {}
            for error_type, errors in errors_by_type.items():
                errors_by_message = defaultdict(list)
                for error in errors:
                    # Manejar tanto formato nuevo como antiguo
                    item_data = {
                        'item': error['item'],
                        'timestamp': error.get('timestamp', 'N/A'),
                        'stage': error.get('stage', 'unknown'),
                        'context': error.get('context', {})
                    }
                    errors_by_message[error['message']].append(item_data)
                
                errors_summary[error_type] = {
                    'total_count': len(errors),
                    'unique_messages': len(errors_by_message),
                    'errors_by_message': {
                        msg: {
                            'count': len(items),
                            'items': items[:10],  # Primeros 10 items como ejemplos
                            'total_items': len(items)
                        }
                        for msg, items in errors_by_message.items()
                    }
                }
            
            # Crear estructura completa del reporte
            report = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_errors': len(self.error_list),
                    'unique_error_types': len(errors_by_type),
                    'dry_run': self.dry_run,
                    'stats': self.stats
                },
                'summary': errors_summary,
                'all_errors': self.error_list  # Lista completa de todos los errores
            }
            
            # Asegurar que el directorio existe
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Escribir archivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n📄 Errores exportados a JSON: {file_path.absolute()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al exportar errores a JSON: {e}')
            )
    
    def export_errors_to_text(self, file_path: Path):
        """
        Exportar errores a un archivo de texto legible.
        
        Args:
            file_path: Ruta del archivo de texto donde guardar los errores
        """
        try:
            # Asegurar que el directorio existe
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('=' * 80 + '\n')
                f.write('REPORTE DE ERRORES - CARGA DE DATOS BEDELIA\n')
                f.write('=' * 80 + '\n')
                f.write(f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                f.write(f'Total de errores: {len(self.error_list)}\n')
                f.write(f'Modo dry-run: {"Sí" if self.dry_run else "No"}\n')
                f.write('=' * 80 + '\n\n')
                
                # Estadísticas
                f.write('ESTADÍSTICAS\n')
                f.write('-' * 80 + '\n')
                for key, value in self.stats.items():
                    f.write(f'{key}: {value}\n')
                f.write('\n')
                
                # Agrupar errores por tipo
                errors_by_type = defaultdict(list)
                for error in self.error_list:
                    errors_by_type[error['type']].append(error)
                
                # Resumen por tipo
                f.write('RESUMEN POR TIPO DE ERROR\n')
                f.write('=' * 80 + '\n')
                for error_type, errors in sorted(errors_by_type.items()):
                    f.write(f'\n[{error_type}] Total: {len(errors)} errores\n')
                    f.write('-' * 80 + '\n')
                    
                    # Agrupar por mensaje
                    errors_by_message = defaultdict(list)
                    for error in errors:
                        errors_by_message[error['message']].append(error)
                    
                    for msg, items in sorted(errors_by_message.items(), key=lambda x: len(x[1]), reverse=True):
                        f.write(f'\n  Mensaje: {msg}\n')
                        f.write(f'  Cantidad: {len(items)} items afectados\n')
                        f.write(f'  Ejemplos (primeros 5):\n')
                        for item in items[:5]:
                            f.write(f'    - {item["item"]}\n')
                        if len(items) > 5:
                            f.write(f'    ... y {len(items) - 5} más\n')
                
                # Lista completa de errores
                f.write('\n\n' + '=' * 80 + '\n')
                f.write('LISTA COMPLETA DE ERRORES\n')
                f.write('=' * 80 + '\n')
                for idx, error in enumerate(self.error_list, 1):
                    f.write(f'\n[{idx}] {error["type"]}\n')
                    f.write(f'  Item: {error["item"]}\n')
                    f.write(f'  Mensaje: {error["message"]}\n')
                    f.write(f'  Etapa: {error["stage"]}\n')
                    f.write(f'  Timestamp: {error["timestamp"]}\n')
                    if error.get('context'):
                        f.write(f'  Contexto: {json.dumps(error["context"], ensure_ascii=False, indent=4)}\n')
                    if error.get('full_message') != error.get('message'):
                        f.write(f'  Mensaje completo: {error["full_message"]}\n')
                    f.write('-' * 80 + '\n')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'📄 Errores exportados a texto: {file_path.absolute()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al exportar errores a texto: {e}')
            )
