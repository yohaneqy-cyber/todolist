from rest_framework import serializers
from .models import Task, ChatMessage

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class ChatMessageSerializers(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    receiver_email = serializers.EmailField(source='receiver.email', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_email', 'receiver', 'receiver_email', 'message', 'timestamp', 'edited']
        read_only_fields = ['id', 'sender', 'receiver', 'timestamp', 'edited']
