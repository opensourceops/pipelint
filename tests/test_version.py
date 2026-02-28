"""Test version and basic imports."""

def test_version():
    """Test that version is accessible."""
    from pipelineiq import __version__
    assert __version__ == "0.1.0"


def test_cli_import():
    """Test that CLI can be imported."""
    from pipelineiq.cli.main import app
    assert app is not None
