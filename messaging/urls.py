"""
Messaging URL routes.
"""

from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox_view, name='inbox'),
    path('new-group/', views.create_group_view, name='create_group'),
    path('direct/<str:username>/', views.direct_chat_view, name='direct_chat'),
    path('chat/<str:username>/', views.direct_chat_view, name='chat'),
    path('<int:conversation_id>/', views.conversation_detail_view, name='conversation_detail'),
    path('<int:conversation_id>/send/', views.send_message_view, name='send_message'),
    path('<int:conversation_id>/api/poll/', views.api_fetch_messages, name='api_fetch_messages'),
]
