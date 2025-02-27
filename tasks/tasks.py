from celery import shared_task
from tasks.models import UserProfile

@shared_task
def reset_daily_tasks():
    UserProfile.objects.update(tasks_completed_today=False)
