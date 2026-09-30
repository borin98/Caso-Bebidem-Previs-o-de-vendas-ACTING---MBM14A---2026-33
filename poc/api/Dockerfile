# Imagem só da API FastAPI do POC. Contexto de build: raiz do repositório
# (precisa do pacote bebibem em src/, do pyproject/uv.lock da raiz e de data/raw).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/poc/api/.venv/bin:$PATH" \
    POC_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data/raw ./data/raw
COPY poc/api/pyproject.toml poc/api/uv.lock ./poc/api/
RUN uv sync --frozen --no-dev --project poc/api --no-install-project

COPY poc/api/src ./poc/api/src
RUN uv sync --frozen --no-dev --project poc/api

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown -R app:app /data
USER 10001:10001

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"]
CMD ["uvicorn", "poc_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
