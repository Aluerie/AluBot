from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed
from discord.ext import commands, tasks

from utils import pages
from utils import dota as d2
from utils import database as db

from utils.var import *
from utils.imgtools import plt_to_file, img_to_file, url_to_img
from utils.distools import scnf, send_pages_list
from utils.format import indent
from utils.mysteam import sd_login

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, time, timezone
import matplotlib.pyplot as plt
import numpy as np
from os import getenv
import logging
log = logging.getLogger('root')

if TYPE_CHECKING:
    from utils.context import Context

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
    sd_login(bot.steam, bot.dota, bot.steam_lgn, bot.steam_psw)

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


class GamerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_match_history_ctrlr.start()
        self.help_category = 'Aluerie'

    @commands.hybrid_group()
    async def stalk(self, ctx: Context):
        """Group command about stalking Aluerie, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @stalk.command(
        name='lm',
        brief=Ems.slash,
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
        brief=Ems.slash,
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
        brief=Ems.slash,
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
                w0, h0 = d.textsize(counter_text, font=font)
                d.text(
                    (0 + (col0 - w0)/2, cell_h * c + (cell_h - h0) / 2),
                    counter_text,
                    fill=(255, 255, 255),
                    font=font
                )

                time_text = datetime.fromtimestamp(x.start_time).strftime("%H:%M %d/%m")
                w1, h1 = d.textsize(time_text, font=time_font)
                d.text(
                    (col0 + (col1 - w1)/2, cell_h * c + (cell_h - h1) / 2),
                    time_text,
                    fill=(255, 255, 255),
                    font=time_font
                )

                mode_text = get_match_type_name(x.lobby_type, x.game_mode)
                w2, h2 = d.textsize(mode_text, font=font)
                d.text(
                    (col0 + col1 + (col2 - w2)/2, cell_h * c + (cell_h - h2) / 2),
                    mode_text,
                    fill=(255, 255, 255),
                    font=font
                )

                hero_img = await url_to_img(self.bot.ses, await d2.iconurl_by_id(x.hero_id))
                hero_img = hero_img.resize((h_width, h_height))
                img.paste(hero_img, (col0 + col1 + col2, int(cell_h * c)))

                hero_text = await d2.name_by_id(x.hero_id)
                w3, h3 = d.textsize(hero_text, font=font)
                d.text(
                    (col0 + col1 + col2 + h_width + (col3-w3)/2, cell_h * c + (cell_h - h3)/2),
                    hero_text,
                    fill=(255, 255, 255),
                    font=font
                )

                wl_text = 'Win' if x.winner else 'Loss'
                w4, h4 = d.textsize(wl_text, font=font)
                d.text(
                    (col0 + col1 + col2 + h_width + col3 + (col4-w4)/2, cell_h * c + (cell_h - h3)/2),
                    wl_text,
                    fill=f'#{MP.green(shade=800):x}' if x.winner else f'#{MP.red(shade=900):x}',  # Pil doesnt like ints
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
        brief=Ems.slash,
        description="Copypastable match_ids"
    )
    async def match_ids(self, ctx: Context):
        """Copypastable match_ids"""
        await ctx.typing()
        start_at_match_id = 0
        string_list = []
        split_size = 20
        offset = 1
        for i in range(5):
            res = try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id)
            max_hero_len = max([len(await d2.name_by_id(x.hero_id)) for x in res])
            for c, x in enumerate(res):
                string_list.append(
                    f'`{indent(c+offset, c+offset, offset, split_size)} '
                    f'{x.match_id} '
                    f'{(await d2.name_by_id(x.hero_id)).ljust(max_hero_len, " ")} '
                    f'{"Win " if x.winner else "Loss"}`'
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

    @stalk.command(
        name='mmr',
        brief=Ems.slash,
        description="Aluerie's Dota 2 MMR Plot"
    ) 
    async def mmr(self, ctx: Context):
        """Aluerie's Dota 2 MMr Plot"""
        await ctx.typing()
        old_dict = db.get_value(db.s, DOTA_FRIENDID, 'match_history')
        starting_mmr = 4340
        points_gain = 30

        fig = plt.figure()
        mmr = starting_mmr
        mmr_array = [mmr]
        for k in reversed(list(old_dict.keys())):
            mmr += points_gain if old_dict[k] else -points_gain
            mmr_array.append(mmr)

        plt.plot(mmr_array, label=f'MMR Plot', marker='o')
        plt.title(f'Aluerie\'s MMR Plot - this plot gets updated twice a day (6:45am/pm)')
        axes = plt.gca()
        major_xticks = np.arange(0, len(mmr_array), 1)
        major_yticks = np.arange(min(mmr_array), max(mmr_array) + points_gain, points_gain)
        axes.set_xticks(major_xticks)
        axes.set_yticks(major_yticks)
        plt.grid()
        plt.legend(fontsize='large'), plt.xlabel('Number of games'), plt.ylabel('MMR')
        fig.patch.set_facecolor('#9678B6')
        await ctx.reply(file=plt_to_file(fig, filename='mmr.png'))

    @tasks.loop(time=[time(hour=3, minute=45), time(hour=15, minute=45)])  # minus 3 hours from contracts cause utc
    async def daily_match_history_ctrlr(self):
        with db.session_scope() as ses:
            row = ses.query(db.s).filter_by(id=DOTA_FRIENDID).first()
            dict_res = {}
            for _ in range(5):
                res = try_get_gamerstats(self.bot)
                dict_res = {x.match_id: x.winner for x in res if x.lobby_type == 7} | dict_res
                if row.last_match_id in dict_res:
                    break
            old_dict = db.get_value(db.s, DOTA_FRIENDID, 'match_history')
            new_dict = dict_res | old_dict
            last_match_id = 0 if len(new_dict) == 0 else list(new_dict)[0]  # next(iter(new_dict))
            row.match_history = new_dict
            row.last_match_id = last_match_id

    @daily_match_history_ctrlr.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(GamerStats(bot))
