from django.urls import path
from . import views

app_name = 'moderation'

urlpatterns = [
    path('block/<str:username>/', views.block_toggle_view, name='block_toggle'),
    path('blocked/', views.blocked_users_list_view, name='blocked_list'),
    path('report/', views.report_view, name='report'),
]
