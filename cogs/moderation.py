from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, AluContext, Clr, Ems, Rid, Sid, times

if TYPE_CHECKING:
    from utils import AluBot


class Moderation(AluCog, emote=Ems.peepoPolice):
    """Commands to moderate servers with"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_mutes = {}

    @commands.has_role(Rid.discord_mods.id)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(name='warn', description='Warn member')
    @app_commands.describe(member='Member to warn', reason='Reason')
    async def warn(self, ctx: AluContext, member: discord.Member, *, reason: str = "No reason"):
        """Give member a warning"""
        if member.id == self.bot.owner_id:
            raise commands.BadArgument(f"You can't do that to Aluerie {Ems.bubuGun}")
        if member.bot:
            raise commands.BadArgument("Don't bully bots, please")

        e = discord.Embed(title="Manual warning by a mod", colour=Clr.prpl(), description=reason)
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.reply(embed=e)
        e.url = msg.jump_url
        await self.community.logs.send(embed=e)

    @staticmethod
    async def mute_work(ctx, member, dt: datetime.datetime, duration: datetime.timedelta, reason):
        try:
            await member.timeout(duration, reason=reason)
        except discord.Forbidden:
            e = discord.Embed(color=Clr.error(), description=f'You can not mute that member')
            e.set_author(name='MissingPermissions')
            return await ctx.reply(embed=e, ephemeral=True)

        e = discord.Embed(color=Clr.prpl(), title="Mute member")
        e.description = f'mute until {discord.utils.format_dt(dt, "R")}'
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.add_field(name='Reason', value=reason)
        content = member.mention if ctx.interaction else ''
        await ctx.reply(content=content, embed=e)

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.command(description="Mute+timeout member from chatting")
    @app_commands.describe(member='Member to mute+timeout', duration='Duration of the mute', reason='Reason')
    async def mute(self, ctx: discord.Interaction, member: discord.Member, duration: str, *, reason: str = "No reason"):
        dt = times.FutureTime(duration)
        ctx = await AluContext.from_interaction(ctx)
        delta = dt.dt - discord.utils.utcnow()
        await self.mute_work(ctx, member, dt.dt, delta, reason)

    @commands.has_role(Rid.discord_mods.id)
    @commands.command(usage='<time> [reason]')
    async def mute(
        self,
        ctx: AluContext,
        member: discord.Member,
        *,
        when: Annotated[
            times.FriendlyTimeResult,
            times.UserFriendlyTime(commands.clean_content, default='…'),
        ],
    ):
        """Mute+timeout member from chatting"""
        delta = when.dt - discord.utils.utcnow()
        await self.mute_work(ctx, member, when.dt, delta, when.arg)

    @commands.has_role(Rid.discord_mods.id)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(name='unmute', description='Remove timeout+mute from member')
    @app_commands.describe(member='Member to unmute', reason='Reason')
    async def unmute(self, ctx: AluContext, member: discord.Member, *, reason: str = 'No reason'):
        """Remove timeout+mute from member"""
        await member.timeout(None, reason=reason)
        e = discord.Embed(color=Clr.prpl(), title="Unmute member")
        e.description = f"{member.mention}, you are unmuted now, congrats {Ems.bubuSip}"
        e.add_field(name='Reason', value=reason)
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        content = member.mention if ctx.interaction else ''
        await ctx.reply(content=content, embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id != Sid.community:
            return

        if after.timed_out_until and before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            e = discord.Embed(colour=Clr.red, description=discord.utils.format_dt(after.timed_out_until, style="R"))

            mute_actor_str = "Unknown"
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update):
                target: discord.Member = entry.target  # type: ignore
                user: discord.Member = entry.target  # type: ignore
                if target.id == after.id and entry.after.timed_out_until == after.timed_out_until:
                    mute_actor_str = user.name

            e.set_author(
                name=f'{after.display_name} is muted by {mute_actor_str} until', icon_url=after.display_avatar.url
            )
            return await self.community.logs.send(embed=e)

        # elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
        #     return
        # apparently discord limitation -> it does not ever happen


async def setup(bot: AluBot):
    await bot.add_cog(Moderation(bot))
