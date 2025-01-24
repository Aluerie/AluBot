from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, Literal, Self, TypeVar, override

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from bot import AluContext

__all__ = (
    "LiteralPlatform",
    "Platform",
    "PlatformConverter",
)

T_co = TypeVar("T_co", covariant=True)
TT = TypeVar("TT", bound="type[Any]")


class classproperty(Generic[TT, T_co]):  # noqa: N801
    def __init__(self, func: Callable[[TT], T_co]) -> None:
        self.__func__ = func

    def __get__(self, _: Any, type: TT) -> T_co:  # noqa: A002 # _ is `instance`
        return self.__func__(type)


LiteralPlatform = Literal[
    "BR1",
    "EUN1",
    "EUW1",
    "JP1",
    "KR",
    "LA1",
    "LA2",
    "NA1",
    "OC1",
    "PH2",
    "RU",
    "SG2",
    "TH2",
    "TR1",
    "TW2",
    "VN2",
]


# fmt: off
class Platform(StrEnum):
    """RiotGames routing platform names with numbers like `NA1`.

    Notes
    -----
    region - it's a garbage term, because Riot API uses it as both `platform` and `region` in its namings.
        So in pulsefire's Riot Api Client calls we use both continent and platform for `region=` keyword argument.

    Other terms are fine and documented as properties below in this class.

    """

    Brazil = "BR1"
    EuropeNordicAndEast = "EUN1"
    EuropeWest = "EUW1"
    Japan = "JP1"
    RepublicOfKorea = "KR"
    LatinAmericaNorth = "LA1"
    LatinAmericaSouth = "LA2"
    NorthAmerica = "NA1"
    Oceania = "OC1"
    Philippines = "PH2"
    Russia = "RU"
    Singapore = "SG2"
    Thailand = "TH2"
    Turkey = "TR1"
    Taiwan = "TW2"
    Vietnam = "VN2"
    # PublicBetaEnvironment = "PBE" # no, we will not support it. # noqa: ERA001

    @classproperty
    def DISPLAY_NAMES(cls: type[Self]) -> Mapping[Platform, str]:  # pyright: ignore[reportGeneralTypeIssues]  # noqa: N805, N802
        """Normal human-readable server abbreviations like 'NA' together with its name.

        "Display Name" as a concept does not exist in Riot API and only used by me for display purposes.
        """
        return {
            cls.Brazil: "BR - Brazil",
            cls.EuropeNordicAndEast: "EUNE - Europe Nordic & East",
            cls.EuropeWest: "EUW - Europe West",
            cls.Japan: "JP - Japan",
            cls.RepublicOfKorea: "KR - Republic of Korea",
            cls.LatinAmericaNorth: "LAN - Latin America North",
            cls.LatinAmericaSouth: "LAS - Latin America South",
            cls.NorthAmerica: "NA - North America",
            cls.Oceania: "OCE - Oceania",
            cls.Philippines: "PH - Philippines",
            cls.Russia: "RU - Russia",
            cls.Singapore: "SG - Singapore, Malaysia, & Indonesia",
            cls.Thailand: "TH - Thailand",
            cls.Turkey: "TR - Turkey",
            cls.Taiwan: "TW - Taiwan, Hong Kong, and Macao",
            cls.Vietnam: "VN - Vietnam",
        }

    @property
    def display_name(self) -> str:
        """Get display name for the current platform enum."""
        return self.DISPLAY_NAMES[self]

    @classproperty
    def CONTINENTS(cls: type[Self]) -> Mapping[Platform, str]:  # pyright: ignore[reportGeneralTypeIssues] # noqa: N802, N805
        """RiotGames routing continent names like `AMERICAS`."""
        return {
            cls.Brazil: "AMERICAS",
            cls.EuropeNordicAndEast: "EUROPE",
            cls.EuropeWest: "EUROPE",
            cls.Japan: "ASIA",
            cls.RepublicOfKorea: "ASIA",
            cls.LatinAmericaNorth: "AMERICAS",
            cls.LatinAmericaSouth: "AMERICAS",
            cls.NorthAmerica: "AMERICAS",
            cls.Oceania: "ASIA",
            cls.Philippines: "ASIA",
            cls.Russia: "EUROPE",
            cls.Singapore: "ASIA",
            cls.Thailand: "ASIA",
            cls.Turkey: "EUROPE",
            cls.Taiwan: "ASIA",
            cls.Vietnam: "ASIA",
        }

    @property
    def continent(self) -> str:
        """Get continent for the current platform enum."""
        return self.CONTINENTS[self]

    @classproperty
    def OPGG_NAMES(cls: type[Self]) -> Mapping[Platform, str]:  # pyright: ignore[reportGeneralTypeIssues]  # noqa: N805, N802
        """OP.GG names for platforms.

        Used in their links as sub-domain.
        """
        return {
            cls.Brazil: "BR",
            cls.EuropeNordicAndEast: "EUNE",
            cls.EuropeWest: "EUW",
            cls.Japan: "JP",
            cls.RepublicOfKorea: "KR",
            cls.LatinAmericaNorth: "LAN",
            cls.LatinAmericaSouth: "LAS",
            cls.NorthAmerica: "NA",
            cls.Oceania: "OCE",
            cls.Philippines: "PH",
            cls.Russia: "RU",
            cls.Singapore: "SG",
            cls.Thailand: "TH",
            cls.Turkey: "TR",
            cls.Taiwan: "TW",
            cls.Vietnam: "VN",
        }

    @property
    def opgg_name(self) -> str:
        """Get op.gg name for the current platform enum."""
        return self.OPGG_NAMES[self]
# fmt: on


class PlatformConverter(commands.Converter[Platform], app_commands.Transformer):
    """PlatformConverter for both prefix and slash commands.

    for prefix commands - it accepts OPGG_NAMES - meaning values such as NA, euw, las, oce, etc.
    for slash commands - it offers `choices` with "display_name: platform" mapping.

    Both in the end return Platform type.
    """

    @override
    async def convert(self, ctx: AluContext, argument: str) -> Platform:
        for platform, opgg_name in Platform.OPGG_NAMES.items():
            if argument.upper() == opgg_name:
                return platform
        msg = (
            f"Couldn't find any servers like that `{argument!r}`\n"
            f"The list of League of Legends servers is {[v.upper() for v in Platform.OPGG_NAMES.values()]}"
        )
        raise commands.BadArgument(msg)

    @override
    async def transform(self, _: discord.Interaction[discord.Client], value: str) -> Platform:
        # since we have choices hard-coded it will be of Platform type-string
        # PS. app_commands.Transformer won't run without subclassed `transform`
        return Platform(value)

    @property
    @override
    def choices(self) -> list[app_commands.Choice[Platform]]:
        return [app_commands.Choice(name=name, value=key) for key, name in Platform.DISPLAY_NAMES.items()][:25]
