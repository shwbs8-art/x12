import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import random

# Import modules
from logger_module import Logger
from anti_spam import AntiSpam
from permissions import PermissionManager

# Load configuration
def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

# Initialize bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

# Initialize modules
logger = Logger(bot)
anti_spam = AntiSpam(bot, config['anti_spam_settings'])
permissions = PermissionManager(bot, config.get('admin_role_id'))

# Auto wiggle task for staying active
@tasks.loop(seconds=config['auto_wiggle']['interval'])
async def auto_wiggle():
    """Move around to stay active and prevent timeout"""
    if not config['auto_wiggle']['enabled']:
        return

    try:
        # Random action: left, right, or jump
        actions = ['↔️', '↔️', '↔️', '⬆️']
        action = random.choice(actions)

        # Get bot's status channel if exists
        if config.get('private_channel_id'):
            channel = bot.get_channel(config['private_channel_id'])
            if channel:
                await channel.send(f"🔄 البوت نشط | الحركة: {action}")

        print(f"[AUTO-WIGGLE] Bot is active - {action}")
    except Exception as e:
        print(f"[AUTO-WIGGLE ERROR] {e}")

# ============ BOT EVENTS ============

@bot.event
async def on_ready():
    print(f"✅ البوت بدأ العمل: {bot.user}")
    print(f"📌 بادئة الأوامر: {config['prefix']}")

    # Start auto wiggle
    if config['auto_wiggle']['enabled']:
        auto_wiggle.start()

    # Set bot status
    await bot.change_presence(activity=discord.Game(name="حماية سيرفر Minecraft"))

@bot.event
async def on_message(message):
    """Handle messages and anti-spam"""
    # Ignore bot messages
    if message.author.bot:
        return

    # Check for spam
    if await anti_spam.check_spam(message):
        return

    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    """Log deleted messages"""
    await logger.log_message_delete(message)

@bot.event
async def on_message_edit(before, after):
    """Log edited messages"""
    await logger.log_message_edit(before, after)

@bot.event
async def on_member_join(member):
    """Log member join"""
    await logger.log_member_join(member)

@bot.event
async def on_member_remove(member):
    """Log member leave"""
    await logger.log_member_remove(member)

@bot.event
async def on_member_update(before, after):
    """Log member updates (roles, nicknames)"""
    await logger.log_member_update(before, after)

@bot.event
async def on_voice_state_update(member, before, after):
    """Log voice state changes"""
    await logger.log_voice_state(member, before, after)

@bot.event
async def on_channel_create(channel):
    """Log channel creation"""
    await logger.log_channel_create(channel)

@bot.event
async def on_channel_delete(channel):
    """Log channel deletion"""
    await logger.log_channel_delete(channel)

@bot.event
async def on_channel_update(before, after):
    """Log channel updates"""
    await logger.log_channel_update(before, after)

@bot.event
async def on_role_create(role):
    """Log role creation"""
    await logger.log_role_create(role)

@bot.event
async def on_role_delete(role):
    """Log role deletion"""
    await logger.log_role_delete(role)

@bot.event
async def on_role_update(before, after):
    """Log role updates"""
    await logger.log_role_update(before, after)

@bot.event
async def on_member_ban(guild, user):
    """Log bans"""
    await logger.log_ban(guild, user)

@bot.event
async def on_member_unban(guild, user):
    """Log unbans"""
    await logger.log_unban(guild, user)

@bot.event
async def on_invite_create(invite):
    """Log invite creation"""
    await logger.log_invite_create(invite)

# ============ COMMANDS ============

@bot.command(name='القائمة', aliases=['list', 'members', 'اعضاء'])
async def server_members(ctx):
    """عرض قائمة الأعضاء في السيرفر"""
    guild = ctx.guild

    # Create embed
    embed = discord.Embed(
        title=f"👥 أعضاء السيرفر: {guild.name}",
        color=discord.Color.green()
    )

    # Get all members
    members = guild.members
    online = [m for m in members if m.status != discord.Status.offline]
    offline = [m for m in members if m.status == discord.Status.offline]

    # Count by status
    status_counts = {
        '🟢 متصل': len([m for m in members if m.status == discord.Status.online]),
        '🟡 بعيد': len([m for m in members if m.status == discord.Status.idle]),
        '🔴 مشغول': len([m for m in members if m.status == discord.Status.do_not_disturb]),
        '⚫ غير متصل': len(offline)
    }

    # Add status summary
    status_text = "\n".join([f"{emoji} {count}" for emoji, count in status_counts.items()])
    embed.add_field(name="📊 الحالة", value=status_text, inline=False)
    embed.add_field(name="👤 الإجمالي", value=f"**{len(members)}** عضو", inline=True)
    embed.add_field(name="✅ متصلين", value=f"**{len(online)}**", inline=True)

    # List members by role
    embed.add_field(name="\n📋 قائمة الأعضاء:", value="\u200b", inline=False)

    # Sort members by role hierarchy
    sorted_members = sorted(members, key=lambda m: m.top_role.position, reverse=True)

    member_list = []
    for member in sorted_members[:50]:  # Limit to 50 for embed
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.do_not_disturb: "🔴",
            discord.Status.offline: "⚫"
        }.get(member.status, "⚫")

        roles = [r.mention for r in member.roles[1:] if r.name != '@everyone']
        role_text = " ".join(roles[:3]) if roles else ""

        member_list.append(f"{status_emoji} {member.mention} {role_text}")

    embed.description = "\n".join(member_list)

    if len(members) > 50:
        embed.set_footer(text=f"عرض 50 من {len(members)} عضو")

    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='الة', aliases=['server', 'ip'])
