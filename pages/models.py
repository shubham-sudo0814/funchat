"""
Pages models: Community/Organization Page and Page Follower.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from accounts.validators import validate_image_file


class Page(models.Model):
    """
    Creator, Organization, or Community Page.
    """
    CATEGORY_COMMUNITY = 'community'
    CATEGORY_CREATOR = 'creator'
    CATEGORY_TECH = 'technology'
    CATEGORY_BUSINESS = 'business'
    CATEGORY_EDUCATION = 'education'

    CATEGORY_CHOICES = [
        (CATEGORY_COMMUNITY, _('Community / Club')),
        (CATEGORY_CREATOR, _('Creator / Artist')),
        (CATEGORY_TECH, _('Tech & Open Source')),
        (CATEGORY_BUSINESS, _('Business & Brand')),
        (CATEGORY_EDUCATION, _('Education & Research')),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_pages'
    )
    name = models.CharField(_('name'), max_length=150)
    slug = models.SlugField(_('slug'), max_length=160, unique=True, db_index=True)
    category = models.CharField(_('category'), max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_COMMUNITY)
    description = models.TextField(_('description'), max_length=1000, blank=True)
    avatar = models.ImageField(
        _('avatar'),
        upload_to='pages/avatars/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    cover_image = models.ImageField(
        _('cover image'),
        upload_to='pages/covers/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "page"
            slug = base_slug
            counter = 1
            while Page.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def followers_count(self):
        return self.followers.count()

    def is_followed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.followers.filter(user=user).exists()


class PageFollower(models.Model):
    """
    Follower relationship for a Page.
    """
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='followers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_pages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['page', 'user'], name='unique_page_follower')
        ]

    def __str__(self):
        return f"@{self.user.username} follows Page '{self.page.name}'"
