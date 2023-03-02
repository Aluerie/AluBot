from __future__ import annotations
from typing import TYPE_CHECKING

import datetime
import logging

import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from matplotlib import pyplot as plt

from config import DOTA_FRIENDID
from .utils import pages
from .utils.distools import send_pages_list
from .dota import hero
from utils.dota import Match
from utils.dota import (
    MatchHistoryData,
    fancy_ax,
    generate_data,
    gradient_fill,
    mmr_by_hero_bar,
    heroes_played_bar
)
from .utils.formats import indent
from .utils.imgtools import img_to_file, url_to_img, plt_to_file, get_text_wh
from .utils.var import Ems, Clr, MP

if TYPE_CHECKING:
    from .utils.context import Context
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
# log.setLevel(logging.WARNING)


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
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

        self.current_match_data: MatchHistoryData = None  # type: ignore
        self.new_matches_for_history = []

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.TwoBButt)

    async def cog_load(self) -> None:
        self.bot.ini_steam_dota()
        self.match_history_refresh.start()

    async def cog_unload(self) -> None:
        self.match_history_refresh.cancel()

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
        e = discord.Embed(description=f'`{res[0].match_id}`', colour=Clr.prpl)
        e.set_author(name='Aluerie\'s last match id')
        return await ctx.reply(embed=e)

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
            now = datetime.datetime.now(datetime.timezone.utc)
            morning = now.replace(hour=3, minute=45, second=0)
            if now < morning:
                morning -= datetime.timedelta(days=1)
            return int(morning.timestamp())

        morning_time = get_morning_time()
        start_at_match_id = 0
        dict_answer = {'Ranked': {'W': 0, 'L': 0}, 'Unranked': {'W': 0, 'L': 0}}
        for _ in range(5):
            for match in try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id):
                if match.start_time < morning_time:
                    e = discord.Embed(colour=Clr.prpl)
                    e.set_author(name='Aluerie\'s WL for today')
                    max_len = max([len(key) for key in dict_answer])
                    ans = [
                        f'`{key.ljust(max_len)} W {dict_answer[key]["W"]} - L {dict_answer[key]["L"]}`'
                        for key in dict_answer
                    ]
                    e.description = '\n'.join(ans)
                    return await ctx.reply(embed=e)

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
            time_font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 25)
            font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 40)

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
                w0, h0 = get_text_wh(counter_text, font)
                d.text(
                    (0 + (col0 - w0)/2, cell_h * c + (cell_h - h0) / 2),
                    counter_text,
                    fill=(255, 255, 255),
                    font=font
                )

                time_text = datetime.datetime.fromtimestamp(x.start_time).strftime("%H:%M %d/%m")
                w1, h1 = get_text_wh(time_text, time_font)
                d.text(
                    (col0 + (col1 - w1)/2, cell_h * c + (cell_h - h1) / 2),
                    time_text,
                    fill=(255, 255, 255),
                    font=time_font
                )

                mode_text = get_match_type_name(x.lobby_type, x.game_mode)
                w2, h2 = get_text_wh(mode_text, font)
                d.text(
                    (col0 + col1 + (col2 - w2)/2, cell_h * c + (cell_h - h2) / 2),
                    mode_text,
                    fill=(255, 255, 255),
                    font=font
                )

                hero_img = await self.bot.url_to_img(await hero.imgurl_by_id(x.hero_id))
                hero_img = hero_img.resize((h_width, h_height))
                img.paste(hero_img, (col0 + col1 + col2, int(cell_h * c)))

                hero_text = await hero.name_by_id(x.hero_id)
                w3, h3 = get_text_wh(hero_text, font)
                d.text(
                    (col0 + col1 + col2 + h_width + (col3-w3)/2, cell_h * c + (cell_h - h3)/2),
                    hero_text,
                    fill=(255, 255, 255),
                    font=font
                )

                wl_text = 'Win' if x.winner else 'Loss'
                w4, h4 = get_text_wh(wl_text, font)
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
            e = discord.Embed(title="Aluerie's Dota 2 match history", colour=Clr.prpl)
            e.set_image(url=f'attachment://{item.filename}')
            e.set_footer(text='for copypastable match_ids use `$stalk match_ids`')
            pages_list.append(pages.Page(embeds=[e], files=[item]))

        await pages.Paginator(pages=pages_list).send(ctx)

    @dh.error
    async def dh_error(self, ctx: Context, error):
        if isinstance(error.original, IndexError):
            ctx.error_handled = True
            e = discord.Embed(colour=Clr.error)
            e.description = 'Oups, logging into steam took too long, please retry in a bit'
            e.set_author(name='SteamLoginError')
            e.set_footer(text='If this happens again, then @ Aluerie, please')
            await ctx.reply(embed=e, ephemeral=True)

    @stalk.command(name='match_ids')
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
                    f'{Match(x.match_id).links}'
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
                        player_slot=p.player_slot,
                        pool=self.bot.pool
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
                await self.current_match_data.add_to_database()
            else:
                continue

    @ranked.command()
    async def sync(self, ctx: Context):
        """Sync information for Irene's ranked infographics"""
        await ctx.typing()
        await self.sync_work()
        e = discord.Embed(description='Sync was done', colour=Clr.prpl)
        await ctx.reply(embed=e)

    @tasks.loop(time=[
        datetime.time(hour=3, minute=45, tzinfo=datetime.timezone.utc),
        datetime.time(hour=15, minute=45, tzinfo=datetime.timezone.utc)]
    )
    async def match_history_refresh(self):
        """url = "https://www.dota2.com/patches/"
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

        query = 'SELECT winloss, hero_id FROM dotahistory'
        rows = await self.bot.pool.fetch(query)
        for row in rows:
            # create if it does not exist
            if row.hero_id not in hero_stats_dict:
                hero_stats_dict[row.hero_id] = {'wins': 0, 'losses': 0}
            # fill the dict
            if row.winloss:
                hero_stats_dict[row.hero_id]['wins'] += 1
            else:
                hero_stats_dict[row.hero_id]['losses'] += 1

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
        gradient_fill(*await generate_data(self.bot.pool), color=str(Clr.twitch), ax=ax, linewidth=5.0, marker='o')
        ax.set_title('MMR Plot', x=0.5, y=0.92)
        ax.tick_params(axis="y", direction="in", pad=-42)
        ax.tick_params(axis="x", direction="in", pad=-25)
        ax = fancy_ax(ax)

        ax = fig.add_subplot(gs[5:8, 0:6])
        ax = await mmr_by_hero_bar(self.bot.session, ax, sorted_dict)

        ax = fig.add_subplot(gs[5:8, 6:10])
        ax = await heroes_played_bar(self.bot.session, ax, sorted_dict)

        query = """ SELECT mmr 
                    FROM dotahistory
                    ORDER BY id DESC 
                    LIMIT 1;
                """
        final_mmr = await self.bot.pool.fetchval(query)

        query = 'SELECT count(*) FROM dotahistory'
        total_games = await self.bot.pool.fetchval(query)
        data_info = {
            'Final MMR': final_mmr,
            'Total Games': total_games,
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

        query = """ SELECT *
                    FROM dotahistory
                    ORDER BY id DESC 
                    LIMIT 1
                """
        last_match = await self.bot.pool.fetchrow(query)

        axRain = fig.add_subplot(gs[1, 8:10], ylim=(-30, 30))
        axRain.set_title(f'Last Match', x=0.5, y=0.6)
        axRain.annotate(
            'Win' if last_match['winloss'] else 'Loss', (0.5, 0.5),
            xycoords='axes fraction', va='center', ha='center', fontsize=20, fontweight='black'
        )
        axRain.annotate(
            last_match['dtime'].strftime("%m/%d, %H:%M"), (0.5, 0.2),
            xycoords='axes fraction', va='center', ha='center', fontsize=12
        )
        axRain = fancy_ax(axRain)
        hero_icon = await url_to_img(self.bot.session, url=await hero.imgurl_by_id(last_match['hero_id']))
        hero_icon.putalpha(200)

        axRain.imshow(hero_icon, extent=[-30, 30, -20, 20], aspect='auto')
        axRain.get_xaxis().set_visible(False)
        axRain.get_yaxis().set_visible(False)
        fig.patch.set_linewidth(4)
        fig.patch.set_edgecolor(str(Clr.prpl))
        await ctx.reply(file=plt_to_file(fig, filename='mmr.png'))


async def setup(bot: AluBot):
    await bot.add_cog(GamerStats(bot))
