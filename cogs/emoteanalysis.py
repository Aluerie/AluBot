from discord import Embed, option
from discord.ext import commands, tasks, pages, bridge

from utils.var import *
from utils import database as db

import re
from datetime import time, timezone
from typing import List


def filter_emotes_condition(emote, mode):
    if mode == 1:
        return 1
    elif mode == 2 and emote.animated:
        return 1
    elif mode == 3 and not emote.animated:
        return 1
    else:
        return 0


async def filter_emotes(ctx, mode):
    emotes = [str(emote) for emote in ctx.guild.emojis if not emote.managed and filter_emotes_condition(emote, mode)]
    split_size = 27
    emotes_list = [emotes[x:x + split_size] for x in range(0, len(emotes), split_size)]
    for item in emotes_list:
        await ctx.send(content=' '.join(item))


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
    for key in sorted_emote_dict:
        new_array.append([key, sorted_emote_dict[key]])

    splitedSize = 20
    places_list = [new_array[x:x + splitedSize] for x in range(0, len(new_array), splitedSize)]
    embeds_list = []
    irene_server = ctx.bot.get_guild(Sid.irene)
    offset = 1
    for item in places_list:
        embed = Embed(colour=Clr.prpl)
        embed.title = "Top emotes used last month"
        embed.set_footer(text=f'With love, {irene_server.me.display_name}')

        def indent(symbol):
            return str(symbol).ljust(len(str(offset - 1 + splitedSize)), " ")

        max_length = 18
        field0 = f'`{"Emote".ljust(max_length + 4, " ")}Usages`\n'
        field0 += '\n'.join(
            f'`{indent(i)}` {v[0]}`{v[0].split(":")[1][:max_length].ljust(max_length, " ")}{v[1]}`'
            for i, v in enumerate(item, start=offset)
        )
        embed.description = field0
        offset += splitedSize
        embeds_list.append(embed)
    paginator = pages.Paginator(pages=embeds_list)
    if isinstance(ctx, bridge.BridgeExtContext):
        await paginator.send(ctx, mention_author=False)
    elif isinstance(ctx, bridge.BridgeApplicationContext):
        await paginator.respond(ctx)


class EmoteAnalysis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_emote_shift.start()
        self.help_category = 'Stats'

    @commands.Cog.listener()
    async def on_message(self, msg):
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

    @bridge.bridge_command(
        name='topemotes',
        brief=Ems.slash,
        description='Show emotes usage stats'
    )
    @option('keyword', description='Possible keywords: `all`, `ani`, `nonani`', default='all')
    async def topemotes(self, ctx, keyword: str):
        """Show emotes usage stats for `keyword` group ;\
        Possible keywords: `all`, `ani` for animated emotes, `nonani` for static emotes ;"""
        match keyword:
            case 'all':
                await topemotes_job(ctx, 1)
            case 'ani' | 'animated':
                await topemotes_job(ctx, 2)
            case 'nonani' | 'static' | 'nonanimated':
                await topemotes_job(ctx, 3)
            case _:
                embed = Embed(colour=Clr.prpl)
                embed.description = \
                    'You need to use one of keywords: \n' \
                    '• `all` for all emotes ;\n• `ani` for animated emotes ;\n• `nonani` for static emotes ;'
                await ctx.respond(embed=embed)

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


def setup(bot):
    bot.add_cog(EmoteAnalysis(bot))
