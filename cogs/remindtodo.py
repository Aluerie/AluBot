from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Interaction, Member, app_commands
from discord.ext import commands, tasks
from discord.utils import sleep_until, format_dt

from utils import database as db
from utils.var import *
from utils.time import arg_to_timetext
from utils.discord import scnf

from datetime import datetime, timedelta, timezone
from sqlalchemy import func

if TYPE_CHECKING:
    from utils.context import Context


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()
        self.active_reminders = {}
        self.help_category = 'Todo'

    @commands.hybrid_group(
        name='remind',
        description='Group command about reminders'
    )
    async def remind(self, ctx: Context):
        """Group command about reminders, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @remind.command(
        name='remove',
        brief=Ems.slash,
        description='Remove reminder from your reminders list'
    )
    @app_commands.describe(id_='id of reminder')
    async def remove(self, ctx: Context, id_: int):
        """Removes reminder under id from your reminders list. \
        You can find *ids* of your reminders in `$remind list` command ;"""
        user = db.session.query(db.r).filter_by(userid=ctx.author.id, id=id_)
        if user.first() is None:
            embed = Embed(colour=Clr.rspbrry).set_author(name='Database_Error')
            embed.description = 'Double-check all arguments:\n`id`'
            embed.set_footer(text='Probably this `id` doesn\'t belong to you or doesn\'t exist')
            return await ctx.reply(embed=embed)
        else:
            with db.session_scope() as ses:
                ses.query(db.r).filter_by(id=id_).delete()
            if isinstance(ctx, commands.Context):
                await ctx.message.add_reaction(Ems.PepoG)
            elif isinstance(ctx, Interaction):
                await ctx.response.send_message(content=Ems.DankApprove, ephemeral=True)

    @remind.command(
        name='list',
        brief=Ems.slash,
        description='Show `@member`s reminders list',
        usage='[member=you]'
    )
    async def list(self, ctx: Context, member: Member = None):
        """Shows `@member`'s reminders list ;"""
        member = member or ctx.author
        embed = Embed(colour=member.colour)
        embed.description = '\n'.join([
            f'{counter}. `id #{row.id}` Date: {format_dt(row.dtime.replace(tzinfo=timezone.utc))}\n{row.name}'
            for counter, row in enumerate(db.session.query(db.r).filter_by(userid=member.id))
        ])  # todo: this might be beyond 2000(?) limit
        embed.set_author(name=f'{member.display_name}\'s Reminders list', icon_url=member.display_avatar.url)
        await ctx.reply(embed=embed)

    @remind.command(
        name='me',
        brief=Ems.slash,
        description='Remind you about `remind_text` in `remind_time`',
        usage='<remind_time> <remind_text>',
        aliases=['add']
    )
    async def me(self, ctx: Context, *, remind_time_and_remind_text):
        """Makes bot remind you about `remind_text` in `remind_time` ;"""
        time_secs, remind_text = arg_to_timetext(remind_time_and_remind_text)

        if time_secs is None:
            embed = Embed(colour=Clr.rspbrry)
            embed.set_author(name='TimeNotParsed')
            embed.description = '`$remind me *remind_time* *remind text*` \n' \
                                'where `remind_time` is amount of weeks, days, hours, minutes, seconds'
            embed.set_footer(text='Exception raised when the bot couln\'t recognize time from given command arguments.')
            return await ctx.reply(embed=embed)

        with db.session_scope() as ses:
            old_max_id = int(ses.query(func.max(db.r.id)).scalar() or 0)
            delta_time = timedelta(seconds=time_secs)
            dtime = datetime.now(timezone.utc) + delta_time
            new_row = db.r(
                id=1 + old_max_id, name=remind_text, userid=ctx.author.id, channelid=ctx.channel.id, dtime=dtime)
            ses.add(new_row)
        embed = Embed(color=Clr.prpl)
        embed.description = f'{ctx.author.mention}, you will be reminded about it in {delta_time}'
        embed.set_footer(text=f'Reminder was added under `id #{1 + old_max_id}`')
        await ctx.reply(embed=embed)
        #  self.check_reminders.restart()
        if dtime < self.check_reminders.next_iteration.replace(tzinfo=timezone.utc):
            self.bot.loop.create_task(
                self.fire_the_reminder(1 + old_max_id, remind_text, ctx.author.id, ctx.channel.id, dtime))

    @tasks.loop(minutes=30)
    async def check_reminders(self):
        rows = db.session.query(db.r).filter(db.r.dtime < datetime.now(timezone.utc) + timedelta(minutes=30))
        for row in rows:
            if row.id in self.active_reminders:
                continue
            self.active_reminders[row.id] = row
            self.bot.loop.create_task(
                self.fire_the_reminder(row.id, row.name, row.userid, row.channelid, row.dtime))

    async def fire_the_reminder(self, id_, name, userid, channelid, dtime):
        dtime = dtime.replace(tzinfo=timezone.utc)
        await sleep_until(dtime)
        answer = f"{self.bot.get_user(userid).mention}, remember?"
        embed = Embed(color=Clr.prpl, description=name)
        await self.bot.get_channel(channelid).send(content=answer, embed=embed)
        db.remove_row(db.r, id_)
        self.active_reminders.pop(id_, None)

    @check_reminders.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Todo'

    @commands.hybrid_group()
    async def todo(self, ctx):
        """Group command about ToDolists, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @todo.command(
        name='remove',
        brief=Ems.slash,
        description='Remove todo bullet from your todo list',
        help='Removes tdo bullet under *bullet_id* from your ToDolist. '
             'You can find *ids* of your To Do bullets in `$todo list` command'
    )
    @app_commands.describe(bullet_id='ToDo Bullet id in your list')
    async def remove(self, ctx: Context, bullet_id: int):
        """Read above"""
        user = db.session.query(db.t).filter_by(userid=ctx.author.id, id=bullet_id)
        if user.first() is None:
            embed = Embed(colour=Clr.rspbrry)
            embed.set_author(name='DatabaseError')
            embed.description = 'Double-check all arguments:\n`id`'
            embed.set_footer(text='Probably this `id` doesn\'t belong to you or doesn\'t exist')
            return await ctx.reply(embed=embed)
        else:
            with db.session_scope() as ses:
                ses.query(db.t).filter_by(id=bullet_id).delete()
            if ctx.interaction:
                await ctx.reply(content=f'removed {Ems.PepoG}')
            else:
                await ctx.message.add_reaction(Ems.PepoG)

    @todo.command(
        name='list',
        brief=Ems.slash,
        description="Show `@member` ToDo list ",
        help="Show `@member` ToDo list ;",
        usage='[member=you]'
    )
    @app_commands.describe(member='Member to check')
    async def list(self, ctx: Context, member: Member = None):
        """Read above"""
        member = member or ctx.author
        embed = Embed(colour=member.colour)
        embed.description = '\n'.join([
            f'{cnt} `id #{row.id}`\n{row.name} '
            for cnt, row in enumerate(db.session.query(db.t).filter_by(userid=member.id))
        ])  # todo: this might be beyond 2000(?) limit
        embed.set_author(name=f'{member.display_name}\'s ToDo list', icon_url=member.display_avatar.url)
        await ctx.reply(embed=embed)

    @todo.command(
        name='add',
        brief=Ems.slash,
        description="Add new ToDo Bullet to your ToDo list",
        help='Add new ToDo Bullet to your ToDo list ;'
    )
    @app_commands.describe(todo_text='Text for your ToDo bullet')
    async def add(self, ctx, *, todo_text: str):
        """Read above"""
        db.append_row(db.t, name=todo_text, userid=ctx.author.id)
        if ctx.interaction:
            ctx.reply(f'added {Ems.PepoG}')
        else:
            await ctx.message.add_reaction(Ems.PepoG)


class Afk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_afks.start()
        self.active_afk = {}
        self.help_category = 'Todo'

    @commands.hybrid_command(
        name='afk',
        brief=Ems.slash,
        description='Flag you as afk member'
    )
    @app_commands.describe(afk_text='Your custom afk note')
    async def afk(self, ctx, *, afk_text):
        """Flags you as afk with your custom afk note ;"""
        if db.session.query(db.a).filter_by(id=ctx.author.id).first() is None:
            db.add_row(db.a, ctx.author.id, name=afk_text)
        else:
            db.set_value(db.a, ctx.author.id, name=afk_text)
        self.active_afk[ctx.author.id] = afk_text
        await ctx.message.add_reaction(Ems.PepoG)
        embed = Embed(color=Clr.prpl)
        embed.description = f'{ctx.author.mention}, you are flagged as afk with `afk_text`:\n{afk_text}'
        await ctx.reply(embed=embed)
        try:
            await ctx.author.edit(nick=f'[AFK] | {ctx.author.display_name}')
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.guild.id != Sid.irene:
            return
        if message.content.startswith('$afk'):
            return
        if message.channel.id in [Cid.logs, Cid.spam_me]:
            return

        for key in self.active_afk:
            if key in message.raw_mentions:
                embed = Embed(colour=Clr.prpl, title='Afk note:', description=db.get_value(db.a, key, 'name'))
                irene_server = self.bot.get_guild(Sid.irene)
                member = irene_server.get_member(key)
                embed.set_author(name=f'Sorry, but {member.display_name} is $afk !', icon_url=member.display_avatar.url)
                embed.set_footer(text='PS. Please, consider deleting your ping-message (or just removing ping) '
                                      'if you think it will be irrelevant when they come back (I mean seriously)')
                await message.channel.send(embed=embed)

        if message.author.id in self.active_afk:
            embed = Embed(colour=Clr.prpl, title='Afk note:')
            embed.set_author(
                name=f'{message.author.display_name[8:]} is no longer afk !',
                icon_url=message.author.display_avatar.url
            )
            embed.description = db.get_value(db.a, message.author.id, 'name')
            db.remove_row(db.a, message.author.id)
            self.active_afk.pop(message.author.id)
            await message.channel.send(embed=embed)
            try:
                await message.author.edit(nick=message.author.display_name[8:])
            except:
                pass

    @tasks.loop(minutes=30)
    async def check_afks(self):
        rows = db.session.query(db.a)
        for row in rows:
            if row.id in self.active_afk:
                continue
            self.active_afk[row.id] = row.name

    @check_afks.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Remind(bot))
    await bot.add_cog(Todo(bot))
    await bot.add_cog(Afk(bot))

