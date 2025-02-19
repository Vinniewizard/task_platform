from django.core.management.base import BaseCommand
from tasks.models import UserProfile
import datetime

class Command(BaseCommand):
    help = 'Resets daily task counters for all users at midnight'

    def handle(self, *args, **kwargs):
        today = datetime.date.today()
        profiles = UserProfile.objects.all()
        for profile in profiles:
            # Reset the counters
            profile.mines_today = 0
            profile.ads_watched_today = 0
            # Optionally update the last task date to today (or set to None if you prefer)
            profile.last_mine_date = today
            profile.last_ad_date = today
            profile.save()
        self.stdout.write(self.style.SUCCESS("Successfully reset daily task counters for all users"))
