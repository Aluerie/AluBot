from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, override

from .. import const
from ..cache import KeysCache

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from bot import AluBot

    class HeroFacet(TypedDict):
        title: str
        icon: str
        colour: str
        gradient_id: int

    class HeroKeysData(TypedDict):
        id_by_npcname: MutableMapping[str, int]
        npcname_by_id: MutableMapping[int, str]
        id_by_name: MutableMapping[str, int]
        name_by_id: MutableMapping[int, str]
        img_by_id: MutableMapping[int, str]
        icon_by_id: MutableMapping[int, str]
        ability_icon_by_ability_id: MutableMapping[int, str]
        talents_by_id: MutableMapping[int, list[tuple[int, str]]]
        facets_by_id: MutableMapping[int, list[HeroFacet]]

    class AbilityKeysData(TypedDict):
        icon_by_id: MutableMapping[int, str]


__all__ = ("CacheDota",)


class CacheDota:
    def __init__(self, bot: AluBot) -> None:
        self.hero = HeroKeysCache(bot)
        self.item = ItemKeysCache(bot)


class HeroKeysCache(KeysCache):
    CDN = "https://cdn.cloudflare.steamstatic.com"

    if TYPE_CHECKING:
        cached_data: HeroKeysData

    @override
    async def fill_data(self) -> HeroKeysData:
        hero_data = await self.bot.odota_constants.get_heroes()

        ability_ids = await self.bot.odota_constants.get_ability_ids()
        reverse_ability_ids = {v: int(k) for k, v in ability_ids.items()}
        abilities = await self.bot.odota_constants.get_abilities()
        hero_abilities = await self.bot.odota_constants.get_hero_abilities()

        # by_id or by_name means by hero_name/hero_id, might write full thing if it's too unclear.
        data: HeroKeysData = {
            "id_by_npcname": {"": 0},
            "npcname_by_id": {0: ""},
            "id_by_name": {"unknown": 0},
            "name_by_id": {0: "Unknown"},
            "img_by_id": {0: const.Dota.HERO_DISCONNECT},
            "icon_by_id": {0: const.Dota.HERO_DISCONNECT},
            "ability_icon_by_ability_id": {0: const.Dota.HERO_DISCONNECT, 730: const.Dota.ATTR_BONUS_ICON},
            "talents_by_id": {},
            "facets_by_id": {},
        }

        talent_id_by_name: dict[str, int] = {}
        facets_id_by_name: dict[str, int] = {}

        # ABILITIES
        for ability_id, ability_name in ability_ids.items():
            try_ability = abilities.get(ability_name, None)
            if try_ability:
                img_url = try_ability.get("img", None)
                if img_url:
                    data["ability_icon_by_ability_id"][int(ability_id)] = f"{self.CDN}{img_url}"

        for hero_ability in hero_abilities.values():
            # TALENTS
            for talent in hero_ability["talents"]:
                talent_name = talent["name"]
                ability_id = reverse_ability_ids.get(talent_name)
                if ability_id is None:
                    continue
                data["ability_icon_by_ability_id"][ability_id] = const.Dota.TALENT_TREE_ICON
                talent_id_by_name[talent_name] = ability_id

            # FACETS
            for facet in hero_ability["facets"]:
                facet_name = facet["name"]
                ability_id = reverse_ability_ids.get(facet_name)
                if ability_id is None:
                    continue
                facets_id_by_name[facet_name] = ability_id

        for hero in hero_data.values():
            data["id_by_npcname"][hero["name"]] = hero["id"]
            data["npcname_by_id"][hero["id"]] = hero["name"]
            data["id_by_name"][hero["localized_name"].lower()] = hero["id"]
            data["name_by_id"][hero["id"]] = hero["localized_name"]
            data["img_by_id"][hero["id"]] = f"{self.CDN}{hero['img']}"
            data["icon_by_id"][hero["id"]] = f"{self.CDN}{hero['icon']}"

            data["talents_by_id"][hero["id"]] = [
                # Unknown Talent :( because new patches sometimes introduce terms that opendota fails to figure out
                (talent_id_by_name[talent["name"]], abilities[talent["name"]].get("dname", "Unknown Talent Name"))
                for talent in hero_abilities[hero["name"]]["talents"]
            ]

            data["facets_by_id"][hero["id"]] = [
                {
                    "title": facet["title"],
                    "icon": f"{self.CDN}/apps/dota2/images/dota_react/icons/facets/{facet['icon']}.png",
                    "colour": facet["color"],
                    "gradient_id": facet["gradient_id"],
                }
                for facet in hero_abilities[hero["name"]]["facets"]
            ]

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

    async def alias_by_id(self, hero_id: int) -> str:
        """Get alias by hero id. Alias is just a cut off npcname."""
        alias = await self.get_value("npcname_by_id", hero_id)
        return alias[14:]  # remove gibberish `npc_dota_hero_` prefix.

    async def npcname_by_id(self, hero_id: int) -> str:
        """Get npc_dota_hero_name by hero id."""
        return await self.get_value("npcname_by_id", hero_id)

    async def id_by_name(self, hero_name: str) -> int:
        """Get hero id by localized English name."""
        return await self.get_value("id_by_name", hero_name.lower())

    async def name_by_id(self, hero_id: int) -> str:
        """Get hero id by name."""
        return await self.get_value("name_by_id", hero_id)

    async def img_by_id(self, hero_id: int) -> str:
        """Get hero top-bar image url id by id."""
        return await self.get_value("img_by_id", hero_id)

    async def ability_icon_by_ability_id(self, ability_id: int) -> str:
        """Get hero minimap icon url by id."""
        return await self.get_value("ability_icon_by_ability_id", ability_id)

    async def icon_by_id(self, ability_id: int) -> str:
        """Get ability icon url by id."""
        icon_url: str | None = await self.get_value_or_none("icon_by_id", ability_id)
        if icon_url is None:
            return "https://i.imgur.com/9BQ4VxL.png"  # icon for unknown (new?) hero
        else:
            return icon_url

    async def talents_by_id(self, hero_id: int) -> list[tuple[int, str]]:
        """Get ability name by its id.

        Currently only return data on talents and None for everything else,
        bcs we do not need anything else for now
        """
        return await self.get_value("talents_by_id", hero_id)

    async def facets_by_id(self, hero_id: int, facet_number: int) -> HeroFacet:
        """Get hero facet by hero_id and ordinal number."""
        facet_list: list[HeroFacet] = await self.get_value("facets_by_id", hero_id)
        try:
            return facet_list[facet_number - 1]  # Stratz start facet numbering from 1
        except IndexError:
            # this means opendota has something borked so let's return some template Unknown for now
            return {
                "title": "Unknown Facet",
                "colour": "gray",
                "gradient_id": 1,
                "icon": f"{self.CDN}/apps/dota2/images/dota_react/icons/facets/cooldown.png",
            }


