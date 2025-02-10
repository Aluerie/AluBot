from __future__ import annotations

import asyncio
import datetime
import itertools
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Self, TypedDict, TypeVar, override

import asyncpg
import discord

if TYPE_CHECKING:
    from .bot import AluBot

__all__: tuple[str, ...] = (
    "Timer",
    "TimerManager",
    "TimerRow",
)

# small issue with TypedDict's is why we need to use Mapping here over dict[str, Any]
# https://github.com/python/mypy/issues/4976#issuecomment-384719025
type TimerData = Mapping[str, Any]
TimerDataT = TypeVar("TimerDataT", bound=TimerData)


class TimerRow[TimerDataT](TypedDict):
    """Database Row for Timers.

    Contains basic data about the timers required for its completion and
    custom generic data to be used by the listener dispatching the timer.
    """

    id: int
    event: str
    expires_at: datetime.datetime
    created_at: datetime.datetime
    timezone: str
    data: TimerDataT


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Timer[TimerDataT]:
    """Timer represent delayed tasks.

    Practically, serves same purpose as `ext.tasks`, but allows to dynamically manage timer-tasks on the fly
    via the database such as reminders, birthdays, etc.

    Also due to database usage there is less pain about restarting the bot in the timers
    Tt's useful for such tasks as patch notes checkers as
    they don't need to do an extra fetch from the database on each bot's restart.
    Also such timers can be consistently periodic through bot's restarts.

    Attributes
    ----------
    id: int
        Represents unique ID of the timer. If negative, then the timer is temporary and short-lived.
    event: str
        The event name to trigger when the timer expires.
        This also defines event's name for the timer to be dispatched to (self.event_name).
        The listener can be formatted as follows (with example `.event` being named "reminder"):
        ```py
        @commands.Cog.listener()  # or .listener("on_reminder_timer_complete")
            async def on_reminder_timer_complete(self, timer: Timer):
        ```
    created_at: datetime.datetime
        The datetime the timer was created.
    expires_at: datetime.datetime
        The datetime the timer expires and triggers the event.
    timezone: str
        The timezone string for the `expires_at` attribute.
        PostgreSQL/AsyncPG structure essentially require us to have extra timezone string
        when working with aware `datetime.datetime` objects.
    data: TimerDataT
        A dictionary of keyword arguments to pass to the `create_timer` method.

    """

    __slots__ = (
        "_cs_event_name",
        "created_at",
        "data",
        "event",
        "expires_at",
        "id",
        "timezone",
    )

    def __init__(self, *, row: TimerRow[TimerDataT]) -> None:
        self.id: int = row["id"]
        self.event: str = row["event"]
        self.expires_at: datetime.datetime = row["expires_at"].astimezone(datetime.UTC)
        self.created_at: datetime.datetime = row["created_at"].astimezone(datetime.UTC)
        self.timezone: str = row["timezone"]
        self.data: TimerDataT = row["data"]

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Timer) and self.id == other.id

    @override
    def __hash__(self) -> int:
        return hash(self.id)

    @override
    def __repr__(self) -> str:
        return f"<Timer id={self.id} event={self.event} expires_at={self.expires_at} created_at={self.created_at}>"

    @classmethod
    def temporary(
        cls,
        *,
        id: int,  # noqa: A002
        event: str,
        expires_at: datetime.datetime,
        created_at: datetime.datetime,
        timezone: str,
        data: TimerDataT,
    ) -> Self:
        """Initiate the timer without the database before deciding to put it in."""
        pseudo_row: TimerRow[TimerDataT] = {
            "id": id,
            "event": event,
            "expires_at": expires_at,
            "created_at": created_at,
            "timezone": timezone,
            "data": data,
        }
        return cls(row=pseudo_row)

    @discord.utils.cached_slot_property("_cs_event_name")
    def event_name(self) -> str:
        """Returns the timer's event name."""
        return f"{self.event}_timer_complete"


