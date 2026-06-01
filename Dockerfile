FROM python:3.12-slim AS base

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml / uv.lock change) ──────────
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Application layer ─────────────────────────────────────────────────────────
COPY . .
RUN uv sync --frozen --no-dev

# Collect static assets at build time so the image is self-contained
RUN uv run python manage.py collectstatic --noinput --settings=core.settings

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
