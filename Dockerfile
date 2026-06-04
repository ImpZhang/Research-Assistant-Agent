FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

COPY backend ./backend
COPY scripts ./scripts
COPY docs ./docs

RUN mkdir -p /app/data/research /app/data/papers

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}"]
