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
    def __init__(self, bot: AluBot):
        super().__init__(state=PersonaState.Invisible)
        self._bot: AluBot = bot

    async def login(self):
        if self._bot.test:
            username, password = (config.TEST_STEAM_USERNAME, config.TEST_STEAM_PASSWORD)
        else:
            username, password = (config.STEAM_USERNAME, config.STEAM_PASSWORD)
        await super().login(username, password)
        log.info("We successfully logged invis mode into Steam: %s", username)

    async def on_ready(self) -> None:
        if not self._bot.test:
            await self._bot.wait_until_ready()
            embed = discord.Embed(colour=discord.Colour.blue(), description="Dota2Client: `on_ready`.")
            await self._bot.hideout.spam.send(embed=embed)

    async def on_error(self, event: str, error: Exception, *args: object, **kwargs: object):
        embed = discord.Embed(
            colour=discord.Colour.dark_red(),
            title=f"Error in steam.py's {self.__class__.__name__}",
        ).set_author(
            name=f"Event: {event}",
            icon_url=const.Logo.dota,
        )

        # kwargs
        args_str = ["```py"]
        for value in args:
            args_str.append(f"{value!r}")
        else:
            args_str.append("No args")
        embed.add_field(name="Args", value="\n".join(args_str), inline=False)

        # kwargs
        kwargs_str = ["```py"]
        for name, value in kwargs.items():
            kwargs_str.append(f"[{name}]: {value!r}")
        else:
            kwargs_str.append("No kwargs")
        embed.add_field(name="Kwargs", value="\n".join(kwargs_str), inline=False)

        await self._bot.exc_manager.register_error(error, source=embed, where="Dota2Client")
