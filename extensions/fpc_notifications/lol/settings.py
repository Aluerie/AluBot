from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict, override

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import checks, const, errors, lol

from .._fpc_utils import FPCAccount, FPCSettingsBase
from ..database_management import AddLoLPlayerFlags
from ._models import LoLNotificationAccount

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LoLAccountDict(TypedDict):
    summoner_id: str
    puuid: str
    platform: lol.LiteralPlatform
    game_name: str
    tag_line: str
    # player_id: int
    # last_edited: int


class LoLAccount(FPCAccount):
    if TYPE_CHECKING:
        summoner_id: str
        puuid: str
        platform: lol.LiteralPlatform
        game_name: str
        tag_line: str

    @override
    async def set_game_specific_attrs(self, bot: AluBot, flags: AddLoLPlayerFlags):
        async with bot.acquire_riot_api_client() as riot_api_client:
            # RIOT ACCOUNT INFO
            try:
                riot_account = await riot_api_client.get_account_v1_by_riot_id(
                    game_name=flags.game_name,
                    tag_line=flags.tag_line,
                    region=lol.SERVER_TO_CONTINENT[flags.server],
                )
            except aiohttp.ClientResponseError:
                raise errors.BadArgument(
                    "Error `get_account_v1_by_riot_id` for "
                    f"`{flags.game_name}#{flags.tag_line}` in `{flags.server}` server.\n"
                    "This account probably does not exist."
                )

            self.puuid = puuid = riot_account["puuid"]
            self.platform = platform = lol.SERVER_TO_PLATFORM[flags.server]
            self.game_name = riot_account["gameName"]
            self.tag_line = riot_account["tagLine"]

            # SUMMONER INFO
            try:
                summoner = await riot_api_client.get_lol_summoner_v4_by_puuid(puuid=puuid, region=platform)
            except aiohttp.ClientResponseError:
                raise errors.BadArgument(
                    f"Error `get_lol_summoner_v4_by_puuid` for riot account\n"
                    f"`{flags.game_name}#{flags.tag_line}` in `{flags.server}` server, puuid: `{puuid}`"
                )
            self.summoner_id = summoner["id"]

    @property
    @override
    def hint_database_add_command_args(self) -> str:
        server = lol.PLATFORM_TO_SERVER[self.platform].upper()
        return (
            f"name: {self.player_display_name} game_name: {self.game_name} tag_line: {self.tag_line} server: {server}"
        )

    @override
    @staticmethod
    def embed_account_str_static(platform: lol.LiteralPlatform, game_name: str, tag_line: str, **kwargs: Any):
        server = lol.PLATFORM_TO_SERVER[platform]
        links = LoLNotificationAccount(platform, game_name, tag_line).links
        return f"`{server}`: `{game_name} #{tag_line}` {links}"

    @property
    @override
    def embed_account_str(self):
        return self.embed_account_str_static(self.platform, self.game_name, self.tag_line)

    @override
    @staticmethod
    def simple_account_name_static(game_name: str, tag_line: str, **kwargs: Any) -> str:
        return f"{game_name} #{tag_line}"

    @property
    @override
    def simple_account_name(self) -> str:
        return self.simple_account_name_static(self.game_name, self.tag_line)

    @override
    def to_database_dict(self) -> LoLAccountDict:
        return {
            "summoner_id": self.summoner_id,
            "puuid": self.puuid,
            "platform": self.platform,
            "game_name": self.game_name,
            "tag_line": self.tag_line,
        }


