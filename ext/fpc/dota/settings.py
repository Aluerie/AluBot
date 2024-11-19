from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from steam import ID, InvalidID  # VALVE_SWITCH

# from steam.steamid import EType, SteamID
from utils import const
from utils.dota import Hero, HeroTransformer  # noqa: TCH001

from ..base_classes import Account, BaseSettings

if TYPE_CHECKING:
    from bot import AluBot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DotaPlayerCandidate(NamedTuple):
    name: str
    steam: str
    twitch: bool


class DotaAccountDict(TypedDict):
    steam_id: int
    friend_id: int


class DotaAccount(Account):
    if TYPE_CHECKING:
        steam_id: int
        friend_id: int

    @override  # VALVE_SWITCH
    async def set_game_specific_attrs(self, bot: AluBot, player: DotaPlayerCandidate) -> None:
        try:
            steam_id = ID(player.steam)
        except InvalidID:
            steam_id = await ID.from_url(player.steam, session=bot.session)

        if steam_id is None:
            msg = (
                f"Error checking steam profile for {player.steam}.\n"
                "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
                "or just give steam profile link to the bot."
            )
            raise commands.BadArgument(msg)

        self.steam_id = steam_id.id64
        self.friend_id = steam_id.id  # also known as id32

    # @override
    # async def set_game_specific_attrs(self, _: AluBot, player: DotaPlayerCandidate) -> None:
    #     steam_id_obj = SteamID(player.steam)
    #     if steam_id_obj.type != EType.Individual:
    #         steam_id_obj = SteamID.from_url(player.steam)  # type: ignore # ValvePython doesn't care about TypeHints
    #     if steam_id_obj is None or (hasattr(steam_id_obj, "type") and steam_id_obj.type != EType.Individual):
    #         msg = (
    #             f"Error checking steam profile for {player.steam}.\n"
    #             "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
    #             "or just give steam profile link to the bot."
    #         )
    #         raise commands.BadArgument(msg)

    #     self.steam_id = steam_id_obj.as_64
    #     self.friend_id = steam_id_obj.id

    @property
    @override
    def hint_database_add_command_args(self) -> str:
        return f"name: {self.player_display_name} steam: {self.friend_id} twitch: {self.is_twitch_streamer}"

    @override
    @staticmethod
    def static_account_name_with_links(steam_id: int, friend_id: int) -> str:
        return (
            f"`{steam_id}` - `{friend_id}`| "
            f"[Steam](https://steamcommunity.com/profiles/{steam_id})"
            f"/[Dotabuff](https://www.dotabuff.com/players/{friend_id})"
        )

    @property
    @override
    def account_string_with_links(self) -> str:
        return self.static_account_name_with_links(self.steam_id, self.friend_id)

    @override
    @staticmethod
    def static_account_string(friend_id: int, **kwargs: Any) -> str:
        return f"{friend_id}"

    @property
    @override
    def account_string(self) -> str:
        return self.static_account_string(self.friend_id)

    @override
    def to_pseudo_record(self) -> DotaAccountDict:
        return {
            "steam_id": self.steam_id,
            "friend_id": self.friend_id,
        }


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
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        bot.instantiate_dota()
        super().__init__(
            bot,
            *args,
            prefix="dota",
            colour=const.Colour.blueviolet,
            game_display_name="Dota 2",
            game_icon_url=const.Logo.Dota,
            character_singular="hero",
            character_plural="heroes",
            account_cls=DotaAccount,
            account_typed_dict_cls=DotaAccountDict,
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
    async def dota_request_player(
        self, interaction: discord.Interaction[AluBot], name: str, steam: str, twitch: bool
    ) -> None:
        """\N{LEMON} Request Dota 2 Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.

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
        await self.request_player(interaction, player_tuple)

    dota_setup = app_commands.Group(
        name="setup",
        description="Manage FPC feature settings in your server with those commands..",
        parent=dota_group,
    )

    @dota_setup.command(name="channel")
    async def dota_setup_channel(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC Notifications channel."""
        await self.setup_channel(interaction)

    @dota_setup.command(name="heroes")
    async def dota_setup_heroes(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC favourite heroes list."""
        await self.setup_characters(interaction)

    @dota_setup.command(name="players")
    async def dota_setup_players(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{LEMON} Setup/manage your Dota 2 FPC favourite players list."""
        await self.setup_players(interaction)

    @dota_setup.command(name="miscellaneous")
    async def dota_setup_misc(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{LEMON} Manage your Dota 2 FPC misc settings."""
        await self.setup_misc(interaction)

    @dota_group.command(name="tutorial")
    async def dota_tutorial(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{LEMON} Guide to setup Dota 2 FPC Notifications."""
        await self.tutorial(interaction)

    # HIDEOUT ONLY COMMANDS (at least, at the moment)

    hideout_dota_group = app_commands.Group(
        name="dotafpc",  # cspell: ignore dotafpc
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        guild_ids=[const.Guild.hideout],
    )

    hideout_dota_player = app_commands.Group(
        name="player",  # cspell: ignore dotafpc
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        parent=hideout_dota_group,
    )

    @hideout_dota_player.command(name="add")
    async def hideout_dota_player_add(self, interaction: discord.Interaction[AluBot], player: str) -> None:
        """\N{RED APPLE} Add a Dota 2 player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions exclude your favourite players.
        """
        await self.hideout_player_add(interaction, player)

    @hideout_dota_player_add.autocomplete("player")
    async def hideout_dota_player_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_dota_player.command(name="remove")
    async def hideout_dota_player_remove(self, interaction: discord.Interaction[AluBot], player: str) -> None:
        """\N{RED APPLE} Remove a Dota 2 player into your favourite FPC players list.

        Parameters
        ----------
        player
            Player Name. Autocomplete suggestions include only your favourite players.
        """
        await self.hideout_player_remove(interaction, player)

    @hideout_dota_player_remove.autocomplete("player")
    async def hideout_dota_player_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    hideout_dota_hero = app_commands.Group(
        name="hero",  # cspell: ignore dotafpc
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        parent=hideout_dota_group,
    )

    @hideout_dota_hero.command(name="add")
    async def hideout_dota_hero_add(
        self, interaction: discord.Interaction[AluBot], hero: app_commands.Transform[Hero, HeroTransformer]
    ) -> None:
        """\N{RED APPLE} Add a Dota 2 hero into your favourite FPC heroes list.

        Parameters
        ----------
        hero
            Hero Name. Autocomplete suggestions exclude your favourite champs.
        """
        await self.hideout_character_add(interaction, hero)

    # @hideout_dota_hero_add.autocomplete("hero_name")
    # async def hideout_dota_hero_add_autocomplete(
    #     self, interaction: discord.Interaction[AluBot], current: str
    # ) -> list[app_commands.Choice[str]]:
    #     return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_dota_hero.command(name="remove")
    async def hideout_dota_hero_remove(
        self, interaction: discord.Interaction[AluBot], hero: app_commands.Transform[Hero, HeroTransformer]
    ) -> None:
        """\N{RED APPLE} Remove a Dota 2 hero into your favourite FPC heroes list.

        Parameters
        ----------
        hero
            Hero Name. Autocomplete suggestions only include your favourite champs.
        """
        await self.hideout_character_remove(interaction, hero)

    # @hideout_dota_hero_remove.autocomplete("hero_name")
    # async def hideout_dota_hero_remove_autocomplete(
    #     self, interaction: discord.Interaction[AluBot], current: str
    # ) -> list[app_commands.Choice[str]]:
    #     return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_dota_player.command(name="list")
    async def hideout_dota_player_list(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{RED APPLE} Show a list of your favourite Dota 2 FPC players."""
        await self.hideout_player_list(interaction)

    @hideout_dota_hero.command(name="list")
    async def hideout_dota_hero_list(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{RED APPLE} Show a list of your favourite Dota 2 FPC heroes."""
        await self.hideout_character_list(interaction)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DotaFPCSettings(bot))
