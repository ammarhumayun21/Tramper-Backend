"""
Tramper Django config package.

Loads the Celery app on startup so that @shared_task decorators are registered
and the worker can autodiscover tasks from installed apps.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
