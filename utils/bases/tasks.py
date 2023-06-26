from __future__ import annotations

import datetime
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union

from discord import Embed
from discord.ext import tasks
from discord.utils import MISSING

from .cog import AluCog

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

__all__ = ('aluloop',)


class AluLoop(tasks.Loop):
    """
    Subclass for discord.ext.tasks.Loop
    for extra standard needed functionality
    """

    def __init__(
        self,
        coro: Any,
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
        log.error('Unhandled exception in internal background task %r.', self.coro.__name__, exc_info=exception)

        # this will fail outside a cog
        # but all my tasks are inside cogs anyway.
        cog = args[0]
        if isinstance(cog, AluCog):
            # TODO: make a better embed out of this
            e = Embed(description=f'Something happened in `{self.coro.__name__}`')
            await cog.bot.send_exception(exception, embed=e)


# Slight note, if `discord.ext.tasks` gets extra cool features
# which will be represented in a change of `tasks.loop` decorator/its signature
# which we do not import/inherit so check out for updates in discord.py
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
