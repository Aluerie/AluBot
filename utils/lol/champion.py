from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from pulsefire.clients import CDragonClient

from utils.cache import KeysCache

from .utils import cdragon_asset_url

if TYPE_CHECKING:
    pass
    # class ChampData(TypedDict):
    #     id: int
    #     name: str
    #     alias: str
    #     squarePortraitPath: str
    #     roles: list[str]


__all__ = (
    "id_by_key",
    "id_by_name",
    "key_by_id",
    "name_by_id",
    "key_by_name",
    "name_by_key",
    "icon_by_id",
    "all_champion_names",
    "all_champion_ids",
)


class ChampionKeysCache(KeysCache):
    URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/en_gb/v1/champion-summary.json"
    BASE_ICON_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"

    async def fill_data(self) -> dict:
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as cdragon_client:
            champion_summary = await cdragon_client.get_lol_v1_champion_summary()

        # could just do this, lol
        # champion_summary: list[ChampData] = await self.get_response_json(self.URL)

        data = {
            "id_by_key": {},
            "id_by_name": {},
            "key_by_id": {},
            "key_by_name": {},
            "name_by_id": {},
            "name_by_key": {},
            "icon_by_id": {},
        }
        for champion in champion_summary:
            if champion["id"] == -1:
                continue

            data["id_by_key"][champion["alias"]] = champion["id"]
            data["id_by_name"][champion["name"]] = champion["id"]
            data["key_by_id"][champion["id"]] = champion["alias"]
            data["key_by_name"][champion["name"]] = champion["alias"]
            data["name_by_id"][champion["id"]] = champion["name"]
            data["name_by_key"][champion["alias"]] = champion["name"]
            data["icon_by_id"][champion["id"]] = cdragon_asset_url(champion["squarePortraitPath"])

        return data


champion_keys_cache = ChampionKeysCache()

# example of champion values
# id: 145
# name: "Kai'Sa",
# key: "Kaisa"  # also key eats spaces like "MissFortune"
# icon_url: https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/145.png


async def id_by_key(value: str) -> int:
    """Get champion id by key"""
    return await champion_keys_cache.get("id_by_key", value)


async def id_by_name(value: str) -> int:
    """Get champion id by name"""
    return await champion_keys_cache.get("id_by_name", value)


async def key_by_id(value: int) -> str:  # todo: check if i use key shit at all
    """Get champion key by id"""
    return await champion_keys_cache.get("key_by_id", value)


async def key_by_name(value: str) -> str:
    """Get champion key by name"""
    return await champion_keys_cache.get("key_by_name", value)


async def name_by_id(value: int) -> str:
    """Get champion name by id"""
    return await champion_keys_cache.get("name_by_id", value)


async def name_by_key(value: str) -> str:
    """Get champion name by key"""
    return await champion_keys_cache.get("name_by_key", value)


async def icon_by_id(value: int) -> str:
    """Get champion icon url by id"""
    return await champion_keys_cache.get("icon_by_id", value)


async def all_champion_names() -> list[str]:
    """Get all champion names in League of Legends"""
    data = await champion_keys_cache.get_data()
    return list(data["name_by_id"].values())


async def all_champion_ids() -> list[int]:
    """Get all champion ids in League of Legends"""
    data = await champion_keys_cache.get_data()
    return list(data["name_by_id"].keys())
