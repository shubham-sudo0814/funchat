"""
Projects showcase models: Project and ProjectLike.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from accounts.validators import validate_image_file


class Project(models.Model):
    """
    Project portfolio showcase item for creators, developers, and students.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    title = models.CharField(_('title'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=220, unique=True, db_index=True)
    summary = models.CharField(_('summary'), max_length=250)
    description = models.TextField(_('detailed description'), max_length=5000)
    cover_image = models.ImageField(
        _('cover image'),
        upload_to='projects/covers/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    demo_url = models.URLField(_('demo URL'), blank=True)
    repo_url = models.URLField(_('repository URL'), blank=True)
    tags = models.CharField(
        _('tags'),
        max_length=200,
        blank=True,
        help_text=_('Comma-separated keywords e.g. python, react, machine-learning')
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "project"
            slug = base_slug
            counter = 1
            while Project.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def likes_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()


class ProjectLike(models.Model):
    """
    Like / upvote on a project showcase.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_like')
        ]

    def __str__(self):
        return f"@{self.user.username} liked Project '{self.project.title}'"