class TimerManager:
    """Class to create and manage timers.

    Sources
    -------
    * Rapptz/RoboDanny (license MPL v2), Reminder cog:
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py
    * DuckBot-Discord/DuckBot, rewrite branch (license MPL v2), TimerManager:
        https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/bases/timer.py
    """

    __slots__: tuple[str, ...] = (
        "_current_timer",
        "_have_data",
        "_scheduling_task",
        "_skipped_timer_ids",
        "_temporary_timer_id_count",
        "bot",
        "name",
    )

    def __init__(self, *, bot: AluBot) -> None:
        self.bot: AluBot = bot

        self._temporary_timer_id_count: int = -1
        """Not really useful attribute, but just so `__eq__` can properly work on temporary timers."""
        self._skipped_timer_ids: set[int] = set()

        self._have_data = asyncio.Event()
        self._current_timer: Timer[TimerData] | None = None
        self._scheduling_task = self.bot.loop.create_task(self.dispatch_timers())

    async def dispatch_timers(self) -> None:
        """The main dispatch timers loop.

        This will wait for the next timer to expire and dispatch the bot's event with its data.
        Please note if you use this class, you need to cancel the task when you're done with it.
        """
        await self.bot.wait_until_ready()

        try:
            while not self.bot.is_closed():
                # can `asyncio.sleep` only for up to ~48 days reliably,
                # so we cap it at 40 days, see: http://bugs.python.org/issue20493
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                log.debug("Current_timer = %s", timer)

                # Double check if there exist a listener for the current timer
                available_listeners = [
                    listener[0]
                    for listener in itertools.chain.from_iterable(cog.get_listeners() for cog in self.bot.cogs.values())
                ]
                if not self.bot.test and f"on_{timer.event_name}" not in available_listeners:
                    # the listener existence is NOT confirmed therefore it is not safe to dispatch the event
                    # notify developers that there is no proper listener for the timer
                    desc = (
                        f"The timer with `event={timer.event_name}` is to fire "
                        "but there is no appropriate listener loaded atm."
                    )
                    embed = discord.Embed(colour=discord.Colour.dark_red(), description=desc)
                    await self.bot.spam_webhook.send(content=self.bot.error_ping, embed=embed)

                now = datetime.datetime.now(datetime.UTC)

                if timer.expires_at >= now:
                    to_sleep = (timer.expires_at - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.reschedule_timers()
        except Exception as exc:  # noqa: BLE001
            embed = discord.Embed(
                colour=0xFF8243,
                title="Dispatching Timers Error",
            ).set_footer(text=f"{self.__class__.__name__}.dispatch_timers")
            await self.bot.exc_manager.register_error(exc, embed)

    async def wait_for_active_timers(self, *, days: int = 7) -> Timer[TimerData]:
        """Wait for a timer that has expired.

        This will wait until a timer is expired and should be dispatched.

        Parameters
        ----------
        days: int
            Number of days to look into.

        Returns
        -------
        Timer[TimerMapping]
            The timer that is expired and should be dispatched.

        """
        timer = await self.get_active_timer(days=days)

        if timer is not None:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()

        return await self.get_active_timer(days=days)  # type: ignore[reportReturnType]  # at this point we always have data

    async def call_timer(self, timer: Timer[TimerData]) -> None:
        """Call an expired timer to dispatch it.

        Parameters
        ----------
        timer: Timer[TimerData]
            The timer to dispatch.

        """
        log.debug("Calling and Dispatching the timer %s with event %s", timer.id, timer.event)

        self._skipped_timer_ids.add(timer.id)
        self.bot.dispatch(timer.event_name, timer)

    async def get_active_timer(self, *, days: int = 7) -> Timer[TimerData] | None:
        """Get the most current active timer in the database.

        This timer is expired and should be dispatched.

        Parameters
        ----------
        days: int
            The number of days to look back.

        Returns
        -------
        Timer[TimerData] | None
            The timer that is expired and should be dispatched.

        """
        query = """
            SELECT * FROM timers
            WHERE (expires_at AT TIME ZONE 'UTC' AT TIME ZONE timezone) < (CURRENT_TIMESTAMP + $1::interval)
                AND NOT id=ANY($2)
            ORDER BY expires_at
            LIMIT 1;
        """
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(
            query, datetime.timedelta(days=days), self._skipped_timer_ids
        )
        if record:
            return Timer(row=record)
        return None

    async def create_timer(
        self,
        *,
        event: str,
        expires_at: datetime.datetime,
        created_at: datetime.datetime | None = None,
        timezone: str | None = None,
        data: TimerData,
    ) -> Timer[TimerData]:
        """Creates a timer.

        Used to create a timer and put it into a database, or just dispatch it if it's a short timer.

        Parameters
        ----------
        event: str
            The name of the event to trigger. Will transform to 'on_{event}_timer_complete'.
        expires_at: datetime.datetime
            When the timer should fire.
        created_at: datetime.datetime
            Special keyword-only argument to use as the creation time.
            Should make the time-deltas a bit more consistent.
        timezone: str
            IANA alias. Special keyword-only argument to use as the timezone for the
            expiry time. This automatically adjusts the expiry time to be
            in the future, should it be in the past.
        data: TimerData
            data to pass to the timer to json it up and keep it in the database.
            This should be used when dispatching timer event.

        Note
        ------
        Arguments and keyword arguments must be JSON serializable.

        Returns
        -------
        Timer[TimerData]

        """
        # Maybe, we don't need these two, I'm just scared.
        if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
            # then expires_at is naive
            await self.bot.send_warning(f"`{expires_at=}` for timer with `{event=}` is timezone-naive.")
        if created_at and (created_at.tzinfo is None or created_at.tzinfo.utcoffset(created_at) is None):
            # then created_at is naive
            await self.bot.send_warning(f"`{created_at=}` for timer with `{event=}` is timezone-naive.")

        expires_at = expires_at.astimezone(datetime.UTC)
        log.debug("Creating %s timer for %s", event, expires_at)

        created_at = created_at.astimezone(datetime.UTC) if created_at else datetime.datetime.now(datetime.UTC)
        timezone = timezone or "UTC"

        timer = Timer.temporary(
            id=self._temporary_timer_id_count,
            event=event,
            expires_at=expires_at,
            created_at=created_at,
            timezone=timezone,
            data=data,
        )
        self._temporary_timer_id_count -= 1

        delta = (expires_at - created_at).total_seconds()
        if delta <= 60:
            # a shortcut for small timers
            self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        query = """
            INSERT INTO timers (event, data, expires_at, created_at, timezone)
            VALUES ($1, $2::jsonb, $3, $4, $5)
            RETURNING id;
        """
        row = await self.bot.pool.fetchrow(
            query,
            event,
            data,
            # Remove timezone information since the database does not deal with it
            expires_at.replace(tzinfo=None),
            created_at.replace(tzinfo=None),
            timezone,
        )
        timer.id = row[0]

        # only set the data check if it can be waited on
        if delta <= (86400 * 40):  # 40 days
            self._have_data.set()

        # check if this timer is earlier than our currently run timer
        if self._current_timer and expires_at < self._current_timer.expires_at:
            self.reschedule_timers()

        return timer

    async def short_timer_optimisation(self, seconds: float, timer: Timer[TimerData]) -> None:
        """Optimisation for small timers, skipping the whole database insert/delete procedure."""
        await asyncio.sleep(seconds)
        await self.call_timer(timer)

    async def get_timer_by_id(self, id: int) -> Timer[TimerData] | None:  # noqa: A002
        """Get a timer from its ID.

        Parameters
        ----------
        id: int
            The ID of the timer to get.

        Returns
        -------
        Timer | None
            The timer that was fetched.

        """
        query = "SELECT * FROM timers WHERE id = $1"
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(query, id)
        return Timer(row=record) if record else None

    async def cleanup_timer(self, id: int) -> None:  # noqa: A002
        """Delete a timer by its ID.

        Parameters
        ----------
        id: int
            The ID of the timer to delete.

        """
        self._skipped_timer_ids.remove(id)
        query = "DELETE * FROM timers WHERE id = $1"
        await self.bot.pool.execute(query, id)

    async def get_timer_by_kwargs(self, event: str, /, **kwargs: Any) -> Timer[TimerData] | None:
        """Gets a timer from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event: str
            The name of the event to search for.
        **kwargs: Any
            Keyword arguments to search for in the database.

        Returns
        -------
        Timer[TimerData] | None
            The timer if found, otherwise None.

        """
        filtered_clause = [f"data #>> ARRAY['{key}'] = ${i}" for (i, key) in enumerate(kwargs.keys(), start=2)]
        query = f"SELECT * FROM timers WHERE event = $1 AND {' AND '.join(filtered_clause)} LIMIT 1"
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(query, event, *kwargs.values())
        return Timer(row=record) if record else None

    async def delete_timer_by_kwargs(self, event: str, /, **kwargs: Any) -> None:
        """Delete a timer from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event: str
            The name of the event to search for.
        **kwargs: Any
            Keyword arguments to search for in the database.

        """
        filtered_clause = [f"data #>> ARRAY['{key}'] = ${i}" for (i, key) in enumerate(kwargs.keys(), start=2)]
        query = f"DELETE FROM timers WHERE event = $1 AND {' AND '.join(filtered_clause)} RETURNING id"
        record: Any = await self.bot.pool.fetchrow(query, event, *kwargs.values())

        # if the current timer is being deleted
        if record is not None and self._current_timer and self._current_timer.id == record["id"]:
            # cancel the task and re-run it
            self.reschedule_timers()

    async def fetch_timers(self) -> list[Timer[TimerData]]:
        """Fetch all timers from the database.

        Returns
        -------
        list[Timer[TimerData]]
            A list of `Timer` objects.

        """
        rows = await self.bot.pool.fetch("SELECT * FROM timers")
        return [Timer(row=row) for row in rows]

    def reschedule_timers(self) -> None:
        """A shortcut to cancel the scheduling task which dispatches the timers and rerun it."""
        self._scheduling_task.cancel()
        self._scheduling_task = self.bot.loop.create_task(self.dispatch_timers())
