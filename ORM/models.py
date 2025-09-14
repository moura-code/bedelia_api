"""
SQLAlchemy ORM Models for Bedelia Academic System

This module defines the database models based on the PostgreSQL schema
for managing academic programs, subjects, offerings, and prerequisites.
"""

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    Numeric,
    SmallInteger,
    UUID,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    LargeBinary,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.schema import CreateSchema
import uuid
from datetime import datetime
from typing import Optional, List

Base = declarative_base()

# Define PostgreSQL Enums
offering_type_enum = ENUM("COURSE", "EXAM", name="offering_type", create_type=False)

group_scope_enum = ENUM("ALL", "ANY", "NONE", name="group_scope", create_type=False)

group_flavor_enum = ENUM(
    "GENERIC",
    "APPROVALS",
    "ACTIVITIES",
    "COURSE_APPROVED",
    "COURSE_ENROLLED",
    "EXAM_APPROVED",
    "EXAM_ENROLLED",
    "COURSE_CREDITED",
    "EXAM_CREDITED",
    name="group_flavor",
    create_type=False,
)

req_condition_enum = ENUM(
    "APPROVED", "ENROLLED", "CREDITED", name="req_condition", create_type=False
)

target_type_enum = ENUM("SUBJECT", "OFFERING", name="target_type", create_type=False)

dep_kind_enum = ENUM(
    "REQUIRES_ALL",
    "ALTERNATIVE_ANY",
    "FORBIDDEN_NONE",
    name="dep_kind",
    create_type=False,
)


class Program(Base):
    """Academic programs/plans"""

    __tablename__ = "programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    plan_year = Column(Integer)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    subjects = relationship("Subject", back_populates="program")


class Subject(Base):
    """Canonical subjects/courses"""

    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="SET NULL")
    )
    code = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    credits = Column(Numeric(6, 2))
    dept = Column(Text)
    description = Column(Text)
    semester = Column(Integer)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("program_id", "code"),
        CheckConstraint("semester IN (1, 2) OR semester IS NULL"),
    )

    # Relationships
    program = relationship("Program", back_populates="subjects")
    aliases = relationship(
        "SubjectAlias", back_populates="subject", cascade="all, delete-orphan"
    )
    offerings = relationship(
        "Offering", back_populates="subject", cascade="all, delete-orphan"
    )


class SubjectAlias(Base):
    """Subject synonyms/variants for scraping"""

    __tablename__ = "subject_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias_code = Column(Text)
    alias_name = Column(Text)

    # Constraints
    __table_args__ = (
        UniqueConstraint("subject_id", "alias_code"),
        UniqueConstraint("subject_id", "alias_name"),
    )

    # Relationships
    subject = relationship("Subject", back_populates="aliases")


class Offering(Base):
    """Course/exam offerings"""

    __tablename__ = "offerings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(offering_type_enum, nullable=False)
    term = Column(Text)  # e.g., 2025S1, 2024S2
    section = Column(Text)  # commission/section
    semester = Column(SmallInteger)  # 1=first, 2=second, 3=both
    credits = Column(Numeric(6, 2))
    is_active = Column(Boolean, nullable=False, default=True)
    url_source = Column(Text)
    scraped_at = Column(DateTime(timezone=True))
    html_hash = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("subject_id", "type", "term", "section"),
        CheckConstraint("semester IN (1, 2, 3) OR semester IS NULL"),
    )

    # Relationships
    subject = relationship("Subject", back_populates="offerings")
    links = relationship(
        "OfferingLink", back_populates="offering", cascade="all, delete-orphan"
    )
    requirement_groups = relationship(
        "RequirementGroup", back_populates="offering", cascade="all, delete-orphan"
    )


class OfferingLink(Base):
    """Links associated with offerings"""

    __tablename__ = "offering_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(
        Text, nullable=False
    )  # 'SYLLABUS', 'MOODLE', 'PROGRAM', 'GITHUB', etc.
    url = Column(Text, nullable=False)
    title = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    offering = relationship("Offering", back_populates="links")


class RequirementGroup(Base):
    """Requirement groups with scope and nesting"""

    __tablename__ = "requirement_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope = Column(group_scope_enum, nullable=False)
    flavor = Column(group_flavor_enum, nullable=False, default="GENERIC")
    min_required = Column(Integer)
    note = Column(Text)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(scope <> 'ANY') OR (min_required IS NULL OR min_required >= 1)"
        ),
        CheckConstraint(
            "(scope <> 'ALL') OR (min_required IS NULL OR min_required >= 1)"
        ),
    )

    # Relationships
    offering = relationship("Offering", back_populates="requirement_groups")
    items = relationship(
        "RequirementItem", back_populates="group", cascade="all, delete-orphan"
    )
    parent_links = relationship(
        "RequirementGroupLink",
        foreign_keys="RequirementGroupLink.child_group_id",
        back_populates="child_group",
    )
    child_links = relationship(
        "RequirementGroupLink",
        foreign_keys="RequirementGroupLink.parent_group_id",
        back_populates="parent_group",
    )


