from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import override

from utils.const.abc import ASSETS_IMAGES, RAW_GITHUB_IMAGES

__all__ = ("FACET_COLORS", "NEW_HERO_EMOTE", "PLAYER_COLOR_MAP", "FpcAsset", "LazyIcon")


PLAYER_COLOR_MAP = (
    "#3375FF",
    "#66FFBF",
    "#BF00BF",
    "#F3F00B",
    "#FF6B00",
    "#FE86C2",
    "#A1B447",
    "#65D9F7",
    "#008321",
    "#A46900",
)


class LazyIcon(StrEnum):
    """Lazy links to some commonly used images for Dota 2."""

    TalentTree = "https://liquipedia.net/commons/images/5/54/Talents.png"
    AttributeBonus = "https://static.wikia.nocookie.net/dota2_gamepedia/images/e/e2/Attribute_Bonus_icon.png"


class LazyItemID(IntEnum):
    """Lazy ids for some items that are easier to remember like this for image generation."""

    AghanimsScepter = 108
    AghanimsBlessing = 271
    AghanimsShard = 609


class FpcAsset(StrEnum):
    """Dota 2 images saved as .png file in the repository assets folder."""

    AbilityUnknown = "ability_unknown.png"
    FacetQuestion = "facet_question.png"
    HeroTopbarDisconnectedUnpicked = "hero_disconnected.png"
    HeroTopbarUnknown = "hero_unknown.png"
    ItemEmpty = "item_empty.png"
    ItemUnknown = "item_unknown.png"
    Placeholder640X360 = "Lavender640x360.png"

    @override
    def __str__(self) -> str:
        """Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`."""
        return ASSETS_IMAGES + "dota/" + self.value

    @property
    def url(self) -> str:
        """Link to the image hosted on raw.githubusercontent.com."""
        return RAW_GITHUB_IMAGES + "dota/" + self.value


FACET_COLORS = {
    # yoinked from https://github.com/mdiller/MangoByte/blob/master/resource/json/facet_colors.json
    "Red0": "#9F3C3C",
    "Red1": "#954533",
    "Red2": "#A3735E",
    "Yellow0": "#C8A45C",
    "Yellow1": "#C6A158",
    "Yellow2": "#CAC194",
    "Yellow3": "#C3A99A",
    "Green0": "#A2B23E",
    "Green1": "#7EC2B2",
    "Green2": "#538564",
    "Green3": "#9A9F6A",
    "Green4": "#9FAD8E",
    "Blue0": "#727CB2",
    "Blue1": "#547EA6",
    "Blue2": "#6BAEBC",
    "Blue3": "#94B5BA",
    "Purple0": "#B57789",
    "Purple1": "#9C70A4",
    "Purple2": "#675CAE",
    "Gray0": "#565C61",
    "Gray1": "#6A6D73",
    "Gray2": "#95A9B1",
    "Gray3": "#ADB6BE",
}

NEW_HERO_EMOTE = "\N{SQUARED NEW}"
