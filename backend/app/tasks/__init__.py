from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "growthpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])

# Ensure all task modules are imported for registration
import app.tasks.scraping  # noqa: F401, E402
import app.tasks.analysis  # noqa: F401, E402
import app.tasks.content  # noqa: F401, E402
import app.tasks.notification  # noqa: F401, E402
import app.tasks.scheduler  # noqa: F401, E402
import app.tasks.free_audit  # noqa: F401, E402
