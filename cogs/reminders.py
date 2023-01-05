"""
# This code is licensed MPL v2 from Rapptz/RoboDanny

Most of the code below is inspired/looked/learnt from @Rapptz\'s RoboDanny
https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py
It's too good not to learn from for a pleb programmer like me.
I had to rewrite half of the bot after reading @Danny's `reminder.py` :D
"""
from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union, List
from typing_extensions import Annotated

import asyncio
import datetime
import logging

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from .utils import formats, times
from .utils.context import Context
from .utils.database import DRecord
from .utils.distools import send_pages_list
from .utils.var import Ems, Clr

if TYPE_CHECKING:
    from typing_extensions import Self
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SnoozeModal(discord.ui.Modal, title='Snooze'):
    duration = discord.ui.TextInput(label='Duration', placeholder='10 minutes', default='10 minutes', min_length=2)

    def __init__(self, parent: ReminderView, cog: Reminder, timer: Timer) -> None:
        super().__init__()
        self.parent: ReminderView = parent
        self.timer: Timer = timer
        self.cog: Reminder = cog

    async def on_submit(self, ntr: discord.Interaction) -> None:
        try:
            when = times.FutureTime(str(self.duration)).dt
        except commands.BadArgument:  # Exceptiom
            await ntr.response.send_message(
                'Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"', ephemeral=True
            )
            return

        self.parent.snooze.disabled = True
        await ntr.response.edit_message(view=self.parent)

        refreshed = await self.cog.create_timer(
            when, self.timer.event, *self.timer.args, **self.timer.kwargs, created=ntr.created_at
        )
        author_id, _, message = self.timer.args
        delta = formats.human_timedelta(when, source=refreshed.created_at)
        await ntr.followup.send(
            f"Alright <@{author_id}>, I've snoozed your reminder for {delta}: {message}", ephemeral=True
        )


class SnoozeButton(discord.ui.Button['ReminderView']):
    def __init__(self, cog: Reminder, timer: Timer) -> None:
        super().__init__(label='Snooze', style=discord.ButtonStyle.blurple)
        self.timer: Timer = timer
        self.cog: Reminder = cog

    async def callback(self, interaction: discord.Interaction) -> Any:
        assert self.view is not None
        await interaction.response.send_modal(SnoozeModal(self.view, self.cog, self.timer))


