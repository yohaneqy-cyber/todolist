from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('You must have an email')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get("is_superuser") is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, unique=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar_base_name = models.CharField(max_length=255, blank=True, null=True)
    friends = models.ManyToManyField("self", blank=True, symmetrical=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name
    
class Task(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    is_notified = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    recurring_task = models.ForeignKey('RecurringTask', null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,related_name='subtasks')
    updated_at = models.DateTimeField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to='tasks_files/', null=True, blank=True)
    share_with = models.ManyToManyField(User, related_name='shared_tasks', blank=True)
    PRIORITY_CHOICES = [
        (1,'low'),
        (2,'medium'),
        (3, 'high')
    ]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    def progress_percent(self, user=None):
        subtasks = self.subtasks.filter(user=user) if user else self.subtasks.all()
        total = subtasks.count()
        if total == 0:
            return 100 if self.completed else 0
        completed_count = subtasks.filter(completed=True).count()
        return int((completed_count / total) * 100)

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
class RecurringTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    interval_type = models.CharField(max_length=10, choices=[
        ('daily', 'daily'),
        ('weekly', 'weekly'),
        ('monthly', 'monthly'),
        ('yearly', 'yearly')
    ])
    interval = models.PositiveIntegerField(default=1, help_text='How many days/weeks/months/years/ should be repeated')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    last_generated = models.DateTimeField(null=True, blank=True, help_text=('Last task created date'))
    active = models.BooleanField(default=True)

    def clean(self):
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError('Date of end should bigger than start ')
        
    def __str__(self):
        return f"{self.title} {self.interval} {self.interval_type}"
    

class TaskHistory(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_title = models.CharField(max_length=255, null=True, blank=True)
    new_title = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{ self.task.title } - {self.action} at {self.timestamp}"
    


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    is_accepted = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} ➡ {self.to_user}"

class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_user2')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1} <-> {self.user2}"

class ChatMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    hidden_for_sender = models.BooleanField(default=False)
    hidden_for_receiver = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.sender.email} -> {self.receiver.email}: {self.message[:20]}"

class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocking")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

