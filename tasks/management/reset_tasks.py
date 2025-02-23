from django.core.management.base import BaseCommand
from tasks.models import Task

class Command(BaseCommand):
    help = "Resets all tasks to 'pending' at midnight"

    def handle(self, *args, **kwargs):
        Task.objects.all().update(status="pending")
        self.stdout.write(self.style.SUCCESS("Successfully reset tasks to 'pending'"))

