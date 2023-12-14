from ..cache import KeysCache
from ..const import DOTA

__all__ = (
    "icon_by_id",
    "id_by_key",
)

BLACK_TILE = "https://i.imgur.com/TtOovu5.png"


class ItemKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        item_dict = await self.get_response_json(url="https://api.opendota.com/api/constants/items")
        data = {"icon_by_id": {0: BLACK_TILE}, "id_by_key": {}}  # black tile
        for key, item in item_dict.items():
            data["icon_by_id"][item["id"]] = f"https://cdn.cloudflare.steamstatic.com{item['img']}"
            data["id_by_key"][key] = item["id"]
        return data


item_keys_cache = ItemKeysCache()


async def icon_by_id(value: int) -> str:
    """Get item icon url id by item id.

    example: 2 ->
    'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/blades_of_attack_lg.png'
    """
    return await item_keys_cache.get("icon_by_id", value)


async def id_by_key(value: str) -> int:
    """Get item id by provided key.

    example: "infused_raindrop" -> 265
    """
    return await item_keys_cache.get("id_by_key", value)
