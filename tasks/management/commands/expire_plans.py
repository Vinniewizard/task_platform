from django.core.management.base import BaseCommand
from django.utils.timezone import now
from users.models import UserProfile

class Command(BaseCommand):
    help = "Automatically expire plans when duration ends"

    def handle(self, *args, **kwargs):
        today = now().date()
        expired_profiles = UserProfile.objects.filter(plan_expiry__lte=today)

        for profile in expired_profiles:
            profile.plan_name = None
            profile.plan_expiry = None
            profile.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully expired {expired_profiles.count()} plans."))
