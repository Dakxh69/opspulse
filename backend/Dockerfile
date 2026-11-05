# OpsPulse Backend — Dockerfile
# Multi-stage build: builder installs dependencies, final image runs the app.
#
# Why Python 3.12-slim?
# - Python 3.14 (host) lacks pre-built wheels for pydantic-core and asyncpg.
# - Python 3.12 has full wheel support for all project dependencies.
# - Virtualenv is installed to /opt/venv (outside /app) to avoid accidental shadowing.

# =============================================================================
# Stage 1: Builder — install dependencies
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install OS-level build dependencies (only in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv in /opt/venv
RUN python -m venv /opt/venv --upgrade-deps

# Install Python dependencies
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Final — minimal runtime image
# =============================================================================
FROM python:3.12-slim AS final

WORKDIR /app

# Runtime-only OS libs (libpq for psycopg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . /app/

# Activate venv by updating PATH
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run as non-root user for security
RUN useradd --create-home --shell /bin/bash opspulse && \
    chown -R opspulse:opspulse /app
USER opspulse

EXPOSE 8000

# Default command: run the FastAPI app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
