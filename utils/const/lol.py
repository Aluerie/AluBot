from __future__ import annotations

from enum import StrEnum
from typing import override

from ._meta import ASSETS_IMAGES, RAW_GITHUB_IMAGES

__all__ = (
    "NEW_CHAMPION_EMOTE",
    "LeagueAsset",
)


class LeagueAsset(StrEnum):
    """League images saved as .png file in the repository assets folder."""

    ItemUnknown = "item_unknown_64x64.png"
    RuneUnknown = "rune_unknown_64x64.png"
    SummonerSpellUnknown = "summoner_spell_unknown_64x64.png"

    @override
    def __str__(self) -> str:
        """Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`."""
        return ASSETS_IMAGES + "lol/" + self.value

    @property
    def url(self) -> str:
        """Link to the image hosted on raw.githubusercontent.com."""
        return RAW_GITHUB_IMAGES + "lol/" + self.value


NEW_CHAMPION_EMOTE = "\N{SQUARED NEW}"
