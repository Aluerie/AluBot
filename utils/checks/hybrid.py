from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

import discord
from discord import app_commands
from discord.ext import commands

from .. import const
from . import app, txt

if TYPE_CHECKING:
    from .. import AluBot, AluContext

T = TypeVar('T')


def hybrid_has_permissions(**perms: bool) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        commands.check_any(commands.has_permissions(**perms), commands.is_owner())  # let bot owner surpass those too
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


def is_manager():
    return hybrid_has_permissions(manage_guild=True)


def is_mod():
    return hybrid_has_permissions(ban_members=True, manage_messages=True)


def is_admin():
    return hybrid_has_permissions(administrator=True)


def is_trustee():
    async def pred(ctx_ntr: AluContext | discord.Interaction[AluBot]) -> bool:
        """trustees only"""
        query = 'SELECT trusted_ids FROM botinfo WHERE id=$1'
        trusted_ids: List[int] = await ctx_ntr.client.pool.fetchval(query, Guild.community)  # type: ignore
        if ctx_ntr.user.id in trusted_ids:
            return True
        else:
            raise commands.CheckFailure(message='Sorry, only trusted people can use this command')

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.check(pred)(func)  # if it's only `app_commands.command` then ^commands wont be triggered.
        app_commands.default_permissions(manage_guild=True)(func)
        return func

    return decorator


def is_in_guilds(*guild_ids: int):
    def decorator(func: T) -> T:
        app.is_in_guilds(*guild_ids)
        txt.is_in_guilds(*guild_ids)
        return func

    return decorator


def is_my_guild():
    return is_in_guilds(*const.MY_GUILDS)


def is_community():
    return is_in_guilds(const.Guild.community)


# for following `is_manager`, `is_mod`, `is_admin check` we could use `hybrid_permissions_check`
# but I need to manually define docstring so /help command can catch it
# Unfortunately, I don't know any other way
# TODO: figure a way to get docs to decorators instead of to predicates like we had below:

# def is_manager():
#     perms = {'manage_guild': True}

#     async def pred(ctx: AluGuildContext):
#         """managers only"""
#         return await check_guild_permissions(ctx, perms)

#     def decorator(func: T) -> T:
#         commands.check(pred)(func)
#         app_commands.default_permissions(**perms)(func)
#         return func

#     return decorator
