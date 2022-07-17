from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

from utils.var import *
from utils import database as db

if TYPE_CHECKING:
    from utils.context import Context


def is_guild_owner():
    def predicate(ctx: Context):
        """server owner only"""
        if ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only guild owner is allowed to use this command'
            )
    return commands.check(predicate)


def is_trusted_user():
    def predicate(ctx: Context):
        """trustees only"""
        trusted_ids = db.get_value(db.b, Sid.alu, 'trusted_ids')
        if ctx.author.id in trusted_ids:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only trusted janitors can use this command'
            )
    return commands.check(predicate)