"""
URL configuration for Funchat social network.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='feed:home', permanent=False)),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('feed/', include('feed.urls', namespace='feed')),
    path('messages/', include('messaging.urls', namespace='messaging')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('pages/', include('pages.urls', namespace='pages')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('moderation/', include('moderation.urls', namespace='moderation')),
    path('bots/', include('bots.urls', namespace='bots')),
    # API endpoints
    path('api/v1/bots/', include('bots.api_urls', namespace='bot_api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
