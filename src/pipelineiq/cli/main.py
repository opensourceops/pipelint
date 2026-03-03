"""Main CLI application."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console

from pipelineiq import __version__
from pipelineiq.models import Platform, Severity

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="pipelineiq",
    help="AI-powered CI pipeline analyzer",
    add_completion=False,
)

console = Console()


@app.callback()
def callback() -> None:
    """PipelineIQ - Analyze and optimize your CI pipelines."""
    pass


@app.command()
def version() -> None:
    """Show version information."""
    rprint(f"[bold blue]PipelineIQ[/bold blue] v{__version__}")


@app.command()
def analyze(
    path: Path = typer.Argument(
        ...,
        help="Path to the pipeline file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    platform: str = typer.Option(
        ...,
        "--platform", "-p",
        help="CI platform: harness, github (required)",
    ),
    format: str = typer.Option(
        "terminal",
        "--format", "-f",
        help="Output format: terminal, json, markdown",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity", "-s",
        help="Minimum severity: critical, high, medium, low",
    ),
    rules: Optional[str] = typer.Option(
        None,
        "--rules", "-r",
        help="Comma-separated list of rule IDs to run",
    ),
    ai: bool = typer.Option(
        False,
        "--ai",
        help="Enable AI-powered suggestions (requires ANTHROPIC_API_KEY)",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Generate AI-powered YAML fixes for findings (requires ANTHROPIC_API_KEY)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Verbose output",
    ),
) -> None:
    """Analyze a CI pipeline file for optimization opportunities."""
    from pipelineiq.ai import ClaudeService
    from pipelineiq.core import AnalysisEngine
    from pipelineiq.parsers import ParseError, get_parser
    
    try:
        # Validate platform
        try:
            platform_enum = Platform(platform.lower())
        except ValueError:
            rprint(f"[red]Invalid platform:[/red] {platform}")
            rprint("Supported platforms: harness, github")
            raise typer.Exit(code=1)
        
        # Validate severity if provided
        severity_enum = None
        if severity:
            try:
                severity_enum = Severity(severity.lower())
            except ValueError:
                rprint(f"[red]Invalid severity:[/red] {severity}")
                rprint("Valid severities: critical, high, medium, low, info")
                raise typer.Exit(code=1)
        
        # Load and parse pipeline
        content = path.read_text()
        parser = get_parser(platform_enum)
        pipeline = parser.parse(content, str(path))
        
        if verbose:
            rprint(f"[dim]Parsed pipeline: {pipeline.name}[/dim]")
        
        # Run analysis
        rule_ids = rules.split(",") if rules else None
        engine = AnalysisEngine()
        result = engine.analyze(pipeline, severity_filter=severity_enum, rule_ids=rule_ids)
        
        if verbose:
            rprint(f"[dim]Analysis complete in {result.execution_time_ms}ms[/dim]")
        
        # AI suggestions if enabled
        if ai:
            try:
                claude = ClaudeService()
                if claude.is_available():
                    result.ai_suggestions = claude.generate_suggestions(result)
                    if verbose:
                        rprint("[dim]AI suggestions generated[/dim]")
                else:
                    rprint("[yellow]Warning: ANTHROPIC_API_KEY not set, skipping AI suggestions[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Warning: AI suggestions failed: {e}[/yellow]")
                logger.warning(f"AI suggestions failed: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()

        # Generate fixes if enabled
        if fix:
            try:
                claude = ClaudeService()
                if claude.is_available():
                    if verbose:
                        rprint(f"[dim]Generating fixes for {len(result.findings)} findings...[/dim]")
                    for finding in result.findings:
                        try:
                            generated_fix = claude.generate_fix(finding, content)
                            if generated_fix:
                                finding.ai_fix = generated_fix
                        except Exception as e:
                            logger.warning(f"Failed to generate fix for {finding.rule_id}: {e}")
                    fix_count = sum(1 for f in result.findings if f.ai_fix)
                    if verbose:
                        rprint(f"[dim]Generated {fix_count} fixes[/dim]")
                else:
                    rprint("[yellow]Warning: ANTHROPIC_API_KEY not set, skipping fix generation[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Warning: Fix generation failed: {e}[/yellow]")
                logger.warning(f"Fix generation failed: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
        
        # Output results
        format_lower = format.lower()
        if format_lower == "terminal":
            from pipelineiq.reporters.terminal import TerminalReporter
            reporter = TerminalReporter()
            if output:
                output_text = reporter.render(result)
                output.write_text(output_text)
            else:
                reporter.render(result, to_console=True)
        elif format_lower == "json":
            from pipelineiq.reporters.json_reporter import JsonReporter
            reporter = JsonReporter()
            output_text = reporter.render(result)
            if output:
                output.write_text(output_text)
            else:
                print(output_text)
        elif format_lower == "markdown":
            from pipelineiq.reporters.markdown import MarkdownReporter
            reporter = MarkdownReporter()
            output_text = reporter.render(result)
            if output:
                output.write_text(output_text)
            else:
                print(output_text)
        else:
            rprint(f"[red]Invalid format:[/red] {format}")
            rprint("Valid formats: terminal, json, markdown")
            raise typer.Exit(code=1)
        
        # Exit code based on findings
        if result.summary.score < 50:
            raise typer.Exit(code=2)  # Critical issues
        elif result.findings:
            raise typer.Exit(code=1)  # Has findings
        
    except ParseError as e:
        rprint(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(code=3)
    except FileNotFoundError:
        rprint(f"[red]File not found:[/red] {path}")
        raise typer.Exit(code=4)
    except typer.Exit:
        raise
    except Exception as e:
        if str(e):
            rprint(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(code=5)


@app.command("list-rules")
def list_rules() -> None:
    """List all available analysis rules."""
    from pipelineiq.core import AnalysisEngine
    
    engine = AnalysisEngine()
    
    rprint("\n[bold]Available Analysis Rules:[/bold]\n")
    
    for rule in engine.get_rules():
        severity_color = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "yellow",
            Severity.MEDIUM: "blue",
            Severity.LOW: "dim",
            Severity.INFO: "dim",
        }.get(rule.severity, "white")
        
        rprint(f"  [bold]{rule.id}[/bold]")
        rprint(f"    {rule.description}")
        rprint(f"    Severity: [{severity_color}]{rule.severity.value}[/{severity_color}]")
        rprint(f"    Category: {rule.category.value}")
        rprint()


@app.command()
def explain(
    rule_id: str = typer.Argument(..., help="Rule ID to explain"),
) -> None:
    """Explain a specific analysis rule."""
    from pipelineiq.core import AnalysisEngine
    
    engine = AnalysisEngine()
    
    for rule in engine.get_rules():
        if rule.id == rule_id:
            rprint(f"\n[bold]{rule.name}[/bold] ({rule.id})")
            rprint(f"\n{rule.description}")
            rprint(f"\n[dim]Severity:[/dim] {rule.severity.value}")
            rprint(f"[dim]Category:[/dim] {rule.category.value}")
            rprint(f"[dim]Platforms:[/dim] {', '.join(p.value for p in rule.platforms)}")
            return
    
    rprint(f"[red]Rule not found:[/red] {rule_id}")
    rprint("\nUse [bold]pipelineiq list-rules[/bold] to see available rules.")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
