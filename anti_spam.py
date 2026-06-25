import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class AntiSpam:
    def __init__(self, bot, settings: dict):
        self.bot = bot
        self.enabled = True
        self.settings = settings

        # Track messages per user
        self.user_messages = defaultdict(list)
        self.muted_users = {}

        # Configuration
        self.max_messages = settings.get('max_messages', 5)  # Max messages in time window
        self.time_window = settings.get('time_window', 10)  # Time window in seconds
        self.mute_duration = settings.get('mute_duration', 60)  # Mute duration in seconds

        # Whitelist (channels that are exempt from spam check)
        self.whitelist_channels = set()
        self.whitelist_users = set()

    async def check_spam(self, message: discord.Message) -> bool:
        """Check if message is spam and take action"""
        if not self.enabled:
            return False

        # Ignore bots
        if message.author.bot:
            return False

        # Check whitelist
        if message.author.id in self.whitelist_users:
            return False

        if message.channel.id in self.whitelist_channels:
            return False

        # Check if user is muted
        if message.author.id in self.muted_users:
            if datetime.now() < self.muted_users[message.author.id]:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} أنت مقيّد مؤقتاً!",
                    delete_after=5
                )
                return True
            else:
                # Unmute
                del self.muted_users[message.author.id]

        # Get user's message history
        user_id = message.author.id
        current_time = datetime.now()

        # Clean old messages
        self.user_messages[user_id] = [
            msg_time for msg_time in self.user_messages[user_id]
            if current_time - msg_time < timedelta(seconds=self.time_window)
        ]

        # Add current message
        self.user_messages[user_id].append(current_time)

        # Check if spam
        if len(self.user_messages[user_id]) > self.max_messages:
            await self.handle_spam(message)
            return True

        return False

    async def handle_spam(self, message: discord.Message):
        """Handle spam detected"""
        # Delete the spam message
        try:
            await message.delete()
        except:
            pass

        # Send warning
        warning = await message.channel.send(
            f"⚠️ {message.author.mention} تم اكتشاف سبام!",
            delete_after=5
        )

        # Mute the user temporarily
        self.muted_users[message.author.id] = datetime.now() + timedelta(seconds=self.mute_duration)

        # Log the spam
        try:
            with open('spam_logs.txt', 'a', encoding='utf-8') as f:
                f.write(
                    f"[{datetime.now()}] SPAM: {message.author} ({message.author.id}) "
                    f"in #{message.channel}: {message.content[:100]}\n"
                )
        except:
            pass

        # Try to timeout the user
        try:
            if hasattr(message.author, 'timed_out_until'):
                await message.author.edit(
                    timed_out_until=datetime.now() + timedelta(seconds=self.mute_duration),
                    reason="سبام"
                )
        except discord.Forbidden:
            pass

    def add_whitelist_user(self, user_id: int):
        """Add user to whitelist"""
        self.whitelist_users.add(user_id)

    def remove_whitelist_user(self, user_id: int):
        """Remove user from whitelist"""
        self.whitelist_users.discard(user_id)

    def add_whitelist_channel(self, channel_id: int):
        """Add channel to whitelist"""
        self.whitelist_channels.add(channel_id)

    def remove_whitelist_channel(self, channel_id: int):
        """Remove channel from whitelist"""
        self.whitelist_channels.discard(channel_id)

    def get_spam_count(self, user_id: int) -> int:
        """Get current message count for user"""
        return len(self.user_messages.get(user_id, []))

    def clear_user_history(self, user_id: int):
        """Clear message history for user"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]

    async def unmute_user(self, user_id: int):
        """Manually unmute a user"""
        if user_id in self.muted_users:
            del self.muted_users[user_id]

        self.clear_user_history(user_id)

    def get_stats(self) -> dict:
        """Get spam statistics"""
        return {
            'tracked_users': len(self.user_messages),
            'muted_users': len(self.muted_users),
            'whitelist_users': len(self.whitelist_users),
            'whitelist_channels': len(self.whitelist_channels),
            'settings': {
                'max_messages': self.max_messages,
                'time_window': self.time_window,
                'mute_duration': self.mute_duration
            }
        }
