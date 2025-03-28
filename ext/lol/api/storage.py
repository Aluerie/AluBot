from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypedDict, override

import discord
from roleidentification import get_roles

from utils import const

from ...base_fpc import Character, CharacterStorage, CharacterTransformer, GameDataStorage
from . import game_const

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

    class GetChampionEmoteRow(TypedDict):
        id: int
        emote: str

    from pulsefire.schemas import MerakiCDNSchema


__all__ = (
    "Champion",
    "ChampionTransformer",
    "Champions",
    "ItemIcons",
    "PseudoChampion",
    "RolesIdentifiers",
    "RuneIcons",
    "SummonerSpellIcons",
)


BASE_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"


def cdragon_asset_url(path: str) -> str:
    """Return the CDragon url for the given game asset path."""
    path = path.lower()
    splitted = path.split("/lol-game-data/assets/")
    if len(splitted) == 2:
        return BASE_URL + splitted[1]
    return BASE_URL + path


@dataclass(repr=False)
class Champion(Character):
    alias: str
    """No spaces, no extra symbols, PascalCase-like name for the champion,
    i.e. Kaisa (not Kai'Sa), MissFortune (not Miss Fortune)
    """
    icon_url: str
    """_summary_

    https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/145.png
    """


@dataclass(repr=False)
class PseudoChampion(Character):
    alias: str
    icon_url: str


class Champions(CharacterStorage[Champion, PseudoChampion]):
    @override
    async def fill_data(self) -> dict[int, Champion]:
        """_summary_.

        Sources
        -------
        * https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        """
        champion_summary = await self.bot.lol.cdragon.get_lol_v1_champion_summary()

        query = "SELECT id, emote FROM lol_champions_info"
        rows: list[GetChampionEmoteRow] = await self.bot.pool.fetch(query)
        champion_emotes = {row["id"]: row["emote"] for row in rows}

        data = {
            champion["id"]: Champion(
                id=champion["id"],
                display_name=champion["name"],
                alias=champion["alias"],
                icon_url=cdragon_asset_url(champion["squarePortraitPath"]),
                emote=champion_emotes.get(champion["id"])
                or await self.create_champion_emote(
                    champion["id"],
                    champion["alias"],
                    cdragon_asset_url(champion["squarePortraitPath"]),
                ),
            )
            for champion in champion_summary
        }
        # they provide champion value for None, but I've never seen their API to give me "-1" yet.
        # maybe will regret it
        data.pop(-1, None)
        return data

    @override
    @staticmethod
    def generate_unknown_object(champion_id: int) -> PseudoChampion:
        return PseudoChampion(
            id=champion_id,
            display_name="Unknown",
            alias="Unknown",
            icon_url=cdragon_asset_url("/lol-game-data/assets/v1/champion-icons/-1.png"),
            # taken from `get_lol_v1_champion_summary` response ^ for champion with id=-1
            emote=game_const.NEW_CHAMPION_EMOTE,
        )

    async def create_champion_emote(self, champion_id: int, champion_alias: str, champion_icon_url: str) -> str:
        """Create a new discord emote for a League of Legends champion."""
        try:
            return await self.create_character_emote_helper(
                character_id=champion_id,
                table="lol_champions_info",
                emote_name=champion_alias,
                emote_source_url=champion_icon_url,  # copy of `minimap_icon_url` property
                guild_id=const.EmoteGuilds.LOL[3],
            )
        except Exception as exc:
            embed = discord.Embed(
                description=(
                    f"Something went wrong when creating champion emote for `id={champion_id}, alias={champion_alias}`."
                ),
            )
            await self.bot.exc_manager.register_error(exc, embed=embed)
            return game_const.NEW_CHAMPION_EMOTE


class ChampionTransformer(CharacterTransformer[Champion, PseudoChampion]):
    @override
    def get_character_storage(self, interaction: AluInteraction) -> Champions:
        return interaction.client.lol.champions


class ItemIcons(GameDataStorage[str, str]):
    """_summary_.

    Example
    ----------
    https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/assets/items/icons2d/1001_class_t1_bootsofspeed.png

    """

    @override
    async def fill_data(self) -> dict[int, str]:
        """_summary_.

        https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        """
        items = await self.bot.lol.cdragon.get_lol_v1_items()
        return {item["id"]: cdragon_asset_url(item["iconPath"]) for item in items}

    @override
    @staticmethod
    def generate_unknown_object(_: int) -> str:
        return game_const.LeagueAsset.ItemUnknown


class RuneIcons(GameDataStorage[str, str]):
    """_summary_.

    Examples
    --------
    https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/perk-images/styles/precision/lethaltempo/lethaltempotemp.png
    https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/perk-images/styles/sorcery/unflinching/unflinching.png
    """

    @override
    async def fill_data(self) -> dict[int, str]:
        """_summary_.

        https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        """
        perks = await self.bot.lol.cdragon.get_lol_v1_perks()
        return {perk["id"]: cdragon_asset_url(perk["iconPath"]) for perk in perks}

    @override
    @staticmethod
    def generate_unknown_object(_: int) -> str:
        return game_const.LeagueAsset.RuneUnknown


