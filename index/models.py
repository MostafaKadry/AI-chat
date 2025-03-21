from django.db import models
from django.contrib.auth.models import User

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    role = models.CharField(max_length=10, choices=[
        ('user', 'User'),
        ('ai', 'AI')
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['timestamp']