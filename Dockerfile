# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir poetry

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml poetry.lock* README.md ./

# Configure poetry to not create virtual env (we're in container)
RUN poetry config virtualenvs.create false

# Install dependencies only (not the package itself)
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy source code
COPY src/ ./src/

# Install the package
RUN poetry install --no-interaction --no-ansi --only main


# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/pipelineiq /usr/local/bin/pipelineiq

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pipelineiq
USER pipelineiq

# Set working directory for pipeline files
WORKDIR /workspace

# Default entrypoint
ENTRYPOINT ["pipelineiq"]

# Default command (show help)
CMD ["--help"]
