from __future__ import annotations

from app.celery_factory import create_celery_app
from app.service_roles import BACKEND_CORE_SERVICE

celery_app = create_celery_app(BACKEND_CORE_SERVICE)
