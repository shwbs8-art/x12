import discord
from datetime import datetime
from typing import Optional, List
import json
import os

class Logger:
    def __init__(self, bot):
        self.bot = bot
        self.enabled = True
        self.logs = []
        self.max_logs = 500

    async def get_log_channel(self) -> Optional[discord.TextChannel]:
        """Get the private log channel"""
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        channel_id = config.get('private_channel_id')
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    async def get_admin_channel(self) -> Optional[discord.TextChannel]:
        """Get the admin log channel (for sensitive actions)"""
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        channel_id = config.get('log_channel_id')
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    def add_log(self, log_type: str, message: str, details: str = ""):
        """Add a log entry"""
        log_entry = {
            'type': log_type,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.logs.append(log_entry)

        # Keep only recent logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

        return log_entry

    async def send_log(self, embed: discord.Embed, private: bool = False):
        """Send log to appropriate channel"""
        channel = await self.get_admin_channel() if private else await self.get_log_channel()
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"لا يمكن إرسال اللوق إلى {channel.name}")

    # ============ MESSAGE LOGS ============

    async def log_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if message.author.bot:
            return

        self.add_log('MESSAGE_DELETE', f"رسالة محذوفة", f"{message.author}: {message.content[:100]}")

        embed = discord.Embed(
            title="🗑️ رسالة محذوفة",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="المستخدم", value=message.author.mention, inline=True)
        embed.add_field(name="القناة", value=message.channel.mention, inline=True)

        if message.content:
            embed.add_field(name="المحتوى", value=message.content[:1024], inline=False)
        else:
            embed.add_field(name="المحتوى", value="(مرفق أو نص فارغ)", inline=False)

        if message.attachments:
            embed.add_field(name="المرفقات", value=f"{len(message.attachments)} مرفق(ات)", inline=True)

        await self.send_log(embed, private=True)

    async def log_message_edit(self, before: discord.Message, after: discord.Message):
        """Log edited messages"""
        if before.author.bot:
            return

        self.add_log('MESSAGE_EDIT', f"رسالة معدلة", f"{before.author}: {before.content[:50]} -> {after.content[:50]}")

        embed = discord.Embed(
            title="✏️ رسالة معدلة",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="المستخدم", value=before.author.mention, inline=True)
        embed.add_field(name="القناة", value=before.channel.mention, inline=True)
        embed.add_field(name="قبل", value=before.content[:1024], inline=False)
        embed.add_field(name="بعد", value=after.content[:1024], inline=False)

        await self.send_log(embed, private=True)

    # ============ MEMBER LOGS ============

    async def log_member_join(self, member: discord.Member):
        """Log member join"""
        self.add_log('MEMBER_JOIN', f"دخول عضو جديد", str(member))

        embed = discord.Embed(
            title="👋 عضو جديد",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="العضو", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="تاريخ الإنشاء", value=member.created_at.strftime("%Y-%m-%d"), inline=True)

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        await self.send_log(embed, private=True)

    async def log_member_remove(self, member: discord.Member):
        """Log member leave"""
        self.add_log('MEMBER_LEAVE', f"مغادرة عضو", str(member))

        embed = discord.Embed(
            title="👋 مغادرة عضو",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="العضو", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)

        # Check if was kicked or left
        # (This would require additional tracking in a real implementation)

        await self.send_log(embed, private=True)

    async def log_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates"""
        changes = []

        if before.nick != after.nick:
            changes.append(f"اللقب: {before.nick} -> {after.nick}")

        if before.roles != after.roles:
            removed = set(before.roles) - set(after.roles)
            added = set(after.roles) - set(before.roles)

            if removed:
                changes.append(f"رتبRemoved: {[r.name for r in removed]}")
            if added:
                changes.append(f"رتبAdded: {[r.name for r in added]}")

        if before.status != after.status:
            changes.append(f"الحالة: {before.status} -> {after.status}")

        if not changes:
            return

        self.add_log('MEMBER_UPDATE', f"تحديث عضو", "; ".join(changes))

        embed = discord.Embed(
            title="👤 تحديث عضو",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="العضو", value=after.mention, inline=True)
        embed.add_field(name="التغييرات", value="\n".join(changes), inline=False)

        await self.send_log(embed, private=True)

    # ============ VOICE LOGS ============

    async def log_voice_state(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Log voice state changes"""
        actions = []

        if not before.channel and after.channel:
            actions.append(f"دخل {after.channel.name}")
        elif before.channel and not after.channel:
            actions.append(f"غادر {before.channel.name}")
        elif before.channel != after.channel:
            actions.append(f"انتقل من {before.channel.name} إلى {after.channel.name}")

        if before.mute != after.mute:
            actions.append("تم كتم الصوت" if after.mute else "تم إلغاء كتم الصوت")

        if before.deaf != after.deaf:
            actions.append("تم تعطيل الصوت" if after.deaf else "تم تفعيل الصوت")

        if before.self_mute != after.self_mute:
            actions.append("كتم نفسه" if after.self_mute else "ألغى كتم نفسه")

        if not actions:
            return

        self.add_log('VOICE', f"صوت", f"{member}: {'; '.join(actions)}")

        embed = discord.Embed(
            title="🎤 تحديث صوتي",
            color=discord.Color.dark_blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="العضو", value=member.mention, inline=True)
        embed.add_field(name="الإجراء", value="\n".join(actions), inline=False)

        await self.send_log(embed)

    # ============ CHANNEL LOGS ============

    async def log_channel_create(self, channel: discord.abc.GuildChannel):
        """Log channel creation"""
        self.add_log('CHANNEL_CREATE', f"قناة جديدة", f"{channel.name} ({channel.type})")

        embed = discord.Embed(
            title="📁 قناة جديدة",
            color=discord.Color.teal(),
            timestamp=datetime.now()
        )
        embed.add_field(name="القناة", value=channel.name, inline=True)
        embed.add_field(name="النوع", value=str(channel.type), inline=True)
        embed.add_field(name="الفئة", value=channel.category.name if channel.category else "بدون فئة", inline=True)

        await self.send_log(embed, private=True)

    async def log_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log channel deletion"""
        self.add_log('CHANNEL_DELETE', f"قناة محذوفة", channel.name)

        embed = discord.Embed(
            title="📁 قناة محذوفة",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="القناة", value=channel.name, inline=True)
        embed.add_field(name="النوع", value=str(channel.type), inline=True)

        await self.send_log(embed, private=True)

    async def log_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Log channel updates"""
        changes = []

        if before.name != after.name:
            changes.append(f"الاسم: {before.name} -> {after.name}")

        if isinstance(before, discord.TextChannel):
            if before.topic != after.topic:
                changes.append(f"الموضوع تغير")
            if before.slowmode_delay != after.slowmode_delay:
                changes.append(f"بطء الرسائل: {before.slowmode_delay}s -> {after.slowmode_delay}s")

        if not changes:
            return

        self.add_log('CHANNEL_UPDATE', f"قناة محدثة", "; ".join(changes))

        embed = discord.Embed(
            title="📁 تحديث قناة",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="القناة", value=after.mention, inline=True)
        embed.add_field(name="التغييرات", value="\n".join(changes), inline=False)

        await self.send_log(embed, private=True)

    # ============ ROLE LOGS ============

    async def log_role_create(self, role: discord.Role):
        """Log role creation"""
        self.add_log('ROLE_CREATE', f"رتبة جديدة", role.name)

        embed = discord.Embed(
            title="🎭 رتبة جديدة",
            color=discord.Color.dark_green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الرتبة", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="اللون", value=str(role.color), inline=True)
        embed.add_field(name="الصلاحيات", value=str(role.permissions.value), inline=True)

        await self.send_log(embed, private=True)

    async def log_role_delete(self, role: discord.Role):
        """Log role deletion"""
        self.add_log('ROLE_DELETE', f"رتبة محذوفة", role.name)

        embed = discord.Embed(
            title="🎭 رتبة محذوفة",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الرتبة", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)

        await self.send_log(embed, private=True)

    async def log_role_update(self, before: discord.Role, after: discord.Role):
        """Log role updates"""
        changes = []

        if before.name != after.name:
            changes.append(f"الاسم: {before.name} -> {after.name}")
        if before.color != after.color:
            changes.append(f"اللون: {before.color} -> {after.color}")
        if before.permissions != after.permissions:
            changes.append("الصلاحيات تغيرت")

        if not changes:
            return

        self.add_log('ROLE_UPDATE', f"رتبة محدثة", "; ".join(changes))

        embed = discord.Embed(
            title="🎭 تحديث رتبة",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الرتبة", value=after.mention, inline=True)
        embed.add_field(name="التغييرات", value="\n".join(changes), inline=False)

        await self.send_log(embed, private=True)

    # ============ MODERATION LOGS ============

    async def log_ban(self, guild: discord.Guild, user: discord.User):
        """Log ban"""
        self.add_log('BAN', f"حظر", str(user))

        embed = discord.Embed(
            title="🔨 حظر",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="المستخدم", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)

        await self.send_log(embed, private=True)

    async def log_unban(self, guild: discord.Guild, user: discord.User):
        """Log unban"""
        self.add_log('UNBAN', f"إلغاء حظر", str(user))

        embed = discord.Embed(
            title="🔓 إلغاء حظر",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="المستخدم", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)

        await self.send_log(embed, private=True)

    async def log_invite_create(self, invite: discord.Invite):
        """Log invite creation"""
        self.add_log('INVITE', f"دعوة جديدة", invite.code)

        embed = discord.Embed(
            title="🔗 دعوة جديدة",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الكود", value=invite.code, inline=True)
        embed.add_field(name="بواسطة", value=invite.inviter if invite.inviter else "غير معروف", inline=True)
        embed.add_field(name="المستخدم", value=invite.target_user if invite.target_user else "بدون", inline=True)
        embed.add_field(name="أقصى استخدام", value=invite.max_uses if invite.max_uses else "∞", inline=True)

        await self.send_log(embed, private=True)

    async def log_action(self, moderator: discord.Member, action: str, reason: str = ""):
        """Log moderation actions"""
        self.add_log('MOD_ACTION', action, f"بواسطة {moderator}: {reason}")

        embed = discord.Embed(
            title=f"🛡️ إجراء إشرافي",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الإجراء", value=action, inline=True)
        embed.add_field(name="بواسطة", value=moderator.mention, inline=True)
        if reason:
            embed.add_field(name="السبب", value=reason, inline=False)

        await self.send_log(embed, private=True)

    async def log_error(self, error: str):
        """Log errors"""
        self.add_log('ERROR', "خطأ", error)

        embed = discord.Embed(
            title="❌ خطأ",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="الخطأ", value=error, inline=False)

        await self.send_log(embed, private=True)

    # ============ GET LOGS ============

    async def get_recent_logs(self, count: int = 50, embed: bool = False):
        """Get recent logs"""
        recent = self.logs[-count:]

        if not embed:
            lines = []
            for log in recent:
                lines.append(f"[{log['timestamp']}] [{log['type']}] {log['message']}")
            return "\n".join(lines)

        # Create embed
        embed_obj = discord.Embed(
            title="📜 السجلات الأخيرة",
            color=discord.Color.dark_gray(),
            timestamp=datetime.now()
        )

        log_text = []
        for log in recent:
            log_text.append(f"`[{log['type']}]` {log['message']}\n  └ {log['details'][:100]}")

        embed_obj.description = "\n".join(log_text[:25]) if log_text else "لا توجد سجلات"
        embed_obj.set_footer(text=f"عرض {min(count, len(recent))} من {len(self.logs)} سجل")

        return embed_obj
