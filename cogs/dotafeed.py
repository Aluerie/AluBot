from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, List

from pyot.utils.functools import async_property
from steam.core.msg import MsgProto
from steam.enums import emsg
from steam.steamid import SteamID, EType
import vdf

from discord import Embed, TextChannel, app_commands
from discord.ext import commands, tasks

from utils import database as db
from utils import dota as d2
from utils.checks import is_guild_owner, is_trustee
from utils.var import *
from utils.imgtools import img_to_file, url_to_img
from utils.format import display_relativehmstime
from utils.distools import send_traceback, send_pages_list
from cogs.twitch import TwitchStream, get_dota_streams, get_twtv_id, twitch_by_id

import re
from PIL import Image, ImageOps, ImageDraw, ImageFont
from datetime import datetime, timezone, time

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot
    from aiohttp import ClientSession

import logging
log = logging.getLogger('root')
log.setLevel(logging.WARNING)


class ActiveMatch:

    def __init__(
            self,
            *,
            match_id: int,
            start_time: int,
            stream: str,
            twtv_id: int,
            hero_id: int,
            hero_ids: List[int],
            server_steam_id: int
    ):
        self.match_id = match_id
        self.start_time = start_time
        self.stream = stream
        self.twtv_id = twtv_id
        self.hero_id = hero_id
        self.hero_ids = hero_ids
        self.server_steam_id = server_steam_id

    @async_property
    async def hero_name(self):
        return await d2.name_by_id(self.hero_id)

    async def better_thumbnail(
            self,
            stream: TwitchStream,
            session: ClientSession,
    ):
        img = await url_to_img(session, stream.preview_url)
        width, height = img.size
        rectangle = Image.new("RGB", (width, 70), '#9678b6')
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)

        for count, heroId in enumerate(self.hero_ids):
            hero_img = await url_to_img(session, await d2.iconurl_by_id(heroId))
            # h_width, h_height = heroImg.size
            hero_img = hero_img.resize((62, 35))
            hero_img = ImageOps.expand(hero_img, border=(0, 3, 0, 0), fill=Clr.dota_colour_map.get(count))
            extra_space = 0 if count < 5 else 20
            img.paste(hero_img, (count * 62 + extra_space, 0))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
        draw = ImageDraw.Draw(img)
        text = f'{stream.display_name} - {await self.hero_name}'
        w2, h2 = draw.textsize(text, font=font)
        draw.text(((width - w2) / 2, 35), text, font=font, align="center")
        return img

    async def notif_embed(
            self,
            session: ClientSession
    ):
        long_ago = datetime.now(timezone.utc).timestamp() - self.start_time

        twitch = TwitchStream(self.stream)
        image_name = \
            f'{self.stream.replace("_", "")}-playing-' \
            f'{(await self.hero_name).replace(" ", "")}.png'
        img_file = img_to_file(
            await self.better_thumbnail(twitch, session),
            filename=image_name
        )

        em = Embed(
            colour=Clr.prpl,
            url=twitch.url,
            description=
            f'`/match {self.match_id}` started {display_relativehmstime(long_ago)}\n'
            f'{f"[TwtvVOD]({link})" if (link := twitch.last_vod_link(time_ago=long_ago)) is not None else ""}'
            f'{d2.stats_sites_match_urls(self.match_id)}'
        ).set_image(
            url=f'attachment://{image_name}'
        ).set_thumbnail(
            url=await d2.iconurl_by_id(self.hero_id)
        ).set_author(
            name=f'{twitch.display_name} - {await self.hero_name}',
            url=twitch.url,
            icon_url=twitch.logo_url
        ).set_footer(
            text=f'Console: watch_server {self.server_steam_id}'
        )
        return em, img_file


