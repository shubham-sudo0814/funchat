"""
Messaging views: Inbox, 1-on-1 direct chat, group conversations, and real-time polling API.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Conversation, ConversationParticipant, Message
from accounts.models import User


@login_required
def inbox_view(request):
    """
    User's messaging inbox listing all active conversations.
    """
    participations = ConversationParticipant.objects.filter(
        user=request.user
    ).select_related('conversation').order_by('-conversation__updated_at')

    conversations_data = []
    for p in participations:
        convo = p.conversation
        last_msg = convo.messages.select_related('sender').last()
        unread_count = convo.messages.filter(
            created_at__gt=p.last_read_at
        ).exclude(sender=request.user).count() if p.last_read_at else convo.messages.exclude(sender=request.user).count()

        conversations_data.append({
            'conversation': convo,
            'title': convo.get_title_for_user(request.user),
            'other_user': convo.get_other_user(request.user),
            'last_message': last_msg,
            'unread_count': unread_count,
        })

    context = {
        'conversations_data': conversations_data,
        'active_conversation': None,
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def direct_chat_view(request, username):
    """
    Start or jump into a direct 1-on-1 chat with username.
    """
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user:
        messages.warning(request, "You cannot message yourself.")
        return redirect('messaging:inbox')

    # Verify user hasn't been blocked
    try:
        from moderation.models import Block
        if Block.objects.filter(blocker=other_user, blocked_user=request.user).exists():
            messages.error(request, "You cannot message this user.")
            return redirect('messaging:inbox')
    except Exception:
        pass

    convo, _ = Conversation.get_or_create_direct(request.user, other_user)
    return redirect('messaging:conversation_detail', conversation_id=convo.id)


@login_required
def conversation_detail_view(request, conversation_id):
    """
    Detailed conversation view with messages thread.
    """
    convo = get_object_or_404(Conversation, id=conversation_id)

    # Authorization: User must be a participant
    participant = ConversationParticipant.objects.filter(
        conversation=convo,
        user=request.user
    ).first()

    if not participant:
        raise PermissionDenied("You are not a participant in this conversation.")

    # Mark as read
    participant.mark_read()

    # Load recent messages
    chat_messages = convo.messages.select_related('sender').order_by('created_at')[:100]

    # Inbox conversation list for split-pane UI
    user_participations = ConversationParticipant.objects.filter(
        user=request.user
    ).select_related('conversation').order_by('-conversation__updated_at')

    conversations_data = []
    for p in user_participations:
        c = p.conversation
        conversations_data.append({
            'conversation': c,
            'title': c.get_title_for_user(request.user),
            'other_user': c.get_other_user(request.user),
            'last_message': c.messages.last(),
            'is_active': (c.id == convo.id),
        })

    context = {
        'active_conversation': convo,
        'conversation_title': convo.get_title_for_user(request.user),
        'other_user': convo.get_other_user(request.user),
        'chat_messages': chat_messages,
        'conversations_data': conversations_data,
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
@require_POST
def send_message_view(request, conversation_id):
    """
    Send a message within a conversation. Supports AJAX.
    """
    convo = get_object_or_404(Conversation, id=conversation_id)
    participant = ConversationParticipant.objects.filter(
        conversation=convo,
        user=request.user
    ).first()

    if not participant:
        return HttpResponseBadRequest("Not a participant.")

    text = request.POST.get('text', '').strip()
    if not text:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)
        return redirect('messaging:conversation_detail', conversation_id=convo.id)

    # Create message
    msg = Message.objects.create(
        conversation=convo,
        sender=request.user,
        text=text
    )
    convo.save()  # Updates conversation.updated_at

    # Update sender's last_read_at
    participant.mark_read()

    # Trigger notifications for other participants
    other_members = convo.participants.exclude(user=request.user).select_related('user')
    try:
        from notifications.models import Notification
        for member in other_members:
            Notification.objects.create(
                recipient=member.user,
                actor=request.user,
                verb=f"sent you a message",
                target_url=f"/messages/{convo.id}/"
            )
    except Exception:
        pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': {
                'id': msg.id,
                'sender': msg.sender.username,
                'display_name': msg.sender.get_display_name(),
                'text': msg.text,
                'created_at': msg.created_at.strftime('%H:%M'),
                'is_self': True,
            }
        })

    return redirect('messaging:conversation_detail', conversation_id=convo.id)


@login_required
def api_fetch_messages(request, conversation_id):
    """
    JSON polling endpoint to fetch new messages since last_message_id.
    """
    convo = get_object_or_404(Conversation, id=conversation_id)
    participant = ConversationParticipant.objects.filter(
        conversation=convo,
        user=request.user
    ).first()

    if not participant:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    last_id = request.GET.get('since_id', 0)
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    new_messages = convo.messages.filter(id__gt=last_id).select_related('sender').order_by('created_at')
    
    # Mark read
    participant.mark_read()

    data = []
    for m in new_messages:
        data.append({
            'id': m.id,
            'sender': m.sender.username,
            'display_name': m.sender.get_display_name(),
            'text': m.text,
            'created_at': m.created_at.strftime('%H:%M'),
            'is_self': (m.sender == request.user),
        })

    return JsonResponse({'messages': data})


@login_required
def create_group_view(request):
    """
    Create a new group conversation with chosen friends.
    """
    friends = request.user.get_friends()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        selected_user_ids = request.POST.getlist('members')

        if not title:
            messages.error(request, "Please specify a group title.")
            return render(request, 'messaging/group_create.html', {'friends': friends})

        if not selected_user_ids:
            messages.error(request, "Please select at least one friend to join the group.")
            return render(request, 'messaging/group_create.html', {'friends': friends})

        # Create group conversation
        group_convo = Conversation.objects.create(title=title, is_group=True)
        # Add creator as admin
        ConversationParticipant.objects.create(
            conversation=group_convo,
            user=request.user,
            is_admin=True
        )

        # Add selected friends
        valid_friends = User.objects.filter(id__in=selected_user_ids)
        for friend in valid_friends:
            ConversationParticipant.objects.create(
                conversation=group_convo,
                user=friend
            )

        messages.success(request, f"Group '{title}' created successfully!")
        return redirect('messaging:conversation_detail', conversation_id=group_convo.id)

    return render(request, 'messaging/group_create.html', {'friends': friends})
