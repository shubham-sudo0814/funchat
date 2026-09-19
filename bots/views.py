"""
Bot Developer Dashboard Views (Section 49.14 & 49.15).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import Bot, BotAPIKey, BotCommand, BotWebhook
from .forms import BotCreateForm, BotWebhookForm, BotCommandForm


@login_required
def bot_dashboard_view(request):
    """
    Developer Dashboard: Lists all bots owned by the user.
    """
    bots = Bot.objects.filter(owner=request.user).prefetch_related('api_keys', 'commands')
    return render(request, 'bots/dashboard.html', {'bots': bots})


@login_required
def bot_create_view(request):
    """
    Create a new Telegram-style bot.
    """
    if request.method == 'POST':
        form = BotCreateForm(request.POST, request.FILES)
        if form.is_valid():
            bot = form.save(commit=False)
            bot.owner = request.user
            bot.save()

            # Automatically generate an initial API key
            key_instance, raw_key = BotAPIKey.generate(bot, name="Initial Live Key")

            # Store the raw key in user's session flash storage so it's shown ONCE
            request.session['just_created_bot_key'] = {
                'bot_name': bot.name,
                'key_name': key_instance.name,
                'raw_key': raw_key,
            }

            messages.success(request, f"Bot @{bot.username} created! Please copy your API key now.")
            return redirect('bots:detail', bot_id=bot.id)
    else:
        form = BotCreateForm()

    return render(request, 'bots/create.html', {'form': form})


@login_required
def bot_detail_view(request, bot_id):
    """
    Bot Detail Dashboard: API Keys, Webhook Settings, Commands, and Permissions.
    """
    bot = get_object_or_404(Bot, id=bot_id)
    if bot.owner != request.user:
        raise PermissionDenied("You do not own this bot.")

    # Retrieve one-time raw key from session if present
    one_time_key = request.session.pop('just_created_bot_key', None)

    api_keys = bot.api_keys.all().order_by('-created_at')
    commands = bot.commands.all()
    
    webhook = getattr(bot, 'webhook', None)
    webhook_form = BotWebhookForm(instance=webhook) if webhook else BotWebhookForm()

    context = {
        'bot': bot,
        'api_keys': api_keys,
        'commands': commands,
        'webhook': webhook,
        'webhook_form': webhook_form,
        'command_form': BotCommandForm(),
        'one_time_key': one_time_key,
    }
    return render(request, 'bots/detail.html', context)


@login_required
@require_POST
def bot_key_generate_view(request, bot_id):
    """
    Generate an additional API key for the bot.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    key_name = request.POST.get('name', '').strip() or 'Live API Key'

    key_instance, raw_key = BotAPIKey.generate(bot, name=key_name)
    request.session['just_created_bot_key'] = {
        'bot_name': bot.name,
        'key_name': key_instance.name,
        'raw_key': raw_key,
    }

    messages.success(request, "New API key generated. Save it now, it will not be displayed again.")
    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_key_revoke_view(request, bot_id, key_id):
    """
    Revoke an active API key immediately.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    key = get_object_or_404(BotAPIKey, id=key_id, bot=bot)
    key.is_active = False
    key.save(update_fields=['is_active'])

    messages.warning(request, f"API key '{key.name}' ({key.masked_key}) has been revoked.")
    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_key_rotate_view(request, bot_id, key_id):
    """
    Rotate an API key: Revokes the old key and generates a new active key.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    old_key = get_object_or_404(BotAPIKey, id=key_id, bot=bot)

    # 1. Revoke old key
    old_key.is_active = False
    old_key.save(update_fields=['is_active'])

    # 2. Generate replacement key
    key_name = f"{old_key.name} (Rotated)"
    new_key, raw_key = BotAPIKey.generate(bot, name=key_name)

    request.session['just_created_bot_key'] = {
        'bot_name': bot.name,
        'key_name': new_key.name,
        'raw_key': raw_key,
    }

    messages.success(request, f"Key rotated! New key generated for @{bot.username}.")
    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_command_add_view(request, bot_id):
    """
    Register a new slash command for the bot (e.g. /help, /start).
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    form = BotCommandForm(request.POST)

    if form.is_valid():
        cmd = form.save(commit=False)
        cmd.bot = bot
        # Ensure command starts with /
        if not cmd.command.startswith('/'):
            cmd.command = f"/{cmd.command}"
        cmd.save()
        messages.success(request, f"Command {cmd.command} registered.")
    else:
        messages.error(request, "Invalid command name or already registered.")

    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_command_delete_view(request, bot_id, cmd_id):
    """
    Delete a registered command.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    cmd = get_object_or_404(BotCommand, id=cmd_id, bot=bot)
    cmd.delete()
    messages.info(request, "Command deleted.")
    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_webhook_save_view(request, bot_id):
    """
    Save or update webhook callback URL and secret.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    url = request.POST.get('url', '').strip()

    if not url:
        # If blank, remove existing webhook
        if hasattr(bot, 'webhook'):
            bot.webhook.delete()
            messages.info(request, "Webhook disabled.")
        return redirect('bots:detail', bot_id=bot.id)

    webhook, created = BotWebhook.objects.get_or_create(bot=bot)
    webhook.url = url
    webhook.is_active = True
    webhook.failure_count = 0
    if not webhook.secret:
        webhook.secret = BotWebhook.generate_secret()
    webhook.save()

    messages.success(request, "Webhook configuration saved.")
    return redirect('bots:detail', bot_id=bot.id)


@login_required
@require_POST
def bot_delete_view(request, bot_id):
    """
    Delete bot and all its associated API keys and commands.
    """
    bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
    username = bot.username
    bot.delete()
    messages.info(request, f"Bot @{username} and its API keys have been deleted.")
    return redirect('bots:dashboard')


@login_required
def bot_docs_view(request):
    """
    Developer Documentation page for Bot Platform (Section 49.13).
    """
    return render(request, 'bots/docs.html')
