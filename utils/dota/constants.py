from __future__ import annotations

from utils.const import ImageAsset

__all__ = (
    "TALENT_TREE_ICON",
    "DotaAsset",
    "FACET_COLOURS",
    "NEW_HERO_EMOTE",
)

TALENT_TREE_ICON = "https://liquipedia.net/commons/images/5/54/Talents.png"


_IMAGE_DIR = "./assets/images/dota/"


class DotaAsset(ImageAsset):
    """Dota 2 images saved as .png file in the repository assets folder."""

    AbilityUnknown = f"{_IMAGE_DIR}ability_unknown.png"
    FacetQuestion = f"{_IMAGE_DIR}facet_question.png"
    HeroTopbarDisconnectedUnpicked = f"{_IMAGE_DIR}hero_disconnected.png"
    HeroTopbarUnknown = f"{_IMAGE_DIR}hero_unknown.png"
    ItemEmpty = f"{_IMAGE_DIR}item_empty.png"
    ItemUnknown = f"{_IMAGE_DIR}item_unknown.png"
    Placeholder640X360 = f"{_IMAGE_DIR}Lavender640x360.png"


FACET_COLOURS = {
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
