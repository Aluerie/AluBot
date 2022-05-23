from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed
from discord.ext import commands, tasks

from utils import pages
from utils import dota as d2
from utils import database as db

from utils.var import *
from utils.imgtools import plt_to_file
from utils.distools import ansi, scnf
from utils.mysteam import sd_login

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
    (7, 22): 'RR',  # Ranked
    (0, 23): 'TU',  # Turbo
    (0, 22): 'AP',  # Normal All Pick
    (0, 19): 'EV',  # Event
    (0, 12): 'LP',  # Low Priority
    (0, 5): 'SD',   # SingleDraft
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
        self.help_category = 'Irene'

    @commands.hybrid_group(
        name='irene'
    )
    async def irene(self, ctx: Context):
        """Group command about Irene, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @irene.command(
        name='lm',
        brief=Ems.slash,
        description="View Irene's last played Dota 2 match",
        aliases=['lastmatch']
    )
    async def lm(self, ctx: Context):
        """Irene's last played Dota 2 match id"""
        await ctx.typing()
        res = try_get_gamerstats(ctx.bot, start_at_match_id=0, matches_requested=1)
        em = Embed(colour=Clr.prpl).set_author(name='Irene\'s last match id')
        em.description = f'`{res[0].match_id}`'
        return await ctx.reply(embed=em)

    @irene.command(
        name='wl',
        brief=Ems.slash,
        description="Irene's Win - Loss ratio in Dota 2 games for today",
        aliases=['winrate']
    )
    async def wl(self, ctx: Context):
        """Irene's Win - Loss ratio in Dota 2 games for today"""
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
                    embed.set_author(name='Irene\'s WL for today')
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

    @irene.command(
        name='dh',
        brief=Ems.slash,
        description="Irene's Dota 2 Match History (shows last 100 matches)",
        aliases=['dotahistory']
    )
    async def dh(self, ctx: Context):
        """Irene's Dota 2 Match History (shows last 100 matches)"""
        await ctx.typing()

        def winlose(truefalse):
            return ansi('Win', colour='green') if truefalse else ansi('Loss', colour='red')

        def timestamptostr(your_timestamp):
            dtime = datetime.fromtimestamp(your_timestamp)
            return dtime.strftime("%d/%m %H:%M")

        start_at_match_id = 0
        answer = []
        for _ in range(5):
            res = try_get_gamerstats(ctx.bot, start_at_match_id=start_at_match_id)
            max_hero_len = max([len(await d2.name_by_id(x.hero_id)) for x in res])
            answer.append([
                ansi(timestamptostr(x.start_time), colour='pink') + " " +
                ansi(x.match_id, colour='cyan') + " " +
                ansi(get_match_type_name(x.lobby_type, x.game_mode), colour='blue') + " " +
                ansi((await d2.name_by_id(x.hero_id)).ljust(max_hero_len, ' '), colour='yellow') + " " +
                winlose(x.winner)
                for x in res
            ])
            start_at_match_id = res[-1].match_id

        embeds_list = []
        for item in answer:
            embed = Embed(colour=Clr.prpl)
            embed.title = "Irene's Dota 2 match history"
            ans = '```ansi\n'
            ans += '\n'.join(item)
            ans += '```'
            embed.description = ans
            embeds_list.append(embed)
        paginator = pages.Paginator(pages=embeds_list)
        await paginator.send(ctx)

    @irene.command(
        name='mmr',
        brief=Ems.slash,
        description="Irene's Dota 2 MMR Plot"
    ) 
    async def mmr_slh(self, ctx: Context):
        """Irene's Dota 2 MMr Plot"""
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
        plt.title(f'Irene\'s MMR Plot - this plot gets updated twice a day (6:45am/pm)')
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
