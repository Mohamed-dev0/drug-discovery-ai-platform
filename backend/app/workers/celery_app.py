from celery import Celery


celery_app = Celery(
    "drug_discovery_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
)