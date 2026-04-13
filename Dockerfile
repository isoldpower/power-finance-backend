FROM python:3.12-slim

# Install system dependencies for psycopg (postgres driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY power_finance/ ./power_finance/

ENV PYTHONPATH=/app/power_finance
ENV DJANGO_SETTINGS_MODULE=power_finance.settings

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend