FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY app app
COPY ai_agent_services ai_agent_services
COPY scraping_service scraping_service
COPY scoring_service scoring_service
COPY umgl_ai umgl_ai
COPY scripts scripts
COPY alembic.ini alembic.ini

EXPOSE 8000