class ReminderView(discord.ui.View):
    message: discord.Message

    def __init__(self, *, url: str, timer: Timer, cog: Reminder, author_id: int) -> None:
        super().__init__(timeout=300)
        self.author_id: int = author_id
        self.snooze = SnoozeButton(cog, timer)
        self.add_item(discord.ui.Button(url=url, label='Go to original message'))
        self.add_item(self.snooze)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message('This snooze button is not for you, sorry!', ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.snooze.disabled = True
        await self.message.edit(view=self)


class RemindRecord(DRecord):
    id: int
    event: str
    expires: datetime.datetime
    created: datetime.datetime
    extra: dict[str, Any]

    # cannot create Record instances for proper typing though :thinking:


class Timer:
    __slots__ = (
        'id',
        'event',
        'expires',
        'created_at',
        'args',
        'kwargs'
    )

    def __init__(self, *, record: Union[RemindRecord, dict]):
        self.id: int = record['id']

        extra = record['extra']
        self.event: str = record['event']
        self.expires: datetime.datetime = record['expires']
        self.created_at: datetime.datetime = record['created']
        self.args: Sequence[Any] = extra.get('args', [])
        self.kwargs: dict[str, Any] = extra.get('kwargs', {})

    def __eq__(self, other: object) -> bool:
        try:
            return self.id == other.id  # type: ignore
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f'<Timer event={self.event} expires={self.expires} created={self.created_at}>'

    @classmethod
    def temporary(
            cls,
            *,
            event: str,
            expires: datetime.datetime,
            created: datetime.datetime,
            args: Sequence[Any],
            kwargs: dict[str, Any]
    ) -> Self:
        """Initiate the timer without the database before deciding to put it in"""
        pseudo_record = {
            'id': None,
            'event': event,
            'expires': expires,
            'created': created,
            'extra': {'args': args, 'kwargs': kwargs}
        }
        return cls(record=pseudo_record)

    @property
    def format_dt_R(self) -> str:
        return discord.utils.format_dt(
            self.created_at.replace(tzinfo=datetime.timezone.utc), style='R'
        )

    @property
    def author_id(self) -> Optional[int]:
        if self.args:
            return int(self.args[0])
        return None


class Reminder(commands.Cog):
    """Remind yourself of something at sometime"""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

        self._have_data = asyncio.Event()
        self._current_timer: Optional[Timer] = None
        self._task = bot.loop.create_task(self.dispatch_timers())

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.DankG)

    async def cog_unload(self) -> None:
        self._task.cancel()

    async def cog_command_error(self, ctx: Context, error: commands.CommandError):
        print(error)
        pass

    async def get_active_timer(self, *, days: int = 7) -> Optional[Timer]:
        query = 'SELECT * FROM reminders WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1;'
        record = await self.bot.pool.fetchrow(query, datetime.timedelta(days=days))
        return Timer(record=record) if record else None

    async def wait_for_active_timers(self, *, days: int = 7) -> Timer:
        timer = await self.get_active_timer(days=days)
        log.debug(f'RE | {timer}')
        if timer is not None:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()

        return await self.get_active_timer(days=days)  # type: ignore  # bcs at this point we always have data

    async def call_timer(self, timer: Timer) -> None:
        query = 'DELETE FROM reminders WHERE id=$1'
        await self.bot.pool.execute(query, timer.id)

        event_name = f'{timer.event}_timer_complete'
        self.bot.dispatch(event_name, timer)

    async def dispatch_timers(self) -> None:
        try:
            while not self.bot.is_closed():
                # can `asyncio.sleep` only for up to ~48 days reliably,
                # so we cap it at 40 days, see: http://bugs.python.org/issue20493
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                log.debug(f'RE | {timer}')
                now = datetime.datetime.utcnow()  # even tho it's `__utc__now()` - it's not timezone-aware

                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def short_timer_optimisation(self, seconds: float, timer: Timer) -> None:
        await asyncio.sleep(seconds)
        event_name = f'{timer.event}_timer_complete'
        self.bot.dispatch(event_name, timer)

    async def create_timer(self, when: datetime.datetime, event: str, /, *args: Any, **kwargs: Any) -> Timer:
        """Creates a timer.

        Parameters
        -----------
        when: datetime.datetime
            When the timer should fire.
        event: str
            The name of the event to trigger.
            Will transform to 'on_{event}_timer_complete'.
        *args
            Arguments to pass to the event
        **kwargs
            Keyword arguments to pass to the event
        created: datetime.datetime
            Special keyword-only argument to use as the creation time.
            Should make the timedeltas a bit more consistent.

        Note
        ------
        Arguments and keyword arguments must be JSON serializable.

        Returns
        --------
        :class:`Timer`
        """

        now = kwargs.pop('created', discord.utils.utcnow())

        timer = Timer.temporary(event=event, args=args, kwargs=kwargs, expires=when, created=now)
        delta = (when - now).total_seconds()
        if delta <= 60:
            # a shortcut for small timers
            self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        query = """ INSERT INTO reminders (event, extra, expires, created)
                    VALUES ($1, $2::jsonb, $3, $4)
                    RETURNING id;
                """

        row = await self.bot.pool.fetchrow(query, event, {'args': args, 'kwargs': kwargs}, when, now)
        timer.id = row[0]

        # only set the data check if it can be waited on
        if delta <= (86400 * 40):  # 40 days
            self._have_data.set()

        # check if this timer is earlier than our currently run timer
        if self._current_timer and when < self._current_timer.expires:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        return timer

    async def remind_helper(
            self,
            ctx: Context,
            *,
            dt: datetime.datetime,
            text: str
    ):
        """Remind helper so we don't duplicate"""
        timer = await self.create_timer(
            dt,
            'reminder',
            ctx.author.id,
            ctx.channel.id,
            text,
            created=ctx.message.created_at,
            message_id=ctx.message.id
        )
        delta = formats.human_timedelta(dt, source=timer.created_at)
        e = discord.Embed(colour=ctx.author.colour)
        e.set_author(name=f'Reminder for {ctx.author.display_name} is created', icon_url=ctx.author.display_avatar)
        e.description = f'in {delta} — {formats.format_dt_tdR(dt)}\n{text}'
        await ctx.reply(embed=e)

    @commands.hybrid_group(aliases=['reminder', 'remindme'], usage='<when>')
    async def remind(
            self,
            ctx: Context,
            *,
            when: Annotated[
                times.FriendlyTimeResult,
                times.UserFriendlyTime(commands.clean_content, default='...')  # type: ignore # pycharm things
            ]
    ):
        """Main group of remind command. Just a way to make an alias for 'remind me' with a space."""
        await self.remind_helper(ctx, dt=when.dt, text=when.arg)

    @remind.app_command.command(name='set')
    @app_commands.describe(when='When to be reminded of something, in GMT', text='What to be reminded of')
    async def reminder_set(
            self,
            ntr: discord.Interaction,
            when: app_commands.Transform[datetime.datetime, times.TimeTransformer],
            text: str = '...'
    ):
        """Sets a reminder to remind you of something at a specific time"""
        ctx = await Context.from_interaction(ntr)
        await self.remind_helper(ctx, dt=when, text=text)

    @reminder_set.error
    async def reminder_set_error(self, ntr: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, times.BadTimeTransform):
            await ntr.response.send_message(str(error), ephemeral=True)

    @remind.command(name='me', with_app_command=False)
    async def remind_me(
            self,
            ctx: Context,
            *,
            when: Annotated[
                times.FriendlyTimeResult,
                times.UserFriendlyTime(commands.clean_content, default='...')  # type: ignore # pycharm things
            ]
    ):
        """Reminds you of something after a certain amount of time.

        The input can be any direct date (i.e. DD/MM/YYYY) or a human
        readable offset. Example

        - 'next thursday at 3pm do something funny'
        - 'do the dishes tomorrow'
        - 'in 50 minutes do the thing'
        - '2d unmute someone'

        Times are assumed in UTC.
        """
        await self.remind_helper(ctx, dt=when.dt, text=when.arg)

    @remind.command(name='list', ignore_extra=False)
    async def remind_list(self, ctx: Context):
        """Shows a list of your current reminders"""
        query = """ SELECT id, expires, extra #>> '{args,2}'
                    FROM reminders
                    WHERE event = 'reminder'
                    AND extra #>> '{args,0}' = $1
                    ORDER BY expires
                """
        records = await ctx.pool.fetch(query, str(ctx.author.id))

        string_list = []
        for _id, expires, message in records:
            shorten = textwrap.shorten(message, width=512)
            string_list.append(f'\N{BLACK CIRCLE} {_id}: {formats.format_dt_tdR(expires)}\n{shorten}')

        await send_pages_list(
            ctx,
            string_list,
            split_size=10,
            author_name=f'{ctx.author.display_name}\'s Reminders list',
            author_icon=ctx.author.display_avatar.url,
            colour=ctx.author.colour
        )

    # async def remind_delete_id_autocomplete(
    #         self,
    #         ntr: discord.Interaction,
    #         current: str
    # ) -> List[app_commands.Choice[str]]:
    #     """idk if it is a good idea"""
    #     query = """ SELECT id, expires, extra #>> '{args,2}'
    #                 FROM reminders
    #                 WHERE event = 'reminder'
    #                 AND extra #>> '{args,0}' = $1
    #                 ORDER BY similarity(extra #>> '{args, 2}', $2) DESC
    #                 LIMIT 10
    #             """
    #     records = await self.bot.pool.fetch(query, str(ntr.user.id), current)
    #     choice_list = [
    #         (_id, f"{_id}: ({expires.strftime('%d/%b/%y')}) {textwrap.shorten(message, width=100)}")
    #         for _id, expires, message in records
    #     ]
    #     return [app_commands.Choice(name=m, value=n) for n, m in choice_list if current.lower() in m.lower()]

    @remind.command(name='delete', aliases=['remove', 'cancel'], ignore_extra=True)
    # @app_commands.autocomplete(id=remind_delete_id_autocomplete)  # type: ignore
    # @app_commands.describe(id='either input a number of reminder id or choose it from suggestion^')
    async def remind_delete(self, ctx: Context, *, id: int):
        """Deletes a reminder by its ID.

        To get a reminder ID, use the reminder list command or autocomplete for slash command.

        You must own the reminder to delete it, obviously.
        """
        query = """ DELETE FROM reminders
                    WHERE id=$1
                    AND event = 'reminder'
                    AND extra #>> '{args,0}' = $2;
                """

        status = await ctx.pool.execute(query, id, str(ctx.author.id))
        if status == 'DELETE 0':
            e = discord.Embed(description='Could not delete any reminders with that ID.', colour=Clr.error)
            e.set_author(name='IDError')
            return await ctx.reply(embed=e)

        # if the current timer is being deleted
        if self._current_timer and self._current_timer.id == id:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        e = discord.Embed(description='Successfully deleted reminder.', colour=Clr.prpl)
        await ctx.reply(embed=e)

    @remind.command(name='clear', ignore_extra=False)
    async def reminder_clear(self, ctx: Context):
        """Clears all reminders you have set."""

        # For UX purposes this has to be two queries.

        query = """ SELECT COUNT(*) FROM reminders
                    WHERE event = 'reminder'
                    AND extra #>> '{args,0}' = $1;
                """

        author_id = str(ctx.author.id)
        total: int = await ctx.pool.fetchval(query, author_id)
        if total == 0:
            e = discord.Embed(description='You do not have any reminders to delete.', colour=ctx.author.colour)
            return await ctx.reply(embed=e)

        e = discord.Embed(colour=ctx.author.colour)
        e.description = f'Are you sure you want to delete {formats.Plural(total):reminder}?'
        confirm = await ctx.prompt(embed=e)
        if not confirm:
            return await ctx.reply('Aborting', ephemeral=True)

        query = """ DELETE FROM reminders 
                    WHERE event = 'reminder' 
                    AND extra #>> '{args,0}' = $1;
                """
        await ctx.pool.execute(query, author_id)

        # Check if the current timer is the one being cleared and cancel it if so
        if self._current_timer and self._current_timer.author_id == ctx.author.id:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        e.description = f'Successfully deleted {formats.Plural(total):reminder}.'
        await ctx.reply(embed=e)

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer: Timer):
        log.debug('RE | on_reminder_timer_complete starts now')
        author_id, channel_id, message = timer.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        guild_id = channel.guild.id if isinstance(channel, (discord.TextChannel, discord.Thread)) else '@me'
        message_id = timer.kwargs.get('message_id')
        msg = f'<@{author_id}>, {timer.format_dt_R}: {message}'
        view = discord.utils.MISSING

        if message_id:
            url = f'https://discord.com/channels/{guild_id}/{channel.id}/{message_id}'
            view = ReminderView(url=url, timer=timer, cog=self, author_id=author_id)

        try:
            msg = await channel.send(msg, view=view)  # type: ignore
        except discord.HTTPException:
            return
        else:
            if view is not discord.utils.MISSING:
                view.message = msg


async def setup(bot: AluBot):
    await bot.add_cog(Reminder(bot))
