from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, override

import aiohttp
import discord
from discord import app_commands

from utils import const, errors
from utils.lol import Champion, ChampionTransformer, LiteralPlatform, Platform

from ..base_classes import Account, BaseSettings
from .models import lol_links

if TYPE_CHECKING:
    from bot import AluBot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LolPlayerCandidate(NamedTuple):
    name: str
    platform: Platform
    game_name: str
    tag_line: str


class LoLAccountDict(TypedDict):
    summoner_id: str
    puuid: str
    platform: LiteralPlatform
    game_name: str
    tag_line: str
    # player_id: int
    # last_edited: int


class LoLAccount(Account):
    if TYPE_CHECKING:
        summoner_id: str
        puuid: str
        platform: Platform
        game_name: str
        tag_line: str

    @override
    async def set_game_specific_attrs(self, bot: AluBot, player: LolPlayerCandidate) -> None:
        # RIOT ACCOUNT INFO
        try:
            riot_account = await bot.lol.get_account_v1_by_riot_id(
                game_name=player.game_name,
                tag_line=player.tag_line,
                region=player.platform.continent,
                # in theory we can use continent closest to me bcs they all share the same data
                # for account_v1 endpoint
                # so check response time to this request (BUT WHATEVER)
            )
        except aiohttp.ClientResponseError:
            msg = (
                "Error `get_account_v1_by_riot_id` for "
                f"`{player.game_name}#{player.tag_line}` for `{player.platform}` platform.\n"
                "This account probably does not exist."
            )
            raise errors.BadArgument(msg)

        self.puuid = puuid = riot_account["puuid"]
        self.platform = player.platform
        self.game_name = riot_account["gameName"]
        self.tag_line = riot_account["tagLine"]

        # SUMMONER INFO
        try:
            summoner = await bot.lol.get_lol_summoner_v4_by_puuid(puuid=puuid, region=self.platform)
        except aiohttp.ClientResponseError:
            msg = (
                f"Error `get_lol_summoner_v4_by_puuid` for riot account\n"
                f"`{player.game_name}#{player.tag_line}` in `{player.platform}` platform, puuid: `{puuid}`"
            )
            raise errors.BadArgument(msg)
        self.summoner_id = summoner["id"]

    @property
    @override
    def hint_database_add_command_args(self) -> str:
        return (
            f"name: {self.player_display_name} game_name: {self.game_name} "
            f"tag_line: {self.tag_line} server: {self.platform.display_name}"
        )

    @override
    @staticmethod
    def static_account_name_with_links(platform: LiteralPlatform, game_name: str, tag_line: str, **kwargs: Any) -> str:
        opgg_name = Platform(platform).opgg_name
        links = lol_links(platform, game_name, tag_line)
        return f"`{opgg_name}`: `{game_name} #{tag_line}` {links}"

    @property
    @override
    def account_string_with_links(self) -> str:
        return self.static_account_name_with_links(self.platform.value, self.game_name, self.tag_line)

    @override
    @staticmethod
    def static_account_string(game_name: str, tag_line: str, **kwargs: Any) -> str:
        return f"{game_name} #{tag_line}"

    @property
    @override
    def account_string(self) -> str:
        return self.static_account_string(self.game_name, self.tag_line)

    @override
    def to_pseudo_record(self) -> LoLAccountDict:
        return {
            "summoner_id": self.summoner_id,
            "puuid": self.puuid,
            "platform": self.platform.value,
            "game_name": self.game_name,
            "tag_line": self.tag_line,
        }


