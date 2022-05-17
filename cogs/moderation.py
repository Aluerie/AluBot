from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member
from discord.ext import commands, tasks
from discord.utils import sleep_until

from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from utils.var import *
from utils import database as db
from utils.format import arg_to_timetext

if TYPE_CHECKING:
    pass

blocked_phrases = ['https://cdn.discordapp.com/emojis/831229578340859964.gif?v=1']


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_mutes.start()
        self.active_mutes = {}
        self.help_category = 'Mute'

    @commands.Cog.listener()
    async def on_message(self, message):
        if any(ext in message.content for ext in blocked_phrases):
            embed = Embed(colour=Clr.prpl)
            content = '{0} not allowed {1} {1} {1}'.format(message.author.mention, Ems.peepoPolice)
            embed.description = 'A warning for now !'
            await message.channel.send(content=content, embed=embed)
            await message.delete()

    @commands.has_role(Rid.discord_mods)
    @commands.command()
    async def warn(self, ctx, member: Member = None, *, reason="No reason provided"):
        """Give member a warning"""
        if member is None:
            return await ctx.reply("You didn\'t mention a user to warn.")
        if member.id == Uid.irene:
            return await ctx.reply("You can't do that to Irene {}".format(Ems.bubuGun))
        if member.bot:
            return await ctx.reply("Don't bully bots, please")
        old_max_id = int(db.session.query(func.max(db.w.id)).scalar() or 0)
        dtime = datetime.now(timezone.utc)
        db.add_row(
            db.w, 1 + old_max_id, name='manual', dtime=dtime, userid=member.id, modid=ctx.author.id, reason=reason)

        embed = Embed(colour=Clr.prpl)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.title = "Manual warning by a mod"
        embed.description = reason
        embed.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.has_role(Rid.discord_mods)
    @commands.command()
    async def ban(self, ctx, member: Member = None, *, reason="No reason provided"):
        """Ban member from the server"""
        if member is None:
            return await ctx.reply("You didn\'t mention a user to ban.")
        if member.id == Uid.irene:
            return await ctx.reply(f"You can't do that to Irene {Ems.bubuGun}")
        if member.bot:
            return await ctx.reply("Don't bully bots, please")

        embed = Embed(colour=Clr.red)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.title = "Ban member"
        embed.add_field(name='Reason', value=reason)
        await member.ban()
        await ctx.reply(embed=embed)

    async def mute_work(self, ctx, member: Member, time_secs, reason_str):
        irene_server = self.bot.get_guild(Sid.irene)
        muted_rl = irene_server.get_role(Rid.muted)
        await member.add_roles(muted_rl)

        if time_secs is None:
            embed = Embed(colour=Clr.rspbrry)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            embed.title = 'Indefinite Mute member'
            embed.description = 'This mute is not time-expiring, it can be only manually lifted using `$unmute` command'
            embed.set_footer(text='`$mute @user {mute_time} *reason text*`')
            embed.add_field(name='Reason', value=reason_str)
            await member.edit(nick=f'[MUTED INF] | {member.display_name}'[:32])
            await member.timeout_for(timedelta(days=1000))
            return await ctx.reply(embed=embed)

        await member.timeout_for(timedelta(seconds=time_secs))
        await member.edit(nick=f'[MUTED] | {member.display_name}'[:32])
        old_max_id = int(db.session.query(func.max(db.u.id)).scalar() or 0)
        delta_time = timedelta(seconds=time_secs)
        dtime = datetime.now(timezone.utc) + delta_time
        db.add_row(
            db.u,
            1 + old_max_id,
            userid=member.id,
            channelid=ctx.channel.id,
            dtime=dtime,
            reason=reason_str
        )
        embed = Embed(color=Clr.prpl)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.title = "Mute member"
        embed.description = f'mute for {delta_time}'
        embed.add_field(name='Reason', value=reason_str)
        embed.set_footer(text=f'Mute was added under `id #{1 + old_max_id}`')
        await ctx.reply(embed=embed)
        #  self.check_reminders.restart()
        if dtime < self.check_mutes.next_iteration.replace(tzinfo=timezone.utc):
            self.bot.loop.create_task(
                self.fire_the_unmute(1 + old_max_id, reason_str, member.id, ctx.channel.id, dtime))

    @commands.has_role(Rid.discord_mods)
    @commands.command()
    async def mute(self, ctx, member: Member = None, *, arg_string="No reason provided"):
        """Timeout+mute member from chatting"""
        if member is None:
            return await ctx.reply("You didn\'t mention a user to mute.")
        if member.id == Uid.irene:
            return await ctx.reply(f"You can't do that to Irene {Ems.bubuGun}")
        if member.bot:
            return await ctx.reply("Don't bully bots, please")

        time_secs, reason_text = arg_to_timetext(arg_string)
        await self.mute_work(ctx, member, time_secs, reason_text)

    @commands.has_role(Rid.discord_mods)
    @commands.command()
    async def unmute(self, ctx, member: Member = None):
        """Remove timeout+mute from member"""
        if member is None:
            return await ctx.reply("You didn\'t mention a user to mute.")
        if member.id == Uid.irene:
            return await ctx.reply(f"You can't do that to Irene {Ems.bubuGun}")
        if member.bot:
            return await ctx.reply("You couldn't mute bots in the first place")

        irene_server = self.bot.get_guild(Sid.irene)
        muted_rl = irene_server.get_role(Rid.muted)

        await member.remove_timeout()
        await member.remove_roles(muted_rl)
        await member.edit(nick=db.get_value(db.m, member.id, 'name'))

        answer = f"{member.mention}, you are unmuted now, congrats {Ems.bubuSip}"
        embed = Embed(color=Clr.prpl)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.title = "Unmute member"
        await ctx.reply(content=answer, embed=embed)

    @tasks.loop(minutes=30)
    async def check_mutes(self):
        for row in db.session.query(db.u):
            if row.dtime.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) + timedelta(minutes=30):
                if row.id in self.active_mutes:
                    continue
                self.active_mutes[row.id] = row
                self.bot.loop.create_task(
                    self.fire_the_unmute(row.id, row.reason, row.userid, row.channelid, row.dtime))

    async def fire_the_unmute(self, id_, reason_str, userid, channelid, dtime):
        dtime = dtime.replace(tzinfo=timezone.utc)
        await sleep_until(dtime)
        irene_server = self.bot.get_guild(Sid.irene)
        muted_rl = irene_server.get_role(Rid.muted)
        member = irene_server.get_member(userid)
        await member.remove_roles(muted_rl)
        await member.edit(nick=db.get_value(db.m, member.id, 'name'))

        answer = f"{member.mention}, you are unmuted now, don't be bad ever again {Ems.bubuGun}"
        embed = Embed(color=Clr.prpl, title="Unmute member")
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(name="Reason for mute", value=reason_str)
        await self.bot.get_channel(channelid).send(content=answer, embed=embed)
        db.remove_row(db.u, id_)
        self.active_mutes.pop(id_, None)

    @check_mutes.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if after.timed_out_until is not None and before.timed_out_until != after.timed_out_until:
            embed = Embed(colour=Clr.red)
            embed.set_author(
                name=f'{after.display_name} is timed out until {after.timed_out_until.isoformat()}',
                url=after.display_avatar.url
            )
            await self.bot.get_channel(Cid.logs).send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
