FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace \
    PATH=/workspace/backend/.venv/bin:$PATH \
    UV_PYTHON=python3.12

WORKDIR /workspace

COPY backend/pyproject.toml backend/uv.lock backend/README.md backend/
RUN uv sync --project backend --frozen --no-dev --no-install-project --extra ml

COPY backend backend
COPY scripts scripts

EXPOSE 8080
