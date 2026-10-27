from __future__ import annotations

import datetime  # ruff: ignore[typing-only-standard-library-import]
import logging
import textwrap
from typing import TYPE_CHECKING, Any, Self, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from core import AluView, Cog
from shared import clock, fmt
from utils import MISSING, const, errors, pages, times

if TYPE_CHECKING:
    from core import AluInteraction, Bot, Timer

    class RemindTimerData(TypedDict):
        author_id: int
        channel_id: int
        text: str
        message_id: int


__all__ = ("Reminders",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import parsedatetime as pdt
from dateutil.relativedelta import relativedelta

from .errors import AluBotError

if TYPE_CHECKING:
    from core import AluContext, AluInteraction


class ShortTime:
    compiled = re.compile(
        r"""
            (?:(?P<years>[0-9])(?:years?|y))?                      # e.g. 2y
            (?:(?P<months>[0-9]{1,2})(?:months?|mon?))?            # e.g. 2months
            (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?                 # e.g. 10w
            (?:(?P<days>[0-9]{1,5})(?:days?|d))?                   # e.g. 14d
            (?:(?P<hours>[0-9]{1,5})(?:hours?|hr?s?))?             # e.g. 12h
            (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m(?:ins?)?))?    # e.g. 10m
            (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s(?:ecs?)?))?    # e.g. 15s
        """,
        re.VERBOSE,
    )

    discord_fmt = re.compile(r"<t:(?P<ts>[0-9]+)(?:\:?[RFfDdTt])?>")

    dt: datetime.datetime

    def __init__(self, argument: str, *, now: datetime.datetime | None = None) -> None:
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            match = self.discord_fmt.fullmatch(argument)
            if match is not None:
                self.dt = datetime.datetime.fromtimestamp(int(match.group("ts")), tz=datetime.UTC)
                return
            msg = "invalid time provided"
            raise commands.BadArgument(msg)

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.datetime.now(datetime.UTC)
        self.dt = now + relativedelta(**data)  # type: ignore[reportArgumentType]

    @classmethod
    async def convert(cls, ctx: AluContext, argument: str) -> Self:
        return cls(argument, now=ctx.message.created_at)


class HumanTime:
    # en_AU has proper DD MM format
    # https://bear.im/code/parsedatetime/docs/parsedatetime.pdt_locales-pysrc.html#pdtLocale_au.__init__
    # https://bear.im/code/parsedatetime/docs/parsedatetime.pdt_locales-pysrc.html#pdtLocale_base.__init__
    constants = pdt.Constants(localeID="en_AU")
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE, constants=constants)

    def __init__(self, argument: str, *, now: datetime.datetime | None = None) -> None:
        now = now or datetime.datetime.now(datetime.UTC)
        dt, status = self.calendar.parseDT(argument, sourceTime=now)
        dt = dt.replace(tzinfo=datetime.UTC)
        if not status.hasDateOrTime:  # type: ignore[reportAttributeAccess]
            msg = 'invalid time provided, try e.g. "tomorrow" or "3 days"'
            raise commands.BadArgument(msg)

        if not status.hasTime:  # type: ignore[reportAttributeAccess]
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.dt: datetime.datetime = dt
        self._past: bool = dt < now

    @classmethod
    async def convert(cls, ctx: AluContext, argument: str) -> Self:
        return cls(argument, now=ctx.message.created_at)


class Time(HumanTime):
    def __init__(self, argument: str, *, now: datetime.datetime | None = None) -> None:
        try:
            o = ShortTime(argument, now=now)
        except Exception:  # ruff: ignore[blind-except]
            super().__init__(argument)
        else:
            self.dt = o.dt
            self._past = False


class FutureTime(Time):
    def __init__(self, argument: str, *, now: datetime.datetime | None = None) -> None:
        super().__init__(argument, now=now)

        if self._past:
            msg = "This time is in the past"
            raise commands.BadArgument(msg)


class BadTimeTransform(app_commands.AppCommandError, AluBotError):  # ruff: ignore[error-suffix-on-exception-name]
    pass


