"""
Bot REST API version 1 URL routing.
"""

from django.urls import path
from . import api_views

app_name = 'bot_api'

urlpatterns = [
    path('messages/send', api_views.BotSendMessageAPIView.as_view(), name='send_message'),
    path('commands', api_views.BotCommandsListAPIView.as_view(), name='commands'),
    path('webhook', api_views.BotWebhookStatusAPIView.as_view(), name='webhook_status'),
]
