"""
Automated tests for Messaging: Direct chats, group chats, isolation, and polling API.
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from messaging.models import Conversation, ConversationParticipant, Message


class MessagingTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='alice', email='a@test.com', password='Password123!')
        self.user_b = User.objects.create_user(username='bob', email='b@test.com', password='Password123!')
        self.user_c = User.objects.create_user(username='charlie', email='c@test.com', password='Password123!')

        self.client_a = Client()
        self.client_a.force_login(self.user_a)

        self.client_c = Client()
        self.client_c.force_login(self.user_c)

    def test_direct_chat_creation_and_messaging(self):
        """Users can initiate a 1-on-1 direct chat and exchange messages."""
        # Alice initiates direct chat with Bob
        res = self.client_a.get(reverse('messaging:direct_chat', kwargs={'username': self.user_b.username}))
        self.assertEqual(res.status_code, 302)

        convo = Conversation.objects.filter(is_group=False).first()
        self.assertIsNotNone(convo)
        self.assertEqual(convo.participants.count(), 2)

        # Alice sends a message
        send_url = reverse('messaging:send_message', kwargs={'conversation_id': convo.id})
        send_res = self.client_a.post(send_url, {'text': 'Hey Bob!'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(send_res.status_code, 200)
        self.assertEqual(convo.messages.count(), 1)
        self.assertEqual(convo.messages.first().text, 'Hey Bob!')

    def test_conversation_isolation(self):
        """User C cannot view or send messages to a private conversation between A and B (403 Forbidden)."""
        convo, _ = Conversation.get_or_create_direct(self.user_a, self.user_b)

        # Charlie tries to view the chat
        view_url = reverse('messaging:conversation_detail', kwargs={'conversation_id': convo.id})
        res = self.client_c.get(view_url)
        self.assertEqual(res.status_code, 403)

        # Charlie tries to post a message
        send_url = reverse('messaging:send_message', kwargs={'conversation_id': convo.id})
        post_res = self.client_c.post(send_url, {'text': 'Intruder message!'})
        self.assertEqual(post_res.status_code, 400)

    def test_polling_api(self):
        """API poll returns new messages since specified ID."""
        convo, _ = Conversation.get_or_create_direct(self.user_a, self.user_b)
        m1 = Message.objects.create(conversation=convo, sender=self.user_a, text='Msg 1')
        m2 = Message.objects.create(conversation=convo, sender=self.user_b, text='Msg 2')

        poll_url = reverse('messaging:api_fetch_messages', kwargs={'conversation_id': convo.id})
        res = self.client_a.get(poll_url, {'since_id': m1.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['text'], 'Msg 2')

    def test_create_group_conversation(self):
        """User can create a multi-user group chat."""
        create_url = reverse('messaging:create_group')
        res = self.client_a.post(create_url, {
            'title': 'Core Dev Team',
            'members': [self.user_b.id, self.user_c.id]
        })
        self.assertEqual(res.status_code, 302)

        group = Conversation.objects.filter(is_group=True, title='Core Dev Team').first()
        self.assertIsNotNone(group)
        self.assertEqual(group.participants.count(), 3)
