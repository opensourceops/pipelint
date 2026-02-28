"""Main CLI application."""

import typer

app = typer.Typer(
    name="pipelineiq",
    help="AI-powered CI pipeline analyzer",
    add_completion=False,
)


@app.callback()
def callback() -> None:
    """PipelineIQ - Analyze and optimize your CI pipelines."""
    pass


@app.command()
def version() -> None:
    """Show version information."""
    from pipelineiq import __version__
    from rich import print as rprint
    
    rprint(f"[bold blue]PipelineIQ[/bold blue] v{__version__}")


if __name__ == "__main__":
    app()
