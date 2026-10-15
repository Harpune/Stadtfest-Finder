# Backend images (build context: backend/):
#   target `api` (default, image stadtfest-backend): REST API; the worker uses the same image
#                with `python -m stadtfest.bootstrap.worker`
#   target `mcp` (image stadtfest-mcp): MCP server, `python -m stadtfest.bootstrap.mcp` (R15)
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=app:app /app/migrations /app/migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 ENV=prod LOG_FORMAT=json
USER app

FROM runtime AS mcp
ENV MCP_HOST=0.0.0.0 MCP_PORT=8001
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health/live', timeout=2).status == 200 else 1)"
CMD ["python", "-m", "stadtfest.bootstrap.mcp"]

FROM runtime AS api
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health/live', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "stadtfest.bootstrap.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers"]