class MatchToEdit:

    def __init__(
            self,
            data: dict
    ):
        self.match_id: int = data['match_id']
        self.hero_id: int = data['hero_id']
        self.outcome = "Win" if data['win'] else "Loss"
        self.ability_upgrades_arr = data['ability_upgrades_arr']
        self.items = [data[f'item_{i}'] for i in range(6)]
        self.kda = f'{data["kills"]}/{data["deaths"]}/{data["assists"]}'
        self.purchase_log = data['purchase_log']
        self.aghs_blessing = False
        self.aghs_shard = False
        permanent_buffs = data['permanent_buffs'] or []  # [] if it is None
        for pb in permanent_buffs:
            if pb['permanent_buff'] == 12:
                self.aghs_shard = True
            if pb['permanent_buff'] == 2:
                self.aghs_blessing = True

    def __repr__(self) -> str:
        pairs = ' '.join([f'{k}={v!r}' for k, v in self.__dict__.items()])
        return f'<{self.__class__.__name__} {pairs}>'

    async def edit_the_image(self, img_url, session):

        img = await url_to_img(session, img_url)

        width, height = img.size
        last_row_h = 50

        rectangle = Image.new("RGB", (width, last_row_h), '#9678b6')
        ImageDraw.Draw(rectangle)

        last_row_y = height - last_row_h
        img.paste(rectangle, (0, last_row_y))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 26)

        draw = ImageDraw.Draw(img)
        w3, h3 = draw.textsize(self.kda, font=font)
        draw.text(
            (0, height - h3),
            self.kda,
            font=font,
            align="right"
        )

        draw = ImageDraw.Draw(img)
        w2, h2 = draw.textsize(self.outcome, font=font)
        colour_dict = {
            'Win': f'#{MP.green(shade=800):x}',
            'Loss': f'#{MP.red(shade=900):x}',
            'No Scored': (255, 255, 255)
        }
        draw.text(
            (0, height - h3 - h2),
            self.outcome,
            font=font,
            align="center",
            fill=colour_dict[self.outcome]
        )

        font_m = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 19)

        async def item_timing_text(item_id, x_left):
            for i in reversed(self.purchase_log):
                if item_id == await d2.item_id_by_key(i['key']):
                    text = f"{math.ceil(i['time']/60)}m"
                    w7, h7 = draw.textsize(self.outcome, font=font_m)
                    draw.text(
                        (x_left, height-h7),
                        text,
                        font=font_m,
                        align="left"
                    )
                    return

        left_i = width - 69 * 6
        for count, itemId in enumerate(self.items):
            hero_img = await url_to_img(session, await d2.itemurl_by_id(itemId))
            # h_width, h_height = heroImg.size # naturally in (88, 64)
            hero_img = hero_img.resize((69, 50))  # 69/50 - to match 88/64
            curr_left = left_i + count * hero_img.width
            img.paste(hero_img, (curr_left, height - hero_img.height))
            await item_timing_text(itemId, curr_left)

        ability_h = 37
        for count, abilityId in enumerate(self.ability_upgrades_arr):
            abil_img = await url_to_img(session, await d2.ability_iconurl_by_id(abilityId))
            abil_img = abil_img.resize((ability_h, ability_h))
            img.paste(abil_img, (count * ability_h, last_row_y - abil_img.height))

        talent_strs = []
        for x in self.ability_upgrades_arr:
            if (dname := await d2.ability_dname_by_id(x)) is not None:
                talent_strs.append(dname)

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 12)
        for count, txt in enumerate(talent_strs):
            draw = ImageDraw.Draw(img)
            w4, h4 = draw.textsize(txt, font=font)
            draw.text(
                (width - w4, last_row_y - 30 * 2 - 22 * count),
                txt,
                font=font,
                align="right"
            )
        right = left_i
        if self.aghs_blessing:
            bless_img = await url_to_img(session, d2.lazy_aghs_bless_url)
            bless_img = bless_img.resize((48, 35))
            img.paste(bless_img, (right - bless_img.width, height - bless_img.height))
            await item_timing_text(271, right - bless_img.width)
            right -= bless_img.width
        if self.aghs_shard:
            shard_img = await url_to_img(session, d2.lazy_aghs_shard_url)
            shard_img = shard_img.resize((48, 35))
            img.paste(shard_img, (right - shard_img.width, height - shard_img.height))
            await item_timing_text(609, right - shard_img.width)

        #img.show()
        return img


