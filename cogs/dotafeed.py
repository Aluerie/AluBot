from steam.core.msg import MsgProto
from steam.enums import emsg
import vdf

from discord import Embed
from discord.ext import commands, tasks

from utils import database as db
from utils import dota as d2
from utils.var import Clr, Cid, Sid, Ems, cmntn
from utils.imgtools import img_to_file, url_to_img
from utils.format import display_relativehmstime
from utils.dcordtools import send_traceback, scnf, inout_to_10
from utils.mysteam import sd_login
from cogs.twitch import TwitchStream
from cogs.twitch import get_db_online_streams

import re
from PIL import Image, ImageOps, ImageDraw, ImageFont
from datetime import datetime, timezone
from typing import Optional
import logging
log = logging.getLogger('root')
lobbyids = set()
to_be_posted = {}


async def try_to_find_games(bot, ses):
    log.info("TryToFindGames dota2info")
    global to_be_posted, lobbyids
    to_be_posted = {}
    lobbyids = set()
    fav_hero_ids = ses.query(db.g).filter_by(id=Sid.irene).first().dota_fav_heroes
    sd_login(bot.steam, bot.dota, bot.steam_lgn, bot.steam_psw)

    # @dota.on('ready')
    def ready_function():
        log.info("ready_function dota2info")
        bot.dota.request_top_source_tv_games(lobby_ids=list(lobbyids))

    # @dota.on('top_source_tv_games')
    def response(result):
        log.info(f"top_source_tv_games response NumGames: {result.num_games} SpecificGames: {result.specific_games}")
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
                            'heroid': person.hero_id,
                            'hero_ids': [x.hero_id for x in match.players],
                        }
            log.info(f'to_be_posted {to_be_posted}')
        bot.dota.emit('top_games_response')

    proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
    proto_msg.header.routing_appid = 570
    steamids = [row.id for row in ses.query(db.d).filter(db.d.name.in_(get_db_online_streams(db.d))).all()]
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


async def better_thumbnail(stream, hero_ids, heroname):
    img = await url_to_img(stream.preview_url)
    width, height = img.size
    rectangle = Image.new("RGB", (width, 70), '#9678b6')
    ImageDraw.Draw(rectangle)
    img.paste(rectangle)

    for count, heroId in enumerate(hero_ids):
        hero_img = await url_to_img(await d2.iconurl_by_id(heroId))
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
        match_id, streamer, heroid, hero_ids = tbp['matchid'], tbp['streamer'], tbp['heroid'], tbp['hero_ids']
        long_ago = datetime.now(timezone.utc).timestamp() - tbp['st_time']

        twitch = TwitchStream(streamer)
        embed = Embed(colour=Clr.prpl, title="Irene's fav streamer picked her fav hero !", url=twitch.url)
        vod = f'[TwtvVOD]({link})' if (link := twitch.last_vod_link(time_ago=long_ago)) is not None else ''
        dotabuff = f'[Dotabuff](https://www.dotabuff.com/matches/{match_id})'
        opendota = f'[Opendota](https://www.opendota.com/matches/{match_id})'
        stratz = f'[Stratz](https://stratz.com/matches/{match_id})'
        embed.description =\
            f'`?match {match_id}` started {display_relativehmstime(long_ago)}\n' \
            f'{vod}/{dotabuff}/{opendota}/{stratz}'

        heroname = await d2.name_by_id(heroid)
        image_name = f'{streamer.replace("_", "")}-playing-{heroname.replace(" ", "")}.png'
        img_file = img_to_file(await better_thumbnail(twitch, hero_ids, heroname), filename=image_name)
        embed.set_image(url=f'attachment://{image_name}')
        embed.set_thumbnail(url=await d2.iconurl_by_id(heroid))
        embed.set_author(name=f'{twitch.display_name} - {heroname}', url=twitch.url, icon_url=twitch.logo_url)
        msg = await self.bot.get_channel(Cid.irene_bot).send(embed=embed, file=img_file)
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
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in dotafeed'))
        self.dotafeed.restart()


class DotaFeedTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Dota 2'

    @commands.group()
    async def dota(self, ctx):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @dota.group()
    async def hero(self, ctx):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @commands.is_owner()
    @hero.command()
    async def add(self, ctx, *, heronames=None):
        """Add hero to database"""
        if heronames is None:
            return await ctx.send("Provide all arguments: `heroname`")
        try:
            hero_array = set(db.get_value(db.g, Sid.irene, 'dota_fav_heroes'))
            for hero_str in re.split('; |, |,', heronames):
                if (hero_id := await d2.id_by_name(hero_str)) is not None:
                    hero_array.add(hero_id)
                else:
                    await ctx.send('We got `None` somewhere, double-check: `heronames`')
            db.set_value(db.g, Sid.irene, dota_fav_heroes=list(hero_array))
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.send('Something went wrong, double-check: `heronames`')

    @commands.is_owner()
    @hero.command()
    async def remove(self, ctx, *, heronames=None):
        """Remove hero from database"""
        if heronames is None:
            return await ctx.send("Provide all arguments: `heroname`")
        try:
            hero_array = set(db.get_value(db.g, Sid.irene, 'dota_fav_heroes'))
            for hero_str in re.split('; |, |,', heronames):
                hero_array.remove(await d2.id_by_name(hero_str))
                db.set_value(db.g, Sid.irene, dota_fav_heroes=list(hero_array))
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.send('Something went wrong, double-check: `heroname`')

    @commands.is_owner()
    @hero.command()
    async def list(self, ctx):
        """Show current list of fav heroes ;"""
        embed = Embed(color=Clr.prpl, title='List of fav dota 2 heroes')
        hero_array = db.get_value(db.g, Sid.irene, 'dota_fav_heroes')
        answer = [f'`{await d2.name_by_id(h_id)} - {h_id}`' for h_id in hero_array]
        answer.sort()
        embed.description = '\n'.join(answer)
        await ctx.send(embed=embed)

    @commands.is_owner()
    @dota.group()
    async def streamer(self, ctx):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @commands.is_owner()
    @streamer.command(name='list')
    async def list_streamer(self, ctx):
        """Show current list of fav streamers with optins"""
        embed = Embed(color=Clr.prpl, title='List of fav dota 2 streamers')
        ans_array = [f"[{row.name}](https://www.twitch.tv/{row.name}): `{row.optin}`" for row in db.session.query(db.d)]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)
        embed.description = "\n".join(ans_array)
        await ctx.send(embed=embed)

    @commands.is_owner()
    @streamer.command(name='add')
    async def add_streamer(self, ctx, steamid=None, name=None, friendid=None):
        """Add streamer to database"""
        if name is None or steamid is None or friendid is None:
            return await ctx.send("Provide all arguments: `steamid`, `streamer`, `friendid`")
        try:
            db.add_row(db.d, steamid, name=name.lower(), friendid=friendid)
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.send('Something went wrong, double-check: `steamid`, `streamer`, `friendid`')

    class StreamerFlags(commands.FlagConverter, case_insensitive=True):
        id: Optional[int]
        name: str
        friendid: Optional[int]

    @commands.is_owner()
    @streamer.command(name='remove')
    async def remove_streamer(self, ctx, *, flags: StreamerFlags):
        """Remove streamer(-s) from database"""
        my_dict = {k: v for k, v in dict(flags).items() if v is not None}
        with db.session_scope() as ses:
            ses.query(db.l).filter_by(**my_dict).delete()
        await ctx.message.add_reaction(Ems.PepoG)

    @commands.is_owner()
    @streamer.command(
        help=f'Opt the streamer `in` or `out` from {cmntn(Cid.irene_bot)} channel',
        usage='<twitch_name> in/out',
        aliases=['turn']
    )
    async def opt(self, ctx, in_or_out: inout_to_10, twitch_name):
        """Read above"""
        try:
            db.set_value_by_name(db.d, twitch_name, optin=in_or_out)
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.send('Something went wrong, double-check: `streamer`')


def setup(bot):
    bot.add_cog(DotaFeed(bot))
    bot.add_cog(DotaFeedTools(bot))
