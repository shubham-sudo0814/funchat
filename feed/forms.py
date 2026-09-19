"""
Feed forms: PostForm and CommentForm.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Post, Comment


class PostForm(forms.ModelForm):
    """
    Form for authoring and updating posts.
    """
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "What's on your mind? Share updates, ideas, or projects...",
                'maxlength': 2000,
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'post-image-input'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get('content') or '').strip()
        image = cleaned_data.get('image')

        if not content and not image:
            raise ValidationError("A post must contain either text content or an image.")

        if len(content) > 2000:
            raise ValidationError("Post text cannot exceed 2,000 characters.")

        return cleaned_data


class CommentForm(forms.ModelForm):
    """
    Form for adding a comment to a post.
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Write a comment...',
                'maxlength': 1000,
                'autocomplete': 'off',
            })
        }

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise ValidationError("Comment cannot be empty.")
        if len(content) > 1000:
            raise ValidationError("Comment cannot exceed 1,000 characters.")
        return content
