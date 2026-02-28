"""Claude AI service for intelligent suggestions."""

import logging
import os
from typing import Any

from anthropic import Anthropic

from pipelineiq.models import AnalysisResult, Finding, Pipeline

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for generating AI-powered suggestions using Claude."""
    
    MODEL = "claude-3-haiku-20240307"  # Fast, cost-effective for suggestions
    DEFAULT_TIMEOUT = 30.0  # seconds
    
    def __init__(self, api_key: str | None = None, timeout: float | None = None):
        """Initialize Claude service.
        
        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            timeout: Request timeout in seconds. Defaults to 30s.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._client: Anthropic | None = None
    
    @property
    def client(self) -> Anthropic:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable not set. "
                    "Set it or pass api_key to ClaudeService."
                )
            self._client = Anthropic(api_key=self.api_key)
        return self._client
    
    def is_available(self) -> bool:
        """Check if the service is available (API key set)."""
        return bool(self.api_key)
    
    def explain_finding(self, finding: Finding, pipeline_context: str | None = None) -> str:
        """Generate a detailed explanation for a finding.
        
        Args:
            finding: The finding to explain
            pipeline_context: Optional pipeline YAML context
            
        Returns:
            AI-generated explanation
        """
        prompt = self._build_finding_prompt(finding, pipeline_context)
        
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=500,
            timeout=self.timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        
        return response.content[0].text
    
    def generate_suggestions(self, result: AnalysisResult) -> list[str]:
        """Generate overall suggestions for the pipeline.
        
        Args:
            result: Analysis result with findings
            
        Returns:
            List of AI-generated suggestions
        """
        if not result.findings:
            return ["Great job! Your pipeline follows best practices."]
        
        prompt = self._build_suggestions_prompt(result)
        
        logger.debug(f"Generating suggestions for {len(result.findings)} findings")
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=800,
            timeout=self.timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Parse suggestions from response
        text = response.content[0].text
        suggestions = [
            line.strip().lstrip("•-123456789.)")
            for line in text.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        
        return [s.strip() for s in suggestions if s.strip()][:5]  # Max 5 suggestions
    
    def generate_fix(self, finding: Finding, original_yaml: str) -> str | None:
        """Generate a fix for a specific finding.
        
        Args:
            finding: The finding to fix
            original_yaml: The original pipeline YAML
            
        Returns:
            Suggested YAML fix or None if unable to generate
        """
        prompt = f"""You are a CI/CD expert. Given this finding in a pipeline:

Rule: {finding.rule_name}
Issue: {finding.message}
Location: Stage '{finding.location.stage}', Step '{finding.location.step}'

Original YAML excerpt (relevant section):
```yaml
{original_yaml[:2000]}
```

Provide ONLY the corrected YAML snippet for the affected section. No explanation, just the YAML:"""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=500,
                timeout=self.timeout,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Failed to generate fix: {e}")
            return None
    
    def _build_finding_prompt(self, finding: Finding, context: str | None) -> str:
        """Build prompt for explaining a finding."""
        prompt = f"""You are a CI/CD optimization expert. Explain this finding clearly and concisely:

Rule: {finding.rule_name} ({finding.rule_id})
Severity: {finding.severity.value}
Category: {finding.category.value}
Issue: {finding.message}
Suggestion: {finding.suggestion}
Impact: {finding.estimated_impact or 'Not estimated'}
"""
        if context:
            prompt += f"\nPipeline context:\n```yaml\n{context[:1000]}\n```\n"
        
        prompt += """
Provide a brief (2-3 sentences) explanation of:
1. Why this is a problem
2. How to fix it
3. The expected benefit"""
        
        return prompt
    
    def _build_suggestions_prompt(self, result: AnalysisResult) -> str:
        """Build prompt for generating overall suggestions."""
        findings_summary = "\n".join([
            f"- {f.rule_name}: {f.message} (Severity: {f.severity.value})"
            for f in result.findings[:10]  # Limit for prompt size
        ])
        
        return f"""You are a CI/CD optimization expert analyzing a {result.pipeline.platform.value} pipeline.

Pipeline: {result.pipeline.name}
Health Score: {result.summary.score}/100
Total Findings: {result.summary.total_findings}

Key findings:
{findings_summary}

Provide 3-5 prioritized, actionable suggestions to improve this pipeline. 
Be specific and concise. Focus on the highest impact improvements.
Format as a bulleted list."""
