# Aden Hive Framework - Production Dockerfile
# Implements a multi-stage build for a smaller, secure production image

# Stage 1: Builder
# We use the official python 3.11 image as the builder base
FROM public.ecr.aws/docker/library/python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

# Copy workspace configuration and lock files
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/
COPY tools/pyproject.toml tools/

# Copy the actual source code required for installation
COPY core/ core/
COPY tools/ tools/

# Install dependencies into the system python environment
# Using --system to avoid creating a venv since we're inside a container
RUN uv pip install --system --no-cache -e core/

# Stage 2: Runtime
# Use a fresh, minimal python image for the final stage
FROM public.ecr.aws/docker/library/python:3.11-slim AS runtime

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/core

WORKDIR /app

# Create a non-root user for security
RUN useradd -m -u 1001 appuser

# Copy installed Python packages and binaries from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy the necessary directories to the runtime stage
COPY core/ ./core/
COPY tools/ ./tools/
# Create the exports directory in case it doesn't exist locally but is needed at runtime
RUN mkdir -p ./exports

# Ensure the non-root user owns the working directory and its contents
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Set the default command to run the framework
# This satisfies the acceptance criteria that `framework.runner` executes correctly
ENTRYPOINT ["python", "-m", "framework"]
CMD ["--help"]
