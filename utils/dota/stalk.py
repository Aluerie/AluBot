from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import matplotlib.colors as mcolors
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon

from utils.var import MP, Clr

from ..dota import hero

if TYPE_CHECKING:
    from asyncpg import Pool

    from utils.bot import AluBot


class MatchHistoryData:
    def __init__(
        self,
        *,
        match_id: int,
        hero_id: int,
        start_time: int,
        lane_selection_flags: int,
        match_outcome: int,
        player_slot: int,
        pool: Pool,
    ):
        self.id = match_id
        self.hero_id = hero_id
        self.start_time = start_time
        role_dict = {
            0: 0,
            1: 1,
            2: 3,
            4: 2,
            8: 4,
            16: 5,
        }
        self.role = role_dict[lane_selection_flags]
        self.pool = pool

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

    async def add_to_database(self):
        if self.winloss != -1:  # NotScored
            last_recorded_match = db.session.query(db.dh).order_by(db.dh.id.desc()).limit(1).first()  # type: ignore

            def new_mmr(prev_mmr):
                return prev_mmr + 30 if self.winloss else prev_mmr - 30

            mmr = new_mmr(last_recorded_match.mmr)

            query = """ INSERT INTO dotahistory 
                        (hero_id, winloss, mmr, role, dtime)
                        VALUES ($1, $2, $3, $4, $5)
                    """
            await self.pool.execute(
                query, self.id, self.hero_id, self.winloss, mmr, self.role, datetime.fromtimestamp(self.start_time)
            )


def fancy_ax(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    return ax


async def generate_data(pool: Pool):
    query = """ SELECT mmr
                FROM dotahistory
                ORDER BY id DESC 
            """
    rows = await pool.fetch(query)

    mmrs = np.array([row.mmr for row in rows])
    x = np.array(range(0, len(mmrs)))
    y = mmrs
    return x, y


def gradient_fill(x, y, fill_color=None, ax=None, **kwargs):
    """Plot a line with a linear alpha gradient filled beneath it.

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

    (line,) = ax.plot(x, y, **kwargs)
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
    im = ax.imshow(z, aspect='auto', extent=[xmin, xmax, ymin, ymax], origin='lower', zorder=zorder)

    xy = np.column_stack([x, y])
    xy = np.vstack([[xmin, ymin], xy, [xmax, ymin], [xmin, ymin]])
    clip_path = Polygon(xy, facecolor='none', edgecolor='none', closed=True)
    ax.add_patch(clip_path)
    im.set_clip_path(clip_path)

    ax.autoscale(True)
    return line, im


async def mmr_by_hero_bar(bot: AluBot, ax, hero_stats_dict: dict):
    hero_list = list(hero_stats_dict.keys())
    x_list = list(range(len(hero_stats_dict.keys())))
    y_list = [(v['wins'] - v['losses']) * 30 for v in hero_stats_dict.values()]

    for count, (hero_id, y) in enumerate(zip(hero_list, y_list), start=0):
        hero_icon = await bot.imgtools.url_to_img(url=await hero.icon_url_by_id(hero_id))
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
    return ax


async def heroes_played_bar(bot: AluBot, ax, sorted_dict):
    hero_list = list(sorted_dict.keys())

    y_list = range(len(sorted_dict.keys()))
    w_list = [(v['wins']) for v in sorted_dict.values()]
    l_list = [(v['losses']) for v in sorted_dict.values()]
    sum_list = [x + y for x, y in zip(w_list, l_list)]

    for count, (hero_id, y) in enumerate(zip(hero_list, y_list)):
        hero_icon = await bot.imgtools.url_to_img(url=await hero.icon_url_by_id(hero_id))
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
    return ax
