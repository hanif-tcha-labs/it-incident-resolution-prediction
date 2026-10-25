# Production Dockerfile for IT Incident Resolution Predictor & Simulator
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LOKY_MAX_CPU_COUNT=4

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install application runtime dependencies
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

# Create non-root system user and prepare writable directories
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

# Copy application and artifacts ONLY (raw dataset is never copied)
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser artifacts/ /app/artifacts/

USER appuser

EXPOSE 8000

# Healthcheck targeting FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start production server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
