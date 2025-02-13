from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, override

import discord
from discord import app_commands
from discord.ext import commands
from steam import ID, InvalidID

from utils import const
from utils.dota import Hero, HeroTransformer  # noqa: TC001

from ..base_classes import BaseAccount, BasePlayer, BaseRequestPlayerArguments, BaseSettings

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@dataclass
class DotaRequestPlayerArguments(BaseRequestPlayerArguments):
    """Arguments for the following slash commands.

    * /dota request player
    * /database-dota-dev add
    """

    steam: str


@dataclass
class DotaAccount(BaseAccount):
    """Dota 2 Account."""

    steam_id: int
    friend_id: int

    @override
    @classmethod
    async def create(cls, bot: AluBot, arguments: DotaRequestPlayerArguments) -> Self:
        try:
            steam_id = ID(arguments.steam)
        except InvalidID:
            steam_id = await ID.from_url(arguments.steam, session=bot.session)

        if steam_id is None:
            msg = (
                f"Error checking steam profile for `{arguments.steam}`.\n"
                "Check if your `steam` flag is a correct SteamID in either 64/32/3/2/friend_id representations "
                "or just give their steam profile link to the bot."
            )
            raise commands.BadArgument(msg)

        return cls(steam_id.id64, steam_id.id)

    @override
    def links(self) -> str:
        return (
            f"`{self.steam_id}` - `{self.friend_id}`| "
            f"[Steam](https://steamcommunity.com/profiles/{self.steam_id})"
            f"/[Dotabuff](https://www.dotabuff.com/players/{self.friend_id})"
        )

    @property
    @override
    def display_name(self) -> str:
        return str(self.friend_id)


class DotaPlayer(BasePlayer[DotaAccount]):
    """Dota 2 Player."""

    @override
    def hint_database_add_command_arguments(self) -> str:
        return f"name: {self.display_name} steam: {self.account.friend_id} twitch: {bool(self.twitch_id)}"


