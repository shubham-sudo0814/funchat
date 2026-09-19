"""
Automated tests for the Notifications system.
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from notifications.models import Notification


class NotificationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='diana', email='d@test.com', password='Password123!')
        self.user2 = User.objects.create_user(username='edward', email='e@test.com', password='Password123!')
        self.client1 = Client()
        self.client1.force_login(self.user1)

    def test_notification_creation_and_mark_read(self):
        """Notification can be created and marked as read."""
        notif = Notification.objects.create(
            recipient=self.user1,
            actor=self.user2,
            verb="followed you",
            target_url=f"/accounts/profile/{self.user2.username}/"
        )
        self.assertFalse(notif.is_read)

        # View notification list
        res = self.client1.get(reverse('notifications:list'))
        self.assertEqual(res.status_code, 200)
        self.assertIn(notif, res.context['notifications'])

        # Read notification
        read_res = self.client1.get(reverse('notifications:read', kwargs={'pk': notif.pk}))
        self.assertEqual(read_res.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_read(self):
        """User can mark all unread notifications as read at once."""
        Notification.objects.create(recipient=self.user1, actor=self.user2, verb="liked your post")
        Notification.objects.create(recipient=self.user1, actor=self.user2, verb="commented on your post")

        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 2)

        res = self.client1.post(reverse('notifications:mark_all_read'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 0)
