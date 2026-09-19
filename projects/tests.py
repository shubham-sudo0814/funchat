"""
Automated tests for Projects: Showcase, tag filtering, and likes.
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from projects.models import Project, ProjectLike


class ProjectsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='builder', email='b@test.com', password='Password123!')
        self.client = Client()
        self.client.force_login(self.user)

    def test_publish_and_retrieve_project(self):
        """User can publish a project showcase with tags."""
        res = self.client.post(reverse('projects:create'), {
            'title': 'AI Social Engine',
            'summary': 'Next generation social platform with AI agents',
            'description': 'Built with Django, PostgreSQL, and Python.',
            'demo_url': 'https://demo.funchat.internal',
            'repo_url': 'https://github.com/funchat/engine',
            'tags': 'django, ai, postgresql'
        })
        self.assertEqual(res.status_code, 302)

        proj = Project.objects.filter(slug='ai-social-engine').first()
        self.assertIsNotNone(proj)
        self.assertEqual(proj.owner, self.user)
        self.assertEqual(proj.tag_list, ['django', 'ai', 'postgresql'])

    def test_project_upvote_toggle(self):
        """User can upvote and remove upvote from a project."""
        proj = Project.objects.create(
            owner=self.user,
            title='Fast Search Library',
            summary='Instant search across relational tables',
            description='Detailed docs...'
        )
        user2 = User.objects.create_user(username='voter', email='voter@test.com', password='Password123!')
        client2 = Client()
        client2.force_login(user2)

        like_url = reverse('projects:like_toggle', kwargs={'slug': proj.slug})

        # Upvote
        res1 = client2.post(like_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(proj.likes_count(), 1)
        self.assertTrue(proj.is_liked_by(user2))

        # Remove Upvote
        res2 = client2.post(like_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(proj.likes_count(), 0)
        self.assertFalse(proj.is_liked_by(user2))
