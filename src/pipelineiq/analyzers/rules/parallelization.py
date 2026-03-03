"""Parallelization-related analysis rules."""

from pipelineiq.analyzers.base import AnalysisRule
from pipelineiq.core.dag import PipelineDAG
from pipelineiq.models import Category, Finding, Location, Pipeline, Severity


class ParallelStagesRule(AnalysisRule):
    """Detect independent stages that run sequentially.
    
    Uses the DAG to find stages that have no dependencies on each other
    but are not configured to run in parallel.
    """
    
    id = "parallel-stages"
    name = "Parallel Stages"
    description = "Independent stages that could run in parallel"
    category = Category.PARALLELIZATION
    severity = Severity.HIGH
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find independent stages not running in parallel."""
        findings: list[Finding] = []
        
        # Get parallelizable groups from DAG
        groups = dag.get_parallelizable_groups()
        
        for group in groups:
            if len(group) < 2:
                continue
            
            # Check if stages in this group are marked as parallel
            stages_in_group = [s for s in pipeline.stages if s.id in group]
            non_parallel = [s for s in stages_in_group if not s.parallel]
            
            # If we have multiple stages in a group and not all are parallel
            if len(non_parallel) >= 2:
                stage_names = [s.name for s in non_parallel]
                findings.append(self._create_finding(
                    message=f"Stages {stage_names} have no dependencies but run sequentially",
                    suggestion="Configure these stages to run in parallel",
                    location=Location(
                        file=pipeline.file_path,
                        stage=non_parallel[0].id,
                    ),
                    estimated_impact=f"Save {30 * (len(non_parallel) - 1)}-{60 * (len(non_parallel) - 1)} seconds",
                ))
        
        return findings


class ParallelStepsRule(AnalysisRule):
    """Detect independent steps within a job that could run in parallel.

    Uses command-based analysis to identify steps that don't depend on
    each other's output and could be grouped for parallel execution.
    """

    id = "parallel-steps"
    name = "Parallel Steps"
    description = "Independent steps that could run in parallel"
    category = Category.PARALLELIZATION
    severity = Severity.MEDIUM

    # Command patterns to categorize steps
    # Format: (category, [patterns that indicate this category])
    COMMAND_CATEGORIES = {
        "install": [
            "npm install", "npm ci", "yarn install", "yarn add",
            "pip install", "pip3 install", "poetry install", "pipenv install",
            "apt-get install", "apt install", "apk add", "yum install",
            "go mod download", "cargo fetch", "bundle install", "composer install",
            "pnpm install",
        ],
        "lint": [
            "npm run lint", "yarn lint", "pnpm lint",
            "eslint", "prettier", "tslint", "stylelint",
            "ruff check", "ruff", "flake8", "pylint", "mypy", "black --check",
            "golint", "golangci-lint", "go vet",
            "rubocop", "shellcheck", "hadolint",
        ],
        "format": [
            "npm run format", "yarn format", "pnpm format",
            "prettier --write", "black ", "autopep8", "yapf",
            "gofmt", "rustfmt", "shfmt",
        ],
        "test": [
            "npm test", "npm run test", "yarn test", "pnpm test",
            "jest", "vitest", "mocha", "ava",
            "pytest", "python -m pytest", "unittest", "nose",
            "go test", "cargo test", "rspec", "phpunit",
            "mvn test", "gradle test", "sbt test",
        ],
        "security": [
            "npm audit", "yarn audit", "pnpm audit",
            "snyk", "trivy", "grype", "safety check",
            "bandit", "semgrep", "codeql", "sonar",
            "dependency-check", "retire", "audit-ci",
        ],
        "build": [
            "npm run build", "yarn build", "pnpm build",
            "tsc", "webpack", "vite build", "rollup", "esbuild",
            "go build", "cargo build", "mvn package", "gradle build",
            "docker build", "make ", "cmake",
        ],
        "deploy": [
            "kubectl apply", "helm install", "helm upgrade",
            "aws ", "gcloud ", "az ", "terraform apply",
            "docker push", "npm publish",
        ],
    }

    # Categories that can run in parallel (after dependencies are met)
    PARALLELIZABLE_CATEGORIES = {"lint", "format", "test", "security"}

    # Dependencies: category -> list of categories that must run first
    CATEGORY_DEPENDENCIES = {
        "lint": ["install"],
        "format": ["install"],
        "test": ["install"],
        "security": ["install"],
        "build": ["install"],
        "deploy": ["build"],
    }

    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Find independent steps not running in parallel."""
        findings: list[Finding] = []

        for stage in pipeline.stages:
            for job in stage.jobs:
                if len(job.steps) < 2:
                    continue

                # Categorize each step by analyzing command and name
                categorized_steps, step_map = self._categorize_steps(job.steps)

                # Find parallelizable steps
                parallelizable = self._find_parallelizable_steps(
                    categorized_steps, step_map
                )

                if len(parallelizable) >= 2:
                    step_names = [s.name for s in parallelizable]
                    categories = list({categorized_steps[s.id] for s in parallelizable})
                    findings.append(self._create_finding(
                        message=(
                            f"Steps {step_names} in stage '{stage.name}' are independent "
                            f"({', '.join(categories)}) and could run in parallel"
                        ),
                        suggestion="Use step groups or parallel execution for independent steps",
                        location=Location(
                            file=pipeline.file_path,
                            stage=stage.id,
                            job=job.id,
                        ),
                        estimated_impact="Save 20-40% of combined step time",
                    ))

        return findings

    def _categorize_steps(self, steps: list) -> tuple[dict[str, str], dict[str, any]]:
        """Categorize steps by analyzing their commands and names.

        Returns:
            Tuple of (dict mapping step.id to category, dict mapping step.id to step)
        """
        categorized: dict[str, str] = {}
        step_map: dict[str, any] = {}

        for step in steps:
            category = self._detect_category(step)
            if category:
                categorized[step.id] = category
            step_map[step.id] = step

        return categorized, step_map

    def _detect_category(self, step) -> str | None:
        """Detect the category of a step from its command and name."""
        # Build search text from command and name
        search_text = ""
        if step.command:
            search_text += step.command.lower()
        if step.name:
            search_text += " " + step.name.lower()

        # Also check plugin/action name for action steps
        if step.plugin:
            search_text += " " + step.plugin.lower()

        if not search_text.strip():
            return None

        # Check each category's patterns
        for category, patterns in self.COMMAND_CATEGORIES.items():
            for pattern in patterns:
                if pattern.lower() in search_text:
                    return category

        return None

    def _find_parallelizable_steps(
        self, categorized_steps: dict[str, str], step_map: dict[str, any]
    ) -> list:
        """Find steps that could run in parallel.

        Returns steps that belong to parallelizable categories
        (lint, test, security, format). These steps are typically independent
        and can run concurrently.

        Note: We don't require explicit install steps - if lint/test/security
        steps exist, they can be parallelized regardless of whether install
        was done in the same job or elsewhere.
        """
        # Get steps by category
        steps_by_category: dict[str, list[str]] = {}
        for step_id, category in categorized_steps.items():
            if category not in steps_by_category:
                steps_by_category[category] = []
            steps_by_category[category].append(step_id)

        # Collect all parallelizable step IDs
        parallelizable_ids: list[str] = []
        for category in self.PARALLELIZABLE_CATEGORIES:
            if category in steps_by_category:
                parallelizable_ids.extend(steps_by_category[category])

        # Return actual step objects
        return [step_map[sid] for sid in parallelizable_ids if sid in step_map]
