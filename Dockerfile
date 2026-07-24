FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

RUN groupadd --system privaterag \
    && useradd --system --gid privaterag --create-home privaterag

COPY pyproject.toml README.md ./
COPY app ./app
COPY frontend ./frontend
COPY migrations ./migrations
COPY alembic.ini ./
COPY .streamlit ./.streamlit

RUN pip install --upgrade pip \
    && pip install .

RUN mkdir -p /app/data/uploads /app/data/vector_store /app/data/database \
    && chown -R privaterag:privaterag /app

USER privaterag

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
