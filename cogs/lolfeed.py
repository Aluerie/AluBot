from os import getenv
from pyot.conf.model import activate_model, ModelConf
from pyot.conf.pipeline import activate_pipeline, PipelineConf


@activate_model("lol")
class LolModel(ModelConf):
    default_platform = "na1"
    default_region = "americas"
    default_version = "latest"
    default_locale = "en_us"


@activate_pipeline("lol")
class LolPipeline(PipelineConf):
    name = "lol_main"
    default = True
    stores = [
        {
            "backend": "pyot.stores.omnistone.Omnistone",
            "expirations": {
                "summoner_v4_by_name": 100,
                "match_v4_match": 600,
                "match_v4_timeline": 600,
            }
        },
        {
            "backend": "pyot.stores.cdragon.CDragon",
        },
        {
            "backend": "pyot.stores.riotapi.RiotAPI",
            "api_key": getenv("RIOT_API_KEY"),
        }
    ]


from pyot.models import lol
from pyot.utils.lol import champion, cdragon
from pyot.core.exceptions import NotFound, ServerError

from discord import Embed
from discord.ext import commands, tasks

from utils import database as db
from utils.var import *
from utils.lol import get_role_mini_list
from utils.distools import send_traceback, scnf, inout_to_10
from utils.format import display_relativehmstime
from utils.imgtools import img_to_file, url_to_img
from cogs.twitch import TwitchStream, get_db_online_streams

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, time
import re
import collections
from typing import Optional

import logging
log = logging.getLogger("pyot")
log.setLevel(logging.ERROR)


async def iconurl_by_id(champid):
    champ = await lol.champion.Champion(id=champid).get()
    return cdragon.abs_url(champ.square_path)


async def better_thumbnail(session, stream, champ_ids, champ_name):
    img = await url_to_img(session, stream.preview_url)
    width, height = img.size
    rectangle = Image.new("RGB", (width, 100), '#9678b6')
    ImageDraw.Draw(rectangle)
    img.paste(rectangle)

    champ_img_urls = [await iconurl_by_id(champ_id) for champ_id in champ_ids]
    champ_imgs = await url_to_img(session, champ_img_urls)
    for count, champ_img in enumerate(champ_imgs):
        champ_img = champ_img.resize((62, 62))
        extra_space = 0 if count < 5 else 20
        img.paste(champ_img, (count * 62 + extra_space, 0))

    font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
    draw = ImageDraw.Draw(img)
    text = f'{stream.display_name} - {champ_name}'
    w2, h2 = draw.textsize(text, font=font)
    draw.text(((width - w2) / 2, 65), text, font=font, align="center")
    return img


class LoLFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lolfeed.start()

    async def send_the_embed(self, row, champ_ids, champ_name, long_ago, live_game_id):
        log.info("sending league embed")
        twitch = TwitchStream(row.name)
        embed = Embed(color=Clr.rspbrry, title="Aluerie's fav streamer picked her fav champ!", url=twitch.url)
        twtvvod = f'[TwtvVOD]({link})' if (link := twitch.last_vod_link(time_ago=long_ago)) is not None else ''
        opggregion = ''.join(i for i in row.region if not i.isdigit())  # remove that 1/2 in the end !
        opgg = f'[Opgg](https://{opggregion}.op.gg/summoner/userName={row.accname.replace(" ", "+")})'
        ugg = f'[Ugg](https://u.gg/lol/profile/{row.region}/{row.accname.replace(" ", "+")})'
        embed.description = \
            f'Match `{live_game_id}` started {display_relativehmstime(long_ago)}\n'\
            f'{twtvvod}/{opgg}/{ugg}'

        image_name = f'{twitch.display_name.replace("_", "")}-is-playing-{champ_name.replace(" ", "")}.png'
        file = img_to_file(await better_thumbnail(self.bot.ses, twitch, champ_ids, champ_name), filename=image_name)
        embed.set_image(url=f'attachment://{image_name}')
        champ = await lol.champion.Champion(key=champ_name).get()
        embed.set_thumbnail(url=cdragon.abs_url(champ.square_path))
        embed.set_author(name=f'{twitch.display_name} - {champ_name}', url=twitch.url, icon_url=twitch.logo_url)
        msg = await self.bot.get_channel(Cid.alubot).send(embed=embed, file=file)
        await msg.publish()

    @tasks.loop(seconds=59)
    async def lolfeed(self):
        log.info("league feed every 59 seconds")
        with db.session_scope() as ses:
            fav_ch_ids = ses.query(db.g).filter_by(id=Sid.alu).first().lol_fav_champs
            for row in ses.query(db.l).filter(db.l.name.in_(get_db_online_streams(db.l, session=ses))).all():
                try:
                    live_game = await lol.spectator.CurrentGame(summoner_id=row.id, platform=row.region).get()
                    # print(row.name, row.lastposted, live_game.id)
                    if row.lastposted != live_game.id:
                        our_player = [player for player in live_game.participants if player.summoner_id == row.id][0]
                        if our_player.champion_id in fav_ch_ids:
                            role_mini_list = await get_role_mini_list(
                                self.bot.ses,
                                [player.champion_id for player in live_game.participants],
                                self.bot.get_channel(Cid.spam_me)
                            )
                            if long_ago := round(live_game.start_time_millis / 1000):
                                long_ago = int(datetime.now(timezone.utc).timestamp() - long_ago)
                            champ_name = await champion.key_by_id(our_player.champion_id)
                            await self.send_the_embed(row, role_mini_list, champ_name, long_ago, live_game.id)
                            row.lastposted = live_game.id
                except NotFound:
                    continue
                except ServerError:
                    continue
                    # embed = Embed(colour=Clr.error)
                    # embed.description = f'ServerError `lolfeed.py`: {row.name} {row.region} {row.accname}'
                    # await self.bot.get_channel(Cid.spam_me).send(embed=embed)  # content=umntn(Uid.alu)

    @lolfeed.before_loop
    async def before(self):
        log.info("leaguefeed before the loop")
        await self.bot.wait_until_ready()

    @lolfeed.error
    async def leaguefeed_error(self, error):
        embed = Embed(colour=Clr.error)
        embed.title = 'Error in leaguefeed'
        await send_traceback(error, self.bot, embed=embed)
        # self.lolfeed.restart()


class LoLFeedTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'LoL'

    @commands.group(aliases=['league'])
    async def lol(self, ctx):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @lol.group()
    async def champ(self, ctx):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @commands.is_owner()
    @champ.command()
    async def add(self, ctx, *, champnames=None):
        """Add champion(-s) with `champnames` (can be list of names separated with `;` or `,`) \
        to database"""
        if champnames is None:
            return await ctx.reply("Provide all arguments: `heroname`")
        try:
            hero_array = set(db.get_value(db.g, Sid.alu, 'lol_fav_champs'))
            for champ_str in re.split('; |, |,', champnames):
                hero_array.add(await champion.id_by_key(champ_str))
            db.set_value(db.g, Sid.alu, lol_fav_champs=list(hero_array))
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.reply('Something went wrong, double-check: `heroname`')

    @commands.is_owner()
    @champ.command()
    async def remove(self, ctx, *, champnames=None):
        """Remove champion(-s) with `champnames` (can be list of names separated with `;` or `,`) \
        from database"""
        if champnames is None:
            return await ctx.reply("Provide all arguments: `heroname`")
        try:
            hero_array = set(db.get_value(db.g, Sid.alu, 'lol_fav_champs'))
            for champ_str in re.split('; |, |,', champnames):
                hero_array.remove(await champion.id_by_key(champ_str))
            db.set_value(db.g, Sid.alu, lol_fav_champs=list(hero_array))
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.reply('Something went wrong, double-check: `heroname`')

    @commands.is_owner()
    @champ.command()
    async def list(self, ctx):
        """Show current list of favourite champions ;"""
        embed = Embed(color=Clr.prpl)
        embed.title = 'List of fav lol heroes'
        champ_array = db.get_value(db.g, Sid.alu, 'lol_fav_champs')
        answer = [f'`{await champion.key_by_id(c_id)} - {c_id}`' for c_id in champ_array]
        answer.sort()
        embed.description = '\n'.join(answer)
        await ctx.reply(embed=embed)

    @commands.is_owner()
    @lol.group()
    async def streamer(self, ctx):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @commands.is_owner()
    @streamer.command(name='list')
    async def list_streamer(self, ctx):
        """Show current list of fav streamers with optins ;"""
        embed = Embed(color=Clr.prpl)
        embed.title = 'List of fav lol streamers'
        ss_dict = dict()
        for row in db.session.query(db.l):
            key = f'[{row.name}](https://www.twitch.tv/{row.name}) {row.optin}'
            if key not in ss_dict:
                ss_dict[key] = dict()
            if row.region in ss_dict[key]:
                ss_dict[key][row.region].append(row.accname)
            else:
                ss_dict[key][row.region] = [row.accname]

        ans_dict = collections.defaultdict(list)
        for key in ss_dict:
            for subkey in ss_dict[key]:
                ans_dict[key].append(f' {subkey} `{", ".join(ss_dict[key][subkey])}`')
        embed.description = "\n".join(sorted([f'{k}{" ".join(ans_dict[k])}' for k in ans_dict], key=str.casefold))
        await ctx.reply(embed=embed)

    @commands.is_owner()
    @streamer.command(name='add')
    async def add_streamer(self, ctx, name=None, region=None, *, accname=None):
        """Add streamer to database"""
        if name is None or region is None or accname is None:
            return await ctx.reply("Provide all arguments: `streamer`, `region`, `accname`")
        try:
            summoner = await lol.summoner.Summoner(name=accname, platform=region).get()
            if db.session.query(db.l).filter_by(id=summoner.id).first() is None:
                db.add_row(db.l, summoner.id, name=name.lower(), region=region, accname=accname)
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.reply('Something went wrong, double-check: `streamer`, `region`, `accname`')

    class StreamerFlags(commands.FlagConverter, case_insensitive=True):
        name: str
        region: Optional[str]
        accname: Optional[str]

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
        help=f'Opt the streamer `in` or `out` from {cmntn(Cid.alubot)} channel',
        usage='<twitch_name> in/out',
        aliases=['turn']
    )
    async def opt(self, ctx, in_or_out: inout_to_10, twitch_name):
        """Read above"""
        try:
            db.set_value_by_name(db.l, twitch_name, optin=in_or_out)
            await ctx.message.add_reaction(Ems.PepoG)
        except:
            await ctx.reply('Something went wrong, double-check: `streamer`')


class LoLAccCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_acc_renames.start()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        log.info("league checking acc renames every 24 hours")
        with db.session_scope() as ses:
            for row in ses.query(db.l):
                person = await lol.summoner.Summoner(id=row.id, platform=row.region).get()
                if person.name != row.accname:
                    row.accname = person.name

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(LoLFeed(bot))
    await bot.add_cog(LoLFeedTools(bot))
    if datetime.now(timezone.utc).day == 17:
        await bot.add_cog(LoLAccCheck(bot))
