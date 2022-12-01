from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated, Union

from discord import Embed, Interaction, Member, app_commands
from discord.ext import commands, tasks
from discord.utils import sleep_until
from sqlalchemy import func

from cogs.utils import time
from cogs.utils.context import Context
from cogs.utils.distools import send_pages_list
from cogs.utils.var import Ems, Clr, Cid, Sid

if TYPE_CHECKING:
    from discord import Message


class Remind(commands.Cog, name='Reminders, ToDo and AFK commands'):
    """
    Organize yourself with some instruments
    """
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()
        self.active_reminders = {}
        self.check_afks.start()
        self.active_afk = {}
        self.help_emote = Ems.DankG

    def cog_unload(self) -> None:
        self.check_reminders.cancel()
        self.check_afks.cancel()

    slh_group = app_commands.Group(name="remind", description="Group command about reminders")

    @commands.group()
    async def remind(self, ctx: Context):
        """Group command about reminders, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def add_work(self, ctx: Union[Context, Interaction], member: Member, dt, remind_text):
        with db.session_scope() as ses:
            old_max_id = int(ses.query(func.max(db.r.id)).scalar() or 0)
            new_row = db.r(
                id=1 + old_max_id,
                name=remind_text,
                userid=member.id,
                channelid=ctx.channel.id,
                dtime=dt
            )
            ses.add(new_row)
        embed = Embed(
            color=Clr.prpl,
            title='Reminder was made for you',
            description=remind_text
        ).set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url
        ).add_field(
            inline=False,
            name='Reminder time',
            value=time.format_tdR(dt)
        ).set_footer(
            text=f'Reminder was added under `id #{1 + old_max_id}`'
        )
        if isinstance(ctx, Context):
            await ctx.reply(embed=embed)
        elif isinstance(ctx, Interaction):
            await ctx.response.send_message(embed=embed)
        #  self.check_reminders.restart()
        if dt < self.check_reminders.next_iteration.replace(tzinfo=timezone.utc):
            self.bot.loop.create_task(
                self.fire_the_reminder(1 + old_max_id, remind_text, member.id, ctx.channel.id, dt)
            )

    @slh_group.command(description='Remind you about `remind_text` in `remind_time`')
    @app_commands.describe(remind_time='When to remind', remind_text='What to remind about')
    async def me(self, ntr: Interaction, remind_time: str, remind_text: str):
        future_time = time.FutureTime(remind_time)
        await self.add_work(ntr, ntr.user, future_time.dt, remind_text)

    @remind.command(
        usage='<remind_time> <remind_text>',
        aliases=['add'],
    )
    async def me(
            self,
            ctx: Context,
            *,
            when: Annotated[time.FriendlyTimeResult, time.UserFriendlyTime(commands.clean_content, default='…')]
    ):
        """
        Makes bot remind you about `remind_text` in `remind_time`. \
        The bot tries to understand human language, so you can use it like \
        'tomorrow play PA', 'in 3 days uninstall dota'.
        """
        await self.add_work(ctx, ctx.author, when.dt, when.arg)

    @staticmethod
    async def remove_work(ctx: Union[Context, Interaction], member: Member, reminder_id: int):
        with db.session_scope() as ses:
            try:
                my_row = ses.query(db.r).filter_by(userid=member.id).order_by(db.r.id).limit(reminder_id)[0]
            except Exception as e:
                raise commands.BadArgument(
                    'Invalid `reminder_id`: you probably do not have reminder under such `id` number'
                )
            else:
                ses.query(db.r).filter_by(id=my_row.id).delete()
                if isinstance(ctx, Interaction):
                    await ctx.response.send_message(content=Ems.DankApprove, ephemeral=True)
                elif isinstance(ctx, Context):
                    await ctx.message.add_reaction(Ems.PepoG)

    @slh_group.command(description='Remove reminder from your reminders list')
    @app_commands.describe(reminder_id='Reminder id')
    async def remove(self, ntr: Interaction, reminder_id: int): #todo: use range and think about dynamic change
        await self.remove_work(ntr, ntr.user, reminder_id)

    @remind.command()
    async def remove(self, ctx: Context, reminder_id: int):
        """
        Removes reminder under id from your reminders list. \
        You can find *ids* of your reminders in `$remind list` command ;
        """
        await self.remove_work(ctx, ctx.author, reminder_id)

    @staticmethod
    async def list_work(ctx: Union[Context, Interaction], member: Member):
        remind_list = [
            f'{counter}. {time.format_tdR(row.dtime.replace(tzinfo=timezone.utc))}\n{row.name}'
            for counter, row in enumerate(db.session.query(db.r).filter_by(userid=member.id))
        ]
        await send_pages_list(
            ctx,
            remind_list,
            split_size=0,
            author_name=f'{member.display_name}\'s Reminders list',
            author_icon=member.display_avatar.url,
            colour=member.colour
        )

    @slh_group.command(description='Show `@member`s reminders list')
    @app_commands.describe(member='Member to check')
    async def list(self, ntr: Interaction, member: Member = None):
        member = member or ntr.user
        await self.list_work(ntr, member)

    @remind.command(usage='[member=you]')
    async def list(self, ctx: Context, member: Member = None):
        """Shows `@member`'s reminders list ;"""
        member = member or ctx.author
        await self.list_work(ctx, member)

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
        embed = Embed(color=Clr.prpl, description=name).set_author(name='Reminder')
        await self.bot.get_channel(channelid).send(content=answer, embed=embed)
        db.remove_row(db.r, id_)
        self.active_reminders.pop(id_, None)

    @check_reminders.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_group()
    async def todo(self, ctx):
        """Group command about ToDolists, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @todo.command(
        name='remove',
        description='Remove todo bullet from your todo list',
        help=
        'Removes todo bullet under *bullet_id* from your ToDo list.'
        'You can find *ids* of your To Do bullets in `$todo list` command'
    )
    @app_commands.describe(bullet_id='ToDo Bullet id in your list')
    async def remove(self, ctx: Context, bullet_id: int):
        """Read above"""
        with db.session_scope() as ses:
            try:
                my_row = ses.query(db.t).filter_by(userid=ctx.author.id).order_by(db.t.id).limit(bullet_id)[0]
            except Exception as e:
                raise commands.BadArgument(
                    'Invalid `bullet_id`: you probably do not have todo bullet_id under such `id` number'
                )
            else:
                ses.query(db.t).filter_by(id=my_row.id).delete()
                if ctx.interaction:
                    await ctx.reply(content=f'removed {Ems.PepoG}')
                else:
                    await ctx.message.add_reaction(Ems.PepoG)

    @todo.command(
        name='list',
        description="Show `@member` ToDo list ",
        help="Show `@member` ToDo list ;",
        usage='[member=you]'
    )
    @app_commands.describe(member='Member to check')
    async def list(self, ctx: Context, member: Member = None):
        """Read above"""
        member = member or ctx.author
        todo_list = [
            f'{cnt}. {row.name}'
            for cnt, row in enumerate(db.session.query(db.t).filter_by(userid=member.id), start=1)
        ]
        await send_pages_list(
            ctx,
            todo_list,
            split_size=0,
            author_name=f'{member.display_name}\'s ToDo list',
            author_icon=member.display_avatar.url,
            colour=member.colour
        )

    @todo.command(
        name='add',
        description="Add new ToDo Bullet to your ToDo list",
        help='Add new ToDo Bullet to your ToDo list ;'
    )
    @app_commands.describe(todo_text='Text for your ToDo bullet')
    async def add(self, ctx, *, todo_text: str):
        """Read above"""
        db.append_row(db.t, name=todo_text, userid=ctx.author.id)
        if ctx.interaction:
            await ctx.reply(f'added {Ems.PepoG}')
        else:
            await ctx.message.add_reaction(Ems.PepoG)

    @commands.hybrid_command(
        name='afk',
        description='Flag you as afk member'
    )
    @app_commands.describe(afk_text='Your custom afk note')
    async def afk(self, ctx: Context, *, afk_text: str = '...'):
        """Flags you as afk with your custom afk note ;"""
        if db.session.query(db.a).filter_by(id=ctx.author.id).first() is None:
            db.add_row(db.a, ctx.author.id, name=afk_text)
        else:
            db.set_value(db.a, ctx.author.id, name=afk_text)
        self.active_afk[ctx.author.id] = afk_text
        embed = Embed(color=Clr.prpl)
        embed.description = f'{ctx.author.mention}, you are flagged as afk with `afk_text`:\n{afk_text}'
        await ctx.reply(embed=embed)
        try:
            await ctx.author.edit(nick=f'[AFK] | {ctx.author.display_name}')
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.guild is None:  # message.guild.id != Sid.alu:
            return
        if msg.content.startswith('$afk') or msg.content.startswith('~afk'):
            return
        if msg.channel.id in [Cid.logs, Cid.spam_me]:
            return

        for key in self.active_afk:
            if key in msg.raw_mentions:
                guild = self.bot.get_guild(Sid.alu)
                member = guild.get_member(key)
                em = Embed(
                    colour=Clr.prpl,
                    title='Afk note:',
                    description=db.get_value(db.a, key, 'name')
                ).set_author(
                    name=f'Sorry, but {member.display_name} is $afk !',
                    icon_url=member.display_avatar.url
                ).set_footer(
                    text=
                    'PS. Please, consider deleting your ping-message (or just removing ping) '
                    'if you think it will be irrelevant when they come back (I mean seriously)'
                )
                await msg.channel.send(embed=em)

        async def send_non_afk_em(author, channel):
            em = Embed(
                colour=Clr.prpl,
                title='Afk note:',
                description=db.get_value(db.a, author.id, 'name')
            ).set_author(
                name=f'{author.display_name} is no longer afk !',
                icon_url=author.display_avatar.url
            )
            db.remove_row(db.a, author.id)
            self.active_afk.pop(author.id)
            await channel.send(embed=em)
            try:
                await author.edit(nick=db.get_value(db.m, author.id, 'name'))
            except:
                pass

        if msg.author.id in self.active_afk:
            await send_non_afk_em(msg.author, msg.channel)

        if msg.interaction is not None and msg.interaction.user.id in self.active_afk and msg.interaction.name != 'afk':
            await send_non_afk_em(msg.interaction.user, msg.channel)

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
