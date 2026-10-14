# Worker image: the API image plus Node (Next.js template builds) and Chromium (audits).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==0.11.*"
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/pyproject.toml
COPY worker/pyproject.toml worker/pyproject.toml
RUN mkdir -p api/leadforge worker/leadforge_worker \
 && touch api/leadforge/__init__.py worker/leadforge_worker/__init__.py \
 && uv sync --frozen --no-dev \
 && .venv/bin/playwright install --with-deps chromium

COPY templates/site/package.json templates/site/package-lock.json templates/site/
RUN cd templates/site && npm ci --no-audit --no-fund
COPY templates templates
COPY api api
COPY worker worker
COPY config config
RUN uv sync --frozen --no-dev

RUN useradd --create-home app && mkdir -p /app/var/storage \
 && chown -R app /app/config /app/var /app/templates/site
USER app
ENV PATH="/app/.venv/bin:$PATH" CONFIG_DIR=/app/config TEMPLATES_DIR=/app/templates \
    STORAGE_DIR=/app/var/storage
CMD ["python", "-m", "leadforge_worker.main"]
