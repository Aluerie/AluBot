from datetime import datetime, timedelta, timezone
from pyot.utils.functools import async_property

import asyncio
from aiohttp import ClientSession

def dbuff_match_url(match_id: int, md: bool = True) -> str:
    """Dotabuff.com link for the match with `match_id`"""
    url = f'https://www.dotabuff.com/matches/{match_id}'
    return f'[Dbuff]({url})' if md else url


def odota_match_url(match_id: int, md: bool = True) -> str:
    """Opendota.com link for the match with `match_id`"""
    url = f'https://www.opendota.com/matches/{match_id}'
    return f'[ODota]({url})' if md else url


def stratz_match_url(match_id: int, md: bool = True) -> str:
    """Stratz.com link for `match_id`"""
    url = f'https://www.stratz.com/matches/{match_id}'
    return f'[Stratz]({url})' if md else url


def stats_sites_match_urls(match_id: int, md: bool = True) -> str:
    return \
        f'/{dbuff_match_url(match_id, md)}' \
        f'/{odota_match_url(match_id, md)}' \
        f'/{stratz_match_url(match_id, md)}'


STEAM_CDN_URL = 'https://cdn.cloudflare.steamstatic.com'
ODOTA_API_URL = 'https://api.opendota.com/api'


async def get_resp_json(*, url):
    async with ClientSession() as session:
        resp = await session.request("GET", url)
        if not (resp and resp.status == 200):
            raise RuntimeError(f'Dota constants failed with status {resp.status}')
            # return self.cached_data
        return await resp.json()  # abilities


class HeroKeyCache:

    def __init__(self) -> None:
        self.cached_data = {
            "id_by_npcname": {},
            "id_by_name": {},
            "name_by_id": {},
            "iconurl_by_id": {},
        }
        self.lock = asyncio.Lock()
        self.last_updated = datetime.now(timezone.utc) - timedelta(days=1)

    @async_property
    async def data(self):
        if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
            return self.cached_data
        async with self.lock:
            if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
                return self.cached_data
            try:
                dic = await get_resp_json(url=f'{ODOTA_API_URL}/constants/heroes')
            except RuntimeError as exc:
                if any(self.cached_data.values()):
                    return self.cached_data
                else:
                    raise exc
            data = {
                'id_by_npcname': {'': 0},
                'id_by_name': {'bot_game': 0},
                'name_by_id': {0: 'bot_game'},
                'iconurl_by_id':
                    {0: "https://static.wikia.nocookie.net/dota2_gamepedia/images/3/3d/Greater_Mango_icon.png"},
            }
            for hero in dic:
                data['id_by_npcname'][dic[hero]['name']] = dic[hero]['id']
                data['id_by_name'][dic[hero]['localized_name'].lower()] = dic[hero]['id']
                data['name_by_id'][dic[hero]['id']] = dic[hero]['localized_name']
                data['iconurl_by_id'][dic[hero]['id']] = f"{STEAM_CDN_URL}{dic[hero]['img']}"
            self.cached_data = data
            self.last_updated = datetime.now(timezone.utc)
        return self.cached_data


hero_keys_cache = HeroKeyCache()


async def id_by_npcname(value: str) -> int:
    """ Get hero id by npcname ;
    example: 'npc_dota_hero_antimage' -> 1 """
    data = await hero_keys_cache.data
    return data['id_by_npcname'][value]


async def id_by_name(value: str) -> int:
    """ Get hero id by localized to english name ;
    example: 'Anti-Mage' -> 1 """
    data = await hero_keys_cache.data
    return data['id_by_name'][value.lower()]


async def name_by_id(value: int) -> str:
    """ Get hero id by name ;
    example: 1 -> 'Anti-Mage' """
    data = await hero_keys_cache.data
    return data['name_by_id'][value]


async def iconurl_by_id(value: int) -> str:
    """ Get hero icon utl id by id ;
    example: 1 -> 'https://cdn.cloudflare.steamstatic.com//apps/dota2/images/dota_react/heroes/antimage.png?' """
    data = await hero_keys_cache.data
    return data['iconurl_by_id'][value]


