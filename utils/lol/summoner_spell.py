from __future__ import annotations

from pulsefire.clients import CDragonClient

from utils.cache import KeysCache

from .utils import cdragon_asset_url

__all__ = ("icon_by_id",)


class SummonerSpellKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as cdragon_client:
            summoner_spells = await cdragon_client.get_lol_v1_summoner_spells()

        data = {"icon_by_id": {}}
        for spell in summoner_spells:
            data["icon_by_id"][spell["id"]] = cdragon_asset_url(spell["iconPath"])

        return data


summoner_spell_keys_cache = SummonerSpellKeysCache()


async def icon_by_id(value: int) -> str:
    """Get summoner spell icon url by id"""
    return await summoner_spell_keys_cache.get("icon_by_id", value)
