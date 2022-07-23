from datetime import datetime, timedelta, timezone
from pyot.utils.functools import async_property

import asyncio
from aiohttp import ClientSession


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
            url = 'https://api.opendota.com/api/constants/heroes'
            async with ClientSession() as session:
                resp = await session.request("GET", url)
                if not (resp and resp.status == 200):
                    raise RuntimeError(f'Dota constants failed with status {resp.status}')
                    # return self.cached_data
                dic = await resp.json()
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
                data['iconurl_by_id'][dic[hero]['id']] = f"https://cdn.cloudflare.steamstatic.com{dic[hero]['img']}"
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
                    {0: "https://static.wikia.nocookie.net/dota2_gamepedia/images/3/3d/Greater_Mango_icon.png"},
            }
            for k, v in dic.items():
                data['iconurl_by_id'][v['id']] = f"https://cdn.cloudflare.steamstatic.com/{v['img']}"
            self.cached_data = data
            self.last_updated = datetime.now(timezone.utc)
        return self.cached_data


item_keys_cache = ItemKeyCache()


async def itemurl_by_id(value: int) -> str:
    """
    Get hero icon utl id by id.

    example: 2 ->
    'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/blades_of_attack_lg.png?t=1593393829403'
    """
    data = await item_keys_cache.data
    return data['iconurl_by_id'][value]