class TimeTransformer(app_commands.Transformer):
    @override
    async def transform(self, interaction: AluInteraction, value: str) -> datetime.datetime:
        # fix timezone thing
        # tzinfo = datetime.timezone.utc
        # reminder = interaction.client.get_cog('Reminder')
        # if reminder is not None:
        #     tzinfo = await reminder.get_tzinfo(interaction.user.id)

        now = interaction.created_at  # .astimezone(tzinfo)
        if not now.tzinfo:
            now = now.replace(tzinfo=datetime.UTC)

        try:
            short = ShortTime(value, now=now)
        except commands.BadArgument:
            try:
                human = FutureTime(value, now=now)
            except commands.BadArgument as e:
                raise BadTimeTransform(str(e)) from None
            else:
                return human.dt
        else:
            return short.dt


class FriendlyTimeResult:
    dt: datetime.datetime
    arg: str

    __slots__ = ("arg", "dt")

    def __init__(self, dt: datetime.datetime) -> None:
        self.dt = dt
        self.arg = ""

    @override
    def __repr__(self) -> str:
        return f"<FriendlyTimeResult dt={self.dt} arg={self.arg}>"

    async def ensure_constraints(
        self,
        ctx: AluContext,
        uft: UserFriendlyTime,
        now: datetime.datetime,
        remaining: str,
    ) -> None:
        if self.dt < now:
            msg = "This time is in the past."
            raise commands.BadArgument(msg)

        if not remaining:
            if uft.default is None:
                msg = "Missing argument after the time."
                raise commands.BadArgument(msg)
            remaining = uft.default

        if uft.converter:
            self.arg = await uft.converter.convert(ctx, remaining)
        else:
            self.arg = remaining


class UserFriendlyTime(commands.Converter[FriendlyTimeResult]):
    """That way quotes aren't absolutely necessary."""

    def __init__(
        self,
        converter: type[commands.Converter[str]] | commands.Converter[str] | None = None,
        *,
        default: Any = None,
    ) -> None:
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            msg = "commands.Converter subclass necessary."
            raise TypeError(msg)

        self.converter: commands.Converter[str] | None = converter
        self.default: Any = default


class SnoozeModal(discord.ui.Modal, title="Snooze"):
    duration = discord.ui.TextInput(label="Duration", placeholder="10 minutes", default="10 minutes", min_length=2)

    def __init__(self, parent: ReminderView, timer: Timer[RemindTimerData]) -> None:
        super().__init__()
        self.parent: ReminderView = parent
        self.timer: Timer[RemindTimerData] = timer

    @override
    async def on_submit(self, interaction: AluInteraction) -> None:
        try:
            when = times.FutureTime(str(self.duration)).dt
        except commands.BadArgument:  # Exception
            msg = 'Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"'
            await interaction.response.send_message(msg, ephemeral=True)
            return

        self.parent.snooze.disabled = True
        await interaction.response.edit_message(view=self.parent)

        zone = await interaction.client.tz_manager.get_timezone(interaction.user.id)
        refreshed = await interaction.client.timers.create(
            event=self.timer.event,
            expires_at=when,
            created_at=interaction.created_at,
            timezone=zone or "UTC",
            data=self.timer.data,
        )
        author_id = self.timer.data.get("author_id")
        text = self.timer.data.get("text")
        delta = clock.human_timedelta(when, source=refreshed.created_at)
        msg = f"Alright <@{author_id}>, I've snoozed your reminder for {delta}: {text}"
        await interaction.followup.send(msg, ephemeral=True)


class SnoozeButton(discord.ui.Button["ReminderView"]):
    def __init__(self, cog: Reminders, timer: Timer[RemindTimerData]) -> None:
        super().__init__(label="Snooze", style=discord.ButtonStyle.blurple)
        self.timer: Timer[RemindTimerData] = timer
        self.cog: Reminders = cog

    @override
    async def callback(self, interaction: AluInteraction) -> Any:
        assert self.view is not None
        await interaction.response.send_modal(SnoozeModal(self.view, self.timer))


class ReminderView(AluView, name="Reminder Buttons"):
    def __init__(self, *, url: str, timer: Timer[RemindTimerData], cog: Reminders, author_id: int) -> None:
        super().__init__(timeout=300, author_id=author_id)
        self.timer: Timer[RemindTimerData] = timer
        self.cog: Reminders = cog
        self.author_id: int = author_id
        self.add_item(discord.ui.Button(url=url, label="Go to original message"))

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This snooze button is not for you, sorry!", ephemeral=True)
            return False
        return True

    @override
    async def on_timeout(self) -> None:
        self.snooze.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Snooze", style=discord.ButtonStyle.blurple)
    async def snooze(self, interaction: AluInteraction, button: discord.ui.Button[Self]) -> None:
        """Make a non-anonymous confession."""
        await interaction.response.send_modal(SnoozeModal(self, self.timer))


