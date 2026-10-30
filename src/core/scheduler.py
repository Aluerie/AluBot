# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Scheduler.

Scheduler manages timers, which are delayed tasks that survive bot restarts: they live in the ``timers`` database table.
Once they expire, they are dispatched as ``on_{event}_timer_complete`` events to the cogs' listeners.
"""

from __future__ import annotations

import asyncio
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


type TimerData = Mapping[str, Any]

LOOKAHEAD = dt.timedelta(days=40)
"""How far ahead the dispatch loop looks for timers. When the window elapses, the loop queries the database again."""
SHORT_TIMER = dt.timedelta(seconds=60)
"""Timers expiring sooner than this skip the database entirely and live in memory."""
MAX_RETRY_DELAY = 300.0
"""Upper bound (in seconds) for the dispatch loop's exponential backoff after errors."""

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

        .. code-block:: python

            @commands.Cog.listener()  # or .listener("on_reminder_timer_complete")
            async def on_reminder_timer_complete(self, timer: Timer[MyData]) -> None: ...

    created_at
        The datetime the timer was created (aware, UTC). Informational: it does not affect when the timer fires.
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

    def matches(self, event: str, data_subset: Mapping[str, Any]) -> bool:
        """Check whether the timer has the given event and its `data` contains all the given key-value pairs."""
        return self.event == event and all(self.data.get(key) == value for key, value in data_subset.items())


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
    * Persistent timers: `create` puts a row into the database and, if the new timer is the next one to expire,
      restarts the dispatch loop (`reschedule`). The loop (`_run`) always sleeps until the closest timer within
      the `LOOKAHEAD` window and then dispatches it with `call`.
    * Short timers (shorter than `SHORT_TIMER`) never touch the database: they are plain `asyncio` sleeps.

    Attributes
    ----------
    bot
        The bot instance.
    current_timer
        The timer the dispatch loop is currently sleeping until, if any.

    Warnings
    --------
    Listeners must call ``self.bot.timers.cleanup(timer.id)`` (preferably in a ``finally`` block) when they are done.
    Until then the timer is considered "in progress" and is skipped by the dispatch loop.
    If the bot restarts before the cleanup, the timer is dispatched again: timers are delivered *at least once*.
    """

    __slots__: tuple[str, ...] = (
        "_next_temporary_id",
        "_short_tasks",
        "_skipped_timer_ids",
        "_task",
        "_warned_events",
        "bot",
        "current_timer",
    )

    def __init__(self, *, bot: Bot) -> None:
        self.bot: Bot = bot
        self.current_timer: Timer[TimerData] | None = None

        self._next_temporary_id: int = -1
        """Temporary timers have negative IDs: `Timer.__eq__` works on them and they never clash with the database."""
        self._skipped_timer_ids: set[int] = set()
        """IDs of the timers that were dispatched but not cleaned up yet."""
        self._short_tasks: dict[int, tuple[Timer[TimerData], asyncio.Task[None]]] = {}
        """Pending short timers. Also holds strong references, so the tasks aren't garbage collected mid-sleep."""
        self._warned_events: set[str] = set()
        """Events developers were already notified about having no listener, to not spam them."""
        self._task: asyncio.Task[None] = asyncio.create_task(self._run(), name="scheduler-dispatch")

    def close(self) -> None:
        """Cancel the dispatching loop and all pending short timers."""
        self._task.cancel()
        for _, task in list(self._short_tasks.values()):
            task.cancel()

    # --- DISPATCH LOOP ------------------------------------------------------------------------------------------------

    async def _run(self) -> None:
        """Run the dispatch loop: wait for the closest timer to expire, dispatch it, repeat.

        The loop never dies from an exception: unexpected errors are reported and the loop is restarted after a delay
        that grows with each consecutive failure. Only a cancellation (`close` or `reschedule`) stops it.
        """
        await self.bot.wait_until_ready()

        delay = 5.0
        while not self.bot.is_closed():
            try:
                timer = await self._wait_for_next_timer()
                self.current_timer = timer
                log.debug("Current timer = %s", timer)

                await self._sleep_until(timer.expires_at)

                # forget the timer *before* anything else can fail so `create` never compares against a stale one
                self.current_timer = None
                await self.call(timer)
                delay = 5.0
            except OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError:
                # the database/connection is down: do not hot-loop, just wait for it to come back
                self.current_timer = None
                log.warning("Scheduler lost the connection, retrying in %.0f seconds.", delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)
            except Exception as exc:  # ruff: ignore[blind-except]
                self.current_timer = None
                embed = discord.Embed(
                    color=0xFF8243,
                    title="Dispatching Timers Error",
                    description=f"The scheduler continues to work and will retry in {delay:.0f} seconds.",
                ).set_footer(text=f"{self.__class__.__name__}._run")
                await self.bot.error_notification_manager.register(exc, embed)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)

    @staticmethod
    async def _sleep_until(when: dt.datetime) -> None:
        """Sleep until the given moment.

        `asyncio.sleep` counts on the monotonic clock while timers are set on the wall clock. These can disagree
        (the system clock is adjusted, the machine was suspended, etc.), so the wall clock is re-checked
        after every sleep instead of trusting the first calculation.

        Parameters
        ----------
        when
            The aware datetime to sleep until.
        """
        while True:
            seconds = (when - clock.utcnow()).total_seconds()
            if seconds <= 0:
                return
            await asyncio.sleep(seconds)

    async def _wait_for_next_timer(self) -> Timer[TimerData]:
        """Wait until there is a timer within the look-ahead window and return the closest one.

        The caller is responsible for sleeping until the timer actually expires.

        If there are no timers, this sleeps for the whole window: either `create` restarts the loop earlier
        because a new timer appeared, or the window slides forward and the database is queried again.
        """
        while True:
            timer = await self.get_active()
            if timer is not None:
                return timer
            self.current_timer = None
            await asyncio.sleep(LOOKAHEAD.total_seconds())

    async def call(self, timer: Timer[TimerData]) -> None:
        """Dispatch an expired timer to its listeners.

        Parameters
        ----------
        timer
            The timer to dispatch.
        """
        # mark as "in progress" first, so the dispatch loop doesn't pick it up again while the listener works
        self._skipped_timer_ids.add(timer.id)

        if not self._has_listener(timer):
            # Don't lose the timer: it stays in the database and is dispatched again on the next bot start.
            await self._warn_no_listener(timer)
            return

        log.debug("Dispatching the timer %s with event %s", timer.id, timer.event)
        self.bot.dispatch(timer.event_name, timer)

    def _has_listener(self, timer: Timer[TimerData]) -> bool:
        """Check if any loaded cog (or `bot.listen`) listens to the timer's event."""
        listener_name = f"on_{timer.event_name}"
        if listener_name in self.bot.extra_events:
            return True
        return any(name == listener_name for cog in self.bot.cogs.values() for name, _ in cog.get_listeners())

    async def _warn_no_listener(self, timer: Timer[TimerData]) -> None:
        """Tell developers about a timer that has nobody to be dispatched to (once per event)."""
        if self.bot.test:
            # the test bot usually loads just a few extensions, so this is expected
            log.debug("No listener for %s, skipping the timer %s.", timer.event_name, timer.id)
            return
        if timer.event_name in self._warned_events:
            return
        self._warned_events.add(timer.event_name)

        try:
            await self.bot.notify_developers(
                f"The timer with `event={timer.event_name}` expired but there is no appropriate listener loaded atm. "
                "It is kept in the database and will be dispatched again after the next bot start."
            )
        except discord.HTTPException:
            log.warning("Could not notify developers about %s having no listener.", timer.event_name, exc_info=True)

    def reschedule(self) -> None:
        """Restart the dispatch loop: cancel the current one and start a new one that re-queries the database."""
        self._task.cancel()
        self._task = asyncio.create_task(self._run(), name="scheduler-dispatch")

    def check_reschedule(self, timer_id: int) -> None:
        """Restart the dispatch loop if the timer with the given ID is the one it is currently waiting for.

        Should be called after deleting a timer from the database by hand.
        """
        if self.current_timer and self.current_timer.id == timer_id:
            self.reschedule()

    # --- CREATING -----------------------------------------------------------------------------------------------------

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
            When the timer should fire. Must be timezone-aware.
        created_at
            When the timer was created. Defaults to now. It's informational only (e.g. to show "set 5 minutes ago"),
            it doesn't affect when the timer fires.
        timezone
            IANA alias to store alongside the timer. Defaults to UTC.
        data
            Data to pass to the timer to json it up and keep it in the database.
            This should be used when dispatching timer event. Must be JSON serializable.

        Returns
        -------
        Timer[TimerData]
            The created timer.

        Raises
        ------
        ValueError
            If `expires_at` or `created_at` is a timezone-naive datetime.
        """
        if _is_naive(expires_at):
            msg = f"`expires_at={expires_at!r}` for the timer with `{event=}` is timezone-naive."
            raise ValueError(msg)
        if created_at is not None and _is_naive(created_at):
            msg = f"`created_at={created_at!r}` for the timer with `{event=}` is timezone-naive."
            raise ValueError(msg)

        now = clock.utcnow()
        expires_at = expires_at.astimezone(dt.UTC)
        created_at = created_at.astimezone(dt.UTC) if created_at else now
        log.debug("Creating %s timer for %s", event, expires_at)

        timer = Timer.temporary(
            id=self._next_temporary_id,
            event=event,
            expires_at=expires_at,
            created_at=created_at,
            timezone=timezone or "UTC",
            data=data,
        )
        self._next_temporary_id -= 1

        # How soon the timer fires is measured from *now*: `created_at` is allowed to be in the past.
        if expires_at - now <= SHORT_TIMER:
            self._start_short_timer(timer)
            return timer

        query = """
            INSERT INTO timers (event, data, expires_at, created_at, timezone)
            VALUES ($1, $2::jsonb, $3, $4, $5)
            RETURNING id;
        """
        timer.id = await self.bot.pool.fetchval(query, event, data, expires_at, created_at, timer.timezone)

        # Timers further than the look-ahead window are picked up when the window slides to them.
        if expires_at - now <= LOOKAHEAD:
            current = self.current_timer
            # `current is None`: the loop is idle or in the middle of a query that might have missed the new row
            if current is None or expires_at < current.expires_at:
                self.reschedule()

        return timer

    def _start_short_timer(self, timer: Timer[TimerData]) -> None:
        """Keep a short timer in memory and dispatch it when it expires."""

        async def worker() -> None:
            try:
                seconds = (timer.expires_at - clock.utcnow()).total_seconds()
                if seconds > 0:
                    await asyncio.sleep(seconds)
                await self.call(timer)
            except Exception as exc:  # ruff: ignore[blind-except]
                embed = discord.Embed(
                    color=0xFF8243,
                    title="Short Timer Error",
                    description=f"Failed to dispatch {timer!r}",
                ).set_footer(text=f"{self.__class__.__name__}._start_short_timer")
                await self.bot.error_notification_manager.register(exc, embed)

        task = asyncio.create_task(worker(), name=f"scheduler-short-timer-{timer.id}")
        self._short_tasks[timer.id] = (timer, task)
        task.add_done_callback(lambda _: self._short_tasks.pop(timer.id, None))

    # --- QUERYING -----------------------------------------------------------------------------------------------------

    async def get_active(self) -> Timer[TimerData] | None:
        """Get the closest to expire timer in the database that was not dispatched yet.

        Returns
        -------
        Timer[TimerData] | None
            The timer that is about to expire, if there is any within the look-ahead window.
        """
        query = """
            SELECT * FROM timers
            WHERE expires_at < NOW() + $1::interval
                AND id <> ALL($2::int[])
            ORDER BY expires_at
            LIMIT 1;
        """
        record: TimerRow[TimerData] | None = await self.bot.pool.fetchrow(
            query, LOOKAHEAD, list(self._skipped_timer_ids)
        )
        return Timer(row=record) if record else None

    async def get_by_id[TimerDataT: TimerData](self, timer_id: int) -> Timer[TimerDataT] | None:
        """Get a timer from its ID.

        Parameters
        ----------
        timer_id
            The ID of the timer to get.

        Returns
        -------
        Timer[TimerDataT] | None
            The timer that was fetched. `TimerDataT` is the type of the data that the caller expects the timer to
            have, i.e. ``timer: Timer[MyData] | None = await timers.get_by_id(...)``. It's not checked at runtime.
        """
        record: TimerRow[TimerDataT] | None = await self.bot.pool.fetchrow(
            "SELECT * FROM timers WHERE id = $1", timer_id
        )
        return Timer(row=record) if record else None

    async def get_by_kwargs[TimerDataT: TimerData](self, event: str, /, **kwargs: Any) -> Timer[TimerDataT] | None:
        """Get the closest timer of the event whose `data` contains all the given key-value pairs.

        Note you cannot find a timer by its expiry or creation time.

        Parameters
        ----------
        event
            The name of the event to search for.
        **kwargs
            Key-value pairs that the timer's `data` must contain. Values keep their JSON types,
            i.e. ``user_id=123`` matches ``{"user_id": 123}`` but not ``{"user_id": "123"}``.

        Returns
        -------
        Timer[TimerDataT] | None
            The timer if found, otherwise None. `TimerDataT` is the type of the data that the caller expects
            the timer to have, see `get_by_id`.
        """
        query = """
            SELECT * FROM timers
            WHERE event = $1 AND data @> $2::jsonb
            ORDER BY expires_at
            LIMIT 1;
        """
        record: TimerRow[TimerDataT] | None = await self.bot.pool.fetchrow(query, event, kwargs)
        return Timer(row=record) if record else None

    async def fetch_by_kwargs[TimerDataT: TimerData](self, event: str, /, **kwargs: Any) -> list[Timer[TimerDataT]]:
        """Fetch all timers of the event whose `data` contains all the given key-value pairs, closest first.

        Parameters
        ----------
        event
            The name of the event to search for.
        **kwargs
            Key-value pairs that the timer's `data` must contain. See `get_by_kwargs`.

        Returns
        -------
        list[Timer[TimerDataT]]
            The matching timers sorted by their expiry. `TimerDataT` is the type of the data that the caller
            expects the timers to have, see `get_by_id`.
        """
        query = """
            SELECT * FROM timers
            WHERE event = $1 AND data @> $2::jsonb
            ORDER BY expires_at;
        """
        rows: list[TimerRow[TimerDataT]] = await self.bot.pool.fetch(query, event, kwargs)
        return [Timer(row=row) for row in rows]

    async def fetch(self) -> list[Timer[TimerData]]:
        """Fetch all timers from the database.

        Returns
        -------
        list[Timer[TimerData]]
            A list of `Timer` objects.
        """
        rows = await self.bot.pool.fetch("SELECT * FROM timers")
        return [Timer(row=row) for row in rows]

    # --- DELETING -----------------------------------------------------------------------------------------------------

    async def cleanup(self, timer_id: int) -> None:
        """Mark a dispatched timer as handled and delete it.

        .. important::

            This is supposed to be called in the end of listener's coro.

        Parameters
        ----------
        timer_id
            The ID of the timer to delete.
        """
        self._skipped_timer_ids.discard(timer_id)
        if timer_id < 0:
            # temporary timers never made it to the database
            return
        await self.bot.pool.execute("DELETE FROM timers WHERE id = $1", timer_id)

    async def delete_by_id(self, timer_id: int, /, event: str, **kwargs: Any) -> bool:
        """Delete a timer by its ID, but only if it has the given event and its `data` contains the given pairs.

        The extra conditions make sure users can only delete their own timers, i.e. pass ``author_id=...``.

        Parameters
        ----------
        timer_id
            The ID of the timer to delete.
        event
            The event the timer must have.
        **kwargs
            Key-value pairs that the timer's `data` must contain. See `get_by_kwargs`.

        Returns
        -------
        bool
            Whether a timer was deleted.
        """
        query = "DELETE FROM timers WHERE id = $1 AND event = $2 AND data @> $3::jsonb RETURNING id;"
        deleted_id = await self.bot.pool.fetchval(query, timer_id, event, kwargs)
        if deleted_id is None:
            return False

        self._skipped_timer_ids.discard(deleted_id)
        self.check_reschedule(deleted_id)
        return True

    async def delete_by_kwargs(self, event: str, /, **kwargs: Any) -> int:
        """Delete all timers of the event whose `data` contains all the given key-value pairs.

        This also cancels matching short timers that live only in memory.

        Parameters
        ----------
        event
            The name of the event to search for.
        **kwargs
            Key-value pairs that the timer's `data` must contain. See `get_by_kwargs`.

        Returns
        -------
        int
            How many timers were deleted.
        """
        query = "DELETE FROM timers WHERE event = $1 AND data @> $2::jsonb RETURNING id;"
        rows = await self.bot.pool.fetch(query, event, kwargs)
        for row in rows:
            self._skipped_timer_ids.discard(row["id"])
            self.check_reschedule(row["id"])

        short_deleted = 0
        for timer, task in list(self._short_tasks.values()):
            if timer.matches(event, kwargs):
                task.cancel()
                short_deleted += 1

        return len(rows) + short_deleted
