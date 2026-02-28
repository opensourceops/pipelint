"""Analysis engine - orchestrates pipeline analysis."""

import time
from typing import Type

from pipelineiq import __version__
from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.analyzers.rules.caching import CacheDependenciesRule, CacheDockerLayersRule
from pipelineiq.analyzers.rules.parallelization import ParallelStagesRule, ParallelStepsRule
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
        summary = self._calculate_summary(all_findings, dag)
        
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
    
    def _calculate_summary(self, findings: list[Finding], dag: PipelineDAG) -> AnalysisSummary:
        """Calculate analysis summary from findings."""
        # Count by severity
        by_severity: dict[Severity, int] = {}
        for finding in findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        
        # Count by category
        by_category: dict[Category, int] = {}
        for finding in findings:
            by_category[finding.category] = by_category.get(finding.category, 0) + 1
        
        # Calculate score (100 - penalties)
        # Critical: -15, High: -10, Medium: -5, Low: -2, Info: -1
        penalties = {
            Severity.CRITICAL: 15,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        
        total_penalty = sum(
            penalties.get(f.severity, 0) for f in findings
        )
        score = max(0, min(100, 100 - total_penalty))
        
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
    
    def add_rule(self, rule: AnalysisRule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)
    
    def get_rules(self) -> list[AnalysisRule]:
        """Get all registered rules."""
        return self.rules
