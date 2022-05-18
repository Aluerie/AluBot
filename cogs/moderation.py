from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member, app_commands
from discord.ext import commands
from discord.utils import format_dt

from utils.var import *
from utils import database as db
from utils.time import DTFromStr, arg_to_timetext
from utils.context import Context

from datetime import timedelta

if TYPE_CHECKING:
    from discord import Message
    from discord import Interaction

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
        if member.id == Uid.irene:
            return await ctx.reply(f"You can't do that to Irene {Ems.bubuGun}")
        if member.bot:
            return await ctx.reply("Don't bully bots, please")
        db.append_row(
            db.w, key='warn', name='manual', dtime=ctx.message.created_at, userid=member.id, modid=ctx.author.id,
            reason=reason
        )
        em = Embed(colour=Clr.prpl, title="Manual warning by a mod", description=reason)
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=em)

    @commands.has_role(Rid.discord_mods)
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(member='Member to ban', reason='Reason')
    @commands.hybrid_command(
        name='ban',
        brief=Ems.slash,
        description='Ban member from the server'
    )
    async def ban(self, ctx, member: Member, *, reason: str = "No reason"):
        """Ban member from the server"""
        em = Embed(colour=Clr.red, title="Ban member")
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.add_field(name='Reason', value=reason)
        await member.ban(reason=reason)
        await ctx.reply(embed=em)

    @staticmethod
    async def mute_work(ctx, member, duration, reason):
        await member.timeout(duration, reason=reason)
        db.append_row(
            db.w, key='mute', name='manual', dtime=ctx.message.created_at, userid=member.id, modid=ctx.author.id,
            reason=reason
        )
        em = Embed(color=Clr.prpl, title="Mute member", description=f'mute for {duration}')
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        em.add_field(name='Reason', value=reason)
        await ctx.reply(embed=em)

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.command(
        name='mute',
        description="Mute+timeout member from chatting"
    )
    @app_commands.describe(member='Member to mute+timeout', duration='Duration of the mute', reason='Reason')
    async def mute_slh(self, ctx: Interaction, member: Member, duration: str, *, reason: str = "No reason"):
        duration = DTFromStr(duration)
        ctx = await Context.from_interaction(ctx)
        await self.mute_work(ctx, member, duration.delta, reason)

    @commands.has_role(Rid.discord_mods)
    @commands.command(
        name='mute',
        brief=Ems.slash,
        usage='<time> [reason]'
    )
    async def mute_ext(self, ctx: Context, member: Member, *, duration_reason: str = "5 min No reason"):
        """Mute+timeout member from chatting"""
        duration, reason = arg_to_timetext(duration_reason)
        await self.mute_work(ctx, member, timedelta(seconds=duration), reason)

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
        await ctx.reply(embed=em)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.is_timed_out() != after.is_timed_out() or after.guild.id != Sid.irene:  # member is not muted/unmuted
            return

        muted_rl = after.guild.get_role(Rid.muted)

        if before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            em = Embed(colour=Clr.red)
            em.set_author(
                name=f'{after.display_name} is muted until {format_dt(after.timed_out_until, style="R")}',
                icon_url=after.display_avatar.url
            )
            await after.add_roles(muted_rl)
            if not after.bot:
                await after.edit(nick=f'[MUTED] | {after.display_name}'[:32])
            await self.bot.get_channel(Cid.logs).send(embed=em)

        elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
            em = Embed(colour=Clr.olive)
            em.set_author(
                name=f'{after.display_name} is now unmuted',
                icon_url=after.display_avatar.url
            )
            await after.remove_roles(muted_rl)
            if not after.bot:
                await after.edit(nick=db.get_value(db.m, after.id, 'name'))
            await self.bot.get_channel(Cid.logs).send(embed=em)

            em2 = Embed(color=Clr.prpl, title="Unmute member")
            em2.set_author(name=after.display_name, icon_url=after.display_avatar.url)
            em2.description = f"{after.mention} is unmuted now, don't be bad ever again {Ems.bubuGun}"
            await after.guild.get_channel(Cid.bot_spam).send(embed=em2)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
