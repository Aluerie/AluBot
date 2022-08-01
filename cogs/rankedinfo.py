from __future__ import annotations

import logging
from datetime import time, datetime, timezone
from os import getenv
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon

from discord import Embed
from discord.ext import commands, tasks

from utils import database as db
from utils.dota import hero
from utils.imgtools import url_to_img, plt_to_file
from utils.var import Clr, MP

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot

log = logging.getLogger('root')
log.setLevel(logging.WARNING)

DOTA_FRIENDID = int(getenv('DOTA_FRIENDID'))


class MatchHistoryData:
    def __init__(
            self,
            *,
            match_id: int,
            hero_id: int,
            start_time: int,
            lane_selection_flags: int,
            match_outcome: int,
            player_slot: int
    ):
        self.id = match_id
        self.hero_id = hero_id
        self.start_time = start_time
        role_dict = {0: 0, 1: 1, 2: 3, 4: 2, 8: 4, 16: 5, }
        self.role = role_dict[lane_selection_flags]

        def winloss():
            # https://github.com/ValvePython/dota2/blob/3ca4c43331d8bb946145ffbf92130f52e8eb024a/protobufs/dota_shared_enums.proto#L360
            if match_outcome > 60:
                return -1
            elif match_outcome == 0:
                return None
            elif match_outcome in (2, 3):  # 2 is Radiant, 3 is Dire
                if player_slot < 128:  # Am I Radiant? player slots are 0 1 2 3 4 vs 128 129 130 131 132
                    return 2 == match_outcome
                else:
                    return 3 == match_outcome
            return None
        self.winloss = winloss()

    def add_to_database(self):
        if self.winloss != -1:  # NotScored
            last_recorded_match = db.session.query(db.dh).order_by(db.dh.id.desc()).limit(1).first()  # type: ignore

            def new_mmr(prev_mmr):
                return prev_mmr + 30 if self.winloss else prev_mmr - 30
            mmr = new_mmr(last_recorded_match.mmr)

            db.add_row(
                db.dh,
                self.id,
                hero_id=self.hero_id,
                winloss=self.winloss,
                mmr=mmr,
                role=self.role,
                dtime=datetime.fromtimestamp(self.start_time),
                patch=None,
                patch_letter=None,
                custom_note=None
            )


