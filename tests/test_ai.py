"""Tests for AI integration."""

import pytest
from unittest.mock import Mock, patch

from pipelineiq.ai import ClaudeService
from pipelineiq.models import (
    AnalysisResult,
    AnalysisSummary,
    Category,
    Finding,
    Location,
    Pipeline,
    Platform,
    Severity,
)


class TestClaudeService:
    """Tests for ClaudeService."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        service = ClaudeService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.is_available() is True

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            service = ClaudeService()
            assert service.is_available() is False

    def test_is_available_with_env_var(self):
        """Test is_available with env var set."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            service = ClaudeService()
            assert service.is_available() is True

    def test_client_raises_without_key(self):
        """Test that accessing client raises without API key."""
        with patch.dict("os.environ", {}, clear=True):
            service = ClaudeService()
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                _ = service.client

    @patch("pipelineiq.ai.claude.Anthropic")
    def test_explain_finding(self, mock_anthropic):
        """Test explain_finding method."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="This is an explanation.")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        service = ClaudeService(api_key="test-key")
        
        finding = Finding(
            id="f1",
            rule_id="cache-dependencies",
            rule_name="Cache Dependencies",
            severity=Severity.HIGH,
            category=Category.CACHING,
            message="npm install without cache",
            suggestion="Add cache configuration",
            location=Location(file="test.yaml", stage="build"),
        )

        result = service.explain_finding(finding)

        assert result == "This is an explanation."
        mock_client.messages.create.assert_called_once()

    @patch("pipelineiq.ai.claude.Anthropic")
    def test_generate_suggestions(self, mock_anthropic):
        """Test generate_suggestions method."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="• Add caching\n• Use parallel stages\n• Pin versions")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        service = ClaudeService(api_key="test-key")
        
        pipeline = Pipeline(
            id="test",
            name="Test",
            platform=Platform.HARNESS,
            file_path="test.yaml",
            stages=[],
        )
        
        result = AnalysisResult(
            pipeline=pipeline,
            findings=[
                Finding(
                    id="f1",
                    rule_id="cache-dependencies",
                    rule_name="Cache Dependencies",
                    severity=Severity.HIGH,
                    category=Category.CACHING,
                    message="npm install without cache",
                    suggestion="Add cache",
                    location=Location(file="test.yaml", stage="build"),
                ),
            ],
            summary=AnalysisSummary(score=80, total_findings=1),
            dag_edges=[],
            ai_suggestions=[],
            execution_time_ms=100,
            analyzer_version="0.1.0",
        )

        suggestions = service.generate_suggestions(result)

        assert len(suggestions) >= 1
        mock_client.messages.create.assert_called_once()

    def test_generate_suggestions_no_findings(self):
        """Test generate_suggestions with no findings."""
        service = ClaudeService(api_key="test-key")
        
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
            dag_edges=[],
            ai_suggestions=[],
            execution_time_ms=100,
            analyzer_version="0.1.0",
        )

        suggestions = service.generate_suggestions(result)

        assert len(suggestions) == 1
        assert "Great job" in suggestions[0]

    @patch("pipelineiq.ai.claude.Anthropic")
    def test_generate_fix(self, mock_anthropic):
        """Test generate_fix method."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="```yaml\ncache:\n  key: npm\n```")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        service = ClaudeService(api_key="test-key")
        
        finding = Finding(
            id="f1",
            rule_id="cache-dependencies",
            rule_name="Cache Dependencies",
            severity=Severity.HIGH,
            category=Category.CACHING,
            message="npm install without cache",
            suggestion="Add cache",
            location=Location(file="test.yaml", stage="build", step="install"),
        )

        fix = service.generate_fix(finding, "pipeline:\n  stages: []")

        assert fix is not None
        assert "cache" in fix.lower()

    def test_finding_ai_fix_field(self):
        """Test that Finding model supports ai_fix field."""
        finding = Finding(
            id="f1",
            rule_id="cache-dependencies",
            rule_name="Cache Dependencies",
            severity=Severity.HIGH,
            category=Category.CACHING,
            message="npm install without cache",
            suggestion="Add cache",
            location=Location(file="test.yaml", stage="build"),
            ai_fix="cache:\n  key: npm-{{ checksum 'package-lock.json' }}",
        )

        assert finding.ai_fix is not None
        assert "cache" in finding.ai_fix

    def test_finding_ai_fix_defaults_to_none(self):
        """Test that ai_fix defaults to None."""
        finding = Finding(
            id="f1",
            rule_id="test",
            rule_name="Test",
            severity=Severity.LOW,
            category=Category.BEST_PRACTICE,
            message="Test message",
            suggestion="Test suggestion",
            location=Location(file="test.yaml"),
        )

        assert finding.ai_fix is None
