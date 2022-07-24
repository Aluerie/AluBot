from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

from os import getenv
from pyot.conf.model import activate_model, ModelConf
from pyot.conf.pipeline import activate_pipeline, PipelineConf
from pyot.utils.functools import async_property

from utils.checks import is_owner, is_guild_owner


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

from discord import Embed, app_commands, TextChannel
from discord.ext import commands, tasks

from utils import database as db
from utils.var import *
from utils.lol import get_role_mini_list, get_diff_list
from utils.distools import send_traceback, inout_to_10, send_pages_list
from utils.format import display_relativehmstime
from utils.imgtools import img_to_file, url_to_img
from cogs.twitch import TwitchStream, get_db_online_streams

from roleidentification import pull_data
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, time
import re
import collections

import logging
log = logging.getLogger("pyot")
log.setLevel(logging.ERROR)

if TYPE_CHECKING:
    from utils.context import Context

region_to_platform_dict = {
    'br': 'br1',
    'eun': 'eun1',
    'euw': 'euw1',
    'jp': 'jp1',
    'kr': 'kr',
    'lan': 'la1',
    'las': 'la2',
    'na': 'na1',
    'oc': 'oc1',
    'ru': 'ru',
    'tr': 'tr1'
}

platform_to_region_dict = {
    v: k
    for k, v in region_to_platform_dict.items()
}


def region_to_platform(
        region: str
):
    return region_to_platform_dict[region.lower()]


def opgg_link(platform: str, accname: str):
    region = region_to_platform_dict[platform]
    return f'https://{region}.op.gg/summoner/{region}/{accname.replace(" ", "+")})'


def ugg_link(platform: str, accname: str):
    return f'/[Ugg](https://u.gg/lol/profile/{platform}/{accname.replace(" ", "+")})'


class ActiveMatch:

    def __init__(
            self,
            *,
            match_id: int,
            start_time: int,
            stream: str,
            twtv_id: int,
            champ_id: int,
            champ_ids: List[int]
    ):
        self.match_id = match_id,
        self.start_time = start_time,
        self.stream = stream,
        self.twtv_id = twtv_id,
        self.champ_id = champ_id,
        self.champ_ids = champ_ids

    @async_property
    async def champ_name(self):
        return await champion.key_by_id(self.champ_id)

    @staticmethod
    async def iconurl_by_id(champid):
        champ = await lol.champion.Champion(id=champid).get()
        return cdragon.abs_url(champ.square_path)

    async def better_thumbnail(self, session, stream, champ_ids, champ_name):
        img = await url_to_img(session, stream.preview_url)
        width, height = img.size
        rectangle = Image.new("RGB", (width, 100), '#9678b6')
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)

        champ_img_urls = [await self.iconurl_by_id(champ_id) for champ_id in champ_ids]
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

    async def send_the_embed(self, row, champ_ids, champ_name, long_ago, live_game_id):
        log.info("sending league embed")
        twitch = TwitchStream(row.name)
        opggregion = "".join(i for i in row.region if not i.isdigit())
        image_name = f'{twitch.display_name.replace("_", "")}-is-playing-{champ_name.replace(" ", "")}.png'
        file = img_to_file(await self.better_thumbnail(self.bot.ses, twitch, champ_ids, champ_name), filename=image_name)
        champ = await lol.champion.Champion(key=champ_name).get()

        embed = Embed(
            color=Clr.rspbrry,
            title="Aluerie's fav streamer picked her fav champ!",
            url=twitch.url,
            description=
            f'Match `{live_game_id}` started {display_relativehmstime(long_ago)}\n'
            f'{f"[TwtvVOD]({link})" if (link := twitch.last_vod_link(time_ago=long_ago)) is not None else ""}'
            f'/[Opgg](https://{opggregion}.op.gg/summoner/userName={row.accname.replace(" ", "+")})'       
            f'/[Ugg](https://u.gg/lol/profile/{row.region}/{row.accname.replace(" ", "+")})'
        ).set_image(
            url=f'attachment://{image_name}'
        ).set_thumbnail(
            url=cdragon.abs_url(champ.square_path)
        ).set_author(
            name=f'{twitch.display_name} - {champ_name}',
            url=twitch.url,
            icon_url=twitch.logo_url
        )
        for ch_id in [Cid.alubot, Cid.repost]:
            await self.bot.get_channel(ch_id).send(embed=embed, file=file)


class LoLFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lolfeed.start()
        self.active_matches = []

    async def fill_active_matches(self, ses):
        self.active_matches = []
        fav_champ_ids = []
        for row in ses.query(db.ga):
            fav_champ_ids += row.lolfeed_champ_ids
        fav_champ_ids = list(set(fav_champ_ids))


    @tasks.loop(seconds=59)
    async def lolfeed(self):
        return
        log.info("league feed every 59 seconds")
        with db.session_scope() as ses:
            fav_ch_ids = ses.query(db.g).filter_by(id=Sid.alu).first().lol_fav_champs
            for row in ses.query(db.l).filter(db.l.name.in_(get_db_online_streams(db.l, session=ses))).all():
                try:
                    live_game = await lol.spectator.CurrentGame(summoner_id=row.id, platform=row.region).get()
                    # https://static.developer.riotgames.com/docs/lol/queues.json
                    # says 420 is 5v5 Ranked Solo games
                    if not hasattr(live_game, 'queue_id') or live_game.queue_id != 420:
                        continue

                    our_player = next((x for x in live_game.participants if x.summoner_id == row.id), None)

                    self.active_matches.append(
                        ActiveMatch(
                            match_id=live_game.id,
                            start_time=round(live_game.start_time_millis / 1000),
                            stream=row.name,
                            twtv_id=row.twtv_id,
                            champ_id=our_player.champion_id,
                            champ_ids=[player.champion_id for player in live_game.participants]
                        )
                    )

                    # print(row.name, row.lastposted, live_game.id)
                    if row.lastposted != live_game.id:
                        our_player = [player for player in live_game.participants if player.summoner_id == row.id][0]
                        if our_player.champion_id in fav_ch_ids:
                            role_mini_list = await get_role_mini_list(
                                [player.champion_id for player in live_game.participants]
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

class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    region: Literal['br', 'eun', 'euw', 'jp', 'kr', 'lan', 'las', 'na', 'oc', 'ru', 'tr']
    accname: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    region: Optional[Literal['br', 'eun', 'euw', 'jp', 'kr', 'lan', 'las', 'na', 'oc', 'ru', 'tr']]
    accname: Optional[str]


class LoLFeedTools(commands.Cog, name='LoL'):
    """
    Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot):
        self.bot = bot
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
    @channel.command(
        name='set',
        usage='[channel=curr]'
    )
    @app_commands.describe(channel='Choose channel for LoLFeed notifications')
    async def channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """
        Set channel to be the LoLFeed notifications channel.
        """
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            em = Embed(
                colour=Clr.error,
                description='I do not have permissions to send messages in that channel :('
            )
            return await ctx.reply(embed=em) #todo: change this to raise BotMissingPerms

        db.set_value(db.ga, ctx.guild.id, lolfeed_ch_id=channel.id)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {channel.mention} is set to be the LoLFeed channel for this server'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @channel.command(
        name='disable',
        description='Disable LoLFeed functionality.'
    )
    async def channel_disable(self, ctx: Context):
        """
        Stop getting LoLFeed notifications. \
        Data about fav champs/streamers won't be affected.
        """
        ch_id = db.get_value(db.ga, ctx.guild.id, 'lolfeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.error,
                description=f'LoLFeed channel is not set or already was reset'
            )
            return await ctx.reply(embed=em)
        db.set_value(db.ga, ctx.guild.id, lolfeed_ch_id=None)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {ch.mention} is set to be the LoLFeed channel for this server.'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @lol.group(aliases=['db'])
    async def database(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @database.command(name='list')
    async def database_list(self, ctx: Context):
        """
        List of all streamers in database \
        available for LoLFeed feature.
        """
        await ctx.defer()

        ss_dict = dict()
        for row in db.session.query(db.l):
            key = f"● [**{row.name}**](https://www.twitch.tv/{row.name})"
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(
                f"`{row.region}` - `{row.accname}`| "

            )

        ans_array = [f"{k}\n {chr(10).join(ss_dict[k])}" for k in ss_dict]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)

        await send_pages_list(
            ctx,
            ans_array,
            split_size=10,
            colour=Clr.prpl,
            title="List of LoL Streams in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}'
        )

    @is_guild_owner()
    @channel.command(name='check')
    async def channel_check(self, ctx: Context):
        """
        Check if a LoLFeed channel was set in this server.
        """
        ch_id = db.get_value(db.ga, ctx.guild.id, 'lolfeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.prpl,
                description=f'LoLFeed channel is not currently set.'
            )
            return await ctx.reply(embed=em)
        else:
            em = Embed(
                colour=Clr.prpl,
                description=f'LoLFeed channel is currently set to {ch.mention}.'
            )
            return await ctx.reply(embed=em)

    @is_owner()
    @lol.group(aliasses=['champion'])
    async def champ(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_owner()
    @champ.command()
    @app_commands.describe(champ_names='Champion name(-s)')
    async def add(self, ctx: Context, *, champ_names: str):
        """
        Add champion(-s) into list of fav champs.
        """
        hero_array = set(db.get_value(db.ga, ctx.guild.id, 'lolfeed_champ_ids'))
        for champ_str in re.split('; |, |,', champ_names):
            hero_array.add(await champion.id_by_key(champ_str))
        db.set_value(db.ga, ctx.guild.id, lolfeed_champ_ids=list(hero_array))
        await ctx.reply(Ems.PepoG)

    @is_owner()
    @champ.command()
    @app_commands.describe(champ_names='Champion name(-s)')
    async def remove(self, ctx: Context, *, champ_names: str):
        """
        Remove champion(-s) from fav champs list.
        """
        hero_array = set(db.get_value(db.ga, ctx.guild.id, 'lolfeed_champ_ids'))
        for champ_str in re.split('; |, |,', champ_names):
            hero_array.remove(await champion.id_by_key(champ_str))
        db.set_value(db.ga, ctx.guild.id, lolfeed_champ_ids=list(hero_array))
        await ctx.reply(Ems.PepoG)

    @is_owner()
    @champ.command()
    async def list(self, ctx: Context):
        """
        Show current list of favourite champions.
        """
        champ_array = db.get_value(db.ga, ctx.guild.id, 'lolfeed_champ_ids')
        answer = [f'`{await champion.key_by_id(c_id)} - {c_id}`' for c_id in champ_array]
        answer.sort()
        em = Embed(
            color=Clr.rspbrry,
            title='List of fav lol champs',
            description='\n'.join(answer)
        )
        await ctx.reply(embed=em)

    @is_owner()
    @champ.command()
    async def meraki(self, ctx: Context):
        """
        Show list of champions that are missing from Meraki JSON.
        """
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

    @is_owner()
    @lol.group(aliases=['streamer'])
    async def stream(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_owner()
    @stream.command(name='list')
    async def list_stream(self, ctx: Context):
        """
        Show current list of fav streamers with optins
        """
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

        em = Embed(
            color=Clr.prpl,
            title='List of fav lol streamers',
            description="\n".join(sorted([f'{k}{" ".join(ans_dict[k])}' for k in ans_dict], key=str.casefold))
        )
        await ctx.reply(embed=em)

    @is_owner()
    @stream.command(name='add')
    @app_commands.describe(
        twitch='Twitch name',
        region='League account region, i.e. `euw`, `na`',
        accname='Summoner name for league account'
    )
    async def add_stream(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Add account to the database
        """
        platform = region_to_platform(flags.region)
        summoner = await lol.summoner.Summoner(name=flags.accname, platform=platform).get()
        if db.session.query(db.l).filter_by(id=summoner.id).first() is None:
            db.add_row(db.l, summoner.id, name=flags.twitch.lower(), region=platform, accname=flags.accname)
        await ctx.reply(Ems.PepoG)

    @is_owner()
    @stream.command(name='remove')
    @app_commands.describe(
        twitch='Twitch name',
        region='League account region, i.e. `euw`, `na`',
        accname='Summoner name for league account'
    )
    async def remove_stream(self, ctx: Context, *, flags: RemoveStreamFlags):
        """
        Remove account(-s) of some streamer from the database
        """
        map_dict = {'name': flags.twitch.lower()}
        if flags.region:
            map_dict['region'] = region_to_platform(flags.region)
        if flags.accname:
            map_dict['accname'] = flags.accname

        #my_dict = {k: v for k, v in dict(flags).items() if v is not None}
        with db.session_scope() as ses:
            ses.query(db.l).filter_by(**map_dict).delete()
        await ctx.reply(Ems.PepoG)

    @is_owner()
    @stream.command(
        help=f'Opt the streamer `in` or `out` from {cmntn(Cid.alubot)} channel',
        usage='<twitch_name> in/out',
        aliases=['turn']
    )
    @app_commands.describe(
        twitch='Twitch name'
    )
    async def opt(self, ctx: Context, in_or_out: inout_to_10, twitch: str):
        """Read above"""
        db.set_value_by_name(db.l, twitch, optin=in_or_out)
        await ctx.reply(Ems.PepoG)


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
