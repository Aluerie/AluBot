from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

from pyot.models import lol
from pyot.utils.lol import champion, cdragon
from roleidentification import get_roles

from utils.cache import KeyCache

if TYPE_CHECKING:
    pass

__all__ = (
    'get_pyot_meraki_champ_diff_list',
    'get_meraki_patch',
    'get_all_champ_names',
    'icon_url_by_champ_id',
    'get_role_mini_list',
)


class ChampionRolesCache(KeyCache):
    def __init__(self):
        super().__init__()
        self.meraki_patch: str = ''

    async def fill_data(self) -> dict:
        """My own analogy to `from roleidentification import pull_data`

        Meraki\'s `pull_data` is using `import requests`
        which is blocking, so I have to copypaste it

        We can always check if they changed it at
        https://github.com/meraki-analytics/role-identification
        """

        url = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json"
        champion_roles_json = await self.get_resp_json(url=url)
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
    async def get_champion_roles(champion_roles: dict) -> dict:
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
        diff_list = await get_pyot_meraki_champ_diff_list(champion_roles)

        def construct_the_dict(
            playrate: Optional[float] = 10,
            *,
            top: Optional[float] = 20,
            jungle: Optional[float] = 20,
            mid: Optional[float] = 20,
            bot: Optional[float] = 20,
            support: Optional[float] = 20,
        ) -> dict:
            """Construct the dict for meraki function.

            Note all parameters in percent! Just like at www.leagueofgraphs.com
            """
            return {  # global playrate in percent * champion role appearance in %
                'TOP': playrate * top * 0.01,
                'JUNGLE': playrate * jungle * 0.01,
                'MIDDLE': playrate * mid * 0.01,
                'BOTTOM': playrate * bot * 0.01,
                'UTILITY': playrate * support * 0.01,
            }

        # Nilah (data was taken 03/Jan/23) - {id: the_dict}
        # https://www.leagueofgraphs.com/champions/stats/nilah/master
        manual_data = {895: construct_the_dict(playrate=2.8, top=0.4, jungle=0.0, mid=1.7, bot=97.4, support=0.4)}
        diff_dict = {x: construct_the_dict() for x in diff_list if x not in manual_data}
        return diff_dict | (manual_data | champion_roles)


champion_roles_cache = ChampionRolesCache()


async def get_all_champ_names() -> List[str]:
    """Get all champion names in League of Legends"""
    data = await champion.champion_keys_cache.data
    return list(data['name_by_id'].values())


async def icon_url_by_champ_id(champ_id: int) -> str:
    """Get champion icon url by their champ_id"""
    champ = await lol.champion.Champion(id=champ_id).get()
    return cdragon.abs_url(champ.square_path)


async def get_pyot_meraki_champ_diff_list(data_meraki: dict = None):
    data_pyot = await champion.champion_keys_cache.data
    data_meraki = data_meraki or await champion_roles_cache.data
    return set(data_pyot['id_by_name'].values()) - set(data_meraki.keys())


async def get_meraki_patch():
    _ = await champion_roles_cache.data  # just so it triggers updating the cache, if needed.
    return champion_roles_cache.meraki_patch


async def get_role_mini_list(all_players_champ_ids) -> List[int]:
    champion_roles = await champion_roles_cache.data
    role_mini_list = list(get_roles(champion_roles, all_players_champ_ids[:5]).values()) + list(
        get_roles(champion_roles, all_players_champ_ids[5:]).values()
    )
    return role_mini_list


async def utils_test_main():
    blue_team = [895, 200, 888, 238, 92]  # ['Nilah', 'BelVeth', 'Renata', '', 'Zed', 'Riven']
    red_team = [122, 69, 64, 201, 119]  # ['Darius', 'Cassiopeia', 'Lee Sin', 'Braum', 'Draven']

    sorted_champ_ids = await get_role_mini_list(blue_team + red_team)

    print([await champion.name_by_id(i) for i in sorted_champ_ids[:5]])
    print([await champion.name_by_id(i) for i in sorted_champ_ids[5:]])


if __name__ == '__main__':
    import asyncio
    from pyot.conf.utils import import_confs

    import_confs("utils.lol.pyotconf")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils_test_main())
