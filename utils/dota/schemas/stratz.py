"""Schemas representing data structure for my GraphQL calls with StratzClient."""
from __future__ import annotations

from typing import TypedDict

__all__ = (
    "FPCMatchesResponse",
    "HeroesResponse",
    "AbilitiesResponse",
    "ItemsResponse",
    "FacetsResponse",
)

# STRATZ: GET FPC MATCHES


class FPCMatchesResponse(TypedDict):
    data: Data


class Data(TypedDict):
    match: Match


class Match(TypedDict):
    statsDateTime: int
    players: list[Player]


class Player(TypedDict):
    isVictory: bool
    heroId: int
    variant: int
    kills: int
    deaths: int
    assists: int
    item0Id: int
    item1Id: int
    item2Id: int
    item3Id: int
    item4Id: int
    item5Id: int
    neutral0Id: int
    playbackData: PlaybackData | None
    stats: Stats


class PlaybackData(TypedDict):
    abilityLearnEvents: list[AbilityLearnEvent]
    purchaseEvents: list[PurchaseEvent]


class AbilityLearnEvent(TypedDict):
    abilityId: int


class PurchaseEvent(TypedDict):
    time: int
    itemId: int


class Stats(TypedDict):
    matchPlayerBuffEvent: list[BuffEvent]


class BuffEvent(TypedDict):
    itemId: int | None


# STRATZ: GET HEROES


class HeroesResponse(TypedDict):
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


class AbilitiesResponse(TypedDict):
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


class ItemsResponse(TypedDict):
    data: ItemData


class ItemData(TypedDict):
    constants: ItemConstants


class ItemConstants(TypedDict):
    items: list[Item]


class Item(TypedDict):
    id: int
    shortName: str


# STRATZ: GET FACETS


class FacetsResponse(TypedDict):
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
