from __future__ import annotations

from enum import StrEnum
from typing import override

from ._meta import ASSETS_IMAGES, RAW_GITHUB_IMAGES

__all__ = (
    "NEW_CHAMPION_EMOTE",
    "LoLAsset",
)


class LoLAsset(StrEnum):
    ItemUnknown = "item_unknown_64x64.png"
    RuneUnknown = "rune_unknown_64x64.png"
    SummonerSpellUnknown = "summoner_spell_unknown_64x64.png"

    @override
    def __str__(self) -> str:
        """Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`"""
        return ASSETS_IMAGES + "lol/" + self.value

    @property
    def url(self) -> str:
        return RAW_GITHUB_IMAGES + "lol/" + self.value


NEW_CHAMPION_EMOTE = "\N{SQUARED NEW}"
