"""Analysis finding models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Finding categories."""
    CACHING = "caching"
    PARALLELIZATION = "parallelization"
    SECURITY = "security"
    BEST_PRACTICE = "best-practice"
    RESOURCE = "resource"
    REDUNDANCY = "redundancy"
    RELIABILITY = "reliability"


class Location(BaseModel):
    """Finding location in source."""
    file: str
    line: Optional[int] = None
    stage: Optional[str] = None
    job: Optional[str] = None
    step: Optional[str] = None


class Fix(BaseModel):
    """Suggested fix for a finding."""
    type: str  # add, remove, modify
    description: str
    original: Optional[str] = None
    replacement: str


class Finding(BaseModel):
    """Analysis finding/issue."""
    id: str
    rule_id: str
    rule_name: str
    severity: Severity
    category: Category
    message: str
    suggestion: str
    location: Location
    estimated_impact: Optional[str] = None
    fix: Optional[Fix] = None
    references: list[str] = Field(default_factory=list)
    ai_explanation: Optional[str] = None
