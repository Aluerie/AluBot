from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

from config import RIOT_API_KEY

from pyot.conf.model import activate_model, ModelConf
from pyot.conf.pipeline import activate_pipeline, PipelineConf
from pyot.utils.functools import async_property

from utils.feedtools import FeedTools
from utils.twitch import get_lol_streams


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
            "api_key": RIOT_API_KEY,
        }
    ]


from pyot.models import lol
from pyot.utils.lol import champion, cdragon
from pyot.models.lol import Spell, Rune, Match
from pyot.core.exceptions import NotFound, ServerError

from discord import Embed, app_commands, TextChannel
from discord.ext import commands, tasks

from utils import database as db
from utils.checks import is_owner, is_guild_owner, is_trustee
from utils.var import *
from utils.lol import get_role_mini_list, get_diff_list
from utils.distools import send_traceback, send_pages_list
from utils.format import display_relativehmstime
from utils.imgtools import img_to_file, url_to_img, get_wh
from cogs.twtv import TwitchStream

from roleidentification import pull_data
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, time
import re

import logging
log = logging.getLogger("pyot")
log.setLevel(logging.ERROR)

if TYPE_CHECKING:
    from utils.context import Context
    from aiohttp import ClientSession
    from pyot.models.lol.match import MatchParticipantData
    from utils.bot import AluBot

platform_to_routing_dict = {
    'br1': 'americas',
    'eun1': 'europe',
    'euw1': 'europe',
    'jp1': 'asia',
    'kr': 'asia',
    'la1': 'americas',
    'la2': 'americas',
    'na1': 'americas',
    'oc1': 'asia',
    'ru': 'europe',
    'tr1': 'europe'
}

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


def region_to_platform(region: str):
    """
    Converter for the flag
    """
    return region_to_platform_dict[region.lower()]


platform_to_region_dict = {
    v: k
    for k, v in region_to_platform_dict.items()
}


def platform_to_region(platform: str):
    return platform_to_region_dict[platform.lower()]


def opgg_link(platform: str, acc_name: str):
    region = platform_to_region(platform)
    return f'https://{region}.op.gg/summoners/{region}/{acc_name.replace(" ", "")}'


def ugg_link(platform: str, acc_name: str):
    return f'https://u.gg/lol/profile/{platform}/{acc_name.replace(" ", "")}'


def get_str_match_id(platform: str, match_id: int) -> str:
    return f'{platform.upper()}_{match_id}'


