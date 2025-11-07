"""
Django management command to load Bedelia data from JSON files into the database.

This command imports credits.json, requirements.json, and posprevias.json into
the database models, handling multiple programs and building requirement trees.
"""
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import traceback

from api.models import (
    Program, Subject, SubjectAlias, Offering, OfferingType,
    RequirementGroup, GroupScope, GroupFlavor, RequirementGroupLink,
    RequirementItem, TargetType, ReqCondition, SubjectEquivalence,
    EquivalenceKind
)


class Command(BaseCommand):
    """Load Bedelia data from JSON files into the database."""
    
    help = 'Import Bedelia course data from JSON files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--credits',
            type=str,
            required=False,
            help='Path to credits.json file',
            default='../data/credits_data_backup.json'
        )
        parser.add_argument(
            '--requirements',
            type=str,
            required=False,
            help='Path to requirements.json file',
            default='../data/previas_data_backup.json'
        )
        parser.add_argument(
            '--posprevias',
            type=str,
            required=False,
            help='Path to posprevias.json file',
            default='../data/posprevias_data_backup.json'
        )
        parser.add_argument(
            '--vigentes',
            type=str,
            required=False,
            help='Path to vigentes.json file (optional)',
            default='../data/vigentes_data_backup.json'
        )
        parser.add_argument(
            '--default-term',
            type=str,
            default='2025S1',
            help='Default term for offerings (e.g., 2025S1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Process without saving to database'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = False
        self.dry_run = False
        self.default_term = '2025S1'
        
        # Statistics
        self.stats = {
            'programs': 0,
            'subjects': 0,
            'offerings': 0,
            'req_groups': 0,
            'req_items': 0,
            'warnings': 0,
            'errors': 0,
            'missing_subjects': set(),  # Track unique missing subject codes
        }
        
        # Lookup caches
        self.program_cache: Dict[str, Program] = {}
        self.subject_cache: Dict[str, Subject] = {}  # By code only now
        self.subject_by_code: Dict[str, List[Subject]] = {}
        self.offering_cache: Dict[Tuple[str, str], Offering] = {}
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        self.default_term = options['default_term']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode - no changes will be saved'))
        
        try:
            # Load JSON files
            self.stdout.write('Loading JSON files...')
            credits_data = self._load_json(options['credits'])
            requirements_data = self._load_json(options['requirements'])
            posprevias_data = self._load_json(options['posprevias'])
            
            # Vigentes is optional
            vigentes_data = None
            vigentes_path = options.get('vigentes')
            if vigentes_path and Path(vigentes_path).exists():
                vigentes_data = self._load_json(vigentes_path)
            else:
                self.stdout.write(self.style.WARNING('Vigentes file not found, skipping Phase 4'))
            
            # Process data (each phase has its own transaction in _process_all_data)
            self._process_all_data(credits_data, requirements_data, posprevias_data, vigentes_data)
            
            # Print summary
            self._print_summary()
            
        except Exception as e:
            raise CommandError(f'Error during import: {e}')
    
    def _load_json(self, filepath: str) -> Any:
        """Load and parse JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise CommandError(f'File not found: {filepath}')
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.log(f'Loaded {filepath}: {len(data) if isinstance(data, (list, dict)) else "N/A"} entries')
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in {filepath}: {e}')
    
    def _process_all_data(self, credits_data, requirements_data, posprevias_data, vigentes_data=None):
        """Process all data in phases."""
        try:
            self.stdout.write(self.style.SUCCESS('\n=== Phase 1: Loading Credits (Subjects) ==='))
            if not self.dry_run:
                with transaction.atomic():
                    self._load_credits(credits_data)
            else:
                self._load_credits(credits_data)
        except Exception as e:
            raise CommandError(f'Error in Phase 1 (Credits): {e}')
        
        try:
            self.stdout.write(self.style.SUCCESS('\n=== Phase 2: Loading Requirements (Previas) ==='))
            if not self.dry_run:
                with transaction.atomic():
                    self._load_requirements(requirements_data)
            else:
                self._load_requirements(requirements_data)
        except Exception as e:
            raise CommandError(f'Error in Phase 2 (Requirements): {e}')
        
        # Clear offering cache between phases to avoid stale references
        self.offering_cache.clear()
        
        try:
            self.stdout.write(self.style.SUCCESS('\n=== Phase 3: Processing PosPrevias ==='))
            if not self.dry_run:
                with transaction.atomic():
                    self._load_posprevias(posprevias_data)
            else:
                self._load_posprevias(posprevias_data)
        except Exception as e:
            raise CommandError(f'Error in Phase 3 (PosPrevias): {e}')
        
        if vigentes_data:
            try:
                self.stdout.write(self.style.SUCCESS('\n=== Phase 4: Processing Vigentes (Active Offerings) ==='))
                if not self.dry_run:
                    with transaction.atomic():
                        self._load_vigentes(vigentes_data)
                else:
                    self._load_vigentes(vigentes_data)
            except Exception as e:
                raise CommandError(f'Error in Phase 4 (Vigentes): {e}')
    
    # ========================================================================
    # Phase 1: Credits (Subjects)
    # ========================================================================
    
    def _load_credits(self, credits_data):
        """Load credits.json into Program and Subject models.
        
        Handles both formats:
        - New: {"PROGRAM_YEAR": {"CODE_NAME": {...}}}
        - Old: [{"codigo": "...", "nombre": "...", "creditos": "..."}]
        """
        # Check if new nested format (dict) or old flat list
        if isinstance(credits_data, dict):
            self.stdout.write('Detected new multi-program format')
            # New format: iterate over programs
            for program_key, subjects_dict in credits_data.items():
                # Parse program name and year from key like "INGENIERÍA CIVIL_2021"
                if '_' in program_key:
                    program_name, year_str = program_key.rsplit('_', 1)
                    try:
                        year = int(year_str)
                    except ValueError:
                        year = None
                        program_name = program_key  # If year isn't numeric, treat whole thing as name
                else:
                    program_name, year = program_key, None
                
                program = self._get_or_create_program(program_name, year)
                self.stdout.write(f'Processing program: {program_name} ({year}) with {len(subjects_dict)} subjects')
                
                # subjects_dict is like {"CODE_NAME": {"codigo": ..., "nombre": ..., "creditos": ...}}
                count = 0
                for subject_key, entry in subjects_dict.items():
                    self._process_credit_entry_safe(entry, program)
                    count += 1
                    if count % 100 == 0:
                        self.stdout.write(f'  Processed {count}/{len(subjects_dict)} subjects...')
        
        elif isinstance(credits_data, list):
            self.log('Detected old flat list format')
            # Old format: flat list of subjects
            default_program = self._get_or_create_program('Default Program', None)
            for entry in credits_data:
                self._process_credit_entry_safe(entry, default_program)
        else:
            self.error(f'credits.json has unexpected format: {type(credits_data)}')
            return
    
    def _process_credit_entry_safe(self, entry: Dict, program: Program):
        """Process a credit entry with error isolation."""
        if not self.dry_run:
            try:
                sid = transaction.savepoint()
                self._process_credit_entry(entry, program)
                transaction.savepoint_commit(sid)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                self.stats['errors'] += 1
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'ERROR: Error processing credit entry {entry.get("codigo")}: {e}'))
        else:
            try:
                self._process_credit_entry(entry, program)
            except Exception as e:
                self.stats['errors'] += 1
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'ERROR: Error processing credit entry {entry.get("codigo")}: {e}'))
    
    def _process_credit_entry(self, entry: Dict, default_program: Program):
        """Process a single credit entry."""
        code = entry.get('codigo', '').strip()
        name = entry.get('nombre', '').strip()
        credits_str = entry.get('creditos', '').strip()
        
        if not code or not name:
            self.warn(f'Skipping entry with missing code or name: {entry}')
            return
        
        # Parse credits
        credits = self._parse_credits(credits_str)
        
        # Get or create subject
        subject, created = self._get_or_create_subject(
            program=default_program,
            code=code,
            name=name,
            credits=credits
        )
        
        if created:
            self.stats['subjects'] += 1
            self.log(f'Created subject: {code} - {name} ({credits} credits)')
        else:
            self.log(f'Subject already exists: {code} - {name}')
    
    def _parse_credits(self, credits_str: str) -> Optional[Decimal]:
        """Parse credit string to Decimal."""
        if not credits_str:
            return None
        
        # Handle special formats like "OPTATIVA - 4" or "LDI - 6"
        match = re.search(r'(\d+(?:\.\d+)?)', credits_str)
        if match:
            try:
                return Decimal(match.group(1))
            except InvalidOperation:
                self.warn(f'Could not parse credits: {credits_str}')
                return None
        
        self.warn(f'Could not parse credits: {credits_str}')
        return None
    
    # ========================================================================
    # Phase 2: Requirements (Previas)
    # ========================================================================
    
    def _load_requirements(self, requirements_data: Dict):
        """Load requirements.json into Offering and RequirementGroup models.
        
        Handles both formats:
        - New: {"PROGRAM_YEAR": {"CODE - NAME": {...}}}
        - Old: {"CODE - NAME": {...}}
        """
        if not isinstance(requirements_data, dict):
            self.error('requirements.json should be a dictionary')
            return
        
        # Check if this is the new nested format
        # (first key contains "_" and its value is a dict of subjects)
        first_key = next(iter(requirements_data.keys()), None)
        if first_key and '_' in first_key and isinstance(requirements_data[first_key], dict):
            # Check if the nested dict has subject-like keys
            nested_dict = requirements_data[first_key]
            first_nested_key = next(iter(nested_dict.keys()), None)
            if first_nested_key and (' - ' in first_nested_key or 'code' in nested_dict[first_nested_key]):
                self.stdout.write('Detected new multi-program requirements format')
                # New format: iterate over programs first
                for program_key, subjects_dict in requirements_data.items():
                    if '_' in program_key:
                        program_name, year_str = program_key.rsplit('_', 1)
                        try:
                            year = int(year_str)
                        except ValueError:
                            year = None
                            program_name = program_key
                    else:
                        program_name, year = program_key, None
                    
                    self.stdout.write(f'Processing requirements for program: {program_name} ({year}) with {len(subjects_dict)} subjects')
                    
                    # Now process subjects under this program
                    for subject_key, entry in subjects_dict.items():
                        self._process_requirement_entry_safe(subject_key, entry)
                return
        
        # Old format: flat dict with subject keys
        self.log('Detected old flat requirements format')
        for key, entry in requirements_data.items():
            self._process_requirement_entry_safe(key, entry)
    
    def _process_requirement_entry_safe(self, key: str, entry: Dict):
        """Process a requirement entry with error isolation."""
        if not self.dry_run:
            try:
                sid = transaction.savepoint()
                self._process_requirement_entry(key, entry)
                transaction.savepoint_commit(sid)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                self.stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'ERROR: Error processing requirement {key}: {type(e).__name__}: {e}'))
                if self.verbose:
                    import traceback
                    traceback.print_exc()
        else:
            try:
                self._process_requirement_entry(key, entry)
            except Exception as e:
                self.stats['errors'] += 1
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'ERROR: Error processing requirement {key}: {e}'))
    
    def _process_requirement_entry(self, key: str, entry: Dict):
        """Process a single requirement entry."""
        # Extract subject code from key (format: "CODE - NAME")
        code = self._extract_code_from_key(key)
        if not code:
            self.warn(f'Could not extract code from key: {key}')
            return
        
        # Get offering type from entry
        offering_type_str = entry.get('name', 'Curso')
        offering_type = OfferingType.EXAM if offering_type_str.lower() == 'examen' else OfferingType.COURSE
        
        # Find subject
        subject = self._find_subject_by_code(code)
        if not subject:
            self.warn(f'Subject not found for code {code}, skipping requirements')
            return
        
        # Create or get offering
        offering = self._get_or_create_offering(
            subject=subject,
            offering_type=offering_type,
            term=self.default_term
        )
        
        # Process requirements tree
        requirements = entry.get('requirements')
        if requirements:
            self._build_requirement_tree(offering, requirements)
    
    def _build_requirement_tree(self, offering: Offering, req_node: Dict, parent_group: Optional[RequirementGroup] = None, order: int = 0):
        """Recursively build requirement tree from JSON structure."""
        node_type = req_node.get('type', 'LEAF')
        
        if node_type in ['ALL', 'ANY', 'NONE']:
            # Create a requirement group
            scope = getattr(GroupScope, node_type)
            
            # Determine flavor and min_required
            flavor = GroupFlavor.GENERIC
            min_required = None
            
            if node_type == 'ANY':
                # Check if this is an approvals group
                children = req_node.get('children', [])
                if children and children[0].get('rule') == 'min_approvals':
                    flavor = GroupFlavor.APPROVALS
                    min_required = children[0].get('required_count', 1)
                else:
                    min_required = 1  # Default for ANY
            else:
                # Ensure min_required is explicitly None for ALL and NONE
                min_required = None
            
            group = self._create_requirement_group(
                offering=offering,
                scope=scope,
                flavor=flavor,
                min_required=min_required,
                order=order
            )
            
            # Link to parent if exists
            if parent_group:
                self._create_group_link(parent_group, group, order)
            
            # Process children
            children = req_node.get('children', [])
            for i, child in enumerate(children):
                self._build_requirement_tree(offering, child, group, i)
        
        elif node_type == 'LEAF':
            # Create requirement items
            if parent_group:
                # Special case: if this is a min_approvals leaf and parent is not ANY,
                # we need to create an intermediate ANY group
                rule = req_node.get('rule')
                if rule == 'min_approvals' and parent_group.scope != GroupScope.ANY:
                    # Create intermediate ANY+APPROVALS group
                    min_required = req_node.get('required_count', 1)
                    intermediate_group = self._create_requirement_group(
                        offering=offering,
                        scope=GroupScope.ANY,
                        flavor=GroupFlavor.APPROVALS,
                        min_required=min_required,
                        order=order
                    )
                    self._create_group_link(parent_group, intermediate_group, order)
                    self._create_requirement_items(intermediate_group, req_node, 0)
                else:
                    self._create_requirement_items(parent_group, req_node, order)
    
    def _create_requirement_items(self, group: RequirementGroup, leaf_node: Dict, order: int):
        """Create requirement items from a leaf node."""
        rule = leaf_node.get('rule')
        items = leaf_node.get('items', [])
        
        if rule == 'min_approvals' and items:
            # Process items list
            for i, item in enumerate(items):
                self._create_requirement_item_from_dict(group, item, order + i)
        
        elif rule == 'raw_text':
            # Try to extract subject references from raw text
            value = leaf_node.get('value', '')
            self._create_requirement_item_from_text(group, value, order)
        
        elif rule == 'credits_in_plan':
            # Store as note for now
            self.log(f'Credits requirement: {leaf_node.get("credits")} in {leaf_node.get("plan")}')
    
    def _create_requirement_item_from_dict(self, group: RequirementGroup, item_dict: Dict, order: int):
        """Create a requirement item from parsed item dictionary."""
        code = item_dict.get('code', '').strip()
        name = item_dict.get('name', '').strip()
        kind = item_dict.get('kind', 'curso').lower()
        
        if not code:
            return
        
        # Find subject
        subject = self._find_subject_by_code(code)
        if not subject:
            self.warn(f'Cannot create requirement item: subject {code} not found')
            return
        
        # Determine condition
        condition = ReqCondition.APPROVED  # Default
        
        if not self.dry_run:
            RequirementItem.objects.create(
                group=group,
                target_type=TargetType.SUBJECT,
                target_subject=subject,
                condition=condition,
                alt_code=code,
                alt_label=f'{code} - {name}' if name else code,
                order_index=order
            )
        
        self.stats['req_items'] += 1
        self.log(f'Created requirement item: {code}')
    
    def _create_requirement_item_from_text(self, group: RequirementGroup, text: str, order: int):
        """Create requirement item from raw text."""
        # Try to extract code patterns
        code_match = re.search(r'\b([A-Z0-9]+)\b', text)
        if code_match:
            code = code_match.group(1)
            subject = self._find_subject_by_code(code)
            
            if not subject:
                self.warn(f'Cannot create requirement item from text: subject {code} not found in "{text[:50]}"')
                return
            
            if not self.dry_run:
                RequirementItem.objects.create(
                    group=group,
                    target_type=TargetType.SUBJECT,
                    target_subject=subject,
                    condition=ReqCondition.APPROVED,
                    alt_code=code,
                    alt_label=text[:255],
                    order_index=order
                )
            
            self.stats['req_items'] += 1
    
    # ========================================================================
    # Phase 3: PosPrevias
    # ========================================================================
    
    def _load_posprevias(self, posprevias_data: Dict):
        """Load posprevias.json to create inverse requirement relationships.
        
        Handles both formats:
        - New: {"PROGRAM_YEAR": {"CODE": {...}}}
        - Old: {"CODE": {...}}
        """
        if not isinstance(posprevias_data, dict):
            self.error('posprevias.json should be a dictionary')
            return
        
        # Check if this is the new nested format
        first_key = next(iter(posprevias_data.keys()), None)
        if first_key and '_' in first_key and isinstance(posprevias_data[first_key], dict):
            # Check if nested dict has subject codes
            nested_dict = posprevias_data[first_key]
            first_nested_key = next(iter(nested_dict.keys()), None)
            if first_nested_key and ('code' in nested_dict[first_nested_key] or 'posprevias' in nested_dict[first_nested_key]):
                self.stdout.write('Detected new multi-program posprevias format')
                # New format: iterate over programs first
                for program_key, subjects_dict in posprevias_data.items():
                    if '_' in program_key:
                        program_name, year_str = program_key.rsplit('_', 1)
                        try:
                            year = int(year_str)
                        except ValueError:
                            year = None
                            program_name = program_key
                    else:
                        program_name, year = program_key, None
                    
                    self.stdout.write(f'Processing posprevias for program: {program_name} ({year}) with {len(subjects_dict)} subjects')
                    
                    # Now process subjects under this program
                    for code, entry in subjects_dict.items():
                        self._process_posprevias_entry_safe(code, entry)
                return
        
        # Old format: flat dict with subject codes
        self.log('Detected old flat posprevias format')
        for code, entry in posprevias_data.items():
            self._process_posprevias_entry_safe(code, entry)
    
    def _process_posprevias_entry_safe(self, code: str, entry: Dict):
        """Process a posprevias entry with error isolation."""
        if not self.dry_run:
            try:
                sid = transaction.savepoint()
                self._process_posprevias_entry(code, entry)
                transaction.savepoint_commit(sid)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                self.stats['errors'] += 1
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'ERROR: Error processing posprevias for {code}: {e}'))
        else:
            try:
                self._process_posprevias_entry(code, entry)
            except Exception as e:
                self.stats['errors'] += 1
                if self.verbose:
                    self.stdout.write(self.style.ERROR(f'ERROR: Error processing posprevias for {code}: {e}'))
    
    def _process_posprevias_entry(self, code: str, entry: Dict):
        """Process a single posprevias entry."""
        # Find the prerequisite subject (the one that unlocks others)
        prereq_subject = self._find_subject_by_code(code)
        if not prereq_subject:
            self.warn(f'Subject not found for posprevias code: {code}\n{str(entry)[:100]}...')
            return
        
        posprevias_list = entry.get('posprevias', [])
        
        for posprevia in posprevias_list:
            # Extract target course info
            materia_codigo = posprevia.get('materia_codigo', '').strip()
            tipo = posprevia.get('tipo', 'Curso').strip()
            
            if not materia_codigo:
                continue
            
            # Find target subject
            target_subject = self._find_subject_by_code(materia_codigo)
            if not target_subject:
                # Track missing subject but only warn if verbose
                self.stats['missing_subjects'].add(materia_codigo)
                if self.verbose:
                    self.warn(f'Target subject not found: {materia_codigo}')
                continue
            
            # Get or create target offering
            offering_type = OfferingType.EXAM if tipo.lower() == 'examen' else OfferingType.COURSE
            target_offering = self._get_or_create_offering(
                subject=target_subject,
                offering_type=offering_type,
                term=self.default_term
            )
            
            # Verify offering has an ID and is saved
            if not target_offering.id:
                self.warn(f'Target offering for {target_subject.code} has no ID, skipping posprevia')
                continue
            
            # Refresh from DB to ensure it exists
            try:
                target_offering.refresh_from_db()
            except Offering.DoesNotExist:
                self.warn(f'Target offering for {target_subject.code} not found in DB, skipping posprevia')
                continue
            
            # Create requirement: target_offering requires prereq_subject
            self._add_posprevia_requirement(target_offering, prereq_subject, tipo)
    
    def _add_posprevia_requirement(self, target_offering: Offering, prereq_subject: Subject, tipo: str):
        """Add a requirement to target offering that it requires prereq_subject."""
        # Find or create an ANY group for posprevias
        if not self.dry_run:
            # Use note in the lookup to distinguish from other ANY+APPROVALS groups
            group, created = RequirementGroup.objects.get_or_create(
                offering=target_offering,
                scope=GroupScope.ANY,
                flavor=GroupFlavor.APPROVALS,
                note='Generated from posprevias',
                defaults={
                    'min_required': 1,
                    'order_index': 999  # Put at end
                }
            )
            
            if created:
                self.stats['req_groups'] += 1
            
            # Add the requirement item
            RequirementItem.objects.get_or_create(
                group=group,
                target_type=TargetType.SUBJECT,
                target_subject=prereq_subject,
                defaults={
                    'condition': ReqCondition.APPROVED,
                    'alt_code': prereq_subject.code,
                    'alt_label': f'{prereq_subject.code} - {prereq_subject.name}',
                    'order_index': 0
                }
            )
            
            self.stats['req_items'] += 1
    
    # ========================================================================
    # Phase 4: Vigentes (Active Offerings)
    # ========================================================================
    
    def _load_vigentes(self, vigentes_data):
        """Load vigentes.json to mark which subjects have active offerings.
        
        Handles both formats:
        - New: {"PROGRAM_YEAR": {"CODE": {...}}}
        - Old: [{"course_code": "...", ...}]
        """
        if isinstance(vigentes_data, dict):
            self.stdout.write('Detected new multi-program vigentes format')
            # New format: iterate over programs
            for program_key, courses in vigentes_data.items():
                if '_' in program_key:
                    program_name, year_str = program_key.rsplit('_', 1)
                    try:
                        year = int(year_str)
                    except ValueError:
                        year = None
                        program_name = program_key
                else:
                    program_name, year = program_key, None
                
                courses_count = len(courses) if isinstance(courses, (dict, list)) else 0
                self.stdout.write(f'Processing vigentes for program: {program_name} ({year}) with {courses_count} courses')
                
                # courses could be dict or list
                if isinstance(courses, dict):
                    for code, course_info in courses.items():
                        self._process_vigente_entry(course_info)
                elif isinstance(courses, list):
                    for course_info in courses:
                        self._process_vigente_entry(course_info)
        
        elif isinstance(vigentes_data, list):
            self.log('Detected old flat vigentes list format')
            for course_info in vigentes_data:
                self._process_vigente_entry(course_info)
        else:
            self.error(f'vigentes.json has unexpected format: {type(vigentes_data)}')
    
    def _process_vigente_entry(self, course_info: Dict):
        """Process a single vigente entry to mark subject as active."""
        code = course_info.get('course_code') or course_info.get('codigo', '').strip()
        if not code:
            return
        
        # Find subject
        subject = self._find_subject_by_code(code)
        if not subject:
            if self.verbose:
                self.stdout.write(f'Subject not found for vigente code: {code}')
            return
        
        # Mark subject as having active offerings
        # For now, we just ensure an offering exists
        if not self.dry_run:
            offering, created = Offering.objects.get_or_create(
                subject=subject,
                type=OfferingType.COURSE,
                term=self.default_term,
                defaults={
                    'is_active': True
                }
            )
            
            if created:
                self.stats['offerings'] += 1
                if self.verbose:
                    self.stdout.write(f'Created active offering for {code}')
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _get_or_create_program(self, name: str, year: Optional[int]) -> Program:
        """Get or create a Program."""
        cache_key = f'{name}_{year}'
        if cache_key in self.program_cache:
            return self.program_cache[cache_key]
        
        if not self.dry_run:
            program, created = Program.objects.get_or_create(
                name=name,
                plan_year=year,
                defaults={'name': name, 'plan_year': year}
            )
            if created:
                self.stats['programs'] += 1
                self.log(f'Created program: {name} ({year})')
        else:
            # In dry-run mode, check if it exists first
            try:
                program = Program.objects.get(name=name, plan_year=year)
                created = False
            except Program.DoesNotExist:
                program = Program(name=name, plan_year=year)
                created = True
                self.stats['programs'] += 1
        
        self.program_cache[cache_key] = program
        return program
    
    def _get_or_create_subject(self, program: Program, code: str, name: str, credits: Optional[Decimal]) -> Tuple[Subject, bool]:
        """Get or create a Subject and add it to the program.
        
        Since subjects can belong to multiple programs, we:
        1. Get or create the subject by code only
        2. Add the program to the subject's programs
        """
        # Check global cache by code only
        if code in self.subject_cache:
            subject = self.subject_cache[code]
            created = False
            
            # Add program to subject if not already there
            if not self.dry_run and program.id:
                if not subject.programs.filter(id=program.id).exists():
                    subject.programs.add(program)
                    self.log(f'Added program {program.name} to subject {code}')
            
            return subject, created
        
        if not self.dry_run:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'credits': credits
                }
            )
            
            # Add program to subject
            if program.id:
                subject.programs.add(program)
            
            # Update if needed
            if not created and (subject.name != name or subject.credits != credits):
                subject.name = name
                subject.credits = credits
                subject.save()
        else:
            # In dry-run mode, check if it exists first
            try:
                subject = Subject.objects.get(code=code)
                created = False
            except Subject.DoesNotExist:
                subject = Subject(code=code, name=name, credits=credits)
                created = True
            except Exception as e:
                # If can't query, create mock
                subject = Subject(code=code, name=name, credits=credits)
                created = True
        
        # Cache by code only
        self.subject_cache[code] = subject
        
        # Also add to code lookup
        if code not in self.subject_by_code:
            self.subject_by_code[code] = []
        if subject not in self.subject_by_code[code]:
            self.subject_by_code[code].append(subject)
        
        return subject, created
    
    def _get_or_create_offering(self, subject: Subject, offering_type: OfferingType, term: str) -> Offering:
        """Get or create an Offering."""
        cache_key = (subject.code, offering_type)
        if cache_key in self.offering_cache:
            return self.offering_cache[cache_key]
        
        if not self.dry_run:
            offering, created = Offering.objects.get_or_create(
                subject=subject,
                type=offering_type,
                term=term,
                defaults={
                    'is_active': True,
                    'credits': subject.credits
                }
            )
            if created:
                self.stats['offerings'] += 1
                self.log(f'Created offering: {subject.code} {offering_type}')
        else:
            offering = Offering(subject=subject, type=offering_type, term=term)
        
        self.offering_cache[cache_key] = offering
        return offering
    
    def _create_requirement_group(self, offering: Offering, scope: GroupScope, flavor: GroupFlavor, min_required: Optional[int], order: int) -> RequirementGroup:
        """Create a RequirementGroup."""
        if not self.dry_run:
            group = RequirementGroup.objects.create(
                offering=offering,
                scope=scope,
                flavor=flavor,
                min_required=min_required,
                order_index=order
            )
            self.stats['req_groups'] += 1
            return group
        else:
            return RequirementGroup(offering=offering, scope=scope, flavor=flavor, min_required=min_required, order_index=order)
    
    def _create_group_link(self, parent: RequirementGroup, child: RequirementGroup, order: int):
        """Create a RequirementGroupLink."""
        if not self.dry_run:
            RequirementGroupLink.objects.create(
                parent_group=parent,
                child_group=child,
                order_index=order
            )
    
    def _find_subject_by_code(self, code: str) -> Optional[Subject]:
        """Find a subject by code in cache.
        
        Since subjects are now unique by code (ManyToMany with programs),
        we just return the subject if it exists.
        """
        # Check cache first
        if code in self.subject_cache:
            return self.subject_cache[code]
        
        # Fallback to list lookup
        subjects = self.subject_by_code.get(code, [])
        return subjects[0] if subjects else None
    
    def _extract_code_from_key(self, key: str) -> Optional[str]:
        """Extract subject code from requirement key."""
        # Format: "CODE - NAME" or just "CODE"
        match = re.match(r'^([A-Z0-9]+)\s*-', key)
        if match:
            return match.group(1)
        
        # Try just the first word
        parts = key.split()
        if parts and re.match(r'^[A-Z0-9]+$', parts[0]):
            return parts[0]
        
        return None
    
    # ========================================================================
    # Logging & Output
    # ========================================================================
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            self.stdout.write(f'  {message}')
    
    def warn(self, message: str):
        """Log warning message."""
        self.stats['warnings'] += 1
        self.stdout.write(self.style.WARNING(f'WARNING: {message}'))
    
    def error(self, message: str):
        """Log error message."""
        self.stats['errors'] += 1
        self.stdout.write(self.style.ERROR(f'ERROR: {message}'))
    
    def _print_summary(self):
        """Print import summary statistics."""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('Import Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Programs created: {self.stats["programs"]}')
        self.stdout.write(f'Subjects created: {self.stats["subjects"]}')
        self.stdout.write(f'Offerings created: {self.stats["offerings"]}')
        self.stdout.write(f'Requirement groups created: {self.stats["req_groups"]}')
        self.stdout.write(f'Requirement items created: {self.stats["req_items"]}')
        
        # Show missing subjects summary
        missing_count = len(self.stats['missing_subjects'])
        if missing_count > 0:
            self.stdout.write(self.style.WARNING(f'\nMissing subject codes: {missing_count}'))
            if missing_count <= 20:
                # Show all if not too many
                missing_sorted = sorted(self.stats['missing_subjects'])
                self.stdout.write(self.style.WARNING(f'  Codes: {", ".join(missing_sorted)}'))
            else:
                # Show first 20
                missing_sorted = sorted(self.stats['missing_subjects'])[:20]
                self.stdout.write(self.style.WARNING(f'  First 20: {", ".join(missing_sorted)}...'))
            self.stdout.write('  (These subjects are referenced in posprevias but not found in credits data)')
        
        self.stdout.write(self.style.WARNING(f'\nWarnings: {self.stats["warnings"]}'))
        self.stdout.write(self.style.ERROR(f'Errors: {self.stats["errors"]}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

