"""Terminal reporter with Rich formatting."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pipelineiq.models import AnalysisResult, Severity


class TerminalReporter:
    """Rich-based terminal output reporter."""
    
    SEVERITY_STYLES = {
        Severity.CRITICAL: ("🔴", "red bold"),
        Severity.HIGH: ("🟠", "yellow"),
        Severity.MEDIUM: ("🟡", "blue"),
        Severity.LOW: ("🔵", "dim"),
        Severity.INFO: ("ℹ️", "dim"),
    }
    
    def __init__(self):
        self.console = Console(record=True)
    
    def render(self, result: AnalysisResult, to_console: bool = False) -> str:
        """Render analysis result to terminal string.
        
        Args:
            result: Analysis result to render
            to_console: If True, print directly to console instead of returning string
        """
        if to_console:
            self.console = Console()
        else:
            self.console = Console(record=True, force_terminal=True, file=None)
        
        # Header
        self._render_header(result)
        
        # Summary
        self._render_summary(result)
        
        # Findings
        if result.findings:
            self._render_findings(result)
        
        # AI Suggestions
        if result.ai_suggestions:
            self._render_ai_suggestions(result)
        
        # Critical path
        if result.summary.critical_path:
            self._render_critical_path(result)
        
        if to_console:
            return ""
        return self.console.export_text()
    
    def _render_header(self, result: AnalysisResult) -> None:
        """Render header panel."""
        header = Text()
        header.append("PipelineIQ Analysis Report\n", style="bold blue")
        header.append(f"Pipeline: {result.pipeline.name}\n", style="dim")
        header.append(f"Platform: {result.pipeline.platform.value}\n", style="dim")
        header.append(f"File: {result.pipeline.file_path}", style="dim")
        
        self.console.print(Panel(header, title="[bold]Analysis[/bold]", border_style="blue"))
    
    def _render_summary(self, result: AnalysisResult) -> None:
        """Render summary panel."""
        score = result.summary.score
        score_style = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        
        summary = Table.grid(padding=(0, 2))
        summary.add_column(justify="right")
        summary.add_column(justify="left")
        
        summary.add_row("Score:", Text(f"{score}/100", style=f"bold {score_style}"))
        summary.add_row("Findings:", str(result.summary.total_findings))
        
        # By severity
        severity_counts = []
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            count = result.summary.by_severity.get(sev, 0)
            if count > 0:
                icon, style = self.SEVERITY_STYLES[sev]
                severity_counts.append(f"{icon} {count} {sev.value}")
        
        if severity_counts:
            summary.add_row("Breakdown:", " | ".join(severity_counts))
        
        if result.summary.estimated_time_savings:
            summary.add_row("Est. Savings:", result.summary.estimated_time_savings)
        
        self.console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="green"))
    
    def _render_findings(self, result: AnalysisResult) -> None:
        """Render findings table."""
        table = Table(title="Findings", show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Severity", width=10)
        table.add_column("Rule", width=20)
        table.add_column("Issue", width=50)
        table.add_column("Location", width=15)
        
        for i, finding in enumerate(result.findings, 1):
            icon, style = self.SEVERITY_STYLES[finding.severity]
            severity_text = Text(f"{icon} {finding.severity.value}", style=style)
            
            location = finding.location.stage or finding.location.file
            
            table.add_row(
                str(i),
                severity_text,
                finding.rule_name,
                finding.message,
                location,
            )
        
        self.console.print(table)
        
        # Suggestions
        self.console.print("\n[bold]Suggestions:[/bold]")
        for finding in result.findings[:5]:  # Top 5
            self.console.print(f"  • {finding.suggestion}")
    
    def _render_ai_suggestions(self, result: AnalysisResult) -> None:
        """Render AI suggestions panel."""
        suggestions = Text()
        for i, suggestion in enumerate(result.ai_suggestions, 1):
            suggestions.append(f"{i}. {suggestion}\n")
        
        self.console.print(Panel(
            suggestions,
            title="[bold magenta]AI Suggestions[/bold magenta]",
            border_style="magenta"
        ))
    
    def _render_critical_path(self, result: AnalysisResult) -> None:
        """Render critical path."""
        path = " → ".join(result.summary.critical_path)
        self.console.print(f"\n[dim]Critical Path: {path}[/dim]")
