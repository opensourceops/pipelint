"""JSON reporter."""

import json
from typing import Any

from pipelineiq.models import AnalysisResult


class JsonReporter:
    """JSON output reporter."""
    
    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def render(self, result: AnalysisResult) -> str:
        """Render analysis result to JSON string."""
        data = self._to_dict(result)
        return json.dumps(data, indent=self.indent, default=str)
    
    def _to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "pipeline": {
                "id": result.pipeline.id,
                "name": result.pipeline.name,
                "platform": result.pipeline.platform.value,
                "file_path": result.pipeline.file_path,
            },
            "summary": {
                "score": result.summary.score,
                "total_findings": result.summary.total_findings,
                "by_severity": {
                    k.value: v for k, v in result.summary.by_severity.items()
                },
                "by_category": {
                    k.value: v for k, v in result.summary.by_category.items()
                },
                "estimated_time_savings": result.summary.estimated_time_savings,
                "critical_path": result.summary.critical_path,
            },
            "findings": [
                {
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "message": f.message,
                    "suggestion": f.suggestion,
                    "location": {
                        "file": f.location.file,
                        "stage": f.location.stage,
                        "job": f.location.job,
                        "step": f.location.step,
                    },
                    "estimated_impact": f.estimated_impact,
                }
                for f in result.findings
            ],
            "ai_suggestions": result.ai_suggestions,
            "dag_edges": result.dag_edges,
            "execution_time_ms": result.execution_time_ms,
            "analyzer_version": result.analyzer_version,
        }
