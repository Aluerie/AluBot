"""This code is licensed MPL v2 from Rapptz/RoboDanny
https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py

Most of the code below is a shameless copypaste from @Rapptz's RoboDanny utils
but IDK it's just so good and smart. I really learn a lot from reading @Danny's code.
"""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any, Self, override

import discord
import parsedatetime as pdt
from dateutil.relativedelta import relativedelta
from discord import app_commands
from discord.ext import commands

from .bases import AluBotError

if TYPE_CHECKING:
    from .bases import AluContext


class ShortTime:
    compiled = re.compile(
        """
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
            else:
                msg = "invalid time provided"
                raise commands.BadArgument(msg)

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.datetime.now(datetime.UTC)
        self.dt = now + relativedelta(**data)  # type: ignore #todo: investigate

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
        if not status.hasDateOrTime:  # type: ignore # TODO: fix
            msg = 'invalid time provided, try e.g. "tomorrow" or "3 days"'
            raise commands.BadArgument(msg)

        if not status.hasTime:  # type: ignore # TODO: fix
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
        except Exception:
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


class BadTimeTransform(app_commands.AppCommandError, AluBotError):  # noqa: N818
    pass


class TimeTransformer(app_commands.Transformer):
    @override
    async def transform(self, interaction: discord.Interaction, value: str) -> datetime.datetime:
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

    __slots__ = ("dt", "arg")

    def __init__(self, dt: datetime.datetime) -> None:
        self.dt = dt
        self.arg = ""

    @override
    def __repr__(self) -> str:
        return f"<FriendlyTimeResult dt={self.dt} arg={self.arg}>"

    async def ensure_constraints(
        self, ctx: AluContext, uft: UserFriendlyTime, now: datetime.datetime, remaining: str
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

    @override
    async def convert(self, ctx: AluContext, argument: str) -> FriendlyTimeResult:
        calendar = HumanTime.calendar
        regex = ShortTime.compiled
        now = ctx.message.created_at

        tzinfo = await ctx.bot.tz_manager.get_tzinfo(ctx.author.id)

        match = regex.match(argument)
        if match is not None and match.group(0):
            data = {k: int(v) for k, v in match.groupdict(default=0).items()}
            remaining = argument[match.end() :].strip()
            dt = now + relativedelta(**data)  # type: ignore #todo: investigate
            result = FriendlyTimeResult(dt.astimezone(tzinfo))
            await result.ensure_constraints(ctx, self, now, remaining)
            return result

        if match is None or not match.group(0):
            match = ShortTime.discord_fmt.match(argument)
            if match is not None:
                result = FriendlyTimeResult(
                    datetime.datetime.fromtimestamp(int(match.group("ts")), tz=datetime.UTC).astimezone(tzinfo)
                )
                remaining = argument[match.end() :].strip()
                await result.ensure_constraints(ctx, self, now, remaining)
                return result

        # apparently nlp does not like "from now"
        # it likes "from x" in other cases though so let me handle the 'now' case
        if argument.endswith("from now"):
            argument = argument[:-8].strip()

        if argument[0:2] == "me":  # noqa: SIM102
            # starts with "me to", "me in", or "me at "
            if argument[0:6] in ("me to ", "me in ", "me at "):
                argument = argument[6:]

        # Have to adjust the timezone so pdt knows how to handle things like "tomorrow at 6pm" in an aware way
        now = now.astimezone(tzinfo)
        elements = calendar.nlp(argument, sourceTime=now)
        if elements is None or len(elements) == 0:
            msg = 'Invalid time provided, try e.g. "tomorrow" or "3 days".'
            raise commands.BadArgument(msg)

        # handle the following cases:
        # "date time" foo
        # date time foo
        # foo date time

        # first the first two cases:
        dt, status, begin, end, dt_string = elements[0]

        if not status.hasDateOrTime:
            msg = 'Invalid time provided, try e.g. "tomorrow" or "3 days".'
            raise commands.BadArgument(msg)

        if begin not in (0, 1) and end != len(argument):
            msg = (
                "Time is either in an inappropriate location, which "
                "must be either at the end or beginning of your input, "
                "or I just flat out did not understand what you meant. Sorry."
            )
            raise commands.BadArgument(msg)

        dt = dt.replace(tzinfo=tzinfo)
        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        if status.hasTime and not status.hasDate and dt < now:
            # if it's in the past, and it has a time but no date,
            # assume it's for the next occurrence of that time
            dt = dt + datetime.timedelta(days=1)

        # if midnight is provided, just default to next day
        if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
            dt = dt + datetime.timedelta(days=1)

        result = FriendlyTimeResult(dt.replace(tzinfo=tzinfo))
        remaining = ""

        if begin in (0, 1):
            if begin == 1:
                # check if it's quoted:
                if argument[0] != '"':
                    msg = "Expected quote before time input..."
                    raise commands.BadArgument(msg)

                if not (end < len(argument) and argument[end] == '"'):
                    msg = "If the time is quoted, you must unquote it."
                    raise commands.BadArgument(msg)

                remaining = argument[end + 1 :].lstrip(" ,.!")
            else:
                remaining = argument[end:].lstrip(" ,.!")
        elif len(argument) == end:
            remaining = argument[:begin].strip()

        await result.ensure_constraints(ctx, self, now, remaining)
        return result
