from django.core.management.base import BaseCommand
from django.utils.timezone import now
from tasks.models import UserProfile  # Import UserProfile if tasks are linked to users

class Command(BaseCommand):
    help = "Reset daily completed tasks for all users"

    def handle(self, *args, **options):
        # Reset daily task count for all users
        affected_users = UserProfile.objects.update(tasks_completed_today=0)

        self.stdout.write(self.style.SUCCESS(f"Successfully reset daily tasks for {affected_users} users."))
