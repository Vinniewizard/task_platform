from celery import shared_task
from tasks.models import UserProfile
from .spinning import spin_wheel  # Ensure spinning.py exists in the tasks app


@shared_task
def reset_daily_tasks():
    UserProfile.objects.update(tasks_completed_today=False)
