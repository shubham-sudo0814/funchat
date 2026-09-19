"""
Feed views: Chronological timeline, post CRUD, reactions, comments, bookmarks, shares, and search.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Post, Reaction, Comment, SavedPost
from .forms import PostForm, CommentForm
from accounts.models import User, Follow, Friendship


@login_required
def home_view(request):
    """
    Main chronological social feed.
    Shows posts from followed users, friends, and own posts.
    """
    user = request.user
    
    # 1. Gather relevant user IDs
    following_ids = list(user.following_relations.values_list('following_id', flat=True))
    friend_ids = list(user.get_friends().values_list('id', flat=True))
    relevant_ids = set(following_ids + friend_ids + [user.id])

    # 2. Query posts
    posts = Post.objects.filter(author_id__in=relevant_ids).select_related(
        'author', 'shared_from', 'shared_from__author'
    ).prefetch_related('reactions', 'comments', 'comments__author')

    # If user follows very few people, merge recent public posts
    if posts.count() < 10:
        posts = Post.objects.select_related(
            'author', 'shared_from', 'shared_from__author'
        ).prefetch_related('reactions', 'comments', 'comments__author')[:50]
    else:
        posts = posts[:50]

    # 3. Suggested users to follow
    suggested_users = User.objects.exclude(
        id__in=relevant_ids
    ).exclude(id=user.id).order_by('-date_joined')[:5]

    context = {
        'posts': posts,
        'post_form': PostForm(),
        'comment_form': CommentForm(),
        'suggested_users': suggested_users,
    }
    return render(request, 'feed/home.html', context)


@login_required
@require_POST
def post_create_view(request):
    """
    Create a new post with text and optional media.
    """
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Your post has been published!")
    else:
        errors = [err for sublist in form.errors.values() for err in sublist]
        messages.error(request, " ".join(errors) or "Could not publish post.")
    
    return redirect('feed:home')


@login_required
def post_detail_view(request, pk):
    """
    View a single post with comments thread.
    """
    post = get_object_or_404(
        Post.objects.select_related('author', 'shared_from', 'shared_from__author')
        .prefetch_related('comments', 'comments__author', 'reactions'),
        pk=pk
    )
    comments = post.comments.filter(parent__isnull=True).select_related('author').prefetch_related('replies', 'replies__author')
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': CommentForm(),
    }
    return render(request, 'feed/post_detail.html', context)


@login_required
def post_edit_view(request, pk):
    """
    Edit an existing post (author only).
    """
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        raise PermissionDenied("You do not have permission to edit this post.")

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect('feed:post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, 'feed/post_edit.html', {'form': form, 'post': post})


@login_required
@require_POST
def post_delete_view(request, pk):
    """
    Delete an existing post (author only).
    """
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        raise PermissionDenied("You do not have permission to delete this post.")

    post.delete()
    messages.info(request, "Post deleted.")
    return redirect('feed:home')


@login_required
@require_POST
def post_react_toggle_view(request, pk):
    """
    Toggle a reaction (e.g. LIKE) on a post. Supports AJAX.
    """
    post = get_object_or_404(Post, pk=pk)
    reaction_type = request.POST.get('reaction_type', Reaction.REACTION_LIKE)

    existing_reaction = Reaction.objects.filter(post=post, user=request.user).first()
    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Same reaction clicked -> remove it (unlike)
            existing_reaction.delete()
            is_reacted = False
        else:
            # Change reaction type
            existing_reaction.reaction_type = reaction_type
            existing_reaction.save()
            is_reacted = True
    else:
        Reaction.objects.create(post=post, user=request.user, reaction_type=reaction_type)
        is_reacted = True

        # Trigger notification if reacting to someone else's post
        if post.author != request.user:
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    recipient=post.author,
                    actor=request.user,
                    verb=f"reacted to your post",
                    target_url=f"/feed/posts/{post.pk}/"
                )
            except Exception:
                pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'is_reacted': is_reacted,
            'reactions_count': post.reactions.count(),
        })

    return redirect(request.META.get('HTTP_REFERER', 'feed:home'))


@login_required
@require_POST
def comment_create_view(request, pk):
    """
    Add a comment or reply to a post.
    """
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user

        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent_comment = Comment.objects.filter(pk=parent_id, post=post).first()
            if parent_comment:
                comment.parent = parent_comment

        comment.save()

        # Trigger notification for post author
        if post.author != request.user:
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    recipient=post.author,
                    actor=request.user,
                    verb="commented on your post",
                    target_url=f"/feed/posts/{post.pk}/"
                )
            except Exception:
                pass

        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Could not post comment.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('feed:post_detail', pk=pk)


@login_required
@require_POST
def comment_delete_view(request, pk):
    """
    Delete a comment (comment author or post author only).
    """
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author != request.user and comment.post.author != request.user:
        raise PermissionDenied("You do not have permission to delete this comment.")

    post_pk = comment.post.pk
    comment.delete()
    messages.info(request, "Comment deleted.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('feed:post_detail', pk=post_pk)


@login_required
@require_POST
def post_save_toggle_view(request, pk):
    """
    Save or unsave a post (bookmark). Supports AJAX.
    """
    post = get_object_or_404(Post, pk=pk)
    saved_obj = SavedPost.objects.filter(user=request.user, post=post).first()

    if saved_obj:
        saved_obj.delete()
        is_saved = False
        action_text = "Post removed from bookmarks."
    else:
        SavedPost.objects.create(user=request.user, post=post)
        is_saved = True
        action_text = "Post saved to bookmarks."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_saved': is_saved
        })

    messages.info(request, action_text)
    return redirect(request.META.get('HTTP_REFERER', 'feed:home'))


@login_required
def saved_posts_view(request):
    """
    View all posts saved by the user.
    """
    saved_posts = SavedPost.objects.filter(
        user=request.user
    ).select_related('post', 'post__author', 'post__shared_from').order_by('-created_at')

    posts = [sp.post for sp in saved_posts]
    return render(request, 'feed/saved_posts.html', {'posts': posts})


@login_required
@require_POST
def post_share_view(request, pk):
    """
    Share / repost content without duplicating media.
    """
    original_post = get_object_or_404(Post, pk=pk)
    # If the post was itself a share, link to the root original post
    root_post = original_post.shared_from if original_post.shared_from else original_post

    commentary = request.POST.get('content', '').strip()
    Post.objects.create(
        author=request.user,
        content=commentary,
        shared_from=root_post
    )
    messages.success(request, f"You shared @{root_post.author.username}'s post!")
    return redirect('feed:home')


@login_required
def search_view(request):
    """
    Search across users, posts, and tags.
    """
    query = request.GET.get('q', '').strip()
    users = []
    posts = []

    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(bio__icontains=query)
        ).distinct()[:20]

        posts = Post.objects.filter(
            content__icontains=query
        ).select_related('author').prefetch_related('reactions', 'comments')[:20]

    context = {
        'query': query,
        'users': users,
        'posts': posts,
    }
    return render(request, 'feed/search.html', context)
