"""Pipeline parsers for different CI platforms."""

from pipelineiq.models import Platform
from pipelineiq.parsers.base import ParseError, PipelineParser
from pipelineiq.parsers.harness import HarnessParser

__all__ = ["PipelineParser", "ParseError", "HarnessParser", "get_parser"]


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
    }
    
    if platform not in parsers:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(parsers.keys())}")
    
    return parsers[platform]()
