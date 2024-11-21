from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

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

from . import ODotaConstantsClient, StratzClient
from .storage import Abilities, Facets, Heroes, Items

if TYPE_CHECKING:
    from steam.ext.dota2 import PartialUser

    from bot import AluBot

log = logging.getLogger(__name__)

__all__ = ("Dota2Client",)


class Dota2Client(Client):
    """My subclass to steam.py's Dota 2 Client.

    Extends functionality to provide
    * access to stats/data related API like stratz;
    * access to modelled constants;
    * integration with my discord bot such as error notifications;
    * etc.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__()  # state=PersonaState.Invisible
        self.bot: AluBot = bot

        # clients
        self.stratz = StratzClient()
        self.odota_constants = ODotaConstantsClient()
        # caches
        self.abilities = Abilities(bot)
        self.heroes = Heroes(bot)
        self.items = Items(bot)
        self.facets = Facets(bot)

        self.started = False

    def aluerie(self) -> PartialUser:
        return self.instantiate_partial_user(config.DOTA_FRIEND_ID)

    async def start_helpers(self) -> None:
        """_summary_

        Usage
        -----
        If we only want to test helpers functionality, i.e. Stratz API data, then we can use:
        ```py
        self.bot.instantiate_dota()
        await self.bot.dota.start_helpers()  # only starts helping clients/caches.
        ```
        """
        if not self.started:
            # clients
            await self.stratz.__aenter__()
            await self.odota_constants.__aenter__()

            # caches
            self.abilities.start()
            self.heroes.start()
            self.items.start()
            self.facets.start()

            self.started = True

    # @override
    # async def __aenter__(self) -> Self:
    #     # clients
    #     await self.stratz.__aenter__()
    #     await self.odota_constants.__aenter__()

    #     # caches
    #     self.abilities.start()
    #     self.heroes.start()
    #     self.items.start()
    #     self.facets.start()

    #     return await super().__aenter__()

    # @override
    # async def __aexit__(self) -> None:
    #     # clients
    #     await self.stratz.__aexit__()
    #     await self.odota_constants.__aexit__()

    #     # caches
    #     self.abilities.close()
    #     self.heroes.close()
    #     self.items.close()
    #     self.facets.close()
    #     await super().__aexit__()

    @override
    async def login(self) -> None:
        await self.start_helpers()
        await super().login(config.STEAM_USERNAME, config.STEAM_PASSWORD)
        log.info("We invisibly logged into Steam: %s", config.STEAM_USERNAME)

    @override
    async def close(self) -> None:
        # clients
        await self.stratz.__aexit__()
        await self.odota_constants.__aexit__()

        # caches
        self.abilities.close()
        self.heroes.close()
        self.items.close()
        self.facets.close()

    @override
    async def on_ready(self) -> None:
        if not self.bot.test:
            await self.bot.wait_until_ready()
            embed = discord.Embed(colour=discord.Colour.blue(), description="Dota2Client: `on_ready`.")
            await self.bot.hideout.spam.send(embed=embed)

    @override
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
        await self.bot.exc_manager.register_error(error, embed)
