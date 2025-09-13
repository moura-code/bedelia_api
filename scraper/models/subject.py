"""Data models for subject and requirement information."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


@dataclass
class RequirementNode:
    """Represents a node in the requirements tree structure."""
    
    type: str  # "ALL", "ANY", "NONE", "LEAF"
    label: str
    children: List['RequirementNode'] = field(default_factory=list)
    
    # Leaf-specific properties
    rule: Optional[str] = None
    required_count: Optional[int] = None
    credits: Optional[int] = None
    plan: Optional[str] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    value: Optional[str] = None
    raw: Optional[str] = None

    def is_leaf(self) -> bool:
        """Check if this node is a leaf node."""
        return self.type == "LEAF"

    def has_children(self) -> bool:
        """Check if this node has children."""
        return len(self.children) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "type": self.type,
            "label": self.label
        }
        
        if self.has_children():
            result["children"] = [child.to_dict() for child in self.children]
        
        # Add leaf-specific properties if they exist
        if self.rule:
            result["rule"] = self.rule
        if self.required_count is not None:
            result["required_count"] = self.required_count
        if self.credits is not None:
            result["credits"] = self.credits
        if self.plan:
            result["plan"] = self.plan
        if self.items:
            result["items"] = self.items
        if self.value:
            result["value"] = self.value
        if self.raw:
            result["raw"] = self.raw
            
        return result


@dataclass
class SubjectInfo:
    """Information about a subject and its prerequisites."""
    
    code: str
    name: str
    requirements: Optional[RequirementNode] = None
    prerequisites: List[str] = field(default_factory=list)  # Legacy field for compatibility
    
    def __post_init__(self):
        """Validate subject information after initialization."""
        if not self.code.strip():
            raise ValueError("Subject code cannot be empty")
        if not self.name.strip():
            raise ValueError("Subject name cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "code": self.code,
            "name": self.name,
            "prerequisites": self.prerequisites
        }
        
        if self.requirements:
            result["requirements"] = self.requirements.to_dict()
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubjectInfo':
        """Create SubjectInfo from dictionary."""
        requirements = None
        if "requirements" in data and data["requirements"]:
            requirements = RequirementNode(**data["requirements"])
        
        return cls(
            code=data["code"],
            name=data["name"],
            requirements=requirements,
            prerequisites=data.get("prerequisites", [])
        )
