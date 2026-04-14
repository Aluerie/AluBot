from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

import discord
from steam import PersonaState
from steam.ext.dota2 import Client

from config import config
from utils import const, fmt

from .pulsefire_clients import OpenDotaConstantsClient, StratzClient
from .storage import Abilities, Facets, Heroes, Items

if TYPE_CHECKING:
    from steam.ext.dota2 import PartialUser

    from bot import AluBot

log = logging.getLogger(__name__)

__all__ = ("DotaClient",)


class DotaClient(Client):
    """My subclass to steam.py's Dota 2 Client.

    Extends functionality to provide
    * access to stats/data related API like stratz;
    * access to modelled constants;
    * integration with my discord bot such as error notifications;
    * etc.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__(state=PersonaState.Online)  # .Invisible
        self.bot: AluBot = bot
        self.started: bool = False

        # # TODO: EXPERIMENT
        # # https://discord.com/channels/678629505094647819/1019749658551144458/1341421914714804296
        # self.http.api_key = config["TOKENS"]["STEAM"]

        # clients
        self.stratz = StratzClient()
        self.opendota_constants = OpenDotaConstantsClient()
        # storages
        self.abilities = Abilities(bot)
        self.heroes = Heroes(bot)
        self.items = Items(bot)
        self.facets = Facets(bot)

    def aluerie(self) -> PartialUser:
        """Shortcut to get partial user object for @Aluerie's steam/dota2 profile."""
        return self.create_partial_user(config["STEAM"]["ALUERIE_FRIEND_ID"])

    async def start_helpers(self) -> None:
        """Starting helping clients, tasks and services.

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
            await self.stratz.__aenter__()  # noqa: PLC2801
            await self.opendota_constants.__aenter__()  # noqa: PLC2801

            # caches
            self.abilities.start()
            self.heroes.start()
            self.items.start()
            self.facets.start()

            self.started = True

    @override
    async def login(self) -> None:
        await self.start_helpers()

        account_credentials = config["STEAM"]["ALUBOT"] if not self.bot.test else config["STEAM"]["YENBOT"]
        username, password = account_credentials["USERNAME"], account_credentials["PASSWORD"]
        await super().login(username, password)
        log.info("We logged into Steam: %s", username)

        # # TODO: EXPERIMENT
        # # https://discord.com/channels/678629505094647819/1019749658551144458/1341421914714804296
        # self.http.api_key = config["TOKENS"]["STEAM"]

    @override
    async def close(self) -> None:
        await self.bot.send_warning("DotaClient is closing.")
        # clients
        await self.stratz.__aexit__()
        await self.opendota_constants.__aexit__()

        # caches
        self.abilities.close()
        self.heroes.close()
        self.items.close()
        self.facets.close()

    @override
    async def on_ready(self) -> None:
        if not self.bot.test:
            await self.bot.send_warning("DotaClient is ready.")

    @override
    async def on_error(self, event: str, error: Exception, *args: object, **kwargs: object) -> None:
        args_join = "\n".join(f"[{index}]: {arg!r}" for index, arg in enumerate(args)) if args else "No Args"
        kwargs_join = "\n".join(f"[{name}]: {value!r}" for name, value in kwargs.items()) if kwargs else "No Kwargs"
        embed = (
            discord.Embed(
                color=discord.Color.dark_red(),
                title=f"Error in steam.py's {self.__class__.__name__}",
            )
            .set_author(name=f"Event: {event}", icon_url=const.Logo.Dota)
            .add_field(name="Args", value=fmt.code(args_join), inline=False)
            .add_field(name="Kwargs", value=fmt.code(kwargs_join), inline=False)
        )
        await self.bot.exc_manager.register_error(error, embed)