class RankedInfo(commands.Cog, name='Ranked Infographics for Aluerie'):
    """
    A fancy infographics to show Irene's Dota 2 ranked climb.

    These commands help to see it, to sync or etc.
    """

    def __init__(self, bot):
        self.bot: AluBot = bot
        self.current_match_data: MatchHistoryData = None  # type: ignore
        self.new_matches_for_history = []
        self.match_history_refresh.start()

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
        await ctx.defer()
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

    @staticmethod
    def generate_data():
        mmrs = np.array([row.mmr for row in db.session.query(db.dh.mmr).order_by(db.dh.id.asc())]) # type: ignore
        x = np.array(range(0, len(mmrs)))
        y = mmrs
        return x, y

    @staticmethod
    def gradient_fill(x, y, fill_color=None, ax=None, **kwargs):
        """
        Plot a line with a linear alpha gradient filled beneath it.

        Parameters
        ----------
        x, y : array-like
            The data values of the line.
        fill_color : a matplotlib color specifier (string, tuple) or None
            The color for the fill. If None, the color of the line will be used.
        ax : a matplotlib Axes instance
            The axes to plot on. If None, the current pyplot axes will be used.
        Additional arguments are passed on to matplotlib's ``plot`` function.

        Returns
        -------
        line : a Line2D instance
            The line plotted.
        im : an AxesImage instance
            The transparent gradient clipped to just the area beneath the curve.
        """
        if ax is None:
            ax = plt.gca()

        line, = ax.plot(x, y, **kwargs)
        if fill_color is None:
            fill_color = line.get_color()

        zorder = line.get_zorder()
        alpha = line.get_alpha()
        alpha = 1.0 if alpha is None else alpha

        z = np.empty((100, 1, 4), dtype=float)
        rgb = mcolors.colorConverter.to_rgb(fill_color)
        z[:, :, :3] = rgb
        z[:, :, -1] = np.linspace(0.3, alpha, 100)[:, None]

        xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
        im = ax.imshow(
            z, aspect='auto', extent=[xmin, xmax, ymin, ymax],
            origin='lower', zorder=zorder
        )

        xy = np.column_stack([x, y])
        xy = np.vstack([[xmin, ymin], xy, [xmax, ymin], [xmin, ymin]])
        clip_path = Polygon(xy, facecolor='none', edgecolor='none', closed=True)
        ax.add_patch(clip_path)
        im.set_clip_path(clip_path)

        ax.autoscale(True)
        return line, im

    @ranked.command(aliases=['infographics'])
    async def info(self, ctx: Context):
        """Infographics about Aluerie ranked adventure"""
        await ctx.defer()
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

        def winrate():
            wins = sum(v['wins'] for v in hero_stats_dict.values())
            losses = sum(v['losses'] for v in hero_stats_dict.values())
            winrate = 100 * wins / (wins + losses)
            return f'{winrate:2.2f}%'

        def fancy_ax(ax):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            return ax

        # Set canvas background color the same as axes
        plt.rc('figure', facecolor=str(MP.gray(shade=300)))

        # set constrianed_layout as True to avoid axes overlap
        fig = plt.figure(figsize=(10, 12), dpi=300, constrained_layout=True)

        # Use GridSpec for customising layout
        gs = fig.add_gridspec(nrows=7, ncols=12)

        # Set up a empty axes that occupied 2 rows and 10 cols in the grid for text
        axText = fig.add_subplot(gs[0, :])
        axText.annotate(
            'Aluerie\'s ranked grind', (0.5, 0.5),
            xycoords='axes fraction', va='center', ha='center', fontsize=23, fontweight='black'
        )
        axText.get_xaxis().set_visible(False)
        axText.get_yaxis().set_visible(False)
        axText = fancy_ax(axText)

        ax = fig.add_subplot(gs[1:4, 0:10])
        self.gradient_fill(*self.generate_data(), color=str(Clr.twitch), ax=ax, linewidth=5.0, marker='o')
        ax.set_title('MMR Plot', x=0.5, y=0.92)
        ax.tick_params(axis="y", direction="in", pad=-42)
        ax.tick_params(axis="x", direction="in", pad=-25)
        ax = fancy_ax(ax)

        ax = fig.add_subplot(gs[4:7, 0:5])

        hero_list = list(hero_stats_dict.keys())
        x_list = list(range(len(hero_stats_dict.keys())))
        y_list = [(v['wins'] - v['losses']) * 30 for v in hero_stats_dict.values()]

        for count, (hero_id, y) in enumerate(zip(hero_list, y_list), start=0):
            hero_icon = await url_to_img(self.bot.ses, url=await hero.iconurl_by_id(hero_id))
            if y < 0:
                y = y - 1
            plt.imshow(hero_icon, extent=[count - 0.5, count + 0.5, y, y + 30], aspect='auto')

        profit_color = [(str(Clr.twitch) if p > 0 else str(MP.purple(shade=200))) for p in y_list]

        ax.bar(x_list, y_list, color=profit_color)
        ax.set_yticks(np.arange(min(y_list) - 60, max(y_list) + 60, 30.0))
        ax.set_xticks([])
        ax.set_aspect(1 / 30)
        ax = fancy_ax(ax)
        ax.set_title('MMR by hero', x=0.5, y=0.92)
        ax.tick_params(axis="y", direction="in", pad=-22)
        ax.tick_params(axis="x", direction="in", pad=-15)
        ax.set_xlim(-1)

        ax = fig.add_subplot(gs[4:7, 5:10])

        hero_list = list(hero_stats_dict.keys())
        sorted_dict = dict(sorted(hero_stats_dict.items(), key=lambda x: sum(x[1].values()), reverse=False))
        y_list = range(len(sorted_dict.keys()))
        w_list = [(v['wins']) for v in sorted_dict.values()]
        l_list = [(v['losses']) for v in sorted_dict.values()]
        sum_list = [x + y for x, y in zip(w_list, l_list)]

        for count, (hero_id, y) in enumerate(zip(hero_list, y_list)):
            hero_icon = await url_to_img(self.bot.ses, url=await hero.iconurl_by_id(hero_id))
            plt.imshow(hero_icon, extent=[-1, 0, count - 0.5, count + 0.5], aspect='auto')

        # profit_color = [('green' if p > 0 else 'red') for p in y_list]

        ax.barh(y_list, w_list, color=str(Clr.twitch))  # color=profit_color)
        ax.barh(y_list, l_list, color=str(MP.purple(shade=200)), left=w_list)

        ax.set_aspect(1 / 1)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax = fancy_ax(ax)
        ax.set_title('Heroes Played', x=0.5, y=0.9)
        plt.bar_label(ax.containers[1])
        ax.set_ylim(-2, max(y_list) + 3)
        ax.set_xlim(-1, max(sum_list) + 4)

        data_info = {
            'Final MMR': db.session.query(db.dh.mmr).order_by(db.dh.id.desc()).limit(1).first().mmr,  # type: ignore
            'Total Games': len([row for row in db.session.query(db.dh)]),
            'Winrate': winrate(),
            'Heroes Played': len(sorted_dict)
        }

        for i, (k, v) in enumerate(data_info.items(), start=1):
            axRain = fig.add_subplot(gs[i, 10:12], ylim=(-30, 30))
            axRain.set_title(f'{k}', x=0.5, y=0.6)
            axRain.annotate(
                f'{v}', (0.5, 0.4),
                xycoords='axes fraction', va='center', ha='center', fontsize=20, fontweight='black'
            )
            axRain.get_xaxis().set_visible(False)
            axRain.get_yaxis().set_visible(False)
            axRain = fancy_ax(axRain)

        last_match = db.session.query(db.dh).order_by(db.dh.id.desc()).limit(1).first()  # type: ignore

        axRain = fig.add_subplot(gs[6, 10:12], ylim=(-30, 30))
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


async def setup(bot):
    await bot.add_cog(RankedInfo(bot))
