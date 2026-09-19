"""
Comprehensive test suite for accounts, authentication, follow, and friendship systems.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, Follow, Friendship
from PIL import Image
import io


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'username': 'alice',
            'email': 'alice@example.com',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        }

    def test_user_registration_success(self):
        """User can successfully register with valid data and password is encrypted."""
        response = self.client.post(reverse('accounts:register'), self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='alice').exists())
        
        user = User.objects.get(username='alice')
        self.assertEqual(user.email, 'alice@example.com')
        self.assertNotEqual(user.password, 'SecurePassword123!')  # Must be hashed
        self.assertTrue(user.check_password('SecurePassword123!'))

    def test_registration_duplicate_username_fails(self):
        """Registration fails if username already taken."""
        User.objects.create_user(username='alice', email='existing@example.com', password='Password123!')
        response = self.client.post(reverse('accounts:register'), self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'A user with this username already exists.')

    def test_registration_duplicate_email_fails(self):
        """Registration fails if email already registered."""
        User.objects.create_user(username='other', email='alice@example.com', password='Password123!')
        response = self.client.post(reverse('accounts:register'), self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'An account with this email address already exists.')

    def test_registration_password_mismatch(self):
        """Registration fails if password confirmation does not match."""
        bad_data = self.user_data.copy()
        bad_data['password_confirm'] = 'DifferentPassword123!'
        response = self.client.post(reverse('accounts:register'), bad_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'password_confirm', 'Passwords do not match.')

    def test_user_login_and_logout(self):
        """User can log in and out successfully."""
        user = User.objects.create_user(username='bob', email='bob@example.com', password='BobPassword123!')
        login_res = self.client.post(reverse('accounts:login'), {
            'username': 'bob',
            'password': 'BobPassword123!'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

        logout_res = self.client.get(reverse('accounts:logout'))
        self.assertEqual(logout_res.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)


class RelationshipsSystemTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='carol', email='carol@example.com', password='Password123!')
        self.user2 = User.objects.create_user(username='dave', email='dave@example.com', password='Password123!')
        self.client = Client()
        self.client.force_login(self.user1)

    def test_follow_and_unfollow(self):
        """User can follow and unfollow another user."""
        follow_url = reverse('accounts:follow_toggle', kwargs={'username': self.user2.username})
        
        # Follow
        res1 = self.client.post(follow_url)
        self.assertEqual(res1.status_code, 302)
        self.assertTrue(self.user1.is_following(self.user2))
        self.assertEqual(self.user2.followers_count(), 1)
        self.assertEqual(self.user1.following_count(), 1)

        # Unfollow
        res2 = self.client.post(follow_url)
        self.assertEqual(res2.status_code, 302)
        self.assertFalse(self.user1.is_following(self.user2))
        self.assertEqual(self.user2.followers_count(), 0)

    def test_prevent_self_follow(self):
        """User cannot follow themselves (enforced at view and database level)."""
        self_follow_url = reverse('accounts:follow_toggle', kwargs={'username': self.user1.username})
        res = self.client.post(self_follow_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(self.user1.is_following(self.user1))

        # DB level CheckConstraint
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=self.user1, following=self.user1)

    def test_friendship_request_cycle(self):
        """Full friend request cycle: send -> pending -> accept -> friends."""
        # 1. Carol sends request to Dave
        send_url = reverse('accounts:friend_request_send', kwargs={'username': self.user2.username})
        self.client.post(send_url)
        
        self.assertEqual(self.user1.get_friendship_status(self.user2), 'sent_pending')
        self.assertEqual(self.user2.get_friendship_status(self.user1), 'received_pending')

        # 2. Dave logs in and accepts
        self.client.force_login(self.user2)
        accept_url = reverse('accounts:friend_request_accept', kwargs={'username': self.user1.username})
        self.client.post(accept_url)

        self.assertTrue(self.user1.is_friends_with(self.user2))
        self.assertTrue(self.user2.is_friends_with(self.user1))
        self.assertEqual(self.user1.friends_count(), 1)
        self.assertEqual(self.user2.friends_count(), 1)

    def test_prevent_self_friend_request(self):
        """User cannot send a friend request to themselves."""
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(sender=self.user1, receiver=self.user1)

    def test_other_user_profile_renders_successfully(self):
        """Visiting another user's profile renders with follow/friend/message buttons without NoReverseMatch."""
        profile_url = reverse('accounts:profile', kwargs={'username': self.user2.username})
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "+ Follow")
        self.assertContains(response, "Add Friend")
        self.assertContains(response, "Message")


class ProfileImageUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='eve', email='eve@example.com', password='Password123!')
        self.client = Client()
        self.client.force_login(self.user)

    def _generate_test_image(self):
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(file, 'jpeg')
        file.name = 'test_avatar.jpg'
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type='image/jpeg')

    def test_profile_avatar_upload(self):
        """User can upload a valid image avatar."""
        avatar = self._generate_test_image()
        url = reverse('accounts:profile_edit')
        response = self.client.post(url, {
            'first_name': 'Eve',
            'last_name': 'Hacker',
            'bio': 'Software engineer and enthusiast',
            'location': 'New York',
            'profile_picture': avatar
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_picture))
        self.assertEqual(self.user.bio, 'Software engineer and enthusiast')
