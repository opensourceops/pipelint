"""Analysis result models."""

from typing import Optional

from pydantic import BaseModel, Field

from pipelineiq.models.finding import Category, Finding, Severity
from pipelineiq.models.pipeline import Pipeline


class AnalysisSummary(BaseModel):
    """Analysis summary statistics."""
    score: int  # 0-100
    total_findings: int
    by_severity: dict[Severity, int] = Field(default_factory=dict)
    by_category: dict[Category, int] = Field(default_factory=dict)
    estimated_time_savings: Optional[str] = None
    critical_path: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Complete analysis result."""
    pipeline: Pipeline
    findings: list[Finding]
    summary: AnalysisSummary
    dag_edges: list[tuple[str, str]] = Field(default_factory=list)
    ai_suggestions: list[str] = Field(default_factory=list)
    execution_time_ms: int
    analyzer_version: str
