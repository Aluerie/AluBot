from __future__ import annotations

from pulsefire.clients import CDragonClient

from utils.cache import KeysCache

from .utils import cdragon_asset_url

__all__ = ("icon_by_id",)


class ItemKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as cdragon_client:
            items = await cdragon_client.get_lol_v1_items()

        data = {"icon_by_id": {}}
        for item in items:
            data["icon_by_id"][item["id"]] = cdragon_asset_url(item["iconPath"])

        return data


item_keys_cache = ItemKeysCache()


async def icon_by_id(value: int) -> str:
    """Get item icon url by id"""
    return await item_keys_cache.get("icon_by_id", value)
