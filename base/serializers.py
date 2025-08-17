from rest_framework import serializers
from .models import Task, ChatMessage, User
from django.db.models import Q

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class ChatMessageSerializers(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    receiver_email = serializers.EmailField(source='receiver.email', read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_email', 'receiver', 'receiver_email', 'message', 'timestamp', 'edited', 'status', 'avatar_url']
        read_only_fields = ['id', 'sender', 'receiver', 'timestamp', 'edited', 'status', 'avatar_url']


    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url)
        return request.build_absolute_uri('/media/avatars/default-avatar.png')


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'avatar_url', 'last_message']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url)
        return request.build_absolute_uri('/media/avatars/default-avatar.png')
    
    def get_last_message(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        last_msg = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=obj) | Q(sender=obj, receiver=request.user)
        ).order_by('-timestamp').first()

        return last_msg.message if last_msg else None
