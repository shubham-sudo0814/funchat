"""
Projects forms.
"""

from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'summary', 'description', 'cover_image', 'demo_url', 'repo_url', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Title'}),
            'summary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'One-line summary (up to 250 chars)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Detailed overview, architecture, tech stack, and goals...'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'demo_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://your-demo.com'}),
            'repo_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username/repo'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'python, django, machine-learning, react'}),
        }
