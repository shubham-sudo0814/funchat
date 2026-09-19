"""
Bots web dashboard URL patterns.
"""

from django.urls import path
from . import views

app_name = 'bots'

urlpatterns = [
    path('', views.bot_dashboard_view, name='dashboard'),
    path('create/', views.bot_create_view, name='create'),
    path('docs/', views.bot_docs_view, name='docs'),
    path('<int:bot_id>/', views.bot_detail_view, name='detail'),
    path('<int:bot_id>/delete/', views.bot_delete_view, name='delete'),
    path('<int:bot_id>/keys/generate/', views.bot_key_generate_view, name='key_generate'),
    path('<int:bot_id>/keys/<int:key_id>/revoke/', views.bot_key_revoke_view, name='key_revoke'),
    path('<int:bot_id>/keys/<int:key_id>/rotate/', views.bot_key_rotate_view, name='key_rotate'),
    path('<int:bot_id>/commands/add/', views.bot_command_add_view, name='command_add'),
    path('<int:bot_id>/commands/<int:cmd_id>/delete/', views.bot_command_delete_view, name='command_delete'),
    path('<int:bot_id>/webhook/save/', views.bot_webhook_save_view, name='webhook_save'),
]
