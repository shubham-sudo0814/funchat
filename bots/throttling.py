"""
Bot Rate Limiting (Section 49.12).
"""

from rest_framework.throttling import SimpleRateThrottle


class BotRateThrottle(SimpleRateThrottle):
    """
    Limits bot API requests to prevent abuse or unbounded looping.
    Defaults to 120 requests per minute per bot.
    """
    scope = 'bot_api'

    def get_cache_key(self, request, view):
        if hasattr(request, 'bot') and request.bot:
            return f"throttle_bot_{request.bot.id}"
        # Fallback to IP address if unauthenticated
        return self.get_ident(request)