class LoLFPCSettings(FPCSettingsBase):
    """Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot, *args, **kwargs):
        bot.initiate_pulsefire()
        super().__init__(
            bot,
            *args,
            prefix="lol",
            colour=const.Colour.rspbrry(),
            game_display_name="League of Legends",
            game_icon_url=const.Logo.lol,
            character_singular_word="champion",
            character_plural_word="champions",
            account_cls=LoLAccount,
            account_typed_dict_cls=LoLAccountDict,
            character_cache=bot.cdragon.champion,
            **kwargs,
        )

    @checks.hybrid.is_premium_guild_manager()
    @commands.hybrid_group(name="lol", aliases=["league"])
    async def lol_group(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) commands."""
        await ctx.send_help()

    @lol_group.group(name="request")
    async def lol_request(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) request commands."""
        await ctx.send_help()

    @lol_request.command(name="player")
    async def lol_request_player(self, ctx: AluGuildContext, flags: AddLoLPlayerFlags):
        """Request LoL Player to be added into the bot's FPC database

        So you and other people can add the player into their favourite later and start \
        receiving FPC Notifications.
        """
        await self.request_player(ctx, flags)

    @lol_group.group(name="setup")
    async def lol_setup(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) setup commands.

        Manage FPC feature settings in your server with those commands.
        """
        await ctx.send_help()

    @lol_setup.command(name="channel")
    async def lol_setup_channel(self, ctx: AluGuildContext):
        """Setup/manage your LoL FPC Notifications channel."""
        await self.setup_channel(ctx)

    @lol_setup.command(name="champions")
    async def lol_setup_champions(self, ctx: AluGuildContext):
        """Setup/manage your LoL FPC favourite champions list."""
        await self.setup_characters(ctx)

    @lol_setup.command(name="players")
    async def lol_setup_players(self, ctx: AluGuildContext):
        """Setup/manage your LoL FPC favourite players list."""
        await self.setup_players(ctx)

    @lol_setup.command(name="misc")
    async def lol_setup_misc(self, ctx: AluGuildContext):
        """Manage your LoL FPC misc settings."""
        await self.setup_misc(ctx)

    @checks.hybrid.is_hideout()
    @commands.hybrid_group(name="lol-fpc")
    async def hideout_lol_group(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) Hideout-only commands."""

        await ctx.send_help()

    @hideout_lol_group.group(name="player")
    async def hideout_lol_player(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) Hideout-only player-related commands."""
        await ctx.send_help()

    async def hideout_lol_player_add_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(ntr, current, mode_add_remove=True)

    @hideout_lol_player.command(name="add")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions exclude your favourite players.")
    @app_commands.autocomplete(player_name=hideout_lol_player_add_autocomplete)
    async def hideout_lol_player_add(self, ctx: AluGuildContext, player_name: str):
        """Add a League of Legends player into your favourite FPC players list."""
        await self.hideout_player_add(ctx, player_name)

    async def hideout_lol_player_remove_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_player_add_remove_autocomplete(ntr, current, mode_add_remove=False)

    @hideout_lol_player.command(name="remove")
    @app_commands.describe(player_name="Player Name. Autocomplete suggestions include only your favourite players.")
    @app_commands.autocomplete(player_name=hideout_lol_player_remove_autocomplete)
    async def hideout_lol_player_remove(self, ctx: AluGuildContext, player_name: str):
        """Remove a League of Legends player into your favourite FPC players list."""
        await self.hideout_player_remove(ctx, player_name)

    @hideout_lol_group.group(name="champion")
    async def hideout_lol_champion(self, ctx: AluGuildContext):
        """League of Legends FPC (Favourite Player+Character) Hideout-only champion-related commands."""
        await ctx.send_help()

    async def hideout_lol_champion_add_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(ntr, current, mode_add_remove=True)

    @hideout_lol_champion.command(name="add")
    @app_commands.describe(champion_name="Champion Name. Autocomplete suggestions exclude your favourite champs.")
    @app_commands.autocomplete(champion_name=hideout_lol_champion_add_autocomplete)
    async def hideout_lol_champion_add(self, ctx: AluGuildContext, champion_name: str):
        """Add a League of Legends champion into your favourite FPC champions list."""
        await self.hideout_character_add(ctx, champion_name)

    async def hideout_lol_champion_remove_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.hideout_character_add_remove_autocomplete(ntr, current, mode_add_remove=False)

    @hideout_lol_champion.command(name="remove")
    @app_commands.describe(champion_name="Champion Name. Autocomplete suggestions only include your favourite champs.")
    @app_commands.autocomplete(champion_name=hideout_lol_champion_remove_autocomplete)
    async def hideout_lol_champion_remove(self, ctx: AluGuildContext, champion_name: str):
        """Remove a League of Legends champion into your favourite FPC champions list."""
        await self.hideout_character_add(ctx, champion_name)

    @hideout_lol_player.command(name="list")
    async def hideout_lol_player_list(self, ctx: AluGuildContext):
        """Show a list of your favourite League of Legends FPC players."""
        await self.hideout_player_list(ctx)

    @hideout_lol_champion.command(name="list")
    async def hideout_lol_champion_list(self, ctx: AluGuildContext):
        """Show a list of your favourite League of Legends FPC champions."""
        await self.hideout_character_list(ctx)

    # Utilities to debug some rare situations.

    @commands.command(hidden=True)
    async def meraki(self, ctx: AluGuildContext):
        """Show list of champions that are missing from Meraki JSON."""

        embed = (
            discord.Embed(
                colour=const.Colour.rspbrry(),
                title="List of champs missing from Meraki JSON",
                description=(
                    "\n".join(
                        [
                            f"\N{BLACK CIRCLE} {await self.bot.cdragon.champion.name_by_id(i)} - `{i}`"
                            for i in await self.bot.meraki_roles.get_missing_from_meraki_champion_ids()
                        ]
                    )
                    or "None missing"
                ),
            )
            .add_field(
                name="Links",
                value=(
                    f"• [GitHub](https://github.com/meraki-analytics/role-identification)\n"
                    "• [Json](https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json)"
                ),
            )
            .add_field(name="Meraki last updated", value=f"Patch {self.bot.meraki_roles.meraki_patch}")
        )
        await ctx.reply(embed=embed)


async def setup(bot: AluBot):
    await bot.add_cog(LoLFPCSettings(bot))
