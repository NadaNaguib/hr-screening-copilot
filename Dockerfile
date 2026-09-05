# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md .
COPY src ./src
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .[dev]

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r copilot && useradd -r -g copilot copilot

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY scripts ./scripts
COPY eval ./eval
COPY alembic.ini ./alembic.ini

RUN chown -R copilot:copilot /app
USER copilot

EXPOSE 8000
