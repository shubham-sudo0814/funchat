"""
URL mappings for the accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/<str:username>/follow/', views.follow_toggle_view, name='follow_toggle'),
    path('profile/<str:username>/friend/send/', views.friend_request_send_view, name='friend_request_send'),
    path('profile/<str:username>/friend/accept/', views.friend_request_accept_view, name='friend_request_accept'),
    path('profile/<str:username>/friend/reject/', views.friend_request_reject_view, name='friend_request_reject'),
    path('profile/<str:username>/friend/cancel/', views.friend_request_cancel_view, name='friend_request_cancel'),
    path('profile/<str:username>/friend/unfriend/', views.unfriend_view, name='unfriend'),
    path('profile/<str:username>/followers/', views.followers_list_view, name='followers_list'),
    path('profile/<str:username>/following/', views.following_list_view, name='following_list'),
    path('profile/<str:username>/friends/', views.friends_list_view, name='friends_list'),
]
