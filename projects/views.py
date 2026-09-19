"""
Projects views: Showcase gallery, creation, detail, and upvoting.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Project, ProjectLike
from .forms import ProjectForm


@login_required
def projects_list_view(request):
    """
    Project showcase gallery with optional tag filtering.
    """
    tag = request.GET.get('tag', '').strip()
    if tag:
        projects = Project.objects.filter(tags__icontains=tag).select_related('owner')[:30]
    else:
        projects = Project.objects.select_related('owner')[:30]

    my_projects = Project.objects.filter(owner=request.user)

    return render(request, 'projects/list.html', {
        'projects': projects,
        'my_projects': my_projects,
        'active_tag': tag,
    })


@login_required
def project_create_view(request):
    """
    Publish a new project showcase.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, f"Project '{project.title}' published!")
            return redirect('projects:detail', slug=project.slug)
    else:
        form = ProjectForm()

    return render(request, 'projects/create.html', {'form': form})


@login_required
def project_detail_view(request, slug):
    """
    View detailed project information, links, and demo.
    """
    project = get_object_or_404(Project.objects.select_related('owner'), slug=slug)
    is_liked = project.is_liked_by(request.user)

    return render(request, 'projects/detail.html', {
        'project': project,
        'is_liked': is_liked,
        'likes_count': project.likes_count(),
    })


@login_required
@require_POST
def project_like_toggle(request, slug):
    """
    Upvote / like a project. Supports AJAX.
    """
    project = get_object_or_404(Project, slug=slug)
    existing = ProjectLike.objects.filter(project=project, user=request.user).first()

    if existing:
        existing.delete()
        is_liked = False
    else:
        ProjectLike.objects.create(project=project, user=request.user)
        is_liked = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_liked': is_liked,
            'likes_count': project.likes_count(),
        })

    return redirect('projects:detail', slug=slug)
