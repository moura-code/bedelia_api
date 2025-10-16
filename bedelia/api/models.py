from __future__ import annotations
import uuid
from django.db import models
from django.db.models import Q, F
from django.core.validators import RegexValidator

# ------------------------------------------------------------
# Enum choices (prefer TextChoices over DB ENUM for smoother
# migrations; you can switch to native ENUM via a custom field
# if you truly need it.)
# ------------------------------------------------------------
class OfferingType(models.TextChoices):
    COURSE = "COURSE", "Course"
    EXAM = "EXAM", "Exam"


class GroupScope(models.TextChoices):
    ALL = "ALL", "ALL"
    ANY = "ANY", "ANY"
    NONE = "NONE", "NONE"


class GroupFlavor(models.TextChoices):
    GENERIC = "GENERIC", "GENERIC"
    APPROVALS = "APPROVALS", "APPROVALS"
    ACTIVITIES = "ACTIVITIES", "ACTIVITIES"
    COURSE_APPROVED = "COURSE_APPROVED", "COURSE_APPROVED"
    COURSE_ENROLLED = "COURSE_ENROLLED", "COURSE_ENROLLED"
    EXAM_APPROVED = "EXAM_APPROVED", "EXAM_APPROVED"
    EXAM_ENROLLED = "EXAM_ENROLLED", "EXAM_ENROLLED"
    COURSE_CREDITED = "COURSE_CREDITED", "COURSE_CREDITED"
    EXAM_CREDITED = "EXAM_CREDITED", "EXAM_CREDITED"


class ReqCondition(models.TextChoices):
    APPROVED = "APPROVED", "APPROVED"
    ENROLLED = "ENROLLED", "ENROLLED"
    CREDITED = "CREDITED", "CREDITED"


class TargetType(models.TextChoices):
    SUBJECT = "SUBJECT", "SUBJECT"
    OFFERING = "OFFERING", "OFFERING"


class DepKind(models.TextChoices):
    REQUIRES_ALL = "REQUIRES_ALL", "REQUIRES_ALL"
    ALTERNATIVE_ANY = "ALTERNATIVE_ANY", "ALTERNATIVE_ANY"
    FORBIDDEN_NONE = "FORBIDDEN_NONE", "FORBIDDEN_NONE"


class EquivalenceKind(models.TextChoices):
    FULL = "FULL", "Full Equivalence"
    PARTIAL = "PARTIAL", "Partial Equivalence"


TERM_VALIDATOR = RegexValidator(
    regex=r"^\d{4}S[12]$",
    message="term must look like 2025S1 or 2024S2"
)


