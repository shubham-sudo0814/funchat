"""
Views for Accounts: Registration, Login, Logout, Profile, Follow, and Friendship.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import User, Follow, Friendship
from .forms import UserRegistrationForm, UserLoginForm, UserProfileEditForm


def register_view(request):
    """
    Handle user registration.
    """
    if request.user.is_authenticated:
        return redirect('feed:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Funchat, @{user.username}! Your account has been created.")
            return redirect('feed:home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Handle user login.
    """
    if request.user.is_authenticated:
        return redirect('feed:home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, @{user.username}!")
            next_url = request.GET.get('next', 'feed:home')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    Handle user logout.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def profile_view(request, username):
    """
    Display a user profile with stats, relationship buttons, and posts.
    """
    profile_user = get_object_or_404(User, username=username)
    is_self = (request.user == profile_user)
    
    # Relationship states
    is_following = request.user.is_following(profile_user)
    friendship_status = request.user.get_friendship_status(profile_user)
    
    # Check privacy: if private and not self and not friends, restrict viewing posts
    can_view_content = is_self or (not profile_user.is_private) or (friendship_status == 'friends')

    # Get posts if feed app is active
    posts = []
    if can_view_content:
        posts = profile_user.posts.all().select_related('author').prefetch_related('reactions', 'comments')[:20]

    context = {
        'profile_user': profile_user,
        'is_self': is_self,
        'is_following': is_following,
        'friendship_status': friendship_status,
        'can_view_content': can_view_content,
        'followers_count': profile_user.followers_count(),
        'following_count': profile_user.following_count(),
        'friends_count': profile_user.friends_count(),
        'posts': posts,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """
    Edit profile settings and avatar.
    """
    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been successfully updated.")
            return redirect('accounts:profile', username=request.user.username)
    else:
        form = UserProfileEditForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
@require_POST
def follow_toggle_view(request, username):
    """
    Follow or unfollow a user. Supports AJAX.
    """
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'You cannot follow yourself.'}, status=400)
        messages.warning(request, "You cannot follow yourself.")
        return redirect('accounts:profile', username=username)

    follow_rel = Follow.objects.filter(follower=request.user, following=target_user).first()
    if follow_rel:
        follow_rel.delete()
        is_following = False
        action_text = "Unfollowed"
    else:
        Follow.objects.create(follower=request.user, following=target_user)
        is_following = True
        action_text = "Following"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'is_following': is_following,
            'followers_count': target_user.followers_count(),
        })

    messages.info(request, f"{action_text} @{target_user.username}.")
    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def friend_request_send_view(request, username):
    """
    Send a friend request to a user.
    """
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        messages.warning(request, "You cannot send a friend request to yourself.")
        return redirect('accounts:profile', username=username)

    existing = Friendship.objects.filter(
        (Q(sender=request.user, receiver=target_user) | Q(sender=target_user, receiver=request.user))
    ).first()

    if existing:
        if existing.status == Friendship.STATUS_ACCEPTED:
            messages.info(request, f"You are already friends with @{target_user.username}.")
        elif existing.status == Friendship.STATUS_PENDING:
            messages.info(request, "A friend request is already pending.")
    else:
        Friendship.objects.create(sender=request.user, receiver=target_user, status=Friendship.STATUS_PENDING)
        messages.success(request, f"Friend request sent to @{target_user.username}.")

    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def friend_request_accept_view(request, username):
    """
    Accept a received friend request.
    """
    target_user = get_object_or_404(User, username=username)
    friendship = Friendship.objects.filter(
        sender=target_user,
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).first()

    if friendship:
        friendship.status = Friendship.STATUS_ACCEPTED
        friendship.save()
        messages.success(request, f"You are now friends with @{target_user.username}!")
    else:
        messages.error(request, "Friend request not found.")

    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def friend_request_reject_view(request, username):
    """
    Reject a received friend request.
    """
    target_user = get_object_or_404(User, username=username)
    friendship = Friendship.objects.filter(
        sender=target_user,
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).first()

    if friendship:
        friendship.delete()
        messages.info(request, f"Friend request from @{target_user.username} rejected.")
    else:
        messages.error(request, "Friend request not found.")

    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def friend_request_cancel_view(request, username):
    """
    Cancel an outgoing pending friend request.
    """
    target_user = get_object_or_404(User, username=username)
    friendship = Friendship.objects.filter(
        sender=request.user,
        receiver=target_user,
        status=Friendship.STATUS_PENDING
    ).first()

    if friendship:
        friendship.delete()
        messages.info(request, f"Cancelled friend request to @{target_user.username}.")
    else:
        messages.error(request, "No pending friend request found.")

    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def unfriend_view(request, username):
    """
    Remove an existing friend.
    """
    target_user = get_object_or_404(User, username=username)
    Friendship.objects.filter(
        (Q(sender=request.user, receiver=target_user) | Q(sender=target_user, receiver=request.user)),
        status=Friendship.STATUS_ACCEPTED
    ).delete()

    messages.info(request, f"Removed @{target_user.username} from friends.")
    return redirect('accounts:profile', username=username)


@login_required
def followers_list_view(request, username):
    user = get_object_or_404(User, username=username)
    followers = [f.follower for f in user.follower_relations.select_related('follower')]
    return render(request, 'accounts/user_list.html', {
        'title': f"Followers of @{user.username}",
        'users': followers,
        'profile_user': user,
    })


@login_required
def following_list_view(request, username):
    user = get_object_or_404(User, username=username)
    following = [f.following for f in user.following_relations.select_related('following')]
    return render(request, 'accounts/user_list.html', {
        'title': f"Users followed by @{user.username}",
        'users': following,
        'profile_user': user,
    })


@login_required
def friends_list_view(request, username):
    user = get_object_or_404(User, username=username)
    friends = user.get_friends()
    return render(request, 'accounts/user_list.html', {
        'title': f"Friends of @{user.username}",
        'users': friends,
        'profile_user': user,
    })
