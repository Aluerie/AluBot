from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

import discord
from discord import app_commands
from discord.ext import commands

from .var import Sid

if TYPE_CHECKING:
    from .bases.context import AluContext, AluGuildContext
    from .bot import AluBot

T = TypeVar('T')


def is_guild_owner():
    def predicate(ctx: AluGuildContext) -> bool:
        """server owner only"""
        if ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            raise commands.CheckFailure(message='Sorry, only server owner is allowed to use this command')

    return commands.check(predicate)


def is_trustee():
    async def pred(ctx_ntr: AluContext | discord.Interaction[AluBot]) -> bool:
        """trustees only"""
        query = 'SELECT trusted_ids FROM botinfo WHERE id=$1'
        trusted_ids = await ctx_ntr.client.pool.fetchval(query, Sid.alu)
        if ctx_ntr.user.id in trusted_ids:
            return True
        else:
            raise commands.CheckFailure(message='Sorry, only trusted people can use this command')

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.check(pred)(func)
        app_commands.default_permissions(administrator=True)(func)
        return func

    return decorator


def is_owner():
    async def predicate(ctx: AluContext) -> bool:
        """Aluerie only"""
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner()
        return True

    def decorator(func: T) -> T:
        commands.check(predicate)(func)
        return func

    return decorator


# ######################################################################################################################
# ################################# Hybrid checks ######################################################################
# ######################################################################################################################


async def check_guild_permissions(ctx: AluGuildContext, perms: dict[str, bool], *, check=all):
    if await ctx.bot.is_owner(ctx.author):  # type: ignore
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def hybrid_permissions_check(**perms: bool) -> Callable[[T], T]:
    async def pred(ctx: AluGuildContext):
        return await check_guild_permissions(ctx, perms)

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


# for following `is_manager`, `is_mod`, `is_admin check` we could use `hybrid_permissions_check`
# but I need to manually define docstring so /help command can catch it
# Unfortunately, I don't know any other way
# ToDo: figure a way to get docs to decorators instead of to predicates


# def is_manager():
#     """managers only"""
#     return hybrid_permissions_check(manage_guild=True)
def is_manager():
    perms = {'manage_guild': True}

    async def pred(ctx: AluGuildContext):
        """managers only"""
        return await check_guild_permissions(ctx, perms)

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


# def is_mod():
#     """mods only"""
#     return hybrid_permissions_check(ban_members=True, manage_messages=True)
def is_mod():
    perms = {'ban_members': True, 'manage_messages': True}

    async def pred(ctx: AluGuildContext):
        """mods only"""
        return await check_guild_permissions(ctx, perms)

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


# def is_admin():
#     """admins only"""
#     return hybrid_permissions_check(administrator=True)
def is_admin():
    perms = {'administrator': True}

    async def pred(ctx: AluGuildContext):
        """admins only"""
        return await check_guild_permissions(ctx, perms)

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator
