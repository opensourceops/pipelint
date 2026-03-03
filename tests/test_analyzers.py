"""Tests for analysis rules and engine."""

import pytest

from pipelineiq.analyzers import (
    CacheDependenciesRule,
    CacheDockerLayersRule,
    ParallelStagesRule,
    ParallelStepsRule,
)
from pipelineiq.core import AnalysisEngine, PipelineDAG
from pipelineiq.models import (
    Category,
    Job,
    Pipeline,
    Platform,
    RunnerConfig,
    Severity,
    Stage,
    Step,
    StepType,
    CacheConfig,
)


class TestCacheDependenciesRule:
    """Tests for CacheDependenciesRule."""

    @pytest.fixture
    def rule(self):
        return CacheDependenciesRule()

    def test_detects_npm_install_without_cache(self, rule):
        """Test detecting npm install without cache."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            cache=None,  # No cache!
                            steps=[
                                Step(
                                    id="install",
                                    name="Install",
                                    type=StepType.RUN,
                                    command="npm ci",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert findings[0].rule_id == "cache-dependencies"
        assert findings[0].severity == Severity.HIGH
        assert "npm" in findings[0].message

    def test_no_finding_when_cache_configured(self, rule):
        """Test no finding when cache is configured."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            cache=CacheConfig(key="npm", paths=["node_modules"]),
                            steps=[
                                Step(
                                    id="install",
                                    name="Install",
                                    type=StepType.RUN,
                                    command="npm ci",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 0

    def test_detects_pip_install(self, rule):
        """Test detecting pip install without cache."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(
                                    id="install",
                                    name="Install",
                                    type=StepType.RUN,
                                    command="pip install -r requirements.txt",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert "pip" in findings[0].message

    def test_detects_multiple_package_managers(self, rule):
        """Test detecting multiple package managers."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="S1", type=StepType.RUN, command="npm install"),
                                Step(id="s2", name="S2", type=StepType.RUN, command="pip install flask"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 2


class TestCacheDockerLayersRule:
    """Tests for CacheDockerLayersRule."""

    @pytest.fixture
    def rule(self):
        return CacheDockerLayersRule()

    def test_detects_docker_build_without_cache(self, rule):
        """Test detecting docker build without cache."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="docker",
                    name="Docker",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(
                                    id="build",
                                    name="Build",
                                    type=StepType.RUN,
                                    command="docker build -t myapp .",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert findings[0].rule_id == "cache-docker-layers"

    def test_no_finding_with_cache_from(self, rule):
        """Test no finding when --cache-from is used."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="docker",
                    name="Docker",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(
                                    id="build",
                                    name="Build",
                                    type=StepType.RUN,
                                    command="docker build --cache-from myapp:latest -t myapp .",
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 0


class TestParallelStagesRule:
    """Tests for ParallelStagesRule."""

    @pytest.fixture
    def rule(self):
        return ParallelStagesRule()

    def test_detects_sequential_independent_stages(self, rule):
        """Test detecting independent stages running sequentially."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="build", name="Build", dependencies=[], parallel=False, jobs=[]),
                Stage(id="lint", name="Lint", dependencies=[], parallel=False, jobs=[]),
                Stage(id="test", name="Test", dependencies=[], parallel=False, jobs=[]),
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert findings[0].rule_id == "parallel-stages"
        assert findings[0].severity == Severity.HIGH

    def test_no_finding_when_parallel(self, rule):
        """Test no finding when stages are parallel."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="lint", name="Lint", dependencies=[], parallel=True, jobs=[]),
                Stage(id="test", name="Test", dependencies=[], parallel=True, jobs=[]),
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 0

    def test_no_finding_with_dependencies(self, rule):
        """Test no finding when stages have dependencies."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(id="build", name="Build", dependencies=[], jobs=[]),
                Stage(id="test", name="Test", dependencies=["build"], jobs=[]),
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 0


class TestParallelStepsRule:
    """Tests for ParallelStepsRule."""

    @pytest.fixture
    def rule(self):
        return ParallelStepsRule()

    def test_detects_independent_steps(self, rule):
        """Test detecting independent steps."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Run Lint", type=StepType.RUN, command="npm run lint"),
                                Step(id="s2", name="Run Tests", type=StepType.RUN, command="npm test"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert findings[0].rule_id == "parallel-steps"

    def test_no_finding_single_step(self, rule):
        """Test no finding with single step."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Build", type=StepType.RUN, command="npm build"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 0

    def test_detects_via_command_content_not_name(self, rule):
        """Test detection via command content, not step name (mentor feedback)."""
        # Step names don't contain keywords, but commands do
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="ci",
                    name="CI",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Step 1", type=StepType.RUN, command="eslint src/"),
                                Step(id="s2", name="Step 2", type=StepType.RUN, command="pytest tests/"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert "lint" in findings[0].message.lower() or "test" in findings[0].message.lower()

    def test_detects_security_tools(self, rule):
        """Test detection of security scanning tools."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="ci",
                    name="CI",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Audit", type=StepType.RUN, command="npm audit"),
                                Step(id="s2", name="Tests", type=StepType.RUN, command="jest"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        assert "security" in findings[0].message.lower() or "test" in findings[0].message.lower()

    def test_no_finding_for_sequential_deps(self, rule):
        """Test no finding for install->build (not parallelizable)."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="ci",
                    name="CI",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Install", type=StepType.RUN, command="npm ci"),
                                Step(id="s2", name="Build", type=StepType.RUN, command="npm run build"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        # install and build are not in PARALLELIZABLE_CATEGORIES
        assert len(findings) == 0

    def test_detects_three_parallelizable_steps(self, rule):
        """Test detection of lint + test + security as parallelizable."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="ci",
                    name="CI",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Lint", type=StepType.RUN, command="ruff check ."),
                                Step(id="s2", name="Test", type=StepType.RUN, command="pytest"),
                                Step(id="s3", name="Security", type=StepType.RUN, command="bandit -r src/"),
                            ],
                        )
                    ],
                )
            ],
        )
        dag = PipelineDAG(pipeline)
        findings = rule.analyze(pipeline, dag)

        assert len(findings) == 1
        # All three steps should be mentioned
        assert "Lint" in findings[0].message
        assert "Test" in findings[0].message
        assert "Security" in findings[0].message


