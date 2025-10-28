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
            required=True,
            help='Path to credits.json file'
        )
        parser.add_argument(
            '--requirements',
            type=str,
            required=True,
            help='Path to requirements.json file'
        )
        parser.add_argument(
            '--posprevias',
            type=str,
            required=True,
            help='Path to posprevias.json file'
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
        }
        
        # Lookup caches
        self.program_cache: Dict[str, Program] = {}
        self.subject_cache: Dict[str, Subject] = {}
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
            
            # Process data (each phase has its own transaction in _process_all_data)
            self._process_all_data(credits_data, requirements_data, posprevias_data)
            
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
    
    def _process_all_data(self, credits_data, requirements_data, posprevias_data):
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
    
    # ========================================================================
    # Phase 1: Credits (Subjects)
    # ========================================================================
    
    def _load_credits(self, credits_data: List[Dict]):
        """Load credits.json into Program and Subject models."""
        if not isinstance(credits_data, list):
            self.error('credits.json should be a list')
            return
        
        # Create a default program for now (we'll enhance this later)
        default_program = self._get_or_create_program('Default Program', None)
        
        for entry in credits_data:
            # Use savepoint for each entry to isolate transaction errors
            if not self.dry_run:
                try:
                    sid = transaction.savepoint()
                    self._process_credit_entry(entry, default_program)
                    transaction.savepoint_commit(sid)
                except Exception as e:
                    transaction.savepoint_rollback(sid)
                    self.stats['errors'] += 1
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f'ERROR: Error processing credit entry {entry.get("codigo")}: {e}'))
            else:
                try:
                    self._process_credit_entry(entry, default_program)
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
            self.log(f'Updated subject: {code} - {name}')
    
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
        """Load requirements.json into Offering and RequirementGroup models."""
        if not isinstance(requirements_data, dict):
            self.error('requirements.json should be a dictionary')
            return
        
        for key, entry in requirements_data.items():
            # Use savepoint for each entry to isolate transaction errors
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
        """Load posprevias.json to create inverse requirement relationships."""
        if not isinstance(posprevias_data, dict):
            self.error('posprevias.json should be a dictionary')
            return
        
        for code, entry in posprevias_data.items():
            # Use savepoint for each entry to isolate transaction errors
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
            self.warn(f'Subject not found for posprevias code: {code}')
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
        else:
            # Create mock object for dry run
            program = Program(name=name, plan_year=year)
            created = True
        
        self.program_cache[cache_key] = program
        return program
    
    def _get_or_create_subject(self, program: Program, code: str, name: str, credits: Optional[Decimal]) -> Tuple[Subject, bool]:
        """Get or create a Subject."""
        cache_key = f'{program.id if hasattr(program, "id") else "mock"}_{code}'
        if cache_key in self.subject_cache:
            return self.subject_cache[cache_key], False
        
        if not self.dry_run:
            subject, created = Subject.objects.get_or_create(
                program=program,
                code=code,
                defaults={
                    'name': name,
                    'credits': credits
                }
            )
            
            if not created and (subject.name != name or subject.credits != credits):
                subject.name = name
                subject.credits = credits
                subject.save()
        else:
            subject = Subject(program=program, code=code, name=name, credits=credits)
            created = True
        
        self.subject_cache[cache_key] = subject
        
        # Also add to code lookup
        if code not in self.subject_by_code:
            self.subject_by_code[code] = []
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
        """Find a subject by code in cache."""
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
        self.stdout.write(self.style.WARNING(f'Warnings: {self.stats["warnings"]}'))
        self.stdout.write(self.style.ERROR(f'Errors: {self.stats["errors"]}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

