from __future__ import annotations

from app.celery_factory import create_celery_app
from app.service_roles import AI_AGENT_SERVICE

celery_app = create_celery_app(AI_AGENT_SERVICE)
