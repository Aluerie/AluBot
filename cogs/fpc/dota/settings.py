from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from steam.steamid import EType, SteamID

from utils.const import Colour, Emote
from utils.dota import hero
from utils.dota.const import DOTA_LOGO

from .._fpc_utils._base import FPCBase

if TYPE_CHECKING:
    from utils import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AddDotaPlayerFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    steam: str
    twitch: bool


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: Optional[str]
    steam: Optional[str]


class DotaNotifsSettings(commands.Cog, FPCBase, name="Dota 2"):
    """Commands to set up fav hero + player notifs.

    These commands allow you to choose players from our database as your favorite \
    (or you can request adding them if missing) and choose your favorite Dota 2 heroes. \
    The bot will send messages in a chosen channel when your fav player picks your fav hero.

    **Tutorial**
    1. Set channel with
    `$dota channel set #channel`
    2. Add players to your favourites, i.e.
    `$dota player add gorgc, bzm`
    List of available players can be seen with `$dota database list`
    3. Request missing players to the database , i.e.
    `/dota database request name: cr1tdota steam: 76561197986172872 twitch: yes`
    4. Add heroes to your favourites, i.e.
    `/dota hero add name1: Dark Willow name2: Mirana name3: Anti-Mage`
    5. Use `remove` counterpart commands to `add` to edit out player/hero lists
    *Pro-Tip.* Use autocomplete
    6. Ready ! More info below
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name="DotaFeed",
            game_name="Dota 2",
            game_codeword="dota",
            game_logo=DOTA_LOGO,
            colour=Colour.prpl(),
            bot=bot,
            players_table="dota_players",
            accounts_table="dota_accounts",
            channel_id_column="dotafeed_ch_id",
            players_column="dotafeed_stream_ids",
            characters_column="dotafeed_hero_ids",
            spoil_column="dotafeed_spoils_on",
            acc_info_columns=["friend_id"],
            get_char_id_by_name=hero.id_by_name,
            get_char_name_by_id=hero.name_by_id,
            get_all_character_names=hero.get_all_hero_names,
            character_gather_word="heroes",
        )
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()
        return await super().cog_load()

    # dota ##############################################

    dota = app_commands.Group(
        name="dota",
        description="Group command about DotaFeed",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    dota_channel = app_commands.Group(
        name="channel",
        description="Group command about DotaFeed channel settings",
        parent=dota,
    )

    @dota_channel.command(name="set")
    @app_commands.describe(channel="channel to set up DotaFeed notifications")
    async def dota_channel_set(self, ntr: discord.Interaction[AluBot], channel: Optional[discord.TextChannel]):
        """Set channel to be the DotaFeed notifications channel."""
        await self.channel_set(ntr, channel)

    @dota_channel.command(name="disable")
    async def dota_channel_disable(self, ntr: discord.Interaction[AluBot]):
        """Disable DotaFeed notifications channel. Data won't be affected."""
        await self.channel_disable(ntr)

    @dota_channel.command(name="check")
    async def dota_channel_check(self, ntr: discord.Interaction[AluBot]):
        """Check if DotaFeed channel is set up."""
        await self.channel_check(ntr)

    dota_database = app_commands.Group(
        name="database",
        description="Group command about DotaFeed database",
        parent=dota,
    )

    @staticmethod
    def cmd_usage_str(**kwargs):
        friend_id = kwargs.pop("friend_id")
        twitch = bool(kwargs.pop("twitch_id"))
        return f"steam: {friend_id} twitch: {twitch}"

    @staticmethod
    def player_acc_string(**kwargs):
        steam_id = kwargs.pop("id")
        friend_id = kwargs.pop("friend_id")
        return (
            f"`{steam_id}` - `{friend_id}`| "
            f"[Steam](https://steamcommunity.com/profiles/{steam_id})"
            f"/[Dotabuff](https://www.dotabuff.com/players/{friend_id})"
        )

    @staticmethod
    def get_steam_id_and_64(steam_string: str):
        steam_acc = SteamID(steam_string)
        if steam_acc.type != EType.Individual:
            steam_acc = SteamID.from_url(steam_string)  # type: ignore # ValvePython does not care much about TypeHints

        if steam_acc is None or (hasattr(steam_acc, "type") and steam_acc.type != EType.Individual):
            raise commands.BadArgument(
                "Error checking steam profile for {steam}.\n"
                "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
                "or just give steam profile link to the bot."
            )
        return steam_acc.as_64, steam_acc.id

    async def get_account_dict(self, *, steam_flag: str) -> dict:
        steam_id, friend_id = self.get_steam_id_and_64(steam_flag)
        return {"id": steam_id, "friend_id": friend_id}

    @dota_database.command(name="list")
    async def dota_database_list(self, ntr: discord.Interaction[AluBot]):
        """List of players in the database available for DotaFeed feature."""
        await self.database_list(ntr)

    @dota_database.command(name="request")
    async def dota_database_request(self, ntr: discord.Interaction[AluBot], name: str, steam: str, twitch: bool):
        """Request player to be added into the database.

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

        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=twitch)
        account_dict = await self.get_account_dict(steam_flag=steam)
        await self.database_request(ntr, player_dict, account_dict)

    dota_player = app_commands.Group(
        name="player",
        description="Group command about DotaFeed player",
        parent=dota,
    )

    async def player_add_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=True)

    @dota_player.command(name="add")
    @app_commands.describe(
        **{
            f"name{i}": "Name of a player. Suggestions from database above exclude your already fav players"
            for i in range(1, 11)
        }
    )
    @app_commands.autocomplete(
        name1=player_add_autocomplete,
        name2=player_add_autocomplete,
        name3=player_add_autocomplete,
        name4=player_add_autocomplete,
        name5=player_add_autocomplete,
        name6=player_add_autocomplete,
        name7=player_add_autocomplete,
        name8=player_add_autocomplete,
        name9=player_add_autocomplete,
        name10=player_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_add_autocomplete for i in range(1, 11)})
    async def dota_player_add(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Add player to your favourites."""
        await self.player_add_remove(ntr, locals(), mode_add=True)

    async def player_remove_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=False)

    @dota_player.command(name="remove")
    @app_commands.describe(**{f"name{i}": "Name of a player" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=player_remove_autocomplete,
        name2=player_remove_autocomplete,
        name3=player_remove_autocomplete,
        name4=player_remove_autocomplete,
        name5=player_remove_autocomplete,
        name6=player_remove_autocomplete,
        name7=player_remove_autocomplete,
        name8=player_remove_autocomplete,
        name9=player_remove_autocomplete,
        name10=player_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_remove_autocomplete for i in range(1, 11)})
    async def dota_player_remove(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Remove player from your favourites."""
        await self.player_add_remove(ntr, locals(), mode_add=False)

    @dota_player.command(name="list")
    async def dota_player_list(self, ntr: discord.Interaction[AluBot]):
        """Show list of your favourite players."""
        await self.player_list(ntr)

    dota_hero = app_commands.Group(
        name="hero",
        description="Group command about DotaFeed hero",
        parent=dota,
    )

    async def hero_add_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=True)

    @dota_hero.command(name="add")
    @app_commands.describe(**{f"name{i}": "Name of a hero" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=hero_add_autocomplete,
        name2=hero_add_autocomplete,
        name3=hero_add_autocomplete,
        name4=hero_add_autocomplete,
        name5=hero_add_autocomplete,
        name6=hero_add_autocomplete,
        name7=hero_add_autocomplete,
        name8=hero_add_autocomplete,
        name9=hero_add_autocomplete,
        name10=hero_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': hero_add_autocomplete for i in range(1, 11)})
    async def slh_dota_hero_add(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Add hero to your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=True)

    async def hero_remove_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=False)

    @dota_hero.command(name="remove")
    @app_commands.describe(**{f"name{i}": "Name of a hero" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=hero_remove_autocomplete,
        name2=hero_remove_autocomplete,
        name3=hero_remove_autocomplete,
        name4=hero_remove_autocomplete,
        name5=hero_remove_autocomplete,
        name6=hero_remove_autocomplete,
        name7=hero_remove_autocomplete,
        name8=hero_remove_autocomplete,
        name9=hero_remove_autocomplete,
        name10=hero_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': hero_add_autocomplete for i in range(1, 11)})
    async def slh_dota_hero_remove(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Remove hero from your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=False)

    @dota_hero.command(name="list")
    async def dota_hero_list(self, ntr: discord.Interaction[AluBot]):
        """Show your favourite heroes list."""
        await self.character_list(ntr)

    @dota.command(name="spoil")
    @app_commands.describe(spoil="`True` to enable spoiling with stats, `False` for disable")
    async def dota_spoil(self, ntr: discord.Interaction[AluBot], spoil: bool):
        """Turn on/off spoiling resulting stats for matches."""
        await self.spoil(ntr, spoil)


async def setup(bot: AluBot):
    await bot.add_cog(DotaNotifsSettings(bot))
