from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict, override

from roleidentification import get_roles

from ..cache import NewKeysCache

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from bot import AluBot

    class ChampionCache(TypedDict):
        id_by_name: MutableMapping[str, int]
        name_by_id: MutableMapping[int, str]
        icon_by_id: MutableMapping[int, str]
        alias_by_id: MutableMapping[int, str]


__all__ = (
    "Champions",
    "ItemIcons",
    "RuneIcons",
    "SummonerSpellIcons",
)


BASE_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"


def cdragon_asset_url(path: str) -> str:
    """Return the CDragon url for the given game asset path."""
    path = path.lower()
    splitted = path.split("/lol-game-data/assets/")
    if len(splitted) == 2:
        return BASE_URL + splitted[1]
    return BASE_URL + path


class Champions(NewKeysCache):
    if TYPE_CHECKING:
        cached_data: ChampionCache

    @override
    async def fill_data(self) -> ChampionCache:
        champion_summary = await self.bot.lol.cdragon.get_lol_v1_champion_summary()

        data: ChampionCache = {"id_by_name": {}, "name_by_id": {}, "icon_by_id": {}, "alias_by_id": {}}
        for champion in champion_summary:
            if champion["id"] == -1:
                continue

            data["id_by_name"][champion["name"].lower()] = champion["id"]
            data["name_by_id"][champion["id"]] = champion["name"]
            data["alias_by_id"][champion["id"]] = champion["alias"]
            data["icon_by_id"][champion["id"]] = cdragon_asset_url(champion["squarePortraitPath"])

        return data

    # example of champion values
    # id: 145
    # name: "Kai'Sa" (lower_name in cache "id_by_name": "kai'sa")
    # alias: "Kaisa"  # eats spaces like "MissFortune"
    # icon_url: https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/145.png

    async def id_by_name(self, champion_name: str) -> int:
        """Get champion id by name."""
        return await self.get_value("id_by_name", champion_name.lower())

    async def name_by_id(self, champion_id: int) -> str:
        """Get champion name by id."""
        return await self.get_value("name_by_id", champion_id)

    async def alias_by_id(self, champion_id: int) -> str:
        """Get champion alias by id."""
        return await self.get_value("alias_by_id", champion_id)

    async def icon_by_id(self, champion_id: int) -> str:
        """Get champion icon url by id."""
        return await self.get_value("icon_by_id", champion_id)


class ItemIcons(NewKeysCache[str]):
    @override
    async def fill_data(self) -> dict[int, str]:
        items = await self.bot.lol.cdragon.get_lol_v1_items()
        return {item["id"]: cdragon_asset_url(item["iconPath"]) for item in items}

    async def by_id(self, item_id: int) -> str:
        """Get item icon url by id."""
        return await self.get_value(item_id)


class RuneIcons(NewKeysCache[str]):
    @override
    async def fill_data(self) -> dict[int, str]:
        perks = await self.bot.lol.cdragon.get_lol_v1_perks()
        return {perk["id"]: cdragon_asset_url(perk["iconPath"]) for perk in perks}

    async def by_id(self, rune_id: int) -> str:
        """Get rune icon url by id."""
        return await self.get_value(rune_id)


class SummonerSpellIcons(NewKeysCache[str]):
    @override
    async def fill_data(self) -> dict[int, str]:
        summoner_spells = await self.bot.lol.cdragon.get_lol_v1_summoner_spells()
        return {spell["id"]: cdragon_asset_url(spell["iconPath"]) for spell in summoner_spells}

    async def by_id(self, summoner_spell_id: int) -> str:
        """Get summoner spell icon url by id."""
        return await self.get_value(summoner_spell_id)


class RoleDict(TypedDict):
    TOP: float
    JUNGLE: float
    MIDDLE: float
    BOTTOM: float
    UTILITY: float


class RolesCache(NewKeysCache[RoleDict]):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot=bot)
        self.meraki_patch: str = "Unknown"

    @override
    async def fill_data(self) -> dict[int, RoleDict]:
        """My own analogy to `from roleidentification import pull_data`.

        Meraki's `pull_data` is using `import requests`
        which is blocking, so I have to copypaste it

        We can always check if they changed it at
        https://github.com/meraki-analytics/role-identification
        """
        champion_roles = await self.bot.lol.meraki.get_lol_champion_rates()
        self.meraki_patch = champion_roles["patch"]

        data = {}
        for champion_id, positions in champion_roles["data"].items():
            champion_id = int(champion_id)
            play_rates = {}

            for position, rates in positions.items():
                play_rates[position.upper()] = rates["playRate"]  # type: ignore # wtf ?!
            for position in ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"):
                if position not in play_rates:
                    play_rates[position] = 0.0
            data[champion_id] = play_rates

        data = await self.get_better_champion_roles(data)
        return data

    async def get_missing_from_meraki_champion_ids(self, data_meraki: dict[int, RoleDict] | None = None) -> set[int]:
        data_meraki = data_meraki or await self.get_cached_data()
        name_by_id = await self.bot.lol.champion.get_cache("name_by_id")
        return set(name_by_id.keys()) - set(data_meraki.keys())

    @staticmethod
    def construct_the_dict(
        playrate: float = 10,  # usually new champions (that are likely to be missing) have rather high playrate
        *,
        top: float = 20,
        jungle: float = 20,
        mid: float = 20,
        bot: float = 20,
        support: float = 20,
    ) -> RoleDict:
        """Construct the dict for meraki function.

        Note all parameters in percent! Just like at www.leagueofgraphs.com
        """
        return {  # global playrate in percent * champion role appearance in %
            "TOP": playrate * top * 0.01,
            "JUNGLE": playrate * jungle * 0.01,
            "MIDDLE": playrate * mid * 0.01,
            "BOTTOM": playrate * bot * 0.01,
            "UTILITY": playrate * support * 0.01,
        }

    async def get_better_champion_roles(self, champion_roles: dict[int, RoleDict]) -> dict[int, RoleDict]:
        """Improvement to meraki's `get_roles()`.

        Unfortunately, Meraki run out of money to support their Json
        Thus sometimes it is behind a few patches and
        I need to add new champions myself with this function.

        About Manual adding part:
        For Example, when 12.13 patch was live - Nilah was not in Meraki Json.
        Thus, I can add it myself with the data from League of Graphs
        https://www.leagueofgraphs.com/champions/stats/nilah/master
        and it here for more precise data rather than 0.2 in all roles.
        """
        diff_list = await self.get_missing_from_meraki_champion_ids(champion_roles)

        # Nilah (data was taken 03/Jan/23) - {id: the_dict}
        # https://www.leagueofgraphs.com/champions/stats/nilah/master
        manual_data = {895: self.construct_the_dict(playrate=2.8, top=0.4, jungle=0.0, mid=1.7, bot=97.4, support=0.4)}
        diff_dict = {x: self.construct_the_dict() for x in diff_list if x not in manual_data}
        return diff_dict | (manual_data | champion_roles)

    async def sort_champions_by_roles(self, all_players_champ_ids: list[int]) -> list[int]:
        try:
            champion_roles: dict[int, RoleDict] = await self.get_cached_data()
            team1 = list(get_roles(champion_roles, all_players_champ_ids[:5]).values())
            team2 = list(get_roles(champion_roles, all_players_champ_ids[5:]).values())
            sorted_list = team1 + team2
            return sorted_list  # type: ignore # meraki typing sucks
        except:
            # there was some problem with probably meraki
            return all_players_champ_ids