async def server_info(ctx):
    """عرض معلومات السيرفر"""
    guild = ctx.guild

    embed = discord.Embed(
        title=f"🎮 معلومات السيرفر",
        color=discord.Color.blue()
    )

    # Server info
    server_ip = config.get('main_guild_ip', 'غير محدد')
    server_port = config.get('main_guild_port', 25565)

    embed.add_field(name="📌 الاسم", value=guild.name, inline=True)
    embed.add_field(name="🆔 ID", value=guild.id, inline=True)
    embed.add_field(name="👑 صاحب السيرفر", value=guild.owner.mention if guild.owner else "غير معروف", inline=True)
    embed.add_field(name="📅 تاريخ الإنشاء", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="💾 موقع البيانات", value=str(guild.region), inline=True)
    embed.add_field(name="🎯 مستوى التحقق", value=str(guild.verification_level), inline=True)

    # Counts
    embed.add_field(name="👥 الأعضاء", value=len(guild.members), inline=True)
    embed.add_field(name="📁 القنوات", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 الرتب", value=len(guild.roles), inline=True)
    embed.add_field(name="😀 الإموجي", value=len(guild.emojis), inline=True)

    # Minecraft server IP
    if server_ip:
        embed.add_field(
            name="⛏️ سيرفر Minecraft",
            value=f"```\n{server_ip}:{server_port}\n```",
            inline=False
        )

    # Server icon
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='مساعدة', aliases=['help', 'ساعدني'])
async def help_command(ctx):
    """عرض قائمة الأوامر"""
    embed = discord.Embed(
        title="📚 قائمة الأوامر",
        color=discord.Color.gold()
    )

    commands_list = [
        ("القائمة", "عرض قائمة الأعضاء"),
        ("الة", "عرض معلومات السيرفر"),
        ("مساعدة", "عرض قائمة الأوامر"),
        ("البحث <اسم>", "البحث عن عضو"),
        ("حالة", "عرض حالة البوت"),
        ("سجل", "عرض سجل البوت (للمشرفين)"),
        ("مسح <عدد>", "مسح رسائل (للمشرفين)"),
        ("طرد <عضو>", "طرد عضو (للمشرفين)"),
        ("حظر <عضو>", "حظر عضو (للمشرفين)"),
        ("تقييد <عضو>", "تقييد عضو (للمشرفين)"),
        ("الالغاء <عضو>", "إلغاء تقييد عضو (للمشرفين)")
    ]

    for cmd, desc in commands_list:
        embed.add_field(name=f"`{config['prefix']}{cmd}`", value=desc, inline=False)

    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='البحث', aliases=['search', 'find'])
