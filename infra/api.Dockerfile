# API and worker share this image; the compose file picks the command.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir "uv==0.11.*"
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/pyproject.toml
COPY worker/pyproject.toml worker/pyproject.toml
RUN mkdir -p api/leadforge worker/leadforge_worker \
 && touch api/leadforge/__init__.py worker/leadforge_worker/__init__.py \
 && uv sync --frozen --no-dev

COPY api api
COPY worker worker
COPY config config
RUN uv sync --frozen --no-dev

RUN useradd --create-home app && mkdir -p /app/var/storage && chown -R app /app/config /app/var
USER app
ENV PATH="/app/.venv/bin:$PATH" CONFIG_DIR=/app/config STORAGE_DIR=/app/var/storage
EXPOSE 8000
CMD ["uvicorn", "leadforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "api"]
