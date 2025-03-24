from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, override

import aiohttp
import discord
from discord import app_commands

from utils import const, errors

from ...base_fpc import BaseAccount, BasePlayer, BaseRequestPlayerArguments, BaseSettings
from ..api import Champion, ChampionTransformer, Platform  # noqa: TC001

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@dataclass
class LeagueRequestPlayerArguments(BaseRequestPlayerArguments):
    """Arguments for the following slash commands.

    * /lol request player
    * /database-lol-dev add
    """

    platform: Platform
    in_game_name: str
    tag_line: str


@dataclass
class LeagueAccount(BaseAccount):
    """League Account."""

    summoner_id: str
    puuid: str
    platform: Platform
    in_game_name: str
    tag_line: str

    @override
    @classmethod
    async def create(cls, bot: AluBot, arguments: LeagueRequestPlayerArguments) -> Self:
        # RIOT ACCOUNT INFO
        try:
            riot_account = await bot.lol.get_account_v1_by_riot_id(
                game_name=arguments.in_game_name,
                tag_line=arguments.tag_line,
                region=arguments.platform.continent,
                # in theory we can use continent closest to me bcs they all share the same data
                # for account_v1 endpoint
                # so check response time to this request (BUT WHATEVER)
            )
        except aiohttp.ClientResponseError:
            msg = (
                "Error `get_account_v1_by_riot_id` for "
                f"`{arguments.in_game_name}#{arguments.tag_line}` for `{arguments.platform}` platform.\n"
                "This account probably does not exist."
            )
            raise errors.BadArgument(msg) from None

        puuid = riot_account["puuid"]

        # SUMMONER INFO
        try:
            summoner = await bot.lol.get_lol_summoner_v4_by_puuid(puuid=puuid, region=arguments.platform)
        except aiohttp.ClientResponseError:
            msg = (
                f"Error `get_lol_summoner_v4_by_puuid` for riot account\n"
                f"`{arguments.in_game_name}#{arguments.tag_line}` in `{arguments.platform}` platform, puuid: `{puuid}`"
            )
            raise errors.BadArgument(msg) from None

        return cls(
            summoner_id=summoner["id"],
            puuid=puuid,
            platform=arguments.platform,
            in_game_name=riot_account["gameName"],
            tag_line=riot_account["tagLine"],
        )

    @override
    def links(self) -> str:
        opgg_platform = self.platform.opgg_name

        # self.platform would work too instead of opgg_platform
        opgg_link = f"https://op.gg/summoners/{opgg_platform}/{self.in_game_name}-{self.tag_line}"
        return f"`{opgg_platform}`: `{self.in_game_name} #{self.tag_line}` /[Opgg]({opgg_link})"

    @property
    @override
    def display_name(self) -> str:
        return f"{self.in_game_name} #{self.tag_line}"


class LeaguePlayer(BasePlayer[LeagueAccount]):
    """League of Legends Player."""

    @override
    def hint_database_add_command_arguments(self) -> str:
        return (
            f"name: {self.display_name} in_game_name: {self.account.in_game_name} "
            f"tag_line: {self.account.tag_line} server: {self.account.platform.display_name}"
        )