async def search_member(ctx, *, search_term: str):
    """البحث عن عضو في السيرفر"""
    guild = ctx.guild

    # Search in members
    found_members = [
        m for m in guild.members
        if search_term.lower() in m.name.lower() or
           (m.nick and search_term.lower() in m.nick.lower())
    ]

    if not found_members:
        await ctx.send(f"❌ لم يتم العثور على نتائج لـ: {search_term}")
        return

    embed = discord.Embed(
        title=f"🔍 نتائج البحث عن: {search_term}",
        color=discord.Color.blue()
    )

    results = []
    for member in found_members[:20]:
        status = "🟢 متصل" if member.status == discord.Status.online else "⚫ غير متصل"
        results.append(f"{status} {member.mention}\n  ID: {member.id}")

    embed.description = "\n\n".join(results)
    embed.set_footer(text=f"تم العثور على {len(found_members)} نتيجة")
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='حالة', aliases=['status', 'stats'])
async def bot_status(ctx):
    """عرض حالة البوت"""
    embed = discord.Embed(
        title="🤖 حالة البوت",
        color=discord.Color.green()
    )

    # Bot info
    embed.add_field(name="اسم البوت", value=bot.user.name, inline=True)
    embed.add_field(name="ID", value=bot.user.id, inline=True)

    # Uptime
    if hasattr(bot, 'uptime'):
        embed.add_field(name="وقت التشغيل", value=str(bot.uptime), inline=True)

    # Server count
    embed.add_field(name="عدد السيرفرات", value=len(bot.guilds), inline=True)
    embed.add_field(name="إجمالي الأعضاء", value=len(set(bot.get_all_members())), inline=True)

    # Channels count
    total_channels = sum(len(g.channels) for g in bot.guilds)
    embed.add_field(name="إجمالي القنوات", value=total_channels, inline=True)

    # Auto wiggle status
    wiggle_status = "✅ يعمل" if auto_wiggle.is_running() else "❌ متوقف"
    embed.add_field(name="الحركة التلقائية", value=wiggle_status, inline=True)

    # Anti-spam status
    spam_status = "✅ يعمل" if anti_spam.enabled else "❌ متوقف"
    embed.add_field(name="مضاد السبام", value=spam_status, inline=True)

    # Logger status
    log_status = "✅ يعمل" if logger.enabled else "❌ متوقف"
    embed.add_field(name="نظام اللوقات", value=log_status, inline=True)

    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='سجل', aliases=['logs'])
@commands.has_permissions(administrator=True)
async def show_logs(ctx):
    """عرض سجل اللوقات (للمشرفين فقط)"""
    await ctx.send(await logger.get_recent_logs(embed=True))

@bot.command(name='مسح', aliases=['clear', 'purge'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """مسح رسائل"""
    if amount > 100:
        await ctx.send("❌ لا يمكنك مسح أكثر من 100 رسالة")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ تم مسح **{len(deleted) - 1}** رسالة", delete_after=3)

@bot.command(name='طرد', aliases=['kick'])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason: str = "لا يوجد"):
    """طرد عضو"""
    await member.kick(reason=reason)

    # Log the action
    await logger.log_action(ctx.author, f"طرد {member}", reason)

    embed = discord.Embed(
        title="👢 عضو مطرود",
        color=discord.Color.orange()
    )
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="بواسطة", value=ctx.author.mention)
    embed.add_field(name="السبب", value=reason)
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='حظر', aliases=['ban'])
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason: str = "لا يوجد"):
    """حظر عضو"""
    await member.ban(reason=reason, delete_message_days=1)

    # Log the action
    await logger.log_action(ctx.author, f"حظر {member}", reason)

    embed = discord.Embed(
        title="🔨 عضو محظور",
        color=discord.Color.red()
    )
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="بواسطة", value=ctx.author.mention)
    embed.add_field(name="السبب", value=reason)
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='تقييد', aliases=['mute'])
@commands.has_permissions(manage_roles=True)
async def mute_member(ctx, member: discord.Member, minutes: int = 10):
    """تقييد عضو"""
    # Give muted role or timeout
    timeout_until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.edit(timed_out_until=timeout_until)

    # Log the action
    await logger.log_action(ctx.author, f"تقييد {member}", f"{minutes} دقيقة")

    embed = discord.Embed(
        title="🔇 عضو مقيد",
        color=discord.Color.yellow()
    )
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="بواسطة", value=ctx.author.mention)
    embed.add_field(name="المدة", value=f"{minutes} دقيقة")
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

@bot.command(name='الغاء_التقييد', aliases=['unmute'])
@commands.has_permissions(manage_roles=True)
async def unmute_member(ctx, member: discord.Member):
    """إلغاء تقييد عضو"""
    await member.edit(timed_out_until=None)

    # Log the action
    await logger.log_action(ctx.author, f"إلغاء تقييد {member}", "تم")

    embed = discord.Embed(
        title="🔊 تم إلغاء التقييد",
        color=discord.Color.green()
    )
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="بواسطة", value=ctx.author.mention)
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)

# Error handlers
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ لم يتم العثور على هذا العضو")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ خطأ في الإدخال، تأكد من صحة البيانات")
    else:
        await ctx.send(f"❌ حدث خطأ: {str(error)}")
        await logger.log_error(f"Command error: {error}")

# Run bot
if __name__ == "__main__":
    if config['token'] == "YOUR_DISCORD_BOT_TOKEN":
        print("⚠️ يرجى وضع رمز البوت في config.json!")
        print("1. اذهب إلى https://discord.com/developers/applications")
        print("2. أنشئ تطبيق جديد")
        print("3. أضف بوت")
        print("4. انسخ الرمز وضعه في config.json")
    else:
        bot.run(config['token'])
