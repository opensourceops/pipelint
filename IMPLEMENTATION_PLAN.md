# PipelineIQ - Implementation Plan

**Version:** 1.0.0  
**Last Updated:** February 28, 2026  
**Target Completion:** 2 weeks

---

## Overview

This document breaks down the implementation into detailed tasks with dependencies, estimates, and acceptance criteria.

---

## Phase Summary

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| **Phase 1** | Project Setup | Day 1 | None |
| **Phase 2** | Data Models | Day 1-2 | Phase 1 |
| **Phase 3** | Harness Parser | Day 2-3 | Phase 2 |
| **Phase 4** | DAG Builder | Day 3 | Phase 3 |
| **Phase 5** | Analysis Rules | Day 4-6 | Phase 4 |
| **Phase 6** | AI Integration | Day 7-8 | Phase 5 |
| **Phase 7** | CLI | Day 8-9 | Phase 5 |
| **Phase 8** | Reporters | Day 9-10 | Phase 7 |
| **Phase 9** | Testing & Polish | Day 11-12 | All |
| **Phase 10** | Documentation | Day 13-14 | All |

---

## Phase 1: Project Setup (Day 1)

### Task 1.1: Initialize Python Project

**Effort:** 30 minutes

**Actions:**
- [ ] Create `pyproject.toml` with Poetry
- [ ] Configure dependencies (typer, rich, pyyaml, pydantic, networkx, anthropic)
- [ ] Configure dev dependencies (pytest, ruff, mypy)
- [ ] Set up `src/pipelineiq/` package structure
- [ ] Create `__init__.py` with version

**Acceptance Criteria:**
- `poetry install` succeeds
- `poetry run python -c "import pipelineiq"` works

### Task 1.2: Configure Development Tools

**Effort:** 20 minutes

**Actions:**
- [ ] Configure ruff in `pyproject.toml`
- [ ] Configure mypy in `pyproject.toml`
- [ ] Create `.gitignore`
- [ ] Create `LICENSE` (MIT)

**Acceptance Criteria:**
- `poetry run ruff check .` runs
- `poetry run mypy src/` runs

### Task 1.3: Create Project Structure

**Effort:** 15 minutes

**Actions:**
- [ ] Create directory structure:
  ```
  src/pipelineiq/
  ├── cli/
  ├── core/
  ├── parsers/
  ├── models/
  ├── analyzers/rules/
  ├── ai/
  └── reporters/
  ```
- [ ] Add `__init__.py` to each directory

**Acceptance Criteria:**
- All directories exist with `__init__.py`

---

## Phase 2: Data Models (Day 1-2)

### Task 2.1: Pipeline IR Models

**Effort:** 1 hour

**File:** `src/pipelineiq/models/pipeline.py`

**Actions:**
- [ ] Define `Platform` enum
- [ ] Define `StepType` enum
- [ ] Define `ResourceSpec` model
- [ ] Define `RunnerConfig` model
- [ ] Define `CacheConfig` model
- [ ] Define `Step` model
- [ ] Define `Job` model
- [ ] Define `Stage` model
- [ ] Define `Trigger` model
- [ ] Define `Pipeline` model

**Acceptance Criteria:**
- All models have Pydantic validation
- Can create Pipeline from dict
- Can serialize to JSON

### Task 2.2: Finding Models

**Effort:** 45 minutes

**File:** `src/pipelineiq/models/finding.py`

**Actions:**
- [ ] Define `Severity` enum
- [ ] Define `Category` enum
- [ ] Define `Location` model
- [ ] Define `Fix` model
- [ ] Define `Finding` model

**Acceptance Criteria:**
- Finding can be created with all fields
- Severity comparison works

### Task 2.3: Result Models

**Effort:** 30 minutes

**File:** `src/pipelineiq/models/result.py`

**Actions:**
- [ ] Define `AnalysisSummary` model
- [ ] Define `AnalysisResult` model

**Acceptance Criteria:**
- Can calculate score from findings
- JSON serialization works

### Task 2.4: Models Package Init

**Effort:** 10 minutes

**File:** `src/pipelineiq/models/__init__.py`

**Actions:**
- [ ] Export all models

---

## Phase 3: Harness Parser (Day 2-3)

### Task 3.1: Parser Base Class

