import re
from datetime import time, timezone
from typing import List, Literal

from discord import app_commands
from discord.ext import commands, tasks

from .utils import database as db
from .utils.distools import send_pages_list
from .utils.format import indent
from .utils.var import Clr, Rgx, Ems


def filter_emotes_condition(emote, mode):
    if mode == 1:
        return 1
    elif mode == 2 and emote.animated:
        return 1
    elif mode == 3 and not emote.animated:
        return 1
    else:
        return 0


def get_sorted_emote_dict(mode):
    user = db.session.query(db.e)
    emote_dict = {}

    def filter_mode(mod, animated):
        if mod == 1:
            return True
        elif mod == 2 and animated:
            return True
        elif mod == 3 and not animated:
            return True
        else:
            return False

    for row in user:
        if filter_mode(mode, row.animated):
            emote_dict[row.name] = sum(row.month_array)

    return {k: v for k, v in sorted(emote_dict.items(), key=lambda item: item[1], reverse=True)}


async def topemotes_job(ctx, mode):
    sorted_emote_dict = get_sorted_emote_dict(mode)
    new_array = []
    split_size = 20
    offset = 1
    max_length = 18

    for cnt, key in enumerate(sorted_emote_dict, start=offset):

        new_array.append(
            f'`{indent(cnt, cnt, offset, split_size)}` '
            f'{key}`{key.split(":")[1][:max_length].ljust(max_length, " ")}{sorted_emote_dict[key]}`'
        )
    await send_pages_list(
        ctx,
        new_array,
        split_size=split_size,
        colour=Clr.prpl,
        title="Top emotes used last month",
        footer_text=f'With love, {ctx.guild.me.display_name}',
        description_prefix=f'`{"Emote".ljust(max_length + 4, " ")}Usages`',
    )


class EmoteAnalysis(commands.Cog, name='Emote stats'):
    """
    See stats on emote usage in Aluerie's server

    The bot keeps data for one month.
    """
    def __init__(self, bot):
        self.bot = bot
        self.daily_emote_shift.start()
        self.help_emote = Ems.peepoComfy

    def cog_unload(self) -> None:
        self.daily_emote_shift.cancel()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if self.bot.yen:
            return

        if not msg.author.bot or msg.webhook_id:
            custom_emojis_ids = re.findall(Rgx.emote_stats_ids, msg.content)  # they are in str tho
            custom_emojis_ids = set(list(map(int, custom_emojis_ids)))

            for i in custom_emojis_ids:
                try:
                    emote_array = db.get_value(db.e, i, 'month_array')
                    if emote_array is not None:
                        emote_array[-1] += 1
                        db.set_value(db.e, i, month_array=emote_array)
                except AttributeError:  # emote is not in database
                    pass

    @commands.hybrid_command(
        name='topemotes',
        description='Show emotes usage stats'
    )
    @app_commands.describe(keyword='Possible keywords: `all`, `ani`, `nonani`')
    async def topemotes(self, ctx, keyword: Literal['all', 'ani', 'nonani'] = 'all'):
        """Show emotes usage stats for `keyword` group ;\
        Possible keywords: `all`, `ani` for animated emotes, `nonani` for static emotes ;"""
        match keyword:
            case 'all':
                await topemotes_job(ctx, 1)
            case 'ani' | 'animated':
                await topemotes_job(ctx, 2)
            case 'nonani' | 'static' | 'nonanimated':
                await topemotes_job(ctx, 3)

    @tasks.loop(time=time(hour=17, minute=17, tzinfo=timezone.utc))
    async def daily_emote_shift(self):
        with db.session_scope() as session:
            for row in session.query(db.e):
                def shift_list(array: List):
                    return array[1:] + [0]
                row.month_array = shift_list(row.month_array)

    @daily_emote_shift.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(EmoteAnalysis(bot))
