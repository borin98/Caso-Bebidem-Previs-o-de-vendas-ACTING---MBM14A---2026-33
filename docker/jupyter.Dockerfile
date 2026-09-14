FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra notebook --no-install-project

COPY src ./src
COPY notebooks/01_analise_demanda_bebibem.ipynb ./notebooks/01_analise_demanda_bebibem.ipynb
RUN uv sync --frozen --no-dev --extra notebook

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data /app/reports \
    && chown -R app:app /app
USER 10001:10001

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import pathlib, urllib.request; token = pathlib.Path('/app/.jupyter-token').read_text(); urllib.request.urlopen(f'http://127.0.0.1:8888/api/status?token={token}', timeout=3)"]

CMD ["sh", "-c", "TOKEN=\"${JUPYTER_TOKEN:-$(python -c 'import secrets; print(secrets.token_urlsafe(32))')}\"; printf '%s' \"$TOKEN\" > /app/.jupyter-token; exec jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --ServerApp.token=\"$TOKEN\" --ServerApp.allow_root=False --ServerApp.root_dir=/app"]
