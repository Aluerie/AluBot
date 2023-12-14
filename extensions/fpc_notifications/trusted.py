from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, const
from utils.lol.const import LiteralServerUpper

from ._base import FPCCog

if TYPE_CHECKING:
    from bot import AluBot

    from .dota.settings import DotaNotifsSettings
    from .lol.settings import LoLNotifsSettings


class FPCTrusted(FPCCog):
    database = app_commands.Group(
        name="database",
        description="Group command about managing database",
        guild_ids=const.TRUSTED_GUILDS,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    db_dota = app_commands.Group(
        name="dota",
        description="Group command about managing Dota 2 database",
        parent=database,
    )

    def get_dota_tools_cog(self) -> DotaNotifsSettings:
        """Get dota tools cog"""
        dota_cog: Optional[DotaNotifsSettings] = self.bot.get_cog("Dota2FPC")  # type:ignore
        if dota_cog is None:
            # todo: sort this out when we gonna do error handler refactor
            raise commands.ExtensionNotLoaded(name="Dota 2 Cog is not loaded")
        return dota_cog

    @checks.hybrid.is_trustee()
    @db_dota.command(name="add")
    async def db_dota_add(self, ntr: discord.Interaction[AluBot], name: str, steam: str, twitch: bool):
        """Add player to the database.

        Parameters
        ----------
        ntr: discord.Interaction
        name:
            Player name. If it is a twitch tv streamer then provide their twitch handle.
        steam:
            Steamid in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch:
            If you proved twitch handle for "name" then press `True` otherwise `False`.

        """

        dota_cog = self.get_dota_tools_cog()
        player_dict = await dota_cog.get_player_dict(name_flag=name, twitch_flag=twitch)
        account_dict = await dota_cog.get_account_dict(steam_flag=steam)
        await dota_cog.database_add(ntr, player_dict, account_dict)

    @checks.hybrid.is_trustee()
    @db_dota.command(name="remove")
    async def db_dota_remove(self, ntr: discord.Interaction[AluBot], name: str, steam: Optional[str]):
        """Remove account/player from the database.

        Parameters
        ----------
        ntr :
        name :
            Twitch.tv stream name.
        steam :
            Steam_id in any of 64/32/3/2 versions, friend_id or just Steam profile link.
        """

        dota_cog = self.get_dota_tools_cog()
        if steam:
            steam_id, _ = dota_cog.get_steam_id_and_64(steam)
        else:
            steam_id = None
        await dota_cog.database_remove(ntr, name.lower(), steam_id)

    db_lol = app_commands.Group(
        name="lol",
        description="Group command about managing Dota 2 database",
        parent=database,
    )

    def get_lol_tools_cog(self) -> LoLNotifsSettings:
        """Get lol tools cog"""
        # TODO: you will change the name below - make it more reliable, idk how
        lol_cog: Optional[LoLNotifsSettings] = self.bot.get_cog("LoLFPC")  # type:ignore
        if lol_cog is None:
            # todo: sort this out when we gonna do error handler refactor
            raise commands.ExtensionNotLoaded(name="LoLFPC is not loaded")
        return lol_cog

    @checks.hybrid.is_trustee()
    @db_lol.command(name="add")
    async def db_lol_add(self, ntr: discord.Interaction[AluBot], name: str, server: LiteralServerUpper, account: str):
        """Add player to the database.

        Parameters
        ----------
        ntr: discord.Interaction[AluBot]
        name:
            Twitch.tv player\'s handle
        server:
            Server of the account, i.e. "NA", "EUW"
        account:
            Summoner name of the account
        """

        lol_cog = self.get_lol_tools_cog()
        player_dict = await lol_cog.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await lol_cog.get_account_dict(server=server, account=account)
        await lol_cog.database_add(ntr, player_dict, account_dict)

    @checks.hybrid.is_trustee()
    @db_lol.command(name="remove")
    async def db_lol_remove(
        self, ntr: discord.Interaction[AluBot], name: str, server: Optional[LiteralServerUpper], account: Optional[str]
    ):
        """Remove account/player from the database.

        Parameters
        ----------
        ntr: discord.Interaction[AluBot]
        name:
            Twitch.tv player name
        server:
            Server region of the account
        account:
            Summoner name of the account
        """

        lol_cog = self.get_lol_tools_cog()
        if bool(server) != bool(account):
            raise commands.BadArgument("You need to provide both `server` and `account` to delete the specific account")
        elif server and account:
            # todo: check type str | None for account
            lol_id, _, _ = await lol_cog.get_lol_id(server=server, account=account)
        else:
            lol_id = None
        await lol_cog.database_remove(ntr, name.lower(), lol_id)


async def setup(bot: AluBot):
    await bot.add_cog(FPCTrusted(bot))
