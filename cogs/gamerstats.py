from __future__ import annotations
from typing import TYPE_CHECKING

import vdf
from discord import Embed
from discord.ext import commands, tasks
from matplotlib import pyplot as plt
from steam.core.msg import MsgProto
from steam.enums import emsg

from utils import pages

from utils import database as db
from utils.dota import hero
from utils.dota.const import ODOTA_API_URL
from utils.dota.models import Match
from utils.dota.stalk import (
    MatchHistoryData,
    fancy_ax,
    generate_data,
    gradient_fill,
    mmr_by_hero_bar,
    heroes_played_bar
)

from utils.var import *
from utils.imgtools import img_to_file, url_to_img, plt_to_file, get_wh
from utils.distools import send_pages_list
from utils.format import indent

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, timezone, time
from os import getenv

import logging

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot

log = logging.getLogger('root')
log.setLevel(logging.WARNING)

DOTA_FRIENDID = int(getenv('DOTA_FRIENDID'))

send_matches = []

lobby_type_dict = {
    -1: 'Invalid', 0: 'Casual', 1: 'Practice', 2: 'Tournament', 4: 'CoopBot', 5: 'LegacyTeam', 6: 'LegacySoloQ',
    7: 'Ranked', 8: 'Casual1v1', 9: 'WeekendTourney', 10: 'LocalBot', 11: 'Spectator'
}

game_mode_dict = {
    1: 'None', 2: 'AP', 3: 'CM', 4: 'RD', 5: 'SD', 6: 'Intro', 7: 'HW', 8: 'Reverse CM', 9: 'XMAS', 10: 'Tutorial',
    11: 'MO', 12: 'LP', 13: 'Pool1', 14: 'FH', 15: 'Custom', 16: 'CD', 17: 'BD', 18: 'AD', 19: 'Event', 20: 'ARDM',
    21: '1v1Mid', 22: 'All Draft', 23: 'Turbo', 24: 'Mutation', 25: 'Coach'
}
both_dict = {
    (7, 22): 'Ranked',  # Ranked
    (0, 23): 'Turbo',  # Turbo
    (0, 22): 'All Pick',  # Normal All Pick
    (0, 19): 'Event',  # Event
    (0, 12): 'LowPriority',  # Low Priority
    (0, 5):  'SingleDraft',   # SingleDraft
}


def get_match_type_name(lobby_type, game_mode):
    res = both_dict.get((lobby_type, game_mode))
    if res is not None:
        return res
    else:
        return f'{lobby_type_dict.get(lobby_type)}-{game_mode_dict.get(game_mode)}'


def try_get_gamerstats(bot, start_at_match_id=0, matches_requested=20):
    log.info("try_get_gamerstats dota2info")
    global send_matches
    bot.steam_dota_login()

    def ready_function():
        log.info("ready_function gamerstats")
        bot.dota.request_player_match_history(
            account_id=DOTA_FRIENDID,
            matches_requested=matches_requested,
            start_at_match_id=start_at_match_id,
            )

    def response(request_id, matches):
        global send_matches
        print(1)
        send_matches = matches
        bot.dota.emit('player_match_history_response')

    bot.dota.once('player_match_history', response)
    ready_function()
    bot.dota.wait_event('player_match_history_response', timeout=20)
    return send_matches


