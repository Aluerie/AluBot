from __future__ import annotations
from typing import TYPE_CHECKING, Callable, TypeVar

from discord import app_commands
from discord.ext import commands

from .var import Sid

if TYPE_CHECKING:
    from .context import GuildContext, Context

T = TypeVar('T')


def is_guild_owner():
    def predicate(ctx: Context) -> bool:
        """server owner only"""
        if ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only server owner is allowed to use this command'
            )
    return commands.check(predicate)


def is_trustee():
    async def predicate(ctx: Context) -> bool:
        """trustees only"""
        query = 'SELECT trusted_ids FROM botinfo WHERE id=$1'
        trusted_ids = await ctx.pool.fetchval(query, Sid.alu)
        if ctx.author.id in trusted_ids:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only trusted people can use this command'
            )
    return commands.check(predicate)


def is_owner():
    async def predicate(ctx: Context) -> bool:
        """Aluerie only"""
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner()
        return True

    def decorator(func: T) -> T:
        commands.check(predicate)(func)
        return func

    return decorator


#####################################

async def check_guild_permissions(ctx: GuildContext, perms: dict[str, bool], *, check=all):
    if await ctx.bot.is_owner(ctx.author):  # type: ignore
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def hybrid_permissions_check(**perms: bool) -> Callable[[T], T]:
    async def pred(ctx: GuildContext):
        return await check_guild_permissions(ctx, perms)

    def decorator(func: T) -> T:
        commands.check(pred)(func)
        app_commands.default_permissions(**perms)(func)
        return func

    return decorator


def is_mod():
    return hybrid_permissions_check(ban_members=True, manage_messages=True)


def is_admin():
    return hybrid_permissions_check(administrator=True)