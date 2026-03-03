"""Integration tests for full pipeline analysis flow."""

from pathlib import Path

import pytest

from pipelineiq.core import AnalysisEngine
from pipelineiq.models import Platform, Severity
from pipelineiq.parsers import get_parser
from pipelineiq.reporters import JsonReporter, MarkdownReporter, TerminalReporter


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "harness"


class TestFullAnalysisFlow:
    """Integration tests for complete analysis workflow."""

    def test_simple_pipeline_analysis(self):
        """Test full analysis of simple pipeline."""
        # Load
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        
        # Parse
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(content, "simple.yaml")
        
        # Analyze
        engine = AnalysisEngine()
        result = engine.analyze(pipeline)
        
        # Verify
        assert result.pipeline.name == "Simple CI Pipeline"
        assert result.summary.total_findings > 0
        assert result.summary.score <= 100
        assert len(result.dag_edges) > 0
        assert result.analyzer_version == "0.1.0"

    def test_complex_pipeline_analysis(self):
        """Test full analysis of complex pipeline."""
        content = (FIXTURES_DIR / "complex.yaml").read_text()
        
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(content, "complex.yaml")
        
        engine = AnalysisEngine()
        result = engine.analyze(pipeline)
        
        # Complex pipeline should have more stages
        assert len(pipeline.stages) >= 4
        assert result.summary.critical_path
        assert len(result.summary.critical_path) > 1

    def test_severity_filter_integration(self):
        """Test severity filtering in full flow."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(content, "simple.yaml")
        
        engine = AnalysisEngine()
        
        # Get all findings
        all_result = engine.analyze(pipeline)
        
        # Get only high severity
        high_result = engine.analyze(pipeline, severity_filter=Severity.HIGH)
        
        # High filter should have fewer or equal findings
        assert high_result.summary.total_findings <= all_result.summary.total_findings

    def test_rule_filter_integration(self):
        """Test rule filtering in full flow."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(content, "simple.yaml")
        
        engine = AnalysisEngine()
        
        # Only run cache-dependencies rule
        result = engine.analyze(pipeline, rule_ids=["cache-dependencies"])
        
        # All findings should be from cache-dependencies
        for finding in result.findings:
            assert finding.rule_id == "cache-dependencies"


class TestReporterIntegration:
    """Integration tests for reporters."""

    @pytest.fixture
    def analysis_result(self):
        """Get analysis result for testing reporters."""
        content = (FIXTURES_DIR / "simple.yaml").read_text()
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(content, "simple.yaml")
        engine = AnalysisEngine()
        return engine.analyze(pipeline)

    def test_terminal_reporter(self, analysis_result):
        """Test terminal reporter output."""
        reporter = TerminalReporter()
        output = reporter.render(analysis_result)
        
        assert "PipelineIQ Analysis Report" in output
        assert "Simple CI Pipeline" in output
        assert "Score" in output
        assert "Findings" in output

    def test_json_reporter(self, analysis_result):
        """Test JSON reporter output."""
        import json
        
        reporter = JsonReporter()
        output = reporter.render(analysis_result)
        
        # Should be valid JSON
        data = json.loads(output)
        
        assert "pipeline" in data
        assert "summary" in data
        assert "findings" in data
        assert data["pipeline"]["name"] == "Simple CI Pipeline"

    def test_markdown_reporter(self, analysis_result):
        """Test Markdown reporter output."""
        reporter = MarkdownReporter()
        output = reporter.render(analysis_result)
        
        assert "# PipelineIQ Analysis Report" in output
        assert "Simple CI Pipeline" in output
        assert "## Summary" in output
        assert "## Findings" in output


class TestEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_stages_pipeline(self):
        """Test pipeline with minimal configuration."""
        yaml_content = """
pipeline:
  identifier: minimal
  name: Minimal Pipeline
  stages: []
"""
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(yaml_content, "minimal.yaml")
        
        engine = AnalysisEngine()
        result = engine.analyze(pipeline)
        
        assert result.summary.score == 100  # No findings
        assert result.summary.total_findings == 0

    def test_pipeline_with_all_best_practices(self):
        """Test pipeline following all best practices."""
        yaml_content = """
pipeline:
  identifier: best_practices
  name: Best Practices Pipeline
  stages:
    - stage:
        identifier: build
        name: Build
        type: CI
        spec:
          infrastructure:
            type: KubernetesDirect
            spec:
              os: Linux
              resources:
                cpu: "2"
                memory: 4Gi
          caching:
            enabled: true
            key: npm-cache
            paths:
              - node_modules
          execution:
            steps:
              - step:
                  identifier: install
                  name: Install
                  type: Run
                  timeout: 10m
                  spec:
                    image: node:20.10.0
                    command: npm ci
        timeout: 30m
"""
        parser = get_parser(Platform.HARNESS)
        pipeline = parser.parse(yaml_content, "best.yaml")
        
        engine = AnalysisEngine()
        result = engine.analyze(pipeline)
        
        # Should have high score (may still have some findings)
        assert result.summary.score >= 80


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_cli_list_rules(self):
        """Test list-rules command."""
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["list-rules"])
        
        assert result.exit_code == 0
        assert "cache-dependencies" in result.output
        assert "missing-timeout" in result.output

    def test_cli_explain_rule(self):
        """Test explain command."""
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["explain", "cache-dependencies"])
        
        assert result.exit_code == 0
        assert "Cache Dependencies" in result.output

    def test_cli_version(self):
        """Test version command."""
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_analyze_simple(self):
        """Test analyze command with simple pipeline."""
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, [
            "analyze",
            str(FIXTURES_DIR / "simple.yaml"),
            "--platform", "harness",
        ])
        
        # Exit code 1 means findings found (expected)
        assert result.exit_code in [0, 1, 2]
        assert "Score" in result.output or "score" in result.output.lower()

    def test_cli_analyze_json_format(self):
        """Test analyze with JSON output."""
        import json
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app
        
        runner = CliRunner()
        result = runner.invoke(app, [
            "analyze",
            str(FIXTURES_DIR / "simple.yaml"),
            "--platform", "harness",
            "--format", "json",
        ])
        
        assert result.exit_code in [0, 1, 2]
        # Should be valid JSON
        data = json.loads(result.output)
        assert "pipeline" in data

    def test_cli_invalid_platform(self):
        """Test error handling for invalid platform."""
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "analyze",
            str(FIXTURES_DIR / "simple.yaml"),
            "--platform", "invalid",
        ])

        assert result.exit_code == 1
        assert "Invalid platform" in result.output

    def test_cli_fix_flag_with_mock(self):
        """Test --fix flag generates and displays fixes."""
        from unittest.mock import patch, Mock
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app

        runner = CliRunner()

        # Mock ClaudeService to return a fix
        with patch("pipelineiq.ai.ClaudeService") as mock_claude_class:
            mock_service = Mock()
            mock_service.is_available.return_value = True
            mock_service.generate_fix.return_value = "cache:\n  key: npm-{{ checksum 'package-lock.json' }}"
            mock_claude_class.return_value = mock_service

            result = runner.invoke(app, [
                "analyze",
                str(FIXTURES_DIR / "simple.yaml"),
                "--platform", "harness",
                "--fix",
            ])

            # Should call generate_fix for each finding
            assert mock_service.generate_fix.call_count > 0
            # Exit code 1 or 2 means findings found
            assert result.exit_code in [1, 2]

    def test_cli_fix_flag_json_output(self):
        """Test --fix flag includes ai_fix in JSON output."""
        import json
        from unittest.mock import patch, Mock
        from typer.testing import CliRunner
        from pipelineiq.cli.main import app

        runner = CliRunner()

        with patch("pipelineiq.ai.ClaudeService") as mock_claude_class:
            mock_service = Mock()
            mock_service.is_available.return_value = True
            mock_service.generate_fix.return_value = "cache:\n  enabled: true"
            mock_claude_class.return_value = mock_service

            result = runner.invoke(app, [
                "analyze",
                str(FIXTURES_DIR / "simple.yaml"),
                "--platform", "harness",
                "--fix",
                "--format", "json",
            ])

            data = json.loads(result.output)
            # At least one finding should have ai_fix
            findings_with_fix = [f for f in data["findings"] if f.get("ai_fix")]
            assert len(findings_with_fix) > 0