class Settings(BaseSettings):
    """Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        bot.instantiate_lol()
        super().__init__(
            bot,
            *args,
            prefix="lol",
            colour=const.Colour.darkslategray,
            game_display_name="League of Legends",
            game_icon_url=const.Logo.Lol,
            character_singular="champion",
            character_plural="champions",
            account_cls=LoLAccount,
            account_typed_dict_cls=LoLAccountDict,
            characters=bot.lol.champions,
            **kwargs,
        )

    lol_group = app_commands.Group(
        name="lol",
        description="League of Legends FPC (Favourite Player+Character) commands.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    lol_request = app_commands.Group(
        name="request",
        description="League of Legends FPC (Favourite Player+Character) request commands.",
        parent=lol_group,
    )

    @lol_request.command(name="player")
    @app_commands.rename(platform="server", game_name="in-game-name")
    async def lol_request_player(
        self,
        interaction: discord.Interaction[AluBot],
        name: str,
        platform: Platform,
        game_name: str,
        tag_line: str,
    ) -> None:
        """\N{BANANA} Request LoL Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.

        Parameters
        ----------
        name
            Player name. if it's a twitch streamer then it should match their twitch handle.
        platform
            Server where the account is from, i.e. "KR", "NA", "EUW".
        game_name
            Riot ID name (without a hashtag or a tag), i.e. "Hide on bush", "Sneaky".
        tag_line
            Riot ID tag line (characters after a hashtag), i.e. "KR1", "NA69".
        """
        player_tuple = LolPlayerCandidate(name=name, platform=platform, game_name=game_name, tag_line=tag_line)
        await self.request_player(interaction, player_tuple)

    lol_setup = app_commands.Group(
        name="setup",
        description="Manage FPC feature settings in your server with those commands..",
        parent=lol_group,
    )

    @lol_setup.command(name="channel")
    async def lol_setup_channel(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{BANANA} Setup/manage your LoL FPC Notifications channel."""
        await self.setup_channel(interaction)

    @lol_setup.command(name="champions")
    async def lol_setup_champions(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{BANANA} Setup/manage your LoL FPC favourite champions list."""
        await self.setup_characters(interaction)

    @lol_setup.command(name="players")
    async def lol_setup_players(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{BANANA} Setup/manage your LoL FPC favourite players list."""
        await self.setup_players(interaction)

    @lol_setup.command(name="miscellaneous")
    async def lol_setup_misc(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{BANANA} Manage your LoL FPC misc settings."""
        await self.setup_misc(interaction)

    @lol_group.command(name="tutorial")
    async def lol_tutorial(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{BANANA} Guide to setup League of Legends FPC Notifications."""
        await self.tutorial(interaction)

    # HIDEOUT ONLY COMMANDS (at least, at the moment)
    hideout_lol_group = app_commands.Group(
        name="lolfpc",  # cspell: ignore lolfpc
        description="League of Legends FPC (Favourite Player+Character) Hideout-only commands.",
        guild_ids=[const.Guild.hideout],
    )

    hideout_lol_player = app_commands.Group(
        name="player",  # cspell: ignore lolfpc
        description="League of Legends FPC (Favourite Player+Character) Hideout-only player-related commands.",
        parent=hideout_lol_group,
    )

    @hideout_lol_player.command(name="add")
    async def hideout_lol_player_add(self, interaction: discord.Interaction[AluBot], player: str) -> None:
        """\N{GREEN APPLE} Add a League of Legends player into your favourite FPC players list.

        Parameters
        ----------
        player
            "Player Name. Autocomplete suggestions exclude your favourite players."
        """
        await self.hideout_player_add(interaction, player)

    @hideout_lol_player_add.autocomplete("player")
    async def hideout_lol_player_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_lol_player.command(name="remove")
    async def hideout_lol_player_remove(self, interaction: discord.Interaction[AluBot], player: str) -> None:
        """\N{GREEN APPLE} Remove a League of Legends player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions include only your favourite players.
        """
        await self.hideout_player_remove(interaction, player)

    @hideout_lol_player_remove.autocomplete("player")
    async def hideout_lol_player_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    hideout_lol_champion = app_commands.Group(
        name="champion",  # cspell: ignore lolfpc
        description="League of Legends FPC (Favourite Player+Character) Hideout-only champion-related commands.",
        parent=hideout_lol_group,
    )

    @hideout_lol_champion.command(name="add")
    async def hideout_lol_champion_add(
        self, interaction: discord.Interaction[AluBot], champion: app_commands.Transform[Champion, ChampionTransformer],
    ) -> None:
        """\N{GREEN APPLE} Add a League of Legends champion into your favourite FPC champions list.

        Parameters
        ----------
        champion
            Champion Name. Autocomplete suggestions exclude your favourite champs.
        """
        await self.hideout_character_add(interaction, champion)

    # @hideout_lol_champion_add.autocomplete("champion")
    # async def hideout_lol_champion_add_autocomplete(
    #     self, interaction: discord.Interaction[AluBot], current: str
    # ) -> list[app_commands.Choice[str]]:
    #     return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_lol_champion.command(name="remove")
    async def hideout_lol_champion_remove(
        self, interaction: discord.Interaction[AluBot], champion: app_commands.Transform[Champion, ChampionTransformer],
    ) -> None:
        """\N{GREEN APPLE} Remove a League of Legends champion into your favourite FPC champions list.

        Parameters
        ----------
        champion
            Champion Name. Autocomplete suggestions only include your favourite champs.
        """
        await self.hideout_character_remove(interaction, champion)

    # @hideout_lol_champion_remove.autocomplete("champion_name")
    # async def hideout_lol_champion_remove_autocomplete(
    #     self, interaction: discord.Interaction[AluBot], current: str
    # ) -> list[app_commands.Choice[str]]:
    #     return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_lol_player.command(name="list")
    async def hideout_lol_player_list(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{GREEN APPLE} Show a list of your favourite League of Legends FPC players."""
        await self.hideout_player_list(interaction)

    @hideout_lol_champion.command(name="list")
    async def hideout_lol_champion_list(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{GREEN APPLE} Show a list of your favourite League of Legends FPC champions."""
        await self.hideout_character_list(interaction)

    # Utilities to debug some rare situations.

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command()
    async def meraki(self, interaction: discord.Interaction[AluBot]) -> None:
        """Show list of champions that are missing from Meraki JSON."""
        embed = (
            discord.Embed(
                colour=const.Colour.darkslategray,
                title="List of champs missing from Meraki JSON",
                description=(
                    "\n".join(
                        [
                            f"\N{BLACK CIRCLE} {(await self.bot.lol.champions.by_id(i)).display_name} - `{i}`"
                            for i in await self.bot.lol.roles.get_missing_from_meraki_champion_ids()
                        ],
                    )
                    or "None missing"
                ),
            )
            .add_field(
                name="Links",
                value=(
                    "• [GitHub](https://github.com/meraki-analytics/role-identification)\n"
                    "• [Json](https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json)"
                ),
            )
            .add_field(name="Meraki last updated", value=f"Patch {self.bot.lol.roles.meraki_patch}")
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Settings(bot))
