from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated

from discord import Embed, Forbidden, Member, app_commands, AuditLogAction
from discord.ext import commands
from discord.utils import format_dt

from .utils import time
from .utils.context import Context
from .utils.var import Rid, Ems, Clr, Uid, Sid, Cid

if TYPE_CHECKING:
    from discord import Interaction
    from .utils.bot import AluBot


class Moderation(commands.Cog):
    """Commands to moderate server with"""
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.help_emote = Ems.peepoPolice
        self.active_mutes = {}

    @commands.has_role(Rid.discord_mods)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(name='warn', description='Warn member')
    @app_commands.describe(member='Member to warn', reason='Reason')
    async def warn(self, ctx: Context, member: Member, *, reason: str = "No reason"):
        """Give member a warning"""
        if member.id == Uid.alu:
            raise commands.BadArgument(f"You can't do that to Aluerie {Ems.bubuGun}")
        if member.bot:
            raise commands.BadArgument("Don't bully bots, please")

        em = Embed(title="Manual warning by a mod", colour=Clr.prpl, description=reason)
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.reply(embed=em)
        em.url = msg.jump_url
        await self.bot.get_channel(Cid.logs).send(embed=em)

    @staticmethod
    async def mute_work(ctx, member, dt: datetime, duration: timedelta, reason):
        try:
            await member.timeout(duration, reason=reason)
        except Forbidden:
            em = Embed(color=Clr.error, description=f'You can not mute that member')
            em.set_author(name='MissingPermissions')
            return await ctx.reply(embed=em, ephemeral=True)

        em = Embed(color=Clr.prpl, title="Mute member", description=f'mute until {format_dt(dt, "R")}')
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.add_field(name='Reason', value=reason)
        content = member.mention if ctx.interaction else ''
        await ctx.reply(content=content, embed=em)

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.command(description="Mute+timeout member from chatting")
    @app_commands.describe(member='Member to mute+timeout', duration='Duration of the mute', reason='Reason')
    async def mute(self, ctx: Interaction, member: Member, duration: str, *, reason: str = "No reason"):
        dt = time.FutureTime(duration)
        ctx = await Context.from_interaction(ctx)
        delta = dt.dt - datetime.now(timezone.utc)
        await self.mute_work(ctx, member, dt.dt, delta, reason)

    @commands.has_role(Rid.discord_mods)
    @commands.command(usage='<time> [reason]')
    async def mute(
            self,
            ctx: Context,
            member: Member,
            *,
            when: Annotated[time.FriendlyTimeResult, time.UserFriendlyTime(commands.clean_content, default='…')]
    ):
        """Mute+timeout member from chatting"""
        delta = when.dt - datetime.now(timezone.utc)
        await self.mute_work(ctx, member, when.dt, delta, when.arg)

    @commands.has_role(Rid.discord_mods)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(name='unmute', description='Remove timeout+mute from member')
    @app_commands.describe(member='Member to unmute', reason='Reason')
    async def unmute(self, ctx: Context, member: Member, *, reason: str = 'No reason'):
        """Remove timeout+mute from member"""
        await member.timeout(None, reason=reason)
        em = Embed(color=Clr.prpl, title="Unmute member")
        em.description = f"{member.mention}, you are unmuted now, congrats {Ems.bubuSip}"
        em.add_field(name='Reason', value=reason)
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        content = member.mention if ctx.interaction else ''
        await ctx.reply(content=content, embed=em)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if after.guild.id != Sid.alu:
            return

        if before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            em = Embed(colour=Clr.red, description=format_dt(after.timed_out_until, style="R"))

            mute_actor_str = "Unknown"
            async for entry in after.guild.audit_logs(action=AuditLogAction.member_update):
                if entry.target.id == after.id and entry.after.timed_out_until == after.timed_out_until:
                    mute_actor_str = entry.user.name

            em.set_author(
                name=f'{after.display_name} is muted by {mute_actor_str} until',
                icon_url=after.display_avatar.url
            )
            return await self.bot.get_channel(Cid.logs).send(embed=em)

        elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
            return  # apparently discord limitation > it doesnt ever happen


async def setup(bot: AluBot):
    await bot.add_cog(Moderation(bot))
