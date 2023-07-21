from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands
from pyot.core.exceptions import NotFound
from pyot.utils.lol import champion

from utils import const, checks
from utils.lol.const import LiteralServer, LiteralServerUpper, platform_to_server, server_to_platform
from utils.lol.utils import get_all_champ_names, get_meraki_patch, get_pyot_meraki_champ_diff_list

from .._fpc_utils import FPCSettingsBase
from ._models import Account

# need to import the last because in import above we activate 'lol' model
from pyot.models.lol import summoner  # isort: skip

if TYPE_CHECKING:
    from utils import AluBot, AluGuildContext

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: LiteralServer
    account: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: Optional[LiteralServer]
    account: Optional[str]


class LoLNotifsSettings(FPCSettingsBase, name='LoL'):
    """Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(
            bot,
            *args,
            colour=const.Colour.rspbrry(),
            game='lol',
            game_mention='League of Legends',
            game_icon=const.Logo.lol,
            extra_account_info_columns=['platform', 'account'],
            character_name_by_id=champion.name_by_id,
            character_id_by_name=champion.id_by_name,
            all_character_names=get_all_champ_names,
            character_word_plural='champs',
            **kwargs,
        )

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()
        return await super().cog_load()

    # lol ##############################################

    slh_lol = app_commands.Group(
        name="lol",
        description="Group command about LolFeed",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @checks.hybrid.is_manager()
    @commands.group(name='lol', aliases=['league'])
    async def ext_lol(self, ctx: AluGuildContext):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol channel ##############################################

    slh_lol_channel = app_commands.Group(
        name='channel', description='Group command about LoLFeed channel settings', parent=slh_lol
    )

    @checks.hybrid.is_manager()
    @ext_lol.group(name='channel')
    async def ext_lol_channel(self, ctx: AluGuildContext):
        """Group command about LoL channel, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol channel set ##############################################

    @slh_lol_channel.command(name='set')
    @app_commands.describe(channel='Choose channel to set up LoLFeed notifications')
    async def slh_lol_channel_set(
        self, ntr: discord.Interaction[AluBot], channel: Optional[discord.TextChannel] = None
    ):
        """Set channel to be the LoLFeed notifications channel."""
        await self.channel_set(ntr, channel)

    @checks.hybrid.is_manager()
    @ext_lol_channel.command(name='set', usage='[channel=curr]')
    async def ext_lol_channel_set(self, ctx: AluGuildContext, channel: Optional[discord.TextChannel] = None):
        """Set channel to be the LoLFeed notifications channel."""
        await self.channel_set(ctx, channel)

    # lol channel disable ##############################################

    @slh_lol_channel.command(name='disable')
    async def slh_lol_channel_disable(self, ntr: discord.Interaction[AluBot]):
        """Disable LoLFeed notifications channel."""
        await self.channel_disable(ntr)

    @checks.hybrid.is_manager()
    @ext_lol_channel.command(name='disable')
    async def ext_lol_channel_disable(self, ctx: AluGuildContext):
        """Stop getting LoLFeed notifs. Data about fav champs/players won't be affected."""
        await self.channel_disable(ctx)

    # lol channel check ##############################################

    @slh_lol_channel.command(name='check')
    async def slh_lol_channel_check(self, ntr: discord.Interaction[AluBot]):
        """Check if LoLFeed channel is set up."""
        await self.channel_check(ntr)

    @checks.hybrid.is_manager()
    @ext_lol_channel.command(name='check')
    async def ext_lol_channel_check(self, ctx: AluGuildContext):
        """Check if LoLFeed channel is set up in the server."""
        await self.channel_check(ctx)

    # lol database ##############################################

    slh_lol_database = app_commands.Group(
        name='database',
        description='Group command about LoLFeed database',
        parent=slh_lol,
    )

    @checks.hybrid.is_manager()
    @ext_lol.group(name='database', aliases=['db'])
    async def ext_lol_database(self, ctx: AluGuildContext):
        """Group command about LoL database, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # helper functions ##############################################

    @staticmethod
    def cmd_usage_str(**kwargs):
        platform = kwargs.pop('platform')
        account = kwargs.pop('account')
        return f'server: {platform_to_server(platform).upper()} account: {account}'

    @staticmethod
    def player_acc_string(**kwargs):
        platform = kwargs.pop('platform')
        account = kwargs.pop('account')
        return f"`{platform_to_server(platform).upper()}` - `{account}` {Account(platform, account).links}"

    @staticmethod
    async def get_lol_id(server: LiteralServer, account: str) -> tuple[str, str, str]:
        try:
            platform = server_to_platform(server)
            player = await summoner.Summoner(name=account, platform=platform).get()
            return player.id, player.platform, player.name
        except NotFound:
            raise commands.BadArgument(
                f"Error checking league account with name `{account}` for `{server}` server: \n"
                f"This account does not exist."
            )

    async def get_account_dict(self, *, server: LiteralServer, account: str) -> dict:
        lol_id, platform, account = await self.get_lol_id(server, account)
        return {'id': lol_id, 'platform': platform, 'account': account}

    # lol database list ##################################

    @slh_lol_database.command(name='list')
    async def slh_lol_database_list(self, ntr: discord.Interaction[AluBot]):
        """List of players in the database available for LoLFeed feature."""
        await self.database_list(ntr)

    @checks.hybrid.is_manager()
    @ext_lol_database.command(name='list')
    async def ext_lol_database_list(self, ctx: AluGuildContext):
        """List of players in the database available for LoLFeed feature."""
        await self.database_list(ctx)

    # lol database request ##################################

    @slh_lol_database.command(name='request')
    @app_commands.describe(
        name='twitch.tv player\'s handle',
        server='Server of the account, i.e. "NA", "EUW"',
        account='Summoner name of the account',
    )
    async def slh_lol_database_request(
        self, ntr: discord.Interaction[AluBot], name: str, server: LiteralServerUpper, account: str
    ):
        """Request player to be added into the database."""
        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=server, account=account)
        await self.database_request(ntr, player_dict, account_dict)

    @checks.hybrid.is_manager()
    @ext_lol_database.command(
        name='request',
        usage='name: <twitch_name> server: <server-region> account: <account_name>',
    )
    async def ext_lol_database_request(self, ctx: AluGuildContext, *, flags: AddStreamFlags):
        """Request player to be added into the database.
        This will send a request message into Aluerie's personal logs channel.
        """
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=flags.server, account=flags.account)
        await self.database_request(ctx, player_dict, account_dict)

    # lol player ##################################

    slh_lol_player = app_commands.Group(
        name='player',
        description='Group command about LoLFeed player',
        parent=slh_lol,
    )

    @checks.hybrid.is_manager()
    @ext_lol.group(name='player', aliases=['streamer'])
    async def ext_lol_player(self, ctx: AluGuildContext):
        """Group command about LoL player, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol player add ##################################

    async def lol_player_add_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_lol_player.command(name='add')
    @app_commands.describe(
        **{
            f'name{i}': 'Name of a player. Suggestions from database above exclude your already fav players'
            for i in range(1, 11)
        }
    )
    @app_commands.autocomplete(
        name1=lol_player_add_autocomplete,
        name2=lol_player_add_autocomplete,
        name3=lol_player_add_autocomplete,
        name4=lol_player_add_autocomplete,
        name5=lol_player_add_autocomplete,
        name6=lol_player_add_autocomplete,
        name7=lol_player_add_autocomplete,
        name8=lol_player_add_autocomplete,
        name9=lol_player_add_autocomplete,
        name10=lol_player_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_add_autocomplete for i in range(1, 11)})
    async def slh_lol_player_add(
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

    @checks.hybrid.is_manager()
    @ext_lol_player.command(name='add', usage='<player_name(-s)>')
    async def ext_lol_player_add(self, ctx: AluGuildContext, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=True)

    # lol player remove ##################################

    async def player_remove_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_lol_player.command(name='remove')
    @app_commands.describe(**{f'name{i}': 'Name of a player' for i in range(1, 11)})
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
    async def slh_lol_player_remove(
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

    @checks.hybrid.is_manager()
    @ext_lol_player.command(name='remove', usage='<player_name(-s)>')
    async def ext_lol_player_remove(self, ctx: AluGuildContext, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=False)

    # lol player list ##################################

    @slh_lol_player.command(name='list')
    async def slh_lol_player_list(self, ntr: discord.Interaction[AluBot]):
        """Show list of your favourite players."""
        await self.player_list(ntr)

    @checks.hybrid.is_manager()
    @ext_lol_player.command(name='list')
    async def ext_lol_player_list(self, ctx: AluGuildContext):
        """Show list of your favourite players."""
        await self.player_list(ctx)

    # lol champ ##################################

    slh_lol_champ = app_commands.Group(
        name='champion',
        description='Group command about LoLFeed champs',
        parent=slh_lol,
    )

    @checks.hybrid.is_manager()
    @ext_lol.group(name='champion', aliases=['champ'])
    async def ext_lol_champ(self, ctx: AluGuildContext):
        """Group command about LoL champs, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol champ add ##################################

    async def lol_champ_add_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_lol_champ.command(name='add')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_add_autocomplete,
        name2=lol_champ_add_autocomplete,
        name3=lol_champ_add_autocomplete,
        name4=lol_champ_add_autocomplete,
        name5=lol_champ_add_autocomplete,
        name6=lol_champ_add_autocomplete,
        name7=lol_champ_add_autocomplete,
        name8=lol_champ_add_autocomplete,
        name9=lol_champ_add_autocomplete,
        name10=lol_champ_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_add(
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
        """Add champ to your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=True)

    @checks.hybrid.is_manager()
    @ext_lol_champ.command(
        name='add',
        usage='<champ_name(-s)>',
    )
    async def ext_lol_champ_add(self, ctx: AluGuildContext, *, champ_names: str):
        """Add champ(-s) to your fav champ list."""
        await self.character_add_remove(ctx, locals(), mode_add=True)

    # lol champ remove ##################################

    async def lol_champ_remove_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_lol_champ.command(name='remove')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_remove_autocomplete,
        name2=lol_champ_remove_autocomplete,
        name3=lol_champ_remove_autocomplete,
        name4=lol_champ_remove_autocomplete,
        name5=lol_champ_remove_autocomplete,
        name6=lol_champ_remove_autocomplete,
        name7=lol_champ_remove_autocomplete,
        name8=lol_champ_remove_autocomplete,
        name9=lol_champ_remove_autocomplete,
        name10=lol_champ_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_remove(
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
        """Remove champ from your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=False)

    @checks.hybrid.is_manager()
    @ext_lol_champ.command(name='remove', usage='<champ_name(-s)>')
    async def ext_lol_champ_remove(self, ctx: AluGuildContext, *, champ_names: str):
        """Remove champ(-es) from your fav champs list."""
        await self.character_add_remove(ctx, locals(), mode_add=False)

    # lol champ list ##################################

    @slh_lol_champ.command(name='list')
    async def slh_lol_champ_list(self, ntr: discord.Interaction[AluBot]):
        """Show your favourite champs list."""
        await self.character_list(ntr)

    @checks.hybrid.is_manager()
    @ext_lol_champ.command(name='list')
    async def ext_lol_champ_list(self, ctx: AluGuildContext):
        """Show current list of fav champ."""
        await self.character_list(ctx)

    # lol champ spoil ##################################

    @slh_lol.command(name='spoil')
    @app_commands.describe(spoil='`True` to enable spoiling with stats, `False` for disable')
    async def slh_lol_spoil(self, ntr: discord.Interaction[AluBot], spoil: bool):
        """Turn on/off spoiling resulting stats for matches."""
        await self.spoil(ntr, spoil)

    @checks.hybrid.is_manager()
    @ext_lol.command(name='spoil')
    async def ext_lol_spoil(self, ctx: AluGuildContext, spoil: bool):
        """Turn on/off spoiling resulting stats for matches.
        It is "on" by default, so it can show what items players finished with and KDA.
        """
        await self.spoil(ctx, spoil)

    # character setup

    async def get_character_data(self):
        return await champion.champion_keys_cache.data
    
    @slh_lol_champ.command(name='setup')
    async def slh_lol_champ_setup(self, ntr: discord.Interaction[AluBot]):
        """Interactive setup to add/remove champions in/from your favourite list."""
        await self.character_setup(ntr)
    
    @checks.hybrid.is_manager()
    @ext_lol_champ.command(name='setup')
    async def ext_lol_champ_setup(self, ctx: AluGuildContext):
        """Interactive setup to add/remove champions in/from your favourite list."""
        await self.character_setup(ctx)

    # meraki ##################################

    @commands.command(hidden=True)
    async def meraki(self, ctx: AluGuildContext):
        """Show list of champions that are missing from Meraki JSON."""
        champ_ids = await get_pyot_meraki_champ_diff_list()
        champ_str = [f'\N{BLACK CIRCLE} {await champion.key_by_id(i)} - `{i}`' for i in champ_ids] or ['None missing']

        meraki_patch = await get_meraki_patch()

        e = discord.Embed(title='List of champs missing from Meraki JSON', colour=const.Colour.rspbrry())
        e.description = '\n'.join(champ_str)
        e.add_field(
            name='Links',
            value=(
                f'• [GitHub](https://github.com/meraki-analytics/role-identification)\n'
                f'• [Json](https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json)'
            ),
        )
        e.add_field(name='Meraki last updated', value=f'Patch {meraki_patch}')
        await ctx.reply(embed=e)
