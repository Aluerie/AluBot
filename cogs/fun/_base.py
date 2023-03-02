from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot


class FunBase(commands.Cog):

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
