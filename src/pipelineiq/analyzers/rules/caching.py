"""Caching-related analysis rules."""

import re

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity, StepType


class CacheDependenciesRule(AnalysisRule):
    """Detect dependency installation without caching.
    
    Checks for package manager install commands (npm, pip, maven, etc.)
    that don't have corresponding cache configuration.
    """
    
    id = "cache-dependencies"
    name = "Cache Dependencies"
    description = "Detects dependency installation without caching"
    category = Category.CACHING
    severity = Severity.HIGH
    
    # Patterns that indicate dependency installation
    INSTALL_PATTERNS = [
        # Node.js
        (r"\bnpm\s+(ci|install)\b", "npm", "node_modules"),
        (r"\byarn\s+install\b", "yarn", "node_modules"),
        (r"\bpnpm\s+install\b", "pnpm", "node_modules"),
        # Python
        (r"\bpip\s+install\b", "pip", ".cache/pip"),
        (r"\bpip3\s+install\b", "pip", ".cache/pip"),
        (r"\bpoetry\s+install\b", "poetry", ".cache/pypoetry"),
        # Java
        (r"\bmvn\s+(install|package|compile)\b", "maven", ".m2/repository"),
        (r"\bgradle\s+(build|assemble)\b", "gradle", ".gradle"),
        # Go
        (r"\bgo\s+(mod\s+download|build)\b", "go", "go/pkg/mod"),
        # Ruby
        (r"\bbundle\s+install\b", "bundler", "vendor/bundle"),
        # Rust
        (r"\bcargo\s+build\b", "cargo", ".cargo"),
    ]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find install commands without cache configuration."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                # Check if job has cache configured
                has_cache = job.cache is not None
                
                for step in job.steps:
                    if step.type != StepType.RUN or not step.command:
                        continue
                    
                    # Check for install patterns
                    for pattern, pkg_manager, cache_path in self.INSTALL_PATTERNS:
                        if re.search(pattern, step.command):
                            if not has_cache:
                                findings.append(self._create_finding(
                                    message=f"{pkg_manager} install detected without caching in stage '{stage.name}'",
                                    suggestion=f"Add cache configuration for {cache_path}",
                                    location=Location(
                                        file=pipeline.file_path,
                                        stage=stage.id,
                                        job=job.id,
                                        step=step.id,
                                    ),
                                    estimated_impact="Save 30-120 seconds per run",
                                ))
                            break  # Only report once per step
        
        return findings


class CacheDockerLayersRule(AnalysisRule):
    """Detect Docker builds without layer caching.
    
    Checks for docker build commands that don't use --cache-from
    or BuildKit cache mounts.
    """
    
    id = "cache-docker-layers"
    name = "Cache Docker Layers"
    description = "Docker builds without layer caching"
    category = Category.CACHING
    severity = Severity.MEDIUM
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find docker build commands without caching."""
        findings: list[Finding] = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                for step in job.steps:
                    if step.type != StepType.RUN or not step.command:
                        continue
                    
                    # Check for docker build
                    if "docker build" in step.command or "docker buildx build" in step.command:
                        # Check for cache flags
                        has_cache = any([
                            "--cache-from" in step.command,
                            "--cache-to" in step.command,
                            "DOCKER_BUILDKIT=1" in step.command,
                            "--mount=type=cache" in step.command,
                        ])
                        
                        if not has_cache:
                            findings.append(self._create_finding(
                                message=f"Docker build without layer caching in stage '{stage.name}'",
                                suggestion="Add --cache-from or enable BuildKit caching",
                                location=Location(
                                    file=pipeline.file_path,
                                    stage=stage.id,
                                    job=job.id,
                                    step=step.id,
                                ),
                                estimated_impact="Save 1-5 minutes on rebuilds",
                            ))
        
        return findings
