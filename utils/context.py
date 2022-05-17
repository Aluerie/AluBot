from __future__ import annotations
from typing import TYPE_CHECKING
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import VioletBot
    from aiohttp import ClientSession


class Context(commands.Context):
    bot: VioletBot

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def ses(self) -> ClientSession:
        return self.bot.ses

    async def thinking(self):
        if self.interaction:
            await self.defer()
        else:
            await self.typing()