class TestAnalysisEngine:
    """Tests for AnalysisEngine."""

    @pytest.fixture
    def engine(self):
        return AnalysisEngine()

    @pytest.fixture
    def pipeline_with_issues(self):
        return Pipeline(
            id="test",
            name="Test Pipeline",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            steps=[
                                Step(id="s1", name="Install", type=StepType.RUN, command="npm ci"),
                                Step(id="s2", name="Build", type=StepType.RUN, command="docker build -t app ."),
                            ],
                        )
                    ],
                )
            ],
        )

    def test_analyze_returns_result(self, engine, pipeline_with_issues):
        """Test that analyze returns AnalysisResult."""
        result = engine.analyze(pipeline_with_issues)

        assert result.pipeline == pipeline_with_issues
        assert len(result.findings) >= 2  # At least npm + docker
        assert result.summary.total_findings >= 2
        assert result.analyzer_version == "0.1.0"

    def test_calculates_score(self, engine, pipeline_with_issues):
        """Test score calculation."""
        result = engine.analyze(pipeline_with_issues)

        # Score decreases with more findings
        assert result.summary.score <= 85
        assert result.summary.score >= 0

    def test_groups_by_severity(self, engine, pipeline_with_issues):
        """Test grouping by severity."""
        result = engine.analyze(pipeline_with_issues)

        assert Severity.HIGH in result.summary.by_severity
        assert result.summary.by_severity[Severity.HIGH] == 1

    def test_groups_by_category(self, engine, pipeline_with_issues):
        """Test grouping by category."""
        result = engine.analyze(pipeline_with_issues)

        assert Category.CACHING in result.summary.by_category

    def test_severity_filter(self, engine, pipeline_with_issues):
        """Test severity filtering."""
        result = engine.analyze(pipeline_with_issues, severity_filter=Severity.HIGH)

        # Should only include HIGH and above (not MEDIUM)
        assert all(f.severity in [Severity.CRITICAL, Severity.HIGH] for f in result.findings)

    def test_rule_id_filter(self, engine, pipeline_with_issues):
        """Test rule ID filtering."""
        result = engine.analyze(pipeline_with_issues, rule_ids=["cache-dependencies"])

        assert len(result.findings) == 1
        assert result.findings[0].rule_id == "cache-dependencies"

    def test_includes_dag_edges(self, engine, pipeline_with_issues):
        """Test that DAG edges are included."""
        result = engine.analyze(pipeline_with_issues)

        assert isinstance(result.dag_edges, list)

    def test_includes_critical_path(self, engine, pipeline_with_issues):
        """Test that critical path is included."""
        result = engine.analyze(pipeline_with_issues)

        assert "build" in result.summary.critical_path

    def test_clean_pipeline_scores_100(self, engine):
        """Test that clean pipeline scores 100."""
        pipeline = Pipeline(
            id="clean",
            name="Clean",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[
                Stage(
                    id="build",
                    name="Build",
                    jobs=[
                        Job(
                            id="job1",
                            name="Job 1",
                            runner=RunnerConfig(type="kubernetes"),
                            cache=CacheConfig(key="npm", paths=["node_modules"]),
                            timeout_minutes=30,  # Has timeout
                            steps=[
                                Step(id="s1", name="Build", type=StepType.RUN, command="echo hello"),
                            ],
                        )
                    ],
                )
            ],
        )
        result = engine.analyze(pipeline)

        assert result.summary.score == 100
        assert result.summary.total_findings == 0
