# PipelineIQ

**AI-powered CI pipeline analyzer** - identify inefficiencies and optimize your pipelines.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **8 Built-in Analysis Rules** - Detect caching issues, parallelization opportunities, security concerns, and more
- 🤖 **AI-Powered Suggestions** - Get intelligent recommendations using Claude AI
- 📊 **Multiple Output Formats** - Terminal, JSON, and Markdown reports
- 🎯 **Harness CI Support** - Built for Harness CI pipelines (more platforms coming)
- ⚡ **Fast Analysis** - Analyze pipelines in milliseconds

## Installation

```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -e .
```

## Quick Start

```bash
# Analyze a Harness CI pipeline
pipelineiq analyze pipeline.yaml --platform harness

# Get JSON output for CI integration
pipelineiq analyze pipeline.yaml --platform harness --format json

# Enable AI suggestions (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="your-api-key"
pipelineiq analyze pipeline.yaml --platform harness --ai

# List all available rules
pipelineiq list-rules

# Explain a specific rule
pipelineiq explain cache-dependencies
```

## CLI Commands

### `analyze`

Analyze a CI pipeline file for optimization opportunities.

```bash
pipelineiq analyze <path> --platform <platform> [options]
```

**Required:**
- `<path>` - Path to the pipeline file
- `--platform, -p` - CI platform (currently: `harness`)

**Options:**
- `--format, -f` - Output format: `terminal` (default), `json`, `markdown`
- `--severity, -s` - Minimum severity: `critical`, `high`, `medium`, `low`
- `--rules, -r` - Comma-separated rule IDs to run
- `--ai` - Enable AI-powered suggestions
- `--output, -o` - Write output to file
- `--verbose, -v` - Verbose output

**Exit Codes:**
- `0` - No findings
- `1` - Findings found
- `2` - Critical issues (score < 50)
- `3` - Parse error
- `4` - File not found
- `5` - Other error

### `list-rules`

List all available analysis rules.

```bash
pipelineiq list-rules
```

### `explain`

Explain a specific analysis rule.

```bash
pipelineiq explain <rule-id>
```

### `version`

Show version information.

```bash
pipelineiq version
```

## Analysis Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `cache-dependencies` | HIGH | Detects package manager installs without caching |
| `cache-docker-layers` | MEDIUM | Docker builds without layer caching |
| `parallel-stages` | HIGH | Independent stages that could run in parallel |
| `parallel-steps` | MEDIUM | Independent steps within a job |
| `missing-timeout` | MEDIUM | Jobs/stages without timeout configuration |
| `redundant-clone` | HIGH | Multiple git clone operations |
| `pinned-versions` | HIGH | Unpinned image/plugin versions |
| `resource-sizing` | LOW | Mis-sized compute resources |

## Example Output

```
╭─────────────────── Analysis ───────────────────╮
│ PipelineIQ Analysis Report                     │
│ Pipeline: My CI Pipeline                       │
│ Platform: harness                              │
│ File: pipeline.yaml                            │
╰────────────────────────────────────────────────╯
╭─────────────────── Summary ────────────────────╮
│        Score:  78/100                          │
│     Findings:  4                               │
│    Breakdown:  🟠 1 high | 🟡 2 medium | 🔵 1 low │
│ Est. Savings:  2-8 minutes per run             │
╰────────────────────────────────────────────────╯
```

## AI Integration

PipelineIQ integrates with Claude AI to provide intelligent suggestions:

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-api-key"

# Run with AI suggestions
pipelineiq analyze pipeline.yaml --platform harness --ai
```

AI features:
- **Overall Suggestions** - Prioritized recommendations based on findings
- **Finding Explanations** - Detailed explanations of why issues matter
- **Fix Generation** - Suggested YAML fixes (coming soon)

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pipelineiq

# Type checking
poetry run mypy src/

# Linting
poetry run ruff check src/
```

## Project Structure

```
pipelineiq/
├── src/pipelineiq/
│   ├── cli/          # Typer CLI application
│   ├── core/         # Analysis engine and DAG builder
│   ├── models/       # Pydantic data models
│   ├── parsers/      # Platform-specific parsers
│   ├── analyzers/    # Analysis rules
│   ├── reporters/    # Output formatters
│   └── ai/           # Claude AI integration
├── tests/            # Test suite
└── pyproject.toml    # Project configuration
```

## Roadmap

- [ ] GitHub Actions support
- [ ] GitLab CI support
- [ ] CircleCI support
- [ ] Web UI
- [ ] VS Code extension
- [ ] More analysis rules

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
