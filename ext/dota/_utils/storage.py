from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict, override

import discord

from ....utils import const, fmt
from ....utils.fpc import Character, CharacterStorage, CharacterTransformer, GameDataStorage

if TYPE_CHECKING:
    from bot import AluInteraction

    from .schemas import stratz

    class GetHeroEmoteRow(TypedDict):
        id: int
        emote: str


__all__ = (
    "Abilities",
    "Facets",
    "Hero",
    "HeroTransformer",
    "Heroes",
    "Items",
    "PseudoHero",
)

# old CDN was "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
# idk, dota2.com uses the following cdn for hero icons:
CDN_REACT = "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/"


@dataclass(repr=False)
class Hero(Character):
    """Dota 2 Hero."""

    short_name: str
    """A short name for the hero, i.e. `"dark_willow"`.

    Somewhat used as a string hero identifier by Valve for such things as images/icons.
    Probably, the difference compared to stratz's "name" field is that
    the prefix "npc_dota_hero_" is removed in `short_name`.
    """
    talent_ids: list[int]
    """Ability IDs for hero talents.

    I think the list is ordered same as odota constants:
    7 6
    5 4
    3 2
    1 0
    # so if it's even - it's a right talent, if it's odd - left
    """
    facet_ids: list[int]
    """Facet IDs for the hero.

    Facet ID is a completely separate identifier from ability ID.
    This value is also different from "facet slot id" which is simply 0 1 2... index
    """

    @property
    def topbar_icon_url(self) -> str:
        """Hero icon for the in-game topbar with all heroes and score.

        Examples
        --------
        "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/heroes/alchemist.png"
        """
        return f"{CDN_REACT}/heroes/{self.short_name}.png"

    @property
    def minimap_icon_url(self) -> str:
        """Hero icon for the minimap. Somewhat represents small pixel art for the hero.

        Examples
        --------
        "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/icons/hoodwink.png"
        """
        return f"{CDN_REACT}/heroes/icons/{self.short_name}.png"


@dataclass(repr=False)
class PseudoHero(Character):
    """Dota 2 Pseudo Hero."""

    short_name: str

    topbar_icon_url: str
    minimap_icon_url: str | None = None

    talent_ids: list[int] = field(default_factory=list)
    facet_ids: list[int] = field(default_factory=list)


class Heroes(CharacterStorage[Hero, PseudoHero]):  # CharacterCache
    """Dota 2 Heroes."""

    @override
    async def fill_data(self) -> dict[int, Hero]:
        heroes = await self.bot.dota.stratz.get_heroes()

        query = "SELECT id, emote FROM dota_heroes_info"
        rows: list[GetHeroEmoteRow] = await self.bot.pool.fetch(query)
        hero_emotes = {row["id"]: row["emote"] for row in rows}

        return {
            hero["id"]: Hero(
                id=hero["id"],
                short_name=hero["shortName"],
                display_name=hero["displayName"],
                talent_ids=[talent["abilityId"] for talent in hero["talents"]],
                facet_ids=[facet["facetId"] for facet in hero["facets"]],
                # if I don't provide a ready-to-go emote -> assume the hero is new and thus give it a template emote
                emote=hero_emotes.get(hero["id"]) or await self.create_hero_emote(hero["id"], hero["shortName"]),
            )
            for hero in heroes["data"]["constants"]["heroes"]
        }

    @override
    @staticmethod
    def generate_unknown_object(hero_id: int) -> PseudoHero:
        return PseudoHero(
            id=hero_id,
            short_name="unknown_hero",
            display_name="Unknown",
            topbar_icon_url=const.DotaAsset.HeroTopbarUnknown,
            emote=const.NEW_HERO_EMOTE,
        )

    @override
    async def by_id(self, hero_id: int) -> Hero | PseudoHero:
        """Get Hero object by its ID."""
        # special cases
        if hero_id == 0:
            return PseudoHero(
                id=0,
                short_name="disconnected_or_unpicked",
                display_name="Disconnected/Unpicked",
                topbar_icon_url=const.DotaAsset.HeroTopbarDisconnectedUnpicked,
                emote="\N{BLACK QUESTION MARK ORNAMENT}",
            )
        return await super().by_id(hero_id)

    async def create_hero_emote(
        self,
        hero_id: int,
        hero_short_name: str,
    ) -> str:
        """Create a new discord emote for a Dota 2 hero."""
        try:
            return await self.create_character_emote_helper(
                character_id=hero_id,
                table="dota_heroes_info",
                emote_name=fmt.convert_camel_case_to_PascalCase(hero_short_name),
                emote_source_url=f"{CDN_REACT}/heroes/icons/{hero_short_name}.png",  # copy of `minimap_icon_url`
                guild_id=const.EmoteGuilds.DOTA[3],
            )
        except Exception as exc:  # noqa: BLE001
            desc = f"Something went wrong when creating hero emote for `id={hero_id}, name={hero_short_name}`."
            embed = discord.Embed(description=desc)
            await self.bot.exc_manager.register_error(exc, embed=embed)
            return const.NEW_HERO_EMOTE


