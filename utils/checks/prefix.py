from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands

from .. import const

if TYPE_CHECKING:
    from .. import AluGuildContext

T = TypeVar('T')


def is_in_guilds(
    *guild_ids: int,
    explanation: str = 'Sorry! This command is not usable outside of specific servers',
):
    def predicate(ctx: AluGuildContext) -> bool:
        guild = ctx.guild
        if guild is not None and guild.id in guild_ids:
            return True
        else:
            raise commands.CheckFailure(explanation)

    def decorator(func: T) -> T:
        commands.check(predicate)(func)
        return func

    return decorator


def is_my_guild():
    return is_in_guilds(*const.MY_GUILDS)


def is_community():
    return is_in_guilds(
        const.Guild.community,
        explanation='Sorry! This command is not usable outside of Aluerie\'s Community Server.',
    )