**Effort:** 30 minutes

**File:** `src/pipelineiq/parsers/base.py`

**Actions:**
- [ ] Define `PipelineParser` ABC
- [ ] Define `parse()` method signature
- [ ] Define `can_parse()` method signature
- [ ] Define `platform` and `file_patterns` attributes

**Acceptance Criteria:**
- ABC prevents direct instantiation

### Task 3.2: Harness Parser Implementation

**Effort:** 2 hours

**File:** `src/pipelineiq/parsers/harness.py`

**Actions:**
- [ ] Implement `HarnessParser` class
- [ ] Implement `can_parse()` - detect Harness structure
- [ ] Implement `parse()` - main entry point
- [ ] Implement `_parse_stages()` - handle stage array
- [ ] Implement `_parse_stage()` - single stage
- [ ] Implement `_parse_parallel_stages()` - parallel stage groups
- [ ] Implement `_parse_jobs()` - extract jobs from stage
- [ ] Implement `_parse_steps()` - handle step array
- [ ] Implement `_parse_step()` - single step
- [ ] Implement `_parse_step_group()` - step groups
- [ ] Implement `_parse_infrastructure()` - runner config
- [ ] Implement `_parse_variables()` - variables extraction

**Acceptance Criteria:**
- Parses simple Harness pipeline
- Parses complex pipeline with parallel stages
- Parses step groups
- Handles missing optional fields
- Returns valid Pipeline IR

### Task 3.3: Parser Tests

**Effort:** 1 hour

**Files:** 
- `tests/fixtures/harness/simple.yaml`
- `tests/fixtures/harness/complex.yaml`
- `tests/test_parsers/test_harness.py`

**Actions:**
- [ ] Create simple test fixture
- [ ] Create complex test fixture (parallel stages, step groups)
- [ ] Test basic parsing
- [ ] Test stage extraction
- [ ] Test step extraction
- [ ] Test infrastructure parsing
- [ ] Test error handling

**Acceptance Criteria:**
- All tests pass
- Coverage > 90% for parser

### Task 3.4: File Loader

**Effort:** 30 minutes

**File:** `src/pipelineiq/core/loader.py`

**Actions:**
- [ ] Implement `load_file()` - load single file
- [ ] Implement `get_parser(platform: Platform)` - return parser for specified platform

**Acceptance Criteria:**
- Loads file from path
- Returns correct parser for given platform

---

## Phase 4: DAG Builder (Day 3)

### Task 4.1: DAG Implementation

**Effort:** 1.5 hours

**File:** `src/pipelineiq/core/dag.py`

**Actions:**
- [ ] Implement `PipelineDAG` class
- [ ] Implement `_build_graph()` - construct NetworkX DiGraph
- [ ] Implement `_infer_sequential_dependencies()` - handle implicit deps
- [ ] Implement `get_critical_path()` - longest path
- [ ] Implement `get_independent_stages()` - root nodes
- [ ] Implement `get_parallelizable_groups()` - topological generations
- [ ] Implement `get_bottlenecks()` - high out-degree nodes
- [ ] Implement `get_stage_depth()` - distance from root

**Acceptance Criteria:**
- Builds valid DAG from Pipeline
- Handles parallel stages
- Handles explicit dependencies
- Handles implicit (sequential) dependencies
- Critical path calculation correct

### Task 4.2: DAG Tests

**Effort:** 45 minutes

**File:** `tests/test_core/test_dag.py`

**Actions:**
- [ ] Test linear pipeline DAG
- [ ] Test parallel stages DAG
- [ ] Test complex dependency DAG
- [ ] Test critical path
- [ ] Test parallelizable groups

---

## Phase 5: Analysis Rules (Day 4-6)

### Task 5.1: Rule Base Class

**Effort:** 30 minutes

**File:** `src/pipelineiq/analyzers/base.py`

**Actions:**
- [ ] Implement `AnalysisRule` ABC
- [ ] Define required attributes (id, name, description, category, severity)
- [ ] Define `analyze()` method signature
- [ ] Define `get_fix()` method (optional)
- [ ] Implement `_create_finding()` helper

**Acceptance Criteria:**
- Clear interface for implementing rules

### Task 5.2: Cache Dependencies Rule

**Effort:** 1 hour

