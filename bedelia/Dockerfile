# backend/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# System deps (psycopg, etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

# Copy Django project files (optimize layer caching)
COPY manage.py .
COPY config/ ./config/
COPY api/ ./api/

# Health endpoint baked into container image path (served by Django below)
# (You'll wire /health url to a simple view; see next snippet)
EXPOSE 8000

# Gunicorn (1 worker per CPU is okay; tune later)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--timeout", "60", \
     "--access-logfile", "-", "--error-logfile", "-"]