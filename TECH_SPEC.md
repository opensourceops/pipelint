# PipelineIQ - Technical Specification

**Version:** 1.0.0  
**Last Updated:** February 28, 2026  
**Author:** Abhay  
**Status:** Draft

---

## 1. Overview

This document defines the technical architecture, data structures, algorithms, and implementation details for PipelineIQ - an AI-powered CI pipeline analyzer.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PipelineIQ                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐   ┌─────────┐   ┌───────────┐   ┌──────────┐   ┌───────────┐  │
│  │  INPUT  │──▶│ PARSER  │──▶│ NORMALIZER│──▶│ ANALYZER │──▶│ REPORTER  │  │
│  │  LAYER  │   │  LAYER  │   │   (IR)    │   │  ENGINE  │   │   LAYER   │  │
│  └─────────┘   └─────────┘   └───────────┘   └────┬─────┘   └───────────┘  │
│       │             │              │              │               │         │
│       │             │              │              ▼               │         │
│       │             │              │         ┌─────────┐          │         │
│       │             │              │         │   AI    │          │         │
│       │             │              │         │ SERVICE │          │         │
│       │             │              │         └─────────┘          │         │
│       ▼             ▼              ▼                              ▼         │
│   File Path +   Platform      Pipeline         Rules +        Terminal/    │
│   Platform      Specific       Model           Claude         JSON/MD      │
│   (user arg)    YAML                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Overview

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **Input Layer** | Load pipeline file | File path + platform flag | Raw YAML string |
| **Parser Layer** | Parse platform-specific YAML | Raw YAML + Platform | Platform-specific dict |
| **Normalizer** | Convert to common IR | Platform dict | Pipeline IR (unified model) |
| **DAG Builder** | Build dependency graph | Pipeline IR | NetworkX DAG |
| **Analyzer Engine** | Execute analysis rules | Pipeline IR + DAG | List[Finding] |
| **AI Service** | Generate AI suggestions | Finding + Context | Enhanced Finding |
| **Reporter Layer** | Format output | AnalysisResult | Formatted string |

### 2.3 Data Flow

```
1. User invokes: pipelineiq analyze pipeline.yaml --platform harness

2. Input Layer:
   - Read file from provided path
   - Use platform from --platform flag (required)
   - Return (content: str, platform: Platform, path: str)

3. Parser Layer:
   - Select parser based on platform (e.g., HarnessParser)
   - Parse YAML to platform-specific dict structure
   - Return raw parsed dict

4. Normalizer:
   - Transform platform dict to Pipeline IR
   - Validate structure
   - Return Pipeline object (unified model)

5. DAG Builder:
   - Build NetworkX DiGraph from Pipeline stages
   - Calculate critical path (longest execution path)
   - Identify parallel opportunities
   - Return PipelineDAG object

6. Analyzer Engine:
   - Load enabled rules
   - Execute each rule against Pipeline + DAG
   - Collect all findings
   - Calculate summary statistics
   - Return List[Finding]

7. AI Service (if enabled):
   - For each finding, generate explanation
   - Optionally generate fixes
   - Return enhanced findings

8. Reporter Layer:
   - Select reporter based on format
   - Render AnalysisResult
   - Output to terminal/file
```

---

## 2.4 Why Normalizer? What is Pipeline IR?

### The Problem: Every CI Platform is Different

Each CI platform has its own YAML structure:

| Platform | Pipeline | Stage | Job | Step |
|----------|----------|-------|-----|------|
| **Harness** | `pipeline.stages[].stage` | `stage.spec.execution` | (embedded in stage) | `steps[].step` |
| **GitHub** | `jobs` (flat) | (no stages) | `jobs.<id>` | `steps[]` |
| **GitLab** | `stages[]` + jobs | stage name | job key | `script[]` |
| **CircleCI** | `workflows` | `workflows.<name>` | `jobs.<name>` | `steps[]` |

**Without normalization:** We'd need separate analysis rules for each platform. 8 rules × 4 platforms = 32 rule implementations!

### The Solution: Intermediate Representation (IR)

**Pipeline IR** is a **unified data model** that represents any CI pipeline, regardless of platform.

```
                    ┌─────────────────┐
   Harness YAML ───▶│                 │
   GitHub YAML ────▶│  Pipeline IR    │───▶ ONE set of analysis rules
   GitLab YAML ────▶│  (unified model)│
   CircleCI YAML ──▶│                 │
                    └─────────────────┘
```

**Benefits:**
1. **Write rules once** - Rules work on IR, automatically support all platforms
2. **Add platforms easily** - Just add a new parser, rules work instantly
3. **Consistent analysis** - Same rule = same results across platforms
4. **Simpler testing** - Test rules against IR, not platform-specific YAML

### IR Structure (Simplified)

```
Pipeline
├── id, name, platform
├── stages[]
│   ├── id, name
│   ├── dependencies[]    ← which stages must run first
│   ├── parallel: bool    ← runs in parallel with siblings?
│   └── jobs[]
│       ├── id, name
│       ├── runner (image, resources)
│       ├── cache config
│       └── steps[]
│           ├── id, name, type (run/plugin)
│           ├── command or plugin name
│           └── image, environment, timeout
└── variables, triggers
```

