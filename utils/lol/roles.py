from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TypedDict

from roleidentification import get_roles

from ..cache import KeysCache
from .champion import all_champion_ids

if TYPE_CHECKING:

    class RoleDict(TypedDict):
        TOP: float
        JUNGLE: float
        MIDDLE: float
        BOTTOM: float
        UTILITY: float


__all__ = (
    "get_missing_from_meraki_champion_ids",
    "get_meraki_patch",
    "sort_champions_by_roles",
)


class RolesCache(KeysCache):
    def __init__(self):
        super().__init__()
        self.meraki_patch: str = ""

    async def fill_data(self) -> dict:
        """My own analogy to `from roleidentification import pull_data`

        Meraki's `pull_data` is using `import requests`
        which is blocking, so I have to copypaste it

        We can always check if they changed it at
        https://github.com/meraki-analytics/role-identification
        """

        url = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json"
        champion_roles_json = await self.get_response_json(url=url)
        self.meraki_patch = champion_roles_json["patch"]
        data = {}
        for champion_id, positions in champion_roles_json["data"].items():
            champion_id = int(champion_id)
            play_rates = {}
            for position, rates in positions.items():
                play_rates[position.upper()] = rates["playRate"]
            for position in ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"):
                if position not in play_rates:
                    play_rates[position] = 0.0
            data[champion_id] = play_rates

        data = await self.get_champion_roles(data)
        return data

    @staticmethod
    async def get_champion_roles(champion_roles: dict[int, RoleDict]) -> dict[int, RoleDict]:
        """Improvement to meraki's `get_roles()`

        Unfortunately, Meraki run out of money to support their Json
        Thus sometimes it is behind a few patches and
        I need to add new champions myself with this function.

        About Manual adding part:
        For Example, when 12.13 patch was live - Nilah was not in Meraki Json.
        Thus, I can add it myself with the data from League of Graphs
        https://www.leagueofgraphs.com/champions/stats/nilah/master
        and it here for more precise data rather than 0.2 in all roles.
        """
        diff_list = await get_missing_from_meraki_champion_ids(champion_roles)

        def construct_the_dict(
            playrate: float = 10,
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

        # Nilah (data was taken 03/Jan/23) - {id: the_dict}
        # https://www.leagueofgraphs.com/champions/stats/nilah/master
        manual_data = {895: construct_the_dict(playrate=2.8, top=0.4, jungle=0.0, mid=1.7, bot=97.4, support=0.4)}
        diff_dict = {x: construct_the_dict() for x in diff_list if x not in manual_data}
        return diff_dict | (manual_data | champion_roles)


roles_cache = RolesCache()


async def get_missing_from_meraki_champion_ids(data_meraki: Optional[dict] = None) -> set[int]:
    data_meraki = data_meraki or await roles_cache.get_data()
    return set(await all_champion_ids()) - set(data_meraki.keys())


async def get_meraki_patch():
    await roles_cache.get_data()  # just so it triggers updating the cache, if needed.
    return roles_cache.meraki_patch


async def sort_champions_by_roles(all_players_champ_ids: list[int]) -> list[int]:
    try:
        champion_roles: dict[int, RoleDict] = await roles_cache.get_data()
        team1 = list(get_roles(champion_roles, all_players_champ_ids[:5]).values())
        team2 = list(get_roles(champion_roles, all_players_champ_ids[5:]).values())
        sorted_list = team1 + team2
        return sorted_list  # type: ignore # meraki typing sucks
    except:
        # there was some problem with probably meraki
        return all_players_champ_ids