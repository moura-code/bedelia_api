"""
Comando de Django para cargar datos de Bedelia desde archivos JSON a la base de datos.

Este comando importa los archivos JSON de la carpeta data/:
- vigentes_data_backup.json: Cursos vigentes
- credits_data_backup.json: Créditos de cursos
- previas_data_backup.json: Requisitos (estructura de árbol)
- posprevias_data_backup.json: Materias que dependen de un curso

Uso:
    python manage.py load_bedelia_data
    python manage.py load_bedelia_data --dry-run
    python manage.py load_bedelia_data --verbose
    python manage.py load_bedelia_data --clear
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import Carrera, Curso, Previa, ItemPrevia, Posprevia


class Command(BaseCommand):
    """Cargar datos de Bedelia desde archivos JSON."""
    
    help = 'Importar datos de cursos de Bedelia desde archivos JSON'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--vigentes',
            type=str,
            default='data/vigentes_data_backup.json',
            help='Ruta al archivo vigentes_data_backup.json'
        )
        parser.add_argument(
            '--credits',
            type=str,
            default='data/credits_data_backup.json',
            help='Ruta al archivo credits_data_backup.json'
        )
        parser.add_argument(
            '--previas',
            type=str,
            default='data/previas_data_backup.json',
            help='Ruta al archivo previas_data_backup.json'
        )
        parser.add_argument(
            '--posprevias',
            type=str,
            default='data/posprevias_data_backup.json',
            help='Ruta al archivo posprevias_data_backup.json'
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
            help='Limpiar la base de datos antes de cargar'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = False
        self.dry_run = False
        
        # Estadísticas
        self.stats = {
            'carreras': 0,
            'cursos': 0,
            'previas': 0,
            'items_previa': 0,
            'posprevias': 0,
            'warnings': 0,
            'errors': 0,
        }
        
        # Cachés
        self.carrera_cache: Dict[str, Carrera] = {}
        self.curso_cache: Dict[str, Curso] = {}
    
    def handle(self, *args, **options):
        """Punto de entrada principal del comando."""
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔄 Modo DRY RUN - No se guardará nada en la base de datos'))
        
        # Verificar archivos
        vigentes_path = Path(options['vigentes'])
        credits_path = Path(options['credits'])
        previas_path = Path(options['previas'])
        posprevias_path = Path(options['posprevias'])
        
        for path, name in [
            (vigentes_path, 'vigentes'),
            (credits_path, 'credits'),
            (previas_path, 'previas'),
            (posprevias_path, 'posprevias')
        ]:
            if not path.exists():
                raise CommandError(f'❌ Archivo no encontrado: {path}')
        
        try:
            with transaction.atomic():
                # Limpiar base de datos si se solicita
                if options['clear']:
                    self.clear_database()
                
                # Cargar datos
                self.stdout.write('📖 Cargando archivos JSON...')
                vigentes_data = self.load_json(vigentes_path)
                credits_data = self.load_json(credits_path)
                previas_data = self.load_json(previas_path)
                posprevias_data = self.load_json(posprevias_path)
                
                # Procesar en orden
                self.stdout.write('🎓 Procesando carreras y cursos...')
                self.process_vigentes(vigentes_data, credits_data)
                
                self.stdout.write('🌳 Procesando previas (requisitos)...')
                self.process_previas(previas_data)
                
                self.stdout.write('🔗 Procesando posprevias...')
                self.process_posprevias(posprevias_data)
                
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
        """Limpiar la base de datos."""
        self.stdout.write(self.style.WARNING('🗑️  Limpiando base de datos...'))
        
        if not self.dry_run:
            Posprevia.objects.all().delete()
            ItemPrevia.objects.all().delete()
            Previa.objects.all().delete()
            Curso.objects.all().delete()
            Carrera.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('✅ Base de datos limpiada'))
    
    def load_json(self, path: Path) -> Dict:
        """Cargar archivo JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_or_create_carrera(self, nombre: str, anio_plan: str = None) -> Optional[Carrera]:
        """Obtener o crear una carrera."""
        cache_key = f"{nombre}_{anio_plan or ''}"
        
        if cache_key in self.carrera_cache:
            return self.carrera_cache[cache_key]
        
        if self.dry_run:
            # En dry-run, crear objeto temporal
            carrera = Carrera(nombre=nombre, anio_plan=anio_plan)
        else:
            carrera, created = Carrera.objects.get_or_create(
                nombre=nombre,
                anio_plan=anio_plan,
                defaults={}
            )
            if created:
                self.stats['carreras'] += 1
                if self.verbose:
                    self.stdout.write(f'  ✨ Nueva carrera: {carrera}')
        
        self.carrera_cache[cache_key] = carrera
        return carrera
    
    def process_vigentes(self, vigentes_data: Dict, credits_data: Dict):
        """
        Procesar cursos vigentes y créditos.
        
        IMPORTANTE: 
        - vigentes contiene TODOS los cursos activos
        - credits contiene los créditos (puede tener cursos adicionales)
        - NO todos los cursos tienen previas (solo algunos)
        
        Estructura de vigentes_data:
        {
            "CARRERA_PLAN": {
                "codigo_curso": {
                    "university_code": "FING",
                    "course_code": "1267",
                    "course_name": "TALLER REPR. Y COM. GRAFICA"
                }
            }
        }
        
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
        """
        total_programs = len(vigentes_data)
        
        for idx, (carrera_plan, cursos) in enumerate(vigentes_data.items(), 1):
            if self.verbose:
                self.stdout.write(f'  [{idx}/{total_programs}] Procesando: {carrera_plan}')
            
            # Parsear carrera y año
            carrera_nombre, anio_plan = self.parse_carrera_plan(carrera_plan)
            
            # Crear carrera
            carrera = self.get_or_create_carrera(carrera_nombre, anio_plan)
            
            # Obtener créditos para esta carrera
            credits_for_carrera = credits_data.get(carrera_plan, {})
            
            # Procesar cada curso
            for codigo_curso, curso_data in cursos.items():
                self.create_curso(
                    codigo_curso=curso_data['course_code'],
                    nombre_curso=curso_data['course_name'],
                    codigo_universidad=curso_data['university_code'],
                    carrera=carrera,
                    credits_data=credits_for_carrera
                )
        
        self.stdout.write(
            f'  ✅ Procesados {self.stats["cursos"]} cursos en {self.stats["carreras"]} carreras'
        )
    
    def create_curso(self, codigo_curso: str, nombre_curso: str, 
                     codigo_universidad: str, carrera: Carrera,
                     credits_data: Dict):
        """Crear o actualizar un curso."""
        cache_key = f"{codigo_universidad}_{codigo_curso}"
        
        # Buscar créditos
        creditos = 0
        for codigo_nombre, credit_info in credits_data.items():
            if credit_info['codigo'] == codigo_curso:
                try:
                    creditos = int(credit_info['creditos'])
                except (ValueError, KeyError):
                    creditos = 0
                break
        
        if cache_key in self.curso_cache:
            curso = self.curso_cache[cache_key]
            if not self.dry_run:
                # Agregar carrera si no está
                if carrera and carrera.pk:
                    curso.carrera.add(carrera)
            return curso
        
        if self.dry_run:
            curso = Curso(
                codigo_universidad=codigo_universidad,
                codigo_curso=codigo_curso,
                nombre_curso=nombre_curso,
                creditos=creditos,
                activo=True
            )
        else:
            curso, created = Curso.objects.get_or_create(
                codigo_universidad=codigo_universidad,
                codigo_curso=codigo_curso,
                defaults={
                    'nombre_curso': nombre_curso,
                    'creditos': creditos,
                    'activo': True
                }
            )
            
            # Agregar carrera
            if carrera:
                curso.carrera.add(carrera)
            
            if created:
                self.stats['cursos'] += 1
                if self.verbose:
                    self.stdout.write(f'    ✨ Nuevo curso: {curso} ({creditos} créditos)')
        
        self.curso_cache[cache_key] = curso
        return curso
    
    def process_previas(self, previas_data: Dict):
        """
        Procesar previas (requisitos).
        
        IMPORTANTE: NO todos los cursos tienen previas. Solo se procesan
        los cursos que tienen requisitos definidos.
        
        Estructura:
        {
            "CARRERA_PLAN": {
                "codigo - nombre": {
                    "code": "1944 - ADMINISTRACION GENERAL PARA INGENIEROS",
                    "name": "Examen",
                    "requirements": {
                        "type": "ALL",
                        "title": "debe tener todas",
                        "children": [...]
                    }
                }
            }
        }
        """
        total_programs = len(previas_data)
        cursos_con_previas = 0
        
        for idx, (carrera_plan, previas) in enumerate(previas_data.items(), 1):
            if self.verbose:
                self.stdout.write(f'  [{idx}/{total_programs}] Procesando previas: {carrera_plan}')
            
            # Parsear carrera y año
            carrera_nombre, anio_plan = self.parse_carrera_plan(carrera_plan)
            carrera = self.get_or_create_carrera(carrera_nombre, anio_plan)
            
            # Procesar cada previa
            for codigo_nombre, previa_data in previas.items():
                try:
                    previa_creada = self.create_previa_tree(
                        codigo=previa_data['code'],
                        nombre=previa_data['name'],
                        requirements=previa_data.get('requirements'),
                        carrera=carrera
                    )
                    if previa_creada:
                        cursos_con_previas += 1
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbose:
                        self.stdout.write(
                            self.style.ERROR(f'    ❌ Error en {codigo_nombre}: {e}')
                        )
        
        total_cursos = len(self.curso_cache)
        cursos_sin_previas = total_cursos - cursos_con_previas
        
        self.stdout.write(
            f'  ✅ Procesadas {self.stats["previas"]} previas con '
            f'{self.stats["items_previa"]} items'
        )
        self.stdout.write(
            f'  ℹ️  {cursos_con_previas} cursos con previas, '
            f'{cursos_sin_previas} cursos sin previas (de {total_cursos} totales)'
        )
    
    def create_previa_tree(self, codigo: str, nombre: str, 
                          requirements: Optional[Dict], carrera: Carrera,
                          padre: Optional[Previa] = None) -> Optional[Previa]:
        """
        Crear árbol de previas recursivamente.
        
        Args:
            codigo: Código del curso (ej: "1944 - ADMINISTRACION...")
            nombre: Tipo de requisito (ej: "Examen", "Curso")
            requirements: Diccionario con la estructura del árbol
            carrera: Carrera a la que pertenece
            padre: Nodo padre (None para raíz)
        """
        if not requirements:
            return None
        
        tipo = requirements.get('type', 'LEAF')
        titulo = requirements.get('title', '')
        required_count = requirements.get('required_count', 0)
        
        # Buscar el curso correspondiente
        curso = None
        if not padre:  # Solo para el nodo raíz
            # Extraer el código del curso del string "codigo - nombre"
            codigo_parts = codigo.split(' - ')
            if codigo_parts:
                codigo_limpio = codigo_parts[0].strip()
                # Buscar curso en cache
                for key, c in self.curso_cache.items():
                    if c.codigo_curso == codigo_limpio:
                        curso = c
                        break
        
        # Crear nodo previa
        if self.dry_run:
            previa = Previa(
                curso=curso,
                codigo=codigo if not padre else '',
                nombre=nombre if not padre else '',
                tipo=tipo,
                titulo=titulo,
                cantidad_requerida=required_count,
                padre=padre,
                carrera=carrera
            )
        else:
            previa = Previa.objects.create(
                curso=curso,
                codigo=codigo if not padre else '',
                nombre=nombre if not padre else '',
                tipo=tipo,
                titulo=titulo,
                cantidad_requerida=required_count,
                padre=padre,
                carrera=carrera
            )
            self.stats['previas'] += 1
        
        # Procesar según el tipo
        if tipo == 'LEAF':
            # Crear items
            items = requirements.get('items', [])
            for orden, item_data in enumerate(items):
                self.create_item_previa(previa, item_data, orden)
        
        else:
            # Procesar hijos (ALL, ANY, NOT)
            children = requirements.get('children', [])
            for orden, child in enumerate(children):
                self.create_previa_tree(
                    codigo='',
                    nombre='',
                    requirements=child,
                    carrera=carrera,
                    padre=previa
                )
        
        return previa
    
    def create_item_previa(self, previa: Previa, item_data: Dict, orden: int):
        """
        Crear un item de previa.
        
        Estructura de item_data:
        {
            "source": "UCB",
            "modality": "exam",
            "code": "FI15",
            "title": "CREDITOS ASIGNADOS POR REVALIDA",
            "notes": [],
            "raw": "Examen de la U.C.B: FI15 - CREDITOS..."
        }
        """
        if self.dry_run:
            item = ItemPrevia(
                previa=previa,
                fuente=item_data.get('source', ''),
                modalidad=item_data.get('modality', ''),
                codigo=item_data.get('code', ''),
                titulo=item_data.get('title', ''),
                notas=item_data.get('notes', []),
                texto_raw=item_data.get('raw', ''),
                orden=orden
            )
        else:
            item = ItemPrevia.objects.create(
                previa=previa,
                fuente=item_data.get('source', ''),
                modalidad=item_data.get('modality', ''),
                codigo=item_data.get('code', ''),
                titulo=item_data.get('title', ''),
                notas=item_data.get('notes', []),
                texto_raw=item_data.get('raw', ''),
                orden=orden
            )
            self.stats['items_previa'] += 1
    
    def process_posprevias(self, posprevias_data: Dict):
        """
        Procesar posprevias.
        
        Estructura:
        {
            "CARRERA_PLAN": {
                "codigo": {
                    "code": "CP228",
                    "name": "ABASTECIMIENTO DE AGUA POTABLE",
                    "posprevias": [
                        {
                            "anio_plan": "1997",
                            "carrera": "INGENIERIA CIVIL",
                            "fecha": "01/01/1997",
                            "descripcion": "ING. CIVIL CURRICULAR",
                            "tipo": "Curso",
                            "materia_codigo": "2311",
                            "materia_nombre": "CONDUCCION DE LIQUIDOS...",
                            "materia_full": "2311-CONDUCCION DE LIQUIDOS..."
                        }
                    ]
                }
            }
        }
        """
        total_programs = len(posprevias_data)
        
        for idx, (carrera_plan, posprevias) in enumerate(posprevias_data.items(), 1):
            if self.verbose:
                self.stdout.write(f'  [{idx}/{total_programs}] Procesando posprevias: {carrera_plan}')
            
            # Procesar cada posprevia
            for codigo, posprevia_data in posprevias.items():
                codigo_curso = posprevia_data['code']
                
                # Buscar curso
                curso = None
                for key, c in self.curso_cache.items():
                    if c.codigo_curso == codigo_curso:
                        curso = c
                        break
                
                if not curso:
                    if self.verbose:
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠️  Curso no encontrado: {codigo_curso}')
                        )
                    self.stats['warnings'] += 1
                    continue
                
                # Crear posprevias
                for posprevia_item in posprevia_data.get('posprevias', []):
                    self.create_posprevia(curso, posprevia_data, posprevia_item)
        
        self.stdout.write(f'  ✅ Procesadas {self.stats["posprevias"]} posprevias')
    
    def create_posprevia(self, curso: Curso, posprevia_data: Dict, item: Dict):
        """Crear una posprevia."""
        if self.dry_run:
            posprevia = Posprevia(
                curso=curso,
                codigo=posprevia_data['code'],
                nombre=posprevia_data['name'],
                anio_plan=item.get('anio_plan', ''),
                carrera=item.get('carrera', ''),
                fecha=item.get('fecha', ''),
                descripcion=item.get('descripcion', ''),
                tipo=item.get('tipo', ''),
                materia_codigo=item.get('materia_codigo', ''),
                materia_nombre=item.get('materia_nombre', ''),
                materia_full=item.get('materia_full', '')
            )
        else:
            posprevia = Posprevia.objects.create(
                curso=curso,
                codigo=posprevia_data['code'],
                nombre=posprevia_data['name'],
                anio_plan=item.get('anio_plan', ''),
                carrera=item.get('carrera', ''),
                fecha=item.get('fecha', ''),
                descripcion=item.get('descripcion', ''),
                tipo=item.get('tipo', ''),
                materia_codigo=item.get('materia_codigo', ''),
                materia_nombre=item.get('materia_nombre', ''),
                materia_full=item.get('materia_full', '')
            )
            self.stats['posprevias'] += 1
    
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
    
    def print_stats(self):
        """Imprimir estadísticas."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 ESTADÍSTICAS'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'🎓 Carreras creadas:    {self.stats["carreras"]}')
        self.stdout.write(f'📚 Cursos creados:      {self.stats["cursos"]}')
        self.stdout.write(f'🌳 Previas creadas:     {self.stats["previas"]}')
        self.stdout.write(f'📝 Items creados:       {self.stats["items_previa"]}')
        self.stdout.write(f'🔗 Posprevias creadas:  {self.stats["posprevias"]}')
        
        if self.stats['warnings'] > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Advertencias:        {self.stats["warnings"]}'))
        
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores:             {self.stats["errors"]}'))
        
        self.stdout.write('=' * 60 + '\n')

