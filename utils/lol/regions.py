"""
Glossary:
* platform 
    RiotGames routing platform names with numbers like `NA1`.
* continent 
    RiotGames routing continent names like `AMERICAS`.
* region 
    Garbage term, because Riot API uses it as both platform and region.
    So in pulsefire riot api client calls we use both continent and platform for `region=` keyword argument.
* server 
    Normal human-readable server abbreviations like 'NA'. 
    Name does not exist in riot api calls and only used for display purposes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Callable, Generic, Literal, Mapping, Self, TypeVar

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from .. import AluContext

__all__ = (
    "LiteralPlatform",
    "Platform",
    "PlatformConverter",
)

T_co = TypeVar("T_co", covariant=True)
TT = TypeVar("TT", bound="type[Any]")


class classproperty(Generic[TT, T_co]):
    def __init__(self, func: Callable[[TT], T_co]):
        self.__func__ = func

    def __get__(self, instance: Any, type: TT) -> T_co:
        return self.__func__(type)


LiteralPlatform = Literal[
    "BR1", "EUN1", "EUW1", "JP1", "KR", "LA1", "LA2", "NA1", "OC1", "PH2", "RU", "SG2", "TH2", "TR1", "TW2", "VN2"
]


# fmt: off
class Platform(StrEnum):
    Brazil              = "BR1"
    EuropeNordicAndEast = "EUN1"
    EuropeWest          = "EUW1"
    Japan               = "JP1"
    RepublicOfKorea     = "KR"
    LatinAmericaNorth   = "LA1"
    LatinAmericaSouth   = "LA2"
    NorthAmerica        = "NA1"
    Oceania             = "OC1"
    Philippines         = "PH2"
    Russia              = "RU"
    Singapore           = "SG2"
    Thailand            = "TH2" 
    Turkey              = "TR1"
    Taiwan              = "TW2"
    Vietnam             = "VN2"
    # PublicBetaEnvironment = "PBE" # no, we will not support it.

    @classproperty
    def DISPLAY_NAMES(cls: type[Self]) -> Mapping[Platform, str]:  # type: ignore
        return {
            cls.Brazil             : "BR - Brazil",
            cls.EuropeNordicAndEast: "EUNE - Europe Nordic & East",
            cls.EuropeWest         : "EUW - Europe West",
            cls.Japan              : "JP - Japan",
            cls.RepublicOfKorea    : "KR - Republic of Korea",
            cls.LatinAmericaNorth  : "LAN - Latin America North",
            cls.LatinAmericaSouth  : "LAS - Latin America South",
            cls.NorthAmerica       : "NA - North America",
            cls.Oceania            : "OCE - Oceania",
            cls.Philippines        : "PH - Philippines",
            cls.Russia             : "RU - Russia",
            cls.Singapore          : "SG - Singapore, Malaysia, & Indonesia",
            cls.Thailand           : "TH - Thailand",
            cls.Turkey             : "TR - Turkey",
            cls.Taiwan             : "TW - Taiwan, Hong Kong, and Macao", 
            cls.Vietnam            : "VN - Vietnam",
        }

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAMES[self]

    @classproperty
    def CONTINENTS(cls: type[Self]) -> Mapping[Platform, str]:  # type: ignore
        return {
            cls.Brazil             : "AMERICAS",
            cls.EuropeNordicAndEast: "EUROPE",
            cls.EuropeWest         : "EUROPE",
            cls.Japan              : "ASIA",
            cls.RepublicOfKorea    : "ASIA",
            cls.LatinAmericaNorth  : "AMERICAS",
            cls.LatinAmericaSouth  : "AMERICAS",
            cls.NorthAmerica       : "AMERICAS",
            cls.Oceania            : "ASIA",
            cls.Philippines        : "ASIA",
            cls.Russia             : "EUROPE",
            cls.Singapore          : "ASIA",
            cls.Thailand           : "ASIA",
            cls.Turkey             : "EUROPE",
            cls.Taiwan             : "ASIA",
            cls.Vietnam            : "ASIA",
        }

    @property
    def continent(self):
        return self.CONTINENTS[self]
    
    @classproperty
    def OPGG_NAMES(cls: type[Self]) -> Mapping[Platform, str]:  # type: ignore
        return {
            cls.Brazil             : "BR",
            cls.EuropeNordicAndEast: "EUNE",
            cls.EuropeWest         : "EUW",
            cls.Japan              : "JP",
            cls.RepublicOfKorea    : "KR",
            cls.LatinAmericaNorth  : "LAN",
            cls.LatinAmericaSouth  : "LAS",
            cls.NorthAmerica       : "NA",
            cls.Oceania            : "OCE",
            cls.Philippines        : "PH",
            cls.Russia             : "RU",
            cls.Singapore          : "SG",
            cls.Thailand           : "TH",
            cls.Turkey             : "TR",
            cls.Taiwan             : "TW",
            cls.Vietnam            : "VN",
        }

    @property
    def opgg_name(self):
        return self.OPGG_NAMES[self]


# fmt: on


class PlatformConverter(commands.Converter, app_commands.Transformer):
    """PlatformConverter for both prefix and slash commands.

    for prefix commands - it accepts OPGG_NAMES - meaning values such as NA, euw, las, oce, etc.
    for slash commands - it offers `choices` with "display_name: platform" mapping.

    Both in the end return Platform type.
    """

    async def convert(self, _ctx: AluContext, argument: str) -> Platform:
        for platform, opgg_name in Platform.OPGG_NAMES.items():
            if argument.upper() == opgg_name:
                return platform
        else:
            raise commands.BadArgument(
                f"Couldn't find any servers like that `{argument!r}`\n"
                + f"The list of League of Legends servers is {[v.upper() for v in Platform.OPGG_NAMES.values()]}"
            )

    async def transform(self, interaction: discord.Interaction[discord.Client], value: str) -> Platform:
        # since we have choices hard-coded it will be of Platform type-string
        # PS. app_commands.Transformer won't run without subclassed `transform`
        return Platform(value)

    @property
    def choices(self):
        return [app_commands.Choice(name=name, value=key) for key, name in Platform.DISPLAY_NAMES.items()][:25]
