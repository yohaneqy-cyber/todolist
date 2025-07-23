from django.core.management.base import BaseCommand
from django.utils import timezone
from base.models import Task, RecurringTask
from datetime import timedelta
from dateutil.relativedelta import relativedelta

def generate_recurring_tasks_for_user(user):
    current_time = timezone.now()
    recurring_tasks = RecurringTask.objects.filter(user=user)

    for rt in recurring_tasks:
        next_date = rt.last_generated or rt.start_date

        while next_date <= current_time:
            if rt.end_date and next_date > rt.end_date:
                break

            exists = Task.objects.filter(recurring_task=rt, due_date=next_date).exists()
            if not exists:
                Task.objects.create(
                    user=user,
                    title=rt.title,
                    category=rt.category,
                    due_date=next_date,
                    recurring_task=rt
                )

            if rt.interval_type == 'daily':
                next_date += timedelta(days=rt.interval)
            elif rt.interval_type == 'weekly':
                next_date += timedelta(weeks=rt.interval)
            elif rt.interval_type == 'monthly':
                next_date += relativedelta(months=rt.interval)
            elif rt.interval_type == 'yearly':
                next_date += relativedelta(years=rt.interval)

        rt.last_generated = next_date
        rt.save()
