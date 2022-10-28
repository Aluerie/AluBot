from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from . import database as db
from .var import *

if TYPE_CHECKING:
    from context import Context


def is_guild_owner():
    def predicate(ctx: Context) -> bool:
        """server owner only"""
        if ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only guild owner is allowed to use this command'
            )
    return commands.check(predicate)


def is_trustee():
    def predicate(ctx: Context) -> bool:
        """trustees only"""
        trusted_ids = db.get_value(db.b, Sid.alu, 'trusted_ids')
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
            raise commands.NotOwner(
                f'Only {ctx.bot.owner} as the bot owner is allowed to use this command.'
            )
        return True
    return commands.check(predicate)

