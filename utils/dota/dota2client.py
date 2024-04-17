from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from steam import PersonaState
from steam.ext.dota2 import Client

try:
    import config
except ImportError:
    import sys

    sys.path.append("D:/LAPTOP/AluBot")
    import config

from utils import const

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)

__all__ = ("Dota2Client",)


class Dota2Client(Client):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(state=PersonaState.Invisible)
        self._bot: AluBot = bot

    async def login(self) -> None:
        await super().login(config.STEAM_USERNAME, config.STEAM_PASSWORD)
        log.info("We successfully logged invis mode into Steam: %s", config.STEAM_USERNAME)

    async def on_ready(self) -> None:
        if not self._bot.test:
            await self._bot.wait_until_ready()
            embed = discord.Embed(colour=discord.Colour.blue(), description="Dota2Client: `on_ready`.")
            await self._bot.hideout.spam.send(embed=embed)

    async def on_error(self, event: str, error: Exception, *args: object, **kwargs: object) -> None:
        embed = (
            discord.Embed(
                colour=discord.Colour.dark_red(),
                title=f"Error in steam.py's {self.__class__.__name__}",
            )
            .set_author(
                name=f"Event: {event}",
                icon_url=const.Logo.Dota,
            )
            .add_field(
                name="Args",
                value=(
                    "```py\n" + "\n".join(f"[{index}]: {arg!r}" for index, arg in enumerate(args)) + "```"
                    if args
                    else "No Args"
                ),
                inline=False,
            )
            .add_field(
                name="Kwargs",
                value=(
                    "```py\n" + "\n".join(f"[{name}]: {value!r}" for name, value in kwargs.items()) + "```"
                    if kwargs
                    else "No Kwargs"
                ),
                inline=False,
            )
        )
        await self._bot.exc_manager.register_error(error, embed)