class DotaFPCSettings(BaseSettings, name="Dota 2"):
    """Commands to set up fav hero + player notifications.

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
    """  # cSpell: ignore tdota

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        bot.instantiate_dota()
        super().__init__(
            bot,
            *args,
            prefix="dota",
            colour=const.Colour.prpl,
            game_display_name="Dota 2",
            game_icon_url=const.Logo.Dota,
            character_singular="hero",
            character_plural="heroes",
            player_cls=DotaPlayer,
            characters=bot.dota.heroes,
            **kwargs,
        )

    dota_group = app_commands.Group(
        name="dota",
        description="Dota 2 FPC (Favourite Player+Character) commands.",
        guild_ids=const.PREMIUM_GUILDS,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    dota_request = app_commands.Group(
        name="request",
        description="Dota 2 FPC (Favourite Player+Character) request commands.",
        parent=dota_group,
    )

    @dota_request.command(name="player")
    async def dota_request_player(self, interaction: AluInteraction, name: str, steam: str, *, twitch: bool) -> None:
        """\N{LEMON} Request Dota 2 Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.

        Parameters
        ----------
        name
            Player name. if it's a twitch streamer then it should match their twitch handle.
        steam
            Steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch
            Is this person a twitch.tv streamer (under same name)?
        """
        player_arguments = DotaRequestPlayerArguments(name=name, steam=steam, is_twitch_streamer=twitch)
        await self.request_player(interaction, player_arguments)

    dota_setup = app_commands.Group(
        name="setup",
        description="Manage FPC feature settings in your server with those commands..",
        parent=dota_group,
    )

    @dota_setup.command(name="channel")
    async def dota_setup_channel(self, interaction: AluInteraction) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC Notifications channel."""
        await self.setup_channel(interaction)

    @dota_setup.command(name="heroes")
    async def dota_setup_heroes(self, interaction: AluInteraction) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC favourite heroes list."""
        await self.setup_characters(interaction)

    @dota_setup.command(name="players")
    async def dota_setup_players(self, interaction: AluInteraction) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC favourite players list."""
        await self.setup_players(interaction)

    @dota_setup.command(name="miscellaneous")
    async def dota_setup_misc(self, interaction: AluInteraction) -> None:
        """\N{LEMON} Manage your Dota 2 FPC misc settings."""
        await self.setup_misc(interaction)

    @dota_group.command(name="tutorial")
    async def dota_tutorial(self, interaction: AluInteraction) -> None:
        """\N{LEMON} Guide to setup Dota 2 FPC Notifications."""
        await self.tutorial(interaction)

    # HIDEOUT ONLY COMMANDS (at least, at the moment)

    hideout_dota_group = app_commands.Group(
        name="dota-dev",
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        guild_ids=[const.Guild.hideout],
    )

    hideout_dota_player = app_commands.Group(
        name="player",
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        parent=hideout_dota_group,
    )

    @hideout_dota_player.command(name="add")
    async def hideout_dota_player_add(self, interaction: AluInteraction, player: str) -> None:
        """\N{RED APPLE} Add a Dota 2 player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions exclude your favourite players.
        """
        await self.hideout_player_add(interaction, player)

    @hideout_dota_player_add.autocomplete("player")
    async def hideout_dota_player_add_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/dota-dev player add` command.

        Suggests players from the Dota 2 FPC database that the current guild hasn't subscribed to.
        """
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_dota_player.command(name="remove")
    async def hideout_dota_player_remove(self, interaction: AluInteraction, player: str) -> None:
        """\N{RED APPLE} Remove a Dota 2 player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions include only your favourite players.
        """
        await self.hideout_player_remove(interaction, player)

    @hideout_dota_player_remove.autocomplete("player")
    async def hideout_dota_player_remove_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/database dota remove` command.

        Suggests pro players in the Dota 2 FPC database that the current guild subscribed to.
        """
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    hideout_dota_hero = app_commands.Group(
        name="hero",
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        parent=hideout_dota_group,
    )

    @hideout_dota_hero.command(name="add")
    async def hideout_dota_hero_add(
        self, interaction: AluInteraction, hero: app_commands.Transform[Hero, HeroTransformer]
    ) -> None:
        """\N{RED APPLE} Add a Dota 2 hero into your favourite FPC heroes list.

        Parameters
        ----------
        hero: Hero
            Hero Name. Autocomplete suggestions exclude your favourite champs.
        """
        await self.hideout_character_add(interaction, hero)

    @hideout_dota_hero.command(name="remove")
    async def hideout_dota_hero_remove(  # TODO: should autocomplete for hero only include heroes we have in the thing?
        self, interaction: AluInteraction, hero: app_commands.Transform[Hero, HeroTransformer]
    ) -> None:
        """\N{RED APPLE} Remove a Dota 2 hero into your favourite FPC heroes list.

        Parameters
        ----------
        hero: Hero
            Hero Name. Autocomplete suggestions only include your favourite champs.
        """
        await self.hideout_character_remove(interaction, hero)

    @hideout_dota_player.command(name="list")
    async def hideout_dota_player_list(self, interaction: AluInteraction) -> None:
        """\N{RED APPLE} Show a list of your favourite Dota 2 FPC players."""
        await self.hideout_player_list(interaction)

    @hideout_dota_hero.command(name="list")
    async def hideout_dota_hero_list(self, interaction: AluInteraction) -> None:
        """\N{RED APPLE} Show a list of your favourite Dota 2 FPC heroes."""
        await self.hideout_character_list(interaction)

    # DOTA DATABASE COMMANDS

    database_dota = app_commands.Group(
        name="database-dota-dev",
        description="Group command about managing Dota 2 players/accounts in the bot's FPC database.",
        guild_ids=[const.Guild.hideout],
    )

    @database_dota.command(name="add")
    async def database_dota_add(self, interaction: AluInteraction, name: str, steam: str, *, twitch: bool) -> None:
        """\N{TANGERINE} Add Dota 2 player to the FPC database.

        Parameters
        ----------
        name: str
            Player name. if it's a twitch streamer then it should match their twitch handle.
        steam: str
            Steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch: bool
            Is this person a twitch.tv streamer (under same name)?

        """
        player_arguments = DotaRequestPlayerArguments(name=name, steam=steam, is_twitch_streamer=twitch)
        await self.database_add(interaction, player_arguments)

    @database_dota.command(name="remove")
    async def database_dota_remove(self, interaction: AluInteraction, player_name: str) -> None:
        """\N{TANGERINE} Show menu with buttons to remove Dota 2 account/player from the database.

        Parameters
        ----------
        player_name: str
            Player Name to find accounts from the database for.
        """
        await self.database_remove(interaction, player_name)

    @database_dota_remove.autocomplete("player_name")
    async def database_dota_remove_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for `/database dota remove` command.

        Includes all pro players in the Dota 2 FPC database.
        """
        return await self.database_remove_autocomplete(interaction, current)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DotaFPCSettings(bot))
