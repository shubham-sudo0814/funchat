"""
Moderation views: Block, Unblock, and Report content or users.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q
from .models import Block, Report
from accounts.models import User, Follow, Friendship


@login_required
@require_POST
def block_toggle_view(request, username):
    """
    Toggle blocking of a user.
    When blocking, immediately severs follows and friendships.
    """
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        messages.warning(request, "You cannot block yourself.")
        return redirect('accounts:profile', username=username)

    existing_block = Block.objects.filter(blocker=request.user, blocked_user=target_user).first()
    if existing_block:
        existing_block.delete()
        messages.info(request, f"Unblocked @{target_user.username}.")
    else:
        Block.objects.create(blocker=request.user, blocked_user=target_user)
        # Sever follow relationships
        Follow.objects.filter(
            Q(follower=request.user, following=target_user) |
            Q(follower=target_user, following=request.user)
        ).delete()
        # Sever friendship
        Friendship.objects.filter(
            Q(sender=request.user, receiver=target_user) |
            Q(sender=target_user, receiver=request.user)
        ).delete()
        messages.warning(request, f"Blocked @{target_user.username}.")

    return redirect(request.META.get('HTTP_REFERER', 'feed:home'))


@login_required
def blocked_users_list_view(request):
    """
    View all users currently blocked by the logged-in user.
    """
    blocked_relations = Block.objects.filter(blocker=request.user).select_related('blocked_user')
    blocked_users = [b.blocked_user for b in blocked_relations]
    return render(request, 'moderation/blocked_list.html', {'blocked_users': blocked_users})


@login_required
@require_POST
def report_view(request):
    """
    File a moderation report for a user, post, or comment.
    """
    target_type = request.POST.get('target_type')
    target_id = request.POST.get('target_id')
    reason = request.POST.get('reason')
    details = request.POST.get('details', '').strip()

    if not target_type or not target_id or not reason:
        messages.error(request, "Invalid report submission.")
        return redirect('feed:home')

    Report.objects.create(
        reporter=request.user,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details=details
    )
    messages.success(request, "Thank you for helping keep Funchat safe. Your report has been submitted to moderators.")
    return redirect(request.META.get('HTTP_REFERER', 'feed:home'))
