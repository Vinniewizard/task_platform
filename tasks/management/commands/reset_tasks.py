from django.core.management.base import BaseCommand
from django.utils.timezone import now
from tasks.models import Task

class Command(BaseCommand):
    help = "Reset tasks status to pending"

    def handle(self, *args, **options):
        today = now().date()  # <-- Make sure this line is correctly indented!
        
        affected_tasks = Task.objects.filter(title__in=["Download", "Watch Ads"]).update(status="pending")

        
        self.stdout.write(self.style.SUCCESS(f"Successfully reset {affected_tasks} tasks to pending."))
