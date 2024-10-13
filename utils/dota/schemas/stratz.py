from __future__ import annotations

from typing import TypedDict

__all__ = (
    "GetHeroesResponse",
    "GetAbilitiesResponse",
    "GetItemsResponse",
    "GetFacetsResponse",
)

# STRATZ: GET HEROES


class GetHeroesResponse(TypedDict):
    """Constants data for Dota 2 Heroes from Stratz GraphQL API.

    Information.
    """

    data: HeroData


class HeroData(TypedDict):
    constants: HeroConstants


class HeroConstants(TypedDict):
    heroes: list[Hero]


class Hero(TypedDict):
    id: int
    shortName: str
    displayName: str
    abilities: list[HeroAbility]
    talents: list[HeroTalent]
    facets: list[HeroFacet]


class HeroAbility(TypedDict):
    id: int
    name: str


class HeroTalent(TypedDict):
    abilityId: int


class HeroFacet(TypedDict):
    facetId: int


# STRATZ: GET ABILITIES


class GetAbilitiesResponse(TypedDict):
    data: AbilityData


class AbilityData(TypedDict):
    constants: AbilityConstants


class AbilityConstants(TypedDict):
    abilities: list[Ability]


class Ability(TypedDict):
    id: int
    name: str
    language: AbilityLanguage
    isTalent: bool


class AbilityLanguage(TypedDict):
    displayName: str


# STRATZ: GET ITEMS


class GetItemsResponse(TypedDict):
    data: ItemData


class ItemData(TypedDict):
    constants: ItemConstants


class ItemConstants(TypedDict):
    items: list[Item]


class Item(TypedDict):
    id: int
    shortName: str


# STRATZ: GET FACETS


class GetFacetsResponse(TypedDict):
    data: FacetData


class FacetData(TypedDict):
    constants: FacetConstants


class FacetConstants(TypedDict):
    facets: list[Facet]


class Facet(TypedDict):
    id: int
    name: str
    color: str
    icon: str
    language: FacetLanguage
    gradientId: int


class FacetLanguage(TypedDict):
    displayName: str
