from __future__ import annotations

import datetime
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Sequence, TypeVar

import discord
from discord.ext import tasks
from discord.utils import MISSING

from .cog import AluCog

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)

__all__ = ("aluloop",)

_func = Callable[..., Coroutine[Any, Any, Any]]
LF = TypeVar("LF", bound=_func)


class AluLoop(tasks.Loop[LF]):
    """
    Subclass for discord.ext.tasks.Loop
    for extra standard needed functionality
    """

    def __init__(
        self,
        coro: LF,
        seconds: float,
        hours: float,
        minutes: float,
        time: datetime.time | Sequence[datetime.time],
        count: int | None,
        reconnect: bool,
        name: str | None,
    ) -> None:
        super().__init__(coro, seconds, hours, minutes, time, count, reconnect, name)
        self._before_loop = self._base_before_loop

    async def _base_before_loop(self, *args: Any) -> None:
        """
        I want to give a standard coro to `_before_loop`.

        Otherwise every task has same
        >>> @my_task.before_loop
        >>> @other_task.before_loop
        >>> async def my_task_before(self):
        >>>     await self.bot.wait_until_ready()

        fragment of code.
        """

        # this will fail outside a cog
        # but all my tasks are inside cogs anyway.
        cog = args[0]
        if isinstance(cog, AluCog):
            await cog.bot.wait_until_ready()

    async def _error(self, *args: Any) -> None:
        """
        Same _error as in parent class but
        added sending webhook notifications to my spam
        """
        exception: Exception = args[-1]
        # log.error('Unhandled exception in internal background task %r.', self.coro.__name__, exc_info=exception)

        embed = (
            discord.Embed(title=self.coro.__name__, colour=0xEF7A85)
            .set_author(name=f"{self.coro.__module__}: {self.coro.__qualname__}")
            .set_footer(text="Error in aluloop task")
        )

        # this will fail outside a cog or a bot class
        # but all my tasks are inside those anyway.
        cog: AluCog = args[0]
        try:  
            # if isinstance(cog, AluCog):
            # not that this code will work for task inside any class that has .bot as its attribute
            # like we use it in cache class
            await cog.bot.exc_manager.register_error(exception, embed, where=f"aluloop {self.coro.__name__}")
        except AttributeError:
            bot: AluBot = args[0]
            # if isinstance(cog, AluBot):
            # this will work for tasks inside the bot class
            await bot.exc_manager.register_error(exception, embed, where=f"aluloop {self.coro.__name__}")
        # otherwise we can't reach bot.exc_manager
        # so maybe add some other webhook?


# Slight note, if `discord.ext.tasks` gets extra cool features
# which will be represented in a change of `tasks.loop` decorator/its signature
# which we do not import/inherit so check out for updates in discord.py
@discord.utils.copy_doc(tasks.loop)
def aluloop(
    *,
    seconds: float = MISSING,
    minutes: float = MISSING,
    hours: float = MISSING,
    time: datetime.time | Sequence[datetime.time] = MISSING,
    count: int | None = None,
    reconnect: bool = True,
    name: str | None = None,
) -> Callable[[LF], AluLoop[LF]]:
    def decorator(func) -> AluLoop:
        return AluLoop(
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            count=count,
            time=time,
            reconnect=reconnect,
            name=name,
        )

    return decorator
