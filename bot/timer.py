from __future__ import annotations

import asyncio
import datetime
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Generic, Self, TypedDict, TypeVar, override

import asyncpg
import discord

type TimerMapping = Mapping[str, Any]
TimerDataT = TypeVar("TimerDataT", bound=TimerMapping)

if TYPE_CHECKING:
    from utils.database import DotRecord

    from .bot import AluBot

    # currently somewhat pointless since this gives typing for attributes like .id instead of ["id"]
    class TimerRecord(DotRecord, Generic[TimerDataT]):
        id: int
        event: str
        expires_at: datetime.datetime
        created_at: datetime.datetime
        timezone: str
        data: TimerDataT

    # mirror above for @classmethod .temporary
    class PseudoTimerRecord(TypedDict, Generic[TimerDataT]):
        id: None
        event: str
        expires_at: datetime.datetime
        created_at: datetime.datetime
        timezone: str
        data: TimerDataT


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


__all__: tuple[str, ...] = (
    "Timer",
    "TimerManager",
)


class Timer(Generic[TimerDataT]):
    """Represents a Timer from the Database.

    Timers represent delayed tasks like basic use-case of `ext.tasks` provide but
    with better functionality about custom event times or args/kwargs.

    This also makes it possible for dynamically created routines such as `/remind me` to exist.
    Also due to database structure there is less pain about restarting the bot+tasks logic for dynamic period timers.

    Attributes
    ----------
    id: Optional[int]
        If present, then it represents unique ID of the timer.
    event: str
        The event name to trigger when the timer expires.
        This also affects dispatched event name to be f""on_{timer.event}_timer_complete"".
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
    args: list[Any]
        A list of arguments to pass to the :meth:`TimerManager.create_timer` method.
    kwargs: dict[str, Any]
        A dictionary of keyword arguments to pass to the :meth:`TimerManager.create_timer` method.

    """

    __slots__ = ("id", "event", "expires_at", "created_at", "timezone", "data")

    def __init__(self, *, record: TimerRecord[TimerDataT] | PseudoTimerRecord[TimerDataT]) -> None:
        self.id: int | None = record["id"]
        self.event: str = record["event"]
        self.expires_at: datetime.datetime = record["expires_at"]
        self.created_at: datetime.datetime = record["created_at"]
        self.timezone: str = record["timezone"]
        self.data: TimerDataT = record["data"]

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Timer):
            return False
        elif self.id or other.id:
            return self.id == other.id
        else:
            # if both ids are None then it's a a tough question
            # condition below still doesn't prove it
            # but we should not need to compare id=None Timers anyway
            return (
                self.event == other.event
                and self.expires_at == other.expires_at
                and self.created_at == other.created_at
            )

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
        event: str,
        expires_at: datetime.datetime,
        created_at: datetime.datetime,
        timezone: str,
        data: TimerDataT,
    ) -> Self:
        """Initiate the timer without the database before deciding to put it in."""
        pseudo_record: PseudoTimerRecord[TimerDataT] = {
            "id": None,
            "event": event,
            "expires_at": expires_at,
            "created_at": created_at,
            "timezone": timezone,
            "data": data,
        }
        return cls(record=pseudo_record)

    @property
    def format_dt_R(self) -> str:  # noqa: N802
        return discord.utils.format_dt(self.created_at.replace(tzinfo=datetime.UTC), style="R")


