"""
This code is licensed MPL v2 from Rapptz/RoboDanny
https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py

Most of the code below is a shameless copypaste from @Rapptz's RoboDanny utils
but IDK it's just so good and smart. I really learn a lot from reading @Danny's code.
"""

from __future__ import annotations

import re
import datetime
from typing import TYPE_CHECKING, Any, Optional, Union

import parsedatetime as pdt
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from discord import app_commands

if TYPE_CHECKING:
    from typing_extensions import Self
    from .context import Context


class ShortTime:
    compiled = re.compile(
        """
        (?:(?P<years>[0-9])(?:years?|y))?             # e.g. 2y
        (?:(?P<months>[0-9]{1,2})(?:months?|mo))?     # e.g. 2months
        (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?        # e.g. 10w
        (?:(?P<days>[0-9]{1,5})(?:days?|d))?          # e.g. 14d
        (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?        # e.g. 12h
        (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?    # e.g. 10m
        (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?    # e.g. 15s
        """,
        re.VERBOSE,
    )

    def __init__(self, argument: str, *, now: Optional[datetime.datetime] = None):
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            raise commands.BadArgument('invalid time provided')

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.datetime.now(datetime.timezone.utc)
        self.dt: datetime.datetime = now + relativedelta(**data)

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        return cls(argument, now=ctx.message.created_at)


class HumanTime:
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument: str, *, now: Optional[datetime.datetime] = None):
        now = now or datetime.datetime.now(datetime.timezone.utc)
        dt, status = self.calendar.parseDT(argument, sourceTime=now)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        if not status.hasDateOrTime:
            raise commands.BadArgument('invalid time provided, try e.g. "tomorrow" or "3 days"')

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.dt: datetime.datetime = dt
        self._past: bool = dt < now

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        return cls(argument, now=ctx.message.created_at)


class Time(HumanTime):
    def __init__(self, argument: str, *, now: Optional[datetime.datetime] = None):
        try:
            o = ShortTime(argument, now=now)
        except Exception as e:
            super().__init__(argument)
        else:
            self.dt = o.dt
            self._past = False


class FutureTime(HumanTime):
    def __init__(self, argument: str, *, now: Optional[datetime.datetime] = None):
        super().__init__(argument, now=now)

        if self._past:
            raise commands.BadArgument('this time is in the past')


class BadTimeTransform(app_commands.AppCommandError):
    pass


class TimeTransformer(app_commands.Transformer):
    async def transform(self, interaction, value: str) -> datetime.datetime:
        now = interaction.created_at.replace(tzinfo=None)
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

    __slots__ = ('dt', 'arg')

    def __init__(self, dt: datetime.datetime):
        self.dt = dt
        self.arg = ''

    async def ensure_constraints(
            self,
            ctx: Context,
            uft: UserFriendlyTime,
            now: datetime.datetime,
            remaining: str
    ) -> None:
        if self.dt < now:
            raise commands.BadArgument('This time is in the past.')

        if not remaining:
            if uft.default is None:
                raise commands.BadArgument('Missing argument after the time.')
            remaining = uft.default

        if uft.converter is not None:
            self.arg = await uft.converter.convert(ctx, remaining)
        else:
            self.arg = remaining


class UserFriendlyTime(commands.Converter):
    """That way quotes aren't absolutely necessary."""

    def __init__(
        self,
        converter: Optional[Union[type[commands.Converter], commands.Converter]] = None,
        *,
        default: Any = None,
    ):
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            raise TypeError('commands.Converter subclass necessary.')

        self.converter: commands.Converter = converter  # type: ignore  # It doesn't understand this narrowing
        self.default: Any = default

    async def convert(self, ctx: Context, argument: str) -> FriendlyTimeResult:
        try:
            calendar = HumanTime.calendar
            regex = ShortTime.compiled
            now = ctx.message.created_at

            match = regex.match(argument)
            if match is not None and match.group(0):
                data = {k: int(v) for k, v in match.groupdict(default=0).items()}
                remaining = argument[match.end():].strip()
                result = FriendlyTimeResult(now + relativedelta(**data))
                await result.ensure_constraints(ctx, self, now, remaining)
                return result

            # apparently nlp does not like "from now"
            # it likes "from x" in other cases though so let me handle the 'now' case
            if argument.endswith('from now'):
                argument = argument[:-8].strip()

            if argument[0:2] == 'me':
                # starts with "me to", "me in", or "me at "
                if argument[0:6] in ('me to ', 'me in ', 'me at '):
                    argument = argument[6:]

            elements = calendar.nlp(argument, sourceTime=now)
            if elements is None or len(elements) == 0:
                raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            # handle the following cases:
            # "date time" foo
            # date time foo
            # foo date time

            # first the first two cases:
            dt, status, begin, end, dt_string = elements[0]

            if not status.hasDateOrTime:
                raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            if begin not in (0, 1) and end != len(argument):
                raise commands.BadArgument(
                    'Time is either in an inappropriate location, which '
                    'must be either at the end or beginning of your input, '
                    'or I just flat out did not understand what you meant. Sorry.'
                )

            if not status.hasTime:
                # replace it with the current time
                dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

            # if midnight is provided, just default to next day
            if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=now.day + 1)

            result = FriendlyTimeResult(dt.replace(tzinfo=datetime.timezone.utc))
            remaining = ''

            if begin in (0, 1):
                if begin == 1:
                    # check if it's quoted:
                    if argument[0] != '"':
                        raise commands.BadArgument('Expected quote before time input...')

                    if not (end < len(argument) and argument[end] == '"'):
                        raise commands.BadArgument('If the time is quoted, you must unquote it.')

                    remaining = argument[end + 1:].lstrip(' ,.!')
                else:
                    remaining = argument[end:].lstrip(' ,.!')
            elif len(argument) == end:
                remaining = argument[:begin].strip()

            await result.ensure_constraints(ctx, self, now, remaining)
            return result
        except:
            import traceback

            traceback.print_exc()
            raise
