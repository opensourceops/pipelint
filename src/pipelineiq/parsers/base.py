"""Base parser interface."""

from abc import ABC, abstractmethod

from pipelineiq.models import Pipeline, Platform


class PipelineParser(ABC):
    """Base class for all CI platform parsers."""
    
    platform: Platform
    
    @abstractmethod
    def parse(self, content: str, file_path: str) -> Pipeline:
        """Parse YAML content to Pipeline IR.
        
        Args:
            content: Raw YAML content as string
            file_path: Path to the pipeline file
            
        Returns:
            Pipeline IR representation
            
        Raises:
            ParseError: If the content cannot be parsed
        """
        pass


class ParseError(Exception):
    """Raised when pipeline parsing fails."""
    
    def __init__(self, message: str, file_path: str | None = None, line: int | None = None):
        self.file_path = file_path
        self.line = line
        super().__init__(message)