class TimerManager:
    """Class to create and manage timers.

    Attributes
    ----------
    bot : AluBot
        The bot instance.

    """

    __slots__: tuple[str, ...] = ("name", "bot", "_have_data", "_current_timer", "_task")

    def __init__(self, *, bot: AluBot) -> None:
        self.bot: AluBot = bot

        self._have_data = asyncio.Event()
        self._current_timer: Timer[TimerMapping] | None = None
        self._task = self.bot.loop.create_task(self.dispatch_timers())

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
                now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

                if timer.expires_at >= now:
                    to_sleep = (timer.expires_at - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())
        except Exception as exc:
            await self.bot.exc_manager.register_error(exc, source="TimerManager", where="dispatch_timers")

    async def wait_for_active_timers(self, *, days: int = 7) -> Timer[TimerMapping]:
        """Wait for a timer that has expired.

        This will wait until a timer is expired and should be dispatched.

        Parameters
        ----------
        days : int
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

        return await self.get_active_timer(days=days)  # type: ignore  # bcs at this point we always have data

    async def call_timer(self, timer: Timer) -> None:
        """Call an expired timer to dispatch it.

        Parameters
        ----------
        timer : Timer
            The timer to dispatch.

        """
        log.debug("Calling and Dispatching the timer %s with event %s", timer.id, timer.event)

        # delete the timer
        query = "DELETE FROM timers WHERE id=$1"
        await self.bot.pool.execute(query, timer.id)

        # dispatch the event
        event_name = f"{timer.event}_timer_complete"
        self.bot.dispatch(event_name, timer)

    async def get_active_timer(self, *, days: int = 7) -> Timer[TimerMapping] | None:
        """Get the most current active timer in the database.

        This timer is expired and should be dispatched.

        Parameters
        ----------
        days: int
            The number of days to look back.

        Returns
        -------
        Timer | None
            The timer that is expired and should be dispatched.

        """
        query = """
            SELECT * FROM timers
            WHERE (expires_at AT TIME ZONE 'UTC' AT TIME ZONE timezone) < (CURRENT_TIMESTAMP + $1::interval)
            ORDER BY expires_at
            LIMIT 1;
        """
        record: TimerRecord[TimerMapping] = await self.bot.pool.fetchrow(query, datetime.timedelta(days=days))
        if record:
            timer = Timer(record=record)
            return timer
        else:
            return None

    async def create_timer(
        self,
        *,
        event: str,
        expires_at: datetime.datetime,
        created_at: datetime.datetime | None = None,
        timezone: str | None = None,
        data: TimerMapping,
    ) -> Timer:
        """Creates a timer.

        Used to create a timer and put it into a database, or just dispatch it if it's a short timer.

        Parameters
        ----------
        when : datetime.datetime
            When the timer should fire.
        event : str
            The name of the event to trigger. Will transform to 'on_{event}_timer_complete'.
        created_at: datetime.datetime
            Special keyword-only argument to use as the creation time.
            Should make the time-deltas a bit more consistent.
        timezone : str
            IANA alias. Special keyword-only argument to use as the timezone for the
            expiry time. This automatically adjusts the expiry time to be
            in the future, should it be in the past.
        data : TimerMapping
            data to pass to the timer to json it up and keep it in the database.
            This should be used when dispatching timer event.

        Note
        ------
        Arguments and keyword arguments must be JSON serializable.

        Returns
        -------
        Timer

        """
        log.debug("Creating %s timer for %s", event, expires_at)

        created_at = created_at or datetime.datetime.now(datetime.UTC)
        timezone = timezone or "UTC"

        # Remove timezone information since the database does not deal with it
        expires_at = expires_at.astimezone(datetime.UTC).replace(tzinfo=None)
        created_at = created_at.astimezone(datetime.UTC).replace(tzinfo=None)

        timer = Timer.temporary(
            event=event,
            expires_at=expires_at,
            created_at=created_at,
            timezone=timezone,
            data=data,
        )

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
        row = await self.bot.pool.fetchrow(query, event, data, expires_at, created_at, timezone)
        timer.id = row[0]

        # only set the data check if it can be waited on
        if delta <= (86400 * 40):  # 40 days
            self._have_data.set()

        # check if this timer is earlier than our currently run timer
        if self._current_timer and expires_at < self._current_timer.expires_at:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        return timer

    async def short_timer_optimisation(self, seconds: float, timer: Timer[TimerMapping]) -> None:
        await asyncio.sleep(seconds)
        event_name = f"{timer.event}_timer_complete"
        self.bot.dispatch(event_name, timer)

    async def get_timer_by_id(self, id: int) -> Timer[TimerMapping] | None:
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
        record: TimerRecord[TimerMapping] | None = await self.bot.pool.fetchrow(query, id)
        return Timer(record=record) if record else None

    async def delete_timer_by_id(self, id: int) -> None:
        """Delete a timer by its ID.

        Parameters
        ----------
        id: int
            The ID of the timer to delete.

        """
        query = "DELETE * FROM timers WHERE id = $1"
        await self.bot.pool.execute(query, id)

    async def get_timer_by_kwargs(self, event: str, /, **kwargs: Any) -> Timer | None:
        """Gets a timer from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event : str
            The name of the event to search for.
        **kwargs
            Keyword arguments to search for in the database.

        Returns
        -------
        Timer | None
            The timer if found, otherwise None.

        """
        filtered_clause = [f"data #>> ARRAY['{key}'] = ${i}" for (i, key) in enumerate(kwargs.keys(), start=2)]
        query = f"SELECT * FROM timers WHERE event = $1 AND {' AND '.join(filtered_clause)} LIMIT 1"
        record: TimerRecord | None = await self.bot.pool.fetchrow(query, event, *kwargs.values())
        return Timer(record=record) if record else None

    async def delete_timer_by_kwargs(self, event: str, /, **kwargs: Any) -> None:
        """Delete a timer from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event: str
            The name of the event to search for.
        **kwargs
            Keyword arguments to search for in the database.

        """
        filtered_clause = [f"data #>> ARRAY['{key}'] = ${i}" for (i, key) in enumerate(kwargs.keys(), start=2)]
        query = f"DELETE FROM timers WHERE event = $1 AND {' AND '.join(filtered_clause)} RETURNING id"
        record: Any = await self.bot.pool.fetchrow(query, event, *kwargs.values())

        # if the current timer is being deleted
        if record is not None and self._current_timer and self._current_timer.id == record["id"]:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def fetch_timers(self) -> list[Timer]:
        """Fetch all timers from the database.

        Returns
        -------
        list
            A list of `Timer` objects.

        """
        rows = await self.bot.pool.fetch("SELECT * FROM timers")
        return [Timer(record=row) for row in rows]

    def rerun_the_task(self) -> None:
        self._task.cancel()
        self._task = self.bot.loop.create_task(self.bot.dispatch_timers())
