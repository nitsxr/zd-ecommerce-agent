# Multi-Agent E-commerce Assistant — API
# Stateless backend; session state in Redis.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (orchestrator, agents, memory, tools, observability, schemas, src)
COPY agents/ agents/
COPY memory/ memory/
COPY observability/ observability/
COPY orchestrator/ orchestrator/
COPY schemas/ schemas/
COPY tools/ tools/
COPY src/ src/

# REDIS_URL set by docker-compose (e.g. redis://redis:6379/0)
ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
