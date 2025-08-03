from rest_framework import serializers
from .models import Task, ChatMessage

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class ChatMessageSerializers(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'receiver', 'message', 'timestamp', 'edited']
        read_only_fields = ['id', 'sender', 'receiver', 'timestamp', 'edited']