**File:** `src/pipelineiq/analyzers/rules/caching.py`

**Actions:**
- [ ] Implement `CacheDependenciesRule`
- [ ] Define install patterns (npm, pip, maven, etc.)
- [ ] Implement `_find_install_steps()`
- [ ] Implement `_has_cache_step()`
- [ ] Implement `analyze()`
- [ ] Write tests

**Acceptance Criteria:**
- Detects npm/pip/maven install without cache
- No false positives when cache exists
- Accurate location tracking

### Task 5.3: Cache Docker Layers Rule

**Effort:** 45 minutes

**File:** `src/pipelineiq/analyzers/rules/caching.py`

**Actions:**
- [ ] Implement `CacheDockerLayersRule`
- [ ] Detect `docker build` commands
- [ ] Check for `--cache-from` or BuildKit
- [ ] Implement `analyze()`
- [ ] Write tests

### Task 5.4: Parallel Stages Rule

**Effort:** 1 hour

**File:** `src/pipelineiq/analyzers/rules/parallelization.py`

**Actions:**
- [ ] Implement `ParallelStagesRule`
- [ ] Use DAG to find independent stages
- [ ] Check if configured as parallel
- [ ] Implement `analyze()`
- [ ] Write tests

**Acceptance Criteria:**
- Identifies sequential independent stages
- Handles already-parallel stages correctly

### Task 5.5: Parallel Steps Rule

**Effort:** 45 minutes

**File:** `src/pipelineiq/analyzers/rules/parallelization.py`

**Actions:**
- [ ] Implement `ParallelStepsRule`
- [ ] Identify independent steps within job
- [ ] Suggest step groups
- [ ] Write tests

### Task 5.6: Missing Timeout Rule

**Effort:** 30 minutes

**File:** `src/pipelineiq/analyzers/rules/best_practices.py`

**Actions:**
- [ ] Implement `MissingTimeoutRule`
- [ ] Check job/stage timeout config
- [ ] Implement `analyze()`
- [ ] Write tests

### Task 5.7: Redundant Clone Rule

**Effort:** 45 minutes

**File:** `src/pipelineiq/analyzers/rules/redundancy.py`

**Actions:**
- [ ] Implement `RedundantCloneRule`
- [ ] Count clone/checkout steps
- [ ] Check for artifact passing
- [ ] Implement `analyze()`
- [ ] Write tests

### Task 5.8: Pinned Versions Rule

**Effort:** 45 minutes

**File:** `src/pipelineiq/analyzers/rules/security.py`

**Actions:**
- [ ] Implement `PinnedVersionsRule`
- [ ] Check image tags (latest, main, etc.)
- [ ] Check plugin versions
- [ ] Implement `analyze()`
- [ ] Write tests

### Task 5.9: Resource Sizing Rule

**Effort:** 45 minutes

**File:** `src/pipelineiq/analyzers/rules/resource.py`

**Actions:**
- [ ] Implement `ResourceSizingRule`
- [ ] Analyze step complexity vs resources
- [ ] Flag potential issues
- [ ] Write tests

### Task 5.10: Analysis Engine

**Effort:** 1 hour

**File:** `src/pipelineiq/core/engine.py`

**Actions:**
- [ ] Implement `AnalysisEngine` class
- [ ] Implement `_get_default_rules()`
- [ ] Implement `analyze()` - orchestrate analysis
- [ ] Implement `_calculate_summary()`
- [ ] Implement rule filtering (by id, severity)
- [ ] Implement platform filtering
- [ ] Write tests

**Acceptance Criteria:**
- Runs all enabled rules
- Filters by severity
- Calculates correct score
- Returns complete AnalysisResult

---

## Phase 6: AI Integration (Day 7-8)

### Task 6.1: Claude Service

**Effort:** 2 hours

**File:** `src/pipelineiq/ai/claude.py`

**Actions:**
- [ ] Implement `ClaudeAIService` class
- [ ] Handle API key from env
- [ ] Implement `explain_finding()`
- [ ] Implement `suggest_fix()`
- [ ] Implement `generate_suggestions()`
- [ ] Handle rate limits and errors
- [ ] Write tests (mocked)

**Acceptance Criteria:**
- API calls work with valid key
- Graceful error handling
- Reasonable prompts

