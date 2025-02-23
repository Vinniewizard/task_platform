from django.core.management.base import BaseCommand
from django.utils.timezone import now
from tasks.models import Task
from tasks.models import UserProfile  # Correct import path


class Command(BaseCommand):
    help = "Resets specific tasks and user mining/ad-watching data at midnight"

    def handle(self, *args, **kwargs):
        # Reset only specific tasks (Download & Watch Ads)
        affected_tasks = Task.objects.filter(title__in=["Download", "Watch Ads"]).update(status="pending")
        
        # Reset user mining and ad-watching data
        today = now().date()
        updated_users = UserProfile.objects.update(mines_today=0, last_mine_date=today, ads_watched_today=0, last_ad_date=today)

        # Logging success messages
        self.stdout.write(self.style.SUCCESS(f"Successfully reset {affected_tasks} tasks to 'pending'"))
        self.stdout.write(self.style.SUCCESS(f"Successfully reset {updated_users} user profiles"))
