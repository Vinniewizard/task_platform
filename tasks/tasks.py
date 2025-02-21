# tasks/tasks.py
from celery import shared_tasks
from django.utils import timezone
from .models import UserProfile

@shared_tasks
def reset_daily_counters():
    today = timezone.localtime(timezone.now()).date()
    profiles = UserProfile.objects.all()
    for profile in profiles:
        profile.mines_today = 0
        profile.ads_watched_today = 0
        profile.last_mine_date = today
        profile.last_ad_date = today
        profile.save()