### Task 6.2: AI Service Interface

**Effort:** 30 minutes

**File:** `src/pipelineiq/ai/__init__.py`

**Actions:**
- [ ] Create factory function for AI service
- [ ] Handle missing API key gracefully

---

## Phase 7: CLI Implementation (Day 8-9)

### Task 7.1: Main CLI Entry Point

**Effort:** 30 minutes

**File:** `src/pipelineiq/cli/main.py`

**Actions:**
- [ ] Create Typer app
- [ ] Add version callback
- [ ] Import commands

### Task 7.2: Analyze Command

**Effort:** 1.5 hours

**File:** `src/pipelineiq/cli/main.py`

**Actions:**
- [ ] Implement `analyze` command
- [ ] Add path argument (required)
- [ ] Add platform option (-p, --platform) - **required**, enum [harness]
- [ ] Add format option (-f)
- [ ] Add severity option (-s)
- [ ] Add rules option (-r)
- [ ] Add ai flag (--ai)
- [ ] Add output option (-o)
- [ ] Add verbose flag (-v)
- [ ] Wire up loader, parser, engine
- [ ] Handle errors with nice messages
- [ ] Implement exit codes

**Acceptance Criteria:**
- `pipelineiq analyze <file> --platform harness` works
- Error if --platform not provided
- Format options work
- Exit codes correct

### Task 7.3: List Rules Command

**Effort:** 30 minutes

**File:** `src/pipelineiq/cli/main.py`

**Actions:**
- [ ] Implement `list-rules` command
- [ ] Show rule id, name, category, severity
- [ ] Format as table

### Task 7.4: Explain Command

**Effort:** 30 minutes

**File:** `src/pipelineiq/cli/main.py`

**Actions:**
- [ ] Implement `explain` command
- [ ] Take rule-id argument
- [ ] Show detailed rule description

### Task 7.5: CLI Entry Point

**Effort:** 15 minutes

**File:** `src/pipelineiq/__main__.py`

**Actions:**
- [ ] Import and run CLI app

**Acceptance Criteria:**
- `python -m pipelineiq` works
- `poetry run pipelineiq` works

---

## Phase 8: Reporters (Day 9-10)

### Task 8.1: Terminal Reporter

**Effort:** 1.5 hours

**File:** `src/pipelineiq/reporters/terminal.py`

**Actions:**
- [ ] Implement `TerminalReporter` class
- [ ] Implement `render()` main method
- [ ] Implement `_render_header()`
- [ ] Implement `_render_summary()` with score gauge
- [ ] Implement `_render_findings()` grouped by severity
- [ ] Implement `_render_ai_suggestions()`
- [ ] Implement `_render_footer()`
- [ ] Use Rich for formatting

**Acceptance Criteria:**
- Beautiful terminal output
- Colors and icons work
- Findings grouped correctly

### Task 8.2: JSON Reporter

**Effort:** 30 minutes

**File:** `src/pipelineiq/reporters/json_reporter.py`

**Actions:**
- [ ] Implement `JSONReporter` class
- [ ] Use Pydantic's JSON serialization
- [ ] Format with indentation

**Acceptance Criteria:**
- Valid JSON output
- All fields included

### Task 8.3: Markdown Reporter

**Effort:** 45 minutes

**File:** `src/pipelineiq/reporters/markdown.py`

**Actions:**
- [ ] Implement `MarkdownReporter` class
- [ ] Render summary section
- [ ] Render findings table
- [ ] Render AI suggestions

**Acceptance Criteria:**
- Valid Markdown
- Tables render correctly

### Task 8.4: Reporter Factory

**Effort:** 15 minutes

**File:** `src/pipelineiq/reporters/__init__.py`

**Actions:**
- [ ] Create `get_reporter()` factory function
- [ ] Support format argument

---

## Phase 9: Testing & Polish (Day 11-12)

### Task 9.1: Integration Tests

**Effort:** 2 hours

**File:** `tests/test_integration.py`

**Actions:**
- [ ] Test end-to-end CLI flow
- [ ] Test with sample Harness pipelines
- [ ] Test different output formats
- [ ] Test error scenarios

### Task 9.2: Test Fixtures

**Effort:** 1 hour

**Files:** `tests/fixtures/harness/`

