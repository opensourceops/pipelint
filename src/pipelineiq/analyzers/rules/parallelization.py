"""Parallelization-related analysis rules."""

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity


class ParallelStagesRule(AnalysisRule):
    """Detect independent stages that run sequentially.
    
    Uses the DAG to find stages that have no dependencies on each other
    but are not configured to run in parallel.
    """
    
    id = "parallel-stages"
    name = "Parallel Stages"
    description = "Independent stages that could run in parallel"
    category = Category.PARALLELIZATION
    severity = Severity.HIGH
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find independent stages not running in parallel."""
        findings: list[Finding] = []
        
        # Get parallelizable groups from DAG
        groups = dag.get_parallelizable_groups()
        
        for group in groups:
            if len(group) < 2:
                continue
            
            # Check if stages in this group are marked as parallel
            stages_in_group = [s for s in pipeline.stages if s.id in group]
            non_parallel = [s for s in stages_in_group if not s.parallel]
            
            # If we have multiple stages in a group and not all are parallel
            if len(non_parallel) >= 2:
                stage_names = [s.name for s in non_parallel]
                findings.append(self._create_finding(
                    message=f"Stages {stage_names} have no dependencies but run sequentially",
                    suggestion="Configure these stages to run in parallel",
                    location=Location(
                        file=pipeline.file_path,
                        stage=non_parallel[0].id,
                    ),
                    estimated_impact=f"Save {30 * (len(non_parallel) - 1)}-{60 * (len(non_parallel) - 1)} seconds",
                ))
        
        return findings


class ParallelStepsRule(AnalysisRule):
    """Detect independent steps within a job that could run in parallel.
    
    Identifies steps that don't depend on each other's output
    and could be grouped for parallel execution.
    """
    
    id = "parallel-steps"
    name = "Parallel Steps"
    description = "Independent steps that could run in parallel"
    category = Category.PARALLELIZATION
    severity = Severity.MEDIUM
    
    # Steps that are typically independent (can run in parallel)
    INDEPENDENT_PATTERNS = [
        ("lint", "test"),
        ("lint", "security"),
        ("test", "security"),
        ("format", "lint"),
    ]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find independent steps not running in parallel."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                if len(job.steps) < 2:
                    continue
                
                # Look for common independent step patterns
                step_names_lower = [s.name.lower() for s in job.steps]
                
                for pattern in self.INDEPENDENT_PATTERNS:
                    matches = []
                    for i, name in enumerate(step_names_lower):
                        for p in pattern:
                            if p in name:
                                matches.append(job.steps[i])
                                break
                    
                    if len(matches) >= 2:
                        step_names = [s.name for s in matches]
                        findings.append(self._create_finding(
                            message=f"Steps {step_names} in stage '{stage.name}' could run in parallel",
                            suggestion="Use step groups or parallel execution for independent steps",
                            location=Location(
                                file=pipeline.file_path,
                                stage=stage.id,
                                job=job.id,
                            ),
                            estimated_impact="Save 20-40% of combined step time",
                        ))
                        break  # One finding per job
        
        return findings
