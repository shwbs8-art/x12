import discord
from typing import Optional, List

class PermissionManager:
    def __init__(self, bot, admin_role_id: Optional[int] = None):
        self.bot = bot
        self.admin_role_id = admin_role_id

    def is_admin(self, member: discord.Member) -> bool:
        """Check if member is admin"""
        # Check if member is server owner
        if member.guild.owner_id == member.id:
            return True

        # Check if member has administrator permission
        if member.guild_permissions.administrator:
            return True

        # Check if member has the admin role
        if self.admin_role_id:
            admin_role = discord.utils.get(member.roles, id=self.admin_role_id)
            if admin_role:
                return True

        return False

    def is_moderator(self, member: discord.Member) -> bool:
        """Check if member is moderator"""
        if self.is_admin(member):
            return True

        # Check for moderator permissions
        mod_permissions = [
            'manage_messages',
            'kick_members',
            'ban_members',
            'mute_members',
            'manage_roles'
        ]

        for perm in mod_permissions:
            if getattr(member.guild_permissions, perm):
                return True

        return False

    def can_manage_channels(self, member: discord.Member) -> bool:
        """Check if member can manage channels"""
        return (
            member.guild_permissions.manage_channels or
            self.is_admin(member)
        )

    def can_manage_roles(self, member: discord.Member) -> bool:
        """Check if member can manage roles"""
        return (
            member.guild_permissions.manage_roles or
            self.is_admin(member)
        )

    def can_moderate(self, member: discord.Member) -> bool:
        """Check if member can moderate"""
        return self.is_moderator(member)

    def get_member_level(self, member: discord.Member) -> str:
        """Get member permission level"""
        if self.is_admin(member):
            return "admin"
        elif self.is_moderator(member):
            return "moderator"
        elif member.guild_permissions.manage_guild:
            return "manager"
        else:
            return "member"

    def get_permission_embed(self, member: discord.Member) -> discord.Embed:
        """Create embed showing member permissions"""
        embed = discord.Embed(
            title=f"🔐 صلاحيات: {member}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )

        level = self.get_member_level(member)
        level_names = {
            'admin': '👑 مدير',
            'moderator': '🛡️ مشرف',
            'manager': '⚙️ مدير السيرفر',
            'member': '👤 عضو'
        }

        embed.add_field(
            name="المستوى",
            value=level_names.get(level, level),
            inline=True
        )

        # General permissions
        perms = []
        perm_names = {
            'administrator': 'مدير',
            'manage_guild': 'إدارة السيرفر',
            'manage_channels': 'إدارة القنوات',
            'manage_roles': 'إدارة الرتب',
            'manage_messages': 'إدارة الرسائل',
            'kick_members': 'طرد الأعضاء',
            'ban_members': 'حظر الأعضاء',
            'mention_everyone': 'ذكر الجميع'
        }

        for perm, name in perm_names.items():
            if getattr(member.guild_permissions, perm):
                perms.append(f"✅ {name}")
            else:
                perms.append(f"❌ {name}")

        embed.add_field(
            name="الصلاحيات العامة",
            value="\n".join(perms[:10]),
            inline=False
        )

        return embed

    async def check_permission(self, ctx, required_level: str = 'member') -> bool:
        """Check if command invoker has required permission level"""
        if required_level == 'admin':
            return self.is_admin(ctx.author)
        elif required_level == 'moderator':
            return self.is_moderator(ctx.author)
        elif required_level == 'manager':
            return ctx.author.guild_permissions.manage_guild or self.is_admin(ctx.author)
        else:
            return True

    def get_admins(self, guild: discord.Guild) -> List[discord.Member]:
        """Get all admins in guild"""
        admins = []
        for member in guild.members:
            if self.is_admin(member):
                admins.append(member)
        return admins

    def get_moderators(self, guild: discord.Guild) -> List[discord.Member]:
        """Get all moderators in guild"""
        mods = []
        for member in guild.members:
            if self.is_moderator(member):
                mods.append(member)
        return mods
