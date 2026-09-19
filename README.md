# Funchat — Modern Social Networks 

Funchat is a full-featured, production-ready social networking platform built with **Django**, **PostgreSQL**, and **Django REST Framework**.

It incorporates user accounts, profiles, bidirectional friendships, directional follows, chronological feeds, image sharing, multi-reaction likes, threaded comments, bookmarks, reposts/shares, search, direct messaging, group conversations, actionable notifications, community pages, project showcase galleries, user moderation/reporting, and a complete **Telegram-style Bot Platform** with cryptographically secure, hashed API keys (`bot_live_...`), developer dashboards, rate limits, and HMAC-SHA256 signed webhooks.

---

## Key Architecture & Features

### 1. User Accounts & Relationships (`accounts`)
* Custom user model with avatars, bios, locations, and privacy modes.
* Strict validation, password strength requirements, and session authentication.
* Directional follow system with database-level self-follow prevention.
* Bidirectional friendship state machine (pending, accepted, rejected, unfriend).

### 2. Chronological Social Feed (`feed`)
* Post creation supporting text and validated image uploads (Pillow image verification).
* Reposts and content sharing without duplicating media storage.
* Multi-reaction system (Like, Love, Celebrate, Fire) with unique constraint per user+post.
* Threaded comment system with nested reply architecture.
* Bookmarks/Saved posts collection.
* Full-text and keyword search across users and posts.

### 3. Messaging & Group Conversations (`messaging`)
* 1-on-1 direct private chat with participant isolation and authorization barriers.
* Multi-user group conversations with custom group naming and admin roles.
* Low-latency client polling API (`/messages/<id>/api/poll/`) for incoming messages.

### 4. Notifications (`notifications`)
* Real-time actionable notifications for likes, comments, follows, friend requests, and messages.
* Global navbar badge counter via context processor.
* "Mark all as read" acknowledgment.

### 5. Pages & Projects Showcase (`pages`, `projects`)
* Creator and organization community pages with custom slugs, categories, banners, and followers.
* Projects portfolio showcase with demo links, repository links, tags, and community upvotes.

### 6. Moderation & Safety (`moderation`)
* Bidirectional user blocking (immediately severs relationships and prevents messaging).
* Content reporting pipeline for spam, harassment, hate speech, and copyright violations.

### 7. Bot Platform (`bots` — Section 49)
* **Bot Model**: Name, unique username (e.g. `@study_buddy_bot`), avatar, description, permissions.
* **Hashed API Keys**: Cryptographically secure keys (`bot_live_...`). Stored solely as SHA-256 hashes. Displayed **once** upon generation and masked thereafter (`bot_live_••••••••••••abcd`).
* **Bot Authentication**: Custom DRF `BotAPIKeyAuthentication` validating `Authorization: Bearer bot_live_...` with active status, expiration, and last-used tracking.
* **Developer Dashboard**: Web UI to create bots, generate/rotate/revoke keys, register slash commands (`/start`, `/help`), and configure webhooks.
* **Messaging API**: `POST /api/v1/bots/messages/send` allowing automated messaging and bot command dispatching.
* **Signed Webhooks**: Real-time event notifications sent with `X-Funchat-Bot-Signature: sha256=<hmac>` and `X-Funchat-Timestamp` headers for replay protection.
* **Rate Limiting**: Throttled at 120 requests/minute per bot with HTTP 429 status.
* **Interactive Docs**: Built-in developer documentation with cURL, Python, and JavaScript snippets at `/bots/docs/`.

---

## Getting Started

### 1. Environment Configuration
Create a `.env` file from `.env.example`:
```env
DJANGO_SECRET_KEY=your-secure-random-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.postgresql
DB_NAME=funchat_db
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

### 2. Activate Virtual Environment & Install Dependencies
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Apply PostgreSQL Database Migrations
```bash
python manage.py migrate
```

### 4. Seed Initial Test Personas & Content
```bash
python manage.py seed_data
```
*Creates 10 test users (e.g. `alex_dev`, `sarah_ui`, `marcus_ai`) with default password `Pass1234!`.*

### 5. Run Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Open **http://127.0.0.1:8000** in your browser.

---

## Running Automated Tests

Run the complete 42-test automated verification suite across all apps on PostgreSQL:
```bash
python manage.py test
```
Or test specific subsystems:
```bash
python manage.py test accounts
python manage.py test feed
python manage.py test messaging
python manage.py test bots
```
