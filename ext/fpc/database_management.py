from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from discord import app_commands
from discord.ext import commands

from utils import const, errors
from utils.lol import Platform  # noqa: TCH001

from .base_classes import FPCCog
from .dota.settings import DotaPlayerCandidate
from .lol.settings import LolPlayerCandidate

if TYPE_CHECKING:
    import discord

    from bot import AluBot, Timer

    from .dota import DotaFPC
    from .lol import LolFPC

    class CheckAccRenamesQueryRow(TypedDict):
        player_id: int
        twitch_id: int
        display_name: str


# # common flag descriptions
# NAME_FLAG_DESC = "Player name. if it's a twitch streamer then it should match their twitch handle."
# TWITCH_FLAG_DESC = "Is this person a twitch.tv streamer (under same name)?"

# # Dota 2 flag descriptions
# STEAM_FLAG_DESC = "Steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link."

# # League of Legends flag descriptions
# SERVER_FLAG_DESC = ""
# GAME_NAME_FLAG_DESC = ""
# TAG_LINE_FLAG_DESC = ""

# # Note that all classes below should implement .name attribute
# # Since our FPCAccount depends on the assumption that it exists.


# class AddDotaPlayerFlags(commands.FlagConverter):
#     name: str = commands.flag(description=NAME_FLAG_DESC)
#     steam: str = commands.flag(description=STEAM_FLAG_DESC)
#     twitch: bool = commands.flag(description=TWITCH_FLAG_DESC)


# class RemoveDotaPlayerFlags(commands.FlagConverter):
#     name: str | None = commands.flag(description=NAME_FLAG_DESC, default=None)
#     steam: str | None = commands.flag(description=STEAM_FLAG_DESC, default=None)


# class AddLoLPlayerFlags(commands.FlagConverter):
#     name: str = commands.flag(description=NAME_FLAG_DESC)
#     platform: Platform = commands.flag(name="server", description=SERVER_FLAG_DESC, converter=PlatformConverter)
#     game_name: str = commands.flag(description=GAME_NAME_FLAG_DESC)
#     tag_line: str = commands.flag(description=TAG_LINE_FLAG_DESC)


# class RemoveLoLPlayerFlags(commands.FlagConverter):
#     name: str | None = commands.flag(description=NAME_FLAG_DESC, default=None)


class FPCDatabaseManagement(FPCCog):
    """FPC Database Management.

    Commands for bot owner(-s) to add/remove player accounts from the FPC database.
    """

    def get_fpc_settings_cog(self, cog_name: str) -> FPCCog:
        """Get FPC Settings Cog."""
        fpc_settings_cog: FPCCog | None = self.bot.get_cog(cog_name)  # type:ignore
        if fpc_settings_cog is None:
            msg = f"Cog `{cog_name}` is not loaded."
            raise errors.ErroneousUsage(msg)
        return fpc_settings_cog

    database_group = app_commands.Group(
        name="database",
        description="Group command about managing players/accounts bot's FPC database.",
        guild_ids=[const.Guild.hideout],
    )

    database_dota = app_commands.Group(
        name="dota",
        description="Group command about managing Dota 2 players/accounts in the bot's FPC database.",
        parent=database_group,
    )

    @property
    def dota_fpc_settings_cog(self) -> DotaFPC:
        """Get Dota 2 FPC Settings Cog."""
        return self.get_fpc_settings_cog("Dota 2 FPC")  # type: ignore

    @database_dota.command(name="add")
    async def database_dota_add(
        self, interaction: discord.Interaction[AluBot], name: str, steam: str, twitch: bool
    ) -> None:
        """Add Dota 2 player to the FPC database.

        Parameters
        ----------
        name:
            Player name. if it's a twitch streamer then it should match their twitch handle.
        steam:
            Steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch:
            Is this person a twitch.tv streamer (under same name)?
        """
        player_tuple = DotaPlayerCandidate(name=name, steam=steam, twitch=twitch)
        await self.dota_fpc_settings_cog.database_add(interaction, player_tuple)

    @database_dota.command(name="remove")
    async def database_dota_remove(self, interaction: discord.Interaction[AluBot], player_name: str) -> None:
        """Remove Dota 2 account/player from the database."""
        await self.dota_fpc_settings_cog.database_remove(interaction, player_name)

    @database_dota_remove.autocomplete("player_name")
    async def database_dota_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/database dota remove` command.

        Includes all pro players in the Dota 2 FPC database.
        """
        return await self.dota_fpc_settings_cog.database_remove_autocomplete(interaction, current)

    database_lol = app_commands.Group(
        name="lol",
        description="Group command about managing LoL 2 players/accounts in the bot's FPC database.",
        parent=database_group,
    )

    @property
    def lol_fpc_settings_cog(self) -> LolFPC:
        """Get LoL FPC Settings Cog."""
        return self.get_fpc_settings_cog("League of Legends FPC")  # type: ignore

    @database_lol.command(name="add")
    async def database_lol_add(
        self,
        interaction: discord.Interaction[AluBot],
        name: str,
        platform: Platform,
        game_name: str,
        tag_line: str,
    ) -> None:
        """Add LoL player to the FPC database.

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
        await self.lol_fpc_settings_cog.database_add(interaction, player_tuple)

    @database_lol.command(name="remove")
    async def database_lol_remove(self, interaction: discord.Interaction[AluBot], player_name: str) -> None:
        """Remove LoL account/player from the FPC database."""
        await self.lol_fpc_settings_cog.database_remove(interaction, player_name)

    @database_lol_remove.autocomplete("player_name")
    async def database_lol_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/database lol remove` command.

        Includes all pro-players/streamers in the League FPC database.
        """
        return await self.lol_fpc_settings_cog.database_remove_autocomplete(interaction, current)

    @commands.Cog.listener("on_fpc_twitch_renames_check_timer_complete")
    async def check_twitch_accounts_renames(self, timer: Timer) -> None:
        """Checks if people in FPC database renamed themselves on twitch.tv.

        I think we're using twitch ids everywhere so this timer is more for convenience matter
        when I'm browsing the database, but still.
        """
        for table_name in ("dota_players", "lol_players"):
            query = f"SELECT player_id, twitch_id, display_name FROM {table_name} WHERE twitch_id IS NOT NULL"
            rows: list[CheckAccRenamesQueryRow] = await self.bot.pool.fetch(query)

            for row in rows:
                # todo: wtf fetch only one user ?!
                user = next(iter(await self.bot.twitch.fetch_users(ids=[row["twitch_id"]])), None)

                if user is None:
                    continue
                elif user.display_name != row["display_name"]:
                    query = f"UPDATE {table_name} SET display_name=$1 WHERE player_id=$3"
                    await self.bot.pool.execute(query, user.display_name, row["player_id"])
        # TODO: periodic timer - create a new one
        # TODO: maybe standardize the process of periodic timers
        # TODO: remove twitch_check from other folders
        # TODO: check if it's possible to fire a timer before cogs load in


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FPCDatabaseManagement(bot))