class ItemKeysCache(KeysCache):
    # ITEMS_URL = "https://api.opendota.com/api/constants/items"
    ITEMS_URL = "https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json"

    @override
    async def fill_data(self) -> dict:
        item_dict = await self.get_response_json(url=self.ITEMS_URL)
        data = {
            "icon_by_id": {0: const.Dota.EMPTY_ITEM_TILE},
            "id_by_key": {},
            "name_by_id": {0: "Empty Slot"},
            "id_by_name": {},
        }
        for key, item in item_dict.items():
            data["icon_by_id"][item["id"]] = f"https://cdn.cloudflare.steamstatic.com{item['img']}"
            data["id_by_key"][key] = item["id"]
            data["name_by_id"][item["id"]] = item.get("dname", key)

        data["id_by_name"] = {v.lower(): k for k, v in data["name_by_id"].items()}
        return data

    # Example of item values to be transposed into each other
    # id: 265
    # key: "infused_raindrop"
    # name: "Infused Raindrops"
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

    async def name_by_id(self, item_id: int) -> str:
        """Get item display name by provided item_id."""
        return await self.get_value("name_by_id", item_id)

    async def id_by_name(self, item_name: str) -> int:
        """Get item id by provided item_name."""
        return await self.get_value("id_by_name", item_name.lower())
