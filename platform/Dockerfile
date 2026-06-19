FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/platform:/workspace

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY platform/requirements.txt platform/requirements.txt
RUN pip install -r platform/requirements.txt

COPY platform platform
COPY backend_core backend_core
COPY ai_agent_services ai_agent_services
COPY scraping_service scraping_service
COPY scoring_service scoring_service

EXPOSE 8000
