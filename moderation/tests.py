"""
Automated tests for Moderation: User blocking and content reporting.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from accounts.models import User, Follow, Friendship
from moderation.models import Block, Report


class ModerationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='victor', email='v@test.com', password='Password123!')
        self.user2 = User.objects.create_user(username='wendy', email='w@test.com', password='Password123!')
        self.client1 = Client()
        self.client1.force_login(self.user1)

    def test_block_user_severs_relationships(self):
        """Blocking a user severs follow and friendship relationships."""
        # Establish follow and friendship
        Follow.objects.create(follower=self.user1, following=self.user2)
        Friendship.objects.create(sender=self.user1, receiver=self.user2, status=Friendship.STATUS_ACCEPTED)

        self.assertTrue(self.user1.is_following(self.user2))
        self.assertTrue(self.user1.is_friends_with(self.user2))

        # Victor blocks Wendy
        block_url = reverse('moderation:block_toggle', kwargs={'username': self.user2.username})
        res = self.client1.post(block_url)
        self.assertEqual(res.status_code, 302)

        self.assertTrue(Block.objects.filter(blocker=self.user1, blocked_user=self.user2).exists())
        self.assertFalse(self.user1.is_following(self.user2))
        self.assertFalse(self.user1.is_friends_with(self.user2))

    def test_prevent_self_block(self):
        """User cannot block themselves."""
        with self.assertRaises(IntegrityError):
            Block.objects.create(blocker=self.user1, blocked_user=self.user1)

    def test_file_report(self):
        """User can submit a moderation report."""
        report_url = reverse('moderation:report')
        res = self.client1.post(report_url, {
            'target_type': 'user',
            'target_id': self.user2.id,
            'reason': Report.REASON_SPAM,
            'details': 'Sending spam messages'
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Report.objects.filter(reporter=self.user1, target_id=self.user2.id).exists())
