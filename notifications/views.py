"""
Notifications views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_list_view(request):
    """
    Display all notifications for the current user.
    """
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('actor')[:50]

    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def notification_read_view(request, pk):
    """
    Mark a notification as read and redirect to target.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()

    if notification.target_url:
        return redirect(notification.target_url)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read_view(request):
    """
    Mark all unread notifications as read. Supports AJAX.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notifications:list')
