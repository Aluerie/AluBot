from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, time
from typing import TYPE_CHECKING, Optional, Literal

from discord import Embed, app_commands, TextChannel
from discord.ext import commands, tasks
from pyot.core.exceptions import NotFound, ServerError
from pyot.models import lol

from roleidentification import pull_data

from .lol.models import ActiveMatch, PostMatchPlayerData
from .lol.utils import get_diff_list
from .utils.checks import is_owner, is_guild_owner, is_trustee
from .utils.distools import send_pages_list
from .utils.fpc import FPCBase
from .utils.twitch import get_lol_streams
from .utils.var import Clr, MP, Ems, Cid

if TYPE_CHECKING:
    from .utils.context import Context
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LoLFeed(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.lolfeed.start()

        self.active_matches = []
        self.after_match = []

    def cog_unload(self) -> None:
        self.lolfeed.cancel()

    async def after_match_games(self):
        self.after_match = []
        row_dict = {}
        query = 'SELECT * FROM lfmatches'
        rows = await self.bot.pool.fetch(query)
        for row in rows: # TODO: rework this monstrocity with the dict - just query it properly
            if row.match_id in row_dict:
                row_dict[row.match_id]['champ_ids'].append(row.champ_id)
            else:
                row_dict[row.match_id] = {
                    'champ_ids': [row.champ_id],
                    'routing_region': row.routing_region
                }

        for m_id in row_dict:
            try:
                match = await lol.Match(
                    id=m_id,
                    region=row_dict[m_id]['routing_region']
                ).get()
            except NotFound:
                continue
            except ValueError:  # gosu incident ValueError: '' is not a valid platform
                continue  # TODO: remove message from the database
            for participant in match.info.participants:
                if participant.champion_id in row_dict[m_id]['champ_ids']:
                    self.after_match.append(PostMatchPlayerData(player_data=participant))

    async def edit_the_embed(self, match: PostMatchPlayerData):
        query = 'DELETE FROM lfmatches WHERE match_id=$1 RETURNING *'
        rows = await self.bot.pool.fetch(query, match.match_id)
        for row in rows:
            ch = self.bot.get_channel(row.ch_id)
            if ch is None:
                continue  # wrong bot, I guess

            msg = await ch.fetch_message(row.id)

            em = msg.embeds[0]
            image_name = 'edited.png'
            img_file = img_to_file(
                await match.edit_the_image(
                    em.image.url,
                    self.bot.ses
                ),
                filename=image_name
            )
            em.set_image(url=f'attachment://{image_name}')
            await msg.edit(embed=em, attachments=[img_file])
            query = 'UPDATE lolaccs SET last_edited=$1 WHERE id=$2'
            await self.bot.pool.execute(query, match.match_id, match.match_id)

    async def fill_active_matches(self):
        self.active_matches = []

        async def get_all_fav_ids(column_name: str):
            query = f'SELECT DISTINCT(unnest({column_name})) FROM guilds'
            rows = await self.bot.pool.fetch(query)
            return [row.unnest for row in rows]
        fav_champ_ids = await get_all_fav_ids('lolfeed_champ_ids')

        twtv_ids = await get_lol_streams(self.bot.pool)

        query = 'SELECT * FROM lolaccs WHERE twtv_id=ANY($1)'
        rows = await self.bot.pool.fetch(query, twtv_ids)
        for row in rows:
            try:
                live_game = await lol.spectator.CurrentGame(summoner_id=row.id, platform=row.platform).get()
                # https://static.developer.riotgames.com/docs/lol/queues.json
                # says 420 is 5v5 Ranked Solo games
                if not hasattr(live_game, 'queue_id') or live_game.queue_id != 420:
                    continue
                our_player = next((x for x in live_game.participants if x.summoner_id == row.id), None)
                if our_player.champion_id in fav_champ_ids and \
                        row.last_edited != get_str_match_id(live_game.platform, live_game.id):
                    self.active_matches.append(
                        ActiveMatch(
                            match_id=live_game.id,
                            platform=our_player.platform,
                            acc_name=our_player.summoner_name,
                            start_time=round(live_game.start_time_millis / 1000),
                            champ_id=our_player.champion_id,
                            all_champ_ids=[player.champion_id for player in live_game.participants],
                            twitch_id=row.twtv_id,
                            spells=our_player.spells,
                            runes=our_player.runes
                        )
                    )
            except NotFound:
                continue
            except ServerError:
                log.debug(f'ServerError `lolfeed.py`: {row.name} {row.platform} {row.accname}')
                continue
                # embed = Embed(colour=Clr.error)
                # embed.description = f'ServerError `lolfeed.py`: {row.name} {row.platform} {row.accname}'
                # await self.bot.get_channel(Cid.spam_me).send(embed=embed)  # content=umntn(Uid.alu)

    async def send_the_embed(
            self,
            match: ActiveMatch,
    ):
        query = 'SELECT lolfeed_ch_id, lolfeed_champ_ids, lolfeed_stream_ids FROM guilds'
        rows = await self.bot.pool.fetch(query )
        for row in rows:
            if match.champ_id in row.lolfeed_champ_ids and match.twtv_id in row.lolfeed_stream_ids:
                ch: TextChannel = self.bot.get_channel(row.lolfeed_ch_id)
                if ch is None:
                    continue  # the bot does not have access to the said channel
                match_id_str = get_str_match_id(match.platform, match.match_id)

                query = """ SELECT id
                            FROM lfmatches
                            WHERE ch_id=$1 AND match_id=$2 AND champ_id=$3
                            LIMIT 1
                        """
                val = await self.bot.pool.fetchval(query, ch.id, match_id_str, match.champ_id)
                if val:
                    continue  # the message was already sent
                em, img_file = await match.notif_embed(self.bot.ses)
                em.title = f"{ch.guild.owner.name}'s fav champ + fav stream spotted"
                msg = await ch.send(embed=em, file=img_file)

                query = """ INSERT INTO lfmatches 
                            (id, match_id, ch_id, champ_id, routing_region)
                            VALUES ($1, $2, $3, $4, $5)
                        """
                await self.bot.pool.execute(
                    query, msg.id, match_id_str, ch.id, match.champ_id, platform_to_routing_dict[match.platform]
                )

    @tasks.loop(seconds=59)
    async def lolfeed(self):
        log.info("league feed every 59 seconds")
        await self.fill_active_matches()
        for match in self.active_matches:
            await self.send_the_embed(match)

        await self.after_match_games()
        for match in self.after_match:
            await self.edit_the_embed(match)

    @lolfeed.before_loop
    async def before(self):
        log.info("leaguefeed before the loop")
        await self.bot.wait_until_ready()

    @lolfeed.error
    async def leaguefeed_error(self, error):
        await self.bot.send_traceback(error, where='LoLFeed Notifs')
        # self.lolfeed.restart()


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    region: Literal['br', 'eun', 'euw', 'jp', 'kr', 'lan', 'las', 'na', 'oc', 'ru', 'tr']
    accname: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    region: Optional[Literal['br', 'eun', 'euw', 'jp', 'kr', 'lan', 'las', 'na', 'oc', 'ru', 'tr']]
    accname: Optional[str]


class LoLFeedTools(commands.Cog, FPCBase, name='LoL'):
    """
    Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name='LoLFeed',
            game_name='LoL',
            game_codeword='lol',
            colour=Clr.rspbrry,
            bot=bot,
            players_table='lol_players',
            accounts_table='lol_accounts',
            channel_id_column='lolfeed_ch_id',
            players_column='lolfeed_stream_ids',
            characters_column='lolfeed_champ_ids',
            spoil_column='lolfeed_spoils_on',
            acc_info_columns=[],
            get_char_name_by_id=,
            get_char_id_by_name=,
            get_all_character_names=,
            character_gather_word='champs'
        )
        self.bot: AluBot = bot
        self.help_emote = Ems.PogChampPepe

    @is_owner()
    @commands.hybrid_group(aliases=['league'])
    @app_commands.default_permissions(administrator=True)
    async def lol(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @lol.group()
    async def channel(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @channel.command(name='set', usage='[channel=curr]')
    @app_commands.describe(channel='Choose channel for LoLFeed notifications')
    async def channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Set channel to be the LoLFeed notifications channel."""
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            em = Embed(
                colour=Clr.error,
                description='I do not have permissions to send messages in that channel :('
            )
            return await ctx.reply(embed=em)  # todo: change this to raise BotMissingPerms

        query = 'UPDATE guilds SET lolfeed_ch_id=$1 WHERE id=$2'
        await self.bot.pool.execute(query, channel.id, ctx.guild.id)

        em = Embed(
            colour=Clr.rspbrry,
            description=f'Channel {channel.mention} is set to be the LoLFeed channel for this server'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @channel.command(name='disable', description='Disable LoLFeed functionality.')
    async def channel_disable(self, ctx: Context):
        """
        Stop getting LoLFeed notifications. \
        Data about fav champs/streamers won't be affected.
        """
        query = 'SELECT lolfeed_ch_id FROM guilds WHERE id=$1'
        ch_id = await self.bot.pool.fetchval(query, ctx.guild.id)
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.error,
                description=f'LoLFeed channel is not set or already was reset'
            )
            return await ctx.reply(embed=em)
        query = 'UPDATE guilds SET lolfeed_ch_id=NULL WHERE id=$1'
        await self.bot.pool.execute(query, ctx.guild.id)
        em = Embed(
            colour=Clr.rspbrry,
            description=f'Channel {ch.mention} is set to be the LoLFeed channel for this server.'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @channel.command(name='check')
    async def channel_check(self, ctx: Context):
        """Check if a LoLFeed channel was set in this server."""
        query = 'SELECT lolfeed_ch_id FROM guilds WHERE id=$1'
        ch_id = await self.bot.pool.fetchval(query, ctx.guild.id)
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.rspbrry,
                description=f'LoLFeed channel is not currently set.'
            )
            return await ctx.reply(embed=em)
        else:
            em = Embed(
                colour=Clr.rspbrry,
                description=f'LoLFeed channel is currently set to {ch.mention}.'
            )
            return await ctx.reply(embed=em)

    @is_guild_owner()
    @lol.group(aliases=['db'])
    async def database(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    def field_twitch_string(twitch: str):
        return f"● [**{twitch}**](https://www.twitch.tv/{twitch})"

    @staticmethod
    def field_account_string(platform: str, accname: str):
        return \
            f"`{platform_to_region(platform)}`: `{accname}` " \
            f"/[Opgg]({opgg_link(platform, accname)})" \
            f"/[Ugg]({ugg_link(platform, accname)})"

    def field_both(self, twitch, platform, accname):
        return \
            f"{self.field_twitch_string(twitch)}\n" \
            f"{self.field_account_string(platform, accname)}"

    @is_guild_owner()
    @database.command(name='list')
    async def database_list(self, ctx: Context):
        """
        List of all streamers in database \
        available for LoLFeed feature.
        """
        await ctx.typing()

        query = 'SELECT lolfeed_stream_ids FROM guilds WHERE id=$1'
        twtvid_list = await self.bot.pool.fetchval(query, ctx.guild.id)

        query = 'SELECT * FROM lolaccs'
        rows = await self.bot.pool.fetch(query)
        ss_dict = dict()
        for row in rows:
            followed = f' {Ems.DankLove}' if row.twtv_id in twtvid_list else ''
            key = f'{self.field_twitch_string(row.name)}{followed}'
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(
                self.field_account_string(row.platform, row.accname)
            )

        ans_array = [f"{k}\n {chr(10).join(ss_dict[k])}" for k in ss_dict]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)

        await send_pages_list(
            ctx,
            ans_array,
            split_size=10,
            colour=Clr.rspbrry,
            title="List of LoL Streams in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}'
        )

    @staticmethod
    async def get_lol_id(ctx: Context, region: str, accname: str):
        platform = region_to_platform(region)
        try:
            summoner = await lol.summoner.Summoner(name=accname, platform=platform).get()
            return summoner.id, summoner.platform, summoner.name
        except NotFound:
            em = Embed(
                colour=Clr.error,
                description=
                f"Error checking account for \n"
                f"`{region}` {accname}\n"
                f"This account does not exist."
            )
            await ctx.reply(embed=em)
            return None, None, None

    @is_trustee()
    @database.command(
        name='add',
        usage='twitch: <twitch_name> region: <region> accname: <accname>',
        description='Add stream to the database.'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        region='Region of the account',
        accname='Summoner name of the account'
    )
    async def database_add(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Add stream to the database.
        • `<twitch_name>` is twitch.tv stream name
        • `<region>` is LoL region of the account
        • `<accname>` is Summoner name of the account
        """
        await ctx.typing()
        twitch = flags.twitch.lower()
        twtv_id = await self.get_check_twitch_id(ctx, twitch)
        if twtv_id is None:
            return

        lolid, platform, accname = await self.get_lol_id(ctx, flags.region, flags.accname)
        if lolid is None:
            return

        query = 'SELECT * FROM lolaccs WHERE id=$1 LIMIT 1'
        user = await self.bot.pool.fetchrow(query, lolid)
        if user is not None:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name=f'This lol account is already in the database',
                value=
                f'It is marked as [{user.name}](https://www.twitch.tv/{user.name})\'s account.\n\n'
                f'Did you mean to use `$lol stream add {user.name}` to add the stream into your fav list?'
            )
            return await ctx.reply(embed=em, ephemeral=True)

        query = """ INSERT INTO lolaccs 
                    (id, name, platform, accname, twtv_id) 
                    VALUES ($1, $2, $3, $4)
                """
        await self.bot.pool.execute(query, lolid, twitch, platform, accname, twtv_id)
        em = Embed(
            colour=Clr.rspbrry
        ).add_field(
            name=f'Successfully added the account to the database',
            value=self.field_both(twitch, platform, accname)
        )
        await ctx.reply(embed=em)
        em.colour = MP.green(shade=200)
        em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        await self.bot.get_channel(Cid.global_logs).send(embed=em)

    @is_trustee()
    @database.command(
        name='remove',
        usage='twitch: <twitch_name> region: [region] accname: [accname]'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        region='Region of the account',
        accname='Summoner name of the account'
    )
    async def database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """Remove stream from the database."""
        await ctx.typing()

        map_dict = {
            'name': flags.twitch.lower(),
        }
        if flags.region:
            map_dict['platform'] = region_to_platform(flags.region)
        if flags.accname:
            map_dict['accname'] = flags.accname

        success = []
        with db.session_scope() as ses:
            query = ses.query(db.l).filter_by(**map_dict)
            for row in query:
                success.append(
                    {
                        'name': row.name,
                        'platform': row.platform,
                        'accname': row.accname
                    }
                )
            query.delete()
        if success:
            em = Embed(
                colour=Clr.rspbrry,
            ).add_field(
                name='Successfully removed account(-s) from the database',
                value=
                '\n'.join(self.field_both(x['name'], x['platform'], x['accname']) for x in success)
            )
            await ctx.reply(embed=em)

            em.colour = MP.red(shade=200)
            em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
            await self.bot.get_channel(Cid.global_logs).send(embed=em)
        else:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name='There is no account in the database like that',
                value=', '.join([f'{k}: {v}' for k, v in flags.__dict__.items()])
            )
            await ctx.reply(embed=em)

    @is_guild_owner()
    @database.command(
        name='request',
        usage='twitch: <twitch_name> region: <region> accname: <accname>',
        description='Request lol account to be added into the database.'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        region='Region of the account',
        accname='Summoner name of the account'
    )
    async def database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Request lol account to be added into the database. \
        This will send a request message into Aluerie's personal logs channel.
        """
        await ctx.typing()

        twitch = flags.twitch.lower()
        twtv_id = await self.get_check_twitch_id(ctx, twitch)
        if twtv_id is None:
            return

        lolid, platform, accname = await self.get_lol_id(ctx, flags.region, flags.accname)
        if lolid is None:
            return

        warn_em = Embed(
            colour=Clr.rspbrry,
            title='Confirmation Prompt',
            description=
            f'Are you sure you want to request this streamer steam account to be added into the database?\n'
            f'This information will be sent to Aluerie. Please, double check before confirming.'
        ).add_field(
            name='Request to add an account into the database',
            value=self.field_both(flags.twitch.lower(), platform, accname)
        )
        confirm = await ctx.prompt(embed=warn_em)
        if not confirm:
            return await ctx.send('Aborting...', delete_after=5.0)

        warn_em.colour = MP.orange(shade=200)
        warn_em.description = ''
        warn_em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        warn_em.add_field(
            name='Command',
            value=f'`$lol stream add twitch: {flags.twitch.lower()} region: {flags.region} accname: {accname}`'
        )
        await self.bot.get_channel(Cid.global_logs).send(embed=warn_em)

    @is_guild_owner()
    @lol.group(aliases=['streamer'])
    async def stream(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    async def stream_add_remove(ctx, twitch_names, mode):
        twitch_list = set(db.get_value(db.ga, ctx.guild.id, 'lolfeed_stream_ids'))

        success = []
        fail = []
        already = []

        for name in re.split('; |, |,', twitch_names):
            streamer = db.session.query(db.l).filter_by(name=name.lower()).first()
            if streamer is None:
                fail.append(f'`{name}`')
            else:
                if mode == 'add':
                    if streamer.twtv_id in twitch_list:
                        already.append(f'`{name}`')
                    else:
                        twitch_list.add(streamer.twtv_id)
                        success.append(f'`{name}`')
                elif mode == 'remov':
                    if streamer.twtv_id not in twitch_list:
                        already.append(f'`{name}`')
                    else:
                        twitch_list.remove(streamer.twtv_id)
                        success.append(f'`{name}`')
        db.set_value(db.ga, ctx.guild.id, lolfeed_stream_ids=list(twitch_list))

        if len(success):
            em = Embed(
                colour=Clr.rspbrry
            ).add_field(
                name=f'Successfully {mode}ed following streamers: \n',
                value=", ".join(success)
            )
            await ctx.reply(embed=em)
        if len(already):
            em = Embed(
                colour=MP.orange(shade=500)
            ).add_field(
                name=f'Stream(-s) already {"not" if mode == "remov" else ""} in fav list',
                value=", ".join(already)
            )
            await ctx.reply(embed=em)
        if len(fail):
            em = Embed(
                colour=Clr.error
            ).add_field(
                name='Could not find streamers in the database from these names:',
                value=", ".join(fail)
            ).set_footer(
                text=
                'Check your argument or '
                'consider adding (for trustees)/requesting such streamer with '
                '`$lol database add/request twitch: <twitch_name> region: <region> accname: <accname>`'
            )
            await ctx.reply(embed=em)

    @is_guild_owner()
    @stream.command(
        name='add',
        usage='<twitch_name(-s)>'
    )
    @app_commands.describe(twitch_names='Name(-s) of twitch streams')
    async def stream_add(self, ctx: Context, *, twitch_names: str):
        """Add twitch stream(-s) to the list of your fav LoL streamers."""
        await self.stream_add_remove(ctx, twitch_names, mode='add')

    @is_guild_owner()
    @stream.command(
        name='remove',
        usage='<twitch_name(-s)>'
    )
    @app_commands.describe(twitch_names='Name(-s) of twitch streams')
    async def stream_remove(self, ctx: Context, *, twitch_names: str):
        """Remove twitch stream(-s) from the list of your fav LoL streamers."""
        await self.stream_add_remove(ctx, twitch_names, mode='remov')

    @is_guild_owner()
    @stream.command(name='list')
    async def stream_list(self, ctx: Context):
        """Show current list of fav streams."""

        twtvid_list = db.get_value(db.ga, ctx.guild.id, 'lolfeed_stream_ids')
        names_list = [
            row.name
            for row in db.session.query(db.l).filter(db.l.twtv_id.in_(twtvid_list)).all() # type: ignore
        ]

        ans_array = [f"[{name}](https://www.twitch.tv/{name})" for name in names_list]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)
        embed = Embed(
            color=Clr.rspbrry,
            title='List of fav LoL streamers',
            description="\n".join(ans_array)
        )
        await ctx.reply(embed=embed)

    @is_guild_owner()
    @lol.group()
    async def champ(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    async def champ_add_remove(ctx, hero_names, mode):
        hero_list = set(db.get_value(db.ga, ctx.guild.id, 'lolfeed_champ_ids'))
        success = []
        fail = []
        already = []
        for name in re.split('; |, |,', hero_names):
            try:
                if (hero_id := await champion.id_by_name(name)) is not None:
                    hero_name = f'`{await champion.name_by_id(hero_id)}`'
                    if mode == 'add':
                        if hero_id in hero_list:
                            already.append(hero_name)
                        else:
                            hero_list.add(hero_id)
                            success.append(hero_name)
                    elif mode == 'remov':
                        if hero_id not in hero_list:
                            already.append(hero_name)
                        else:
                            hero_list.remove(hero_id)
                            success.append(hero_name)

            except KeyError:
                fail.append(f'`{name}`')

        db.set_value(db.ga, ctx.guild.id, lolfeed_champ_ids=list(hero_list))

        if len(success):
            em = Embed(
                colour=Clr.rspbrry
            ).add_field(
                name=f'Successfully {mode}ed following champs',
                value=", ".join(success)
            )
            await ctx.reply(embed=em)
        if len(already):
            em = Embed(
                colour=MP.orange(shade=500)
            ).add_field(
                name=f'Champ(-s) already {"not" if mode == "remov" else ""} in fav list',
                value=", ".join(already)
            )
            await ctx.reply(embed=em)
        if len(fail):
            em = Embed(
                colour=Clr.error
            ).add_field(
                name='Could not recognize LoL champs from these names',
                value=", ".join(fail)
            ).set_footer(
                text='You can look in $help for help in champ names'
            )
            await ctx.reply(embed=em)

    @is_guild_owner()
    @champ.command(
        name='add',
        usage='<champ_name(-s)>',
        description='Add champ(-es) to your fav champs list.'
    )
    @app_commands.describe(champ_names='Champ name(-s) from League of Legends')
    async def champ_add(self, ctx: Context, *, champ_names: str):
        """Add champ(-es) to your fav champ list."""
        await self.champ_add_remove(ctx, champ_names, mode='add')

    @is_guild_owner()
    @champ.command(
        name='remove',
        usage='<champ_name(-s)>'
    )
    @app_commands.describe(champ_names='Champ name(-s) from League of Legends')
    async def champ_remove(self, ctx: Context, *, champ_names: str):
        """Remove hero(-es) from your fav champs list."""
        await self.champ_add_remove(ctx, champ_names, mode='remov')

    @staticmethod
    async def champ_add_remove_error(ctx: Context, error):
        if getattr(error, 'original', None) and isinstance(error.original, KeyError):
            ctx.error_handled = True
            em = Embed(
                colour=Clr.error,
                description=
                f'Looks like there is no hero with name `{error.original}`. '

            ).set_author(
                name='ChampNameNotFound'
            )
            await ctx.send(embed=em)

    @champ_add.error
    async def champ_add_error(self, ctx: Context, error):
        await self.champ_add_remove_error(ctx, error)

    @champ_remove.error
    async def champ_remove_error(self, ctx: Context, error):
        await self.champ_add_remove_error(ctx, error)

    @is_guild_owner()
    @champ.command(name='list')
    async def champ_list(self, ctx: Context):
        """Show current list of fav champs."""
        query = 'SELECT lolfeed_champ_ids FROM guilds WHERE id=$1'
        hero_list = await self.bot.pool.fetchval(query, ctx.guild.id)
        answer = [f'`{await champion.name_by_id(h_id)} - {h_id}`' for h_id in hero_list]
        answer.sort()
        em = Embed(
            color=Clr.rspbrry,
            title='List of fav LoL champs',
            description='\n'.join(answer)
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @lol.command(description='Turn on/off spoiling resulting stats for matches. ')
    @app_commands.describe(spoil='`Yes` to enable spoiling with stats, `No` for disable')
    async def spoil(
            self,
            ctx: Context,
            spoil: bool
    ):
        """
        Turn on/off spoiling resulting stats for matches.

        It is "on" by default, so it can show items streamers finished with and KDA.
        """
        query = 'UPDATE guilds SET lolfeed_spoils_on=$1 WHERE id=$2'
        await self.bot.pool.execute(query, spoil, ctx.guild.id)
        em = Embed(
            colour=Clr.rspbrry,
            description=f"Changed spoil value to {spoil}"
        )
        await ctx.reply(embed=em)

    @is_owner()
    @champ.command()
    async def meraki(self, ctx: Context):
        """Show list of champions that are missing from Meraki JSON."""
        meraki_data = pull_data()
        champ_ids = await get_diff_list(meraki_data)
        champ_str = [f'● {await champion.key_by_id(i)} - `{i}`' for i in champ_ids]

        url_json = 'http://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json'
        async with self.bot.ses.get(url_json) as resp:
            json_dict = await resp.json()
            meraki_patch = json_dict["patch"]

        em = Embed(
            colour=Clr.rspbrry,
            title='List of champs missing from Meraki JSON',
            description='\n'.join(champ_str)
        ).add_field(
            name='Links',
            value=
            f'• [GitHub](https://github.com/meraki-analytics/role-identification)\n'
            f'• [Json]({url_json})'
        ).add_field(
            name='Meraki last updated',
            value=f'Patch {meraki_patch}'
        )
        await ctx.reply(embed=em)


class LoLAccCheck(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    def cog_unload(self) -> None:
        self.check_acc_renames.cancel()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        log.info("league checking acc renames every 24 hours")
        query = 'SELECT id, platform, accname FROM lolaccs'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            person = await lol.summoner.Summoner(id=row.id, platform=row.platform).get()
            if person.name != row.accname:
                query = 'UPDATE lolaccs SET accname=$1 WHERE id=$2'
                await self.bot.pool.execute(query, person.name, row.id)

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(LoLFeed(bot))
    await bot.add_cog(LoLFeedTools(bot))
    if datetime.now(timezone.utc).day == 17:
        await bot.add_cog(LoLAccCheck(bot))
