from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, AluGuildContext, const

if TYPE_CHECKING:
    from utils import AluBot


class ModerationCog(AluCog, emote=const.Emote.peepoPolice):
    """Commands to moderate servers with"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @commands.has_role(const.Role.discord_mods)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(name='warn', description='Warn member')
    @app_commands.describe(member='Member to warn', reason='Reason')
    async def warn(self, ctx: AluGuildContext, member: discord.Member, *, reason: str = "No reason"):
        """Give member a warning"""
        if member.id == self.bot.owner_id:
            raise commands.BadArgument(f"You can't do that to Aluerie {const.Emote.bubuGun}")
        if member.bot:
            raise commands.BadArgument("Don't bully bots, please")

        e = discord.Embed(title="Manual warning by a mod", colour=const.Colour.prpl(), description=reason)
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.reply(embed=e)
        e.url = msg.jump_url
        await self.community.logs.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id != const.Guild.community:
            return

        if after.timed_out_until and before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            e = discord.Embed(colour=const.Colour.red())
            e.description = discord.utils.format_dt(after.timed_out_until, style="R")

            mute_actor_str = "Unknown"
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update):
                target: discord.Member = entry.target  # type: ignore
                user: discord.Member = entry.target  # type: ignore
                if target.id == after.id and entry.after.timed_out_until == after.timed_out_until:
                    mute_actor_str = user.name

            author_text = f'{after.display_name} is muted by {mute_actor_str} until'
            e.set_author(name=author_text, icon_url=after.display_avatar.url)
            return await self.community.logs.send(embed=e)

        # elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
        #     return
        # apparently discord limitation -> it does not ever happen

    @commands.Cog.listener('on_guild_channel_create')
    async def give_aluerie_all_perms(self, channel: discord.abc.GuildChannel):
        if channel.guild.id != self.community.id:
            return

        sister_of_the_veil = self.community.sister_of_the_veil
        allow, deny = discord.Permissions.all(), discord.Permissions.none()
        all_perms = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)
        reason = 'Give all permissions to Aluerie'
        await channel.set_permissions(sister_of_the_veil, overwrite=all_perms, reason=reason)


async def setup(bot: AluBot):
    await bot.add_cog(ModerationCog(bot))