class GamerStats(commands.Cog, name='Stalk Aluerie\'s Gamer Stats'):
    """
    Stalk match history, ranked infographics and much more.

    You can get various information about Aluerie's Dota 2 progress.
    """
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.TwoBButt
        self.current_match_data: MatchHistoryData = None  # type: ignore
        self.new_matches_for_history = []
        self.match_history_refresh.start()

    @commands.hybrid_group()
    async def stalk(self, ctx: Context):
        """Group command about stalking Aluerie, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @stalk.command(
        name='lm',
        description="View Aluerie's last played Dota 2 match",
        aliases=['lastmatch']
    )
    async def lm(self, ctx: Context):
        """Aluerie's last played Dota 2 match id"""
        await ctx.typing()
        res = try_get_gamerstats(ctx.bot, start_at_match_id=0, matches_requested=1)
        em = Embed(
            colour=Clr.prpl,
            description=f'`{res[0].match_id}`'
        ).set_author(name='Aluerie\'s last match id')
        return await ctx.reply(embed=em)

    @stalk.command(
        name='wl',
        description="Aluerie's Win - Loss ratio in Dota 2 games for today",
        aliases=['winrate']
    )
    async def wl(self, ctx: Context):
        """Aluerie's Win - Loss ratio in Dota 2 games for today"""
        await ctx.typing()
        res = try_get_gamerstats(ctx.bot, start_at_match_id=0)

        def get_morning_time():
            now = datetime.now(timezone.utc)
            morning = now.replace(hour=3, minute=45, second=0)
            if now < morning:
                morning -= timedelta(days=1)
            return int(morning.timestamp())

        morning_time = get_morning_time()
        start_at_match_id = 0
        dict_answer = {'Ranked': {'W': 0, 'L': 0}, 'Unranked': {'W': 0, 'L': 0}}
        for _ in range(5):
            for match in try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id):
                if match.start_time < morning_time:
                    embed = Embed(colour=Clr.prpl)
                    embed.set_author(name='Aluerie\'s WL for today')
                    max_len = max([len(key) for key in dict_answer])
                    ans = [
                        f'`{key.ljust(max_len)} W {dict_answer[key]["W"]} - L {dict_answer[key]["L"]}`'
                        for key in dict_answer
                    ]
                    embed.description = '\n'.join(ans)
                    return await ctx.reply(embed=embed)

                match match.lobby_type:
                    case 7:
                        mode = 'Ranked'
                    case _:
                        mode = 'Unranked'

                if match.winner:
                    dict_answer[mode]['W'] += 1
                else:
                    dict_answer[mode]['L'] += 1
            start_at_match_id = res[-1].match_id

    @stalk.command(
        name='dh',
        description="Aluerie's Dota 2 Match History (shows last 100 matches)",
        aliases=['dotahistory']
    )
    async def dh(self, ctx: Context):
        """Aluerie's Dota 2 Match History (shows last 100 matches)"""
        await ctx.typing()

        async def create_dh_image(result, offset):
            time_font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 25)
            font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 40)

            img = Image.new("RGB", (1200, 1200), '#9678b6')
            d = ImageDraw.Draw(img)
            cell_h = img.height / 20
            col0 = 80
            col1 = 160
            col2 = 210
            h_width, h_height = 106, 60  # 62/35 ratio for dota hero icons
            col3 = 464
            col4 = 180
            for c, x in enumerate(result):
                counter_text = str(c + offset)
                w0, h0 = get_wh(font.getbbox(counter_text))
                d.text(
                    (0 + (col0 - w0)/2, cell_h * c + (cell_h - h0) / 2),
                    counter_text,
                    fill=(255, 255, 255),
                    font=font
                )

                time_text = datetime.fromtimestamp(x.start_time).strftime("%H:%M %d/%m")
                w1, h1 = get_wh(time_font.getbbox(time_text))
                d.text(
                    (col0 + (col1 - w1)/2, cell_h * c + (cell_h - h1) / 2),
                    time_text,
                    fill=(255, 255, 255),
                    font=time_font
                )

                mode_text = get_match_type_name(x.lobby_type, x.game_mode)
                w2, h2 = get_wh(font.getbbox(mode_text))
                d.text(
                    (col0 + col1 + (col2 - w2)/2, cell_h * c + (cell_h - h2) / 2),
                    mode_text,
                    fill=(255, 255, 255),
                    font=font
                )

                hero_img = await url_to_img(self.bot.ses, await hero.imgurl_by_id(x.hero_id))
                hero_img = hero_img.resize((h_width, h_height))
                img.paste(hero_img, (col0 + col1 + col2, int(cell_h * c)))

                hero_text = await hero.name_by_id(x.hero_id)
                w3, h3 = get_wh(font.getbbox(hero_text))
                d.text(
                    (col0 + col1 + col2 + h_width + (col3-w3)/2, cell_h * c + (cell_h - h3)/2),
                    hero_text,
                    fill=(255, 255, 255),
                    font=font
                )

                wl_text = 'Win' if x.winner else 'Loss'
                w4, h4 = get_wh(font.getbbox(wl_text))
                d.text(
                    (col0 + col1 + col2 + h_width + col3 + (col4-w4)/2, cell_h * c + (cell_h - h3)/2),
                    wl_text,
                    fill=str(MP.green(shade=800)) if x.winner else str(MP.red(shade=900)),
                    font=font,
                )
            return img

        start_at_match_id = 0
        files_list = []
        offset = 1
        for i in range(5):
            res = try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id)
            files_list.append(img_to_file(await create_dh_image(res, offset), filename=f'page_{i}.png'))
            start_at_match_id = res[-1].match_id
            offset += 20

        pages_list = []
        for item in files_list:
            em = Embed(
                colour=Clr.prpl,
                title="Aluerie's Dota 2 match history"
            ).set_image(
                url=f'attachment://{item.filename}'
            ).set_footer(
                text='for copypastable match_ids use `$stalk match_ids`'
            )
            pages_list.append(pages.Page(embeds=[em], files=[item]))

        await pages.Paginator(pages=pages_list).send(ctx)

    @dh.error
    async def dh_error(self, ctx, error):
        if isinstance(error.original, IndexError):
            ctx.error_handled = True
            em = Embed(
                colour=Clr.error,
                description='Oups, logging into steam took too long, please retry in a bit ;'
            ).set_author(
                name='SteamLoginError'
            ).set_footer(
                text='If this happens again, then @ Aluerie, please'
            )
            await ctx.send(embed=em)

    @stalk.command(
        name='match_ids',
        description="Copypastable match ids"
    )
    async def match_ids(self, ctx: Context):
        """Copypastable match ids"""
        await ctx.typing()
        start_at_match_id = 0
        string_list = []
        split_size = 20
        offset = 1
        for i in range(5):
            res = try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id)
            max_hero_len = max([len(await hero.name_by_id(x.hero_id)) for x in res])
            for c, x in enumerate(res):
                string_list.append(
                    f'`{indent(c+offset, c+offset, offset, split_size)} '
                    f'{x.match_id} '
                    f'{(await hero.name_by_id(x.hero_id)).ljust(max_hero_len, " ")} '
                    f'{"Win " if x.winner else "Loss"}` '
                    f'{Match(x.match_id).links()}'
                )
            start_at_match_id = res[-1].match_id
            offset += 20

        await send_pages_list(
            ctx,
            string_list,
            split_size=split_size,
            colour=Clr.prpl,
            title="Copypastable match ids",
        )

    def request_player_match_history(self, start_at_match_id=0, matches_requested=20):
        log.info("try_get_gamerstats dota2info")
        self.bot.steam_dota_login()

        def ready_function():
            log.info("ready_function gamerstats")
            self.bot.dota.request_player_match_history(
                account_id=DOTA_FRIENDID,
                matches_requested=matches_requested,
                start_at_match_id=start_at_match_id,
            )

        def response(_, matches):  # "_" is request_id
            self.new_matches_for_history = matches
            self.bot.dota.emit('player_match_history_response')

        self.bot.dota.once('player_match_history', response)
        ready_function()
        self.bot.dota.wait_event('player_match_history_response', timeout=20)

    def request_match_details(self, match_id=0, prev_mmr=0):
        log.info("try_get_gamerstats dota2info")
        self.current_match_data = None
        self.bot.steam_dota_login()

        def ready_function():
            log.info("ready_function gamerstats")
            self.bot.dota.request_match_details(
                match_id=match_id
            )

        def response(_match_id, _eresult, match):
            for p in match.players:
                if p.account_id == DOTA_FRIENDID:
                    self.current_match_data = MatchHistoryData(
                        match_id=match.match_id,
                        hero_id=p.hero_id,
                        start_time=match.startTime,
                        lane_selection_flags=getattr(p, 'lane_selection_flags', None),
                        match_outcome=match.match_outcome,
                        player_slot=p.player_slot
                    )
            self.bot.dota.emit('match_details_response')

        self.bot.dota.once('match_details', response)
        ready_function()
        self.bot.dota.wait_event('match_details_response', timeout=20)

    @commands.hybrid_group()
    async def ranked(self, ctx: Context):
        """Group command"""
        await ctx.scnf()

    async def sync_work(self):
        self.request_player_match_history()
        last_recorded_match = db.session.query(db.dh).order_by(db.dh.id.desc()).limit(1).first()  # type: ignore
        for m in reversed(self.new_matches_for_history):
            if m.match_id > last_recorded_match.id and m.lobby_type == 7:
                self.request_match_details(m.match_id)
                self.current_match_data.add_to_database()
            else:
                continue

    @ranked.command()
    async def sync(self, ctx: Context):
        """Sync information for Irene's ranked infographics"""
        await ctx.typing()
        await self.sync_work()
        em = Embed(
            colour=Clr.prpl,
            description='Sync was done'
        )
        await ctx.reply(embed=em)

    @tasks.loop(time=[time(hour=3, minute=45, tzinfo=timezone.utc), time(hour=15, minute=45, tzinfo=timezone.utc)])
    async def match_history_refresh(self):
        """
        url = "https://www.dota2.com/patches/"
        async with self.bot.ses.get(url) as resp:
            soup = BeautifulSoup(await resp.read(), 'html.parser')

        print(soup)
        """
        await self.sync_work()

    @match_history_refresh.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @ranked.command(aliases=['infographics'])
    async def info(self, ctx: Context):
        """Infographics about Aluerie ranked adventure"""
        await ctx.typing()
        hero_stats_dict = {}

        for row in db.session.query(db.dh):
            def fill_the_dict():
                if row.winloss:
                    hero_stats_dict[row.hero_id]['wins'] += 1
                else:
                    hero_stats_dict[row.hero_id]['losses'] += 1

            if row.hero_id not in hero_stats_dict:
                hero_stats_dict[row.hero_id] = {'wins': 0, 'losses': 0}
            fill_the_dict()

        sorted_dict = dict(sorted(hero_stats_dict.items(), key=lambda x: sum(x[1].values()), reverse=False))

        def winrate():
            wins = sum(v['wins'] for v in hero_stats_dict.values())
            losses = sum(v['losses'] for v in hero_stats_dict.values())
            winrate = 100 * wins / (wins + losses)
            return f'{winrate:2.2f}%'

        plt.rc('figure', facecolor=str(MP.gray(shade=300)))
        fig = plt.figure(figsize=(10, 12), dpi=300, constrained_layout=True)
        gs = fig.add_gridspec(nrows=7, ncols=10)

        axText = fig.add_subplot(gs[0, :])
        axText.annotate(
            'Aluerie\'s ranked grind', (0.5, 0.5),
            xycoords='axes fraction', va='center', ha='center', fontsize=23, fontweight='black'
        )
        axText.get_xaxis().set_visible(False)
        axText.get_yaxis().set_visible(False)
        axText = fancy_ax(axText)

        ax = fig.add_subplot(gs[2:5, 0:10])
        gradient_fill(*generate_data(), color=str(Clr.twitch), ax=ax, linewidth=5.0, marker='o')
        ax.set_title('MMR Plot', x=0.5, y=0.92)
        ax.tick_params(axis="y", direction="in", pad=-42)
        ax.tick_params(axis="x", direction="in", pad=-25)
        ax = fancy_ax(ax)

        ax = fig.add_subplot(gs[5:8, 0:6])
        ax = await mmr_by_hero_bar(self.bot.ses, ax, sorted_dict)

        ax = fig.add_subplot(gs[5:8, 6:10])
        ax = await heroes_played_bar(self.bot.ses, ax, sorted_dict)

        data_info = {
            'Final MMR': db.session.query(db.dh.mmr).order_by(db.dh.id.desc()).limit(1).first().mmr,  # type: ignore
            'Total Games': len([row for row in db.session.query(db.dh)]),
            'Winrate': winrate(),
            'Heroes Played': len(sorted_dict)
        }

        for i, (k, v) in enumerate(data_info.items(), start=0):
            left, right = i*2, i*2+2
            axRain = fig.add_subplot(gs[1, left:right], ylim=(-30, 30))
            axRain.set_title(f'{k}', x=0.5, y=0.6)
            axRain.annotate(
                f'{v}', (0.5, 0.4),
                xycoords='axes fraction', va='center', ha='center', fontsize=20, fontweight='black'
            )
            axRain.get_xaxis().set_visible(False)
            axRain.get_yaxis().set_visible(False)
            axRain = fancy_ax(axRain)

        last_match = db.session.query(db.dh).order_by(db.dh.id.desc()).limit(1).first()  # type: ignore

        axRain = fig.add_subplot(gs[1, 8:10], ylim=(-30, 30))
        axRain.set_title(f'Last Match', x=0.5, y=0.6)
        axRain.annotate(
            'Win' if last_match.winloss else 'Loss', (0.5, 0.5),
            xycoords='axes fraction', va='center', ha='center', fontsize=20, fontweight='black'
        )
        axRain.annotate(
            last_match.dtime.strftime("%m/%d, %H:%M"), (0.5, 0.2),
            xycoords='axes fraction', va='center', ha='center', fontsize=12
        )
        axRain = fancy_ax(axRain)
        hero_icon = await url_to_img(self.bot.ses, url=await hero.imgurl_by_id(last_match.hero_id))
        hero_icon.putalpha(200)

        axRain.imshow(hero_icon, extent=[-30, 30, -20, 20], aspect='auto')
        axRain.get_xaxis().set_visible(False)
        axRain.get_yaxis().set_visible(False)
        fig.patch.set_linewidth(4)
        fig.patch.set_edgecolor(str(Clr.prpl))
        await ctx.reply(file=plt_to_file(fig, filename='mmr.png'))


