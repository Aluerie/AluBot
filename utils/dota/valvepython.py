from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import dataclass
from enum import IntEnum
from operator import attrgetter
from typing import TYPE_CHECKING, override

import discord
from dota2.client import Dota2Client as Dota2Client_
from steam.client import SteamClient

import config

from .pulsefire_clients import ODotaConstantsClient, StratzClient
from .storage import Abilities, Facets, Heroes, Items

if TYPE_CHECKING:
    from bot import AluBot

    from .schemas import game_coordinator

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

__all__ = (
    "DotaClient",
    "LiveMatch",
)


class EDOTAGCMsg(IntEnum):
    EMsgClientToGCFindTopSourceTVGames = 8009
    EMsgGCToClientFindTopSourceTVGamesResponse = 8010


class DotaClient(Dota2Client_):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(SteamClient())
        self.check_list: set[int] = set()
        self.matches: list[game_coordinator.CSourceTVGameSmall] = []
        self.on(EDOTAGCMsg.EMsgGCToClientFindTopSourceTVGamesResponse, self._handle_top_source_tv)

        self.bot: AluBot = bot
        self.deaths: int = 0

        # TEST PRINT
        # self.test_print: bool = False

        # clients
        self.stratz = StratzClient()
        self.odota_constants = ODotaConstantsClient()
        # caches
        self.abilities = Abilities(bot)
        self.heroes = Heroes(bot)
        self.items = Items(bot)
        self.facets = Facets(bot)

        self.started: bool = False

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

    async def start(self) -> None:
        """_summary_

        Usage
        -----
        To start the whole client, including logging into steam/dota use:
        ```py
        self.bot.instantiate_dota()
        await self.bot.dota.start()
        ```
        """
        # VALVE_SWITCH: we need proper close for all of these
        await self.login()
        await self.start_helpers()

    async def close(self) -> None:
        # clients
        await self.stratz.__aexit__()
        await self.odota_constants.__aexit__()

        # caches
        self.abilities.close()
        self.heroes.close()
        self.items.close()
        self.facets.close()

    async def login(self) -> None:
        log.debug("dota2info: client.connected %s", self.steam.connected)
        try:
            if self.steam.login(username=config.STEAM_USERNAME, password=config.STEAM_PASSWORD):
                self.steam.change_status(persona_state=7)
                log.info("Logged in Steam as `%s`", config.STEAM_USERNAME)
                self.launch()
        except Exception as exc:
            log.error("Logging in Steam failed")
            embed = discord.Embed(
                colour=0x233423,
                title="Steam login",
            ).set_footer(text="Dota2Client.login")
            await self.bot.exc_manager.register_error(exc, embed)

    async def top_live_matches(self) -> list[LiveMatch]:
        # log.debug("Steam is connected: %s", self.steam.connected)
        if not self.steam.connected:
            await self.bot.spam.send("Dota2Client: Steam is not connected.")
            log.warning("Dota2Client: Steam is not connected.")
            await asyncio.sleep(3.3)
            await self.login()
            await asyncio.sleep(3.3)

        self.check_list = {i * 10 for i in range(0, 10)}
        self.matches.clear()
        self.send(EDOTAGCMsg.EMsgClientToGCFindTopSourceTVGames, {"start_game": 90})
        # can it fix the blocking problem ?
        # https://github.com/gfmio/asyncio-gevent?tab=readme-ov-file#converting-greenlets-to-asyncio-futures
        self.wait_event("live_matches_ready", timeout=4)
        if self.check_list:
            self.deaths += 1
            # we didn't cross out all checking `start_game`-s
            raise TimeoutError
        else:
            self.deaths = 0
            return [LiveMatch(match) for match in self.matches]

    def _handle_top_source_tv(self, message: game_coordinator.GCToClientFindTopSourceTVGamesResponse) -> None:
        for match in message.game_list:
            self.matches.append(match)

            # TEST PRINT
            # if not self.test_print:
            #     print(match)
            #     self.test_print = True

        self.check_list.discard(message.start_game)
        if not self.check_list:
            self.emit("live_matches_ready")


class LiveMatch:
    def __init__(self, proto: game_coordinator.CSourceTVGameSmall) -> None:
        self.id = proto.match_id
        self.start_time = datetime.datetime.fromtimestamp(proto.activate_time, datetime.UTC)
        self.server_steam_id = proto.server_steam_id

        sorted_players = sorted(proto.players, key=attrgetter("team", "team_slot"))
        self.players = [LiveMatchPlayer(id=p.account_id, hero=Hero(id=p.hero_id)) for p in sorted_players]

    @property
    def heroes(self) -> list[Hero]:
        return [p.hero for p in self.players]

    @override
    def __repr__(self) -> str:
        return f"<LiveMatch id={self.id}"


@dataclass
class LiveMatchPlayer:
    id: int
    hero: Hero


@dataclass
class Hero:
    id: int
