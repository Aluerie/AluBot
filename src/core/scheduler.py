"""Scheduler.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Self, TypedDict, override

import asyncpg
import discord

from shared import clock

if TYPE_CHECKING:
    from core import Bot

__all__: tuple[str, ...] = (
    "Scheduler",
    "Timer",
    "TimerRow",
)

# small issue with TypedDict's is why we need to use Mapping here over dict[str, Any]
# https://github.com/python/mypy/issues/4976#issuecomment-384719025
type TimerData = Mapping[str, Any]

LOOKAHEAD_DAYS = 40
"""How far ahead the dispatch loop looks for timers. When the window elapses, the loop queries the database again."""
SHORT_TIMER_SECONDS = 60
"""Timers shorter than this skip the database entirely."""
RECONNECT_DELAY = 5.0
"""Seconds to wait before restarting the dispatch loop after a connection error."""

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class TimerRow[TimerDataT: TimerData](TypedDict):
    """Database Row for Timers.

    Contains basic data about the timers required for its completion and
    custom generic data to be used by the listener dispatching the timer.
    """

    id: int
    event: str
    expires_at: dt.datetime
    created_at: dt.datetime
    timezone: str
    data: TimerDataT


def _is_naive(when: dt.datetime) -> bool:
    return when.tzinfo is None or when.tzinfo.utcoffset(when) is None


class Timer[TimerDataT: TimerData]:
    """Timer represent delayed tasks.

    Practically, serves same purpose as `ext.tasks`, but allows to dynamically manage timer-tasks on the fly
    via the database such as reminders, birthdays, etc.

    Also due to database usage there is less pain about restarting the bot in the timers.
    It's useful for such tasks as patch notes checkers as
    they don't need to do an extra fetch from the database on each bot's restart.
    Also such timers can be consistently periodic through bot's restarts.

    Attributes
    ----------
    id
        Represents unique ID of the timer. If negative, then the timer is temporary and short-lived.
    event
        The event name to trigger when the timer expires.
        This also defines event's name for the timer to be dispatched to (`event_name`).
        The listener can be formatted as follows (with example `.event` being named "reminder"):
        ```py
        @commands.Cog.listener()  # or .listener("on_reminder_timer_complete")
        async def on_reminder_timer_complete(self, timer: Timer[MyData]) -> None: ...
        ```
    created_at
        The datetime the timer was created (aware, UTC).
    expires_at
        The datetime the timer expires and triggers the event (aware, UTC).
    timezone
        IANA timezone name associated with the timer, i.e. the timezone of the user who created it.
        It is informational only (for example, to display times to the user): `expires_at` is always an aware UTC
        datetime and does not depend on this value.
    data
        JSON-serializable data stored with the timer and passed to the listener.

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
        self.expires_at: dt.datetime = row["expires_at"].astimezone(dt.UTC)
        self.created_at: dt.datetime = row["created_at"].astimezone(dt.UTC)
        self.timezone: str = row["timezone"]
        self.data: TimerDataT = row["data"]

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Timer):
            return NotImplemented
        return self.id == other.id

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
        id: int,  # ruff: ignore[builtin-argument-shadowing]
        event: str,
        expires_at: dt.datetime,
        created_at: dt.datetime,
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
        """Return the timer's event name."""
        return f"{self.event}_timer_complete"


