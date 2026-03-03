"""Pipeline parsers for different CI platforms."""

from pipelineiq.models import Platform
from pipelineiq.parsers.base import ParseError, PipelineParser
from pipelineiq.parsers.github import GitHubActionsParser
from pipelineiq.parsers.harness import HarnessParser

__all__ = [
    "PipelineParser",
    "ParseError",
    "HarnessParser",
    "GitHubActionsParser",
    "get_parser",
]


def get_parser(platform: Platform) -> PipelineParser:
    """Get parser for the specified platform.

    Args:
        platform: CI platform to get parser for

    Returns:
        Parser instance for the platform

    Raises:
        ValueError: If platform is not supported
    """
    parsers = {
        Platform.HARNESS: HarnessParser,
        Platform.GITHUB: GitHubActionsParser,
    }

    if platform not in parsers:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(parsers.keys())}")

    return parsers[platform]()
