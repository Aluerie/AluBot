from __future__ import annotations
from typing import TYPE_CHECKING, Annotated

from discord import Embed, Forbidden, Member, app_commands
from discord.ext import commands, tasks
from discord.utils import format_dt, sleep_until

from utils.var import *
from utils import database as db
from utils import time
from utils.context import Context

from datetime import datetime, timedelta, timezone
from sqlalchemy import func

if TYPE_CHECKING:
    from discord import Message, Interaction

blocked_phrases = ['https://cdn.discordapp.com/emojis/831229578340859964.gif?v=1']


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Mute'

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if any(i in msg.content for i in blocked_phrases):
            embed = Embed(colour=Clr.prpl)
            content = '{0} not allowed {1} {1} {1}'.format(msg.author.mention, Ems.peepoPolice)
            embed.description = 'Blocked phase. A warning for now !'
            await msg.channel.send(content=content, embed=embed)
            await msg.delete()

    @commands.has_role(Rid.discord_mods)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_command(
        name='warn',
        brief=Ems.slash,
        description='Warn member'
    )
    @app_commands.describe(member='Member to warn', reason='Reason')
    async def warn(self, ctx, member: Member, *, reason="No reason"):
        """Give member a warning"""
        if member.id == Uid.alu:
            return await ctx.reply(f"You can't do that to Aluerie {Ems.bubuGun}")
        if member.bot:
            return await ctx.reply("Don't bully bots, please")

        old_max_id = int(db.session.query(func.max(db.w.id)).scalar() or 0)
        db.add_row(
            db.w,
            old_max_id + 1,
            key='warn',
            name='manual',
            dtime=ctx.message.created_at,
            userid=member.id,
            modid=ctx.author.id,
            reason=reason
        )
        em = Embed(colour=Clr.prpl, title="Manual warning by a mod", description=reason)
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=em)

    async def mute_work(self, ctx, member, dt: datetime, duration: timedelta, reason):
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
    @commands.command(brief=Ems.slash, usage='<time> [reason]')
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
    @commands.hybrid_command(
        name='unmute',
        brief=Ems.slash,
        description='Remove timeout+mute from member'
    )
    @app_commands.describe(member='Member to unmute', reason='Reason')
    async def unmute(self, ctx, member: Member, *, reason: str = 'No reason'):
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
        if before.is_timed_out() == after.is_timed_out() or after.guild.id != Sid.alu:  # member is not muted/unmuted
            return

        if before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            em = Embed(colour=Clr.red)
            em.set_author(
                name=f'{after.display_name} is muted until',
                icon_url=after.display_avatar.url
            )
            em.description = format_dt(after.timed_out_until, style="R")
            await self.bot.get_channel(Cid.logs).send(embed=em)

        elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
            return  # apparently discord limitation > it doesnt ever happen


class PlebModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Tools'
        self.active_mutes = {}
        self.check_mutes.start()

    @commands.hybrid_command(
        name='selfmute',
        brief=Ems.slash,
        description='Mute yourself for chosen duration'
    )
    @app_commands.describe(duration='Choose duration of the mute')
    async def selfmute(self, ctx: Context, *, duration: time.FutureTime):
        """
        Anti-addiction feature.
        If you want to detach from my server for some time -
        use this command, and you will not be able to chat for specified `<time_duration>`.
        Duration should satisfy `5 minutes < duration < 30 days`.
        """
        if not timedelta(minutes=4, seconds=59) <= duration.dt - ctx.message.created_at <= timedelta(days=30, seconds=9):
            raise commands.BadArgument(
                'Sorry! Duration of selfmute should satisfy `5 minutes < duration < 30 days`'
            )
        selfmute_rl = ctx.guild.get_role(Rid.selfmuted)

        if ctx.author._roles.has(Rid.selfmuted):
            return await ctx.send(f'Somehow you are already muted {Ems.DankFix}')

        warn_em = Embed(colour=Clr.prpl, title='Confirmation Prompt')
        warn_em.description = \
            f'Are you sure you want to be muted until this time:\n' \
            f'{time.format_tdR(duration.dt)}?\n' \
            f'**Do not ask the moderators to undo this!**'
        confirm = await ctx.prompt(embed=warn_em)
        if not confirm:
            return await ctx.send('Aborting...', delete_after=5.0)

        await ctx.author.add_roles(selfmute_rl)

        em2 = Embed(colour=Clr.red).set_author(name=f'{ctx.author.display_name} is selfmuted until')
        em2.description = time.format_tdR(duration.dt)
        await ctx.guild.get_channel(Cid.logs).send(embed=em2)

        old_max_id = int(db.session.query(func.max(db.u.id)).scalar() or 0)
        db.add_row(
            db.u,
            1 + old_max_id,
            userid=ctx.author.id,
            channelid=ctx.channel.id,
            dtime=duration.dt,
            reason='Selfmute'
        )
        em = Embed(colour=ctx.author.colour)
        em.description = f'{ctx.author.mention} is self-muted until this time:\n{time.format_tdR(duration.dt)}'
        await ctx.send(embed=em)
        if duration.dt < self.check_mutes.next_iteration.replace(tzinfo=timezone.utc):
            self.bot.loop.create_task(self.fire_the_unmute(1 + old_max_id, ctx.author.id, duration.dt))

    @tasks.loop(minutes=30)
    async def check_mutes(self):
        for row in db.session.query(db.u):
            if row.dtime.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) + timedelta(minutes=30):
                if row.id in self.active_mutes:
                    continue
                self.active_mutes[row.id] = row
                self.bot.loop.create_task(self.fire_the_unmute(row.id, row.userid, row.dtime))

    async def fire_the_unmute(self, id_, userid, dtime):
        dtime = dtime.replace(tzinfo=timezone.utc)
        await sleep_until(dtime)
        guild = self.bot.get_guild(Sid.alu)
        selfmute_rl = guild.get_role(Rid.selfmuted)
        member = guild.get_member(userid)
        await member.remove_roles(selfmute_rl)
        db.remove_row(db.u, id_)
        self.active_mutes.pop(id_, None)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        selfmute_rl = channel.guild.get_role(Rid.selfmuted)
        muted_rl = channel.guild.get_role(Rid.muted)
        await channel.set_permissions(selfmute_rl, view_channel=False)
        await channel.set_permissions(muted_rl, send_messages=False)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(PlebModeration(bot))
