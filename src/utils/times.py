# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Times.

Parsing of the time that users type in: "10m", "2 days 3h", "tomorrow at 3pm", Discord timestamps like ``<t:123456:R>``.

Sources
-------
* Most of the code below is a shameless copypaste from @Rapptz's RoboDanny utils
    licensed MPL v2 from Rapptz/RoboDanny
    https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py
"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, override

import parsedatetime as pdt
from dateutil.relativedelta import relativedelta
from discord import app_commands

from shared import clock, errors

if TYPE_CHECKING:
    from core import Interaction

__all__ = (
    "FutureTime",
    "HumanTime",
    "ShortTime",
    "Time",
    "TimeTransformer",
)


class ShortTime:
    """Short time notation, i.e. "1h30m", "2d" or Discord timestamp like ``<t:1700000000:R>``.

    Attributes
    ----------
    dt
        The moment in time the argument stands for (aware, UTC).
    """

    compiled = re.compile(
        r"""
            (?:(?P<years>[0-9]{1,3})(?:years?|y))?                 # e.g. 2y
            (?:(?P<months>[0-9]{1,3})(?:months?|mon?))?            # e.g. 2months
            (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?                 # e.g. 10w
            (?:(?P<days>[0-9]{1,5})(?:days?|d))?                   # e.g. 14d
            (?:(?P<hours>[0-9]{1,5})(?:hours?|hr?s?))?             # e.g. 12h
            (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m(?:ins?)?))?    # e.g. 10m
            (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s(?:ecs?)?))?    # e.g. 15s
        """,
        re.VERBOSE,
    )

    discord_fmt = re.compile(r"<t:(?P<ts>[0-9]+)(?:\:?[RFfDdTt])?>")

    def __init__(self, argument: str, *, now: dt.datetime | None = None) -> None:
        """Parse the argument.

        Parameters
        ----------
        argument
            The text to parse.
        now
            The moment to count the time from. Defaults to the current moment.

        Raises
        ------
        errors.BadUserInputError
            If the argument is not a short time or the resulting date is out of range.
        """
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            match = self.discord_fmt.fullmatch(argument)
            if match is None:
                msg = "invalid time provided"
                raise errors.BadUserInputError(msg)
            try:
                self.dt: dt.datetime = dt.datetime.fromtimestamp(int(match.group("ts")), tz=dt.UTC)
            except (OverflowError, ValueError, OSError):
                msg = "That timestamp is out of range."
                raise errors.BadUserInputError(msg) from None
            return

        data = {key: int(value) for key, value in match.groupdict(default="0").items()}
        try:
            self.dt = (now or clock.utcnow()) + relativedelta(**data)
        except (OverflowError, ValueError):
            msg = "That is too far away, please choose a closer time."
            raise errors.BadUserInputError(msg) from None


class HumanTime:
    """Human time notation, i.e. "tomorrow", "next friday at 3pm", "in 2 weeks".

    Attributes
    ----------
    dt
        The moment in time the argument stands for (aware).
    """

    # en_AU has proper DD MM format
    # https://bear.im/code/parsedatetime/docs/parsedatetime.pdt_locales-pysrc.html#pdtLocale_au.__init__
    # https://bear.im/code/parsedatetime/docs/parsedatetime.pdt_locales-pysrc.html#pdtLocale_base.__init__
    constants = pdt.Constants(localeID="en_AU")
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE, constants=constants)

    def __init__(self, argument: str, *, now: dt.datetime | None = None, tzinfo: dt.tzinfo = dt.UTC) -> None:
        """Parse the argument.

        Parameters
        ----------
        argument
            The text to parse.
        now
            The moment to count the time from. Defaults to the current moment.
        tzinfo
            Timezone to understand the argument in, i.e. the one of the user:
            "tomorrow at 6pm" means 6pm *in their timezone*.

        Raises
        ------
        errors.BadUserInputError
            If the argument can't be understood.
        """
        local_now = (now or clock.utcnow()).astimezone(tzinfo)

        # The parser works with the wall clock time, so it's given the user's local time (without a timezone)
        # and the timezone is attached to the result afterwards.
        parsed, status = self.calendar.parseDT(argument, sourceTime=local_now.replace(tzinfo=None))
        if not status.hasDateOrTime:  # type: ignore[reportAttributeAccess]
            msg = 'invalid time provided, try e.g. "tomorrow" or "3 days"'
            raise errors.BadUserInputError(msg)

        parsed = parsed.replace(tzinfo=tzinfo)
        if not status.hasTime:  # type: ignore[reportAttributeAccess]
            # replace it with the current time
            parsed = parsed.replace(
                hour=local_now.hour,
                minute=local_now.minute,
                second=local_now.second,
                microsecond=local_now.microsecond,
            )
        elif not status.hasDate and parsed < local_now:  # type: ignore[reportAttributeAccess]
            # the time (without a date) has already passed today, so assume the next occurrence of that time
            parsed += dt.timedelta(days=1)

        self.dt: dt.datetime = parsed
        self._past: bool = parsed < local_now


class Time(HumanTime):
    """Either a short time or a human time, whichever the argument turns out to be."""

    @override
    def __init__(self, argument: str, *, now: dt.datetime | None = None, tzinfo: dt.tzinfo = dt.UTC) -> None:
        try:
            short = ShortTime(argument, now=now)
        except errors.BadUserInputError:
            super().__init__(argument, now=now, tzinfo=tzinfo)
        else:
            self.dt = short.dt
            self._past = self.dt < (now or clock.utcnow())


class FutureTime(Time):
    """Same as `Time` but the moment must be in the future."""

    @override
    def __init__(self, argument: str, *, now: dt.datetime | None = None, tzinfo: dt.tzinfo = dt.UTC) -> None:
        super().__init__(argument, now=now, tzinfo=tzinfo)

        if self._past:
            msg = "This time is in the past"
            raise errors.BadUserInputError(msg)


class TimeTransformer(app_commands.Transformer):
    """Transformer for slash commands that turns user's input into a moment in the future.

    The input is understood in the timezone the user has set with `/timezone set` (UTC otherwise).
    """

    @override
    async def transform(self, interaction: Interaction, value: str) -> dt.datetime:
        tzinfo = await interaction.client.tz_manager.get_tzinfo(interaction.user.id)
        return FutureTime(value, now=interaction.created_at, tzinfo=tzinfo).dt
