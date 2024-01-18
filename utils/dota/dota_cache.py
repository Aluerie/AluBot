from __future__ import annotations

from typing import TYPE_CHECKING, MutableMapping, TypedDict

from .. import const
from ..cache import KeysCache

if TYPE_CHECKING:
    from bot import AluBot

    class HeroKeysData(TypedDict):
        id_by_npcname: MutableMapping[str, int]
        id_by_name: MutableMapping[str, int]
        name_by_id: MutableMapping[int, str]
        img_by_id: MutableMapping[int, str]
        icon_by_id: MutableMapping[int, str]


__all__ = ("DotaCache",)


class DotaCache:
    def __init__(self, bot: AluBot) -> None:
        self.hero = HeroKeysCache(bot)
        self.ability = AbilityKeyCache(bot)
        self.item = ItemKeysCache(bot)


class HeroKeysCache(KeysCache):
    if TYPE_CHECKING:
        cached_data: HeroKeysData

    async def fill_data(self) -> HeroKeysData:
        # url = f"https://api.opendota.com/api/constants/heroes"
        url = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/heroes.json"
        hero_dict = await self.get_response_json(url=url)
        data: HeroKeysData = {
            "id_by_npcname": {"": 0},
            "id_by_name": {"Unknown": 0},
            "name_by_id": {0: "Unknown"},
            "img_by_id": {0: const.DOTA.HERO_DISCONNECT},
            "icon_by_id": {0: const.DOTA.HERO_DISCONNECT},
        }
        for _, hero in hero_dict.items():
            data["id_by_npcname"][hero["name"]] = hero["id"]
            data["id_by_name"][hero["localized_name"].lower()] = hero["id"]
            data["name_by_id"][hero["id"]] = hero["localized_name"]
            data["img_by_id"][hero["id"]] = f"https://cdn.cloudflare.steamstatic.com{hero['img']}"
            data["icon_by_id"][hero["id"]] = f"https://cdn.cloudflare.steamstatic.com{hero['icon']}"
        return data

    # Example of hero values to be transposed into each other
    # id: 1
    # name: "Anti-Mage" (lower_name in cache "id_by_name": "anti-mage")
    # npcname: "npc_dota_hero_antimage"
    # img: 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/antimage.png?'
    # ^^^ (referencing top bar image)
    # icon: https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/icons/antimage.png?'
    # ^^^ (referencing mini map icon)

    async def id_by_npcname(self, npcname: str) -> int:
        """Get hero id by npc_name."""
        return await self.get_value("id_by_npcname", npcname)

    async def id_by_name(self, hero_name: str) -> int:
        """Get hero id by localized English name."""
        return await self.get_value("id_by_name", hero_name.lower())

    async def name_by_id(self, hero_id: int) -> str:
        """Get hero id by name."""
        return await self.get_value("name_by_id", hero_id)

    async def img_by_id(self, hero_id: int) -> str:
        """Get hero top-bar image url id by id."""
        return await self.get_value("img_by_id", hero_id)

    async def icon_by_id(self, hero_id: int) -> str:
        """Get hero minimap icon url by id."""
        return await self.get_value("icon_by_id", hero_id)


class AbilityKeyCache(KeysCache):
    TALENT_ICON = "https://liquipedia.net/commons/images/5/54/Talents.png"

    # ABILITY_IDS_URL = "https://api.opendota.com/api/constants/ability_ids"
    ABILITY_IDS_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/ability_ids.json"
    # ABILITIES_URL = "https://api.opendota.com/api/constants/abilities"
    ABILITIES_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/abilities.json"
    # HERO_ABILITIES_URL = "https://api.opendota.com/api/constants/hero_abilities"
    HERO_ABILITIES_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/hero_abilities.json"

    async def fill_data(self) -> dict:
        ability_ids = await self.get_response_json(self.ABILITY_IDS_URL)
        reverse_ability_ids = {v: int(k) for k, v in ability_ids.items()}
        abilities = await self.get_response_json(self.ABILITIES_URL)
        hero_abilities = await self.get_response_json(self.HERO_ABILITIES_URL)

        data = {
            "icon_by_id": {0: const.DOTA.HERO_DISCONNECT, 730: const.DOTA.ATTR_BONUS_ICON},
            "talent_by_id": {730: None},
        }
        for hero_ability in hero_abilities.values():
            # fill ability icons related data
            for ability_name in hero_ability["abilities"]:
                ability_id = reverse_ability_ids[ability_name]

                img_url = abilities[ability_name].get("img", None)
                if img_url:
                    data["icon_by_id"][ability_id] = f"https://cdn.cloudflare.steamstatic.com{img_url}"
                else:
                    # todo: check if this ever proc
                    data["icon_by_id"][ability_id] = const.DOTA.HERO_DISCONNECT

            for talent in hero_ability["talents"]:
                talent_name = talent["name"]
                ability_id = reverse_ability_ids.get(talent_name, None)
                if ability_id is None:
                    continue
                data["icon_by_id"][ability_id] = self.TALENT_ICON
                data["talent_by_id"][ability_id] = abilities[talent_name].get("dname", "Unknown Talent Text")
        return data

    async def icon_by_id(self, ability_id: int) -> str:
        """Get ability icon url by id"""
        return await self.get_value("icon_by_id", ability_id)

    async def talent_by_id(self, talent_id: int) -> str:
        """Get ability name by its id

        Currently only return data on talents and None for everything else,
        bcs we do not need anything else for now
        """
        return await self.get_value_or_none("talent_by_id", talent_id)


class ItemKeysCache(KeysCache):
    # ITEMS_URL = "https://api.opendota.com/api/constants/items"
    ITEMS_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"

    async def fill_data(self) -> dict:
        item_dict = await self.get_response_json(url=self.ITEMS_URL)
        data = {
            "icon_by_id": {0: const.DOTA.EMPTY_ITEM_TILE},
            "id_by_key": {},
        }
        for key, item in item_dict.items():
            data["icon_by_id"][item["id"]] = f"https://cdn.cloudflare.steamstatic.com{item['img']}"
            data["id_by_key"][key] = item["id"]
        return data

    # Example of item values to be transposed into each other
    # id: 265
    # key: "infused_raindrop"
    # icon: "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/infused_raindrop_lg.png"

    async def icon_by_id(self, item_id: int) -> str:
        """Get item icon url id by item_id.

        example: 2 ->
        'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/blades_of_attack_lg.png'
        """
        return await self.get_value("icon_by_id", item_id)

    async def id_by_key(self, item_key: str) -> int:
        """Get item id by provided item_key."""
        return await self.get_value("id_by_key", item_key)
