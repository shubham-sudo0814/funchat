"""
Telegram-Style Bot Platform Models.
Follows all security, hashing, and relational constraints defined in Section 49.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.validators import validate_image_file
import secrets
import hashlib


class Bot(models.Model):
    """
    Bot model owned by a user (Section 49.1 & 49.2).
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_bots'
    )
    name = models.CharField(_('bot name'), max_length=100)
    username = models.CharField(
        _('bot username'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique username identifier, e.g. @assistant_bot')
    )
    description = models.TextField(_('description'), max_length=1000, blank=True)
    profile_image = models.ImageField(
        _('profile picture'),
        upload_to='bots/avatars/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    is_active = models.BooleanField(_('is active'), default=True)
    
    # Bot Permissions (Section 49.11)
    can_send_messages = models.BooleanField(default=True)
    can_read_messages = models.BooleanField(default=True)
    can_send_notifications = models.BooleanField(default=True)
    can_use_commands = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (@{self.username})"

    def clean_username(self):
        u = self.username.strip()
        if not u.startswith('@'):
            u = f"@{u}"
        return u.lower()

    def save(self, *args, **kwargs):
        self.username = self.clean_username()
        super().save(*args, **kwargs)


class BotAPIKey(models.Model):
    """
    Cryptographically secure hashed API Key for Bot Authentication (Section 49.3 & 49.4).
    Never stores the complete plaintext key in the database!
    """
    PREFIX = "bot_live_"

    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    key_prefix = models.CharField(max_length=20, default=PREFIX)
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    masked_key = models.CharField(max_length=50)  # e.g. bot_live_••••••••••••abcd
    name = models.CharField(_('key name'), max_length=100, default='Default Key')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.masked_key}) for @{self.bot.username}"

    @classmethod
    def generate(cls, bot, name='Default Key', expires_in_days=None):
        """
        Generates a new secure random API key.
        Returns tuple: (BotAPIKey_instance, plaintext_key)
        The plaintext_key is only returned here once and never saved to the DB!
        """
        # Generate 32 bytes of cryptographically secure random entropy
        entropy = secrets.token_hex(24)  # 48 characters hex
        raw_token = f"{cls.PREFIX}{entropy}"

        # Secure SHA-256 Hash
        hashed_token = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        # Masked representation: prefix + bullet points + last 4 characters
        masked = f"{cls.PREFIX}{'•' * 16}{raw_token[-4:]}"

        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)

        instance = cls.objects.create(
            bot=bot,
            key_prefix=cls.PREFIX,
            key_hash=hashed_token,
            masked_key=masked,
            name=name,
            expires_at=expires_at,
            is_active=True
        )
        return instance, raw_token

    def is_valid(self):
        """
        Checks if key is active, not expired, and bot is active.
        """
        if not self.is_active:
            return False
        if not self.bot.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class BotCommand(models.Model):
    """
    Registered bot command (Section 49.8), e.g. /start, /help, /weather.
    """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='commands')
    command = models.CharField(max_length=50)  # e.g. /start
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['command']
        constraints = [
            models.UniqueConstraint(fields=['bot', 'command'], name='unique_bot_command')
        ]

    def __str__(self):
        return f"{self.command} - {self.description} (@{self.bot.username})"


class BotWebhook(models.Model):
    """
    Configured webhook callback for a bot (Section 49.9 & 49.10).
    """
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name='webhook')
    url = models.URLField(_('callback url'), max_length=500)
    secret = models.CharField(max_length=64)  # Shared secret for HMAC-SHA256 signature
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Webhook for @{self.bot.username}: {self.url}"

    @classmethod
    def generate_secret(cls):
        return secrets.token_hex(32)


class BotDeliveryLog(models.Model):
    """
    Webhook and event delivery log (Section 49.10).
    """
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='delivery_logs')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    is_success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        status = "OK" if self.is_success else f"FAIL ({self.response_status})"
        return f"{self.event_type} to @{self.bot.username} -> {status}"
