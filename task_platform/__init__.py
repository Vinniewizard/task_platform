default_app_config = 'tasks.apps.TasksConfig'
from .celery import app as celery_app

__all__ = ('celery_app',)