---

## 2.5 What is DAG Builder? Why Do We Need It?

### The Problem: Understanding Pipeline Structure

A pipeline YAML tells us *what* runs, but not the *relationships*:
- Which stages depend on which?
- What's the longest path (bottleneck)?
- Which stages could run in parallel but don't?

### The Solution: Directed Acyclic Graph (DAG)

A **DAG** is a graph where:
- **Nodes** = Stages (or jobs)
- **Edges** = Dependencies ("stage B needs stage A to finish first")
- **Acyclic** = No circular dependencies (A→B→C→A is invalid)

```
Example Pipeline:

  ┌─────────┐     ┌─────────┐
  │  Build  │────▶│  Test   │
  └─────────┘     └────┬────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  ┌─────────┐     ┌─────────┐     ┌─────────┐
  │  Lint   │     │  E2E    │     │  Scan   │
  └────┬────┘     └────┬────┘     └────┬────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                 ┌─────────┐
                 │ Deploy  │
                 └─────────┘
```

### What DAG Builder Does

| Function | Purpose | How It Helps |
|----------|---------|-------------|
| **Build graph** | Create nodes/edges from stages | Visualize structure |
| **Critical path** | Find longest execution path | Identify where to optimize |
| **Find roots** | Stages with no dependencies | What runs first |
| **Parallel groups** | Stages that CAN run together | Parallelization opportunities |
| **Bottlenecks** | Stages many others wait for | Focus optimization efforts |

### Example Analysis from DAG

```python
dag.get_critical_path()  
# Returns: ["Build", "Test", "E2E", "Deploy"]
# This is the slowest path - optimizing these stages has most impact

dag.get_parallelizable_groups()
# Returns: [["Build"], ["Test"], ["Lint", "E2E", "Scan"], ["Deploy"]]
# "Lint", "E2E", "Scan" can run in parallel!

dag.get_bottlenecks()
# Returns: ["Test"]  
# Test has 3 dependents - it's a bottleneck
```

---

## 2.6 Layman's Explanation: What Happens for End User?

### The User's Journey

**Step 1: User has a CI pipeline file**
```
User has: .harness/pipeline.yaml (their build/test/deploy config)
```

**Step 2: User runs PipelineIQ**
```bash
pipelineiq analyze .harness/pipeline.yaml --platform harness
```

**Step 3: Behind the scenes (what PipelineIQ does)**

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  1. READ FILE                                                       │
│     "Let me read your pipeline.yaml file..."                       │
│                                                                     │
│  2. PARSE IT                                                        │
│     "Ah, this is Harness format. Let me understand the structure." │
│                                                                     │
│  3. NORMALIZE                                                       │
│     "Converting to my standard format so I can analyze it."        │
│                                                                     │
│  4. BUILD THE MAP                                                   │
│     "Let me map out how your stages connect to each other."        │
│     "Build → Test → Deploy... got it."                             │
│                                                                     │
│  5. RUN CHECKS                                                      │
│     "Checking for common problems..."                              │
│     ✗ "You're installing npm packages but not caching them!"       │
│     ✗ "These 2 stages could run in parallel but don't."            │
│     ✗ "This image uses 'latest' tag - risky!"                      │
│                                                                     │
│  6. ASK AI (optional)                                               │
│     "Let me ask Claude for specific fix suggestions..."            │
│                                                                     │
│  7. SHOW RESULTS                                                    │
│     "Here's your report with score and recommendations."           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Step 4: User sees the report**

```
╭──────────────────── PipelineIQ Analysis Report ─────────────────────╮
│ Pipeline: .harness/pipeline.yaml                                    │
│ Platform: harness                                                   │
╰─────────────────────────────────────────────────────────────────────╯

┌─────────────────────────── Summary ─────────────────────────────────┐
│ Score: 65/100  |  Findings: 4                                       │
│ 🟠 2 high  |  🟡 1 medium  |  🔵 1 low                               │
└─────────────────────────────────────────────────────────────────────┘

🟠 HIGH
  [cache-dependencies]
  npm install detected without caching
  → Add cache configuration for node_modules
  Impact: Save 30-120 seconds per run

  [parallel-stages]
  Stages ["Lint", "Test"] have no dependencies but run sequentially
  → Configure these stages to run in parallel
  Impact: Save 30-50% of combined stage time

🟡 MEDIUM  
  [missing-timeout]
  Job 'build-job' has no timeout configured
  → Add timeout to prevent zombie jobs (recommended: 30-60 min)

💡 AI Suggestions:
  • Your pipeline spends most time in the Test stage - consider 
    splitting tests into parallel jobs
  • Add dependency caching to save ~2 minutes per build
```

**Step 5: User fixes their pipeline**

Based on the report, user:
1. Adds caching for npm dependencies
2. Configures Lint and Test to run in parallel
3. Adds timeout to jobs

**Result:** Pipeline runs 40% faster, costs less!

---

## 3. Technology Stack

