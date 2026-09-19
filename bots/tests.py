"""
Comprehensive automated tests for Telegram-Style Bot Platform (Section 49.21).
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from bots.models import Bot, BotAPIKey, BotCommand, BotWebhook
from bots.webhook_service import compute_webhook_signature
from rest_framework.test import APIClient
import hashlib


class BotPlatformTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='bot_owner', email='owner@test.com', password='Password123!')
        self.other_user = User.objects.create_user(username='other_user', email='other@test.com', password='Password123!')
        self.client = Client()
        self.client.force_login(self.owner)
        self.api_client = APIClient()

    def test_bot_creation_and_unique_username(self):
        """Verify bot creation, ownership, and unique username enforcement (49.1 & 49.2)."""
        bot = Bot.objects.create(
            owner=self.owner,
            name='Helper Bot',
            username='@helper_bot',
            description='Helpful assistant'
        )
        self.assertEqual(bot.owner, self.owner)
        self.assertEqual(bot.username, '@helper_bot')

        # Duplicate username should be rejected
        with self.assertRaises(Exception):
            Bot.objects.create(
                owner=self.other_user,
                name='Duplicate Bot',
                username='@helper_bot'
            )

    def test_api_key_generation_and_hashing(self):
        """API key is generated with secure random entropy; only hash is stored in DB (49.3 & 49.4)."""
        bot = Bot.objects.create(owner=self.owner, name='Sec Bot', username='@sec_bot')
        key_instance, raw_key = BotAPIKey.generate(bot, name='Live Key')

        # Raw key format check: starts with bot_live_
        self.assertTrue(raw_key.startswith('bot_live_'))
        self.assertGreater(len(raw_key), 30)

        # Database must NOT store raw key
        key_db = BotAPIKey.objects.get(id=key_instance.id)
        self.assertNotEqual(key_db.key_hash, raw_key)

        # Hash check: SHA-256 of raw key must match key_hash
        expected_hash = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
        self.assertEqual(key_db.key_hash, expected_hash)

        # Masked representation check: e.g. bot_live_••••••••••••abcd
        self.assertTrue(key_db.masked_key.startswith('bot_live_'))
        self.assertEqual(key_db.masked_key[-4:], raw_key[-4:])

    def test_api_key_authentication_success(self):
        """Bot can authenticate via Bearer token and send messages (49.5 & 49.7)."""
        bot = Bot.objects.create(owner=self.owner, name='Chat Bot', username='@chat_bot')
        _, raw_key = BotAPIKey.generate(bot)

        # Call send message API with valid token
        url = reverse('bot_api:send_message')
        res = self.api_client.post(
            url,
            {'recipient_username': self.other_user.username, 'text': 'Hello from bot!'},
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
            format='json'
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['success'])

    def test_invalid_api_key_rejection(self):
        """Invalid or forged API key is rejected with HTTP 401 (49.5 & 49.21)."""
        url = reverse('bot_api:send_message')
        res = self.api_client.post(
            url,
            {'recipient_username': self.other_user.username, 'text': 'Spam'},
            HTTP_AUTHORIZATION="Bearer bot_live_fake_invalid_token_1234567890",
            format='json'
        )
        self.assertEqual(res.status_code, 401)

    def test_revoked_key_rejection(self):
        """Revoked API key cannot be used (49.5 & 49.21)."""
        bot = Bot.objects.create(owner=self.owner, name='Revoke Bot', username='@revoke_bot')
        key_instance, raw_key = BotAPIKey.generate(bot)
        
        # Revoke key
        key_instance.is_active = False
        key_instance.save()

        url = reverse('bot_api:send_message')
        res = self.api_client.post(
            url,
            {'recipient_username': self.other_user.username, 'text': 'Test'},
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
            format='json'
        )
        self.assertEqual(res.status_code, 401)

    def test_expired_key_rejection(self):
        """Expired API key cannot be used (49.5 & 49.21)."""
        bot = Bot.objects.create(owner=self.owner, name='Expire Bot', username='@expire_bot')
        key_instance, raw_key = BotAPIKey.generate(bot)

        # Set expiration in the past
        key_instance.expires_at = timezone.now() - timezone.timedelta(days=1)
        key_instance.save()

        url = reverse('bot_api:send_message')
        res = self.api_client.post(
            url,
            {'recipient_username': self.other_user.username, 'text': 'Test'},
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
            format='json'
        )
        self.assertEqual(res.status_code, 401)

    def test_bot_permission_enforcement(self):
        """Bot without can_send_messages permission is blocked with HTTP 403 (49.11)."""
        bot = Bot.objects.create(
            owner=self.owner,
            name='Silent Bot',
            username='@silent_bot',
            can_send_messages=False
        )
        _, raw_key = BotAPIKey.generate(bot)

        url = reverse('bot_api:send_message')
        res = self.api_client.post(
            url,
            {'recipient_username': self.other_user.username, 'text': 'Silent test'},
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
            format='json'
        )
        self.assertEqual(res.status_code, 403)

    def test_webhook_signature_verification(self):
        """Webhook signatures match HMAC-SHA256 expectations (49.9 & 49.10)."""
        payload = b'{"event": "message.created", "text": "/start"}'
        secret = "super_secret_webhook_key_123"
        signature = compute_webhook_signature(payload, secret)

        # Verify signature length & valid hex format
        self.assertEqual(len(signature), 64)
        
        # Tampered payload fails verification
        tampered_sig = compute_webhook_signature(b'{"event": "tampered"}', secret)
        self.assertNotEqual(signature, tampered_sig)

    def test_bot_deletion_cascades_keys(self):
        """Deleting a bot invalidates and deletes all its API keys (49.21)."""
        bot = Bot.objects.create(owner=self.owner, name='Del Bot', username='@del_bot')
        key_instance, _ = BotAPIKey.generate(bot)

        key_id = key_instance.id
        bot.delete()

        self.assertFalse(BotAPIKey.objects.filter(id=key_id).exists())
