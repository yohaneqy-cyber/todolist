import threading
import time
from django.utils import timezone
from django.core.mail import send_mail
from .models import Task

def send_reminders_periodically():
    while True:
        due_tasks = Task.objects.filter(reminder_at__lte=timezone.now(), is_notified=False)
        for task in due_tasks:
            send_mail(
                subject="Reminder",
                message=f"Hi! This is a reminder for your task: {task.title}",
                from_email="avjj8130@gmail.com",
                recipient_list=[task.user.email],
                fail_silently=False,
            )
            task.is_notified = True
            task.save()
        time.sleep(60) 