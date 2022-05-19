from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Union

from discord.ext import commands
from discord.utils import format_dt

from datetime import datetime, timedelta, timezone
from pytimeparse import parse

if TYPE_CHECKING:
    from typing_extensions import Self
    from utils.context import Context


class DTFromStr:
    def __init__(self, argument: str, *, now: Optional[datetime] = None):
        if (seconds := parse(argument)) is None:
            raise commands.BadArgument('invalid time provided')  # TODO check how this interacts with commands
        self.seconds: int = seconds
        self.delta: timedelta = timedelta(seconds=seconds)
        now = now or datetime.now(timezone.utc)
        self.dt: datetime = now + self.delta
        self.fdt_r = format_dt(self.dt, style='R')

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        return cls(argument, now=ctx.message.created_at)


def arg_to_timetext(arg):  # TODO: rewrite this into a class and maybe better ideas
    """
    Convert a string into its epoch_time + remaining string:
        "1 hours hello"     => (3600, "hello")
        "15m 3s where"      => (903, "where")
    """
    check_array, time_seconds, result = '', None, None
    for word in arg.split():
        check_array += word
        if new_time := parse(check_array):
            time_seconds = new_time
            try:
                result = arg.split(word + ' ')[1]
            except IndexError:
                result = 'Empty text'
    return time_seconds, result