class HeroTransformer(CharacterTransformer[Hero, PseudoHero]):
    @override
    def get_character_storage(self, interaction: AluInteraction) -> Heroes:
        return interaction.client.dota.heroes


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
        return const.TALENT_TREE_ICON if self.is_talent else f"{CDN_REACT}/abilities/{self.name}.png"

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.display_name}>"


@dataclass
class PseudoAbility:
    id: int
    name: str
    display_name: str
    is_talent: bool | None
    icon_url: str

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.display_name}>"


class Abilities(GameDataStorage[Ability, PseudoAbility]):
    @override
    async def fill_data(self) -> dict[int, Ability]:
        abilities = await self.bot.dota.stratz.get_abilities()

        # as of 12/October/2024 Stratz doesn't have full data on some Talent names (a lot of nulls)
        # so for now we fill the missing data with opendota
        odota_abilities = await self.bot.dota.opendota_constants.get_abilities()

        def get_display_name(ability: stratz.Ability) -> str:
            if ability["language"] and (display_name := ability["language"]["displayName"]):
                # can be `None`, especially for new abilities
                return display_name
            # else get the information from opendota
            opendota_ability = odota_abilities.get(ability["name"])
            if opendota_ability:
                return opendota_ability.get("dname", "unknown")
            return "Unknown"

        return {
            ability["id"]: Ability(
                ability["id"],
                ability["name"],
                get_display_name(ability),
                ability["isTalent"],
            )
            for ability in abilities["data"]["constants"]["abilities"]
        }

    @override
    @staticmethod
    def generate_unknown_object(ability_id: int) -> PseudoAbility:
        return PseudoAbility(
            id=ability_id,
            name="unknown_ability",
            display_name="Unknown",
            is_talent=None,
            icon_url=const.DotaAsset.AbilityUnknown,
        )


@dataclass
class Item:
    id: int
    short_name: str

    @property
    def icon_url(self) -> str:
        """Get item's `icon_url` id by its `item_id`.

        Examples
        --------
        <Item id=1076> -> "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/items/specialists_array.png"
        """
        if self.short_name.startswith("recipe_"):
            # all recipes fall back to a common recipe icon
            return f"{CDN_REACT}/items/recipe.png"
        return f"{CDN_REACT}/items/{self.short_name}.png"

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.short_name}>"


@dataclass
class PseudoItem:
    id: int
    short_name: str
    icon_url: str

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.short_name}>"


class Items(GameDataStorage[Item, PseudoItem]):
    @override
    async def fill_data(self) -> dict[int, Item]:
        items = await self.bot.dota.stratz.get_items()
        return {
            item["id"]: Item(
                item["id"],
                item["shortName"],
            )
            for item in items["data"]["constants"]["items"]
        }

    @override
    @staticmethod
    def generate_unknown_object(item_id: int) -> PseudoItem:
        return PseudoItem(
            id=item_id,
            short_name="unknown_item",
            icon_url=const.DotaAsset.ItemUnknown,
        )

    @override
    async def by_id(self, item_id: int) -> Item | PseudoItem:
        """Get Item by its ID."""
        # special case
        if item_id == 0:
            return PseudoItem(
                0,
                "Empty Slot",
                const.DotaAsset.ItemEmpty,
            )
        return await super().by_id(item_id)


@dataclass
class Facet:
    id: int
    display_name: str
    icon: str
    color: str

    @property
    def icon_url(self) -> str:
        """The icon url to the facet's image.

        Usually just some small logo-symbol.

        Examples
        --------
        "https://cdn.akamai.steamstatic.com/apps/dota2/images/dota_react/icons/facets/mana.png"
        """
        return f"{CDN_REACT}/icons/facets/{self.icon}.png"

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.display_name}>"


@dataclass
class PseudoFacet:
    id: int
    display_name: str
    icon: str
    color: str
    icon_url: str

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.display_name}>"


class Facets(GameDataStorage[Facet, PseudoFacet]):
    @override
    async def fill_data(self) -> dict[int, Facet]:
        facets = await self.bot.dota.stratz.get_facets()

        # as of 12/October/2024 Stratz doesn't have full data on Facets (a lot of nulls)
        # so for now we fill the missing data with opendota
        hero_abilities = await self.bot.dota.opendota_constants.get_hero_abilities()
        short_name_display_name_lookup: dict[str, str] = {
            facet["name"]: facet["title"] for hero in hero_abilities.values() for facet in hero["facets"]
        }

        return {
            facet["id"]: Facet(
                facet["id"],
                facet["language"]["displayName"]
                or short_name_display_name_lookup.get(facet["name"])
                or "Unknown Facet",
                facet["icon"],
                const.FACET_COLORS[f"{facet['color']}{facet['gradientId']}"],
            )
            for facet in facets["data"]["constants"]["facets"]
        }

    @override
    @staticmethod
    def generate_unknown_object(facet_id: int) -> PseudoFacet:
        return PseudoFacet(
            id=facet_id,
            display_name="Unknown",
            icon="question",
            color="#675CAE",
            icon_url=const.DotaAsset.FacetQuestion,
        )
