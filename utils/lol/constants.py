from __future__ import annotations

from utils.const import ImageAsset

__all__ = (
    "LoLAsset",
    "NEW_CHAMPION_EMOTE",
)

_IMAGE_DIR = "./assets/images/lol/"


class LoLAsset(ImageAsset):
    ItemUnknown = f"{_IMAGE_DIR}item_unknown_64x64.png"
    RuneUnknown = f"{_IMAGE_DIR}rune_unknown_64x64.png"
    SummonerSpellUnknown = f"{_IMAGE_DIR}summoner_spell_unknown_64x64.png"


NEW_CHAMPION_EMOTE = "\N{SQUARED NEW}"
