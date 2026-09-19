from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_list_view, name='list'),
    path('<int:pk>/read/', views.notification_read_view, name='read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
]
