from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands

from .. import const

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluContext

T = TypeVar("T")


def is_in_guilds(
    *guild_ids: int,
    explanation: str = "Sorry! This command is not usable outside of specific servers",
) -> Callable[[T], T]:
    def predicate(ctx: AluContext) -> bool:
        guild = ctx.guild
        if guild is not None and guild.id in guild_ids:
            return True
        else:
            raise commands.CheckFailure(explanation)

    def decorator(func: T) -> T:
        commands.check(predicate)(func)
        return func

    return decorator


def is_my_guild() -> Callable[[T], T]:
    return is_in_guilds(*const.MY_GUILDS)


def is_community() -> Callable[[T], T]:
    return is_in_guilds(
        const.Guild.community,
        explanation="Sorry! This command is not usable outside of Aluerie's Community Server.",
    )
