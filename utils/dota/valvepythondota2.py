from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import dataclass
from enum import IntEnum
from operator import attrgetter
from typing import TYPE_CHECKING

from dota2.client import Dota2Client as Dota2Client_
from steam.client import SteamClient

import config

if TYPE_CHECKING:
    from bot import AluBot

    from .schemas import GameCoordinatorAPISchema

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

__all__ = (
    "Dota2Client",
    "LiveMatch",
)


class EDOTAGCMsg(IntEnum):
    EMsgClientToGCFindTopSourceTVGames = 8009
    EMsgGCToClientFindTopSourceTVGamesResponse = 8010


class Dota2Client(Dota2Client_):
    def __init__(self, bot: AluBot):
        super().__init__(SteamClient())
        self.check_list: set[int] = set()
        self.matches: list[GameCoordinatorAPISchema.CSourceTVGameSmall] = []
        self.on(EDOTAGCMsg.EMsgGCToClientFindTopSourceTVGamesResponse, self._handle_top_source_tv)

        self._bot: AluBot = bot
        self.deaths: int = 0

    async def login(self):
        log.debug(f"dota2info: client.connected {self.steam.connected}")
        if self._bot.test:
            username, password = (config.TEST_STEAM_USERNAME, config.TEST_STEAM_PASSWORD)
        else:
            username, password = (config.STEAM_USERNAME, config.STEAM_PASSWORD)

        try:
            if self.steam.login(username=username, password=password):
                self.steam.change_status(persona_state=7)
                log.info("Logged in Steam as `%s`", username)
                self.launch()
        except Exception as exc:
            log.error("Logging in Steam failed")
            await self._bot.exc_manager.register_error(exc, source="Steam login", where="Steam login")

    async def top_live_matches(self) -> list[LiveMatch]:
        log.debug("Steam is connected: %s", self.steam.connected)
        if not self.steam.connected:
            await self._bot.hideout.spam.send("Dota2Client: Steam is not connected.")

        self.check_list = {i * 10 for i in range(0, 10)}
        self.matches = []
        self.send(EDOTAGCMsg.EMsgClientToGCFindTopSourceTVGames, {"start_game": 90})
        # can it fix the blocking problem ?
        # https://github.com/gfmio/asyncio-gevent?tab=readme-ov-file#converting-greenlets-to-asyncio-futures
        self.wait_event("live_matches_ready", timeout=4)
        if self.check_list:
            self.deaths += 1
            # we didn't cross out all checking `start_game`-s
            if self.deaths > 4:
                self.exit()
                self.steam.logout()
                await asyncio.sleep(10.0)
                await self.login()
            raise asyncio.TimeoutError
        else:
            self.deaths = 0
            return [LiveMatch(match) for match in self.matches]

    def _handle_top_source_tv(self, message: GameCoordinatorAPISchema.GCToClientFindTopSourceTVGamesResponse):
        for match in message.game_list:
            self.matches.append(match)

        self.check_list.discard(message.start_game)
        if not self.check_list:
            self.emit("live_matches_ready")


class LiveMatch:
    def __init__(self, proto: GameCoordinatorAPISchema.CSourceTVGameSmall) -> None:
        self.id = proto.match_id
        self.start_time = datetime.datetime.fromtimestamp(proto.activate_time, datetime.timezone.utc)
        self.server_steam_id = proto.server_steam_id

        sorted_players = sorted(proto.players, key=attrgetter("team", "team_slot"))
        self.players = [LiveMatchPlayer(id=p.account_id, hero=Hero(id=p.hero_id)) for p in sorted_players]

    @property
    def heroes(self):
        return [p.hero for p in self.players]


@dataclass
class LiveMatchPlayer:
    id: int
    hero: Hero


@dataclass
class Hero:
    id: int
