"""
Bot API Key Authentication backend for Django REST Framework (Section 49.5).
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import BotAPIKey
import hashlib


class BotAPIKeyAuthentication(BaseAuthentication):
    """
    Authenticates requests with Bearer bot_live_... tokens.
    Verifies SHA-256 hash against database, checks key & bot activity and expiration.
    """
    keyword = 'Bearer'

    def authenticate_header(self, request):
        return 'Bearer realm="bot_api"'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        raw_token = parts[1].strip()
        if not raw_token.startswith(BotAPIKey.PREFIX):
            return None

        # 1. Securely hash raw token using SHA-256
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        # 2. Lookup API key by hash
        try:
            api_key = BotAPIKey.objects.select_related('bot', 'bot__owner').get(key_hash=token_hash)
        except BotAPIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid bot API key.")

        # 3. Check key validity
        if not api_key.is_active:
            raise AuthenticationFailed("This bot API key has been revoked.")

        if api_key.expires_at and timezone.now() > api_key.expires_at:
            raise AuthenticationFailed("This bot API key has expired.")

        # 4. Check Bot status
        if not api_key.bot.is_active:
            raise AuthenticationFailed("The associated bot is disabled or inactive.")

        # 5. Update last_used_at timestamp safely
        BotAPIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        # Set request.bot
        request.bot = api_key.bot
        request.bot_api_key = api_key

        # DRF expects (user, auth) tuple
        # User is the bot's owner, auth is the api_key object
        return (api_key.bot.owner, api_key)
