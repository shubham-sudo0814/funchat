"""
Bots forms for creation and configuration.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Bot, BotCommand, BotWebhook
import re


class BotCreateForm(forms.ModelForm):
    class Meta:
        model = Bot
        fields = ['name', 'username', 'description', 'profile_image', 'can_send_messages', 'can_read_messages', 'can_send_notifications', 'can_use_commands']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Study Assistant'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. study_assistant_bot'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What does this bot do?'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        cleaned = username.lstrip('@')
        if not re.match(r'^[a-zA-Z0-9_]+$', cleaned):
            raise ValidationError("Bot username may only contain letters, numbers, and underscores.")
        if len(cleaned) < 3:
            raise ValidationError("Bot username must be at least 3 characters long.")
        formatted = f"@{cleaned.lower()}"
        if Bot.objects.filter(username__iexact=formatted).exists():
            raise ValidationError(f"Bot username '{formatted}' is already taken.")
        return formatted


class BotCommandForm(forms.ModelForm):
    class Meta:
        model = BotCommand
        fields = ['command', 'description']
        widgets = {
            'command': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '/start or /help'}),
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Description of command'}),
        }


class BotWebhookForm(forms.ModelForm):
    class Meta:
        model = BotWebhook
        fields = ['url', 'is_active']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://your-domain.com/webhook'}),
        }
