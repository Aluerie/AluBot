from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord import app_commands
from discord.ext import commands

from .. import const

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluContext

T = TypeVar("T")


# Permissions


def hybrid_has_permissions(**perms: bool) -> Callable[[T], T]:
    """Helper function for permission check decorator within hybrid commands.

    Notes
    -----
    * Prefix command permissions will be check bot-side and be dependant on what's in the code.
    * While slash command permissions are only recommended defaults and checked server side.
        Server owners can change it in any way they like on the Integrations page

    """

    def decorator(func: T) -> T:
        commands.has_permissions(**perms)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


def is_manager() -> Callable[[T], T]:
    """Only managers (manage server permission in role settings) are allowed to use this hybrid command."""
    return hybrid_has_permissions(manage_guild=True)


def is_mod() -> Callable[[T], T]:
    """Only moderators (people who can ban members and delete messages) are allowed to use this hybrid command."""
    return hybrid_has_permissions(ban_members=True, manage_messages=True)


def is_admin() -> Callable[[T], T]:
    """Only administrators are allowed to use this hybrid command."""
    return hybrid_has_permissions(administrator=True)


# In Guilds


def is_in_guilds(
    *guild_ids: int,
    error_text: str = "Sorry! This command is not usable outside of specific servers.",
) -> Callable[[T], T]:
    """Helper function to create decorators within hybrid commands that locks command behind certain guilds.

    Notes
    -----
    * Guilds for prefix command will be checked bot-side.
    * While slash command are handled discord-server side and they just only get synced to provided guilds.

    """

    def predicate(ctx: AluContext) -> bool:
        if ctx.guild and ctx.guild.id in guild_ids:
            return True
        else:
            raise commands.CheckFailure(error_text)

    def decorator(func: T) -> T:
        commands.check(predicate)(func)
        app_commands.guilds(*guild_ids)(func)
        return func

    return decorator


def is_my_guild() -> Callable[[T], T]:
    """Restrict hybrid command to my guilds (community and hideout)."""
    return is_in_guilds(*const.MY_GUILDS)


def is_community() -> Callable[[T], T]:
    """Restrict hybrid command to my community server."""
    return is_in_guilds(const.Guild.community)


def is_hideout() -> Callable[[T], T]:
    """Restrict hybrid command to my hideout server."""
    return is_in_guilds(const.Guild.hideout)


def is_premium_guild() -> Callable[[T], T]:
    """Restrict hybrid command to premium servers.

    Currently, "Premium servers" just means these servers can use FPC notifications commands to set them up.
    It is not connected with any type of subscriptions, donations or newish discord features enabling premium bots.
    """
    # async def predicate(ctx: AluContext) -> bool:
    #     """only premium servers"""
    #     if not ctx.guild:
    #         raise commands.CheckFailure("Sorry! This command can only be used within premium servers.")

    #     query = "SELECT premium FROM guild_settings WHERE guild_id=$1"
    #     premium: bool = await ctx.pool.fetchval(query, ctx.guild.id)
    #     if not premium:
    #         raise commands.CheckFailure(
    #             "Sorry! This server is not a premium server thus doesn't have access to premium features/commands."
    #         )
    #     return True

    # def decorator(func: T) -> T:
    #     commands.check(predicate)(func)
    #     return func

    # Note to possible future:
    # if my bot actually becomes popular and premium thing will be a database subscription
    # then we will need to rework this concept into something where all premium commands get added everywhere
    # as in without `app_commands.guilds(*guild_ids)`
    # and when non-premium guild calls it - they get a response saying they are not premium guild
    # kinda like all existing bots. This is super annoying tho from a user perspective so maybe
    # hopefully discord comes with some better solution for this.

    return is_in_guilds(*const.PREMIUM_GUILDS)


def is_premium_guild_manager() -> Callable[[T], T]:
    """Restrict hybrid command to premium servers and only allow server managers to use it."""

    def decorator(func: T) -> T:
        is_premium_guild()(func)
        commands.has_permissions(manage_guild=True)(func)
        app_commands.default_permissions(manage_guild=True)(func)
        return func

    return decorator


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
