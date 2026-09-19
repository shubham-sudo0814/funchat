"""
Pages views: List, Create, Detail, and Follow toggle.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Page, PageFollower
from .forms import PageForm


@login_required
def pages_list_view(request):
    """
    Explore all pages and view user's owned and followed pages.
    """
    all_pages = Page.objects.all()[:30]
    owned_pages = Page.objects.filter(owner=request.user)
    return render(request, 'pages/list.html', {
        'pages': all_pages,
        'owned_pages': owned_pages
    })


@login_required
def page_create_view(request):
    """
    Create a new community, business, or creator page.
    """
    if request.method == 'POST':
        form = PageForm(request.POST, request.FILES)
        if form.is_valid():
            page = form.save(commit=False)
            page.owner = request.user
            page.save()
            # Owner automatically follows their own page
            PageFollower.objects.create(page=page, user=request.user)
            messages.success(request, f"Page '{page.name}' created successfully!")
            return redirect('pages:detail', slug=page.slug)
    else:
        form = PageForm()

    return render(request, 'pages/create.html', {'form': form})


@login_required
def page_detail_view(request, slug):
    """
    View page profile, description, and stats.
    """
    page = get_object_or_404(Page, slug=slug)
    is_following = page.is_followed_by(request.user)
    is_owner = (page.owner == request.user)

    return render(request, 'pages/detail.html', {
        'page': page,
        'is_following': is_following,
        'is_owner': is_owner,
        'followers_count': page.followers_count(),
    })


@login_required
@require_POST
def page_follow_toggle(request, slug):
    """
    Follow or unfollow a page.
    """
    page = get_object_or_404(Page, slug=slug)
    existing = PageFollower.objects.filter(page=page, user=request.user).first()

    if existing:
        existing.delete()
        messages.info(request, f"Unfollowed {page.name}.")
    else:
        PageFollower.objects.create(page=page, user=request.user)
        messages.success(request, f"You are now following {page.name}!")

    return redirect('pages:detail', slug=slug)