class ODotaAutoParse(commands.Cog):
    """Automatic request to parse Dota 2 matches after its completion"""
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.matches_to_parse = []
        self.active_matches = []
        self.lobby_ids = set()
        self.autoparse_task.start()

    async def get_active_matches(self):
        self.lobby_ids = set()
        self.bot.steam_dota_login()

        def ready_function():
            self.bot.dota.request_top_source_tv_games(lobby_ids=list(self.lobby_ids))

        def response(result):
            if result.specific_games:
                m_ids = [m.match_id for m in result.game_list]
                self.matches_to_parse = [m_id for m_id in self.active_matches if m_id not in m_ids]
                self.active_matches += [m_id for m_id in m_ids if m_id not in self.active_matches]
            else:
                self.matches_to_parse = self.active_matches
            #print(f'to parse {self.matches_to_parse} active {self.active_matches}')
            self.bot.dota.emit('top_games_response')

        proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
        proto_msg.header.routing_appid = 570
        steamids = [row.id for row in db.session.query(db.ap)]
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
                    self.lobby_ids.add(lobby_id)

        #print(self.lobby_ids)
        # dota.on('ready', ready_function)
        self.bot.dota.once('top_source_tv_games', response)
        ready_function()
        self.bot.dota.wait_event('top_games_response', timeout=8)

    @tasks.loop(seconds=59)
    async def autoparse_task(self):
        await self.get_active_matches()
        for m_id in self.matches_to_parse:
            #print(m_id)
            url = f"{ODOTA_API_URL}/request/{m_id}"
            async with self.bot.ses.post(url):
                pass

            url = f"{ODOTA_API_URL}/matches/{m_id}"
            async with self.bot.ses.get(url) as resp:
                dic = await resp.json()
                if dic == {"error": "Not Found"}:
                    continue

            if dic.get('players', None):
                if dic['players'][0]['purchase_log'] is not None:
                    self.active_matches.remove(m_id)

    @autoparse_task.before_loop
    async def before(self):
        log.info("dotafeed before loop wait")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(GamerStats(bot))
    await bot.add_cog(ODotaAutoParse(bot))