class ActiveMatch:

    def __init__(
            self,
            *,
            match_id: int,
            start_time: int,
            stream: str,
            twtv_id: int,
            champ_id: int,
            champ_ids: List[int],
            platform: str,
            accname: str,
            spells: List[Spell],
            runes: List[Rune]
    ):
        self.match_id = match_id
        self.start_time = start_time
        self.stream = stream
        self.twtv_id = twtv_id
        self.champ_id = champ_id
        self.champ_ids = champ_ids
        self.platform = platform
        self.accname = accname
        self.spells = spells
        self.runes = runes

    @property
    def long_ago(self):
        if self.start_time:
            return int(datetime.now(timezone.utc).timestamp() - self.start_time)
        else:
            return self.start_time

    @async_property
    async def roles_arr(self):
        return await get_role_mini_list(self.champ_ids)

    @async_property
    async def champ_name(self):
        return await champion.key_by_id(self.champ_id)

    @staticmethod
    async def iconurl_by_id(champid):
        champ = await lol.champion.Champion(id=champid).get()
        return cdragon.abs_url(champ.square_path)

    @async_property
    async def champ_icon(self):
        return await self.iconurl_by_id(self.champ_id)

    async def better_thumbnail(
            self,
            stream: TwitchStream,
            session: ClientSession,
    ):
        img = await url_to_img(session, stream.preview_url)
        width, height = img.size
        last_row_h = 50
        last_row_y = height - last_row_h
        rectangle = Image.new("RGB", (width, 100), str(Clr.rspbrry))
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)
        img.paste(rectangle, (0, last_row_y))

        champ_img_urls = [await self.iconurl_by_id(champ_id) for champ_id in await self.roles_arr]
        champ_imgs = await url_to_img(session, champ_img_urls)
        for count, champ_img in enumerate(champ_imgs):
            champ_img = champ_img.resize((62, 62))
            extra_space = 0 if count < 5 else 20
            img.paste(champ_img, (count * 62 + extra_space, 0))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
        draw = ImageDraw.Draw(img)
        text = f'{stream.display_name} - {await self.champ_name}'
        w2, h2 = get_wh(font.getbbox(text))
        draw.text(((width - w2) / 2, 65), text, font=font, align="center")

        rune_img_urls = [(await r.get()).icon_abspath for r in self.runes]
        rune_imgs = await url_to_img(session, rune_img_urls)
        left = 0
        for count, rune_img in enumerate(rune_imgs):
            if count < 6:
                rune_img = rune_img.resize((last_row_h, last_row_h))
            img.paste(rune_img, (left, height - rune_img.height), rune_img)
            left += rune_img.height

        spell_img_urls = [(await s.get()).icon_abspath for s in self.spells]
        spell_imgs = await url_to_img(session, spell_img_urls)
        left = width - 2 * last_row_h
        for count, spell_img in enumerate(spell_imgs):
            spell_img = spell_img.resize((last_row_h, last_row_h))
            img.paste(spell_img, (left + count * spell_img.width, height - spell_img.height))

        return img

    async def notif_embed(self, session: ClientSession):
        log.info("sending league embed")
        twitch = TwitchStream(self.twtv_id)
        image_name = \
            f'{twitch.display_name.replace("_", "")}-is-playing-' \
            f'{(await self.champ_name).replace(" ", "")}.png'
        img_file = img_to_file(
            await self.better_thumbnail(twitch, session),
            filename=image_name
        )

        em = Embed(
            color=Clr.rspbrry,
            url=twitch.url,
            description=
            f'Match `{self.match_id}` started {display_relativehmstime(self.long_ago)}\n'
            f'{twitch.last_vod_link(epoch_time_ago=self.long_ago)}'
            f'/[Opgg]({opgg_link(self.platform, self.accname)})'       
            f'/[Ugg]({ugg_link(self.platform, self.accname)})'
        ).set_image(
            url=f'attachment://{image_name}'
        ).set_thumbnail(
            url=await self.champ_icon
        ).set_author(
            name=f'{twitch.display_name} - {await self.champ_name}',
            url=twitch.url,
            icon_url=twitch.logo_url
        )
        return em, img_file


class MatchToEdit:

    def __init__(
            self,
            match_id: str,
            participant: MatchParticipantData
    ):
        self.match_id = match_id
        self.player_id = participant.summoner_id
        self.kda = f'{participant.kills}/{participant.deaths}/{participant.assists}'
        self.outcome = "Win" if participant.win else "Loss"
        self.items = participant.items

    async def edit_the_image(self, img_url, session):

        img = await url_to_img(session, img_url)
        width, height = img.size
        last_row_h = 50
        last_row_y = height - last_row_h
        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)

        draw = ImageDraw.Draw(img)
        w3, h3 = get_wh(font.getbbox(self.kda))
        draw.text(
            (0, height - last_row_h - h3),
            self.kda,
            font=font,
            align="right"
        )
        w2, h2 = get_wh(font.getbbox(self.outcome))
        colour_dict = {
            'Win': str(MP.green(shade=800)),
            'Loss': str(MP.red(shade=900)),
            'No Scored': (255, 255, 255)
        }
        draw.text(
            (0, height - last_row_h - h3 - h2 - 5),
            self.outcome,
            font=font,
            align="center",
            fill=colour_dict[self.outcome]
        )

        item_img_urls = [(await i.get()).icon_abspath for i in self.items if i.id]
        item_imgs = await url_to_img(session, item_img_urls, return_list=True)
        left = width - len(item_imgs) * last_row_h
        for count, item_img in enumerate(item_imgs):
            item_img = item_img.resize((last_row_h, last_row_h))
            img.paste(item_img, (left + count * item_img.width, height - last_row_h - item_img.height))
        return img


class LoLFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lolfeed.start()
        self.active_matches = []
        self.after_match = []

    def cog_unload(self) -> None:
        self.lolfeed.cancel()

    async def after_match_games(self, db_ses):
        self.after_match = []
        row_dict = {}
        for row in db_ses.query(db.lf):
            if row.match_id in row_dict:
                row_dict[row.match_id]['champ_ids'].append(row.champ_id)
            else:
                row_dict[row.match_id] = {
                    'champ_ids': [row.champ_id],
                    'routing_region': row.routing_region
                }

        for m_id in row_dict:
            try:
                match = await Match(
                    id=m_id,
                    region=row_dict[m_id]['routing_region']
                ).get()
            except NotFound:
                continue
            except ValueError:  # gosu incident ValueError: '' is not a valid platform
                continue  # TODO: remove message from the database
            for participant in match.info.participants:
                if participant.champion_id in row_dict[m_id]['champ_ids']:
                    self.after_match.append(
                        MatchToEdit(
                            participant=participant,
                            match_id=match.id
                        )
                    )

    async def edit_the_embed(self, match: MatchToEdit, ses):
        query = ses.query(db.lf).filter_by(match_id=match.match_id)
        for row in query:  # todo: huh what if there is same match id for different regions

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
            db.set_value(db.l, match.player_id, last_edited=match.match_id)
        query.delete()

    async def fill_active_matches(self, db_ses):
        self.active_matches = []
        fav_champ_ids = []
        for row in db_ses.query(db.ga):
            fav_champ_ids += row.lolfeed_champ_ids
        fav_champ_ids = list(set(fav_champ_ids))

        for row in db_ses.query(db.l).filter(db.l.twtv_id.in_(get_lol_streams())):
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
                            start_time=round(live_game.start_time_millis / 1000),
                            stream=row.name,
                            twtv_id=row.twtv_id,
                            champ_id=our_player.champion_id,
                            champ_ids=[player.champion_id for player in live_game.participants],
                            platform=our_player.platform,
                            accname=our_player.summoner_name,
                            spells=our_player.spells,
                            runes=our_player.runes
                        )
                    )
            except NotFound:
                continue
            except ServerError:
                print(f'ServerError `lolfeed.py`: {row.name} {row.region} {row.accname}')
                continue
                # embed = Embed(colour=Clr.error)
                # embed.description = f'ServerError `lolfeed.py`: {row.name} {row.region} {row.accname}'
                # await self.bot.get_channel(Cid.spam_me).send(embed=embed)  # content=umntn(Uid.alu)

    async def send_the_embed(
            self,
            match: ActiveMatch,
            db_ses
    ):
        for row in db_ses.query(db.ga):
            if match.champ_id in row.lolfeed_champ_ids and match.twtv_id in row.lolfeed_stream_ids:
                ch: TextChannel = self.bot.get_channel(row.lolfeed_ch_id)
                if ch is None:
                    continue  # the bot does not have access to the said channel
                match_id_str = get_str_match_id(match.platform, match.match_id)
                if db_ses.query(db.lf).filter_by(
                    ch_id=ch.id,
                    match_id=match_id_str,
                    champ_id=match.champ_id
                ).first():
                    continue  # the message was already sent
                em, img_file = await match.notif_embed(self.bot.ses)
                em.title = f"{ch.guild.owner.name}'s fav champ + fav stream spotted"
                msg = await ch.send(embed=em, file=img_file)
                db.add_row(
                    db.lf,
                    msg.id,
                    match_id=match_id_str,
                    ch_id=ch.id,
                    champ_id=match.champ_id,
                    routing_region=platform_to_routing_dict[match.platform]
                )

    @tasks.loop(seconds=59)
    async def lolfeed(self):
        log.info("league feed every 59 seconds")
        with db.session_scope() as db_ses:
            await self.fill_active_matches(db_ses)
            for match in self.active_matches:
                await self.send_the_embed(match, db_ses)

            await self.after_match_games(db_ses)
            for match in self.after_match:
                await self.edit_the_embed(match, db_ses)

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


