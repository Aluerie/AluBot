"""
The MIT License (MIT)

"""
from .const import *
from .cache import KeyCache

__all__ = (
    # 'hero_keys_cache', # maybe
    'id_by_name',
    'id_by_npcname',
    'iconurl_by_id',
    'name_by_id',
)


class HeroKeyCache(KeyCache):

    async def fill_data(self) -> dict:
        url = f'{ODOTA_API_URL}/constants/heroes'
        hero_dict = await self.get_resp_json(url=url)
        data = {
            'id_by_npcname': {'': 0},
            'id_by_name': {'bot_game': 0},
            'name_by_id': {0: 'bot_game'},
            'iconurl_by_id': {0: MANGO_ICON},
        }
        for id_, hero in hero_dict.items():
            data['id_by_npcname'][hero['name']] = hero['id']
            data['id_by_name'][hero['localized_name'].lower()] = hero['id']
            data['name_by_id'][hero['id']] = hero['localized_name']
            data['iconurl_by_id'][hero['id']] = f"{STEAM_CDN_URL}{hero['img']}"
        return data


hero_keys_cache = HeroKeyCache()


async def id_by_npcname(value: str) -> int:
    """
    Get hero id by npc_name.

    example: 'npc_dota_hero_antimage' -> 1
    """
    data = await hero_keys_cache.data
    return data['id_by_npcname'][value]


async def id_by_name(value: str) -> int:
    """
    Get hero id by localized to english name.

    Example: 'Anti-Mage' -> 1
    """
    data = await hero_keys_cache.data
    return data['id_by_name'][value.lower()]


async def name_by_id(value: int) -> str:
    """
    Get hero id by name.

    Example: 1 -> 'Anti-Mage'
    """
    data = await hero_keys_cache.data
    return data['name_by_id'][value]


async def iconurl_by_id(value: int) -> str:
    """
    Get hero icon utl id by id.

    Example: 1 -> 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/antimage.png?'
    """
    data = await hero_keys_cache.data
    return data['iconurl_by_id'][value]