class DotaFeed(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.dotafeed.start()
        self.lobby_ids = set()
        self.active_matches = []
        self.after_match = []

    async def after_match_games(self, ses):
        log.info("after match after match")
        self.after_match = []
        row_dict = {}
        for row in ses.query(db.em):
            row_dict.setdefault(row.match_id, set()).add(row.hero_id)

        for m_id in row_dict:
            url = f"https://api.opendota.com/api/request/{m_id}"
            async with self.bot.ses.post(url):
                pass
            url = f"https://api.opendota.com/api/matches/{m_id}"
            async with self.bot.ses.get(url) as resp:
                dic = await resp.json()
                if dic == {"error": "Not Found"}:
                    continue

                for player in dic['players']:
                    if player['hero_id'] in row_dict[m_id]:
                        if player['purchase_log'] is not None:
                            m = MatchToEdit(data=player)
                            self.after_match.append(m)

    async def edit_the_embed(self, match: MatchToEdit, ses):

        query = ses.query(db.em).filter_by(match_id=match.match_id)
        for row in query:

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
        query.delete()

    async def try_to_find_games(self, ses):
        log.info("TryToFindGames dota2info")

        self.active_matches = []
        self.lobby_ids = set()
        fav_hero_ids = []
        for row in ses.query(db.ga):
            fav_hero_ids += row.dotafeed_hero_ids
        fav_hero_ids = list(set(fav_hero_ids))

        self.bot.steam_dota_login()

        # @dota.on('ready')
        def ready_function():
            log.info("ready_function dota2info")
            self.bot.dota.request_top_source_tv_games(lobby_ids=list(self.lobby_ids))

        # @dota.on('top_source_tv_games')
        def response(result):
            log.info(f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games}")
            if result.specific_games:
                friendids = [r.friendid for r in ses.query(db.d.friendid)]
                for match in result.game_list:  # games
                    our_persons = [x for x in match.players if x.account_id in friendids and x.hero_id in fav_hero_ids]
                    for person in our_persons:
                        user = ses.query(db.d).filter_by(friendid=person.account_id).first()
                        self.active_matches.append(
                            ActiveMatch(
                                match_id=match.match_id,
                                start_time=match.activate_time,
                                stream=user.name,
                                twtv_id=user.twtv_id,
                                hero_id=person.hero_id,
                                hero_ids=[x.hero_id for x in match.players],
                                server_steam_id=match.server_steam_id
                            )
                        )
                log.info(f'to_be_posted {self.active_matches}')
            self.bot.dota.emit('top_games_response')

        proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
        proto_msg.header.routing_appid = 570
        steamids = [row.id for row in ses.query(db.d).filter(db.d.twtv_id.in_(get_dota_streams())).all()]
        # print(steamids)
        proto_msg.body.steamid_request.extend(steamids)
        resp = self.bot.steam.send_message_and_wait(proto_msg, emsg.EMsg.ClientRichPresenceInfo, timeout=8)
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
                            self.lobby_ids.add(lobby_id)

        # print(lobbyids)
        log.info(f'lobbyids {self.lobby_ids}')
        # dota.on('ready', ready_function)
        self.bot.dota.once('top_source_tv_games', response)
        ready_function()
        self.bot.dota.wait_event('top_games_response', timeout=8)

    async def send_the_embed(
            self,
            active_match: ActiveMatch,
            db_ses
    ):
        log.info("sending dota 2 embed")

        for row in db_ses.query(db.ga):
            if active_match.hero_id in row.dotafeed_hero_ids and active_match.twtv_id in row.dotafeed_stream_ids:
                ch: TextChannel = self.bot.get_channel(row.dotafeed_ch_id)
                if ch is None:
                    continue  # the bot does not have access to the said channel
                elif db_ses.query(db.em).filter_by(
                    ch_id=ch.id,
                    match_id=active_match.match_id,
                    hero_id=active_match.hero_id
                ).first():
                    continue  # the message was already sent
                em, img_file = await active_match.notif_embed(self.bot.ses)
                em.title = f"{ch.guild.owner.name}'s fav hero + fav stream spotted"
                msg = await ch.send(embed=em, file=img_file)
                db.add_row(
                    db.em,
                    msg.id,
                    match_id=active_match.match_id,
                    ch_id=ch.id,
                    hero_id=active_match.hero_id
                )
        return 1

    @tasks.loop(seconds=59)
    async def dotafeed(self):
        with db.session_scope() as db_ses:
            await self.try_to_find_games(db_ses)
            for match in self.active_matches:
                await self.send_the_embed(match, db_ses)

            await self.after_match_games(db_ses)
            for match in self.after_match:
                await self.edit_the_embed(match, db_ses)

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
    steam: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    twitch: str
    steam: Optional[str]


class DotaFeedTools(commands.Cog, name='Dota 2'):
    """
    Commands to set up fav hero + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if missing) and choose your favorite Dota 2 heroes. \
    The bot will send messages in a chosen channel when your fav streamer picks your fav hero.

    **Tutorial**
    1. Set channel with
    `$dota channel set #channel`
    2. Add fav streams, i.e.
    `$dota stream add gorgc, bububu`
    3. Add missing streams to `$dota database list`, i.e.
    `$dota database add twitch: cr1tdota steam: 76561197986172872`
    Only trustees can use `database add`. Others should `$dota database request` their fav streams.
    4. Add fav heroes, i.e.
    `$dota hero add Dark Willow, Mirana, Anti-Mage`
    5. Use `remove` counterpart commands to `add` to edit out streams/heroes
    *Pro-Tip.* As shown for multiple hero/stream add/remove commands - use commas to separate names
    6. Ready ! More info below
    """

    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.DankLove

    @is_guild_owner()
    @commands.hybrid_group()
    @app_commands.default_permissions(administrator=True)
    async def dota(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @dota.group()
    async def channel(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @channel.command(
        name='set',
        usage='[channel=curr]'
    )
    @app_commands.describe(channel='Choose channel for Dota2Feed notifications')
    async def channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """
        Set channel to be the DotaFeed notifications channel.
        """
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            em = Embed(
                colour=Clr.error,
                description='I do not have permissions to send messages in that channel :('
            )
            return await ctx.reply(embed=em)

        db.set_value(db.ga, ctx.guild.id, dotafeed_ch_id=channel.id)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {channel.mention} is set to be the Dota2Feed channel for this server'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @channel.command(
        name='disable',
        description='Disable Dota2Feed functionality.'
    )
    async def channel_disable(self, ctx: Context):
        """
        Stop getting DotaFeed notifs. \
        Data about fav heroes/streams won't be affected.
        """
        ch_id = db.get_value(db.ga, ctx.guild.id, 'dotafeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.error,
                description=f'Dota2Feed channel is not set or already was reset'
            )
            return await ctx.reply(embed=em)
        db.set_value(db.ga, ctx.guild.id, dotafeed_ch_id=None)
        em = Embed(
            colour=Clr.prpl,
            description=f'Channel {ch.mention} is set to be the DotaFeed channel for this server.'
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @channel.command(name='check')
    async def channel_check(self, ctx: Context):
        """
        Check if DotaFeed channel is set in the server.
        """
        ch_id = db.get_value(db.ga, ctx.guild.id, 'dotafeed_ch_id')
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.prpl,
                description=f'Dota2Feed channel is not currently set.'
            )
            return await ctx.reply(embed=em)
        else:
            em = Embed(
                colour=Clr.prpl,
                description=f'Dota2Feed channel is currently set to {ch.mention}.'
            )
            return await ctx.reply(embed=em)

    @is_guild_owner()
    @dota.group(aliases=['db'])
    async def database(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @database.command(name='list')
    async def database_list(self, ctx: Context):
        """
        List of streams in the database available for DotaFeed feature.
        """
        await ctx.defer()
        twtvid_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids')
        ss_dict = dict()
        for row in db.session.query(db.d):
            followed = f' {Ems.DankLove}' if row.twtv_id in twtvid_list else ''
            key = f"● [**{row.name}**](https://www.twitch.tv/{row.name}){followed}"
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(
                f"`{row.id}` - `{row.friendid}` "
                f"/[Steam](https://steamcommunity.com/profiles/{row.id})"
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

    @staticmethod
    def field_info_str(twitch, steamid, friendid):
        return \
            f"[**{twitch}**](https://www.twitch.tv/{twitch})\n" \
            f"`{steamid}` - `{friendid}`| " \
            f"[Steam](https://steamcommunity.com/profiles/{steamid})" \
            f"/[Dotabuff](https://www.dotabuff.com/players/{friendid})"

    @staticmethod
    async def get_steam_id_and_64(ctx: Context, steam: str):
        steam = SteamID(steam)
        if steam.type != EType.Individual:
            steam = SteamID.from_url(steam)

        if steam is None or (hasattr(steam, 'type') and steam.type != EType.Individual):
            em = Embed(
                colour=Clr.error,
                description=
                f'Error checking steam profile for {steam}.\n '
                f'Check if your `steam` flag is correct steam id in either 64/32/3/2/friendid representations '
                f'or just give steam profile link to the bot.'
            )
            await ctx.reply(embed=em, ephemeral=True)
            return None, None

        return steam.as_64, steam.id

    @staticmethod
    async def get_check_twitch_id(ctx: Context, twitch: str):
        twtv_id = get_twtv_id(twitch.lower())
        if twtv_id is None:
            em = Embed(
                colour=Clr.error,
                description=
                f'Error checking stream {twitch}.\n '
                f'User either does not exist or is banned.'
            )
            await ctx.reply(embed=em, ephemeral=True)
            return None

        return twtv_id

    @is_trustee()
    @database.command(
        name='add',
        usage='twitch: <twitch_name> steam: <steamid>',
        description='Add stream to the database.'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link'
    )
    async def database_add(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Add stream to the database.
        • `<twitch_name>` is twitch.tv name
        • `<steamid>` is either steamid in any of 64/32/3/2/friendid versions or just steam profile link.
        """
        await ctx.defer()

        twtv_id = await self.get_check_twitch_id(ctx, flags.twitch.lower())
        if twtv_id is None:
            return

        steamid, friendid = await self.get_steam_id_and_64(ctx, flags.steam)
        if steamid is None:
            return

        if (user := db.session.query(db.d).filter_by(id=steamid).first()) is not None:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name=f'This steam account is already in the database',
                value=
                f'It is marked as [{user.name}](https://www.twitch.tv/{user.name})\'s account.\n\n'
                f'Did you mean to use `$dota stream add {user.name}` to add the stream into your fav list?'
            )
            return await ctx.reply(embed=em, ephemeral=True)

        db.add_row(db.d, steamid, name=flags.twitch.lower(), friendid=friendid, twtv_id=twtv_id)
        em = Embed(
            colour=Clr.prpl
        ).add_field(
            name=f'Successfully added the account to the database',
            value=self.field_info_str(flags.twitch.lower(), steamid, friendid)
        )
        await ctx.reply(embed=em)
        em.colour = MP.green(shade=200)
        em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        await self.bot.get_channel(Cid.global_logs).send(embed=em)

    @is_trustee()
    @database.command(
        name='remove',
        usage='twitch: <twitch_name> steam: [steamid]'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link'
    )
    async def database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """
        Remove stream from the database.
        """
        await ctx.defer()

        map_dict = {'name': flags.twitch.lower()}
        if flags.steam:
            steamid, friendid = await self.get_steam_id_and_64(ctx, flags.steam)
            if steamid is None:
                return
            map_dict['id'] = steamid

        success = []
        with db.session_scope() as ses:
            query = ses.query(db.d).filter_by(**map_dict)
            for row in query:
                success.append(
                    {
                        'name': row.name,
                        'id': row.id,
                        'friendid': row.friendid
                    }
                )
            query.delete()
        if success:
            em = Embed(
                colour=Clr.prpl,
            ).add_field(
                name='Successfully removed account(-s) from the database',
                value=
                '\n'.join(self.field_info_str(x['name'], x['id'], x['friendid']) for x in success)
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
        usage='twitch: <twitch_name> steam: <steamid>',
        description='Request steam account to be added into the database.'
    )
    @app_commands.describe(
        twitch='twitch.tv stream name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link'
    )
    async def database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Request steam account to be added into the database. \
        This will send a request message into Aluerie's personal logs channel.
        """
        await ctx.defer()

        twtv_id = await self.get_check_twitch_id(ctx, flags.twitch.lower())
        if twtv_id is None:
            return

        steamid, friendid = self.get_steam_id_and_64(ctx, flags.steam)
        if steamid is None:
            return

        warn_em = Embed(
            colour=Clr.prpl,
            title='Confirmation Prompt',
            description=
            f'Are you sure you want to request this streamer steam account to be added into the database?\n'
            f'This information will be sent to Aluerie. Please, double check before confirming.'
        ).add_field(
            name='Request to add an account into the database',
            value=self.field_info_str(flags.twitch.lower(), steamid, friendid)
        )
        confirm = await ctx.prompt(embed=warn_em)
        if not confirm:
            return await ctx.send('Aborting...', delete_after=5.0)

        warn_em.colour = MP.orange(shade=200)
        warn_em.description = ''
        warn_em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        warn_em.add_field(
            name='Command',
            value=f'`$dota stream add twitch: {flags.twitch.lower()} steam: {steamid}`'
        )
        await self.bot.get_channel(Cid.global_logs).send(embed=warn_em)

    @is_guild_owner()
    @dota.group(aliases=['streamer'])
    async def stream(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    async def stream_add_remove(ctx, twitch_names, mode):
        twitch_list = set(db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids'))

        success = []
        fail = []
        already = []

        for name in re.split('; |, |,', twitch_names):
            streamer = db.session.query(db.d).filter_by(name=name.lower()).first()
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
        db.set_value(db.ga, ctx.guild.id, dotafeed_stream_ids=list(twitch_list))

        if len(success):
            em = Embed(
                colour=Clr.prpl
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
                '`$dota database add/request twitch: <twitch_name> steam: <steamid>`'
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
        Add twitch stream(-s) to your fav Dota 2 streams.
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
        Remove twitch stream(-s) from your fav Dota 2 streams.
        """
        await self.stream_add_remove(ctx, twitch_names, mode='remov')

    @is_guild_owner()
    @stream.command(name='list')
    async def stream_list(self, ctx: Context):
        """
        Show current list of fav streams.
        """
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

    @is_guild_owner()
    @dota.group()
    async def hero(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    async def hero_add_remove(ctx, hero_names, mode):
        hero_list = set(db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids'))
        success = []
        fail = []
        already = []
        for name in re.split('; |, |,', hero_names):
            try:
                if (hero_id := await d2.id_by_name(name)) is not None:
                    hero_name = f'`{await d2.name_by_id(hero_id)}`'
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

        db.set_value(db.ga, ctx.guild.id, dotafeed_hero_ids=list(hero_list))

        if len(success):
            em = Embed(
                colour=Clr.prpl
            ).add_field(
                name=f'Successfully {mode}ed following heroes',
                value=", ".join(success)
            )
            await ctx.reply(embed=em)
        if len(already):
            em = Embed(
                colour=MP.orange(shade=500)
            ).add_field(
                name=f'Hero(-s) already {"not" if mode == "remov" else ""} in fav list',
                value=", ".join(already)
            )
            await ctx.reply(embed=em)
        if len(fail):
            em = Embed(
                colour=Clr.error
            ).add_field(
                name='Could not recognize Dota 2 heroes from these names',
                value=", ".join(fail)
            ).set_footer(
                text='You can look in $help for help in hero names'
            )
            await ctx.reply(embed=em)

    @is_guild_owner()
    @hero.command(
        name='add',
        usage='<hero_name(-s)>',
        description='Add hero(-es) to your fav heroes list.'
    )
    @app_commands.describe(hero_names='Name(-s) from Dota 2 Hero grid')
    async def hero_add(self, ctx: commands.Context, *, hero_names: str):
        """
        Add hero(-es) to your fav heroes list. \
        Use names from Dota 2 hero grid. For example,
        • `Anti-Mage` (letter case does not matter) and not `Magina`;
        • `Queen of Pain` and not `QoP`.
        """
        # At last you can find proper name
        # [here](https://api.opendota.com/api/constants/heroes) with Ctrl+F \
        # under one of `"localized_name"`
        await self.hero_add_remove(ctx, hero_names, mode='add')

    @is_guild_owner()
    @hero.command(
        name='remove',
        usage='<hero_name(-s)>'
    )
    @app_commands.describe(hero_names='Name(-s) from Dota 2 Hero grid')
    async def hero_remove(self, ctx: commands.Context, *, hero_names: str):
        """
        Remove hero(-es) from your fav heroes list.
        """
        await self.hero_add_remove(ctx, hero_names, mode='remov')

    @staticmethod
    async def hero_add_remove_error(ctx: Context, error):
        if isinstance(error.original, KeyError):
            ctx.error_handled = True
            em = Embed(
                colour=Clr.error,
                description=
                f'Looks like there is no hero with name `{error.original}`. '

            ).set_author(
                name='HeroNameNotFound'
            )
            await ctx.send(embed=em)

    @hero_add.error
    async def hero_add_error(self, ctx: Context, error):
        await self.hero_add_remove_error(ctx, error)

    @hero_remove.error
    async def hero_remove_error(self, ctx: Context, error):
        await self.hero_add_remove_error(ctx, error)

    @is_guild_owner()
    @hero.command(name='list')
    async def hero_list(self, ctx: Context):
        """
        Show current list of fav heroes.
        """
        hero_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids')
        answer = [f'`{await d2.name_by_id(h_id)} - {h_id}`' for h_id in hero_list]
        answer.sort()
        em = Embed(
            color=Clr.prpl,
            title='List of fav dota 2 heroes',
            description='\n'.join(answer)
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @dota.command(description='Turn on/off spoiling resulting stats for matches. ')
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
        db.set_value(db.ga, ctx.guild.id, dotafeed_spoils_on=spoil)
        em = Embed(
            colour=Clr.prpl,
            description=f"Changed spoil value to {spoil}"
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
