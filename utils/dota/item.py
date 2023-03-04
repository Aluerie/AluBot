from utils.cache import KeyCache
from .const import *

__all__ = ('iconurl_by_id', 'id_by_key')

BLACK_TILE = "https://i.imgur.com/TtOovu5.png"


class ItemKeyCache(KeyCache):
    async def fill_data(self) -> dict:
        item_dict = await self.get_resp_json(url=f'{ODOTA_API_URL}/constants/items')
        data = {'iconurl_by_id': {0: BLACK_TILE}, 'id_by_key': {}}  # black tile
        for key, item in item_dict.items():
            data['iconurl_by_id'][item['id']] = f"{STEAM_CDN_URL}{item['img']}"
            data['id_by_key'][key] = item['id']
        return data


item_keys_cache = ItemKeyCache()


async def iconurl_by_id(value: int) -> str:
    """Get item icon url id by item id.

    example: 2 ->
    'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/blades_of_attack_lg.png'
    """
    data = await item_keys_cache.data
    return data['iconurl_by_id'][value]


async def id_by_key(value: str) -> int:
    """Get item id by provided key.

    example: "infused_raindrop" -> 265
    """
    data = await item_keys_cache.data
    return data['id_by_key'][value]
