from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from .. import const
from ..cache import CharacterCache, NewKeysCache
from . import constants

if TYPE_CHECKING:
    from bot import AluBot

    from .pulsefire_clients import StratzClient


__all__ = (
    "Abilities",
    "Facets",
    "Heroes",
    "Items",
)

# CDN_REACT = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
# idk, dota2.com uses the following cdn for hero icons:
CDN_REACT = "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/"


@dataclass
class Hero:
    id: int
    short_name: str
    """A short name for the hero, i.e. `"dark_willow"`.

    Somewhat used as a string hero identifier by Valve for such things as images/icons.
    Probably, the difference compared to stratz's "name" field is that
    the prefix "npc_dota_hero_" is removed in `short_name`.
    """
    display_name: str
    """A display name for the hero, i.e. `"Dark Willow"`"""
    talents: list[int]
    facets: list[int]

    @property
    def topbar_icon_url(self) -> str:
        """_summary_

        Examples
        -------
        "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/heroes/alchemist.png"
        """
        return f"{CDN_REACT}/heroes/{self.short_name}.png"

    @property
    def minimap_icon_url(self) -> str:
        """_summary_

        Examples
        -------
        "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/icons/hoodwink.png"
        """
        return f"{CDN_REACT}/heroes/icons/{self.short_name}.png"


class Heroes(NewKeysCache[Hero], CharacterCache):
    def __init__(self, bot: AluBot, stratz: StratzClient) -> None:
        super().__init__(bot)
        self.stratz: StratzClient = stratz

    @override
    async def fill_data(self) -> dict[int, Hero]:
        heroes = await self.stratz.get_heroes()

        return {
            hero["id"]: Hero(
                hero["id"],
                hero["shortName"],
                hero["displayName"],
                [talent["abilityId"] for talent in hero["talents"]],
                [facet["facetId"] for facet in hero["facets"]],
            )
            for hero in heroes["data"]["constants"]["heroes"]
        }

    async def by_id(self, hero_id: int) -> Hero:
        try:
            hero = await self.get_value(hero_id)
        except KeyError:
            raise  # TODO: ???
        else:
            return hero

    @override
    async def id_display_name_tuples(self) -> list[tuple[int, str]]:
        data = await self.get_cached_data()
        return [(hero_id, hero.display_name) for hero_id, hero in data.items()]

    @override
    async def id_display_name_dict(self) -> dict[int, str]:
        data = await self.get_cached_data()
        return {hero_id: hero.display_name for hero_id, hero in data.items()}

    @override
    async def display_name_by_id(self, hero_id: int) -> str:
        try:
            hero = await self.get_value(hero_id)
        except KeyError:
            raise  # TODO: ???
        else:
            return hero.display_name

    @override
    async def id_by_display_name(self, hero_display_name: str) -> int:
        data = await self.get_cached_data()
        try:
            hero = next(iter(hero for hero in data.values() if hero.display_name == hero_display_name))
        except Exception:
            raise  # TODO: ???
        else:
            return hero.id

    async def topbar_icon_by_id(self, hero_id: int) -> str:
        try:
            hero = await self.get_value(hero_id)
        except KeyError:
            raise  # TODO: ???
        else:
            return hero.topbar_icon_url


@dataclass
class Ability:
    """Class describing Dota 2 Hero Ability.

    Can be a talent from Talent trees.
    """

    id: int
    name: str
    display_name: str
    is_talent: bool

    @property
    def icon_url(self) -> str:
        return constants.TALENT_TREE_ICON if self.is_talent else f"{CDN_REACT}/abilities/{self.name}.png"


class Abilities(NewKeysCache[Ability]):
    def __init__(self, bot: AluBot, stratz: StratzClient) -> None:
        super().__init__(bot)
        self.stratz: StratzClient = stratz

    @override
    async def fill_data(self) -> dict[int, Ability]:
        abilities = await self.stratz.get_abilities()
        return {
            ability["id"]: Ability(
                ability["id"],
                ability["name"],
                ability["language"]["displayName"],
                ability["isTalent"],
            )
            for ability in abilities["data"]["constants"]["abilities"]
        }

    async def icon_by_id(self, ability_id: int) -> str:
        try:
            ability = await self.get_value(ability_id)
        except KeyError:
            return const.DotaAsset.AbilityUnknown
        else:
            return ability.icon_url

    async def display_name_by_id(self, ability_id: int) -> str:
        try:
            ability = await self.get_value(ability_id)
        except KeyError:
            return "Unknown Talent"
        else:
            return ability.display_name


@dataclass
class Item:
    id: int
    name: str

    @property
    def icon_url(self) -> str:
        if self.name.startswith("recipe_"):
            # all recipes fall back to a common recipe icon
            return f"{CDN_REACT}/items/recipe.png"
        else:
            return f"{CDN_REACT}/items/{self.name}.png"


@dataclass
class PseudoItem:
    id: int
    name: str
    icon_url: str


class Items(NewKeysCache[Item | PseudoItem]):
    def __init__(self, bot: AluBot, stratz: StratzClient) -> None:
        super().__init__(bot)
        self.stratz: StratzClient = stratz

    @override
    async def fill_data(self) -> dict[int, Item | PseudoItem]:
        items = await self.stratz.get_items()
        return {
            0: PseudoItem(
                0,
                "Empty Slot",
                const.DotaAsset.ItemEmpty,
            )
        } | {
            item["id"]: Item(
                item["id"],
                item["shortName"],
            )
            for item in items["data"]["constants"]["items"]
        }

    async def icon_by_id(self, item_id: int) -> str:
        """Get item's `icon_url` id by its `item_id`.

        Examples
        -------
        1076 -> "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/specialists_array.png"
        """
        try:
            item = await self.get_value(item_id)
        except KeyError:
            return const.DotaAsset.ItemUnknown
        else:
            return item.icon_url


@dataclass
class Facet:
    id: int
    display_name: str
    icon: str
    colour: str

    @property
    def icon_url(self) -> str:
        return f"{CDN_REACT}/icons/facets/{self.icon}.png"


class Facets(NewKeysCache[Facet]):
    def __init__(self, bot: AluBot, stratz: StratzClient) -> None:
        super().__init__(bot)
        self.stratz: StratzClient = stratz

    @override
    async def fill_data(self) -> dict[int, Facet]:
        facets = await self.stratz.get_facets()
        return {
            facet["id"]: Facet(
                facet["id"],
                facet["language"]["displayName"],
                facet["icon"],
                constants.FACET_COLOURS[f'{facet["color"]}{facet['gradientId']}'],
            )
            for facet in facets["data"]["constants"]["facets"]
        }

    async def by_id(self, facet_id: int) -> Facet:
        try:
            facet = await self.get_value(facet_id)
        except KeyError:
            raise  # TODO???
        else:
            return facet