### 3.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **Python** | 3.11+ | Runtime |
| **Typer** | 0.9+ | CLI framework |
| **Rich** | 13.7+ | Terminal formatting |
| **PyYAML** | 6.0+ | YAML parsing |
| **Pydantic** | 2.6+ | Data validation |
| **NetworkX** | 3.2+ | Graph algorithms |
| **Anthropic** | 0.18+ | Claude AI API |

### 3.2 Development Dependencies

| Package | Purpose |
|---------|---------|
| **Poetry** | Dependency management |
| **pytest** | Testing |
| **pytest-cov** | Coverage |
| **ruff** | Linting |
| **mypy** | Type checking |

### 3.3 Why These Choices

| Choice | Rationale |
|--------|-----------|
| **Python** | Rich ecosystem, fast development, AI library support |
| **Typer** | Modern CLI with auto-docs, type hints, Rich integration |
| **Pydantic** | Runtime validation, serialization, IDE support |
| **NetworkX** | Battle-tested graph library, algorithms built-in |
| **Claude** | Superior code analysis, large context, accurate YAML generation |

---

## 4. Data Models

### 4.1 Pipeline Intermediate Representation (IR)

The IR is a platform-agnostic representation of any CI pipeline.

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Platform(str, Enum):
    HARNESS = "harness"
    GITHUB = "github"
    GITLAB = "gitlab"
    CIRCLECI = "circleci"

class StepType(str, Enum):
    RUN = "run"
    PLUGIN = "plugin"
    ACTION = "action"
    BACKGROUND = "background"
    GROUP = "group"

class ResourceSpec(BaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None

class RunnerConfig(BaseModel):
    type: str  # kubernetes, cloud, vm, docker
    os: str = "linux"
    image: Optional[str] = None
    resources: Optional[ResourceSpec] = None

class CacheConfig(BaseModel):
    key: str
    paths: list[str]
    restore_keys: list[str] = Field(default_factory=list)

class Step(BaseModel):
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
    id: str
    name: str
    runner: RunnerConfig
    steps: list[Step]
    timeout_minutes: Optional[int] = None
    cache: Optional[CacheConfig] = None
    environment: dict[str, str] = Field(default_factory=dict)

class Stage(BaseModel):
    id: str
    name: str
    type: str  # CI, CD, Custom
    dependencies: list[str] = Field(default_factory=list)
    parallel: bool = False
    condition: Optional[str] = None
    jobs: list[Job] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)

class Trigger(BaseModel):
    type: str  # push, pull_request, schedule, manual
    branches: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    paths_ignore: list[str] = Field(default_factory=list)

class Pipeline(BaseModel):
    id: str
    name: str
    platform: Platform
    file_path: str
    triggers: list[Trigger] = Field(default_factory=list)
    stages: list[Stage]
    variables: dict[str, str] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
```

### 4.2 Analysis Finding Model

```python
class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Category(str, Enum):
    CACHING = "caching"
    PARALLELIZATION = "parallelization"
    SECURITY = "security"
    BEST_PRACTICE = "best-practice"
    RESOURCE = "resource"
    REDUNDANCY = "redundancy"
    RELIABILITY = "reliability"

class Location(BaseModel):
    file: str
    line: Optional[int] = None
    stage: Optional[str] = None
    job: Optional[str] = None
    step: Optional[str] = None

class Fix(BaseModel):
    type: str  # add, remove, modify
    description: str
    original: Optional[str] = None
    replacement: str

