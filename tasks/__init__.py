from task_platform.celery import app as celery_app


default_app_config = 'tasks.apps.TasksConfig'


__all__ = ('celery_app',)