class RequirementGroupLink(Base):
    """Links between parent and child requirement groups"""

    __tablename__ = "requirement_group_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requirement_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requirement_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("parent_group_id", "child_group_id"),
        CheckConstraint("parent_group_id <> child_group_id"),
    )

    # Relationships
    parent_group = relationship(
        "RequirementGroup", foreign_keys=[parent_group_id], back_populates="child_links"
    )
    child_group = relationship(
        "RequirementGroup", foreign_keys=[child_group_id], back_populates="parent_links"
    )


class RequirementItem(Base):
    """Individual requirement items"""

    __tablename__ = "requirement_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requirement_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type = Column(target_type_enum, nullable=False)
    target_subject_id = Column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE")
    )
    target_offering_id = Column(
        UUID(as_uuid=True), ForeignKey("offerings.id", ondelete="CASCADE")
    )
    condition = Column(req_condition_enum, nullable=False, default="APPROVED")
    alt_code = Column(Text)  # fallback if ID not resolved
    alt_label = Column(Text)  # display text as-is
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(target_type='SUBJECT' AND target_subject_id IS NOT NULL AND target_offering_id IS NULL) OR "
            "(target_type='OFFERING' AND target_offering_id IS NOT NULL AND target_subject_id IS NULL)"
        ),
    )

    # Relationships
    group = relationship("RequirementGroup", back_populates="items")
    target_subject = relationship("Subject")
    target_offering = relationship("Offering")


class SubjectEquivalence(Base):
    """Subject equivalences"""

    __tablename__ = "subject_equivalences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id_a = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id_b = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(Text, nullable=False)
    note = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("kind IN ('FULL', 'PARTIAL')"),
        CheckConstraint("subject_id_a <> subject_id_b"),
        UniqueConstraint("subject_id_a", "subject_id_b"),
    )


class AuditSource(Base):
    """Scraping audit trail"""

    __tablename__ = "audit_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offering_id = Column(
        UUID(as_uuid=True), ForeignKey("offerings.id", ondelete="CASCADE")
    )
    url = Column(Text, nullable=False)
    fetched_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status = Column(Integer)
    html_checksum = Column(Text)
    parsed_ok = Column(Boolean)
    raw_snapshot = Column(LargeBinary)


class DependencyEdge(Base):
    """Materialized dependency relationships"""

    __tablename__ = "dependency_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_type = Column(target_type_enum, nullable=False)
    from_subject_id = Column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE")
    )
    from_offering_id = Column(
        UUID(as_uuid=True), ForeignKey("offerings.id", ondelete="CASCADE")
    )
    to_offering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requirement_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(dep_kind_enum, nullable=False)
    condition = Column(req_condition_enum, nullable=False, default="APPROVED")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(from_type='SUBJECT' AND from_subject_id IS NOT NULL AND from_offering_id IS NULL) OR "
            "(from_type='OFFERING' AND from_offering_id IS NOT NULL AND from_subject_id IS NULL)"
        ),
        # Indexes
        Index("idx_dep_from_subject", "from_subject_id"),
        Index("idx_dep_from_off", "from_offering_id"),
        Index("idx_dep_to_offering", "to_offering_id"),
        Index("idx_dep_kind", "kind"),
    )


# Additional indexes as specified in schema
Index("idx_subjects_code", Subject.code)
Index("idx_subjects_program", Subject.program_id)
Index("idx_offerings_subject", Offering.subject_id)
Index("idx_offerings_type_term", Offering.type, Offering.term)
Index("idx_offerings_active", Offering.is_active)
Index("idx_offerings_semester", Offering.semester)
Index(
    "idx_req_groups_offering",
    RequirementGroup.offering_id,
    RequirementGroup.order_index,
)
Index(
    "idx_req_group_links_parent",
    RequirementGroupLink.parent_group_id,
    RequirementGroupLink.order_index,
)
Index("idx_req_items_group", RequirementItem.group_id, RequirementItem.order_index)
Index("idx_req_items_target_subj", RequirementItem.target_subject_id)
Index("idx_req_items_target_off", RequirementItem.target_offering_id)