**Actions:**
- [ ] Create `simple.yaml` - basic pipeline
- [ ] Create `complex.yaml` - parallel stages, step groups
- [ ] Create `with_issues.yaml` - triggers all rules
- [ ] Create `clean.yaml` - passes all rules

### Task 9.3: Code Coverage

**Effort:** 30 minutes

**Actions:**
- [ ] Run coverage report
- [ ] Add missing tests
- [ ] Target: >80% coverage

### Task 9.4: Linting & Type Checking

**Effort:** 30 minutes

**Actions:**
- [ ] Fix all ruff issues
- [ ] Fix all mypy issues
- [ ] Ensure CI-ready

### Task 9.5: Error Handling Polish

**Effort:** 1 hour

**Actions:**
- [ ] Review all error messages
- [ ] Add helpful suggestions
- [ ] Handle edge cases

---

## Phase 10: Documentation (Day 13-14)

### Task 10.1: README

**Effort:** 2 hours

**File:** `README.md`

**Actions:**
- [ ] Write compelling intro
- [ ] Add installation instructions
- [ ] Add quick start guide
- [ ] Add CLI reference
- [ ] Add rule documentation
- [ ] Add configuration guide
- [ ] Add AI setup instructions
- [ ] Add contributing section
- [ ] Add badges (license, version)
- [ ] Add demo GIF/screenshot

### Task 10.2: Example Pipelines

**Effort:** 1 hour

**Files:** `examples/harness/`

**Actions:**
- [ ] Create `basic-ci.yaml` with comments
- [ ] Create `optimized-ci.yaml` showing best practices
- [ ] Create `before-after.md` showing improvements

### Task 10.3: Contributing Guide

**Effort:** 30 minutes

**File:** `CONTRIBUTING.md`

**Actions:**
- [ ] Setup instructions
- [ ] Coding standards
- [ ] Adding new rules guide
- [ ] Pull request process

### Task 10.4: Changelog

**Effort:** 15 minutes

**File:** `CHANGELOG.md`

**Actions:**
- [ ] Document v0.1.0 features

---

## Dependency Graph

```
Phase 1 (Setup)
     │
     ▼
Phase 2 (Models)
     │
     ▼
Phase 3 (Parser) ──────┐
     │                 │
     ▼                 │
Phase 4 (DAG) ◄────────┘
     │
     ▼
Phase 5 (Rules)
     │
     ├──────────────────┐
     ▼                  ▼
Phase 6 (AI)      Phase 7 (CLI)
     │                  │
     └────────┬─────────┘
              ▼
        Phase 8 (Reporters)
              │
              ▼
        Phase 9 (Testing)
              │
              ▼
        Phase 10 (Docs)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Harness YAML variations | Test with real-world examples, handle unknown fields gracefully |
| AI API issues | Make AI optional, graceful degradation |
| Complex step groups | Start simple, iterate based on testing |
| Performance on large pipelines | Profile early, optimize hot paths |

---

## Definition of Done

### MVP Complete When:

- [ ] `pipelineiq analyze <harness-pipeline.yaml>` works
- [ ] All 8 rules implemented and tested
- [ ] Terminal output is beautiful and helpful
- [ ] JSON and Markdown output work
- [ ] AI suggestions work (with API key)
- [ ] AI is optional (works without key)
- [ ] README is comprehensive
- [ ] At least 3 example pipelines
- [ ] Tests pass with >80% coverage
- [ ] No linting or type errors

---

## Daily Checklist

### Day 1
- [ ] Phase 1 complete (project setup)
- [ ] Phase 2 started (models)

### Day 2
- [ ] Phase 2 complete (models)
- [ ] Phase 3 started (parser)

### Day 3
- [ ] Phase 3 complete (parser)
- [ ] Phase 4 complete (DAG)

### Day 4-6
- [ ] Phase 5 complete (all 8 rules)

### Day 7-8
- [ ] Phase 6 complete (AI)
- [ ] Phase 7 started (CLI)

### Day 9-10
- [ ] Phase 7 complete (CLI)
- [ ] Phase 8 complete (reporters)

### Day 11-12
- [ ] Phase 9 complete (testing)

### Day 13-14
- [ ] Phase 10 complete (docs)
- [ ] MVP shipped! 🚀

---

*Ready to start implementation!*
