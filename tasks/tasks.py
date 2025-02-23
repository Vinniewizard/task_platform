from datetime import datetime
from tasks.models import Task  # Import your Task model

def reset_tasks():
    """
    Resets all user tasks daily at midnight.
    """
    Task.objects.all().update(status="pending")  # Reset status
    print(f"Tasks reset at {datetime.now()}")  # Log when it runs