class ItemKeyCache:

    def __init__(self) -> None:
        self.cached_data = {
            "iconurl_by_id": {},
            "id_by_key": {}
        }
        self.lock = asyncio.Lock()
        self.last_updated = datetime.now(timezone.utc) - timedelta(days=1)

    @async_property
    async def data(self):
        if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
            return self.cached_data
        async with self.lock:
            if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
                return self.cached_data
            url = 'https://api.opendota.com/api/constants/items'
            async with ClientSession() as session:
                resp = await session.request("GET", url)
                if not (resp and resp.status == 200):
                    raise RuntimeError(f'Dota constants failed with status {resp.status}')
                    # return self.cached_data
                dic = await resp.json()
            data = {
                'iconurl_by_id':
                    {0: "https://i.imgur.com/TtOovu5.png"},  # black tile
                'id_by_key':
                    {}
            }
            for k, v in dic.items():
                data['iconurl_by_id'][v['id']] = f"https://cdn.cloudflare.steamstatic.com/{v['img']}"
                data['id_by_key'][k] = v['id']
            self.cached_data = data
            self.last_updated = datetime.now(timezone.utc)
        return self.cached_data


item_keys_cache = ItemKeyCache()


async def itemurl_by_id(value: int) -> str:
    """
    Get item icon utl id by id.

    example: 2 ->
    'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/blades_of_attack_lg.png?t=1593393829403'
    """
    data = await item_keys_cache.data
    return data['iconurl_by_id'][value]


async def item_id_by_key(value: str) -> int:
    """
    Get item id by provided key.

    example: "infused_raindrop" -> 265
    """
    data = await item_keys_cache.data
    return data['id_by_key'][value]


class AbilityKeyCache:

    def __init__(self) -> None:
        self.cached_data = {
            "iconurl_by_id": {},
            "dname_by_id": {},
        }
        self.lock = asyncio.Lock()
        self.last_updated = datetime.now(timezone.utc) - timedelta(days=1)

    @async_property
    async def data(self):
        if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
            return self.cached_data
        async with self.lock:
            if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
                return self.cached_data

            dict_ids = await get_resp_json(url='https://api.opendota.com/api/constants/ability_ids')
            dict_abs = await get_resp_json(url='https://api.opendota.com/api/constants/abilities')
            dict_hab = await get_resp_json(url='https://api.opendota.com/api/constants/hero_abilities')

            revert_dict_ids = {v: int(k) for k, v in dict_ids.items()}

            data = {
                'iconurl_by_id': {
                        0: "https://static.wikia.nocookie.net/dota2_gamepedia/images/3/3d/Greater_Mango_icon.png",
                        730: "https://static.wikia.nocookie.net/dota2_gamepedia/images/e/e2/Attribute_Bonus_icon.png"
                    },
                "dname_by_id":
                    {},
            }
            for k, v in dict_hab.items():
                for npc_name in v['abilities']:
                    ability_id = revert_dict_ids[npc_name]
                    data['iconurl_by_id'][ability_id] = f"{STEAM_CDN_URL}{dict_abs[npc_name].get('img', None)}"
                    data['dname_by_id'][ability_id] = None
                for talent in v['talents']:
                    npc_name = talent['name']
                    ability_id = revert_dict_ids[npc_name]
                    data['iconurl_by_id'][ability_id] = "https://liquipedia.net/commons/images/5/54/Talents.png"
                    data['dname_by_id'][ability_id] = dict_abs[npc_name].get('dname', None)

            self.cached_data = data
            self.last_updated = datetime.now(timezone.utc)
        return self.cached_data


ability_keys_cache = AbilityKeyCache()


async def ability_iconurl_by_id(value: int) -> str:
    """

    """
    data = await ability_keys_cache.data
    return data['iconurl_by_id'][value]


async def ability_dname_by_id(value: int) -> str:
    """

    """
    data = await ability_keys_cache.data
    return data['dname_by_id'][value]

lazy_aghs_bless_url = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/ultimate_scepter_2.png"
lazy_aghs_shard_url = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/aghanims_shard.png"


async def test_main():
    m_id = 6678205280
    url = f"https://api.opendota.com/api/matches/{m_id}"
    session = ClientSession()
    async with session.get(url) as resp:
        dic = await resp.json()
        arr = dic['players'][4]['ability_upgrades_arr']
        for i in arr:
            if i is not None:
                print(i, await ability_dname_by_id(i))
    await session.close()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_main())
    #  loop.close()