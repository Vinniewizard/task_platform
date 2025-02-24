from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import UserProfile


class Command(BaseCommand):
    help = "Reset daily counters for all user profiles"

    def handle(self, *args, **options):
        today = timezone.localtime(timezone.now()).date()
        profiles = UserProfile.objects.all()
        for profile in profiles:
            profile.mines_today = 0
            profile.ads_watched_today = 0
            profile.last_mine_date = today
            profile.last_ad_date = today
            profile.save()
        self.stdout.write(self.style.SUCCESS("Daily counters reset for all users."))
