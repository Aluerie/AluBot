from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine, Sequence
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

import discord
from discord.ext import tasks
from discord.utils import MISSING

from utils import fmt

if TYPE_CHECKING:
    import datetime

    from ..bot import AluBot

    class HasBotAttribute(Protocol):
        bot: AluBot


log = logging.getLogger(__name__)

__all__ = ("aluloop",)

_func = Callable[..., Coroutine[Any, Any, Any]]
LF = TypeVar("LF", bound=_func)


class AluLoop(tasks.Loop[LF]):
    """My subclass for discord.ext.tasks.Loop.

    Just extra boilerplate functionality.

    Notes
    -----
    * This should be used inside a class that having `.bot` attribute for the purpose of error handling/typehinting.
        such as AluCog, KeysCache, etc, because for convenience my function signatures are
        `(self, cog: AluCog, *_: Any)` where `AluCog` is a fake type (the only thing that matters is that it has `.bot`)
    * Thankfully, there is no real need to use tasks outside of cogs.

    """

    def __init__(
        self,
        coro: LF,
        seconds: float,
        hours: float,
        minutes: float,
        time: datetime.time | Sequence[datetime.time],
        count: int | None,
        name: str | None,
        *,
        reconnect: bool,
    ) -> None:
        super().__init__(coro, seconds, hours, minutes, time, count, reconnect, name)
        self._before_loop = self._base_before_loop

    async def _base_before_loop(self, cog: HasBotAttribute) -> None:  # *args: Any
        """A standard coro to `_before_loop`.

        Otherwise every task has same
        ```py
        @my_task.before_loop
        @other_task.before_loop
        async def my_task_before(self):
            await self.bot.wait_until_ready()
        ```
        fragment of code.

        Can still be overwritten it for custom behavior.
        """
        await cog.bot.wait_until_ready()

    @override
    async def _error(self, cog: HasBotAttribute, exception: Exception) -> None:
        """Same `_error` as in parent class but with `exc_manager` integrated."""
        meta = f"module   = {self.coro.__module__}\nqualname = {self.coro.__qualname__}"
        embed = (
            discord.Embed(title=f"Task Error: `{self.coro.__name__}`", color=0xEF7A85)
            .add_field(name="Meta", value=fmt.code(meta, "ebnf"), inline=False)
            .set_footer(text=f"{self.__class__.__name__}._error: {self.coro.__name__}")
        )
        await cog.bot.exc_manager.register_error(exception, embed)


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
    """Copy-pasted `loop` decorator from `discord.ext.tasks` corresponding to AluLoop class.

    Notes
    -----
    * if `discord.ext.tasks` gets extra cool features which will be represented in a change of `tasks.loop`
        decorator/signature we would need to manually update this function (or maybe even AluLoop class)

    """

    def decorator(func: LF) -> AluLoop[LF]:
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


"""Notes to myself that I'm not sure where to put

* `before_loop/after_loop` only happens before/after the whole "loop" task is done,
    it doesn't trigger before/after iteration. The name is clear.
* `cancel` - not graceful. `stop` - graceful. I have no idea how to remember that.
* `after_loop` will be triggered after both `stop`/`cancel`. The way to distinguish is `is_being_cancelled` property.
"""
