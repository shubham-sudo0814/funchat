"""
Automated tests for Pages: Creation, slugs, and followers.
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from pages.models import Page, PageFollower


class PagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='creator', email='creator@test.com', password='Password123!')
        self.client = Client()
        self.client.force_login(self.user)

    def test_create_page(self):
        """User can create a page with auto-slug generation."""
        res = self.client.post(reverse('pages:create'), {
            'name': 'Python Developers Club',
            'category': Page.CATEGORY_TECH,
            'description': 'A community for Python devs.'
        })
        self.assertEqual(res.status_code, 302)

        page = Page.objects.filter(slug='python-developers-club').first()
        self.assertIsNotNone(page)
        self.assertEqual(page.owner, self.user)
        self.assertEqual(page.followers_count(), 1)  # Owner auto-follows

    def test_page_follow_toggle(self):
        """User can follow and unfollow a page."""
        page = Page.objects.create(
            owner=self.user,
            name='Open AI Hub',
            category=Page.CATEGORY_TECH
        )
        user2 = User.objects.create_user(username='follower', email='f@test.com', password='Password123!')
        client2 = Client()
        client2.force_login(user2)

        follow_url = reverse('pages:follow_toggle', kwargs={'slug': page.slug})

        # Follow
        res1 = client2.post(follow_url)
        self.assertEqual(res1.status_code, 302)
        self.assertTrue(page.is_followed_by(user2))

        # Unfollow
        res2 = client2.post(follow_url)
        self.assertEqual(res2.status_code, 302)
        self.assertFalse(page.is_followed_by(user2))
