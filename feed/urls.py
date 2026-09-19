"""
Feed URL routes.
"""

from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('posts/create/', views.post_create_view, name='post_create'),
    path('posts/<int:pk>/', views.post_detail_view, name='post_detail'),
    path('posts/<int:pk>/edit/', views.post_edit_view, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete_view, name='post_delete'),
    path('posts/<int:pk>/react/', views.post_react_toggle_view, name='post_react'),
    path('posts/<int:pk>/comment/', views.comment_create_view, name='comment_create'),
    path('posts/comments/<int:pk>/delete/', views.comment_delete_view, name='comment_delete'),
    path('posts/<int:pk>/save/', views.post_save_toggle_view, name='post_save'),
    path('posts/<int:pk>/share/', views.post_share_view, name='post_share'),
    path('saved/', views.saved_posts_view, name='saved_posts'),
    path('search/', views.search_view, name='search'),
]
