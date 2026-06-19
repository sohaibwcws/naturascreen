"""Celery application. Redis is the broker + result backend (compose `redis` service)."""

from __future__ import annotations

from celery import Celery

from ..config import get_settings

settings = get_settings()

celery_app = Celery(
    "naturascreen",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["naturascreen.tasks.pipeline"],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)
