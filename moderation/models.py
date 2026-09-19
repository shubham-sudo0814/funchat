"""
Moderation models: Block and Report.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F


class Block(models.Model):
    """
    User-to-user blocking relationship.
    """
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_relations'
    )
    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_by_relations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['blocker', 'blocked_user'],
                name='unique_user_block'
            ),
            models.CheckConstraint(
                condition=~Q(blocker=F('blocked_user')),
                name='prevent_self_block'
            )
        ]

    def __str__(self):
        return f"@{self.blocker.username} blocked @{self.blocked_user.username}"


class Report(models.Model):
    """
    Content and user reporting for safety and moderation.
    """
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_HATE_SPEECH = 'hate_speech'
    REASON_VIOLENCE = 'violence'
    REASON_COPYRIGHT = 'copyright'
    REASON_OTHER = 'other'

    REASON_CHOICES = [
        (REASON_SPAM, _('Spam or Scam')),
        (REASON_HARASSMENT, _('Harassment or Bullying')),
        (REASON_HATE_SPEECH, _('Hate Speech')),
        (REASON_VIOLENCE, _('Violence or Dangerous Content')),
        (REASON_COPYRIGHT, _('Copyright Violation')),
        (REASON_OTHER, _('Other')),
    ]

    STATUS_PENDING = 'pending'
    STATUS_REVIEWED = 'reviewed'
    STATUS_DISMISSED = 'dismissed'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending Review')),
        (STATUS_REVIEWED, _('Reviewed & Actioned')),
        (STATUS_DISMISSED, _('Dismissed')),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='filed_reports'
    )
    target_type = models.CharField(_('target type'), max_length=50)  # 'user', 'post', 'comment'
    target_id = models.PositiveIntegerField(_('target id'))
    reason = models.CharField(_('reason'), max_length=50, choices=REASON_CHOICES)
    details = models.TextField(_('details'), blank=True, max_length=1000)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.id} by @{self.reporter.username} on {self.target_type}:{self.target_id}"
