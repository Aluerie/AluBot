from __future__ import annotations

import datetime
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, Sequence, TypeVar, Union

import discord
from discord.ext import tasks
from discord.utils import MISSING

from .cog import AluCog

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

__all__ = ('aluloop',)

_func = Callable[..., Coroutine[Any, Any, Any]]
LF = TypeVar('LF', bound=_func)


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
        time: Union[datetime.time, Sequence[datetime.time]],
        count: int | None,
        reconnect: bool,
        name: Optional[str],
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

        # this will fail outside a cog
        # but all my tasks are inside cogs anyway.
        cog = args[0]
        if isinstance(cog, AluCog):
            e = discord.Embed(title=self.coro.__name__, colour=0xef7a85)
            e.set_author(name='Error in aluloop task')
            await cog.bot.exc_manager.register_error(exception, e, where=f'aluloop {self.coro.__name__}')


# Slight note, if `discord.ext.tasks` gets extra cool features
# which will be represented in a change of `tasks.loop` decorator/its signature
# which we do not import/inherit so check out for updates in discord.py
@discord.utils.copy_doc(tasks.loop)
def aluloop(
    *,
    seconds: float = MISSING,
    minutes: float = MISSING,
    hours: float = MISSING,
    time: Union[datetime.time, Sequence[datetime.time]] = MISSING,
    count: Optional[int] = None,
    reconnect: bool = True,
    name: Optional[str] = None,
):
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
