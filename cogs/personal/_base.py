from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.var import Sid

if TYPE_CHECKING:
    from utils.bot import AluBot


class HideoutBase(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def hideout(self) -> discord.Guild:
        return self.bot.get_guild(Sid.test)  # type: ignore
