FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data /app/reports \
    && chown -R app:app /app
USER 10001:10001

ENTRYPOINT ["bebibem-forecast"]
