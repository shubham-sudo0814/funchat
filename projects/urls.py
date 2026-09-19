from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.projects_list_view, name='list'),
    path('create/', views.project_create_view, name='create'),
    path('<slug:slug>/', views.project_detail_view, name='detail'),
    path('<slug:slug>/like/', views.project_like_toggle, name='like_toggle'),
]
