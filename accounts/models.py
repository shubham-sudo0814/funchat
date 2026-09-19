"""
Accounts models: Custom User, Follow relationships, and Friendships.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from .validators import validate_image_file


class User(AbstractUser):
    """
    Custom User Model for Funchat.
    """
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_DEACTIVATED = 'deactivated'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _('Active')),
        (STATUS_SUSPENDED, _('Suspended')),
        (STATUS_DEACTIVATED, _('Deactivated')),
    ]

    email = models.EmailField(_('email address'), unique=True, db_index=True)
    bio = models.TextField(_('bio'), max_length=500, blank=True)
    location = models.CharField(_('location'), max_length=100, blank=True)
    birth_date = models.DateField(_('birth date'), null=True, blank=True)
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    account_status = models.CharField(
        _('account status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    is_verified = models.BooleanField(_('verified account'), default=False)
    is_private = models.BooleanField(
        _('private profile'),
        default=False,
        help_text=_('Designates whether this profile is visible to friends only.')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

    def get_display_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def followers_count(self):
        return self.follower_relations.count()

    def following_count(self):
        return self.following_relations.count()

    def is_following(self, other_user):
        if not other_user or other_user == self:
            return False
        return self.following_relations.filter(following=other_user).exists()

    def is_friends_with(self, other_user):
        if not other_user or other_user == self:
            return False
        return Friendship.objects.filter(
            (Q(sender=self, receiver=other_user) | Q(sender=other_user, receiver=self)),
            status=Friendship.STATUS_ACCEPTED
        ).exists()

    def get_friendship_status(self, other_user):
        """
        Returns one of: 'self', 'friends', 'sent_pending', 'received_pending', 'none'
        """
        if other_user == self:
            return 'self'
        
        friendship = Friendship.objects.filter(
            (Q(sender=self, receiver=other_user) | Q(sender=other_user, receiver=self))
        ).first()

        if not friendship:
            return 'none'
        if friendship.status == Friendship.STATUS_ACCEPTED:
            return 'friends'
        if friendship.status == Friendship.STATUS_PENDING:
            if friendship.sender == self:
                return 'sent_pending'
            return 'received_pending'
        return 'none'

    def friends_count(self):
        return Friendship.objects.filter(
            (Q(sender=self) | Q(receiver=self)),
            status=Friendship.STATUS_ACCEPTED
        ).count()

    def get_friends(self):
        accepted_friendships = Friendship.objects.filter(
            (Q(sender=self) | Q(receiver=self)),
            status=Friendship.STATUS_ACCEPTED
        ).select_related('sender', 'receiver')

        friend_ids = []
        for f in accepted_friendships:
            friend_ids.append(f.receiver_id if f.sender_id == self.id else f.sender_id)
        return User.objects.filter(id__in=friend_ids)


class Follow(models.Model):
    """
    Directional Follow system: User A follows User B.
    """
    follower = models.ForeignKey(
        User,
        related_name='following_relations',
        on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        User,
        related_name='follower_relations',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_user_follow'
            ),
            models.CheckConstraint(
                condition=~Q(follower=F('following')),
                name='prevent_self_follow'
            ),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Friendship(models.Model):
    """
    Bidirectional Friend Request & Friendship system.
    """
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_ACCEPTED, _('Accepted')),
        (STATUS_REJECTED, _('Rejected')),
    ]

    sender = models.ForeignKey(
        User,
        related_name='sent_friend_requests',
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User,
        related_name='received_friend_requests',
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                name='unique_friendship_request'
            ),
            models.CheckConstraint(
                condition=~Q(sender=F('receiver')),
                name='prevent_self_friend_request'
            ),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"
