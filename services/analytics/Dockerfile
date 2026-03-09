# Analytics service
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# ── Production stage ────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos '' appuser

COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin/gunicorn /usr/local/bin/gunicorn

COPY services/shared/ /app/services/shared/
COPY services/auth/__init__.py /app/services/auth/__init__.py
COPY services/auth/models/ /app/services/auth/models/
COPY services/inventory/__init__.py /app/services/inventory/__init__.py
COPY services/inventory/models/ /app/services/inventory/models/
COPY services/sales/__init__.py /app/services/sales/__init__.py
COPY services/sales/models/ /app/services/sales/models/
COPY services/analytics/ /app/services/analytics/

USER appuser

EXPOSE 5004

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5004/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5004", "--workers", "4", "--timeout", "120", "services.analytics.wsgi:app"]
