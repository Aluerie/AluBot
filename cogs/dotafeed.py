from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from steam.core.msg import MsgProto
from steam.enums import emsg
import vdf

from discord import Embed, TextChannel
from discord.ext import commands, tasks

from utils import database as db
from utils import dota as d2
from utils.var import *
from utils.imgtools import img_to_file, url_to_img
from utils.format import display_relativehmstime
from utils.distools import send_traceback, scnf, send_pages_list
from utils.mysteam import sd_login
from cogs.twitch import TwitchStream, get_dota_streams, get_twtv_id, twitch_by_id
from utils.context import Context

import re
from PIL import Image, ImageOps, ImageDraw, ImageFont
from datetime import datetime, timezone, time

if TYPE_CHECKING:
    pass


import logging
log = logging.getLogger('root')
lobbyids = set()
to_be_posted = {}


async def try_to_find_games(bot, ses):
    log.info("TryToFindGames dota2info")
    global to_be_posted, lobbyids
    to_be_posted = {}
    lobbyids = set()
    fav_hero_ids = []
    for row in ses.query(db.ga):
        fav_hero_ids += row.dotafeed_hero_ids
    fav_hero_ids = list(set(fav_hero_ids))

    sd_login(bot.steam, bot.dota, bot.steam_lgn, bot.steam_psw)

    # @dota.on('ready')
    def ready_function():
        log.info("ready_function dota2info")
        bot.dota.request_top_source_tv_games(lobby_ids=list(lobbyids))

    # @dota.on('top_source_tv_games')
    def response(result):
        log.info(f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games}")
        if result.specific_games:
            friendids = [row.friendid for row in ses.query(db.d.friendid)]
            for match in result.game_list:  # games
                our_persons = [x for x in match.players if x.account_id in friendids and x.hero_id in fav_hero_ids]
                for person in our_persons:
                    user = ses.query(db.d).filter_by(friendid=person.account_id).first()
                    if user.lastposted != match.match_id:
                        to_be_posted[user.name] = {
                            'matchid': match.match_id,
                            'st_time': match.activate_time,
                            'streamer': user.name,
                            'twtv_id': user.twtv_id,
                            'heroid': person.hero_id,
                            'hero_ids': [x.hero_id for x in match.players],
                        }
            log.info(f'to_be_posted {to_be_posted}')
        bot.dota.emit('top_games_response')

    proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
    proto_msg.header.routing_appid = 570
    steamids = [row.id for row in ses.query(db.d).filter(db.d.twtv_id.in_(get_dota_streams())).all()]
    # print(steamids)
    proto_msg.body.steamid_request.extend(steamids)
    resp = bot.steam.send_message_and_wait(proto_msg, emsg.EMsg.ClientRichPresenceInfo, timeout=8)
    if resp is None:
        print('resp is None, hopefully everything else will be fine tho;')
        return
    for item in resp.rich_presence:
        if rp_bytes := item.rich_presence_kv:
            # steamid = item.steamid_user
            rp = vdf.binary_loads(rp_bytes)['RP']
            # print(rp)
            if lobby_id := int(rp.get('WatchableGameID', 0)):
                if rp.get('param0', 0) == '#DOTA_lobby_type_name_ranked':
                    if await d2.id_by_npcname(rp.get('param2', '#')[1:]) in fav_hero_ids:  # that's npcname
                        lobbyids.add(lobby_id)

    # print(lobbyids)
    log.info(f'lobbyids {lobbyids}')
    # dota.on('ready', ready_function)
    bot.dota.once('top_source_tv_games', response)
    ready_function()
    bot.dota.wait_event('top_games_response', timeout=8)


