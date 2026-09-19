"""
Bot REST API Endpoints (Section 49.6 & 49.7).
Endpoints authenticated with Bot API Keys via Bearer bot_live_...
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .authentication import BotAPIKeyAuthentication
from .throttling import BotRateThrottle
from .models import Bot, BotCommand, BotWebhook
from accounts.models import User
from messaging.models import Conversation, Message


class BotSendMessageAPIView(APIView):
    """
    POST /api/v1/bots/messages/send
    Allows authenticated bot to send a message to a user or conversation.
    """
    authentication_classes = [BotAPIKeyAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [BotRateThrottle]

    def post(self, request):
        bot = request.bot

        # Check bot permission (Section 49.11)
        if not bot.can_send_messages:
            return Response(
                {"error": "This bot does not have permission to send messages."},
                status=status.HTTP_403_FORBIDDEN
            )

        recipient_username = request.data.get('recipient_username')
        conversation_id = request.data.get('conversation_id')
        text = (request.data.get('text') or '').strip()

        if not text:
            return Response({"error": "Message text is required."}, status=status.HTTP_400_BAD_REQUEST)

        convo = None
        if conversation_id:
            convo = Conversation.objects.filter(id=conversation_id).first()
            if not convo:
                return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        elif recipient_username:
            clean_username = recipient_username.lstrip('@')
            target_user = User.objects.filter(username__iexact=clean_username).first()
            if not target_user:
                return Response({"error": f"Recipient user '@{clean_username}' not found."}, status=status.HTTP_404_NOT_FOUND)
            # Find or create direct conversation between bot's owner and target user
            convo, _ = Conversation.get_or_create_direct(bot.owner, target_user)
        else:
            return Response(
                {"error": "Must specify either recipient_username or conversation_id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create message with bot indicator prefix
        msg_text = f"🤖 [{bot.name}]: {text}"
        msg = Message.objects.create(
            conversation=convo,
            sender=bot.owner,
            text=msg_text
        )
        convo.save()

        return Response({
            "success": True,
            "message_id": msg.id,
            "conversation_id": convo.id,
            "bot": bot.username,
            "created_at": msg.created_at.isoformat()
        }, status=status.HTTP_201_CREATED)


class BotCommandsListAPIView(APIView):
    """
    GET /api/v1/bots/commands
    Lists commands supported by this bot.
    """
    authentication_classes = [BotAPIKeyAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [BotRateThrottle]

    def get(self, request):
        bot = request.bot
        commands = bot.commands.all().values('command', 'description')
        return Response({
            "bot": bot.username,
            "commands": list(commands)
        })


class BotWebhookStatusAPIView(APIView):
    """
    GET /api/v1/bots/webhook
    Returns webhook configuration and health status.
    """
    authentication_classes = [BotAPIKeyAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        bot = request.bot
        try:
            wh = bot.webhook
            return Response({
                "configured": True,
                "url": wh.url,
                "is_active": wh.is_active,
                "failure_count": wh.failure_count,
            })
        except BotWebhook.DoesNotExist:
            return Response({"configured": False})
