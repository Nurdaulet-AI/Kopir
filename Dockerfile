# syntax=docker/dockerfile:1

# --- 1. Веб-интерфейс: собираем статику ---
FROM node:24.11.0-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY web/ ./
RUN npm run build

# --- 2. Сервер: API + собранный интерфейс ---
FROM python:3.12.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Зависимости отдельным слоем: при правке кода они не переустанавливаются.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/kopir ./kopir
RUN uv sync --frozen --no-dev

COPY data ./data
COPY --from=web /web/dist ./web

ENV PATH="/app/.venv/bin:$PATH" \
    KOPIR_PROFILES=/app/data/profiles.json \
    KOPIR_WEB_DIR=/app/web

RUN useradd --create-home --uid 10001 kopir
USER kopir

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["uvicorn", "kopir.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
