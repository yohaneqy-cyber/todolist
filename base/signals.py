from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .utils import save_resized_avatars  # اگر تابع کمکی توی utils هست

@receiver(post_save, sender=User)
def process_avatar(sender, instance, created, **kwargs):
    if instance.avatar:
        avatar_path = instance.avatar.path
        base_name = save_resized_avatars(avatar_path, instance.id)
        if instance.avatar_base_name != base_name:
            instance.avatar_base_name = base_name
            instance.save(update_fields=['avatar_base_name'])