class Scheduler:
    """Class to create and manage timers.

    Sources
    -------
    * Rapptz/RoboDanny (license MPL v2), Reminder cog:
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py
    * DuckBot-Discord/DuckBot, rewrite branch (license MPL v2), TimerManager:
        https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/bases/timer.py

    Workflow
    --------
    * __init__ > dispatch > wait_for_active (get_active) > call > looped again
    * create > maybe short_optimization > reschedule

    Warnings
    --------
    Remember to use `self.bot.timers.cleanup(timer.id)` in the end of listener's coro.
    """

    __slots__: tuple[str, ...] = (
        "_have_data",
        "_scheduling_task",
        "_short_tasks",
        "_skipped_timer_ids",
        "_temporary_timer_id_count",
        "bot",
        "current_timer",
    )

    def __init__(self, *, bot: Bot) -> None:
        self.bot: Bot = bot

        self._temporary_timer_id_count: int = -1
        """Not really useful attribute, but just so `__eq__` can properly work on temporary timers."""
        self._skipped_timer_ids: set[int] = set()
        self._short_tasks: set[asyncio.Task[None]] = set()
        """Strong references to short timers' tasks, otherwise they can be garbage collected mid-sleep."""
        self._have_data: asyncio.Event = asyncio.Event()
        """Wakes `wait_for_active` up when a new timer that it can wait on is added."""
        self.current_timer: Timer[TimerData] | None = None
        self._scheduling_task: asyncio.Task[None] = self.bot.loop.create_task(self.dispatch())

    def close(self) -> None:
        """Cancel the dispatching loop and all pending short timers."""
        self._scheduling_task.cancel()
        for task in list(self._short_tasks):
            task.cancel()

    def _available_listener_names(self) -> set[str]:
        return {name for cog in self.bot.cogs.values() for name, _ in cog.get_listeners()}

    async def _warn_if_no_listener(self, timer: Timer[TimerData]) -> None:
        """Notify developers if there is no listener for the timer that is about to be dispatched."""
        if self.bot.test or f"on_{timer.event_name}" in self._available_listener_names():
            return

        await self.bot.notify_developers(
            f"The timer with `event={timer.event_name}` is to fire but there is no appropriate listener loaded atm."
        )

    async def dispatch(self) -> None:
        """Dispatch timers loop.

        This will wait for the next timer to expire and dispatch the bot's event with its data.
        Please note if you use this class, you need to cancel the task when you're done with it.
        """
        await self.bot.wait_until_ready()

        try:
            while not self.bot.is_closed():
                timer = self.current_timer = await self.wait_for_active(days=LOOKAHEAD_DAYS)
                log.debug("Current_timer = %s", timer)

                now = clock.utcnow()
                if timer.expires_at > now:
                    await asyncio.sleep((timer.expires_at - now).total_seconds())

                # check right before dispatching: cogs might have been (re)loaded while we were sleeping
                await self._warn_if_no_listener(timer)
                await self.call(timer)
        except OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError:
            # do not hot-loop while the database/connection is down
            await asyncio.sleep(RECONNECT_DELAY)
            self.reschedule()
        except Exception as exc:  # ruff: ignore[blind-except]
            embed = discord.Embed(
                color=0xFF8243,
                title="Dispatching Timers Error",
            ).set_footer(text=f"{self.__class__.__name__}.dispatch")
            await self.bot.error_notification_manager.register(exc, embed)

    async def wait_for_active(self, *, days: int = 7) -> Timer[TimerData]:
        """Wait for the next timer that should be dispatched.

        This will wait until a timer is found within the look-ahead window.
        The caller is responsible for sleeping until the timer actually expires.

        Parameters
        ----------
        days
            Number of days to look ahead into.

        Returns
        -------
        Timer[TimerData]
            The closest timer that is about to expire and should be dispatched.

        """
        timeout = dt.timedelta(days=days).total_seconds()

        while True:
            # clear *before* querying, so a `create` landing between the query and the wait is not lost
            self._have_data.clear()

            timer = await self.get_active(days=days)
            if timer is not None:
                return timer

            self.current_timer = None
            # wake up periodically as timers further than `days` away are invisible to `get_active` until
            # they enter the window, and nothing else would ever wake us up for them
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._have_data.wait(), timeout=timeout)

    async def call(self, timer: Timer[TimerData]) -> None:
        """Call an expired timer to dispatch its event.

        Parameters
        ----------
        timer
            The timer to dispatch.

        """
        log.debug("Calling and Dispatching the timer %s with event %s", timer.id, timer.event)

        self._skipped_timer_ids.add(timer.id)
        self.bot.dispatch(timer.event_name, timer)

    async def get_active(self, *, days: int = 7) -> Timer[TimerData] | None:
        """Get the closest to expire timer in the database that was not dispatched yet.

        Parameters
        ----------
        days
            The number of days to look ahead.

        Returns
        -------
        Timer[TimerData] | None
            The timer that is about to expire, if there is any within the window.

        """
        query = """
            SELECT * FROM timers
            WHERE expires_at < NOW() + $1::interval
                AND NOT id = ANY($2)
            ORDER BY expires_at
            LIMIT 1;
        """
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(
            query, dt.timedelta(days=days), self._skipped_timer_ids
        )
        return Timer(row=record) if record else None

    async def create(
        self,
        *,
        event: str,
        expires_at: dt.datetime,
        created_at: dt.datetime | None = None,
        timezone: str | None = None,
        data: TimerData,
    ) -> Timer[TimerData]:
        """Create a timer.

        Used to create a timer and put it into a database, or just dispatch it if it's a short timer.

        Parameters
        ----------
        event
            The name of the event to trigger. Will transform to 'on_{event}_timer_complete'.
        expires_at
            When the timer should fire.
        created_at
            Special keyword-only argument to use as the creation time.
            Should make the time-deltas a bit more consistent.
        timezone
            IANA alias to store alongside the timer. Defaults to UTC.
        data
            Data to pass to the timer to json it up and keep it in the database.
            This should be used when dispatching timer event.

        Returns
        -------
        Timer[TimerData]
            The created timer.

        Notes
        -----
        `data` must be JSON serializable.

        """
        # Maybe, we don't need these two, I'm just scared.
        if _is_naive(expires_at):
            await self.bot.notify_developers(f"`{expires_at=}` for timer with `{event=}` is timezone-naive.")
        if created_at and _is_naive(created_at):
            await self.bot.notify_developers(f"`{created_at=}` for timer with `{event=}` is timezone-naive.")

        expires_at = expires_at.astimezone(dt.UTC)
        log.debug("Creating %s timer for %s", event, expires_at)

        created_at = created_at.astimezone(dt.UTC) if created_at else clock.utcnow()
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
        if delta <= SHORT_TIMER_SECONDS:
            # a shortcut for small timers
            task = self.bot.loop.create_task(self.short_optimization(delta, timer))
            self._short_tasks.add(task)
            task.add_done_callback(self._short_tasks.discard)
            return timer

        query = """
            INSERT INTO timers (event, data, expires_at, created_at, timezone)
            VALUES ($1, $2::jsonb, $3, $4, $5)
            RETURNING id;
        """
        row = await self.bot.pool.fetchrow(query, event, data, expires_at, created_at, timezone)
        timer.id = row["id"]

        # only set the data check if it can be waited on
        if delta <= dt.timedelta(days=LOOKAHEAD_DAYS).total_seconds():
            self._have_data.set()

        # check if this timer is earlier than our currently run timer
        if self.current_timer and expires_at < self.current_timer.expires_at:
            self.reschedule()

        return timer

    async def short_optimization(self, seconds: float, timer: Timer[TimerData]) -> None:
        """Optimization for small timers, skipping the whole database insert/delete procedure."""
        await asyncio.sleep(seconds)
        await self.call(timer)

    async def get_by_id(self, id: int) -> Timer[TimerData] | None:  # ruff: ignore[builtin-argument-shadowing]
        """Get a timer from its ID.

        Parameters
        ----------
        id
            The ID of the timer to get.

        Returns
        -------
        Timer[TimerData] | None
            The timer that was fetched.

        """
        query = "SELECT * FROM timers WHERE id = $1"
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(query, id)
        return Timer(row=record) if record else None

    @staticmethod
    def _where_clause(event: str, kwargs: Mapping[str, Any]) -> tuple[str, list[Any]]:
        """Build `WHERE` conditions (and their arguments) matching the event and `data` fields.

        Keys are passed as query parameters too, so nothing user-controlled is ever formatted into the SQL.
        """
        conditions = ["event = $1"]
        args: list[Any] = [event]
        for key, value in kwargs.items():
            conditions.append(f"data ->> ${len(args) + 1}::text = ${len(args) + 2}")
            args.extend((key, value))
        return " AND ".join(conditions), args

    async def get_by_kwargs(self, event: str, /, **kwargs: Any) -> Timer[TimerData] | None:
        """Get a timer from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event
            The name of the event to search for.
        **kwargs
            Keyword arguments to search for in the database.

        Returns
        -------
        Timer[TimerData] | None
            The timer if found, otherwise None.

        """
        where, args = self._where_clause(event, kwargs)
        query = f"SELECT * FROM timers WHERE {where} LIMIT 1"  # ruff: ignore[hardcoded-sql-expression]
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(query, *args)
        return Timer(row=record) if record else None

    async def fetch(self) -> list[Timer[TimerData]]:
        """Fetch all timers from the database.

        Returns
        -------
        list[Timer[TimerData]]
            A list of `Timer` objects.

        """
        rows = await self.bot.pool.fetch("SELECT * FROM timers")
        return [Timer(row=row) for row in rows]

    async def cleanup(self, id: int) -> None:  # ruff: ignore[builtin-argument-shadowing]
        """Cleanup a timer by its ID.

        Important! This is supposed to be called in the end of listeners coro.

        Parameters
        ----------
        id
            The ID of the timer to delete.

        """
        self._skipped_timer_ids.discard(id)
        if id < 0:
            # temporary timers never made it to the database
            return
        await self.bot.pool.execute("DELETE FROM timers WHERE id = $1", id)

    async def delete_by_kwargs(self, event: str, /, **kwargs: Any) -> None:
        """Delete timers from the database.

        Note you cannot find a database by its expiry or creation time.

        Parameters
        ----------
        event
            The name of the event to search for.
        **kwargs
            Keyword arguments to search for in the database.

        """
        where, args = self._where_clause(event, kwargs)
        # `DELETE` removes *every* match, so every deleted id has to be checked against the current timer
        query = f"DELETE FROM timers WHERE {where} RETURNING id"  # ruff: ignore[hardcoded-sql-expression]
        rows = await self.bot.pool.fetch(query, *args)

        for row in rows:
            self._skipped_timer_ids.discard(row["id"])
            self.check_reschedule(row["id"])

    def reschedule(self) -> None:
        """Reschedule shortcut: cancel the scheduling task which dispatches the timers and rerun it."""
        self._scheduling_task.cancel()
        self._scheduling_task = self.bot.loop.create_task(self.dispatch())

    def check_reschedule(self, id_: int) -> None:
        """Cleanup function for deleting timers by id.

        Should be called in the end of most "delete" methods, i.e. /remind delete slash command
        """
        # if the current timer is being deleted
        if self.current_timer and self.current_timer.id == id_:
            # cancel the task and re-run it
            self.reschedule()

# SHOULD WE COMBINE TIMEZONES AND SCHEDULER ???