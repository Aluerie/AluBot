from typing import List

from ..cache import KeysCache
from ..const import DOTA

__all__ = (
    "id_by_name",
    "id_by_npcname",
    "icon_by_id",
    "name_by_id",
    "img_by_id",
)


class HeroKeysCache(KeysCache):
    # TODO: if type_checking: so we have typed dict and autocomplete on  hero_keys_cache.data['id_by_npcname']
    # instead of unknown unknown
    async def fill_data(self) -> dict:
        url = f"https://api.opendota.com/api/constants/heroes"
        hero_dict = await self.get_response_json(url=url)
        data = {
            "id_by_npcname": {"": 0},
            "id_by_name": {"Unknown": 0},
            "name_by_id": {0: "Unknown"},
            "img_by_id": {0: DOTA.HERO_DISCONNECT},
            "icon_by_id": {0: DOTA.HERO_DISCONNECT},
        }
        for _, hero in hero_dict.items():
            data["id_by_npcname"][hero["name"]] = hero["id"]
            data["id_by_name"][hero["localized_name"].lower()] = hero["id"]
            data["name_by_id"][hero["id"]] = hero["localized_name"]
            data["img_by_id"][hero["id"]] = f"https://cdn.cloudflare.steamstatic.com{hero['img']}"
            data["icon_by_id"][hero["id"]] = f"https://cdn.cloudflare.steamstatic.com{hero['icon']}"
        return data


hero_keys_cache = HeroKeysCache()


async def id_by_npcname(value: str) -> int:
    """Get hero id by npc_name.

    example: 'npc_dota_hero_antimage' -> 1
    """
    return await hero_keys_cache.get("id_by_npcname", value)


async def id_by_name(value: str) -> int:
    """Get hero id by localized to english name.

    Example: 'Anti-Mage' -> 1
    """
    return await hero_keys_cache.get("id_by_name", value.lower())


async def name_by_id(value: int) -> str:
    """Get hero id by name.

    Example: 1 -> 'Anti-Mage'
    """
    return await hero_keys_cache.get("name_by_id", value)


async def img_by_id(value: int) -> str:
    """Get hero top-bar image url id by id.

    Example: 1 -> 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/antimage.png?'
    """
    return await hero_keys_cache.get("img_by_id", value)


async def icon_by_id(value: int) -> str:
    """Get hero minimap icon url by id.

    Example: 1 -> 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/icons/antimage.png?'
    """
    return await hero_keys_cache.get("icon_by_id", value)


async def all_hero_names() -> List[str]:
    """Get all hero names in Dota 2"""
    data = await hero_keys_cache.get_data()
    hero_dict = data["name_by_id"]
    hero_dict.pop(0, None)
    return sorted(list(hero_dict.values()))


async def all_hero_ids() -> List[int]:
    """Get all hero ids in Dota 2"""
    data = await hero_keys_cache.get_data()
    hero_dict = data["name_by_id"]
    hero_dict.pop(0, None)
    return list(hero_dict.keys())
