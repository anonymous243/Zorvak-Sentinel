FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/core/src:/app/apps/api/src

# Create non-root user
RUN addgroup --system appuser && adduser --system --group appuser

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential needed for some packages like asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir asyncpg psycopg2-binary gunicorn

# Copy application code
COPY packages/ ./packages/
COPY apps/ ./apps/
COPY alembic.ini .
COPY migrations/ ./migrations/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Start Gunicorn with Uvicorn workers for production readiness
CMD ["gunicorn", "sentinel_api.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
