from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.pages_list_view, name='list'),
    path('create/', views.page_create_view, name='create'),
    path('<slug:slug>/', views.page_detail_view, name='detail'),
    path('<slug:slug>/follow/', views.page_follow_toggle, name='follow_toggle'),
]
