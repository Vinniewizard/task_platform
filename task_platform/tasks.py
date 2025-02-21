from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from .models import UserTask

@shared_task
def reset_daily_tasks():
    """Reset all user tasks at midnight so users can complete them again."""
    UserTask.objects.all().update(completed=False)
    return "Tasks reset successfully"
