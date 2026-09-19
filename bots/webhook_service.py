"""
Webhook delivery service with HMAC-SHA256 signatures and delivery logging (Section 49.9 & 49.10).
"""

import hmac
import hashlib
import json
import time
import urllib.request
import urllib.error
from django.utils import timezone
from .models import BotWebhook, BotDeliveryLog


def compute_webhook_signature(payload_bytes, secret):
    """
    Computes an HMAC-SHA256 hex digest for the payload using the bot's secret.
    """
    return hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()


def dispatch_bot_event(bot, event_type, data):
    """
    Sends a signed webhook event to the bot's callback URL.
    """
    try:
        webhook = bot.webhook
    except BotWebhook.DoesNotExist:
        return None

    if not webhook.is_active:
        return None

    timestamp = str(int(time.time()))
    payload = {
        'event': event_type,
        'bot_id': bot.id,
        'bot_username': bot.username,
        'timestamp': timestamp,
        'data': data
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = compute_webhook_signature(payload_bytes, webhook.secret)

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Funchat-Bot-Webhook/1.0',
        'X-Funchat-Bot-Signature': f"sha256={signature}",
        'X-Funchat-Timestamp': timestamp,
    }

    req = urllib.request.Request(webhook.url, data=payload_bytes, headers=headers, method='POST')
    status_code = None
    response_body = ""
    is_success = False

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.status
            response_body = response.read().decode('utf-8', errors='ignore')[:1000]
            is_success = (200 <= status_code < 300)
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_body = e.read().decode('utf-8', errors='ignore')[:1000]
    except Exception as e:
        response_body = str(e)[:500]

    # Update webhook failure tracking
    if not is_success:
        webhook.failure_count += 1
        if webhook.failure_count >= 10:
            webhook.is_active = False  # Auto-disable faulty webhooks after 10 consecutive failures
        webhook.save(update_fields=['failure_count', 'is_active'])
    else:
        if webhook.failure_count > 0:
            webhook.failure_count = 0
            webhook.save(update_fields=['failure_count'])

    # Log delivery
    return BotDeliveryLog.objects.create(
        bot=bot,
        event_type=event_type,
        payload=payload,
        response_status=status_code,
        response_body=response_body,
        is_success=is_success
    )