class Finding(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: Severity
    category: Category
    message: str
    suggestion: str
    location: Location
    estimated_impact: Optional[str] = None
    fix: Optional[Fix] = None
    references: list[str] = Field(default_factory=list)
    ai_explanation: Optional[str] = None
```

### 4.3 Analysis Result Model

```python
class AnalysisSummary(BaseModel):
    score: int  # 0-100
    total_findings: int
    by_severity: dict[Severity, int]
    by_category: dict[Category, int]
    estimated_time_savings: Optional[str] = None
    critical_path: list[str] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    pipeline: Pipeline
    findings: list[Finding]
    summary: AnalysisSummary
    dag_edges: list[tuple[str, str]]  # Serialized DAG
    ai_suggestions: list[str] = Field(default_factory=list)
    execution_time_ms: int
    analyzer_version: str
```

---

## 5. Parser Implementation

### 5.1 Parser Interface

```python
from abc import ABC, abstractmethod

class PipelineParser(ABC):
    """Base class for all CI platform parsers."""
    
    platform: Platform  # Which platform this parser handles
    
    @abstractmethod
    def parse(self, content: str, file_path: str) -> Pipeline:
        """Parse YAML content to Pipeline IR."""
        pass
```

> **Note:** Platform is specified by user via `--platform` flag, no auto-detection needed.

### 5.2 Harness Parser

```python
class HarnessParser(PipelineParser):
    platform = Platform.HARNESS
    
    def parse(self, content: str, file_path: str) -> Pipeline:
        """Parse Harness pipeline YAML."""
        data = yaml.safe_load(content)
        pipeline_data = data["pipeline"]
        
        return Pipeline(
            id=pipeline_data.get("identifier", "unknown"),
            name=pipeline_data.get("name", "Unnamed"),
            platform=Platform.HARNESS,
            file_path=file_path,
            stages=self._parse_stages(pipeline_data.get("stages", [])),
            variables=self._parse_variables(pipeline_data),
            properties=pipeline_data.get("properties", {}),
        )
    
    def _parse_stages(self, stages_data: list) -> list[Stage]:
        """Parse Harness stages to IR stages."""
        stages = []
        for stage_wrapper in stages_data:
            if "stage" in stage_wrapper:
                stage_data = stage_wrapper["stage"]
                stages.append(self._parse_stage(stage_data))
            elif "parallel" in stage_wrapper:
                # Handle parallel stage groups
                for parallel_stage in stage_wrapper["parallel"]:
                    stage = self._parse_stage(parallel_stage["stage"])
                    stage.parallel = True
                    stages.append(stage)
        return stages
    
    def _parse_stage(self, stage_data: dict) -> Stage:
        """Parse single Harness stage."""
        spec = stage_data.get("spec", {})
        execution = spec.get("execution", {})
        steps_data = execution.get("steps", [])
        
        return Stage(
            id=stage_data.get("identifier", str(uuid4())),
            name=stage_data.get("name", "Unnamed"),
            type=stage_data.get("type", "CI"),
            jobs=[Job(
                id=f"{stage_data.get('identifier')}-job",
                name=stage_data.get("name", ""),
                runner=self._parse_infrastructure(spec.get("infrastructure", {})),
                steps=self._parse_steps(steps_data),
            )],
        )
    
    def _parse_steps(self, steps_data: list) -> list[Step]:
        """Parse Harness steps to IR steps."""
        steps = []
        for step_wrapper in steps_data:
            if "step" in step_wrapper:
                step_data = step_wrapper["step"]
                steps.append(self._parse_step(step_data))
            elif "stepGroup" in step_wrapper:
                # Handle step groups
                group_data = step_wrapper["stepGroup"]
                for group_step in group_data.get("steps", []):
                    steps.append(self._parse_step(group_step["step"]))
        return steps
    
    def _parse_step(self, step_data: dict) -> Step:
        """Parse single Harness step."""
        spec = step_data.get("spec", {})
        step_type = step_data.get("type", "Run")
        
        return Step(
            id=step_data.get("identifier", str(uuid4())),
            name=step_data.get("name", "Unnamed"),
            type=StepType.RUN if step_type == "Run" else StepType.PLUGIN,
            command=spec.get("command"),
            image=spec.get("image"),
            plugin=step_type if step_type != "Run" else None,
            environment=spec.get("envVariables", {}),
        )
    
    def _parse_infrastructure(self, infra_data: dict) -> RunnerConfig:
        """Parse Harness infrastructure config."""
        infra_type = infra_data.get("type", "KubernetesDirect")
        spec = infra_data.get("spec", {})
        
        return RunnerConfig(
            type=infra_type.lower(),
            os="linux",  # Default
        )
```

---

## 6. DAG Builder

### 6.1 DAG Construction

```python
import networkx as nx

class PipelineDAG:
    """Directed Acyclic Graph representation of pipeline."""
    
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.graph = nx.DiGraph()
        self._build_graph()
    
    def _build_graph(self):
        """Build graph from pipeline stages."""
        # Add nodes for each stage
        for stage in self.pipeline.stages:
            self.graph.add_node(
                stage.id,
                name=stage.name,
                type=stage.type,
                parallel=stage.parallel,
            )
        
        # Add edges for dependencies
        for stage in self.pipeline.stages:
            for dep_id in stage.dependencies:
                if dep_id in self.graph:
                    self.graph.add_edge(dep_id, stage.id)
        
        # Infer sequential dependencies if none specified
        if not any(stage.dependencies for stage in self.pipeline.stages):
            self._infer_sequential_dependencies()
    
    def _infer_sequential_dependencies(self):
        """Infer dependencies from stage order (Harness default)."""
        non_parallel_stages = [s for s in self.pipeline.stages if not s.parallel]
        for i in range(1, len(non_parallel_stages)):
            prev_stage = non_parallel_stages[i - 1]
            curr_stage = non_parallel_stages[i]
            self.graph.add_edge(prev_stage.id, curr_stage.id)
    
    def get_critical_path(self) -> list[str]:
        """Get the longest path through the pipeline."""
        if not self.graph.nodes():
            return []
        try:
            return nx.dag_longest_path(self.graph)
        except nx.NetworkXError:
            return list(self.graph.nodes())
    
    def get_independent_stages(self) -> list[str]:
        """Get stages with no dependencies (roots)."""
        return [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
    
    def get_parallelizable_groups(self) -> list[list[str]]:
        """Get groups of stages that can run in parallel."""
        return [list(gen) for gen in nx.topological_generations(self.graph)]
    
    def get_bottlenecks(self) -> list[str]:
        """Get stages that are bottlenecks (many dependents)."""
        bottlenecks = []
        for node in self.graph.nodes():
            if self.graph.out_degree(node) > 1:
                bottlenecks.append(node)
        return bottlenecks
```

---

## 7. Analysis Engine

### 7.1 Rule Interface

```python
from abc import ABC, abstractmethod

class AnalysisRule(ABC):
    """Base class for all analysis rules."""
    
    id: str
    name: str
    description: str
    category: Category
    severity: Severity
    platforms: list[Platform] = [Platform.HARNESS]
    
    @abstractmethod
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        """Execute analysis and return findings."""
        pass
    
    def get_fix(self, finding: Finding, pipeline: Pipeline) -> Optional[Fix]:
        """Generate fix for finding (optional)."""
        return None
    
    def _create_finding(
        self,
        message: str,
        suggestion: str,
        location: Location,
        estimated_impact: Optional[str] = None,
        fix: Optional[Fix] = None,
    ) -> Finding:
        """Helper to create a finding."""
        return Finding(
            id=f"{self.id}-{uuid4().hex[:8]}",
            rule_id=self.id,
            rule_name=self.name,
            severity=self.severity,
            category=self.category,
            message=message,
            suggestion=suggestion,
            location=location,
            estimated_impact=estimated_impact,
            fix=fix,
        )
```

### 7.2 Rule Implementations

#### CacheDependenciesRule

```python
class CacheDependenciesRule(AnalysisRule):
    """Detect missing dependency caching."""
    
    id = "cache-dependencies"
    name = "Cache Dependencies"
    description = "Detects dependency installation without caching"
    category = Category.CACHING
    severity = Severity.HIGH
    
    INSTALL_PATTERNS = {
        "npm": ["npm install", "npm ci", "yarn install", "pnpm install"],
        "pip": ["pip install", "poetry install", "pip3 install"],
        "maven": ["mvn install", "mvn package", "./mvnw"],
        "gradle": ["gradle build", "./gradlew", "gradle assemble"],
        "go": ["go mod download", "go get"],
        "bundler": ["bundle install", "gem install"],
    }
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        findings = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                has_cache = job.cache is not None
                install_steps = self._find_install_steps(job.steps)
                
                for step, pkg_manager in install_steps:
                    if not has_cache and not self._has_cache_step(job.steps):
                        findings.append(self._create_finding(
                            message=f"{pkg_manager} install detected without caching",
                            suggestion=f"Add cache configuration for {pkg_manager} dependencies",
                            location=Location(
                                file=pipeline.file_path,
                                stage=stage.id,
                                job=job.id,
                                step=step.id,
                            ),
                            estimated_impact="Save 30-120 seconds per run",
                        ))
        
        return findings
    
    def _find_install_steps(self, steps: list[Step]) -> list[tuple[Step, str]]:
        """Find steps that install dependencies."""
        results = []
        for step in steps:
            if step.command:
                for pkg_manager, patterns in self.INSTALL_PATTERNS.items():
                    if any(p in step.command for p in patterns):
                        results.append((step, pkg_manager))
                        break
        return results
    
    def _has_cache_step(self, steps: list[Step]) -> bool:
        """Check if there's a cache-related step."""
        for step in steps:
            if step.plugin and "cache" in step.plugin.lower():
                return True
            if step.name and "cache" in step.name.lower():
                return True
        return False
```

#### ParallelStagesRule

```python
class ParallelStagesRule(AnalysisRule):
    """Detect stages that could run in parallel."""
    
    id = "parallel-stages"
    name = "Parallelize Independent Stages"
    description = "Identifies stages with no dependencies that run sequentially"
    category = Category.PARALLELIZATION
    severity = Severity.HIGH
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        findings = []
        
        # Get parallelizable groups
        groups = dag.get_parallelizable_groups()
        
        for group in groups:
            if len(group) > 1:
                # Check if they're actually configured as parallel
                stages_in_group = [s for s in pipeline.stages if s.id in group]
                non_parallel = [s for s in stages_in_group if not s.parallel]
                
                if len(non_parallel) > 1:
                    stage_names = [s.name for s in non_parallel]
                    findings.append(self._create_finding(
                        message=f"Stages {stage_names} have no dependencies but run sequentially",
                        suggestion="Configure these stages to run in parallel",
                        location=Location(
                            file=pipeline.file_path,
                            stage=non_parallel[0].id,
                        ),
                        estimated_impact="Save 30-50% of combined stage time",
                    ))
        
        return findings
```

#### MissingTimeoutRule

```python
class MissingTimeoutRule(AnalysisRule):
    """Detect missing timeout configuration."""
    
    id = "missing-timeout"
    name = "Add Timeout Configuration"
    description = "Jobs without timeout can run indefinitely"
    category = Category.BEST_PRACTICE
    severity = Severity.MEDIUM
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        findings = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                if job.timeout_minutes is None:
                    findings.append(self._create_finding(
                        message=f"Job '{job.name}' has no timeout configured",
                        suggestion="Add timeout to prevent zombie jobs (recommended: 30-60 min)",
                        location=Location(
                            file=pipeline.file_path,
                            stage=stage.id,
                            job=job.id,
                        ),
                        estimated_impact="Prevent stuck pipelines and wasted resources",
                    ))
        
        return findings
```

#### PinnedVersionsRule

```python
class PinnedVersionsRule(AnalysisRule):
    """Detect unpinned plugin/image versions."""
    
    id = "pinned-versions"
    name = "Pin Plugin Versions"
    description = "Unpinned versions can cause unexpected behavior"
    category = Category.SECURITY
    severity = Severity.HIGH
    
    UNSAFE_TAGS = ["latest", "main", "master", "develop"]
    
    def analyze(self, pipeline: Pipeline, dag: PipelineDAG) -> list[Finding]:
        findings = []
        
        for stage in pipeline.stages:
            for job in stage.jobs:
                for step in job.steps:
                    # Check image tag
                    if step.image:
                        if self._is_unpinned(step.image):
                            findings.append(self._create_finding(
                                message=f"Step '{step.name}' uses unpinned image: {step.image}",
                                suggestion="Pin to specific version tag or SHA",
                                location=Location(
                                    file=pipeline.file_path,
                                    stage=stage.id,
                                    step=step.id,
                                ),
                            ))
                    
                    # Check plugin version
                    if step.plugin and not step.plugin_version:
                        findings.append(self._create_finding(
                            message=f"Plugin '{step.plugin}' has no version specified",
                            suggestion="Specify explicit plugin version",
                            location=Location(
                                file=pipeline.file_path,
                                stage=stage.id,
                                step=step.id,
                            ),
                        ))
        
        return findings
    
    def _is_unpinned(self, image: str) -> bool:
        """Check if image reference is unpinned."""
        if ":" not in image:
            return True  # No tag = latest
        tag = image.split(":")[-1]
        return tag in self.UNSAFE_TAGS
```

### 7.3 Analysis Engine

```python
class AnalysisEngine:
    """Orchestrates pipeline analysis."""
    
    def __init__(self, rules: list[AnalysisRule] = None):
        self.rules = rules or self._get_default_rules()
    
    def _get_default_rules(self) -> list[AnalysisRule]:
        """Load all default rules."""
        return [
            CacheDependenciesRule(),
            CacheDockerLayersRule(),
            ParallelStagesRule(),
            ParallelStepsRule(),
            MissingTimeoutRule(),
            RedundantCloneRule(),
            PinnedVersionsRule(),
            ResourceSizingRule(),
        ]
    
    def analyze(
        self,
        pipeline: Pipeline,
        severity_threshold: Severity = Severity.LOW,
        enabled_rules: list[str] = None,
    ) -> AnalysisResult:
        """Run analysis on pipeline."""
        start_time = time.time()
        
        # Build DAG
        dag = PipelineDAG(pipeline)
        
        # Run rules
        all_findings = []
        for rule in self.rules:
            if enabled_rules and rule.id not in enabled_rules:
                continue
            if pipeline.platform not in rule.platforms:
                continue
            
            findings = rule.analyze(pipeline, dag)
            all_findings.extend(findings)
        
        # Filter by severity
        severity_order = list(Severity)
        threshold_idx = severity_order.index(severity_threshold)
        filtered_findings = [
            f for f in all_findings
            if severity_order.index(f.severity) <= threshold_idx
        ]
        
        # Calculate summary
        summary = self._calculate_summary(filtered_findings, dag)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisResult(
            pipeline=pipeline,
            findings=filtered_findings,
            summary=summary,
            dag_edges=list(dag.graph.edges()),
            execution_time_ms=execution_time,
            analyzer_version=__version__,
        )
    
    def _calculate_summary(
        self,
        findings: list[Finding],
        dag: PipelineDAG,
    ) -> AnalysisSummary:
        """Calculate analysis summary."""
        by_severity = {}
        for sev in Severity:
            by_severity[sev] = len([f for f in findings if f.severity == sev])
        
        by_category = {}
        for cat in Category:
            by_category[cat] = len([f for f in findings if f.category == cat])
        
        # Calculate score (100 - deductions)
        deductions = (
            by_severity.get(Severity.CRITICAL, 0) * 25 +
            by_severity.get(Severity.HIGH, 0) * 15 +
            by_severity.get(Severity.MEDIUM, 0) * 5 +
            by_severity.get(Severity.LOW, 0) * 2
        )
        score = max(0, 100 - deductions)
        
        return AnalysisSummary(
            score=score,
            total_findings=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            critical_path=dag.get_critical_path(),
        )
```

---

## 8. AI Integration

### 8.1 Claude Service

```python
import anthropic

class ClaudeAIService:
    """Claude AI integration for intelligent suggestions."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def explain_finding(
        self,
        finding: Finding,
        pipeline_context: str,
    ) -> str:
        """Generate human-readable explanation."""
        prompt = f"""You are a CI/CD optimization expert. Explain this issue clearly.

Platform: Harness
Issue: {finding.message}
Rule: {finding.rule_name}
Category: {finding.category.value}

Pipeline context:
```yaml
{pipeline_context}
```

Provide:
1. Why this is a problem (1-2 sentences)
2. The impact (time/cost/reliability)
3. How to fix it (specific steps for Harness)

Keep response under 150 words. Be direct and actionable."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        
        return response.content[0].text
    
    def suggest_fix(
        self,
        finding: Finding,
        pipeline_yaml: str,
    ) -> Fix:
        """Generate YAML fix for finding."""
        prompt = f"""You are a Harness CI/CD expert. Generate a fix for this issue.

Issue: {finding.message}
Suggestion: {finding.suggestion}
Location: stage={finding.location.stage}, step={finding.location.step}

Current pipeline:
```yaml
{pipeline_yaml}
```

Generate ONLY the corrected YAML snippet that fixes this issue.
Output valid Harness pipeline YAML, no explanations."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        
        return Fix(
            type="modify",
            description=f"AI-generated fix for {finding.rule_name}",
            replacement=response.content[0].text,
        )
    
    def generate_suggestions(
        self,
        pipeline: Pipeline,
        findings: list[Finding],
    ) -> list[str]:
        """Generate high-level optimization suggestions."""
        findings_summary = "\n".join([
            f"- [{f.severity.value}] {f.message}"
            for f in findings[:10]  # Limit to top 10
        ])
        
        prompt = f"""You are a CI/CD optimization expert reviewing a Harness pipeline.

Pipeline: {pipeline.name}
Stages: {[s.name for s in pipeline.stages]}
Issues found:
{findings_summary}

Provide 3-5 high-level optimization suggestions specific to this pipeline.
Focus on the most impactful improvements.
Each suggestion should be 1-2 sentences.
Format as a numbered list."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Parse numbered list
        text = response.content[0].text
        suggestions = []
        for line in text.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove number prefix
                suggestion = line.lstrip("0123456789.").strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions
```

---

## 9. CLI Implementation

### 9.1 CLI Structure

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="pipelineiq",
    help="AI-powered CI pipeline analyzer",
    no_args_is_help=True,
)
console = Console()

@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to pipeline file or directory"),
    format: str = typer.Option("terminal", "-f", "--format", help="Output format"),
    severity: str = typer.Option("low", "-s", "--severity", help="Minimum severity"),
    rules: str = typer.Option(None, "-r", "--rules", help="Comma-separated rules"),
    ai: bool = typer.Option(False, "--ai", help="Enable AI suggestions"),
    output: str = typer.Option(None, "-o", "--output", help="Output file"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Analyze CI pipeline for optimization opportunities."""
    # Implementation
    pass

@app.command()
def list_rules():
    """List all available analysis rules."""
    pass

@app.command()
def explain(
    rule_id: str = typer.Argument(..., help="Rule ID to explain"),
):
    """Get detailed explanation of a rule."""
    pass

@app.command()
def version():
    """Show version information."""
    console.print(f"PipelineIQ v{__version__}")

if __name__ == "__main__":
    app()
```

### 9.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no findings above threshold |
| 1 | Success, findings present |
| 2 | Error (invalid input, parse failure) |
| 3 | Configuration error |

---

## 10. Reporter Implementation

### 10.1 Terminal Reporter

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

class TerminalReporter:
    """Rich terminal output."""
    
    SEVERITY_COLORS = {
        Severity.CRITICAL: "red",
        Severity.HIGH: "orange1",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "blue",
        Severity.INFO: "dim",
    }
    
    SEVERITY_ICONS = {
        Severity.CRITICAL: "🔴",
        Severity.HIGH: "🟠",
        Severity.MEDIUM: "🟡",
        Severity.LOW: "🔵",
        Severity.INFO: "⚪",
    }
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def render(self, result: AnalysisResult) -> None:
        """Render analysis result to terminal."""
        self._render_header(result)
        self._render_summary(result.summary)
        self._render_findings(result.findings)
        if result.ai_suggestions:
            self._render_ai_suggestions(result.ai_suggestions)
        self._render_footer()
    
    def _render_header(self, result: AnalysisResult):
        self.console.print()
        self.console.print(Panel(
            f"[bold]Pipeline:[/bold] {result.pipeline.file_path}\n"
            f"[bold]Platform:[/bold] {result.pipeline.platform.value}",
            title="[bold blue]PipelineIQ Analysis Report[/bold blue]",
            border_style="blue",
        ))
    
    def _render_summary(self, summary: AnalysisSummary):
        # Score with color
        score_color = "green" if summary.score >= 80 else "yellow" if summary.score >= 60 else "red"
        
        summary_text = Text()
        summary_text.append(f"Score: ", style="bold")
        summary_text.append(f"{summary.score}/100", style=f"bold {score_color}")
        summary_text.append(f"  |  Findings: {summary.total_findings}")
        
        # Severity breakdown
        breakdown = []
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            count = summary.by_severity.get(sev, 0)
            if count > 0:
                icon = self.SEVERITY_ICONS[sev]
                breakdown.append(f"{icon} {count} {sev.value}")
        
        if breakdown:
            summary_text.append(f"\n{' | '.join(breakdown)}")
        
        self.console.print(Panel(summary_text, title="Summary", border_style="dim"))
    
    def _render_findings(self, findings: list[Finding]):
        if not findings:
            self.console.print("[green]✓ No issues found![/green]")
            return
        
        # Group by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            sev_findings = [f for f in findings if f.severity == severity]
            if not sev_findings:
                continue
            
            color = self.SEVERITY_COLORS[severity]
            icon = self.SEVERITY_ICONS[severity]
            
            self.console.print(f"\n[{color} bold]{icon} {severity.value.upper()}[/{color} bold]")
            
            for finding in sev_findings:
                self.console.print(f"  [{color}][{finding.rule_id}][/{color}]")
                self.console.print(f"  {finding.message}")
                self.console.print(f"  [dim]→ {finding.suggestion}[/dim]")
                if finding.estimated_impact:
                    self.console.print(f"  [dim italic]Impact: {finding.estimated_impact}[/dim italic]")
                self.console.print()
    
    def _render_ai_suggestions(self, suggestions: list[str]):
        self.console.print(Panel(
            "\n".join([f"• {s}" for s in suggestions]),
            title="[bold magenta]💡 AI Suggestions[/bold magenta]",
            border_style="magenta",
        ))
    
    def _render_footer(self):
        self.console.print("[dim]Run `pipelineiq explain <rule-id>` for detailed explanations[/dim]")
```

### 10.2 JSON Reporter

```python
import json

class JSONReporter:
    """JSON output for integrations."""
    
    def render(self, result: AnalysisResult) -> str:
        return result.model_dump_json(indent=2)
```

### 10.3 Markdown Reporter

```python
class MarkdownReporter:
    """Markdown output for documentation/PRs."""
    
    def render(self, result: AnalysisResult) -> str:
        lines = []
        
        lines.append("## 🔍 PipelineIQ Analysis\n")
        lines.append(f"**Pipeline:** `{result.pipeline.file_path}`\n")
        lines.append(f"**Score:** {result.summary.score}/100\n")
        
        # Findings table
        if result.findings:
            lines.append("\n### Findings\n")
            lines.append("| Severity | Rule | Message |")
            lines.append("|----------|------|---------|")
            for f in result.findings:
                lines.append(f"| {f.severity.value} | {f.rule_id} | {f.message} |")
        else:
            lines.append("\n✅ No issues found!\n")
        
        if result.ai_suggestions:
            lines.append("\n### AI Suggestions\n")
            for s in result.ai_suggestions:
                lines.append(f"- {s}")
        
        return "\n".join(lines)
```

---

## 11. Project Structure

```
pipelineiq/
├── src/
│   └── pipelineiq/
│       ├── __init__.py              # Package init, version
│       ├── __main__.py              # Entry point
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py              # Typer CLI
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── engine.py            # Analysis engine
│       │   ├── loader.py            # File loading
│       │   └── dag.py               # DAG builder
│       │
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py              # Parser interface
│       │   └── harness.py           # Harness parser
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── pipeline.py          # Pipeline IR
│       │   ├── finding.py           # Finding model
│       │   └── result.py            # Analysis result
│       │
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── base.py              # Rule interface
│       │   └── rules/
│       │       ├── __init__.py
│       │       ├── caching.py
│       │       ├── parallelization.py
│       │       ├── security.py
│       │       ├── best_practices.py
│       │       └── resource.py
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   └── claude.py            # Claude service
│       │
│       └── reporters/
│           ├── __init__.py
│           ├── terminal.py
│           ├── json_reporter.py
│           └── markdown.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Fixtures
│   ├── fixtures/                    # Sample pipelines
│   │   └── harness/
│   │       ├── simple.yaml
│   │       ├── complex.yaml
│   │       └── with_issues.yaml
│   ├── test_parsers/
│   ├── test_analyzers/
│   └── test_reporters/
│
├── examples/
│   └── harness/
│       ├── basic-ci.yaml
│       └── full-pipeline.yaml
│
├── pyproject.toml
├── README.md
├── LICENSE
├── PRODUCT_SPEC.md
├── TECH_SPEC.md
└── IMPLEMENTATION_PLAN.md
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| **Parsers** | Parse valid YAML, handle edge cases, detect platform |
| **Models** | Validation, serialization, defaults |
| **DAG** | Graph construction, critical path, parallelization |
| **Rules** | Detection accuracy, false positive rate |
| **Reporters** | Output format correctness |

### 12.2 Integration Tests

- End-to-end CLI tests
- Real Harness pipeline parsing
- AI service (mocked)

### 12.3 Test Fixtures

Sample Harness pipelines with known issues for testing rule accuracy.

---

## 13. Error Handling

### 13.1 Error Types

```python
class PipelineIQError(Exception):
    """Base exception for PipelineIQ."""
    pass

class ParseError(PipelineIQError):
    """Failed to parse pipeline file."""
    pass

class ValidationError(PipelineIQError):
    """Pipeline validation failed."""
    pass

class AIServiceError(PipelineIQError):
    """AI service error."""
    pass

class ConfigurationError(PipelineIQError):
    """Configuration error."""
    pass
```

### 13.2 Error Handling Strategy

- Parse errors: Show helpful message with line number
- Validation errors: Show what's missing/invalid
- AI errors: Graceful degradation (continue without AI)
- Config errors: Clear instructions to fix

---

## 14. Configuration

### 14.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | (required for AI) |
| `PIPELINEIQ_CONFIG` | Config file path | `pipelineiq.toml` |

### 14.2 Config File (pipelineiq.toml)

```toml
[analysis]
enabled_rules = ["*"]
disabled_rules = []
severity_threshold = "low"

[ai]
enabled = false
model = "claude-3-5-sonnet-20241022"

[output]
format = "terminal"
color = true
verbose = false
```

---

*End of Technical Specification*
