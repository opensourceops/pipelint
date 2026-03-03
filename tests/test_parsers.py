"""Tests for pipeline parsers."""

from pathlib import Path

import pytest

from pipelineiq.models import Platform, StepType
from pipelineiq.parsers import GitHubActionsParser, HarnessParser, ParseError, get_parser


HARNESS_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "harness"
GITHUB_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "github"


class TestGetParser:
    """Tests for get_parser factory."""

    def test_get_harness_parser(self):
        """Test getting Harness parser."""
        parser = get_parser(Platform.HARNESS)
        assert isinstance(parser, HarnessParser)
        assert parser.platform == Platform.HARNESS

    def test_get_github_parser(self):
        """Test getting GitHub Actions parser."""
        parser = get_parser(Platform.GITHUB)
        assert isinstance(parser, GitHubActionsParser)
        assert parser.platform == Platform.GITHUB

    def test_unsupported_platform(self):
        """Test error for unsupported platform."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_parser(Platform.GITLAB)


class TestHarnessParser:
    """Tests for HarnessParser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return HarnessParser()

    def test_parse_simple_pipeline(self, parser):
        """Test parsing simple pipeline."""
        content = (HARNESS_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        assert pipeline.id == "simple_pipeline"
        assert pipeline.name == "Simple CI Pipeline"
        assert pipeline.platform == Platform.HARNESS
        assert len(pipeline.stages) == 2

    def test_parse_stages(self, parser):
        """Test stage parsing."""
        content = (HARNESS_FIXTURES_DIR / "simple.yaml").read_text()
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
        content = (HARNESS_FIXTURES_DIR / "simple.yaml").read_text()
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
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert pipeline.id == "complex_pipeline"
        assert len(pipeline.stages) == 4  # build, lint, test, docker

    def test_parse_parallel_stages(self, parser):
        """Test parallel stage parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        # lint and test should be marked as parallel
        lint_stage = next(s for s in pipeline.stages if s.id == "lint")
        test_stage = next(s for s in pipeline.stages if s.id == "test")

        assert lint_stage.parallel is True
        assert test_stage.parallel is True

    def test_parse_plugin_step(self, parser):
        """Test plugin step parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        docker_stage = next(s for s in pipeline.stages if s.id == "docker")
        docker_step = docker_stage.jobs[0].steps[0]

        assert docker_step.type == StepType.PLUGIN
        assert docker_step.plugin == "docker"

    def test_parse_cache_config(self, parser):
        """Test cache configuration parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = pipeline.stages[0]
        cache = build_stage.jobs[0].cache

        assert cache is not None
        assert cache.key == "npm-cache"
        assert "node_modules" in cache.paths

    def test_parse_timeout(self, parser):
        """Test timeout parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = pipeline.stages[0]
        build_step = build_stage.jobs[0].steps[1]

        assert build_step.timeout_minutes == 10

    def test_parse_variables(self, parser):
        """Test pipeline variables parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert "NODE_VERSION" in pipeline.variables
        assert pipeline.variables["NODE_VERSION"] == "20"

    def test_parse_runner_config(self, parser):
        """Test runner configuration parsing."""
        content = (HARNESS_FIXTURES_DIR / "complex.yaml").read_text()
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


class TestGitHubActionsParser:
    """Tests for GitHubActionsParser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return GitHubActionsParser()

    def test_parse_simple_workflow(self, parser):
        """Test parsing simple workflow."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        assert pipeline.name == "Simple CI"
        assert pipeline.platform == Platform.GITHUB
        assert len(pipeline.stages) == 2  # build and test jobs

    def test_parse_jobs_as_stages(self, parser):
        """Test that GitHub jobs are parsed as stages."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        job_ids = [s.id for s in pipeline.stages]
        assert "build" in job_ids
        assert "test" in job_ids

    def test_parse_job_dependencies(self, parser):
        """Test parsing job dependencies (needs)."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        test_stage = next(s for s in pipeline.stages if s.id == "test")
        assert test_stage.dependencies == ["build"]

    def test_parse_steps(self, parser):
        """Test step parsing."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        steps = build_stage.jobs[0].steps

        assert len(steps) == 4  # checkout, setup-node, install, build

    def test_parse_action_step(self, parser):
        """Test parsing 'uses' action step."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        checkout_step = build_stage.jobs[0].steps[0]

        assert checkout_step.type == StepType.ACTION
        assert checkout_step.plugin == "actions/checkout"
        assert checkout_step.plugin_version == "v4"

    def test_parse_run_step(self, parser):
        """Test parsing 'run' command step."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        install_step = build_stage.jobs[0].steps[2]

        assert install_step.type == StepType.RUN
        assert install_step.command == "npm install"

    def test_parse_complex_workflow(self, parser):
        """Test parsing complex workflow with multiple jobs."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert pipeline.name == "Complex CI/CD Pipeline"
        assert len(pipeline.stages) == 6  # lint, test, security, build, docker, deploy

    def test_parse_triggers(self, parser):
        """Test parsing workflow triggers."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        trigger_types = [t.type for t in pipeline.triggers]
        assert "push" in trigger_types
        assert "pull_request" in trigger_types
        assert "manual" in trigger_types  # workflow_dispatch

    def test_parse_trigger_branches(self, parser):
        """Test parsing trigger branch filters."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        push_trigger = next(t for t in pipeline.triggers if t.type == "push")
        assert "main" in push_trigger.branches
        assert "develop" in push_trigger.branches

    def test_parse_env_variables(self, parser):
        """Test parsing workflow-level env variables."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        assert "NODE_VERSION" in pipeline.variables
        assert pipeline.variables["NODE_VERSION"] == "20"

    def test_parse_runner_config(self, parser):
        """Test parsing runs-on to RunnerConfig."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        runner = build_stage.jobs[0].runner

        assert runner.type == "cloud"
        assert runner.os == "linux"
        assert runner.image == "ubuntu-latest"

    def test_parse_job_timeout(self, parser):
        """Test parsing job timeout-minutes."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        assert build_stage.jobs[0].timeout_minutes == 30

    def test_parse_continue_on_error(self, parser):
        """Test parsing continue-on-error."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        security_stage = next(s for s in pipeline.stages if s.id == "security")
        audit_step = security_stage.jobs[0].steps[1]  # npm audit step

        assert audit_step.continue_on_error is True

    def test_parse_step_with_inputs(self, parser):
        """Test parsing step 'with' inputs."""
        content = (GITHUB_FIXTURES_DIR / "simple.yaml").read_text()
        pipeline = parser.parse(content, "simple.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        setup_node_step = build_stage.jobs[0].steps[1]

        assert setup_node_step.inputs.get("node-version") == "20"

    def test_parse_job_condition(self, parser):
        """Test parsing job 'if' condition."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        docker_stage = next(s for s in pipeline.stages if s.id == "docker")
        assert docker_stage.condition is not None
        assert "github.event_name" in docker_stage.condition

    def test_parse_cache_action(self, parser):
        """Test parsing actions/cache to CacheConfig."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        lint_stage = next(s for s in pipeline.stages if s.id == "lint")
        cache = lint_stage.jobs[0].cache

        assert cache is not None
        assert "~/.npm" in cache.paths

    def test_parse_multiple_dependencies(self, parser):
        """Test parsing job with multiple needs."""
        content = (GITHUB_FIXTURES_DIR / "complex.yaml").read_text()
        pipeline = parser.parse(content, "complex.yaml")

        build_stage = next(s for s in pipeline.stages if s.id == "build")
        assert "test" in build_stage.dependencies
        assert "security" in build_stage.dependencies

    def test_invalid_yaml(self, parser):
        """Test error on invalid YAML."""
        with pytest.raises(ParseError, match="Invalid YAML"):
            parser.parse("{ invalid: yaml: content", "bad.yaml")

    def test_missing_jobs_key(self, parser):
        """Test error when jobs key missing."""
        with pytest.raises(ParseError, match="Missing 'jobs' key"):
            parser.parse("name: Test\non: push", "bad.yaml")

    def test_non_mapping_yaml(self, parser):
        """Test error when YAML is not a mapping."""
        with pytest.raises(ParseError, match="must be a YAML mapping"):
            parser.parse("- item1\n- item2", "bad.yaml")
