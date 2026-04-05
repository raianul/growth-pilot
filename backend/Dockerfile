FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Railway sets $PORT dynamically; fallback to 8000 for local
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
