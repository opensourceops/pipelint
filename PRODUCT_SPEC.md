# PipelineIQ - Product Specification

**Version:** 1.0.0  
**Last Updated:** February 28, 2026  
**Author:** Abhay  
**Status:** Draft

---

## Executive Summary

PipelineIQ is an open-source, AI-powered CI pipeline analyzer that helps DevOps teams optimize their CI/CD pipelines. Starting with Harness CI support, it provides actionable recommendations to reduce build times, cut costs, and improve pipeline reliability.

**Core Value Proposition:** "Analyze your CI pipelines in seconds. Get AI-powered recommendations to make them faster, cheaper, and more reliable."

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Target Users](#2-target-users)
3. [Product Goals](#3-product-goals)
4. [Feature Specification](#4-feature-specification)
5. [Technical Architecture](#5-technical-architecture)
6. [Data Models](#6-data-models)
7. [Analysis Rules](#7-analysis-rules)
8. [AI Integration](#8-ai-integration)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Roadmap](#10-roadmap)
11. [Success Metrics](#11-success-metrics)

> **Note:** MVP is CLI-only. Web UI deferred to v2.0.

---

## 1. Problem Statement

### The Pain

CI/CD pipelines are critical infrastructure, yet most teams:
- Don't know where their pipelines are slow
- Waste cloud credits on inefficient configurations
- Lack expertise to optimize complex pipelines
- Have no automated way to enforce best practices

### The Cost

| Problem | Impact |
|---------|--------|
| Slow builds | Developers wait 2-4 hours/day |
| Wasted compute | 40% over-provisioning typical |
| Manual optimization | 20% of DevOps time |
| No visibility | Teams optimize blindly |

### The Opportunity

No tool today provides:
- Multi-CI platform analysis
- AI-powered optimization suggestions
- Automated fix generation
- Visual pipeline bottleneck analysis

---

## 2. Target Users

### Primary Personas

#### DevOps Engineer
- **Role:** Maintains CI/CD pipelines
- **Pain:** Spends hours manually optimizing pipelines
- **Need:** Automated recommendations, quick wins
- **Success:** Faster builds, less manual work

#### Platform Engineer
- **Role:** Manages CI/CD platform for org
- **Pain:** No visibility into pipeline efficiency across teams
- **Need:** Org-wide analysis, enforce standards
- **Success:** Reduced CI costs, consistent quality

#### Developer
- **Role:** Uses CI pipelines daily
- **Pain:** Slow feedback loops, waiting for builds
- **Need:** Faster builds, clear pipeline status
- **Success:** Ship code faster

### Secondary Personas

- **Engineering Manager:** Wants metrics on pipeline performance
- **FinOps Team:** Wants to reduce CI infrastructure costs
- **Security Team:** Wants to enforce pipeline security practices

---

## 3. Product Goals

### MVP Goals (v1.0)

| Goal | Metric | Target |
|------|--------|--------|
| **Analyze Harness pipelines** | Parse success rate | 100% valid YAMLs |
| **Identify optimizations** | Rules implemented | 8 core rules |
| **Provide AI suggestions** | AI response quality | 90% actionable |
| **Easy to use** | Time to first analysis | < 30 seconds |
| **Open source adoption** | GitHub stars (3 months) | 500+ |

### Long-term Goals (v2.0+)

- Support 4+ CI platforms
- 25+ analysis rules
- Auto-fix generation
- GitHub/GitLab integration
- Team collaboration features

---

## 4. Feature Specification

### 4.1 Pipeline Analysis Engine

#### Description
Core engine that parses, normalizes, and analyzes CI pipeline configurations.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1.1 | Parse Harness pipeline YAML files | P0 |
| F1.2 | Normalize to platform-agnostic IR | P0 |
| F1.3 | Build pipeline DAG (Directed Acyclic Graph) | P0 |
| F1.4 | Calculate critical path | P0 |
| F1.5 | Identify parallelization opportunities | P0 |
| F1.6 | Detect stage/step dependencies | P0 |

#### Acceptance Criteria
- [ ] Can parse all valid Harness pipeline YAML structures
- [ ] Handles nested stages and step groups
- [ ] Correctly identifies dependencies between stages
- [ ] Generates accurate DAG representation

---

### 4.2 Analysis Rules

#### Description
Rule engine that evaluates pipelines against best practices and identifies optimization opportunities.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F2.1 | Extensible rule interface | P0 |
| F2.2 | Rule categories (caching, parallel, security, etc.) | P0 |
| F2.3 | Severity levels (critical, high, medium, low) | P0 |
| F2.4 | Location tracking (file, line, stage, step) | P0 |
| F2.5 | Estimated impact calculation | P1 |
| F2.6 | Auto-fix generation per rule | P1 |

#### MVP Rules

| Rule ID | Category | Description | Severity |
|---------|----------|-------------|----------|
| `cache-dependencies` | Caching | Detect missing dependency caching | High |
| `cache-docker-layers` | Caching | Detect Docker builds without layer caching | High |
| `parallel-stages` | Parallelization | Find stages that can run in parallel | High |
| `parallel-steps` | Parallelization | Find steps that can run in parallel | Medium |
| `missing-timeout` | Best Practice | Jobs without timeout configured | Medium |
| `redundant-clone` | Redundancy | Multiple unnecessary git clones | Medium |
| `pinned-versions` | Security | Unpinned plugin/action versions | High |
| `resource-sizing` | Resource | Over/under-provisioned runners | Medium |

---

### 4.3 AI-Powered Suggestions

#### Description
Integration with Claude AI to provide intelligent, context-aware recommendations.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F3.1 | Connect to Anthropic Claude API | P0 |
| F3.2 | Generate human-readable explanations | P0 |
| F3.3 | Suggest optimized pipeline structure | P1 |
| F3.4 | Generate fix code (YAML patches) | P1 |
| F3.5 | Answer natural language questions | P2 |
| F3.6 | API key configuration (env var) | P0 |

#### AI Features

| Feature | Input | Output |
|---------|-------|--------|
| **Explain Finding** | Finding + context | Plain English explanation |
| **Suggest Fix** | Finding + pipeline | YAML code fix |
| **Optimize Pipeline** | Full pipeline | Rewritten pipeline |
| **Q&A** | User question | Contextual answer |

---

### 4.4 Command Line Interface

#### Description
Typer-based CLI for local pipeline analysis.

#### Commands

```bash
# Core commands
pipelineiq analyze <path> --platform harness   # Analyze pipeline file
pipelineiq explain <rule-id>                   # Explain a rule
pipelineiq list-rules                          # List all available rules

# Required
--platform, -p  [harness]           # CI platform (required)

# Options
--format, -f    [terminal|json|markdown]
--severity, -s  [critical|high|medium|low|all]
--rules, -r     [rule1,rule2,...]
--ai            Enable AI suggestions (requires API key)
--output, -o    Output file path
--verbose, -v   Verbose output
```

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F4.1 | `analyze` command with path and `--platform` flag | P0 |
| F4.2 | Format selection (terminal, json, markdown) | P0 |
| F4.3 | Severity filtering | P1 |
| F4.4 | Rule selection/exclusion | P1 |
| F4.5 | Exit codes for CI integration | P0 |

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no findings |
| 1 | Success, findings present |
| 2 | Error (invalid input, parse failure) |
| 3 | Configuration error |

---

### 4.5 Output Reporters

#### Description
Multiple output formats for different use cases.

#### Terminal Output
```
┌──────────────────────────────────────────────────────────────────┐
│  PipelineIQ Analysis Report                                      │
│  Pipeline: .harness/pipeline.yaml                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 SUMMARY                                                      │
│  Score: 65/100 ⚠️                                                │
│  Findings: 6 (🔴 1 critical, 🟠 2 high, 🟡 3 medium)             │
│  Estimated Savings: 3-5 minutes per run                         │
│                                                                  │
│  🔴 CRITICAL                                                     │
│  [security/pinned-versions]                                     │
│  Plugin 'docker' uses unpinned version                          │
│  → Pin to specific version for security                         │
│                                                                  │
│  🟠 HIGH                                                         │
│  [caching/cache-dependencies]                                   │
│  npm install without cache configured                           │
│  → Add cache step for node_modules                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### JSON Output
```json
{
  "version": "1.0.0",
  "pipeline": {
    "file": ".harness/pipeline.yaml",
    "name": "Build Pipeline",
    "platform": "harness"
  },
  "summary": {
    "score": 65,
    "findings_count": 6,
    "by_severity": {"critical": 1, "high": 2, "medium": 3}
  },
  "findings": [...],
  "dag": {...}
}
```

#### Markdown Output
For PR comments and documentation.

---

## 5. Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PipelineIQ                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                            CLI (Typer)                                  │
│                                 │                                        │
│                                 ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                        Core Engine                               │   │
│   │  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────────┐   │   │
│   │  │ Loader  │──▶│  Parser  │──▶│ Analyzer │──▶│  Reporter   │   │   │
│   │  └─────────┘   └──────────┘   └──────────┘   └─────────────┘   │   │
│   │                      │              │                           │   │
│   │                      ▼              ▼                           │   │
│   │               ┌──────────┐   ┌──────────┐                      │   │
│   │               │ Pipeline │   │    AI    │                      │   │
│   │               │    IR    │   │  Service │                      │   │
│   │               └──────────┘   └──────────┘                      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Core Engine** | Python 3.11+ | Rich ecosystem, fast development |
| **CLI** | Typer | Modern, auto-docs, type hints |
| **Terminal Output** | Rich | Beautiful terminal formatting |
| **AI** | Anthropic Claude | Best for code analysis |
| **Graph Library** | NetworkX | DAG algorithms |
| **Package Manager** | Poetry | Modern, fast |
| **Testing** | pytest | Standard, reliable |

### Project Structure

```
pipelineiq/
├── src/
│   └── pipelineiq/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       │
│       ├── cli/                 # Command line interface
│       │   ├── __init__.py
│       │   └── main.py          # Typer app
│       │
│       ├── core/                # Core engine
│       │   ├── __init__.py
│       │   ├── loader.py        # File loading
│       │   ├── engine.py        # Analysis orchestrator
│       │   └── config.py        # Configuration
│       │
│       ├── parsers/             # Platform parsers
│       │   ├── __init__.py
│       │   ├── base.py          # Parser interface
│       │   └── harness.py       # Harness parser
│       │
│       ├── models/              # Data models
│       │   ├── __init__.py
│       │   ├── pipeline.py      # Pipeline IR
│       │   ├── finding.py       # Analysis finding
│       │   └── dag.py           # DAG representation
│       │
│       ├── analyzers/           # Analysis rules
│       │   ├── __init__.py
│       │   ├── base.py          # Rule interface
│       │   └── rules/
│       │       ├── __init__.py
│       │       ├── caching.py
│       │       ├── parallelization.py
│       │       ├── security.py
│       │       ├── best_practices.py
│       │       └── resource.py
│       │
│       ├── ai/                  # AI integration
│       │   ├── __init__.py
│       │   ├── service.py       # AI service interface
│       │   ├── prompts.py       # Prompt templates
│       │   └── claude.py        # Claude implementation
│       │
│       └── reporters/           # Output formatters
│           ├── __init__.py
│           ├── terminal.py
│           ├── json_reporter.py
│           └── markdown.py
│
├── tests/
│   ├── fixtures/                # Sample pipelines
│   │   └── harness/
│   ├── test_parsers/
│   ├── test_analyzers/
│   └── test_reporters/
│
├── docs/                        # Documentation
│   ├── getting-started.md
│   └── rules.md
│
├── examples/                    # Example pipelines
│   └── harness/
│
├── pyproject.toml               # Python config
├── README.md
├── LICENSE                      # MIT
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## 6. Data Models

### 6.1 Pipeline Intermediate Representation (IR)

```python
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

class Platform(Enum):
    HARNESS = "harness"
    GITHUB = "github"
    GITLAB = "gitlab"
    CIRCLECI = "circleci"

@dataclass
class Pipeline:
    """Root pipeline representation"""
    id: str
    name: str
    platform: Platform
    file_path: str
    triggers: List['Trigger']
    stages: List['Stage']
    properties: Dict[str, Any]
    variables: Dict[str, str]
    
@dataclass
class Stage:
    """Pipeline stage"""
    id: str
    name: str
    type: str  # CI, CD, Custom, etc.
    dependencies: List[str]  # Stage IDs
    parallel: bool
    condition: Optional[str]
    jobs: List['Job']
    variables: Dict[str, str]
    
@dataclass
class Job:
    """Execution job within a stage"""
    id: str
    name: str
    runner: 'RunnerConfig'
    steps: List['Step']
    services: List['Service']
    timeout_minutes: Optional[int]
    retry: Optional['RetryConfig']
    cache: Optional['CacheConfig']
    artifacts: Optional['ArtifactConfig']

@dataclass
class Step:
    """Individual execution step"""
    id: str
    name: str
    type: 'StepType'
    command: Optional[str]
    plugin: Optional[str]
    plugin_version: Optional[str]
    inputs: Dict[str, Any]
    environment: Dict[str, str]
    condition: Optional[str]
    timeout_minutes: Optional[int]
    continue_on_error: bool = False

class StepType(Enum):
    RUN = "run"
    PLUGIN = "plugin"
    ACTION = "action"
    BACKGROUND = "background"
    GROUP = "group"

@dataclass
class RunnerConfig:
    """Execution environment configuration"""
    type: str  # kubernetes, cloud, vm
    os: str
    image: Optional[str]
    resources: Optional['ResourceSpec']
    
@dataclass
class ResourceSpec:
    """Compute resource specification"""
    cpu: Optional[str]
    memory: Optional[str]
    
@dataclass
class CacheConfig:
    """Caching configuration"""
    key: str
    paths: List[str]
    restore_keys: List[str]
    
@dataclass
class Trigger:
    """Pipeline trigger configuration"""
    type: str  # push, pull_request, schedule, manual
    branches: List[str]
    paths: List[str]
    paths_ignore: List[str]
```

### 6.2 Analysis Finding

```python
@dataclass
class Finding:
    """Analysis finding/issue"""
    id: str
    rule_id: str
    rule_name: str
    severity: 'Severity'
    category: 'Category'
    message: str
    suggestion: str
    location: 'Location'
    estimated_impact: Optional[str]
    fix: Optional['Fix']
    references: List[str]
    ai_explanation: Optional[str]

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Category(Enum):
    CACHING = "caching"
    PARALLELIZATION = "parallelization"
    SECURITY = "security"
    BEST_PRACTICE = "best-practice"
    RESOURCE = "resource"
    REDUNDANCY = "redundancy"
    RELIABILITY = "reliability"

@dataclass
class Location:
    """Finding location in source"""
    file: str
    line: Optional[int]
    stage: Optional[str]
    job: Optional[str]
    step: Optional[str]
    
@dataclass
class Fix:
    """Suggested fix"""
    type: str  # add, remove, modify
    description: str
    original: Optional[str]
    replacement: str
    line_start: Optional[int]
    line_end: Optional[int]
```

### 6.3 Analysis Result

```python
@dataclass
class AnalysisResult:
    """Complete analysis result"""
    pipeline: Pipeline
    findings: List[Finding]
    summary: 'AnalysisSummary'
    dag: 'PipelineDAG'
    ai_suggestions: List[str]
    execution_time_ms: int
    analyzer_version: str

@dataclass
class AnalysisSummary:
    """Analysis summary statistics"""
    score: int  # 0-100
    total_findings: int
    by_severity: Dict[Severity, int]
    by_category: Dict[Category, int]
    estimated_time_savings: Optional[str]
    estimated_cost_savings: Optional[str]
    critical_path: List[str]
```

---

## 7. Analysis Rules

### 7.1 Rule Interface

```python
from abc import ABC, abstractmethod

class AnalysisRule(ABC):
    """Base class for all analysis rules"""
    
    id: str                    # Unique identifier
    name: str                  # Human-readable name
    description: str           # What this rule checks
    category: Category         # Rule category
    severity: Severity         # Default severity
    platforms: List[Platform]  # Applicable platforms
    enabled: bool = True       # Default enabled state
    
    @abstractmethod
    def analyze(
        self, 
        pipeline: Pipeline, 
        dag: PipelineDAG
    ) -> List[Finding]:
        """Execute rule analysis"""
        pass
    
    def get_fix(self, finding: Finding) -> Optional[Fix]:
        """Generate fix for finding (optional)"""
        return None
```

### 7.2 MVP Rules Specification

#### Rule: `cache-dependencies`

| Property | Value |
|----------|-------|
| **ID** | `cache-dependencies` |
| **Category** | Caching |
| **Severity** | High |
| **Description** | Detects dependency installation without caching |

**Detection Logic:**
1. Find steps with `npm install`, `pip install`, `mvn install`, etc.
2. Check if corresponding cache step exists
3. Report if no cache found

**Patterns to Detect:**
- `npm install` / `npm ci` / `yarn install` / `pnpm install`
- `pip install` / `poetry install`
- `mvn install` / `gradle build`
- `go mod download`
- `bundle install`

---

#### Rule: `cache-docker-layers`

| Property | Value |
|----------|-------|
| **ID** | `cache-docker-layers` |
| **Category** | Caching |
| **Severity** | High |
| **Description** | Docker builds without layer caching |

**Detection Logic:**
1. Find `docker build` commands
2. Check for `--cache-from` or BuildKit cache mounts
3. Report if no caching mechanism found

---

#### Rule: `parallel-stages`

| Property | Value |
|----------|-------|
| **ID** | `parallel-stages` |
| **Category** | Parallelization |
| **Severity** | High |
| **Description** | Independent stages that run sequentially |

**Detection Logic:**
1. Build dependency DAG
2. Find stages with no dependencies (roots)
3. Check if they're configured to run in parallel
4. Report sequential independent stages

---

#### Rule: `parallel-steps`

| Property | Value |
|----------|-------|
| **ID** | `parallel-steps` |
| **Category** | Parallelization |
| **Severity** | Medium |
| **Description** | Independent steps within a stage |

**Detection Logic:**
1. Analyze steps within each job
2. Identify steps with no data dependencies
3. Suggest step groups for parallel execution

---

#### Rule: `missing-timeout`

| Property | Value |
|----------|-------|
| **ID** | `missing-timeout` |
| **Category** | Best Practice |
| **Severity** | Medium |
| **Description** | Jobs/stages without timeout configuration |

**Detection Logic:**
1. Check each stage/job for timeout configuration
2. Report missing timeouts
3. Suggest reasonable defaults

---

#### Rule: `redundant-clone`

| Property | Value |
|----------|-------|
| **ID** | `redundant-clone` |
| **Category** | Redundancy |
| **Severity** | Medium |
| **Description** | Multiple git clone operations |

**Detection Logic:**
1. Count clone/checkout steps across jobs
2. Check if artifacts are passed between jobs
3. Report redundant clones

---

#### Rule: `pinned-versions`

| Property | Value |
|----------|-------|
| **ID** | `pinned-versions` |
| **Category** | Security |
| **Severity** | High |
| **Description** | Unpinned plugin/image versions |

**Detection Logic:**
1. Find plugin references
2. Check version specification
3. Report `latest`, missing, or branch-based versions

---

#### Rule: `resource-sizing`

| Property | Value |
|----------|-------|
| **ID** | `resource-sizing` |
| **Category** | Resource |
| **Severity** | Medium |
| **Description** | Potentially mis-sized compute resources |

**Detection Logic:**
1. Analyze step complexity
2. Compare to resource allocation
3. Flag potential over/under-provisioning

---

## 8. AI Integration

### 8.1 Claude Integration

```python
class ClaudeAIService:
    """Anthropic Claude integration for AI-powered suggestions"""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def explain_finding(
        self, 
        finding: Finding, 
        context: str
    ) -> str:
        """Generate human-readable explanation"""
        pass
    
    async def suggest_fix(
        self, 
        finding: Finding, 
        pipeline_yaml: str
    ) -> Fix:
        """Generate code fix for finding"""
        pass
    
    async def optimize_pipeline(
        self, 
        pipeline_yaml: str,
        findings: List[Finding]
    ) -> str:
        """Generate fully optimized pipeline"""
        pass
    
    async def answer_question(
        self, 
        question: str, 
        pipeline_context: str
    ) -> str:
        """Answer natural language question about pipeline"""
        pass
```

### 8.2 Prompt Templates

```python
EXPLAIN_FINDING_PROMPT = """
You are a CI/CD optimization expert. Explain this pipeline issue clearly.

Platform: {platform}
Issue: {finding.message}
Rule: {finding.rule_name}
Location: {finding.location}

Pipeline context:
```yaml
{context}
```

Provide:
1. Why this is a problem (1-2 sentences)
2. The impact (time/cost/reliability)  
3. How to fix it (specific steps)

Keep response under 150 words. Be direct and actionable.
"""

GENERATE_FIX_PROMPT = """
You are a CI/CD expert. Generate a fix for this pipeline issue.

Platform: {platform}
Issue: {finding.message}
Location: {finding.location}

Current configuration:
```yaml
{current_yaml}
```

Generate the corrected YAML. Only output valid YAML, no explanations.
"""

OPTIMIZE_PIPELINE_PROMPT = """
You are a CI/CD optimization expert. Optimize this pipeline.

Platform: {platform}
Current pipeline:
```yaml
{pipeline_yaml}
```

Issues found:
{findings_summary}

Generate an optimized version that:
1. Addresses all issues
2. Follows {platform} best practices
3. Includes comments explaining changes

Output only valid YAML.
"""
```

### 8.3 Configuration

```python
# Environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Config file (pipelineiq.toml)
[ai]
enabled = true
provider = "anthropic"
model = "claude-3-5-sonnet-20241022"
max_tokens = 4096
temperature = 0.3
```

---

## 9. User Interface

### 9.1 Landing Page

**Hero Section:**
- Headline: "Optimize Your CI Pipelines with AI"
- Subheadline: "Get actionable recommendations in seconds"
- CTA: "Analyze Now" → /analyze
- Demo animation showing analysis

**Features Section:**
- Multi-platform support
- AI-powered suggestions
- Visual DAG analysis
- Open source

**How It Works:**
1. Paste your pipeline YAML
2. Get instant analysis
3. Apply recommendations

### 9.2 Analyze Page

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  PipelineIQ                                    [Docs] [GitHub] │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Paste your pipeline YAML                      [Analyze] │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  pipeline:                                         │  │  │
│  │  │    name: Build                                     │  │  │
│  │  │    stages:                                         │  │  │
│  │  │      - stage:                                      │  │  │
│  │  │          name: Build                               │  │  │
│  │  │          ...                                       │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │  Platform: [Auto-detect ▼]                               │  │
│  │  □ Enable AI suggestions (requires API key)              │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Or: [Load example] [Connect GitHub] [Connect GitLab]          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 9.3 Results Page

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  PipelineIQ                                    [Docs] [GitHub] │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐ │
│  │  Score: 65/100 ⚠️   │  │  Pipeline DAG                    │ │
│  │                     │  │  ┌─────┐     ┌─────┐             │ │
│  │  Findings: 6        │  │  │Build│────▶│Test │             │ │
│  │  🔴 1 critical      │  │  └─────┘     └──┬──┘             │ │
│  │  🟠 2 high          │  │                 │                │ │
│  │  🟡 3 medium        │  │            ┌────┴────┐           │ │
│  │                     │  │            ▼         ▼           │ │
│  │  Est. Savings:      │  │       ┌───────┐ ┌───────┐        │ │
│  │  3-5 min/run        │  │       │Deploy │ │ Docs  │        │ │
│  │                     │  │       └───────┘ └───────┘        │ │
│  └─────────────────────┘  └──────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Findings                    [All ▼] [Category ▼] [↓]    │  │
│  │  ────────────────────────────────────────────────────────│  │
│  │  🔴 CRITICAL                                             │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ [security/pinned-versions]                         │  │  │
│  │  │ Plugin 'docker' uses unpinned version              │  │  │
│  │  │ Location: stages[0].steps[2]                       │  │  │
│  │  │ → Pin to specific version for security             │  │  │
│  │  │                                    [View Fix] [AI] │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │  🟠 HIGH                                                 │  │
│  │  ...                                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  [Export JSON] [Export Markdown] [Copy optimized pipeline]     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 10. API Specification

### 10.1 REST API (for Web UI)

#### POST /api/analyze

**Request:**
```json
{
  "yaml": "pipeline:\n  name: Build\n  ...",
  "platform": "harness",
  "options": {
    "ai_enabled": true,
    "rules": ["all"],
    "severity_threshold": "medium"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "summary": {
      "score": 65,
      "findings_count": 6,
      "by_severity": {...}
    },
    "findings": [...],
    "dag": {...},
    "ai_suggestions": [...]
  }
}
```

#### POST /api/explain

**Request:**
```json
{
  "finding_id": "cache-dependencies-1",
  "pipeline_context": "..."
}
```

**Response:**
```json
{
  "explanation": "..."
}
```

#### POST /api/fix

**Request:**
```json
{
  "finding_id": "cache-dependencies-1",
  "pipeline_yaml": "..."
}
```

**Response:**
```json
{
  "fix": {
    "type": "add",
    "description": "...",
    "replacement": "..."
  }
}
```

---

## 11. Non-Functional Requirements

### 11.1 Performance

| Metric | Target |
|--------|--------|
| Analysis time (typical pipeline) | < 2 seconds |
| Analysis time (large pipeline) | < 10 seconds |
| AI response time | < 5 seconds |
| Web UI load time | < 3 seconds |
| CLI startup time | < 500ms |

### 11.2 Reliability

| Metric | Target |
|--------|--------|
| Parser accuracy | 100% valid YAMLs |
| Rule accuracy | > 95% true positives |
| AI availability | Graceful degradation |
| Uptime (web) | 99.9% |

### 11.3 Security

- No pipeline data stored on server
- API keys stored in environment variables only
- HTTPS for all web traffic
- No telemetry without opt-in

### 11.4 Compatibility

| Platform | Version |
|----------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Browsers | Chrome, Firefox, Safari, Edge (latest 2 versions) |

---

## 12. Roadmap

### Phase 1: MVP (Weeks 1-2)
- [x] Project setup
- [ ] Harness parser
- [ ] Pipeline IR
- [ ] 8 analysis rules
- [ ] Claude AI integration
- [ ] CLI with analyze command
- [ ] Terminal reporter

### Phase 2: Web UI (Weeks 3-4)
- [ ] Next.js app setup
- [ ] Landing page
- [ ] Analyze page
- [ ] Results page
- [ ] DAG visualization
- [ ] Deploy to Vercel

### Phase 3: Polish & Launch (Week 5)
- [ ] README with demos
- [ ] Documentation
- [ ] Example pipelines
- [ ] GitHub release
- [ ] LinkedIn posts
- [ ] Hacker News / Reddit

### Future (v2.0+)
- [ ] GitHub Actions parser
- [ ] GitLab CI parser
- [ ] CircleCI parser
- [ ] More analysis rules
- [ ] PR integration (GitHub Action)
- [ ] Team features
- [ ] Pipeline history/trends

---

## 13. Success Metrics

### Launch Metrics (First 30 days)

| Metric | Target |
|--------|--------|
| GitHub stars | 200+ |
| Unique users (web) | 500+ |
| CLI downloads | 100+ |
| LinkedIn post engagement | 10K+ impressions |

### Growth Metrics (First 90 days)

| Metric | Target |
|--------|--------|
| GitHub stars | 500+ |
| Contributors | 5+ |
| Pipelines analyzed | 5,000+ |
| Feature requests | 20+ |

### Quality Metrics

| Metric | Target |
|--------|--------|
| GitHub issues resolved | 80%+ within 1 week |
| User satisfaction | 4.5/5 rating |
| Rule accuracy | > 95% true positives |

---

## Appendix A: Harness Pipeline YAML Structure

```yaml
pipeline:
  name: Build Pipeline
  identifier: build_pipeline
  projectIdentifier: my_project
  orgIdentifier: my_org
  tags: {}
  properties:
    ci:
      codebase:
        connectorRef: github_connector
        repoName: my-repo
        build: <+input>
  stages:
    - stage:
        name: Build
        identifier: Build
        description: ""
        type: CI
        spec:
          cloneCodebase: true
          infrastructure:
            type: KubernetesDirect
            spec:
              connectorRef: k8s_connector
              namespace: harness-builds
          execution:
            steps:
              - step:
                  type: Run
                  name: Install Dependencies
                  identifier: install_deps
                  spec:
                    connectorRef: docker_hub
                    image: node:18
                    shell: Sh
                    command: npm ci
              - step:
                  type: Run
                  name: Build
                  identifier: build
                  spec:
                    connectorRef: docker_hub
                    image: node:18
                    shell: Sh
                    command: npm run build
              - step:
                  type: Run
                  name: Test
                  identifier: test
                  spec:
                    connectorRef: docker_hub
                    image: node:18
                    shell: Sh
                    command: npm test
    - stage:
        name: Deploy
        identifier: Deploy
        type: Deployment
        spec:
          deploymentType: Kubernetes
          # ... deployment config
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **IR** | Intermediate Representation - normalized pipeline model |
| **DAG** | Directed Acyclic Graph - pipeline dependency graph |
| **Finding** | An issue or optimization opportunity identified |
| **Rule** | Analysis logic that detects specific patterns |
| **Fix** | Suggested code change to address a finding |

---

*End of Product Specification*
