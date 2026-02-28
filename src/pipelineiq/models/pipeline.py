"""Pipeline Intermediate Representation (IR) models."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported CI platforms."""
    HARNESS = "harness"
    GITHUB = "github"
    GITLAB = "gitlab"
    CIRCLECI = "circleci"


class StepType(str, Enum):
    """Types of pipeline steps."""
    RUN = "run"
    PLUGIN = "plugin"
    ACTION = "action"
    BACKGROUND = "background"
    GROUP = "group"


class ResourceSpec(BaseModel):
    """Compute resource specification."""
    cpu: Optional[str] = None
    memory: Optional[str] = None


class RunnerConfig(BaseModel):
    """Execution environment configuration."""
    type: str  # kubernetes, cloud, vm, docker
    os: str = "linux"
    image: Optional[str] = None
    resources: Optional[ResourceSpec] = None


class CacheConfig(BaseModel):
    """Caching configuration."""
    key: str
    paths: list[str]
    restore_keys: list[str] = Field(default_factory=list)


class Step(BaseModel):
    """Individual execution step."""
    id: str
    name: str
    type: StepType
    command: Optional[str] = None
    plugin: Optional[str] = None
    plugin_version: Optional[str] = None
    image: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)
    condition: Optional[str] = None
    timeout_minutes: Optional[int] = None
    continue_on_error: bool = False


class Job(BaseModel):
    """Execution job within a stage."""
    id: str
    name: str
    runner: RunnerConfig
    steps: list[Step] = Field(default_factory=list)
    timeout_minutes: Optional[int] = None
    cache: Optional[CacheConfig] = None
    environment: dict[str, str] = Field(default_factory=dict)


class Stage(BaseModel):
    """Pipeline stage."""
    id: str
    name: str
    type: str = "CI"  # CI, CD, Custom
    dependencies: list[str] = Field(default_factory=list)
    parallel: bool = False
    condition: Optional[str] = None
    jobs: list[Job] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)


class Trigger(BaseModel):
    """Pipeline trigger configuration."""
    type: str  # push, pull_request, schedule, manual
    branches: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    paths_ignore: list[str] = Field(default_factory=list)


class Pipeline(BaseModel):
    """Root pipeline representation - Platform-agnostic IR."""
    id: str
    name: str
    platform: Platform
    file_path: str
    triggers: list[Trigger] = Field(default_factory=list)
    stages: list[Stage]
    variables: dict[str, str] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
