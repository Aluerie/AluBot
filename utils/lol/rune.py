from __future__ import annotations

from pulsefire.clients import CDragonClient

from utils.cache import KeysCache

from .utils import cdragon_asset_url

__all__ = ("icon_by_id",)


# todo: maybe give generics to this garbage so we can dive into nerdy typing
class RuneKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as cdragon_client:
            perks = await cdragon_client.get_lol_v1_perks()

        data = {"icon_by_id": {}}
        for perk in perks:
            data["icon_by_id"][perk["id"]] = cdragon_asset_url(perk["iconPath"])

        return data


rune_keys_cache = RuneKeysCache()


async def icon_by_id(value: int) -> str:
    """Get rune icon url by id"""
    return await rune_keys_cache.get("icon_by_id", value)
