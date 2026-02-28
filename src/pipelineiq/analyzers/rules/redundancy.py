"""Redundancy analysis rules."""

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity, StepType


class RedundantCloneRule(AnalysisRule):
    """Detect multiple git clone operations.
    
    Cloning the repository multiple times across stages wastes time.
    Artifacts or shared workspaces should be used instead.
    """
    
    id = "redundant-clone"
    name = "Redundant Clone"
    description = "Multiple git clone operations across stages"
    category = Category.REDUNDANCY
    severity = Severity.HIGH
    
    # Patterns that indicate cloning
    CLONE_PATTERNS = [
        "git clone",
        "git checkout",
        "actions/checkout",
        "Clone Codebase",
        "gitclone",
    ]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find redundant clone operations."""
        findings: list[Finding] = []
        clone_stages: list[str] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                for step in job.steps:
                    is_clone = False
                    
                    # Check step name
                    if any(p.lower() in step.name.lower() for p in self.CLONE_PATTERNS):
                        is_clone = True
                    
                    # Check command
                    if step.type == StepType.RUN and step.command:
                        if any(p.lower() in step.command.lower() for p in self.CLONE_PATTERNS):
                            is_clone = True
                    
                    # Check plugin
                    if step.type == StepType.ACTION and step.plugin:
                        if "checkout" in step.plugin.lower():
                            is_clone = True
                    
                    if is_clone:
                        clone_stages.append(stage.name)
                        break  # Only count once per stage
        
        if len(clone_stages) > 1:
            findings.append(self._create_finding(
                message=f"Repository cloned multiple times (stages: {', '.join(clone_stages)})",
                suggestion="Use artifacts or shared workspace instead of re-cloning",
                location=Location(
                    file=pipeline.file_path,
                    stage=clone_stages[1],  # Report on second clone
                ),
                estimated_impact=f"Save {10 * (len(clone_stages) - 1)}-{30 * (len(clone_stages) - 1)} seconds",
            ))
        
        return findings
