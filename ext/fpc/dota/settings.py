from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from steam.steamid import EType, SteamID

from utils import checks, const, errors

from .._base import Account, BaseSettings

# from steam import ID, InvalidID # VALVE_SWITCH
from ..database_management import AddDotaPlayerFlags  # noqa: TCH001

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DotaAccountDict(TypedDict):
    steam_id: int
    friend_id: int


class DotaAccount(Account):
    if TYPE_CHECKING:
        steam_id: int
        friend_id: int

    # @override #VALVE_SWITCH
    # async def set_game_specific_attrs(self, bot: AluBot, flags: AddDotaPlayerFlags):
    #     try:
    #         steam_id = ID(flags.steam)
    #     except InvalidID:
    #         steam_id = await ID.from_url(flags.steam, session=bot.session)

    #     if steam_id is None:
    #         raise commands.BadArgument(
    #             f"Error checking steam profile for {flags.steam}.\n"
    #             "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
    #             "or just give steam profile link to the bot."
    #         )

    #     self.steam_id = steam_id.id64
    #     self.friend_id = steam_id.id  # also known as id32

    @override
    async def set_game_specific_attrs(self, bot: AluBot, flags: AddDotaPlayerFlags) -> None:
        steam_id_obj = SteamID(flags.steam)
        if steam_id_obj.type != EType.Individual:
            steam_id_obj = SteamID.from_url(flags.steam)  # type: ignore # ValvePython doesn't care about TypeHints
        if steam_id_obj is None or (hasattr(steam_id_obj, "type") and steam_id_obj.type != EType.Individual):
            msg = (
                f"Error checking steam profile for {flags.steam}.\n"
                "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
                "or just give steam profile link to the bot."
            )
            raise commands.BadArgument(msg)

        self.steam_id = steam_id_obj.as_64
        self.friend_id = steam_id_obj.id

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
        bot.initialize_cache_dota()
        super().__init__(
            bot,
            *args,
            prefix="dota",
            colour=const.Colour.blueviolet,
            game_display_name="Dota 2",
            game_icon_url=const.Logo.Dota,
            character_singular_word="hero",
            character_plural_word="heroes",
            account_cls=DotaAccount,
            account_typed_dict_cls=DotaAccountDict,
            character_cache=bot.cache_dota.hero,
            emote_cls=const.DotaHeroes,
            **kwargs,
        )

    @checks.hybrid.is_premium_guild_manager()
    @commands.hybrid_group(name="dota")
    async def dota_group(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) commands."""
        await ctx.send_help()

    @dota_group.group(name="request")
    async def dota_request(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) request commands."""
        await ctx.send_help()

    @dota_request.command(name="player")
    async def dota_request_player(self, ctx: AluGuildContext, *, flags: AddDotaPlayerFlags) -> None:
        """Request Dota 2 Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.
        """
        await self.request_player(ctx, flags)

    @dota_group.group(name="setup")
    async def dota_setup(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) setup commands.

        Manage FPC feature settings in your server with those commands.
        """
        await ctx.send_help()

    @dota_setup.command(name="channel")
    async def dota_setup_channel(self, ctx: AluGuildContext) -> None:
        """Setup/manage your Dota 2 FPC Notifications channel."""
        await self.setup_channel(ctx)

    @dota_setup.command(name="heroes")
    async def dota_setup_heroes(self, ctx: AluGuildContext) -> None:
        """Setup/manage your Dota 2 FPC favourite heroes list."""
        await self.setup_characters(ctx)

    @dota_setup.command(name="players")
    async def dota_setup_players(self, ctx: AluGuildContext) -> None:
        """Setup/manage your Dota 2 FPC favourite players list."""
        await self.setup_players(ctx)

    @dota_setup.command(name="miscellaneous", aliases=["misc"])
    async def dota_setup_misc(self, ctx: AluGuildContext) -> None:
        """Manage your Dota 2 FPC misc settings."""
        await self.setup_misc(ctx)

    @dota_group.command(name="tutorial")
    async def dota_tutorial(self, ctx: AluGuildContext) -> None:
        """Guide to setup Dota 2 FPC Notifications."""
        await self.tutorial(ctx)

    @checks.hybrid.is_hideout()
    @commands.hybrid_group(name="dotafpc")  # cspell: ignore dotafpc
    async def hideout_dota_group(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) Hideout-only commands."""
        await ctx.send_help()

    @hideout_dota_group.group(name="player")
    async def hideout_dota_player(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) Hideout-only player-related commands."""
        await ctx.send_help()

    async def hideout_dota_player_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_dota_player.command(name="add")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions exclude your favourite players.")
    @app_commands.autocomplete(player_name=hideout_dota_player_add_autocomplete)
    async def hideout_dota_player_add(self, ctx: AluGuildContext, player_name: str) -> None:
        """Add a Dota 2 player into your favourite FPC players list."""
        await self.hideout_player_add(ctx, player_name)

    async def hideout_dota_player_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_dota_player.command(name="remove")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions include only your favourite players.")
    @app_commands.autocomplete(player_name=hideout_dota_player_remove_autocomplete)
    async def hideout_dota_player_remove(self, ctx: AluGuildContext, player_name: str) -> None:
        """Remove a Dota 2 player into your favourite FPC players list."""
        await self.hideout_player_remove(ctx, player_name)

    @hideout_dota_group.group(name="hero")
    async def hideout_dota_hero(self, ctx: AluGuildContext) -> None:
        """Dota 2 FPC (Favourite Player+Character) Hideout-only hero-related commands."""
        await ctx.send_help()

    async def hideout_dota_hero_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_dota_hero.command(name="add")
    @app_commands.describe(hero_name="Hero Name. Autocomplete suggestions exclude your favourite champs.")
    @app_commands.autocomplete(hero_name=hideout_dota_hero_add_autocomplete)
    async def hideout_dota_hero_add(self, ctx: AluGuildContext, hero_name: str) -> None:
        """Add a Dota 2 hero into your favourite FPC heroes list."""
        await self.hideout_character_add(ctx, hero_name)

    async def hideout_dota_hero_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_dota_hero.command(name="remove")
    @app_commands.describe(hero_name="Hero Name. Autocomplete suggestions only include your favourite champs.")
    @app_commands.autocomplete(hero_name=hideout_dota_hero_remove_autocomplete)
    async def hideout_dota_hero_remove(self, ctx: AluGuildContext, hero_name: str) -> None:
        """Remove a Dota 2 hero into your favourite FPC heroes list."""
        await self.hideout_character_remove(ctx, hero_name)

    @hideout_dota_player.command(name="list")
    async def hideout_dota_player_list(self, ctx: AluGuildContext) -> None:
        """Show a list of your favourite Dota 2 FPC players."""
        await self.hideout_player_list(ctx)

    @hideout_dota_hero.command(name="list")
    async def hideout_dota_hero_list(self, ctx: AluGuildContext) -> None:
        """Show a list of your favourite Dota 2 FPC heroes."""
        await self.hideout_character_list(ctx)

    @commands.is_owner()
    @commands.command(name="create_hero_emote")
    async def create_hero_emote(self, ctx: AluGuildContext, hero_name: str) -> None:
        """Create a new discord emote for a Dota 2 hero.

        Useful when a new Dota 2 hero gets added to the game, so we can just use this command,
        copy-paste the answer to `utils.const` and be happy.
        """
        await ctx.typing()

        hero_id = await self.bot.cache_dota.hero.id_by_name(hero_name)

        heroes_json = await self.bot.odota_constants.get_heroes()
        hero_data = heroes_json[str(hero_id)]

        guild_id = const.EmoteGuilds.DOTA[3]
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            msg = f"Guild with id {guild_id} is `None`."
            raise errors.SomethingWentWrong(msg)

        async with self.bot.session.get(url=hero_data["icon"]) as response:
            if not response.ok:
                msg = "Response for a new emote link wasn't okay"
                raise errors.ResponseNotOK(msg)

            new_emote = await guild.create_custom_emoji(
                name=hero_data["name"][14:],  # cut the "npc_dota_hero_" gibberish
                image=await response.read(),
            )

        embed = discord.Embed(
            colour=const.Colour.blueviolet,
            title="New Dota 2 Hero emote was created",
            description=f'```py\n{new_emote.name} = "{new_emote}"```',
        ).add_field(
            name=await self.bot.cache_dota.hero.name_by_id(hero_id),
            value=str(new_emote),
        )
        await ctx.reply(embed=embed)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(DotaFPCSettings(bot))