class SummonerSpellIcons(GameDataStorage[str, str]):
    """_summary_.

    Examples
    --------
    https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/data/spells/icons2d/summoner_boost.png
    """

    @override
    async def fill_data(self) -> dict[int, str]:
        """_summary_.

        https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        """
        summoner_spells = await self.bot.lol.cdragon.get_lol_v1_summoner_spells()
        return {spell["id"]: cdragon_asset_url(spell["iconPath"]) for spell in summoner_spells}

    @override
    @staticmethod
    def generate_unknown_object(_: int) -> str:
        return game_const.LeagueAsset.SummonerSpellUnknown


class RoleDict(TypedDict):
    TOP: float
    JUNGLE: float
    MIDDLE: float
    BOTTOM: float
    UTILITY: float


class RolesIdentifiers(GameDataStorage[RoleDict, RoleDict]):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot=bot)
        self.meraki_patch: str = "Unknown"

    @override
    async def fill_data(self) -> dict[int, RoleDict]:
        """My own analogy to `from roleidentification import pull_data`.

        Meraki's `pull_data` is using `import requests`
        which is blocking, so I have to copypaste it

        We can always check if they changed it at
        https://github.com/meraki-analytics/role-identification
        """
        champion_roles = await self.bot.lol.meraki.get_lol_champion_rates()
        self.meraki_patch = champion_roles["patch"]

        data = {}
        for champion_id, positions in champion_roles["data"].items():
            play_rates: dict[Literal["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"], float] = {}

            for position, rates in positions.items():
                # for some reason, `.items` gives dict_items[str, object] typing for TypedDicts while in this case:
                # `position` is secured to be `Literal["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]`
                # `rates` is secured to be `LolPlayRate` which is `TypedDict("LolPlayRate", {"playRate": float})`
                # hence the following line is correct type-wise;
                play_rates[position.upper()] = rates["playRate"]  # type:ignore[reportArgumentType, reportIndexIssue]
            for position in ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"):
                if position not in play_rates:
                    play_rates[position] = 0.0
            data[int(champion_id)] = play_rates

        return await self.get_better_champion_roles(data)

    async def get_missing_from_meraki_champion_ids(self, data_meraki: dict[int, RoleDict] | None = None) -> set[int]:
        data_meraki = data_meraki or await self.get_cached_data()
        champion_dict = await self.bot.lol.champions.get_cached_data()
        return set(champion_dict.keys()) - set(data_meraki.keys())

    @override
    @staticmethod
    def generate_unknown_object(
        playrate: float = 10,  # usually new champions (that are likely to be missing) have rather high playrate
        *,
        top: float = 20,
        jungle: float = 20,
        mid: float = 20,
        bot: float = 20,
        support: float = 20,
    ) -> RoleDict:
        """Construct the dict for meraki function.

        Note all parameters in percent! Just like at www.leagueofgraphs.com
        """
        return {  # global playrate in percent * champion role appearance in %
            "TOP": playrate * top * 0.01,
            "JUNGLE": playrate * jungle * 0.01,
            "MIDDLE": playrate * mid * 0.01,
            "BOTTOM": playrate * bot * 0.01,
            "UTILITY": playrate * support * 0.01,
        }

    async def get_better_champion_roles(self, champion_roles: dict[int, RoleDict]) -> dict[int, RoleDict]:
        """Improvement to meraki's `get_roles()`.

        Unfortunately, Meraki run out of money to support their Json
        Thus sometimes it is behind a few patches and
        I need to add new champions myself with this function.

        About Manual adding part:
        For Example, when 12.13 patch was live - Nilah was not in Meraki Json.
        Thus, I can add it myself with the data from League of Graphs
        https://www.leagueofgraphs.com/champions/stats/nilah/master
        and it here for more precise data rather than 0.2 in all roles.
        """
        diff_list = await self.get_missing_from_meraki_champion_ids(champion_roles)

        # Nilah (data was taken 03/Jan/23) - {id: the_dict}
        # https://www.leagueofgraphs.com/champions/stats/nilah/master
        manual_data = {
            895: self.generate_unknown_object(playrate=2.8, top=0.4, jungle=0.0, mid=1.7, bot=97.4, support=0.4),
        }
        diff_dict = {x: self.generate_unknown_object() for x in diff_list if x not in manual_data}
        return diff_dict | (manual_data | champion_roles)

    async def sort_champions_by_roles(self, all_players_champ_ids: list[int]) -> list[int]:
        try:
            champion_roles: dict[int, RoleDict] = await self.get_cached_data()
            team1 = list(get_roles(champion_roles, all_players_champ_ids[:5]).values())
            team2 = list(get_roles(champion_roles, all_players_champ_ids[5:]).values())
        except Exception:  # noqa: BLE001
            # there was some problem with probably meraki
            return all_players_champ_ids
        else:
            return team1 + team2  # pyright: ignore[reportReturnType] # meraki typing sucks
