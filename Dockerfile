# Multi-stage build for minimal image size
FROM python:3.13-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv
RUN uv sync --frozen --no-dev

# Final stage
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py ./
COPY src ./src

# Create non-root user
RUN useradd -m -u 1000 mcp && \
    chown -R mcp:mcp /app

USER mcp

# Set default environment variables (can be overridden)
ENV USER_AGENT="openstreetmap-mcp/0.1.0" \
    LOG_LEVEL="INFO" \
    NOMINATIM_URL="https://nominatim.openstreetmap.org" \
    OVERPASS_URL="https://overpass-api.de/api/interpreter" \
    OSRM_URL="https://router.project-osrm.org" \
    TRANSITLAND_URL="https://transit.land/api/v2"

# Health check (optional - useful for orchestrators)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the MCP server
ENTRYPOINT ["python", "main.py"]