class LoLFeedTools(commands.Cog, FeedTools, name='LoL'):
    """
    Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot):
        super().__init__(
            display_name='LoLFeed',
            db_name='lolfeed',
            game_name='LoL',
            db_acc_class=db.l,
            clr=Clr.rspbrry
        )
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
            return await ctx.reply(embed=em)  # todo: change this to raise BotMissingPerms

        db.set_value(db.ga, ctx.guild.id, lolfeed_ch_id=channel.id)
        em = Embed(
            colour=Clr.rspbrry,
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
            colour=Clr.rspbrry,
            description=f'Channel {ch.mention} is set to be the LoLFeed channel for this server.'
        )
        await ctx.reply(embed=em)

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
        return \
            f"● [**{twitch}**](https://www.twitch.tv/{twitch})"

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

        twtvid_list = db.get_value(db.ga, ctx.guild.id, 'lolfeed_stream_ids')
        ss_dict = dict()
        for row in db.session.query(db.l):
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
        if (user := db.session.query(db.l).filter_by(id=lolid).first()) is not None:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name=f'This lol account is already in the database',
                value=
                f'It is marked as [{user.name}](https://www.twitch.tv/{user.name})\'s account.\n\n'
                f'Did you mean to use `$lol stream add {user.name}` to add the stream into your fav list?'
            )
            return await ctx.reply(embed=em, ephemeral=True)

        db.add_row(db.l, lolid, name=twitch, platform=platform, accname=accname, twtv_id=twtv_id)
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
        """
        Add twitch stream(-s) to the list of your fav LoL streamers.
        """
        await self.stream_add_remove(ctx, twitch_names, mode='add')

    @is_guild_owner()
    @stream.command(
        name='remove',
        usage='<twitch_name(-s)>'
    )
    @app_commands.describe(twitch_names='Name(-s) of twitch streams')
    async def stream_remove(self, ctx: Context, *, twitch_names: str):
        """
        Remove twitch stream(-s) from the list of your fav LoL streamers.
        """
        await self.stream_add_remove(ctx, twitch_names, mode='remov')

    @is_guild_owner()
    @stream.command(name='list')
    async def stream_list(self, ctx: Context):
        """
        Show current list of fav streams.
        """
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
    async def champ_add(self, ctx: commands.Context, *, champ_names: str):
        """
        Add champ(-es) to your fav champ list.
        """
        await self.champ_add_remove(ctx, champ_names, mode='add')

    @is_guild_owner()
    @champ.command(
        name='remove',
        usage='<champ_name(-s)>'
    )
    @app_commands.describe(champ_names='Champ name(-s) from League of Legends')
    async def champ_remove(self, ctx: commands.Context, *, champ_names: str):
        """
        Remove hero(-es) from your fav champs list.
        """
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
        """
        Show current list of fav champs.
        """
        hero_list = db.get_value(db.ga, ctx.guild.id, 'lolfeed_champ_ids')
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
        db.set_value(db.ga, ctx.guild.id, lolfeed_spoils_on=spoil)
        em = Embed(
            colour=Clr.rspbrry,
            description=f"Changed spoil value to {spoil}"
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


class LoLAccCheck(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    def cog_unload(self) -> None:
        self.check_acc_renames.cancel()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        log.info("league checking acc renames every 24 hours")
        with db.session_scope() as ses:
            for row in ses.query(db.l):
                person = await lol.summoner.Summoner(id=row.id, platform=row.platform).get()
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
