"""Tests for DAG builder."""

import pytest

from pipelineiq.core import PipelineDAG
from pipelineiq.models import Job, Pipeline, Platform, RunnerConfig, Stage


class TestPipelineDAG:
    """Tests for PipelineDAG."""

    @pytest.fixture
    def linear_pipeline(self) -> Pipeline:
        """Create a linear pipeline: A -> B -> C."""
        return Pipeline(
            id="linear",
            name="Linear Pipeline",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="A", name="Stage A", dependencies=[], jobs=[]),
                Stage(id="B", name="Stage B", dependencies=["A"], jobs=[]),
                Stage(id="C", name="Stage C", dependencies=["B"], jobs=[]),
            ],
        )

    @pytest.fixture
    def parallel_pipeline(self) -> Pipeline:
        """Create a pipeline with parallel stages: A -> (B, C) -> D."""
        return Pipeline(
            id="parallel",
            name="Parallel Pipeline",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="A", name="Stage A", dependencies=[], jobs=[]),
                Stage(id="B", name="Stage B", dependencies=["A"], parallel=True, jobs=[]),
                Stage(id="C", name="Stage C", dependencies=["A"], parallel=True, jobs=[]),
                Stage(id="D", name="Stage D", dependencies=["B", "C"], jobs=[]),
            ],
        )

    @pytest.fixture
    def complex_pipeline(self) -> Pipeline:
        """Create a complex pipeline with multiple paths."""
        return Pipeline(
            id="complex",
            name="Complex Pipeline",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="build", name="Build", dependencies=[], jobs=[]),
                Stage(id="lint", name="Lint", dependencies=["build"], jobs=[]),
                Stage(id="test", name="Test", dependencies=["build"], jobs=[]),
                Stage(id="security", name="Security", dependencies=["build"], jobs=[]),
                Stage(id="package", name="Package", dependencies=["lint", "test"], jobs=[]),
                Stage(id="deploy", name="Deploy", dependencies=["package", "security"], jobs=[]),
            ],
        )

    def test_build_linear_dag(self, linear_pipeline):
        """Test building DAG from linear pipeline."""
        dag = PipelineDAG(linear_pipeline)
        
        assert len(dag.graph.nodes()) == 3
        assert len(dag.graph.edges()) == 2

    def test_get_edges(self, linear_pipeline):
        """Test getting edges."""
        dag = PipelineDAG(linear_pipeline)
        edges = dag.get_edges()
        
        assert ("A", "B") in edges
        assert ("B", "C") in edges

    def test_critical_path_linear(self, linear_pipeline):
        """Test critical path for linear pipeline."""
        dag = PipelineDAG(linear_pipeline)
        path = dag.get_critical_path()
        
        assert path == ["A", "B", "C"]

    def test_critical_path_parallel(self, parallel_pipeline):
        """Test critical path for parallel pipeline."""
        dag = PipelineDAG(parallel_pipeline)
        path = dag.get_critical_path()
        
        # Should be A -> B/C -> D (length 3)
        assert len(path) == 3
        assert path[0] == "A"
        assert path[-1] == "D"

    def test_independent_stages(self, linear_pipeline):
        """Test finding independent stages."""
        dag = PipelineDAG(linear_pipeline)
        independent = dag.get_independent_stages()
        
        assert independent == ["A"]

    def test_independent_stages_multiple(self):
        """Test finding multiple independent stages."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="A", name="A", dependencies=[], jobs=[]),
                Stage(id="B", name="B", dependencies=[], jobs=[]),
                Stage(id="C", name="C", dependencies=["A", "B"], jobs=[]),
            ],
        )
        dag = PipelineDAG(pipeline)
        independent = dag.get_independent_stages()
        
        assert set(independent) == {"A", "B"}

    def test_parallelizable_groups_linear(self, linear_pipeline):
        """Test parallelizable groups for linear pipeline."""
        dag = PipelineDAG(linear_pipeline)
        groups = dag.get_parallelizable_groups()
        
        assert len(groups) == 3
        assert groups[0] == ["A"]
        assert groups[1] == ["B"]
        assert groups[2] == ["C"]

    def test_parallelizable_groups_parallel(self, parallel_pipeline):
        """Test parallelizable groups for parallel pipeline."""
        dag = PipelineDAG(parallel_pipeline)
        groups = dag.get_parallelizable_groups()
        
        assert len(groups) == 3
        assert groups[0] == ["A"]
        assert set(groups[1]) == {"B", "C"}  # B and C can run together
        assert groups[2] == ["D"]

    def test_bottlenecks(self, complex_pipeline):
        """Test finding bottlenecks."""
        dag = PipelineDAG(complex_pipeline)
        bottlenecks = dag.get_bottlenecks(threshold=2)
        
        # build has 3 dependents (lint, test, security)
        assert "build" in bottlenecks

    def test_stage_depth(self, linear_pipeline):
        """Test stage depth calculation."""
        dag = PipelineDAG(linear_pipeline)
        
        assert dag.get_stage_depth("A") == 0
        assert dag.get_stage_depth("B") == 1
        assert dag.get_stage_depth("C") == 2

    def test_stage_depth_complex(self, complex_pipeline):
        """Test stage depth in complex pipeline."""
        dag = PipelineDAG(complex_pipeline)
        
        assert dag.get_stage_depth("build") == 0
        assert dag.get_stage_depth("lint") == 1
        assert dag.get_stage_depth("package") == 2
        assert dag.get_stage_depth("deploy") == 3

    def test_get_dependents(self, complex_pipeline):
        """Test getting dependents."""
        dag = PipelineDAG(complex_pipeline)
        dependents = dag.get_dependents("build")
        
        assert set(dependents) == {"lint", "test", "security"}

    def test_get_dependencies(self, complex_pipeline):
        """Test getting dependencies."""
        dag = PipelineDAG(complex_pipeline)
        deps = dag.get_dependencies("deploy")
        
        assert set(deps) == {"package", "security"}

    def test_to_dict(self, linear_pipeline):
        """Test converting DAG to dictionary."""
        dag = PipelineDAG(linear_pipeline)
        data = dag.to_dict()
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    def test_empty_pipeline(self):
        """Test handling empty pipeline."""
        pipeline = Pipeline(
            id="empty",
            name="Empty",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[],
        )
        dag = PipelineDAG(pipeline)
        
        assert dag.get_critical_path() == []
        assert dag.get_independent_stages() == []
        assert dag.get_parallelizable_groups() == []

    def test_nonexistent_stage(self, linear_pipeline):
        """Test handling nonexistent stage."""
        dag = PipelineDAG(linear_pipeline)
        
        assert dag.get_stage_depth("nonexistent") == -1
        assert dag.get_dependents("nonexistent") == []
        assert dag.get_dependencies("nonexistent") == []
