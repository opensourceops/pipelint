"""GitHub Actions workflow parser."""

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
    Trigger,
)
from pipelineiq.parsers.base import ParseError, PipelineParser


class GitHubActionsParser(PipelineParser):
    """Parser for GitHub Actions workflow YAML files."""

    platform = Platform.GITHUB

    def parse(self, content: str, file_path: str) -> Pipeline:
        """Parse GitHub Actions workflow YAML to Pipeline IR."""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML: {e}", file_path)

        if not isinstance(data, dict):
            raise ParseError("Workflow must be a YAML mapping", file_path)

        # GitHub Actions workflows must have 'jobs' key
        if "jobs" not in data:
            raise ParseError("Missing 'jobs' key in workflow", file_path)

        # Extract workflow name
        name = data.get("name", self._derive_name_from_path(file_path))

        # Handle 'on' key - YAML 1.1 parses 'on' as boolean True
        on_data = data.get("on") or data.get(True, {})

        return Pipeline(
            id=self._derive_id_from_path(file_path),
            name=name,
            platform=Platform.GITHUB,
            file_path=file_path,
            triggers=self._parse_triggers(on_data),
            stages=self._parse_jobs(data.get("jobs", {})),
            variables=self._parse_env(data.get("env", {})),
            properties=self._extract_properties(data),
        )

    def _derive_name_from_path(self, file_path: str) -> str:
        """Derive workflow name from file path."""
        # Extract filename without extension
        import os
        basename = os.path.basename(file_path)
        name = os.path.splitext(basename)[0]
        # Convert to title case, replace hyphens/underscores
        return name.replace("-", " ").replace("_", " ").title()

    def _derive_id_from_path(self, file_path: str) -> str:
        """Derive workflow ID from file path."""
        import os
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]

    def _parse_triggers(self, on_data: dict | list | str) -> list[Trigger]:
        """Parse GitHub Actions 'on' triggers."""
        triggers: list[Trigger] = []

        # Handle string format: on: push
        if isinstance(on_data, str):
            triggers.append(Trigger(type=self._map_trigger_type(on_data)))
            return triggers

        # Handle list format: on: [push, pull_request]
        if isinstance(on_data, list):
            for event in on_data:
                triggers.append(Trigger(type=self._map_trigger_type(event)))
            return triggers

        # Handle dict format: on: { push: { branches: [...] } }
        if isinstance(on_data, dict):
            for event, config in on_data.items():
                trigger = Trigger(type=self._map_trigger_type(event))
                if isinstance(config, dict):
                    trigger.branches = config.get("branches", [])
                    trigger.paths = config.get("paths", [])
                    trigger.paths_ignore = config.get("paths-ignore", [])
                triggers.append(trigger)

        return triggers

    def _map_trigger_type(self, event: str) -> str:
        """Map GitHub event to generic trigger type."""
        mapping = {
            "push": "push",
            "pull_request": "pull_request",
            "pull_request_target": "pull_request",
            "schedule": "schedule",
            "workflow_dispatch": "manual",
            "repository_dispatch": "manual",
            "release": "release",
            "workflow_call": "workflow_call",
        }
        return mapping.get(event, event)

    def _parse_jobs(self, jobs_data: dict) -> list[Stage]:
        """Parse GitHub Actions jobs to IR stages."""
        stages: list[Stage] = []

        for job_id, job_data in jobs_data.items():
            if not isinstance(job_data, dict):
                continue

            stage = self._parse_job(job_id, job_data)
            stages.append(stage)

        return stages

    def _parse_job(self, job_id: str, job_data: dict) -> Stage:
        """Parse single GitHub Actions job to IR stage."""
        # Parse dependencies from 'needs'
        needs = job_data.get("needs", [])
        if isinstance(needs, str):
            dependencies = [needs]
        else:
            dependencies = list(needs) if needs else []

        # Parse runner configuration
        runner = self._parse_runner(job_data)

        # Parse steps
        steps = self._parse_steps(job_data.get("steps", []))

        # Parse cache from steps (GitHub uses actions/cache)
        cache = self._extract_cache_from_steps(steps, job_data)

        # Parse timeout
        timeout = job_data.get("timeout-minutes")

        # Create job
        job = Job(
            id=f"{job_id}-job",
            name=job_data.get("name", job_id),
            runner=runner,
            steps=steps,
            timeout_minutes=timeout,
            cache=cache,
            environment=self._parse_env(job_data.get("env", {})),
        )

        # Check if job is part of a matrix (parallel)
        is_parallel = "matrix" in job_data.get("strategy", {})

        return Stage(
            id=job_id,
            name=job_data.get("name", job_id),
            type="CI",
            dependencies=dependencies,
            parallel=is_parallel,
            condition=job_data.get("if"),
            jobs=[job],
            variables=self._parse_env(job_data.get("env", {})),
        )

    def _parse_runner(self, job_data: dict) -> RunnerConfig:
        """Parse runs-on to RunnerConfig."""
        runs_on = job_data.get("runs-on", "ubuntu-latest")

        # Handle matrix expression
        if isinstance(runs_on, str) and runs_on.startswith("${{"):
            runs_on = "ubuntu-latest"  # Default for matrix

        # Handle list format (self-hosted runners)
        if isinstance(runs_on, list):
            runs_on = runs_on[0] if runs_on else "ubuntu-latest"

        # Determine OS and runner type
        os_type = "linux"
        runner_type = "cloud"
        image = runs_on

        runs_on_lower = runs_on.lower()
        if "ubuntu" in runs_on_lower or "linux" in runs_on_lower:
            os_type = "linux"
        elif "windows" in runs_on_lower:
            os_type = "windows"
        elif "macos" in runs_on_lower or "mac" in runs_on_lower:
            os_type = "macos"

        if "self-hosted" in runs_on_lower:
            runner_type = "self-hosted"

        # Parse container if specified
        container = job_data.get("container")
        if container:
            if isinstance(container, str):
                image = container
            elif isinstance(container, dict):
                image = container.get("image", runs_on)

        return RunnerConfig(
            type=runner_type,
            os=os_type,
            image=image,
        )

    def _parse_steps(self, steps_data: list) -> list[Step]:
        """Parse GitHub Actions steps to IR steps."""
        steps: list[Step] = []

        for i, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                continue

            step = self._parse_step(step_data, i)
            steps.append(step)

        return steps

    def _parse_step(self, step_data: dict, index: int) -> Step:
        """Parse single GitHub Actions step."""
        step_id = step_data.get("id", f"step-{index}")
        step_name = step_data.get("name", f"Step {index + 1}")

        # Determine step type
        step_type = StepType.RUN
        command = None
        plugin = None
        plugin_version = None
        image = None

        if "uses" in step_data:
            # Action step
            step_type = StepType.ACTION
            uses = step_data["uses"]
            plugin, plugin_version = self._parse_uses(uses)
        elif "run" in step_data:
            # Run step
            step_type = StepType.RUN
            command = step_data["run"]

        # Parse inputs from 'with'
        inputs = step_data.get("with", {})

        # Parse environment
        environment = self._parse_env(step_data.get("env", {}))

        # Parse timeout (GitHub uses timeout-minutes)
        timeout = step_data.get("timeout-minutes")

        # Parse continue-on-error
        continue_on_error = step_data.get("continue-on-error", False)

        return Step(
            id=step_id,
            name=step_name,
            type=step_type,
            command=command,
            plugin=plugin,
            plugin_version=plugin_version,
            image=image,
            inputs=inputs,
            environment=environment,
            condition=step_data.get("if"),
            timeout_minutes=timeout,
            continue_on_error=continue_on_error,
        )

    def _parse_uses(self, uses: str) -> tuple[str, str | None]:
        """Parse action 'uses' string to plugin name and version."""
        # Format: owner/repo@version or ./local-action
        if "@" in uses:
            parts = uses.rsplit("@", 1)
            return parts[0], parts[1]
        return uses, None

    def _parse_env(self, env_data: dict) -> dict[str, str]:
        """Parse environment variables."""
        if not isinstance(env_data, dict):
            return {}
        return {k: str(v) for k, v in env_data.items()}

    def _extract_cache_from_steps(
        self, steps: list[Step], job_data: dict
    ) -> CacheConfig | None:
        """Extract cache configuration from actions/cache step."""
        for step in steps:
            if step.plugin and "actions/cache" in step.plugin:
                return CacheConfig(
                    key=step.inputs.get("key", "default"),
                    paths=self._parse_cache_paths(step.inputs.get("path", "")),
                    restore_keys=self._parse_restore_keys(
                        step.inputs.get("restore-keys", "")
                    ),
                )
        return None

    def _parse_cache_paths(self, path_value: str | list) -> list[str]:
        """Parse cache path(s) to list."""
        if isinstance(path_value, list):
            return path_value
        if isinstance(path_value, str):
            # Handle multi-line paths
            return [p.strip() for p in path_value.split("\n") if p.strip()]
        return []

    def _parse_restore_keys(self, restore_keys: str | list) -> list[str]:
        """Parse restore keys to list."""
        if isinstance(restore_keys, list):
            return restore_keys
        if isinstance(restore_keys, str):
            return [k.strip() for k in restore_keys.split("\n") if k.strip()]
        return []

    def _extract_properties(self, data: dict) -> dict:
        """Extract additional workflow properties."""
        props = {}
        if "concurrency" in data:
            props["concurrency"] = data["concurrency"]
        if "permissions" in data:
            props["permissions"] = data["permissions"]
        if "defaults" in data:
            props["defaults"] = data["defaults"]
        return props