async def better_thumbnail(session, stream, hero_ids, heroname):
    img = await url_to_img(session, stream.preview_url)
    width, height = img.size
    rectangle = Image.new("RGB", (width, 70), '#9678b6')
    ImageDraw.Draw(rectangle)
    img.paste(rectangle)

    for count, heroId in enumerate(hero_ids):
        hero_img = await url_to_img(session, await d2.iconurl_by_id(heroId))
        # h_width, h_height = heroImg.size
        hero_img = hero_img.resize((62, 35))
        hero_img = ImageOps.expand(hero_img, border=(0, 3, 0, 0), fill=Clr.dota_colour_map.get(count))
        extra_space = 0 if count < 5 else 20
        img.paste(hero_img, (count * 62 + extra_space, 0))

    font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
    draw = ImageDraw.Draw(img)
    text = f'{stream.display_name} - {heroname}'
    w2, h2 = draw.textsize(text, font=font)
    draw.text(((width - w2) / 2, 35), text, font=font, align="center")
    return img


class DotaFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dotafeed.start()

    async def send_the_embed(self, tbp, session):
        log.info("sending dota 2 embed")
        match_id, streamer, heroid, hero_ids, twtv_id = \
            tbp['matchid'], tbp['streamer'], tbp['heroid'], tbp['hero_ids'], tbp['twtv_id']
        long_ago = datetime.now(timezone.utc).timestamp() - tbp['st_time']

        twitch = TwitchStream(streamer)
        heroname = await d2.name_by_id(heroid)
        image_name = f'{streamer.replace("_", "")}-playing-{heroname.replace(" ", "")}.png'
        img_file = img_to_file(await better_thumbnail(self.bot.ses, twitch, hero_ids, heroname), filename=image_name)

        em = Embed(
            colour=Clr.prpl,
            url=twitch.url,
            description=
            f'`/match {match_id}` started {display_relativehmstime(long_ago)}\n' 
            f'{f"[TwtvVOD]({link})" if (link := twitch.last_vod_link(time_ago=long_ago)) is not None else ""}'
            f'/[Dotabuff](https://www.dotabuff.com/matches/{match_id})'
            f'/[Opendota](https://www.opendota.com/matches/{match_id})'
            f'/[Stratz](https://stratz.com/matches/{match_id})'
        ).set_image(
            url=f'attachment://{image_name}'
        ).set_thumbnail(
            url=await d2.iconurl_by_id(heroid)
        ).set_author(
            name=f'{twitch.display_name} - {heroname}',
            url=twitch.url,
            icon_url=twitch.logo_url
        )

        for row in db.session.query(db.ga):
            if heroid in row.dotafeed_hero_ids and twtv_id in row.dotafeed_stream_ids:
                ch: TextChannel = self.bot.get_channel(row.dotafeed_ch_id)
                em.title = f"{ch.guild.owner.name}'s fav hero + fav stream spotted !"
                msg = await ch.send(embed=em, file=img_file)
                if ch.is_news():
                    await msg.publish()

        for row in session.query(db.d).filter_by(name=streamer):
            row.lastposted = match_id
        return 1

    @tasks.loop(seconds=59)
    async def dotafeed(self):
        with db.session_scope() as ses:
            await try_to_find_games(self.bot, ses)
            for key in to_be_posted:
                await self.send_the_embed(to_be_posted[key], ses)

    @dotafeed.before_loop
    async def before(self):
        log.info("dotafeed before loop wait")
        await self.bot.wait_until_ready()

    @dotafeed.error
    async def dotafeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in dotafeed'))
        # self.dotafeed.restart()


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    steamid: int
    friendid: int


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    steamid: Optional[int]
    friendid: Optional[int]


def is_guild_owner():
    def predicate(ctx: commands.Context):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only guild owner is allowed to use this command'
            )
    return commands.check(predicate)


def is_trusted_user():
    def predicate(ctx: commands.Context):
        trusted_ids = db.get_value(db.b, Sid.alu, 'trusted_ids')
        if ctx.author.id in trusted_ids:
            return True
        else:
            raise commands.CheckFailure(
                message='Sorry, only trusted janitors can use this command'
            )
    return commands.check(predicate)


class DotaFeedTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Dota 2'

    @is_guild_owner()
    @commands.group()
    async def dota(self, ctx):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @dota.group()
    async def channel(self, ctx: commands.Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @channel.command(name='set')
    async def channel_set(
            self,
            ctx: commands.Context,
            ch: Optional[TextChannel] = None
    ):
        """Sets channel to be the DotaFeed notifications channel.
        Messages about favourite streamers picking favourite heroes will be sent here."""
        ch = ch or ctx.channel
        if not ch.permissions_for(ctx.guild.me).send_messages:
            em = Embed(
                colour=Clr.error,
                description='I do not have permissions to send messages in that channel :('
            )
            return await ctx.reply(embed=em)

        db.set_value(db.ga, ctx.guild.id, dotafeed_ch_id=ch.id)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {ch.mention} is set to be the DotaFeed channel for this server'
        )
        await ctx.reply(embed=em)

    @channel.command(name='disable')
    async def channel_disable(self, ctx: commands.Context):
        """Disables DotaFeed functionality in this server.
        Removes the channel info from bot's database.
        Data about fav heroes/streamers won't be deleted in case you want to choose different channel.
        You can kick the bot to achieve that """
        ch_id = db.get_value(db.ga, ctx.guild.id, 'dotafeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.error,
                description=f'DotaFeed channel is not set or already was reset'
            )
            return await ctx.reply(embed=em)
        db.set_value(db.ga, ctx.guild.id, dotafeed_ch_id=None)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {ch.mention} is set to be the DotaFeed channel for this server'
        )
        await ctx.reply(embed=em)

    @channel.command(name='check')
    async def channel_check(self, ctx: commands.Context):
        """Check if a DotaFeed channel was set in this server"""
        ch_id = db.get_value(db.ga, ctx.guild.id, 'dotafeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.prpl,
                description=f'DotaFeed channel is not currently set'
            )
            return await ctx.reply(embed=em)
        else:
            em = Embed(
                colour=Clr.prpl,
                description=f'DotaFeed channel is currently set to {ch.mention}'
            )
            return await ctx.reply(embed=em)

    @dota.group()
    async def database(self, ctx: commands.Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @database.command(name='list')
    async def database_list(self, ctx: commands.Context):
        """Get list of all Dota streamers currently present in database
        that are available for DotaFeed feature"""
        ss_dict = dict()
        for row in db.session.query(db.d):
            key = f"● [**{row.name}**](https://www.twitch.tv/{row.name})"
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(
                f"`{row.id}` - `{row.friendid}`| "
                f"[Steam](https://steamcommunity.com/profiles/{row.id})"
                f"/[Dotabuff](https://www.dotabuff.com/players/{row.friendid})"
            )

        ans_array = [f"{k}\n {chr(10).join(ss_dict[k])}" for k in ss_dict]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)

        await send_pages_list(
            ctx,
            ans_array,
            split_size=10,
            colour=Clr.prpl,
            title="List of Dota 2 Streams in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}'
        )

    @is_trusted_user()
    @database.command(name='add')
    async def database_add(self, ctx: Context, *, flags: AddStreamFlags):
        """Add stream to the database"""
        twtv_name = flags.twitch.lower()
        twtv_id = get_twtv_id(twtv_name)
        if twtv_id is None:
            em = Embed(
                colour=Clr.error,
                description=f'Error checking stream {twtv_name}.\n User either does not exist or is banned.'
            )
            return await ctx.reply(embed=em)
        db.add_row(db.d, flags.steamid, name=flags.twitch.lower(), friendid=flags.friendid, twtv_id=twtv_id)
        await ctx.message.add_reaction(Ems.PepoG)

    @is_trusted_user()
    @database.command(name='remove')
    async def database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """Remove stream from database"""
        map_dict = {
            'twitch': 'name',
            'steamid': 'id',
            'friendid': 'friendid'
        }

        my_dict = {map_dict[k]: v for k, v in dict(flags).items() if v is not None}
        with db.session_scope() as ses:
            ses.query(db.d).filter_by(**my_dict).delete()
        await ctx.message.add_reaction(Ems.PepoG)

    @database.command(name='request')
    async def database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """Request streamer to be added into a database.
        This will send a message into Irene's personal logs channel and maybe one day it will be seen.
        You can just DM Irene to speed up the process."""

        info_str = \
            f'[**{flags.twitch}**](https://www.twitch.tv/{flags.twitch})\n' \
            f'`{flags.steamid}` - `{flags.friendid}`| ' \
            f'[Steam](https://steamcommunity.com/profiles/{flags.steamid})' \
            f'/[Dotabuff](https://www.dotabuff.com/players/{flags.friendid})'

        warn_em = Embed(
            colour=Clr.prpl,
            title='Confirmation Prompt',
            description=
            f'Are you sure you want to request this streamer steam account to be added into the database?\n'
            f'This information will be sent to Irene. Please, double check before confirming.\n\n'
            f'{info_str}'
        )
        confirm = await ctx.prompt(embed=warn_em)
        if not confirm:
            return await ctx.send('Aborting...', delete_after=5.0)

        em2 = Embed(
            colour=Clr.prpl,
            description=info_str,
            title='Request to add a streamer steam account into the database'
        ).set_author(
            name=ctx.author.name,
            icon_url=ctx.author.avatar.url
        ).add_field(
            name='command',
            value=f'`$dota stream add twitch: {flags.twitch} steamid: {flags.steamid} friendid: {flags.friendid}`'
        )
        await self.bot.get_channel(Cid.global_logs).send(embed=em2)

    @dota.group()
    async def stream(self, ctx: commands.Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @staticmethod
    async def stream_add_remove(ctx, twitch_names, mode):
        if twitch_names is None:
            em = Embed(
                colour=Clr.error,
                description="Provide all arguments: `twitch_names`"
            )
            return await ctx.reply(embed=em)

        twitch_list = set(db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids'))

        success = []
        for name in re.split('; |, |,', twitch_names):
            streamer = db.session.query(db.d).filter_by(name=name).first()
            if streamer is None:
                em = Embed(
                    colour=Clr.prpl,
                    description=
                    f'There is no streamer named {name} like that in bot\'s database. Check your argument or  '
                    f'consider adding (for trusted janitors)/requesting such streamer with '
                    f'`$dota stream add/request twitch: <twitch_tag> steamid: <steam_id> friendid: <friend_id>` command'
                )
                await ctx.send(embed=em)
                continue
            else:
                if mode == 'add':
                    twitch_list.add(streamer.twtv_id)
                elif mode == 'remov':
                    twitch_list.remove(streamer.twtv_id)
                success.append(name)
        db.set_value(db.ga, ctx.guild.id, dotafeed_stream_ids=list(twitch_list))

        em = Embed(
            colour=Clr.prpl,
            description=
            f'Successfully {mode}ed following streamers: \n'
            f'{", ".join(success)}'
        )
        await ctx.reply(embed=em)

    @stream.command(name='add')
    async def stream_add(self, ctx: commands.Context, *, twitch_names: str = None):
        """Add twitch streamer(-s) to the list of your favourite Dota 2 streamers.
        You can say name of one streamer or list several streamers divided with commas"""
        await self.stream_add_remove(ctx, twitch_names, mode='add')

    @stream.command(name='remove')
    async def stream_remove(self, ctx: commands.Context, *, twitch_names: str = None):
        """Remove twitch streamer(-s) from the list of your favourite Dota 2 streamers.
        You can say name of one streamer or list several streamers divided with commas"""
        await self.stream_add_remove(ctx, twitch_names, mode='remov')

    @stream.command(name='list')
    async def stream_list(self, ctx: commands.Context):
        """Show current list of fav streamers"""
        twtvid_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids')
        names_list = [row.name for row in db.session.query(db.d).filter(db.d.twtv_id.in_(twtvid_list)).all()]

        ans_array = [f"[{name}](https://www.twitch.tv/{name})" for name in names_list]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)
        embed = Embed(
            color=Clr.prpl,
            title='List of fav dota 2 streamers',
            description="\n".join(ans_array)
        )
        await ctx.reply(embed=embed)

    @dota.group()
    async def hero(self, ctx: commands.Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @staticmethod
    async def hero_add_remove(ctx, hero_names, mode):
        if hero_names is None:
            em = Embed(
                colour=Clr.error,
                description="Provide all arguments: `hero_names`"
            )
            return await ctx.reply(embed=em)

        hero_list = set(db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids'))
        success = []
        for name in re.split('; |, |,', hero_names):
            if (hero_id := await d2.id_by_name(name)) is not None:
                if mode == 'add':
                    hero_list.add(hero_id)
                elif mode == 'remov':
                    hero_list.remove(hero_id)
                success.append(name)

        db.set_value(db.ga, ctx.guild.id, dotafeed_hero_ids=list(hero_list))

        em = Embed(
            colour=Clr.prpl,
            description=
            f'Successfully {mode}ed following heroes: \n'
            f'{", ".join(success)}'
        )
        await ctx.reply(embed=em)

    @hero.command(name='add')
    async def hero_add(self, ctx: commands.Context, *, hero_names: str = None):
        """Add hero(-es) to your favorite heroes list.
        You can specify multiple heroes separated by comma"""
        await self.hero_add_remove(ctx, hero_names, mode='add')

    @hero.command(name='remove')
    async def hero_remove(self, ctx: commands.Context, *, hero_names: str = None):
        """Add hero(-es) to your favorite heroes list.
        You can specify multiple heroes separated by comma"""
        await self.hero_add_remove(ctx, hero_names, mode='remov')

    @staticmethod
    async def hero_add_remove_error(ctx: commands.Context, error):
        if isinstance(error.original, KeyError):
            ctx.error_handled = True
            em = Embed(
                colour=Clr.error,
                description=
                f'Looks like there is no hero with name `{error.original}`. '
                f'Check spelling or usage of correct name from Dota 2 hero grid. '
                f'For example,\n● `Anti-Mage` (letter case does not matter) and not `Magina`;\n'
                f'● `Queen of Pain` and not `QoP`.\n'
                f'In total confusion you can find proper name '
                f'[here](https://api.opendota.com/api/constants/heroes) with Ctrl+F under one of `"localized_name"`'
            ).set_author(
                name='HeroNameNotFound'
            )
            await ctx.send(embed=em)

    @hero_add.error
    async def hero_remove_error(self, ctx: commands.Context, error):
        await self.hero_add_remove_error(ctx, error)

    @hero_remove.error
    async def hero_remove_error(self, ctx: commands.Context, error):
        await self.hero_add_remove_error(ctx, error)

    @hero.command(name='list')
    async def hero_list(self, ctx: commands.Context):
        """Show current list of fav heroes ;"""
        hero_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids')
        answer = [f'`{await d2.name_by_id(h_id)} - {h_id}`' for h_id in hero_list]
        answer.sort()
        em = Embed(
            color=Clr.prpl,
            title='List of fav dota 2 heroes',
            description='\n'.join(answer)
        )
        await ctx.reply(embed=em)


class DotaAccCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_acc_renames.start()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        with db.session_scope() as ses:
            for row in ses.query(db.d):
                name = twitch_by_id(row.twtv_id)
                if name != row.name:
                    row.name = name

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaFeed(bot))
    await bot.add_cog(DotaFeedTools(bot))
    if datetime.now(timezone.utc).day == 16:
        await bot.add_cog(DotaAccCheck(bot))
