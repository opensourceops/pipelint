"""Analysis engine - orchestrates pipeline analysis."""

import time
from typing import Type

from pipelineiq import __version__
from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.analyzers.rules.best_practices import MissingTimeoutRule
from pipelineiq.analyzers.rules.caching import CacheDependenciesRule, CacheDockerLayersRule
from pipelineiq.analyzers.rules.parallelization import ParallelStagesRule, ParallelStepsRule
from pipelineiq.analyzers.rules.redundancy import RedundantCloneRule
from pipelineiq.analyzers.rules.resource import ResourceSizingRule
from pipelineiq.analyzers.rules.security import PinnedVersionsRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import (
    AnalysisResult,
    AnalysisSummary,
    Category,
    Finding,
    Pipeline,
    Severity,
)


class AnalysisEngine:
    """Engine that orchestrates pipeline analysis.
    
    Runs all enabled rules against a pipeline and aggregates results.
    """
    
    def __init__(self, rules: list[AnalysisRule] | None = None):
        """Initialize the analysis engine.
        
        Args:
            rules: List of rules to run. If None, uses default rules.
        """
        self.rules = rules if rules is not None else self._get_default_rules()
    
    def _get_default_rules(self) -> list[AnalysisRule]:
        """Get the default set of analysis rules."""
        return [
            CacheDependenciesRule(),
            CacheDockerLayersRule(),
            ParallelStagesRule(),
            ParallelStepsRule(),
            MissingTimeoutRule(),
            RedundantCloneRule(),
            PinnedVersionsRule(),
            ResourceSizingRule(),
        ]
    
    def analyze(
        self,
        pipeline: Pipeline,
        severity_filter: Severity | None = None,
        rule_ids: list[str] | None = None,
    ) -> AnalysisResult:
        """Run analysis on the pipeline.
        
        Args:
            pipeline: Pipeline IR to analyze
            severity_filter: Only return findings of this severity or higher
            rule_ids: Only run these rules (by ID)
            
        Returns:
            Complete analysis result
        """
        start_time = time.time()
        
        # Build DAG
        dag = PipelineDAG(pipeline)
        
        # Collect all findings
        all_findings: list[Finding] = []
        
        for rule in self.rules:
            # Skip disabled rules
            if not rule.enabled:
                continue
            
            # Skip if rule_ids filter is set and rule not in list
            if rule_ids and rule.id not in rule_ids:
                continue
            
            # Skip if platform not supported
            if pipeline.platform not in rule.platforms:
                continue
            
            # Run rule
            findings = rule.analyze(pipeline, dag)
            all_findings.extend(findings)
        
        # Apply severity filter
        if severity_filter:
            severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
            min_index = severity_order.index(severity_filter)
            all_findings = [
                f for f in all_findings
                if severity_order.index(f.severity) <= min_index
            ]
        
        # Calculate summary
        summary = self._calculate_summary(all_findings, dag, pipeline)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return AnalysisResult(
            pipeline=pipeline,
            findings=all_findings,
            summary=summary,
            dag_edges=dag.get_edges(),
            ai_suggestions=[],
            execution_time_ms=execution_time_ms,
            analyzer_version=__version__,
        )
    
    def _calculate_summary(
        self, findings: list[Finding], dag: PipelineDAG, pipeline: Pipeline
    ) -> AnalysisSummary:
        """Calculate analysis summary from findings.

        Uses normalized scoring based on pipeline complexity to ensure
        fair comparison between small and large pipelines.
        """
        # Count by severity
        by_severity: dict[Severity, int] = {}
        for finding in findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

        # Count by category
        by_category: dict[Category, int] = {}
        for finding in findings:
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

        # Calculate normalized score
        score = self._calculate_normalized_score(findings, pipeline)

        # Estimate time savings
        time_savings = None
        if findings:
            # Rough estimate based on finding count
            min_savings = len(findings) * 30  # 30 seconds per finding
            max_savings = len(findings) * 120  # 2 minutes per finding
            time_savings = f"{min_savings // 60}-{max_savings // 60} minutes per run"

        return AnalysisSummary(
            score=score,
            total_findings=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            estimated_time_savings=time_savings,
            critical_path=dag.get_critical_path(),
        )

    def _calculate_normalized_score(
        self, findings: list[Finding], pipeline: Pipeline
    ) -> int:
        """Calculate score normalized by pipeline complexity.

        Uses findings density (findings per stage) to fairly compare
        pipelines of different sizes. A 50-stage pipeline with 5 findings
        should score better than a 1-stage pipeline with 5 findings.

        Formula:
        1. Calculate base penalty per finding (by severity)
        2. Calculate pipeline complexity (stages + jobs)
        3. Normalize penalty based on density
        4. Apply diminishing returns for very large pipelines
        """
        if not findings:
            return 100

        # Base penalties per severity
        base_penalties = {
            Severity.CRITICAL: 15,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }

        # Calculate raw penalty
        raw_penalty = sum(base_penalties.get(f.severity, 0) for f in findings)

        # Calculate pipeline complexity
        num_stages = len(pipeline.stages)
        num_jobs = sum(len(stage.jobs) for stage in pipeline.stages)
        num_steps = sum(
            len(job.steps)
            for stage in pipeline.stages
            for job in stage.jobs
        )

        # Use stages as primary complexity metric, with minimum of 1
        complexity = max(1, num_stages)

        # Calculate findings density (findings per stage)
        density = len(findings) / complexity

        # Normalize penalty based on density
        # - density < 0.5: reduce penalty (few findings for pipeline size)
        # - density = 1.0: full penalty (1 finding per stage)
        # - density > 2.0: cap penalty (don't over-penalize small pipelines)
        if density < 0.5:
            # Low density: reduce penalty (better relative health)
            normalization_factor = 0.5 + density  # 0.5 to 1.0
        elif density <= 2.0:
            # Normal density: proportional penalty
            normalization_factor = 1.0
        else:
            # High density: cap at 2x to avoid crushing small pipelines
            # but still penalize appropriately
            normalization_factor = min(2.0, density / 2.0 + 0.5)

        # Apply normalization
        normalized_penalty = raw_penalty * normalization_factor

        # Calculate final score
        score = max(0, min(100, 100 - int(normalized_penalty)))

        return score
    
    def add_rule(self, rule: AnalysisRule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)
    
    def get_rules(self) -> list[AnalysisRule]:
        """Get all registered rules."""
        return self.rules
