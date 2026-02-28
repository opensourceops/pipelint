"""Resource analysis rules."""

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity, StepType


class ResourceSizingRule(AnalysisRule):
    """Detect potentially mis-sized compute resources.
    
    Analyzes step complexity vs allocated resources to find
    potential over or under-provisioning.
    """
    
    id = "resource-sizing"
    name = "Resource Sizing"
    description = "Potentially mis-sized compute resources"
    category = Category.RESOURCE
    severity = Severity.LOW
    
    # Commands that typically need more resources
    HEAVY_PATTERNS = [
        "docker build",
        "mvn",
        "gradle",
        "webpack",
        "npm run build",
        "cargo build",
        "go build",
        "make",
        "cmake",
    ]
    
    # Commands that typically need minimal resources
    LIGHT_PATTERNS = [
        "echo",
        "ls",
        "cat",
        "curl",
        "wget",
        "cp",
        "mv",
    ]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find resource sizing issues."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                runner = job.runner
                has_heavy_step = False
                
                for step in job.steps:
                    if step.type != StepType.RUN or not step.command:
                        continue
                    
                    # Check for heavy commands
                    if any(p in step.command.lower() for p in self.HEAVY_PATTERNS):
                        has_heavy_step = True
                        break
                
                # If heavy steps but no resource config
                if has_heavy_step and (not runner.resources or 
                    (not runner.resources.cpu and not runner.resources.memory)):
                    findings.append(self._create_finding(
                        message=f"Stage '{stage.name}' has heavy operations but no resource limits",
                        suggestion="Consider configuring CPU/memory resources for build operations",
                        location=Location(
                            file=pipeline.file_path,
                            stage=stage.id,
                            job=job.id,
                        ),
                        estimated_impact="Optimize resource usage and costs",
                    ))
        
        return findings