class LolFPCSettings(BaseSettings):
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
            color=const.Color.league,
            game_display_name="League of Legends",
            game_icon_url=const.Logo.LeagueOfLegends,
            character_singular="champion",
            character_plural="champions",
            player_cls=LeaguePlayer,
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
    @app_commands.rename(platform="server")
    async def lol_request_player(
        self, interaction: AluInteraction, name: str, platform: Platform, in_game_name: str, tag_line: str
    ) -> None:
        """\N{BANANA} Request League of Legends Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.

        Parameters
        ----------
        name: str
            Player name. if it's a twitch streamer then it should match their twitch handle.
        platform: Platform
            Server where the account is from, i.e. "KR", "NA", "EUW".
        in_game_name: str
            Riot ID name (without a hashtag or a tag), i.e. "Hide on bush", "Sneaky".
        tag_line: str
            Riot ID tag line (characters after a hashtag), i.e. "KR1", "NA69".
        """
        player_arguments = LeagueRequestPlayerArguments(
            name=name, platform=platform, in_game_name=in_game_name, tag_line=tag_line, is_twitch_streamer=True
        )
        await self.request_player(interaction, player_arguments)

    lol_setup = app_commands.Group(
        name="setup",
        description="Manage FPC feature settings in your server with those commands..",
        parent=lol_group,
    )

    @lol_setup.command(name="channel")
    async def lol_setup_channel(self, interaction: AluInteraction) -> None:
        """\N{BANANA} Setup/manage your League of Legends FPC Notifications channel."""
        await self.setup_channel(interaction)

    @lol_setup.command(name="champions")
    async def lol_setup_champions(self, interaction: AluInteraction) -> None:
        """\N{BANANA} Setup/manage your League of Legends FPC favourite champions list."""
        await self.setup_characters(interaction)

    @lol_setup.command(name="players")
    async def lol_setup_players(self, interaction: AluInteraction) -> None:
        """\N{BANANA} Setup/manage your League of Legends FPC favourite players list."""
        await self.setup_players(interaction)

    @lol_setup.command(name="miscellaneous")
    async def lol_setup_misc(self, interaction: AluInteraction) -> None:
        """\N{BANANA} Manage your League of Legends FPC misc settings."""
        await self.setup_misc(interaction)

    @lol_group.command(name="tutorial")
    async def lol_tutorial(self, interaction: AluInteraction) -> None:
        """\N{BANANA} Guide to setup League of Legends FPC Notifications."""
        await self.tutorial(interaction)

    # HIDEOUT ONLY COMMANDS (at least, at the moment)
    hideout_lol_group = app_commands.Group(
        name="lol-dev",
        description="League of Legends FPC (Favourite Player+Character) Hideout-only commands.",
        guild_ids=[const.Guild.hideout],
    )

    hideout_lol_player = app_commands.Group(
        name="player",
        description="League of Legends FPC (Favourite Player+Character) Hideout-only player-related commands.",
        parent=hideout_lol_group,
    )

    @hideout_lol_player.command(name="add")
    async def hideout_lol_player_add(self, interaction: AluInteraction, player: str) -> None:
        """\N{GREEN APPLE} Add a League of Legends player into your favourite FPC players list.

        Parameters
        ----------
        player
            "Player Name. Autocomplete suggestions exclude your favourite players."
        """
        await self.hideout_player_add(interaction, player)

    @hideout_lol_player_add.autocomplete("player")
    async def hideout_lol_player_add_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/lol-dev player add` command.

        Suggests players from the League FPC database that the current guild hasn't subscribed to.
        """
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_lol_player.command(name="remove")
    async def hideout_lol_player_remove(self, interaction: AluInteraction, player: str) -> None:
        """\N{GREEN APPLE} Remove a League of Legends player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions include only your favourite players.
        """
        await self.hideout_player_remove(interaction, player)

    @hideout_lol_player_remove.autocomplete("player")
    async def hideout_lol_player_remove_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/lol-dev player remove` command.

        Suggests players from the League FPC database that the current guild subscribed to.
        """
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    hideout_lol_champion = app_commands.Group(
        name="champion",
        description="League of Legends FPC (Favourite Player+Character) Hideout-only champion-related commands.",
        parent=hideout_lol_group,
    )

    @hideout_lol_champion.command(name="add")
    async def hideout_lol_champion_add(
        self, interaction: AluInteraction, champion: app_commands.Transform[Champion, ChampionTransformer]
    ) -> None:
        """\N{GREEN APPLE} Add a League of Legends champion into your favourite FPC champions list.

        Parameters
        ----------
        champion
            Champion Name. Autocomplete suggestions exclude your favourite champs.
        """
        await self.hideout_character_add(interaction, champion)

    @hideout_lol_champion.command(name="remove")
    async def hideout_lol_champion_remove(
        self, interaction: AluInteraction, champion: app_commands.Transform[Champion, ChampionTransformer]
    ) -> None:
        """\N{GREEN APPLE} Remove a League of Legends champion into your favourite FPC champions list.

        Parameters
        ----------
        champion
            Champion Name. Autocomplete suggestions only include your favourite champs.
        """
        await self.hideout_character_remove(interaction, champion)

    @hideout_lol_player.command(name="list")
    async def hideout_lol_player_list(self, interaction: AluInteraction) -> None:
        """\N{GREEN APPLE} Show a list of your favourite League of Legends FPC players."""
        await self.hideout_player_list(interaction)

    @hideout_lol_champion.command(name="list")
    async def hideout_lol_champion_list(self, interaction: AluInteraction) -> None:
        """\N{GREEN APPLE} Show a list of your favourite League of Legends FPC champions."""
        await self.hideout_character_list(interaction)

    # Utilities to debug some rare situations.

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command()
    async def meraki(self, interaction: AluInteraction) -> None:
        """Show list of champions that are missing from Meraki JSON."""
        embed = (
            discord.Embed(
                color=const.Color.league,
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

    # LEAGUE DATABASE COMMANDS

    database_lol = app_commands.Group(
        name="database-lol-dev",
        description="Group command about managing League players/accounts in the bot's FPC database.",
        guild_ids=[const.Guild.hideout],
    )

    @database_lol.command(name="add")
    async def database_lol_add(
        self, interaction: AluInteraction, name: str, platform: Platform, in_game_name: str, tag_line: str
    ) -> None:
        """\N{PEACH} Add League player to the FPC database.

        Parameters
        ----------
        name: str
            Player name. if it's a twitch streamer then it should match their twitch handle.
        platform: Platform
            Server where the account is from, i.e. "KR", "NA", "EUW".
        in_game_name: str
            Riot ID name (without a hashtag or a tag), i.e. "Hide on bush", "Sneaky".
        tag_line: str
            Riot ID tag line (characters after a hashtag), i.e. "KR1", "NA69".

        """
        player_arguments = LeagueRequestPlayerArguments(
            name=name, platform=platform, in_game_name=in_game_name, tag_line=tag_line, is_twitch_streamer=True
        )
        await self.database_add(interaction, player_arguments)

    @database_lol.command(name="remove")
    async def database_lol_remove(self, interaction: AluInteraction, player_name: str) -> None:
        """\N{PEACH} Remove League account/player from the FPC database.

        Parameters
        ----------
        player_name: str
            Player Name to find accounts from the database for.
        """
        await self.database_remove(interaction, player_name)

    @database_lol_remove.autocomplete("player_name")
    async def database_lol_remove_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/database lol remove` command.

        Includes all pro-players/streamers in the League FPC database.
        """
        return await self.database_remove_autocomplete(interaction, current)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(LolFPCSettings(bot))
