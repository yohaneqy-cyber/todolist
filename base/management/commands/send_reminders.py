from django.core.management.base import BaseCommand
from django.utils import timezone
from base.models import Task
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = "Send reminder emails for tasks"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        due_tasks = Task.objects.filter(reminder_at__lte=now, is_notified=False)

        if not due_tasks.exists():
            print("⏳ No tasks due for reminder.")
            return

        for task in due_tasks:
            try:
                send_mail(
                    subject=f"⏰ Reminder: {task.title}",
                    message=f"Don't forget your task: {task.title}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[task.user.email],
                    fail_silently=False
                )
                task.is_notified = True
                task.save()
                print("✅ Email sent to", task.user.email)
            except Exception as e:
                print(f"❌ Failed to send email to {task.user.email}: {e}")
    