from __future__ import annotations

from utils.const import ImageAsset

__all__ = (
    "LoLAsset",
    "NEW_CHAMPION_EMOTE",
)


class LoLAsset(ImageAsset):
    ItemUnknown = "lol/item_unknown_64x64.png"
    RuneUnknown = "lol/rune_unknown_64x64.png"
    SummonerSpellUnknown = "lol/summoner_spell_unknown_64x64.png"


NEW_CHAMPION_EMOTE = "\N{SQUARED NEW}"
