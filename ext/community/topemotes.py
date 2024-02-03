from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Literal, override

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import const
from utils.formats import indent
from utils.pages import EnumeratedPaginator

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext
    from utils.database import PoolTypedWithAny


def filter_emotes_condition(emote: discord.PartialEmoji, mode: int) -> int:
    if mode == 1:  # noqa: SIM114
        return 1
    elif mode == 2 and emote.animated:  # noqa: SIM114
        return 1
    elif mode == 3 and not emote.animated:
        return 1
    else:
        return 0


async def get_sorted_emote_dict(mode: int, pool: PoolTypedWithAny) -> dict[str, int]:
    emote_dict = {}

    def filter_mode(mod: int, animated: bool) -> bool:
        if mod == 1:  # noqa: SIM114
            return True
        elif mod == 2 and animated:
            return True
        return bool(mod == 3 and not animated)

    query = "SELECT * FROM emotes"
    rows = await pool.fetch(query)
    for row in rows:
        if filter_mode(mode, row.animated):
            emote_dict[row.name] = sum(row.month_array)

    return dict(sorted(emote_dict.items(), key=lambda item: item[1], reverse=True))


async def topemotes_job(ctx: AluContext, mode: int) -> None:
    sorted_emote_dict = await get_sorted_emote_dict(mode, pool=ctx.pool)
    new_array = []
    split_size = 20
    offset = 1
    max_length = 18

    for cnt, key in enumerate(sorted_emote_dict, start=offset):
        new_array.append(
            f"`{indent(cnt, cnt, offset, split_size)}` "
            f'{key}`{key.split(":")[1][:max_length].ljust(max_length, " ")}{sorted_emote_dict[key]}`'
        )
    pgs = EnumeratedPaginator(
        ctx,
        new_array,
        per_page=split_size,
        no_enumeration=True,
        colour=const.Colour.blueviolet,
        title="Top emotes used last month",
        footer_text=f"With love, {ctx.bot.user.display_name}",
        description_prefix=f'`{"Emote".ljust(max_length + 4, " ")}Usages`\n',
    )
    await pgs.start()


class EmoteAnalysis(CommunityCog, name="Emote stats"):
    """See stats on emote usage in Aluerie's server.

    The bot keeps data for one month.
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(const.Emote.peepoComfy)

    @override
    def cog_load(self) -> None:
        self.daily_emote_shift.start()

    @override
    def cog_unload(self) -> None:
        self.daily_emote_shift.cancel()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # if self.bot.test_flag:
        #    return

        if not msg.author.bot or msg.webhook_id:
            custom_emojis_ids = re.findall(const.Regex.EMOTE_STATS_IDS, msg.content)  # they are in str tho
            custom_emojis_ids = set(map(int, custom_emojis_ids))

            for emote_id in custom_emojis_ids:
                query = "UPDATE emotes SET month_array[30]=month_array[30]+1 WHERE id=$1;"
                await self.bot.pool.execute(query, emote_id)

    @commands.hybrid_command(name="topemotes", description="Show emotes usage stats")
    @app_commands.describe(keyword="Possible keywords: `all`, `ani`, `nonani`")
    async def topemotes(self, ctx: AluContext, keyword: Literal["all", "ani", "nonani"] = "all") -> None:
        """Show emotes usage stats for `keyword` group ;\
        Possible keywords: `all`, `ani` for animated emotes, `nonani` for static emotes ;
        """
        match keyword:
            case "all":
                await topemotes_job(ctx, 1)
            case "ani" | "animated":  # type: ignore
                await topemotes_job(ctx, 2)
            case "nonani" | "static" | "nonanimated":  # type: ignore
                await topemotes_job(ctx, 3)

    @tasks.loop(time=datetime.time(hour=16, minute=43, tzinfo=datetime.UTC))
    async def daily_emote_shift(self) -> None:
        query = "SELECT id, month_array FROM emotes"
        rows = await self.bot.pool.fetch(query)
        for row in rows:
            query = "UPDATE emotes SET month_array=$1 WHERE id=$2"
            await self.bot.pool.execute(query, row.month_array[1:] + [0], row.id)

    @daily_emote_shift.before_loop
    async def before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: AluBot) -> None:
    await bot.add_cog(EmoteAnalysis(bot))
