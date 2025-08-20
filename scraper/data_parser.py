"""
Data parsing utilities for Bedelia scraper.

This module contains functions to parse scraped data and convert it
to ORM model instances for database storage.
"""

from typing import List, Dict, Any, Optional
from models import (
    Subject, Offering, RequirementGroup, RequirementItem,
    Program, SubjectAlias, OfferingLink, AuditSource
)
from database import get_db_session
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class DataParser:
    """Handles parsing and storing scraped data using ORM models"""
    
    def __init__(self):
        self.subjects_cache = {}  # Cache for subject lookups
        self.programs_cache = {}  # Cache for programs
    
    def find_or_create_program(self, session, name: str, plan_year: int = None) -> Program:
        """Find existing program or create new one."""
        cache_key = f"{name}_{plan_year}"
        
        if cache_key in self.programs_cache:
            return self.programs_cache[cache_key]
        
        program = session.query(Program).filter(
            Program.name == name,
            Program.plan_year == plan_year
        ).first()
        
        if not program:
            program = Program(name=name, plan_year=plan_year)
            session.add(program)
            session.flush()  # Get the ID
            logger.info(f"Created new program: {name} ({plan_year})")
        
        self.programs_cache[cache_key] = program
        return program
    
    def find_or_create_subject(self, session, code: str, name: str, 
                              program: Program = None, **kwargs) -> Subject:
        """Find existing subject or create new one."""
        cache_key = f"{code}_{program.id if program else None}"
        
        if cache_key in self.subjects_cache:
            return self.subjects_cache[cache_key]
        
        # Try to find by code and program
        query = session.query(Subject).filter(Subject.code == code)
        if program:
            query = query.filter(Subject.program_id == program.id)
        
        subject = query.first()
        
        if not subject:
            subject = Subject(
                code=code,
                name=name,
                program_id=program.id if program else None,
                **kwargs
            )
            session.add(subject)
            session.flush()  # Get the ID
            logger.info(f"Created new subject: {code} - {name}")
        else:
            # Update name if provided and different
            if name and subject.name != name:
                subject.name = name
                logger.info(f"Updated subject name: {code} -> {name}")
        
        self.subjects_cache[cache_key] = subject
        return subject
    
    def create_offering(self, session, subject: Subject, offering_type: str,
                       term: str = None, section: str = None, **kwargs) -> Offering:
        """Create a new offering for a subject."""
        
        # Check if offering already exists
        existing = session.query(Offering).filter(
            Offering.subject_id == subject.id,
            Offering.type == offering_type,
            Offering.term == term,
            Offering.section == section
        ).first()
        
        if existing:
            logger.info(f"Offering already exists: {subject.code} {offering_type}")
            return existing
        
        offering = Offering(
            subject_id=subject.id,
            type=offering_type,
            term=term,
            section=section,
            **kwargs
        )
        session.add(offering)
        session.flush()
        
        logger.info(f"Created offering: {subject.code} {offering_type}")
        return offering
    
    def create_audit_record(self, session, offering: Offering, url: str,
                           html_content: str = None, status: int = 200) -> AuditSource:
        """Create audit record for scraping activity."""
        
        html_checksum = None
        if html_content:
            html_checksum = hashlib.md5(html_content.encode()).hexdigest()
        
        audit = AuditSource(
            offering_id=offering.id,
            url=url,
            status=status,
            html_checksum=html_checksum,
            parsed_ok=True,
            raw_snapshot=html_content.encode() if html_content else None
        )
        session.add(audit)
        return audit
    
    def parse_table_data(self, table_data: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Parse table data from scraper into structured format.
        
        Args:
            table_data: List of lists containing table row data
            
        Returns:
            List of dictionaries with parsed subject information
        """
        parsed_subjects = []
        
        for row in table_data:
            if not row or len(row) < 2:
                continue
            
            # Assuming table structure: [code, name, credits, semester, ...]
            # Adjust based on actual table structure from scraper
            subject_data = {
                'code': row[0].strip() if len(row) > 0 else '',
                'name': row[1].strip() if len(row) > 1 else '',
                'credits': self._parse_credits(row[2]) if len(row) > 2 else None,
                'semester': self._parse_semester(row[3]) if len(row) > 3 else None,
            }
            
            if subject_data['code'] and subject_data['name']:
                parsed_subjects.append(subject_data)
        
        return parsed_subjects
    
    def _parse_credits(self, credits_str: str) -> Optional[float]:
        """Parse credits from string."""
        if not credits_str:
            return None
        
        try:
            # Remove any non-numeric characters except decimal point
            cleaned = ''.join(c for c in credits_str if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _parse_semester(self, semester_str: str) -> Optional[int]:
        """Parse semester from string."""
        if not semester_str:
            return None
        
        try:
            # Extract numeric part
            cleaned = ''.join(c for c in semester_str if c.isdigit())
            semester = int(cleaned) if cleaned else None
            
            # Validate semester value
            if semester and semester in [1, 2, 3]:
                return semester
        except ValueError:
            pass
        
        return None
    
    def store_scraped_data(self, table_data: List[List[str]], 
                          program_name: str = "Default Program",
                          plan_year: int = None):
        """
        Store scraped table data to database using ORM models.
        
        Args:
            table_data: Raw table data from scraper
            program_name: Name of the academic program
            plan_year: Plan year for the program
        """
        parsed_data = self.parse_table_data(table_data)
        
        with get_db_session() as session:
            # Get or create program
            program = self.find_or_create_program(session, program_name, plan_year)
            
            subjects_created = 0
            offerings_created = 0
            
            for subject_data in parsed_data:
                try:
                    # Create or find subject
                    subject = self.find_or_create_subject(
                        session, 
                        code=subject_data['code'],
                        name=subject_data['name'],
                        program=program,
                        credits=subject_data.get('credits'),
                        semester=subject_data.get('semester')
                    )
                    
                    if subject_data['code'] not in [s['code'] for s in parsed_data[:parsed_data.index(subject_data)]]:
                        subjects_created += 1
                    
                    # Create default course offering
                    offering = self.create_offering(
                        session,
                        subject=subject,
                        offering_type='COURSE',
                        credits=subject_data.get('credits'),
                        semester=subject_data.get('semester'),
                        is_active=True
                    )
                    
                    if offering:
                        offerings_created += 1
                
                except Exception as e:
                    logger.error(f"Error processing subject {subject_data.get('code', 'unknown')}: {e}")
                    continue
        
        logger.info(f"Stored {subjects_created} subjects and {offerings_created} offerings to database")
        return subjects_created, offerings_created
    
    def store_previas_data(self, previas_data: Dict[str, Any]):
        """
        Store previas (prerequisite) data to database.
        
        Args:
            previas_data: Dictionary containing prerequisite information
        """
        with get_db_session() as session:
            # Process prerequisite data and create requirement groups/items
            # This would need to be customized based on the actual structure
            # of the previas_data from the scraper
            
            requirements_created = 0
            
            for subject_code, prereq_info in previas_data.items():
                try:
                    # Find the subject this prerequisite applies to
                    subject = session.query(Subject).filter(
                        Subject.code == subject_code
                    ).first()
                    
                    if not subject:
                        logger.warning(f"Subject not found for prereq: {subject_code}")
                        continue
                    
                    # Create offering if not exists
                    offering = session.query(Offering).filter(
                        Offering.subject_id == subject.id,
                        Offering.type == 'COURSE'
                    ).first()
                    
                    if not offering:
                        offering = self.create_offering(
                            session, subject, 'COURSE', is_active=True
                        )
                    
                    # Process prerequisite requirements
                    # This would need detailed implementation based on 
                    # the actual structure of previas_data
                    
                    requirements_created += 1
                
                except Exception as e:
                    logger.error(f"Error processing prereq for {subject_code}: {e}")
                    continue
        
        logger.info(f"Stored {requirements_created} prerequisite requirements to database")
        return requirements_created
