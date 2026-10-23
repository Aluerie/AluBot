from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

__all__ = (
    "GetAbilitiesResponse",
    "GetAbilityIDsResponse",
    "GetHeroAbilitiesResponse",
    "GetHeroesResponse",
    "GetItemsResponse",
)


# GET HEROES


type GetHeroesResponse = dict[str, Hero]


class Hero(TypedDict):
    id: int
    name: str
    primary_attr: str
    attack_type: str
    roles: list[str]
    img: str
    icon: str
    base_health: int
    base_health_regen: float
    base_mana: int
    base_mana_regen: int
    base_armor: int
    base_mr: int
    base_attack_min: int
    base_attack_max: int
    base_str: int
    base_agi: int
    base_int: int
    str_gain: float
    agi_gain: float
    int_gain: float
    attack_range: int
    projectile_speed: int
    attack_rate: float
    base_attack_time: int
    attack_point: float
    move_speed: int
    turn_rate: float | None
    cm_enabled: bool
    legs: int | None
    day_vision: int
    night_vision: int
    localized_name: str


# GET ABILITY IDS


type GetAbilityIDsResponse = dict[str, str]


# GET ABILITIES


type GetAbilitiesResponse = dict[str, Ability | Talent]


class Ability(TypedDict):
    dname: str
    behavior: list[str]
    dmg_type: str
    bkbpierce: str
    target_team: str
    target_type: list[str]
    desc: str
    attrib: list[AbilityAttrib]
    lore: str
    mc: list[str]
    cd: list[str]
    img: str


class Talent(TypedDict):
    dname: str


class AbilityAttrib(TypedDict):
    key: str
    header: str
    value: str
    generated: NotRequired[bool]


#  GET HERO ABILITIESe


type GetHeroAbilitiesResponse = dict[str, HeroAbilities]


class HeroAbilities(TypedDict):
    abilities: list[str]
    talents: list[HeroTalent]
    """Hero Talents

    Note that talents are ordered like this (it's exactly list of length 8):
    # 7 6
    # 5 4
    # 3 2
    # 1 0
    # so if it's even - it's a right talent, if it's odd - left
    """
    facets: list[HeroFacet]


class HeroTalent(TypedDict):
    name: str
    level: int


class HeroFacet(TypedDict):
    name: str
    icon: str
    color: str
    title: str
    gradient_id: int
    description: str


# GET ITEMS

type GetItemsResponse = dict[str, Item]


class Item(TypedDict):
    hint: list[str]
    id: int
    img: str
    dname: str
    qual: str
    cost: int
    notes: str
    attrib: list[ItemAttrib]
    mc: Literal[False] | int
    cd: float
    lore: str
    components: list[str]
    created: bool
    charges: bool


class ItemAttrib(TypedDict):
    key: str
    header: str
    value: str
    generated: NotRequired[bool]
