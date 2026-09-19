"""
Context processors for accounts and global badge counts.
"""

def user_notifications_count(request):
    """
    Supplies unread notification count and pending friend requests to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'pending_friend_requests_count': 0
        }

    count = 0
    try:
        from notifications.models import Notification
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    except Exception:
        count = 0

    pending_friends = 0
    try:
        from accounts.models import Friendship
        pending_friends = Friendship.objects.filter(
            receiver=request.user,
            status=Friendship.STATUS_PENDING
        ).count()
    except Exception:
        pending_friends = 0

    return {
        'unread_notifications_count': count,
        'pending_friend_requests_count': pending_friends
    }
