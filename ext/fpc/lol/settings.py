from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict, override

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, const, errors, lol

from ..base_classes import Account, BaseSettings
from ..database_management import AddLoLPlayerFlags  # noqa: TCH001
from .models import lol_links

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LoLAccountDict(TypedDict):
    summoner_id: str
    puuid: str
    platform: lol.LiteralPlatform
    game_name: str
    tag_line: str
    # player_id: int
    # last_edited: int


class LoLAccount(Account):
    if TYPE_CHECKING:
        summoner_id: str
        puuid: str
        platform: lol.Platform
        game_name: str
        tag_line: str

    @override
    async def set_game_specific_attrs(self, bot: AluBot, flags: AddLoLPlayerFlags) -> None:
        # RIOT ACCOUNT INFO
        try:
            riot_account = await bot.riot.get_account_v1_by_riot_id(
                game_name=flags.game_name,
                tag_line=flags.tag_line,
                region=flags.platform.continent,
                # in theory we can use continent closest to me bcs they all share the same data
                # for account_v1 endpoint
                # so check response time to this request (BUT WHATEVER)
            )
        except aiohttp.ClientResponseError:
            msg = (
                "Error `get_account_v1_by_riot_id` for "
                f"`{flags.game_name}#{flags.tag_line}` for `{flags.platform}` platform.\n"
                "This account probably does not exist."
            )
            raise errors.BadArgument(msg)

        self.puuid = puuid = riot_account["puuid"]
        self.platform = flags.platform
        self.game_name = riot_account["gameName"]
        self.tag_line = riot_account["tagLine"]

        # SUMMONER INFO
        try:
            summoner = await bot.riot.get_lol_summoner_v4_by_puuid(puuid=puuid, region=self.platform)
        except aiohttp.ClientResponseError:
            msg = (
                f"Error `get_lol_summoner_v4_by_puuid` for riot account\n"
                f"`{flags.game_name}#{flags.tag_line}` in `{flags.platform}` platform, puuid: `{puuid}`"
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
    def static_account_name_with_links(
        platform: lol.LiteralPlatform, game_name: str, tag_line: str, **kwargs: Any
    ) -> str:
        opgg_name = lol.Platform(platform).opgg_name
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
        bot.initialize_cache_league()
        super().__init__(
            bot,
            *args,
            prefix="lol",
            colour=const.Colour.darkslategray,
            game_display_name="League of Legends",
            game_icon_url=const.Logo.Lol,
            character_singular_word="champion",
            character_plural_word="champions",
            account_cls=LoLAccount,
            account_typed_dict_cls=LoLAccountDict,
            character_cache=bot.cache_lol.champion,
            emote_dict=const.LOL_CHAMPION_EMOTES,
            **kwargs,
        )

    @checks.hybrid.is_premium_guild_manager()
    @commands.hybrid_group(name="lol", aliases=["league"])
    async def lol_group(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) commands."""
        await ctx.send_help()

    @lol_group.group(name="request")
    async def lol_request(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) request commands."""
        await ctx.send_help()

    @lol_request.command(name="player")
    async def lol_request_player(self, ctx: AluGuildContext, *, flags: AddLoLPlayerFlags) -> None:
        """Request LoL Player to be added into the bot's FPC database.

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.
        """
        await self.request_player(ctx, flags)

    @lol_group.group(name="setup")
    async def lol_setup(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) setup commands.

        Manage FPC feature settings in your server with those commands.
        """
        await ctx.send_help()

    @lol_setup.command(name="channel")
    async def lol_setup_channel(self, ctx: AluGuildContext) -> None:
        """Setup/manage your LoL FPC Notifications channel."""
        await self.setup_channel(ctx)

    @lol_setup.command(name="champions")
    async def lol_setup_champions(self, ctx: AluGuildContext) -> None:
        """Setup/manage your LoL FPC favourite champions list."""
        await self.setup_characters(ctx)

    @lol_setup.command(name="players")
    async def lol_setup_players(self, ctx: AluGuildContext) -> None:
        """Setup/manage your LoL FPC favourite players list."""
        await self.setup_players(ctx)

    @lol_setup.command(name="miscellaneous", aliases=["misc"])
    async def lol_setup_misc(self, ctx: AluGuildContext) -> None:
        """Manage your LoL FPC misc settings."""
        await self.setup_misc(ctx)

    @lol_group.command(name="tutorial")
    async def lol_tutorial(self, ctx: AluGuildContext) -> None:
        """Guide to setup League of Legends FPC Notifications."""
        await self.tutorial(ctx)

    @checks.hybrid.is_hideout()
    @commands.hybrid_group(name="lolfpc")  # cspell: ignore lolfpc
    async def hideout_lol_group(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) Hideout-only commands."""
        await ctx.send_help()

    @hideout_lol_group.group(name="player")
    async def hideout_lol_player(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) Hideout-only player-related commands."""
        await ctx.send_help()

    async def hideout_lol_player_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_lol_player.command(name="add")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions exclude your favourite players.")
    @app_commands.autocomplete(player_name=hideout_lol_player_add_autocomplete)
    async def hideout_lol_player_add(self, ctx: AluGuildContext, player_name: str) -> None:
        """Add a League of Legends player into your favourite FPC players list."""
        await self.hideout_player_add(ctx, player_name)

    async def hideout_lol_player_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_lol_player.command(name="remove")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions include only your favourite players.")
    @app_commands.autocomplete(player_name=hideout_lol_player_remove_autocomplete)
    async def hideout_lol_player_remove(self, ctx: AluGuildContext, player_name: str) -> None:
        """Remove a League of Legends player into your favourite FPC players list."""
        await self.hideout_player_remove(ctx, player_name)

    @hideout_lol_group.group(name="champion")
    async def hideout_lol_champion(self, ctx: AluGuildContext) -> None:
        """League of Legends FPC (Favourite Player+Character) Hideout-only champion-related commands."""
        await ctx.send_help()

    async def hideout_lol_champion_add_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=True)

    @hideout_lol_champion.command(name="add")
    @app_commands.describe(champion_name="Champion Name. Autocomplete suggestions exclude your favourite champs.")
    @app_commands.autocomplete(champion_name=hideout_lol_champion_add_autocomplete)
    async def hideout_lol_champion_add(self, ctx: AluGuildContext, champion_name: str) -> None:
        """Add a League of Legends champion into your favourite FPC champions list."""
        await self.hideout_character_add(ctx, champion_name)

    async def hideout_lol_champion_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(interaction, current, mode_add_remove=False)

    @hideout_lol_champion.command(name="remove")
    @app_commands.describe(champion_name="Champion Name. Autocomplete suggestions only include your favourite champs.")
    @app_commands.autocomplete(champion_name=hideout_lol_champion_remove_autocomplete)
    async def hideout_lol_champion_remove(self, ctx: AluGuildContext, champion_name: str) -> None:
        """Remove a League of Legends champion into your favourite FPC champions list."""
        await self.hideout_character_remove(ctx, champion_name)

    @hideout_lol_player.command(name="list")
    async def hideout_lol_player_list(self, ctx: AluGuildContext) -> None:
        """Show a list of your favourite League of Legends FPC players."""
        await self.hideout_player_list(ctx)

    @hideout_lol_champion.command(name="list")
    async def hideout_lol_champion_list(self, ctx: AluGuildContext) -> None:
        """Show a list of your favourite League of Legends FPC champions."""
        await self.hideout_character_list(ctx)

    # Utilities to debug some rare situations.

    @commands.command(hidden=True)
    async def meraki(self, ctx: AluGuildContext) -> None:
        """Show list of champions that are missing from Meraki JSON."""
        embed = (
            discord.Embed(
                colour=const.Colour.darkslategray,
                title="List of champs missing from Meraki JSON",
                description=(
                    "\n".join(
                        [
                            f"\N{BLACK CIRCLE} {await self.bot.cache_lol.champion.name_by_id(i)} - `{i}`"
                            for i in await self.bot.cache_lol.role.get_missing_from_meraki_champion_ids()
                        ]
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
            .add_field(name="Meraki last updated", value=f"Patch {self.bot.cache_lol.role.meraki_patch}")
        )
        await ctx.reply(embed=embed)

    @commands.is_owner()
    @commands.command(name="create_champion_emote")
    async def create_champion_emote(self, ctx: AluGuildContext, champion_name: str) -> None:
        """Create a new discord emote for a League of Legends champion.

        Useful when a new LoL champion gets added to the game, so we can just use this command,
        copy-paste the answer to `utils.const` and be happy.
        """
        await ctx.typing()
        cache_lol = self.bot.cache_lol.champion

        champion_id = await cache_lol.id_by_name(champion_name)
        # a bit cursed
        alias = await cache_lol.alias_by_id(champion_id)
        icon_url = await cache_lol.icon_by_id(champion_id)

        guild_id = const.EmoteGuilds.LOL[3]
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            msg = f"Guild with id {guild_id} is `None`."
            raise errors.SomethingWentWrong(msg)

        async with self.bot.session.get(url=icon_url) as response:
            if not response.ok:
                msg = "Response for a new emote link wasn't okay"
                raise errors.ResponseNotOK(msg)

            new_emote = await guild.create_custom_emoji(name=alias, image=await response.read())

        embed = discord.Embed(
            colour=const.Colour.darkslategray,
            title="New League of Legends 2 Champion emote was created",
            description=f'```py\n{new_emote.name} = "{new_emote}"```',
        ).add_field(
            name=await cache_lol.name_by_id(champion_id),
            value=str(new_emote),
        )
        await ctx.reply(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Settings(bot))
