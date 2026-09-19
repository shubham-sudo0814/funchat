"""
Seed data command for 10 initial test users and sample interactions.
Run via: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from accounts.models import User, Follow, Friendship
from feed.models import Post, Reaction, Comment
from messaging.models import Conversation, ConversationParticipant, Message
from pages.models import Page, PageFollower
from projects.models import Project
from bots.models import Bot, BotAPIKey, BotCommand


class Command(BaseCommand):
    help = 'Seeds 10 test users and rich social content'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Funchat database...")

        # 1. Test Users (10 test users)
        users_data = [
            {'username': 'alex_dev', 'first_name': 'Alex', 'last_name': 'Rivera', 'email': 'alex@funchat.internal', 'bio': 'Full-stack software architect & open source contributor.', 'location': 'San Francisco, CA'},
            {'username': 'sarah_ui', 'first_name': 'Sarah', 'last_name': 'Chen', 'email': 'sarah@funchat.internal', 'bio': 'Product designer obsessed with sleek UX and design systems.', 'location': 'Seattle, WA'},
            {'username': 'marcus_ai', 'first_name': 'Marcus', 'last_name': 'Vance', 'email': 'marcus@funchat.internal', 'bio': 'Researching LLM agents, memory, and cognitive architectures.', 'location': 'Boston, MA'},
            {'username': 'elena_code', 'first_name': 'Elena', 'last_name': 'Rostova', 'email': 'elena@funchat.internal', 'bio': 'Distributed systems engineer. Writing high-throughput Go & Rust.', 'location': 'Berlin, Germany'},
            {'username': 'david_k', 'first_name': 'David', 'last_name': 'Kim', 'email': 'david@funchat.internal', 'bio': 'Mobile developer crafting cross-platform experiences.', 'location': 'Toronto, Canada'},
            {'username': 'priya_tech', 'first_name': 'Priya', 'last_name': 'Sharma', 'email': 'priya@funchat.internal', 'bio': 'Cybersecurity specialist, ethical hacker, and privacy advocate.', 'location': 'Austin, TX'},
            {'username': 'leo_maker', 'first_name': 'Leo', 'last_name': 'Silva', 'email': 'leo@funchat.internal', 'bio': 'Hardware hacker, IoT builder, and 3D printing enthusiast.', 'location': 'London, UK'},
            {'username': 'hannah_writer', 'first_name': 'Hannah', 'last_name': 'Abbott', 'email': 'hannah@funchat.internal', 'bio': 'Tech writer documenting the next wave of developer tooling.', 'location': 'Denver, CO'},
            {'username': 'omar_data', 'first_name': 'Omar', 'last_name': 'Farooq', 'email': 'omar@funchat.internal', 'bio': 'Data engineer wrangling petabyte pipelines with Apache Spark.', 'location': 'Chicago, IL'},
            {'username': 'chloe_art', 'first_name': 'Chloe', 'last_name': 'Dubois', 'email': 'chloe@funchat.internal', 'bio': 'Digital artist and generative UI visualizer.', 'location': 'Paris, France'},
        ]

        users = {}
        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'bio': data['bio'],
                    'location': data['location'],
                }
            )
            user.set_password('Pass1234!')
            user.save()
            users[data['username']] = user

        self.stdout.write(f"Created/Updated {len(users)} test users with password 'Pass1234!'.")

        # 2. Follows & Friendships
        Follow.objects.get_or_create(follower=users['alex_dev'], following=users['sarah_ui'])
        Follow.objects.get_or_create(follower=users['alex_dev'], following=users['marcus_ai'])
        Follow.objects.get_or_create(follower=users['sarah_ui'], following=users['alex_dev'])
        Follow.objects.get_or_create(follower=users['marcus_ai'], following=users['alex_dev'])
        Follow.objects.get_or_create(follower=users['elena_code'], following=users['alex_dev'])

        Friendship.objects.get_or_create(sender=users['alex_dev'], receiver=users['sarah_ui'], defaults={'status': Friendship.STATUS_ACCEPTED})
        Friendship.objects.get_or_create(sender=users['alex_dev'], receiver=users['marcus_ai'], defaults={'status': Friendship.STATUS_ACCEPTED})

        # 3. Sample Posts
        posts_data = [
            (users['alex_dev'], "Excited to share that Funchat is officially live! Built with clean Django architecture, PostgreSQL, and modern responsive styling. Connect, build, and have fun! 🚀"),
            (users['sarah_ui'], "Designing interfaces that feel like natural extensions of thought is the ultimate goal. Loving the responsive layout here! ✨"),
            (users['marcus_ai'], "Autonomous agents with long-term memory are changing pair programming forever. What architectures are you using in production? 🤖"),
            (users['elena_code'], "Just deployed a new PostgreSQL sharding cluster. 99.99% uptime and sub-10ms query latency under load. Normalization pays off! ⚡"),
        ]

        for author, content in posts_data:
            post, _ = Post.objects.get_or_create(author=author, content=content)
            # Add reactions
            Reaction.objects.get_or_create(post=post, user=users['alex_dev'], defaults={'reaction_type': 'LIKE'})
            Reaction.objects.get_or_create(post=post, user=users['sarah_ui'], defaults={'reaction_type': 'LOVE'})
            # Add comments
            Comment.objects.get_or_create(post=post, author=users['priya_tech'], defaults={'content': 'Congratulations on the launch! Clean and responsive.'})

        # 4. Sample Page
        page, _ = Page.objects.get_or_create(
            slug='open-source-guild',
            defaults={
                'owner': users['alex_dev'],
                'name': 'Open Source Guild',
                'category': Page.CATEGORY_TECH,
                'description': 'A global community of developers building open, transparent, and user-first tools.'
            }
        )
        PageFollower.objects.get_or_create(page=page, user=users['sarah_ui'])
        PageFollower.objects.get_or_create(page=page, user=users['marcus_ai'])

        # 5. Sample Project
        Project.objects.get_or_create(
            slug='autonomous-drone-pilot',
            defaults={
                'owner': users['leo_maker'],
                'title': 'Autonomous Drone Pilot',
                'summary': 'Edge-computing visual navigation system for low-altitude drones.',
                'description': 'Combines real-time computer vision with obstacle avoidance routines running on a Raspberry Pi 5 onboard compute unit.',
                'demo_url': 'https://example.com/drone-demo',
                'repo_url': 'https://github.com/funchat/drone-pilot',
                'tags': 'robotics, python, computer-vision, iot'
            }
        )

        # 6. Sample Telegram-Style Bot (Section 49)
        bot, _ = Bot.objects.get_or_create(
            username='@study_buddy_bot',
            defaults={
                'owner': users['alex_dev'],
                'name': 'Study Buddy Bot',
                'description': 'Automated study assistant and daily code quiz generator.'
            }
        )
        BotCommand.objects.get_or_create(bot=bot, command='/start', defaults={'description': 'Start interacting with Study Buddy'})
        BotCommand.objects.get_or_create(bot=bot, command='/help', defaults={'description': 'View available study commands'})
        BotCommand.objects.get_or_create(bot=bot, command='/quiz', defaults={'description': 'Get a daily programming challenge'})

        if not bot.api_keys.exists():
            _, raw_key = BotAPIKey.generate(bot, name='Production Live Key')
            self.stdout.write(f"Generated Demo Bot API Key for @study_buddy_bot: {raw_key}")

        self.stdout.write(self.style.SUCCESS("Funchat database successfully seeded with 10 test personas, feed posts, page, project, and bot!"))