class Reminders(Cog):
    """Remind yourself of something at sometime."""

    @override
    async def cog_load(self) -> None:
        self.bot.instantiate_tz_manager()
        await super().cog_load()

    remind_group = app_commands.Group(
        name="remind",
        description="Set reminders to ping you when the time comes.",
    )

    @remind_group.command(name="set")
    async def reminder_set(
        self,
        interaction: AluInteraction,
        when: app_commands.Transform[datetime.datetime, times.TimeTransformer],
        text: str = "...",
    ) -> None:
        """Sets a reminder to remind you of something at a specific time.

        Parameters
        ----------
        when
            When to be reminded of something, in GMT.
        text
            What to be reminded of.
        """
        if len(text) >= 1500:
            msg = "Reminder must be fewer than 1500 characters."
            raise errors.BadArgument(msg)

        assert interaction.channel

        zone = await self.bot.tz_manager.get_timezone(interaction.user.id)
        data: RemindTimerData = {
            "author_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "text": text,
            "message_id": interaction.id,  # synthetic, it's invalid id
        }
        timer = await self.bot.timers.create(
            event="reminder",
            expires_at=when,
            created_at=interaction.created_at,
            timezone=zone or "UTC",
            data=data,
        )
        delta = clock.human_timedelta(when, source=timer.created_at)
        embed = discord.Embed(
            color=interaction.user.color, description=f"in {delta} — {fmt.format_dt_tdR(when)}\n{text}"
        ).set_author(
            name=f"Reminder for {interaction.user.display_name} is created", icon_url=interaction.user.display_avatar
        )
        if zone is None:
            mention = interaction.client.tree.find_mention("timezone set")
            embed.add_field(
                name="P.S.",
                value=f"\N{ELECTRIC LIGHT BULB} You can set your timezone with {mention}",
            )
        await interaction.response.send_message(embed=embed)

    # @remind.command(name="me", with_app_command=False)
    # async def remind_me(
    #     self,
    #     ctx: AluContext,
    #     *,
    #     when_and_what: Annotated[
    #         times.FriendlyTimeResult, times.UserFriendlyTime(commands.clean_content, default="...")
    #     ],
    # ) -> None:
    #     """Reminds you of something after a certain amount of time. \
    #     The input can be any direct date (i.e. DD/MM/YYYY) or a human \
    #     readable offset. Examples:
    #     * "next thursday at 3pm do something funny"
    #     * "do the dishes tomorrow"
    #     * "in 50 minutes do the thing"
    #     * "2d unmute someone"
    #     Times are assumed in UTC.
    #     """
    #     await self.remind_helper(ctx, dt=when_and_what.dt, text=when_and_what.arg)

    @remind_group.command(name="list")
    async def remind_list(self, interaction: AluInteraction) -> None:
        """Shows a list of your current reminders."""
        query = """
            SELECT id, expires_at, extra #>> '{args,2}'
            FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1
            ORDER BY expires_at
        """
        records = await self.bot.pool.fetch(query, str(interaction.user.id))

        string_list = []
        for _id, expires_at, message in records:
            shorten = textwrap.shorten(message, width=512)
            string_list.append(f"\N{BLACK CIRCLE} {_id}: {fmt.format_dt_tdR(expires_at)}\n{shorten}")

        pgs = pages.EmbedDescriptionPaginator(
            interaction,
            string_list,
            per_page=10,
            template={
                "color": interaction.user.color.value,
                "author": {
                    "name": f"{interaction.user.display_name}'s Reminders list",
                    "icon_url": interaction.user.display_avatar.url,
                },
            },
        )
        await pgs.start()

    # TODO: finish this?
    # async def remind_delete_id_autocomplete(
    #         self,
    #         interaction: AluInteraction,
    #         current: str
    # ) -> List[app_commands.Choice[str]]:
    #     """idk if it is a good idea"""
    #     query = """ SELECT id, expires, extra #>> '{args,2}'
    #                 FROM reminders
    #                 WHERE event = 'reminder'
    #                 AND data #>> '{author_id}' = $1
    #                 ORDER BY similarity(extra #>> '{args, 2}', $2) DESC
    #                 LIMIT 10
    #             """
    #     records = await self.bot.pool.fetch(query, str(ntr.user.id), current)
    #     choice_list = [
    #         (_id, f"{_id}: ({expires.strftime('%d/%b/%y')}) {textwrap.shorten(message, width=100)}")
    #         for _id, expires, message in records
    #     ]
    #     return [app_commands.Choice(name=m, value=n) for n, m in choice_list if current.lower() in m.lower()]

    @remind_group.command(name="delete")
    # @app_commands.autocomplete(id=remind_delete_id_autocomplete)  # type: ignored
    # @app_commands.describe(id='either input a number of reminder id or choose it from suggestion^')
    async def remind_delete(self, interaction: AluInteraction, id_: int) -> None:
        """Deletes a reminder by its ID.

        To get a reminder ID, use the reminder list command or autocomplete for slash command.

        You must own the reminder to delete it, obviously.
        """
        query = """
            DELETE FROM timers
            WHERE id=$1
            AND event = 'reminder'
            AND data #>> '{author_id}' = $2;
        """
        status = await interaction.client.pool.execute(query, id_, str(interaction.user.id))
        if status == "DELETE 0":
            embed = discord.Embed(
                color=const.Color.error,
                description="Could not delete any reminders with that ID.",
            ).set_author(name="NotFound")
            await interaction.response.send_message(embed=embed)
            return

        self.bot.timers.check_reschedule(id_)

        embed = discord.Embed(description="Successfully deleted reminder.", color=const.Color.prpl)
        await interaction.response.send_message(embed=embed)

    @remind_group.command(name="clear")
    async def reminder_clear(self, interaction: AluInteraction) -> None:
        """Clears all reminders you have set."""
        # For UX purposes this has to be two queries.
        query = """
            SELECT COUNT(*) FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1;
        """
        author_id = str(interaction.user.id)
        total: int = await interaction.client.pool.fetchval(query, author_id)
        if total == 0:
            no_reminders_embed = discord.Embed(
                color=interaction.user.color,
                description="You do not have any reminders to delete.",
            )
            await interaction.response.send_message(embed=no_reminders_embed)
            return

        confirm_embed = discord.Embed(
            color=interaction.user.color,
            description=f"Are you sure you want to delete {fmt.plural(total):reminder}?",
        )
        if not await interaction.client.disambiguator.confirm(interaction, embed=confirm_embed):
            return

        query = """
            DELETE FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1;
        """  # ruff: ignore[missing-f-string-syntax]
        await interaction.client.pool.execute(query, author_id)

        # Check if the current timer is the one being cleared and cancel it if so
        current_timer = self.bot.timers.current_timer
        if current_timer and current_timer.event == "reminder" and current_timer.data:
            author_id = current_timer.data.get("author_id")
            if author_id == interaction.user.id:
                self.bot.timers.reschedule()

        response_embed = discord.Embed(
            color=interaction.user.color,
            description=f"Successfully deleted {fmt.plural(total):reminder}.",
        )
        await interaction.response.send_message(embed=response_embed)

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer: Timer[RemindTimerData]) -> None:
        log.debug('Timer Event "on_reminder_timer_complete" starts now')

        author_id = timer.data["author_id"]
        channel_id = timer.data["channel_id"]
        text = timer.data["text"]
        message_id = timer.data["message_id"]

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            log.warning("Discarding channel %s as it's not found.", channel_id)
            return

        guild_id = channel.guild.id if isinstance(channel, discord.TextChannel | discord.Thread) else "@me"
        content = f"<@{author_id}>, {discord.utils.format_dt(timer.created_at, style='R')}\n{text}"
        view = MISSING

        if message_id:
            url = f"https://discord.com/channels/{guild_id}/{channel.id}/{message_id}"
            view = ReminderView(url=url, timer=timer, cog=self, author_id=author_id)

        try:
            msg = await channel.send(content, view=view)  # ty: ignore[unresolved-attribute]
        except discord.HTTPException:
            pass
        else:
            if view is not MISSING:
                view.message = msg

        await self.bot.timers.cleanup(timer.id)


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Reminders(bot))
