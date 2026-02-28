"""Best practice analysis rules."""

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity


class MissingTimeoutRule(AnalysisRule):
    """Detect jobs/stages without timeout configuration.
    
    Jobs without timeouts can run indefinitely, wasting resources
    and blocking pipelines.
    """
    
    id = "missing-timeout"
    name = "Missing Timeout"
    description = "Jobs/stages without timeout configuration"
    category = Category.BEST_PRACTICE
    severity = Severity.MEDIUM
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find stages/jobs without timeout."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                if job.timeout_minutes is None:
                    findings.append(self._create_finding(
                        message=f"Job '{job.name}' in stage '{stage.name}' has no timeout configured",
                        suggestion="Add timeout configuration (recommended: 30-60 minutes)",
                        location=Location(
                            file=pipeline.file_path,
                            stage=stage.id,
                            job=job.id,
                        ),
                        estimated_impact="Prevent zombie jobs and resource waste",
                    ))
        
        return findings
