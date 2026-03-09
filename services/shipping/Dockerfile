# Shipping service
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
COPY services/shipping/ /app/services/shipping/

USER appuser

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5005/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5005", "--workers", "4", "--timeout", "120", "services.shipping.wsgi:app"]