# ------------------------------------------------------------
# Core models
# ------------------------------------------------------------
class BaseModel(models.Model):
    """Abstract base model with common fields for all models."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Program(BaseModel):
    """Academic programs/plans (e.g., "1997 - INGENIERIA EN COMPUTACION")."""

    name = models.CharField(max_length=255, help_text="Full name of the academic program")
    plan_year = models.IntegerField(null=True, blank=True, help_text="Year the plan was established")

    class Meta:
        db_table = "programs"
        verbose_name = "Program"
        verbose_name_plural = "Programs"
        ordering = ["plan_year", "name"]
        indexes = [
            models.Index(fields=["plan_year"], name="idx_program_year"),
        ]

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"<Program(id={self.id}, name='{self.name}', plan_year={self.plan_year})>"


class Subject(BaseModel):
    """Canonical subjects/courses (UCB/FIng codes)."""

    program = models.ForeignKey(
        Program, null=True, blank=True, on_delete=models.SET_NULL, related_name="subjects",
        help_text="Academic program this subject belongs to"
    )
    code = models.CharField(max_length=16, db_index=True, help_text="Subject code (e.g., UCB/FIng code)")
    name = models.CharField(max_length=255, help_text="Full name of the subject")
    credits = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Number of credits for this subject"
    )
    dept = models.CharField(max_length=100, null=True, blank=True, help_text="Department offering this subject")
    description = models.TextField(null=True, blank=True, help_text="Detailed description of the subject")
    semester = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Recommended semester (1 or 2)"
    )

    class Meta:
        db_table = "subjects"
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ["code", "name"]
        constraints = [
            models.UniqueConstraint(fields=["program", "code"], name="uq_subject_program_code"),
            models.CheckConstraint(
                check=Q(semester__in=[1, 2]) | Q(semester__isnull=True),
                name="ck_subject_semester_in_1_2_or_null",
            ),
        ]
        indexes = [
            models.Index(fields=["code"], name="idx_subjects_code"),
            models.Index(fields=["program"], name="idx_subjects_program"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
    
    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, code='{self.code}', name='{self.name}')>"


class SubjectAlias(BaseModel):
    """Subject synonyms/variants for scraping & matching."""

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="aliases",
        help_text="Subject this alias refers to"
    )
    alias_code = models.CharField(max_length=50, null=True, blank=True, help_text="Alternative code for the subject")
    alias_name = models.CharField(max_length=255, null=True, blank=True, help_text="Alternative name for the subject")

    class Meta:
        db_table = "subject_aliases"
        verbose_name = "Subject Alias"
        verbose_name_plural = "Subject Aliases"
        ordering = ["subject", "alias_code"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "alias_code"], name="uq_alias_code_per_subject"),
            models.UniqueConstraint(fields=["subject", "alias_name"], name="uq_alias_name_per_subject"),
        ]
        indexes = [
            models.Index(fields=["alias_code"], name="idx_alias_code"),
            models.Index(fields=["alias_name"], name="idx_alias_name"),
        ]

    def __str__(self) -> str:
        return self.alias_code or self.alias_name or str(self.id)
    
    def __repr__(self) -> str:
        return f"<SubjectAlias(id={self.id}, subject_id={self.subject_id}, alias_code='{self.alias_code}')>"


class Offering(BaseModel):
    """Course/exam offerings (per term/section)."""

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="offerings",
        help_text="Subject this offering is for"
    )
    type = models.CharField(
        max_length=10, choices=OfferingType.choices,
        help_text="Type of offering: COURSE or EXAM"
    )
    term = models.CharField(
        max_length=8, null=True, blank=True, validators=[TERM_VALIDATOR],
        help_text="Academic term (e.g., 2025S1, 2024S2)"
    )
    section = models.CharField(max_length=32, null=True, blank=True, help_text="Section identifier")
    semester = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Semester number (1, 2, or 3)"
    )
    credits = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Number of credits for this offering"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this offering is currently active")
    url_source = models.URLField(max_length=500, null=True, blank=True, help_text="Source URL for this offering")
    scraped_at = models.DateTimeField(null=True, blank=True, help_text="Last time data was scraped")
    html_hash = models.CharField(max_length=64, null=True, blank=True, help_text="Hash of scraped HTML content")

    class Meta:
        db_table = "offerings"
        verbose_name = "Offering"
        verbose_name_plural = "Offerings"
        ordering = ["-term", "subject__code", "type", "section"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "type", "term", "section"], name="uq_offering_unique"),
            models.CheckConstraint(
                check=Q(semester__in=[1, 2, 3]) | Q(semester__isnull=True),
                name="ck_offering_semester_in_1_2_3_or_null",
            ),
        ]
        indexes = [
            models.Index(fields=["subject"], name="idx_offerings_subject"),
            models.Index(fields=["type", "term"], name="idx_offerings_type_term"),
            models.Index(fields=["is_active"], name="idx_offerings_active"),
            models.Index(fields=["semester"], name="idx_offerings_semester"),
        ]

    def __str__(self) -> str:
        return f"{self.subject.code} {self.type} {self.term or ''} {self.section or ''}".strip()
    
    def __repr__(self) -> str:
        return f"<Offering(id={self.id}, subject_code='{self.subject.code}', type='{self.type}', term='{self.term}')>"


class OfferingLink(BaseModel):
    """Useful links associated with an offering (syllabus, moodle, etc.)."""

    offering = models.ForeignKey(
        Offering, on_delete=models.CASCADE, related_name="links",
        help_text="Offering this link is associated with"
    )
    kind = models.CharField(
        max_length=32,
        help_text="Type of link (e.g., syllabus, moodle, slides)"
    )
    url = models.URLField(max_length=500, help_text="URL of the resource")
    title = models.CharField(max_length=255, null=True, blank=True, help_text="Display title for the link")

    class Meta:
        db_table = "offering_links"
        verbose_name = "Offering Link"
        verbose_name_plural = "Offering Links"
        ordering = ["offering", "kind"]
        indexes = [
            models.Index(fields=["offering"], name="idx_offering_links_offering"),
            models.Index(fields=["kind"], name="idx_offering_links_kind"),
        ]
    
    def __str__(self) -> str:
        return f"{self.offering} - {self.kind}"
    
    def __repr__(self) -> str:
        return f"<OfferingLink(id={self.id}, offering_id={self.offering_id}, kind='{self.kind}')>"


class RequirementGroup(BaseModel):
    """Groups with scope (ALL/ANY/NONE) and optional min_required for ANY."""

    offering = models.ForeignKey(
        Offering, on_delete=models.CASCADE, related_name="requirement_groups",
        help_text="Offering these requirements apply to"
    )
    scope = models.CharField(
        max_length=8, choices=GroupScope.choices,
        help_text="Scope: ALL (all required), ANY (min_required), or NONE (forbidden)"
    )
    flavor = models.CharField(
        max_length=32, choices=GroupFlavor.choices, default=GroupFlavor.GENERIC,
        help_text="Semantic flavor of this requirement group"
    )
    min_required = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Minimum items required (only for ANY scope)"
    )
    note = models.CharField(max_length=500, null=True, blank=True, help_text="Additional notes or clarifications")
    order_index = models.PositiveIntegerField(default=0, help_text="Display order within the offering")

    class Meta:
        db_table = "requirement_groups"
        verbose_name = "Requirement Group"
        verbose_name_plural = "Requirement Groups"
        ordering = ["offering", "order_index"]
        constraints = [
            # Enforce min_required only when ANY (>=1); null otherwise
            models.CheckConstraint(
                check=(Q(scope=GroupScope.ANY) & Q(min_required__gte=1)) |
                      (Q(scope__in=[GroupScope.ALL, GroupScope.NONE]) & Q(min_required__isnull=True)),
                name="ck_group_min_required_semantics",
            ),
        ]
        indexes = [
            models.Index(fields=["offering", "order_index"], name="idx_req_groups_offering"),
        ]

    def __str__(self) -> str:
        return f"{self.offering} [{self.scope}]"
    
    def __repr__(self) -> str:
        return f"<RequirementGroup(id={self.id}, offering_id={self.offering_id}, scope='{self.scope}')>"
    
    def clean(self):
        """Validate min_required based on scope."""
        from django.core.exceptions import ValidationError
        if self.scope == GroupScope.ANY and not self.min_required:
            raise ValidationError("min_required must be set for ANY scope")
        if self.scope in [GroupScope.ALL, GroupScope.NONE] and self.min_required is not None:
            raise ValidationError("min_required must be null for ALL or NONE scope")


class RequirementGroupLink(BaseModel):
    """Parent/child links to form a tree/DAG of requirement groups."""

    parent_group = models.ForeignKey(
        RequirementGroup, on_delete=models.CASCADE, related_name="child_links",
        help_text="Parent requirement group"
    )
    child_group = models.ForeignKey(
        RequirementGroup, on_delete=models.CASCADE, related_name="parent_links",
        help_text="Child requirement group"
    )
    order_index = models.PositiveIntegerField(default=0, help_text="Order of child within parent")

    class Meta:
        db_table = "requirement_group_links"
        verbose_name = "Requirement Group Link"
        verbose_name_plural = "Requirement Group Links"
        ordering = ["parent_group", "order_index"]
        constraints = [
            models.UniqueConstraint(fields=["parent_group", "child_group"], name="uq_group_parent_child"),
            models.CheckConstraint(check=~Q(parent_group=F("child_group")), name="ck_group_no_self_link"),
        ]
        indexes = [
            models.Index(fields=["parent_group", "order_index"], name="idx_req_group_links_parent"),
            models.Index(fields=["child_group"], name="idx_req_group_links_child"),
        ]
    
    def __str__(self) -> str:
        return f"{self.parent_group} -> {self.child_group}"
    
    def __repr__(self) -> str:
        return f"<RequirementGroupLink(id={self.id}, parent={self.parent_group_id}, child={self.child_group_id})>"
    
    def clean(self):
        """Prevent self-referential links."""
        from django.core.exceptions import ValidationError
        if self.parent_group_id == self.child_group_id:
            raise ValidationError("A requirement group cannot link to itself")


class RequirementItem(BaseModel):
    """Leaf requirement items (subject or offering targets)."""

    group = models.ForeignKey(
        RequirementGroup, on_delete=models.CASCADE, related_name="items",
        help_text="Requirement group this item belongs to"
    )
    target_type = models.CharField(
        max_length=16, choices=TargetType.choices,
        help_text="Type of target: SUBJECT or OFFERING"
    )
    target_subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Target subject (if target_type is SUBJECT)"
    )
    target_offering = models.ForeignKey(
        Offering, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Target offering (if target_type is OFFERING)"
    )
    condition = models.CharField(
        max_length=16, choices=ReqCondition.choices, default=ReqCondition.APPROVED,
        help_text="Required condition: APPROVED, ENROLLED, or CREDITED"
    )
    alt_code = models.CharField(max_length=50, null=True, blank=True, help_text="Fallback code if ID not resolved")
    alt_label = models.CharField(max_length=255, null=True, blank=True, help_text="Display label for this item")
    order_index = models.PositiveIntegerField(default=0, help_text="Display order within the group")

    class Meta:
        db_table = "requirement_items"
        verbose_name = "Requirement Item"
        verbose_name_plural = "Requirement Items"
        ordering = ["group", "order_index"]
        constraints = [
            # Exactly one of subject/offering must be set and must match target_type
            models.CheckConstraint(
                check=(Q(target_type=TargetType.SUBJECT) & Q(target_subject__isnull=False) & Q(target_offering__isnull=True)) |
                      (Q(target_type=TargetType.OFFERING) & Q(target_offering__isnull=False) & Q(target_subject__isnull=True)),
                name="ck_item_target_exclusive",
            ),
        ]
        indexes = [
            models.Index(fields=["group", "order_index"], name="idx_req_items_group"),
            models.Index(fields=["target_subject"], name="idx_req_items_target_subj"),
            models.Index(fields=["target_offering"], name="idx_req_items_target_off"),
            models.Index(fields=["condition"], name="idx_req_items_condition"),
        ]

    def __str__(self) -> str:
        return self.alt_label or f"{self.target_type}:{self.target_subject_id or self.target_offering_id}"
    
    def __repr__(self) -> str:
        return f"<RequirementItem(id={self.id}, group_id={self.group_id}, target_type='{self.target_type}')>"
    
    def clean(self):
        """Validate target consistency with target_type."""
        from django.core.exceptions import ValidationError
        if self.target_type == TargetType.SUBJECT:
            if not self.target_subject:
                raise ValidationError("target_subject must be set when target_type is SUBJECT")
            if self.target_offering:
                raise ValidationError("target_offering must be null when target_type is SUBJECT")
        elif self.target_type == TargetType.OFFERING:
            if not self.target_offering:
                raise ValidationError("target_offering must be set when target_type is OFFERING")
            if self.target_subject:
                raise ValidationError("target_subject must be null when target_type is OFFERING")


class SubjectEquivalence(BaseModel):
    """Equivalences between subjects (unordered pairs)."""

    subject_a = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="equiv_as_a",
        help_text="First subject in the equivalence relationship"
    )
    subject_b = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="equiv_as_b",
        help_text="Second subject in the equivalence relationship"
    )
    kind = models.CharField(
        max_length=16, choices=EquivalenceKind.choices,
        help_text="Type of equivalence: FULL or PARTIAL"
    )
    note = models.CharField(max_length=500, null=True, blank=True, help_text="Additional notes about the equivalence")

    class Meta:
        db_table = "subject_equivalences"
        verbose_name = "Subject Equivalence"
        verbose_name_plural = "Subject Equivalences"
        ordering = ["subject_a", "subject_b"]
        constraints = [
            # Disallow self-equivalence
            models.CheckConstraint(check=~Q(subject_a=F("subject_b")), name="ck_equiv_not_self"),
        
        ]
        indexes = [
            models.Index(fields=["subject_a"], name="idx_equiv_subject_a"),
            models.Index(fields=["subject_b"], name="idx_equiv_subject_b"),
            models.Index(fields=["kind"], name="idx_equiv_kind"),
        ]
    
    def __str__(self) -> str:
        return f"{self.subject_a.code} ≡ {self.subject_b.code} ({self.kind})"
    
    def __repr__(self) -> str:
        return f"<SubjectEquivalence(id={self.id}, subject_a_id={self.subject_a_id}, subject_b_id={self.subject_b_id}, kind='{self.kind}')>"
    
    def clean(self):
        """Prevent self-equivalence."""
        from django.core.exceptions import ValidationError
        if self.subject_a_id == self.subject_b_id:
            raise ValidationError("A subject cannot be equivalent to itself")


class AuditSource(BaseModel):
    """Scraping/audit trail for source pages."""

    offering = models.ForeignKey(
        Offering, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Associated offering (if applicable)"
    )
    url = models.URLField(max_length=500, help_text="URL of the scraped page")
    fetched_at = models.DateTimeField(auto_now_add=True, help_text="When the data was fetched")
    status = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="HTTP status code of the request"
    )
    html_checksum = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Checksum of the HTML content"
    )
    parsed_ok = models.BooleanField(
        null=True, blank=True,
        help_text="Whether parsing was successful"
    )
    raw_snapshot = models.BinaryField(
        null=True, blank=True,
        help_text="Raw HTML snapshot (consider external storage for large files)"
    )

    class Meta:
        db_table = "audit_sources"
        verbose_name = "Audit Source"
        verbose_name_plural = "Audit Sources"
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["offering"], name="idx_audit_offering"),
            models.Index(fields=["fetched_at"], name="idx_audit_time"),
            models.Index(fields=["status"], name="idx_audit_status"),
            models.Index(fields=["parsed_ok"], name="idx_audit_parsed"),
        ]
    
    def __str__(self) -> str:
        return f"Audit: {self.url[:50]} at {self.fetched_at}"
    
    def __repr__(self) -> str:
        return f"<AuditSource(id={self.id}, url='{self.url[:50]}', status={self.status})>"


class DependencyEdge(BaseModel):
    """Materialized dependency relationships for fast reachability queries."""

    from_type = models.CharField(
        max_length=16, choices=TargetType.choices,
        help_text="Type of source: SUBJECT or OFFERING"
    )
    from_subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.CASCADE, related_name="dep_out_subject",
        help_text="Source subject (if from_type is SUBJECT)"
    )
    from_offering = models.ForeignKey(
        Offering, null=True, blank=True, on_delete=models.CASCADE, related_name="dep_out_offering",
        help_text="Source offering (if from_type is OFFERING)"
    )
    to_offering = models.ForeignKey(
        Offering, on_delete=models.CASCADE, related_name="dep_in",
        help_text="Target offering that has this dependency"
    )
    group = models.ForeignKey(
        RequirementGroup, on_delete=models.CASCADE, related_name="dependency_edges",
        help_text="Requirement group this dependency comes from"
    )
    kind = models.CharField(
        max_length=32, choices=DepKind.choices,
        help_text="Type of dependency: REQUIRES_ALL, ALTERNATIVE_ANY, or FORBIDDEN_NONE"
    )
    condition = models.CharField(
        max_length=16, choices=ReqCondition.choices, default=ReqCondition.APPROVED,
        help_text="Required condition for the dependency"
    )

    class Meta:
        db_table = "dependency_edges"
        verbose_name = "Dependency Edge"
        verbose_name_plural = "Dependency Edges"
        ordering = ["to_offering", "kind"]
        constraints = [
            models.CheckConstraint(
                check=(Q(from_type=TargetType.SUBJECT) & Q(from_subject__isnull=False) & Q(from_offering__isnull=True)) |
                      (Q(from_type=TargetType.OFFERING) & Q(from_offering__isnull=False) & Q(from_subject__isnull=True)),
                name="ck_dep_from_target_exclusive",
            ),
        ]
        indexes = [
            models.Index(fields=["from_subject"], name="idx_dep_from_subject"),
            models.Index(fields=["from_offering"], name="idx_dep_from_off"),
            models.Index(fields=["to_offering"], name="idx_dep_to_offering"),
            models.Index(fields=["kind"], name="idx_dep_kind"),
            models.Index(fields=["condition"], name="idx_dep_condition"),
        ]

    def __str__(self) -> str:
        return f"{self.from_type} → {self.to_offering_id} ({self.kind})"
    
    def __repr__(self) -> str:
        return f"<DependencyEdge(id={self.id}, from_type='{self.from_type}', to_offering_id={self.to_offering_id}, kind='{self.kind}')>"
    
    def clean(self):
        """Validate from fields consistency with from_type."""
        from django.core.exceptions import ValidationError
        if self.from_type == TargetType.SUBJECT:
            if not self.from_subject:
                raise ValidationError("from_subject must be set when from_type is SUBJECT")
            if self.from_offering:
                raise ValidationError("from_offering must be null when from_type is SUBJECT")
        elif self.from_type == TargetType.OFFERING:
            if not self.from_offering:
                raise ValidationError("from_offering must be set when from_type is OFFERING")
            if self.from_subject:
                raise ValidationError("from_subject must be null when from_type is OFFERING")
