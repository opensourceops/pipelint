"""Harness CI pipeline parser."""

from uuid import uuid4

import yaml

from pipelineiq.models import (
    CacheConfig,
    Job,
    Pipeline,
    Platform,
    ResourceSpec,
    RunnerConfig,
    Stage,
    Step,
    StepType,
)
from pipelineiq.parsers.base import ParseError, PipelineParser


class HarnessParser(PipelineParser):
    """Parser for Harness CI pipeline YAML files."""
    
    platform = Platform.HARNESS
    
    def parse(self, content: str, file_path: str) -> Pipeline:
        """Parse Harness pipeline YAML to Pipeline IR."""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML: {e}", file_path)
        
        if not isinstance(data, dict):
            raise ParseError("Pipeline must be a YAML mapping", file_path)
        
        if "pipeline" not in data:
            raise ParseError("Missing 'pipeline' key in YAML", file_path)
        
        pipeline_data = data["pipeline"]
        
        return Pipeline(
            id=pipeline_data.get("identifier", "unknown"),
            name=pipeline_data.get("name", "Unnamed Pipeline"),
            platform=Platform.HARNESS,
            file_path=file_path,
            stages=self._parse_stages(pipeline_data.get("stages", [])),
            variables=self._parse_variables(pipeline_data),
            properties=pipeline_data.get("properties", {}),
        )
    
    def _parse_stages(self, stages_data: list) -> list[Stage]:
        """Parse Harness stages to IR stages."""
        stages: list[Stage] = []
        previous_stage_id: str | None = None
        
        for stage_wrapper in stages_data:
            if "stage" in stage_wrapper:
                stage = self._parse_stage(stage_wrapper["stage"], previous_stage_id)
                stages.append(stage)
                previous_stage_id = stage.id
            elif "parallel" in stage_wrapper:
                # Handle parallel stage groups
                parallel_stages = stage_wrapper["parallel"]
                for parallel_item in parallel_stages:
                    if "stage" in parallel_item:
                        stage = self._parse_stage(parallel_item["stage"], previous_stage_id)
                        stage.parallel = True
                        stages.append(stage)
                # All parallel stages depend on previous, but next depends on all parallel
                if parallel_stages:
                    # Get last parallel stage id for next sequential stage dependency
                    parallel_ids = [
                        s["stage"].get("identifier", str(uuid4()))
                        for s in parallel_stages
                        if "stage" in s
                    ]
                    previous_stage_id = parallel_ids[-1] if parallel_ids else previous_stage_id
        
        return stages
    
    def _parse_stage(self, stage_data: dict, previous_stage_id: str | None = None) -> Stage:
        """Parse single Harness stage."""
        stage_id = stage_data.get("identifier", str(uuid4()))
        spec = stage_data.get("spec", {})
        execution = spec.get("execution", {})
        steps_data = execution.get("steps", [])
        
        # Handle dependencies - explicit or implicit sequential
        dependencies: list[str] = []
        if previous_stage_id and not stage_data.get("parallel"):
            dependencies = [previous_stage_id]
        
        # Build jobs from stage
        jobs = [
            Job(
                id=f"{stage_id}-job",
                name=stage_data.get("name", "Unnamed"),
                runner=self._parse_infrastructure(spec.get("infrastructure", {})),
                steps=self._parse_steps(steps_data),
                timeout_minutes=self._parse_timeout(stage_data.get("timeout")),
                cache=self._parse_cache(spec.get("caching")),
            )
        ]
        
        return Stage(
            id=stage_id,
            name=stage_data.get("name", "Unnamed Stage"),
            type=stage_data.get("type", "CI"),
            dependencies=dependencies,
            parallel=False,
            condition=stage_data.get("when", {}).get("condition"),
            jobs=jobs,
            variables=self._parse_stage_variables(stage_data),
        )
    
    def _parse_steps(self, steps_data: list) -> list[Step]:
        """Parse Harness steps to IR steps."""
        steps: list[Step] = []
        
        for step_wrapper in steps_data:
            if "step" in step_wrapper:
                step = self._parse_step(step_wrapper["step"])
                steps.append(step)
            elif "stepGroup" in step_wrapper:
                # Handle step groups - flatten into individual steps
                group = step_wrapper["stepGroup"]
                group_steps = group.get("steps", [])
                for gs in group_steps:
                    if "step" in gs:
                        step = self._parse_step(gs["step"])
                        steps.append(step)
            elif "parallel" in step_wrapper:
                # Handle parallel steps
                for ps in step_wrapper["parallel"]:
                    if "step" in ps:
                        step = self._parse_step(ps["step"])
                        steps.append(step)
        
        return steps
    
    def _parse_step(self, step_data: dict) -> Step:
        """Parse single Harness step."""
        step_type_str = step_data.get("type", "Run")
        spec = step_data.get("spec") or {}
        
        # Determine step type
        step_type = StepType.RUN
        command = None
        plugin = None
        plugin_version = None
        image = None
        
        if step_type_str == "Run":
            step_type = StepType.RUN
            command = spec.get("command")
            image = spec.get("image")
        elif step_type_str == "Plugin":
            step_type = StepType.PLUGIN
            plugin = spec.get("type") or spec.get("name")
            plugin_version = spec.get("version")
            image = spec.get("image")
        elif step_type_str == "Background":
            step_type = StepType.BACKGROUND
            command = spec.get("command")
            image = spec.get("image")
        elif step_type_str == "Action":
            step_type = StepType.ACTION
            plugin = spec.get("uses")
        
        # Safely extract condition from 'when' block
        when_block = step_data.get("when")
        condition = when_block.get("condition") if isinstance(when_block, dict) else None
        
        # Safely extract continue_on_error from failureStrategies
        continue_on_error = False
        failure_strategies = step_data.get("failureStrategies")
        if failure_strategies and isinstance(failure_strategies, list) and len(failure_strategies) > 0:
            first_strategy = failure_strategies[0]
            if isinstance(first_strategy, dict):
                on_failure = first_strategy.get("onFailure")
                if isinstance(on_failure, dict):
                    continue_on_error = on_failure.get("action") == "Ignore"
        
        return Step(
            id=step_data.get("identifier", str(uuid4())),
            name=step_data.get("name", "Unnamed Step"),
            type=step_type,
            command=command,
            plugin=plugin,
            plugin_version=plugin_version,
            image=image,
            inputs=spec.get("with") or {},
            environment=spec.get("envVariables") or {},
            condition=condition,
            timeout_minutes=self._parse_timeout(step_data.get("timeout")),
            continue_on_error=continue_on_error,
        )
    
    def _parse_infrastructure(self, infra_data: dict) -> RunnerConfig:
        """Parse Harness infrastructure to RunnerConfig."""
        infra_type = infra_data.get("type", "KubernetesDirect")
        spec = infra_data.get("spec", {})
        
        # Map Harness infra types to generic types
        runner_type = "kubernetes"
        if infra_type == "KubernetesDirect":
            runner_type = "kubernetes"
        elif infra_type == "Cloud":
            runner_type = "cloud"
        elif infra_type == "VM":
            runner_type = "vm"
        elif infra_type == "Docker":
            runner_type = "docker"
        
        os = spec.get("os", "Linux").lower()
        
        resources = None
        if spec.get("resources"):
            res = spec["resources"]
            resources = ResourceSpec(
                cpu=res.get("cpu"),
                memory=res.get("memory"),
            )
        
        return RunnerConfig(
            type=runner_type,
            os=os,
            image=spec.get("image"),
            resources=resources,
        )
    
    def _parse_cache(self, cache_data: dict | None) -> CacheConfig | None:
        """Parse Harness caching configuration."""
        if not cache_data or not cache_data.get("enabled"):
            return None
        
        return CacheConfig(
            key=cache_data.get("key", "default"),
            paths=cache_data.get("paths", []),
            restore_keys=cache_data.get("restoreKeys", []),
        )
    
    def _parse_timeout(self, timeout_str: str | None) -> int | None:
        """Parse timeout string to minutes."""
        if not timeout_str:
            return None
        
        # Handle formats like "10m", "1h", "30s"
        timeout_str = timeout_str.strip()
        if timeout_str.endswith("m"):
            return int(timeout_str[:-1])
        elif timeout_str.endswith("h"):
            return int(timeout_str[:-1]) * 60
        elif timeout_str.endswith("s"):
            return max(1, int(timeout_str[:-1]) // 60)
        
        return None
    
    def _parse_variables(self, pipeline_data: dict) -> dict[str, str]:
        """Parse pipeline-level variables."""
        variables: dict[str, str] = {}
        for var in pipeline_data.get("variables", []):
            if isinstance(var, dict):
                name = var.get("name", "")
                value = var.get("value", "")
                if name:
                    variables[name] = str(value)
        return variables
    
    def _parse_stage_variables(self, stage_data: dict) -> dict[str, str]:
        """Parse stage-level variables."""
        variables: dict[str, str] = {}
        spec = stage_data.get("spec", {})
        for var in spec.get("variables", []):
            if isinstance(var, dict):
                name = var.get("name", "")
                value = var.get("value", "")
                if name:
                    variables[name] = str(value)
        return variables
