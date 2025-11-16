"""
Comando de Django para cargar datos de Bedelia desde archivos JSON a la base de datos.

Este comando importa los archivos JSON de la carpeta data/:
- credits_data_backup.json: Carreras, planes de estudio, materias y relaciones plan-materia
- vigentes_data_backup.json: Cursos vigentes (para marcar materias como activas)

El comando procesa los datos en el siguiente orden:
1. Extrae y crea carreras únicas desde las claves "CARRERA_ANIO"
2. Extrae y crea planes de estudio (carrera + año)
3. Extrae y crea materias únicas (deduplicadas por código)
4. Crea relaciones PlanMateria (qué materias están en cada plan)
5. Marca materias como activas según vigentes_data

Uso:
    python manage.py load_bedelia_data
    python manage.py load_bedelia_data --dry-run
    python manage.py load_bedelia_data --verbose
    python manage.py load_bedelia_data --clear
    python manage.py load_bedelia_data --credits ../data/credits_data_backup.json --vigentes ../data/vigentes_data_backup.json
"""
import json
from pathlib import Path
from typing import Dict, Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Carrera, Materia, PlanEstudio, PlanMateria


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = False
        self.dry_run = False
        
        # Estadísticas
        self.stats = {
            'carreras_creadas': 0,
            'planes_creados': 0,
            'plan_materias_creadas': 0,
            'materias_creadas': 0,
            'materias_actualizadas': 0,
            'materias_marcadas_activas': 0,
            'materias_totales': 0,
            'errors': 0,
        }
        
        # Cachés para evitar consultas repetidas
        self.carrera_cache: Dict[str, Carrera] = {}
        self.plan_cache: Dict[str, PlanEstudio] = {}
        self.materia_cache: Dict[str, Materia] = {}
    
    def handle(self, *args, **options):
        """Punto de entrada principal del comando."""
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔄 Modo DRY RUN - No se guardará nada en la base de datos'))
        
        # Verificar archivos
        credits_path = Path(options['credits'])
        vigentes_path = Path(options['vigentes'])
        
        if not credits_path.exists():
            raise CommandError(f'❌ Archivo no encontrado: {credits_path}')
        
        if not vigentes_path.exists():
            raise CommandError(f'❌ Archivo no encontrado: {vigentes_path}')
        
        try:
            with transaction.atomic():
                # Limpiar base de datos si se solicita
                if options['clear']:
                    self.clear_database()
                
                # Cargar datos
                self.stdout.write('📖 Cargando archivos JSON...')
                credits_data = self.load_json(credits_path)
                vigentes_data = self.load_json(vigentes_path)
                
                # Paso 1: Crear carreras y planes de estudio
                self.stdout.write('🎓 Procesando carreras y planes de estudio desde credits_data...')
                self.process_carreras_y_planes(credits_data)
                
                # Paso 2: Extraer y crear materias desde credits
                self.stdout.write('📚 Procesando materias desde credits_data...')
                self.process_materias(credits_data)
                
                # Paso 3: Crear relaciones PlanMateria
                self.stdout.write('🔗 Creando relaciones plan-materia...')
                self.process_plan_materias(credits_data)
                
                # Paso 4: Marcar materias activas desde vigentes
                self.stdout.write('✅ Marcando materias activas desde vigentes_data...')
                self.mark_active_materias(vigentes_data)
                
                # Si es dry-run, hacer rollback
                if self.dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING('🔙 Rollback aplicado (dry-run)'))
            
            # Mostrar estadísticas
            self.print_stats()
            
            if not self.dry_run:
                self.stdout.write(self.style.SUCCESS('✅ Datos cargados exitosamente!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()
            raise
    
    def clear_database(self):
        """Limpiar todas las carreras, planes y materias de la base de datos."""
        self.stdout.write(self.style.WARNING('🗑️  Limpiando base de datos...'))
        
        if not self.dry_run:
            plan_materias_count = PlanMateria.objects.count()
            PlanMateria.objects.all().delete()
            
            planes_count = PlanEstudio.objects.count()
            PlanEstudio.objects.all().delete()
            
            materias_count = Materia.objects.count()
            Materia.objects.all().delete()
            
            carreras_count = Carrera.objects.count()
            Carrera.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ {plan_materias_count} plan-materias, {planes_count} planes, '
                f'{materias_count} materias, {carreras_count} carreras eliminadas'
            ))
        else:
            plan_materias_count = PlanMateria.objects.count()
            planes_count = PlanEstudio.objects.count()
            materias_count = Materia.objects.count()
            carreras_count = Carrera.objects.count()
            self.stdout.write(self.style.SUCCESS(
                f'✅ {plan_materias_count} plan-materias, {planes_count} planes, '
                f'{materias_count} materias, {carreras_count} carreras serían eliminadas (dry-run)'
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
    
    def get_or_create_carrera(self, nombre: str) -> Carrera:
        """Obtener o crear una carrera."""
        if nombre in self.carrera_cache:
            return self.carrera_cache[nombre]
        
        if self.dry_run:
            carrera = Carrera(nombre=nombre)
        else:
            carrera, created = Carrera.objects.get_or_create(
                nombre=nombre,
                defaults={}
            )
            if created:
                self.stats['carreras_creadas'] += 1
                if self.verbose:
                    self.stdout.write(f'       ✨ Nueva carrera: {nombre}')
        
        self.carrera_cache[nombre] = carrera
        return carrera
    
    def get_or_create_plan(self, carrera: Carrera, anio: str) -> PlanEstudio:
        """Obtener o crear un plan de estudio."""
        cache_key = f"{carrera.nombre}_{anio}"
        
        if cache_key in self.plan_cache:
            return self.plan_cache[cache_key]
        
        if self.dry_run:
            plan = PlanEstudio(carrera=carrera, anio=anio)
        else:
            plan, created = PlanEstudio.objects.get_or_create(
                carrera=carrera,
                anio=anio,
                defaults={}
            )
            if created:
                self.stats['planes_creados'] += 1
                if self.verbose:
                    self.stdout.write(f'       ✨ Nuevo plan: {carrera.nombre} - {anio}')
        
        self.plan_cache[cache_key] = plan
        return plan
    
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
        Procesar carreras y planes de estudio desde credits_data.
        
        Extrae carreras y planes únicos de las claves "CARRERA_ANIO".
        """
        carreras_set: Set[str] = set()
        planes_set: Set[tuple] = set()  # (carrera_nombre, anio)
        
        total_programs = len(credits_data)
        
        # Primera pasada: extraer carreras y planes únicos
        for idx, (carrera_plan, cursos) in enumerate(credits_data.items(), 1):
            if self.verbose and idx % 10 == 0:
                self.stdout.write(f'     [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            carrera_nombre, anio = self.parse_carrera_plan(carrera_plan)
            
            if carrera_nombre:
                carreras_set.add(carrera_nombre)
            if carrera_nombre and anio:
                planes_set.add((carrera_nombre, anio))
        
        self.stdout.write(f'     📊 {len(carreras_set)} carreras únicas encontradas')
        self.stdout.write(f'     📊 {len(planes_set)} planes únicos encontrados')
        
        # Crear carreras
        self.stdout.write('     💾 Guardando carreras en la base de datos...')
        for carrera_nombre in sorted(carreras_set):
            self.get_or_create_carrera(carrera_nombre)
        
        # Crear planes de estudio
        self.stdout.write('     💾 Guardando planes de estudio en la base de datos...')
        for carrera_nombre, anio in sorted(planes_set):
            carrera = self.get_or_create_carrera(carrera_nombre)
            self.get_or_create_plan(carrera, anio)
        
        self.stdout.write(
            f'     ✅ {self.stats["carreras_creadas"]} carreras creadas, '
            f'{self.stats["planes_creados"]} planes creados'
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
                self.stdout.write(
                    self.style.ERROR(f'       ❌ Error procesando {codigo}: {e}')
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
            
            # Obtener carrera y plan
            carrera = self.get_or_create_carrera(carrera_nombre)
            plan = self.get_or_create_plan(carrera, anio)
            
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
                            materia=materia,
                            defaults={
                                'obligatorio': True,
                            }
                        )
                        if created:
                            self.stats['plan_materias_creadas'] += 1
                            processed_relations += 1
                
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbose:
                        self.stdout.write(
                            self.style.ERROR(f'       ❌ Error creando relación {carrera_plan} - {codigo}: {e}')
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
    
    def print_stats(self):
        """Imprimir estadísticas finales."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('📊 ESTADÍSTICAS FINALES'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'🎓 Carreras creadas:            {self.stats["carreras_creadas"]}')
        self.stdout.write(f'📋 Planes de estudio creados:   {self.stats["planes_creados"]}')
        self.stdout.write(f'🔗 Relaciones plan-materia:     {self.stats["plan_materias_creadas"]}')
        self.stdout.write(f'📚 Materias totales procesadas: {self.stats["materias_totales"]}')
        self.stdout.write(f'✨ Materias creadas:            {self.stats["materias_creadas"]}')
        self.stdout.write(f'🔄 Materias actualizadas:        {self.stats["materias_actualizadas"]}')
        self.stdout.write(f'✅ Materias marcadas como activas: {self.stats["materias_marcadas_activas"]}')
        
        if not self.dry_run:
            # Contar en la base de datos
            carreras_count = Carrera.objects.count()
            planes_count = PlanEstudio.objects.count()
            plan_materias_count = PlanMateria.objects.count()
            materias_activas = Materia.objects.filter(activo=True).count()
            materias_inactivas = Materia.objects.filter(activo=False).count()
            
            self.stdout.write('')
            self.stdout.write('   En base de datos:')
            self.stdout.write(f'   🎓 Carreras:                 {carreras_count}')
            self.stdout.write(f'   📋 Planes:                  {planes_count}')
            self.stdout.write(f'   🔗 Plan-Materias:           {plan_materias_count}')
            self.stdout.write(f'   ✅ Materias activas:         {materias_activas}')
            self.stdout.write(f'   📜 Materias inactivas:      {materias_inactivas}')
        
        if self.stats['errors'] > 0:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'❌ Errores:                  {self.stats["errors"]}'))
        
        self.stdout.write('=' * 70 + '\n')
