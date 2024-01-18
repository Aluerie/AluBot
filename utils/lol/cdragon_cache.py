from __future__ import annotations

from typing import TYPE_CHECKING, MutableMapping, TypedDict

from ..cache import KeysCache

if TYPE_CHECKING:
    from bot import AluBot

    class ChampionCache(TypedDict):
        id_by_name: MutableMapping[str, int]
        name_by_id: MutableMapping[int, str]
        icon_by_id: MutableMapping[int, str]


__all__ = ("CDragonCache",)


class CDragonCache:
    def __init__(self, bot: AluBot):
        self.champion = ChampionKeysCache(bot)
        self.rune = RuneKeysCache(bot)
        self.item = ItemKeysCache(bot)
        self.summoner_spell = SummonerSpellKeysCache(bot)


BASE_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"


def cdragon_asset_url(path: str) -> str:
    """Return the CDragon url for the given game asset path"""
    path = path.lower()
    splitted = path.split("/lol-game-data/assets/")
    if len(splitted) == 2:
        return BASE_URL + splitted[1]
    return BASE_URL + path


class ChampionKeysCache(KeysCache):
    if TYPE_CHECKING:
        cached_data: ChampionCache

    async def fill_data(self) -> ChampionCache:
        async with self.bot.acquire_cdragon_client() as cdragon_client:
            champion_summary = await cdragon_client.get_lol_v1_champion_summary()

        data: ChampionCache = {
            "id_by_name": {},
            "name_by_id": {},
            "icon_by_id": {},
        }
        for champion in champion_summary:
            if champion["id"] == -1:
                continue

            data["id_by_name"][champion["name"].lower()] = champion["id"]
            data["name_by_id"][champion["id"]] = champion["name"]
            data["icon_by_id"][champion["id"]] = cdragon_asset_url(champion["squarePortraitPath"])

        return data

    # example of champion values
    # id: 145
    # name: "Kai'Sa" (lower_name in cache "id_by_name": "kai'sa")
    # key: "Kaisa"  # also key eats spaces like "MissFortune"
    # icon_url: https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/145.png

    async def id_by_name(self, champion_name: str) -> int:
        """Get champion id by name"""
        return await self.get_value("id_by_name", champion_name.lower())

    async def name_by_id(self, champion_id: int) -> str:
        """Get champion name by id"""
        return await self.get_value("name_by_id", champion_id)

    async def icon_by_id(self, champion_id: int) -> str:
        """Get champion icon url by id"""
        return await self.get_value("icon_by_id", champion_id)


class ItemKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with self.bot.acquire_cdragon_client() as cdragon_client:
            items = await cdragon_client.get_lol_v1_items()

        data = {"icon_by_id": {}}
        for item in items:
            data["icon_by_id"][item["id"]] = cdragon_asset_url(item["iconPath"])

        return data

    async def icon_by_id(self, item_id: int) -> str:
        """Get item icon url by id"""
        return await self.get_value("icon_by_id", item_id)


class RuneKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with self.bot.acquire_cdragon_client() as cdragon_client:
            perks = await cdragon_client.get_lol_v1_perks()

        data = {"icon_by_id": {}}
        for perk in perks:
            data["icon_by_id"][perk["id"]] = cdragon_asset_url(perk["iconPath"])

        return data

    async def icon_by_id(self, rune_id: int) -> str:
        """Get rune icon url by id"""
        return await self.get_value("icon_by_id", rune_id)


class SummonerSpellKeysCache(KeysCache):
    async def fill_data(self) -> dict:
        async with self.bot.acquire_cdragon_client() as cdragon_client:
            summoner_spells = await cdragon_client.get_lol_v1_summoner_spells()

        data = {"icon_by_id": {}}
        for spell in summoner_spells:
            data["icon_by_id"][spell["id"]] = cdragon_asset_url(spell["iconPath"])

        return data

    async def icon_by_id(self, summoner_spell_id: int) -> str:
        """Get summoner spell icon url by id"""
        return await self.get_value("icon_by_id", summoner_spell_id)
