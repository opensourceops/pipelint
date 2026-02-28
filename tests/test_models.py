"""Tests for data models."""

import pytest
from pipelineiq.models import (
    Pipeline,
    Platform,
    Stage,
    Job,
    Step,
    StepType,
    RunnerConfig,
    Finding,
    Severity,
    Category,
    Location,
    AnalysisResult,
    AnalysisSummary,
)


class TestPipelineModels:
    """Tests for Pipeline IR models."""

    def test_create_step(self):
        """Test Step creation."""
        step = Step(
            id="build-step",
            name="Build",
            type=StepType.RUN,
            command="npm run build",
        )
        assert step.id == "build-step"
        assert step.type == StepType.RUN
        assert step.command == "npm run build"

    def test_create_job(self):
        """Test Job creation with steps."""
        job = Job(
            id="build-job",
            name="Build Job",
            runner=RunnerConfig(type="kubernetes", os="linux"),
            steps=[
                Step(id="s1", name="Install", type=StepType.RUN, command="npm ci"),
                Step(id="s2", name="Build", type=StepType.RUN, command="npm run build"),
            ],
        )
        assert job.id == "build-job"
        assert len(job.steps) == 2
        assert job.runner.type == "kubernetes"

    def test_create_stage(self):
        """Test Stage creation."""
        stage = Stage(
            id="build-stage",
            name="Build",
            type="CI",
            jobs=[
                Job(
                    id="j1",
                    name="Job 1",
                    runner=RunnerConfig(type="docker"),
                )
            ],
        )
        assert stage.id == "build-stage"
        assert len(stage.jobs) == 1

    def test_create_pipeline(self):
        """Test full Pipeline creation."""
        pipeline = Pipeline(
            id="my-pipeline",
            name="My CI Pipeline",
            platform=Platform.HARNESS,
            file_path="pipeline.yaml",
            stages=[
                Stage(id="build", name="Build", jobs=[]),
                Stage(id="test", name="Test", dependencies=["build"], jobs=[]),
            ],
        )
        assert pipeline.id == "my-pipeline"
        assert pipeline.platform == Platform.HARNESS
        assert len(pipeline.stages) == 2
        assert pipeline.stages[1].dependencies == ["build"]

    def test_pipeline_serialization(self):
        """Test Pipeline can be serialized to JSON."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[],
        )
        json_str = pipeline.model_dump_json()
        assert "test" in json_str
        assert "harness" in json_str


class TestFindingModels:
    """Tests for Finding models."""

    def test_create_finding(self):
        """Test Finding creation."""
        finding = Finding(
            id="f1",
            rule_id="cache-dependencies",
            rule_name="Cache Dependencies",
            severity=Severity.HIGH,
            category=Category.CACHING,
            message="npm install without cache",
            suggestion="Add cache configuration",
            location=Location(file="pipeline.yaml", stage="build"),
        )
        assert finding.severity == Severity.HIGH
        assert finding.category == Category.CACHING

    def test_severity_ordering(self):
        """Test severity values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"


class TestResultModels:
    """Tests for AnalysisResult models."""

    def test_create_summary(self):
        """Test AnalysisSummary creation."""
        summary = AnalysisSummary(
            score=75,
            total_findings=5,
            by_severity={Severity.HIGH: 2, Severity.MEDIUM: 3},
        )
        assert summary.score == 75
        assert summary.total_findings == 5

    def test_create_result(self):
        """Test full AnalysisResult creation."""
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[],
        )
        result = AnalysisResult(
            pipeline=pipeline,
            findings=[],
            summary=AnalysisSummary(score=100, total_findings=0),
            execution_time_ms=150,
            analyzer_version="0.1.0",
        )
        assert result.summary.score == 100
        assert result.execution_time_ms == 150
