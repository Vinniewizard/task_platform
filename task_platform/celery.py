from celery.schedules import crontab
from celery import Celery

app = Celery('task_platform')

app.conf.beat_schedule = {
    'reset-daily-counters-at-midnight': {
        'task': 'tasks.tasks.reset_daily_counters',
        'schedule': crontab(hour=0, minute=0),  # Runs at 00:00 AM every day
    },
}

app.conf.timezone = 'Africa/Nairobi'  # Set your timezone if needed
