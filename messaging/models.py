"""
Messaging models: Conversation, ConversationParticipant, and Message.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Conversation(models.Model):
    """
    Direct or group chat conversation.
    """
    title = models.CharField(_('title'), max_length=255, blank=True)
    is_group = models.BooleanField(_('is group conversation'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.is_group:
            return f"Group: {self.title or 'Unnamed Group'}"
        return f"Direct Conversation #{self.id}"

    def get_title_for_user(self, user):
        """
        For direct chats, return the other participant's display name.
        For group chats, return the group title or concatenated member names.
        """
        if self.is_group:
            return self.title or "Group Chat"
        other = self.participants.exclude(user=user).select_related('user').first()
        if other and other.user:
            return other.user.get_display_name()
        return "Conversation"

    def get_other_user(self, user):
        if self.is_group:
            return None
        other = self.participants.exclude(user=user).select_related('user').first()
        return other.user if other else None

    @classmethod
    def get_or_create_direct(cls, user1, user2):
        """
        Retrieves or initializes a direct 1-on-1 conversation between two users.
        """
        if user1 == user2:
            raise ValueError("Cannot create a direct conversation with oneself.")

        # Find direct conversations that include user1
        user1_convos = cls.objects.filter(
            is_group=False,
            participants__user=user1
        )
        # Narrow down to ones that also include user2
        direct_convo = user1_convos.filter(participants__user=user2).first()

        if direct_convo:
            return direct_convo, False

        # Create new conversation and add both participants
        convo = cls.objects.create(is_group=False)
        ConversationParticipant.objects.create(conversation=convo, user=user1)
        ConversationParticipant.objects.create(conversation=convo, user=user2)
        return convo, True


class ConversationParticipant(models.Model):
    """
    Membership in a conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships'
    )
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'user'],
                name='unique_conversation_participant'
            )
        ]

    def __str__(self):
        return f"@{self.user.username} in {self.conversation}"

    def mark_read(self):
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class Message(models.Model):
    """
    Chat message within a conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages'
    )
    text = models.TextField(_('text'), max_length=5000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"@{self.sender.username} in #{self.conversation_id}: {self.text[:30]}"
