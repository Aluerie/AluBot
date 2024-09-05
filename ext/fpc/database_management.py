from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import checks, errors, lol

from ._base import FPCCog

if TYPE_CHECKING:
    import discord
    from discord import app_commands

    from bot import AluBot, AluGuildContext

    from .dota import DotaFPC
    from .lol import LolFPC

# common flag descriptions
NAME_FLAG_DESC = "Player name. if it's a twitch streamer then it should match their twitch handle."
TWITCH_FLAG_DESC = "Is this person a twitch.tv streamer (under same name)?"

# Dota 2 flag descriptions
STEAM_FLAG_DESC = "Steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link."

# League of Legends flag descriptions
SERVER_FLAG_DESC = 'Server where the account is from, i.e. "KR", "NA", "EUW".'
GAME_NAME_FLAG_DESC = 'Riot ID name (without a hashtag or a tag), i.e. "Hide on bush", "Sneaky".'
TAG_LINE_FLAG_DESC = 'Riot ID tag line (characters after a hashtag), i.e. "KR1", "NA69".'

# Note that all classes below should implement .name attribute
# Since our FPCAccount depends on the assumption that it exists.


class AddDotaPlayerFlags(commands.FlagConverter):
    name: str = commands.flag(description=NAME_FLAG_DESC)
    steam: str = commands.flag(description=STEAM_FLAG_DESC)
    twitch: bool = commands.flag(description=TWITCH_FLAG_DESC)


class RemoveDotaPlayerFlags(commands.FlagConverter):
    name: str | None = commands.flag(description=NAME_FLAG_DESC, default=None)
    steam: str | None = commands.flag(description=STEAM_FLAG_DESC, default=None)


class AddLoLPlayerFlags(commands.FlagConverter):
    name: str = commands.flag(description=NAME_FLAG_DESC)
    platform: lol.Platform = commands.flag(name="server", description=SERVER_FLAG_DESC, converter=lol.PlatformConverter)
    game_name: str = commands.flag(description=GAME_NAME_FLAG_DESC)
    tag_line: str = commands.flag(description=TAG_LINE_FLAG_DESC)


class RemoveLoLPlayerFlags(commands.FlagConverter):
    name: str | None = commands.flag(description=NAME_FLAG_DESC, default=None)


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

    @checks.hybrid.is_hideout()
    @commands.hybrid_group()
    async def database(self, ctx: AluGuildContext) -> None:
        """Group command about managing players/accounts bot's FPC database."""
        await ctx.send_help()

    @database.group(name="dota")
    async def database_dota(self, ctx: AluGuildContext) -> None:
        """Group command about managing Dota 2 players/accounts in the bot's FPC database."""
        await ctx.send_help()

    @property
    def dota_fpc_settings_cog(self) -> DotaFPC:
        """Get Dota 2 FPC Settings Cog."""
        return self.get_fpc_settings_cog("Dota 2 FPC")  # type: ignore

    @database_dota.command(name="add")
    async def database_dota_add(self, ctx: AluGuildContext, *, flags: AddDotaPlayerFlags) -> None:
        """Add Dota 2 player to the FPC database."""
        await self.dota_fpc_settings_cog.database_add(ctx, flags)

    @database_dota.command(name="remove")
    async def database_dota_remove(self, ctx: AluGuildContext, player_name: str) -> None:
        """Remove Dota 2 account/player from the database."""
        await self.dota_fpc_settings_cog.database_remove(ctx, player_name)

    @database_dota_remove.autocomplete("player_name")
    async def database_dota_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.dota_fpc_settings_cog.database_remove_autocomplete(interaction, current)

    @database.group(name="lol")
    async def database_lol(self, ctx: AluGuildContext) -> None:
        """Group command about managing LoL 2 players/accounts in the bot's FPC database."""
        await ctx.send_help()

    @property
    def lol_fpc_settings_cog(self) -> LolFPC:
        """Get LoL FPC Settings Cog."""
        return self.get_fpc_settings_cog("League of Legends FPC")  # type: ignore

    @database_lol.command(name="add")
    async def database_lol_add(self, ctx: AluGuildContext, *, flags: AddLoLPlayerFlags) -> None:
        """Add LoL player to the FPC database."""
        await self.lol_fpc_settings_cog.database_add(ctx, flags)

    @database_lol.command(name="remove")
    async def database_lol_remove(self, ctx: AluGuildContext, player_name: str) -> None:
        """Remove LoL account/player from the FPC database."""
        await self.lol_fpc_settings_cog.database_remove(ctx, player_name)

    @database_lol_remove.autocomplete("player_name")
    async def database_lol_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.lol_fpc_settings_cog.database_remove_autocomplete(interaction, current)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FPCDatabaseManagement(bot))
