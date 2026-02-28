"""Tests for pipeline parsers."""

from pathlib import Path

import pytest

from pipelineiq.models import Platform, StepType
from pipelineiq.parsers import HarnessParser, ParseError, get_parser


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "harness"


class TestGetParser:
    """Tests for get_parser factory."""

    def test_get_harness_parser(self):
        """Test getting Harness parser."""
        parser = get_parser(Platform.HARNESS)
        assert isinstance(parser, HarnessParser)
        assert parser.platform == Platform.HARNESS

    def test_unsupported_platform(self):
        """Test error for unsupported platform."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_parser(Platform.GITHUB)


class TestHarnessParser:
    """Tests for HarnessParser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return HarnessParser()

    def test_parse_simple_pipeline(self, parser):
        """Test parsing simple pipeline."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        assert pipeline.id == "simple_pipeline"
        assert pipeline.name == "Simple CI Pipeline"
        assert pipeline.platform == Platform.HARNESS
        assert len(pipeline.stages) == 2

    def test_parse_stages(self, parser):
        """Test stage parsing."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = pipeline.stages[0]
        assert build_stage.id == "build"
        assert build_stage.name == "Build"
        assert build_stage.type == "CI"

        test_stage = pipeline.stages[1]
        assert test_stage.id == "test"
        assert test_stage.dependencies == ["build"]

    def test_parse_steps(self, parser):
        """Test step parsing."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = pipeline.stages[0]
        assert len(build_stage.jobs) == 1

        job = build_stage.jobs[0]
        assert len(job.steps) == 2

        install_step = job.steps[0]
        assert install_step.id == "install"
        assert install_step.type == StepType.RUN
        assert install_step.command == "npm ci"
        assert install_step.image == "node:20-alpine"

    def test_parse_complex_pipeline(self, parser):
        """Test parsing complex pipeline with parallel stages."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert pipeline.id == "complex_pipeline"
        assert len(pipeline.stages) == 4  # build, lint, test, docker

    def test_parse_parallel_stages(self, parser):
        """Test parallel stage parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        # lint and test should be marked as parallel
        lint_stage = next(s for s in pipeline.stages if s.id == "lint")
        test_stage = next(s for s in pipeline.stages if s.id == "test")

        assert lint_stage.parallel is True
        assert test_stage.parallel is True

    def test_parse_plugin_step(self, parser):
        """Test plugin step parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        docker_stage = next(s for s in pipeline.stages if s.id == "docker")
        docker_step = docker_stage.jobs[0].steps[0]

        assert docker_step.type == StepType.PLUGIN
        assert docker_step.plugin == "docker"

    def test_parse_cache_config(self, parser):
        """Test cache configuration parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = pipeline.stages[0]
        cache = build_stage.jobs[0].cache

        assert cache is not None
        assert cache.key == "npm-cache"
        assert "node_modules" in cache.paths

    def test_parse_timeout(self, parser):
        """Test timeout parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = pipeline.stages[0]
        build_step = build_stage.jobs[0].steps[1]

        assert build_step.timeout_minutes == 10

    def test_parse_variables(self, parser):
        """Test pipeline variables parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert "NODE_VERSION" in pipeline.variables
        assert pipeline.variables["NODE_VERSION"] == "20"

    def test_parse_runner_config(self, parser):
        """Test runner configuration parsing."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = pipeline.stages[0]
        runner = build_stage.jobs[0].runner

        assert runner.type == "kubernetes"
        assert runner.os == "linux"
        assert runner.resources is not None
        assert runner.resources.cpu == "1"
        assert runner.resources.memory == "2Gi"

    def test_invalid_yaml(self, parser):
        """Test error on invalid YAML."""
        with pytest.raises(ParseError, match="Invalid YAML"):
            parser.parse("{ invalid: yaml: content", "bad.yaml")

    def test_missing_pipeline_key(self, parser):
        """Test error when pipeline key missing."""
        with pytest.raises(ParseError, match="Missing 'pipeline' key"):
            parser.parse("stages: []", "bad.yaml")

    def test_non_mapping_yaml(self, parser):
        """Test error when YAML is not a mapping."""
        with pytest.raises(ParseError, match="must be a YAML mapping"):
            parser.parse("- item1\n- item2", "bad.yaml")
