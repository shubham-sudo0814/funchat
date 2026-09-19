"""
Notification system models.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Actionable notification for users (likes, comments, follows, friend requests, messages).
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='caused_notifications'
    )
    verb = models.CharField(_('verb'), max_length=255)
    target_url = models.CharField(_('target url'), max_length=500, blank=True)
    is_read = models.BooleanField(_('is read'), default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"Notification for @{self.recipient.username}: @{self.actor.username} {self.verb}"
