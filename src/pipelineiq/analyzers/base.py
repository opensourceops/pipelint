"""Base analysis rule interface."""

from abc import ABC, abstractmethod
from uuid import uuid4

from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Platform, Severity


class AnalysisRule(ABC):
    """Base class for all analysis rules.
    
    Each rule checks for a specific issue or optimization opportunity
    in CI pipelines.
    """
    
    id: str
    name: str
    description: str
    category: Category
    severity: Severity
    platforms: list[Platform] = [Platform.HARNESS]  # Supported platforms
    enabled: bool = True
    
    @abstractmethod
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Execute rule analysis on the pipeline.
        
        Args:
            pipeline: Pipeline IR to analyze
            dag: DAG representation of the pipeline
            
        Returns:
            List of findings (issues found)
        """
        pass
    
    def _create_finding(
        self,
        message: str,
        suggestion: str,
        location: Location,
        estimated_impact: str | None = None,
    ) -> Finding:
        """Helper to create a Finding with rule metadata.
        
        Args:
            message: Issue description
            suggestion: How to fix it
            location: Where the issue was found
            estimated_impact: Expected improvement
            
        Returns:
            Finding instance
        """
        return Finding(
            id=str(uuid4()),
            rule_id=self.id,
            rule_name=self.name,
            severity=self.severity,
            category=self.category,
            message=message,
            suggestion=suggestion,
            location=location,
            estimated_impact=estimated_impact,
        )
