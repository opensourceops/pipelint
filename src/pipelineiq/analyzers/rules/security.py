"""Security analysis rules."""

import re

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity, StepType


class PinnedVersionsRule(AnalysisRule):
    """Detect unpinned plugin/image versions.
    
    Using 'latest' or unpinned versions can cause:
    - Reproducibility issues
    - Security vulnerabilities
    - Unexpected breakages
    """
    
    id = "pinned-versions"
    name = "Pinned Versions"
    description = "Unpinned plugin/image versions"
    category = Category.SECURITY
    severity = Severity.HIGH
    
    # Tags that indicate unpinned versions
    UNPINNED_TAGS = ["latest", "main", "master", "develop", "dev", "edge", "nightly"]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find unpinned versions."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                for step in job.steps:
                    # Check image tags
                    if step.image:
                        finding = self._check_image(step.image, pipeline.file_path, stage, job, step)
                        if finding:
                            findings.append(finding)
                    
                    # Check plugin versions
                    if step.type == StepType.PLUGIN:
                        if not step.plugin_version or step.plugin_version in self.UNPINNED_TAGS:
                            findings.append(self._create_finding(
                                message=f"Plugin '{step.plugin}' uses unpinned version in stage '{stage.name}'",
                                suggestion="Pin to a specific version for reproducibility",
                                location=Location(
                                    file=pipeline.file_path,
                                    stage=stage.id,
                                    job=job.id,
                                    step=step.id,
                                ),
                                estimated_impact="Improve security and reproducibility",
                            ))
        
        return findings
    
    def _check_image(self, image: str, file_path: str, stage, job, step) -> Finding | None:
        """Check if image has unpinned tag."""
        # Parse image:tag format
        if ":" in image:
            tag = image.split(":")[-1]
            # Check for unpinned tags
            if tag.lower() in self.UNPINNED_TAGS:
                return self._create_finding(
                    message=f"Image '{image}' uses unpinned tag '{tag}' in stage '{stage.name}'",
                    suggestion=f"Pin to specific version (e.g., {image.split(':')[0]}:1.0.0)",
                    location=Location(
                        file=file_path,
                        stage=stage.id,
                        job=job.id,
                        step=step.id,
                    ),
                    estimated_impact="Improve security and reproducibility",
                )
        else:
            # No tag specified means :latest is used implicitly
            return self._create_finding(
                message=f"Image '{image}' has no tag (defaults to :latest) in stage '{stage.name}'",
                suggestion=f"Pin to specific version (e.g., {image}:1.0.0)",
                location=Location(
                    file=file_path,
                    stage=stage.id,
                    job=job.id,
                    step=step.id,
                ),
                estimated_impact="Improve security and reproducibility",
            )
        
        return None
