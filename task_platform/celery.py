import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_platform.settings')

app = Celery('task_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'reset-daily-counters-at-midnight': {
        'task': 'tasks.tasks.reset_daily_counters',
        'schedule': crontab(hour=0, minute=0),
    },
}
