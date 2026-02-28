"""Core engine for PipelineIQ."""

from pipelineiq.core.dag import PipelineDAG

__all__ = ["PipelineDAG", "AnalysisEngine"]


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == "AnalysisEngine":
        from pipelineiq.core.engine import AnalysisEngine
        return AnalysisEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
