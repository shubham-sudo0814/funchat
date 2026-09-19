"""
Feed models: Post, Reaction, Comment, and SavedPost.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from accounts.validators import validate_image_file


class Post(models.Model):
    """
    User post containing text and/or an image, with repost support.
    """
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    content = models.TextField(_('content'), max_length=2000, blank=True)
    image = models.ImageField(
        _('image'),
        upload_to='posts/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    shared_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shares'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        snippet = (self.content[:30] + '...') if len(self.content) > 30 else self.content
        return f"Post #{self.id} by @{self.author.username}: {snippet}"

    @property
    def reactions_count(self):
        return self.reactions.count()

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def shares_count(self):
        return self.shares.count()

    def is_reacted_by(self, user, reaction_type=None):
        if not user or not user.is_authenticated:
            return False
        qs = self.reactions.filter(user=user)
        if reaction_type:
            qs = qs.filter(reaction_type=reaction_type)
        return qs.exists()

    def is_saved_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.saved_by_users.filter(user=user).exists()


class Reaction(models.Model):
    """
    Extensible user reaction on a post (Like, Love, Celebrate, Fire).
    """
    REACTION_LIKE = 'LIKE'
    REACTION_LOVE = 'LOVE'
    REACTION_CELEBRATE = 'CELEBRATE'
    REACTION_FIRE = 'FIRE'

    REACTION_CHOICES = [
        (REACTION_LIKE, '👍 Like'),
        (REACTION_LOVE, '❤️ Love'),
        (REACTION_CELEBRATE, '🎉 Celebrate'),
        (REACTION_FIRE, '🔥 Fire'),
    ]

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_reactions'
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=REACTION_CHOICES,
        default=REACTION_LIKE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'],
                name='unique_user_post_reaction'
            )
        ]

    def __str__(self):
        return f"@{self.user.username} reacted {self.reaction_type} on Post #{self.post_id}"


class Comment(models.Model):
    """
    Comment on a post, with support for nested replies.
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField(_('content'), max_length=1000)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by @{self.author.username} on Post #{self.post_id}"


class SavedPost(models.Model):
    """
    Bookmarks/Saved posts collection for users.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_posts'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_user_saved_post'
            )
        ]

    def __str__(self):
        return f"@{self.user.username} saved Post #{self.post_id}"
