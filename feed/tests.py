"""
Comprehensive test suite for Feed: Posts, Reactions, Comments, Bookmarks, Shares, and Search.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, Follow
from feed.models import Post, Reaction, Comment, SavedPost
from PIL import Image
import io


class FeedTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='u1@example.com', password='Password123!')
        self.user2 = User.objects.create_user(username='user2', email='u2@example.com', password='Password123!')
        self.client1 = Client()
        self.client1.force_login(self.user1)
        self.client2 = Client()
        self.client2.force_login(self.user2)

    def _generate_test_image(self):
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='green')
        image.save(file, 'jpeg')
        file.name = 'test_post.jpg'
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type='image/jpeg')

    def test_create_text_post(self):
        """User can create a text-only post."""
        res = self.client1.post(reverse('feed:post_create'), {'content': 'Hello Funchat!'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Post.objects.filter(author=self.user1).count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.content, 'Hello Funchat!')

    def test_create_image_post(self):
        """User can upload an image with a post."""
        img = self._generate_test_image()
        res = self.client1.post(reverse('feed:post_create'), {'content': 'Photo post', 'image': img})
        self.assertEqual(res.status_code, 302)
        post = Post.objects.first()
        self.assertTrue(bool(post.image))

    def test_empty_post_rejected(self):
        """A post with neither content nor image is rejected."""
        res = self.client1.post(reverse('feed:post_create'), {'content': ''})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Post.objects.count(), 0)

    def test_post_ownership_protection_edit(self):
        """User cannot edit another user's post (403 Forbidden)."""
        post = Post.objects.create(author=self.user1, content="Original")
        res = self.client2.post(reverse('feed:post_edit', kwargs={'pk': post.pk}), {'content': 'Hacked!'})
        self.assertEqual(res.status_code, 403)
        post.refresh_from_db()
        self.assertEqual(post.content, "Original")

    def test_post_ownership_protection_delete(self):
        """User cannot delete another user's post (403 Forbidden)."""
        post = Post.objects.create(author=self.user1, content="Protected")
        res = self.client2.post(reverse('feed:post_delete', kwargs={'pk': post.pk}))
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_reactions_toggle_and_uniqueness(self):
        """User can like and unlike a post; duplicate reactions are prevented."""
        post = Post.objects.create(author=self.user1, content="React to me")
        react_url = reverse('feed:post_react', kwargs={'pk': post.pk})

        # 1. Like
        res1 = self.client2.post(react_url, {'reaction_type': 'LIKE'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(post.reactions.count(), 1)
        self.assertTrue(post.is_reacted_by(self.user2))

        # 2. Unlike (clicking same reaction again)
        res2 = self.client2.post(react_url, {'reaction_type': 'LIKE'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(post.reactions.count(), 0)
        self.assertFalse(post.is_reacted_by(self.user2))

    def test_comment_system_and_permissions(self):
        """Users can comment, and only authorized users can delete comments."""
        post = Post.objects.create(author=self.user1, content="Discussion")
        comment_url = reverse('feed:comment_create', kwargs={'pk': post.pk})

        # Add comment
        self.client2.post(comment_url, {'content': 'Great post!'})
        self.assertEqual(post.comments.count(), 1)
        comment = post.comments.first()
        self.assertEqual(comment.content, 'Great post!')

        # User 3 attempts to delete User 2's comment -> 403
        user3 = User.objects.create_user(username='user3', email='u3@example.com', password='Password123!')
        client3 = Client()
        client3.force_login(user3)
        del_res = client3.post(reverse('feed:comment_delete', kwargs={'pk': comment.pk}))
        self.assertEqual(del_res.status_code, 403)

        # Comment author can delete
        del_res2 = self.client2.post(reverse('feed:comment_delete', kwargs={'pk': comment.pk}))
        self.assertEqual(del_res2.status_code, 302)
        self.assertEqual(post.comments.count(), 0)

    def test_save_post_bookmarks(self):
        """User can bookmark/save and un-bookmark a post."""
        post = Post.objects.create(author=self.user1, content="Bookmarking this")
        save_url = reverse('feed:post_save', kwargs={'pk': post.pk})

        # Save
        self.client2.post(save_url)
        self.assertTrue(post.is_saved_by(self.user2))

        # Unsave
        self.client2.post(save_url)
        self.assertFalse(post.is_saved_by(self.user2))

    def test_share_post(self):
        """User can share / repost content."""
        original = Post.objects.create(author=self.user1, content="Original Thought")
        share_url = reverse('feed:post_share', kwargs={'pk': original.pk})

        self.client2.post(share_url, {'content': 'Check this out!'})
        shared_post = Post.objects.filter(author=self.user2, shared_from=original).first()
        self.assertIsNotNone(shared_post)
        self.assertEqual(shared_post.content, 'Check this out!')
        self.assertEqual(original.shares_count, 1)

    def test_search_users_and_posts(self):
        """Search returns matching users and posts."""
        post = Post.objects.create(author=self.user1, content="Exciting news about artificial intelligence")
        search_url = reverse('feed:search')

        res = self.client1.get(search_url, {'q': 'artificial'})
        self.assertEqual(res.status_code, 200)
        self.assertIn(post, res.context['posts'])

        res_user = self.client1.get(search_url, {'q': 'user2'})
        self.assertEqual(res_user.status_code, 200)
        self.assertIn(self.user2, res_user.context['users'])
