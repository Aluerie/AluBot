from __future__ import annotations

import asyncio
import datetime
import itertools
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Literal, TypedDict, override

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, menus

from bot import AluBot
from utils import aluloop, checks, const, errors, formats, pages

from ._base import StatsCog

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluBot
    from utils import AluGuildContext

    class BatchLastYearEntry(TypedDict):
        emote_id: int
        guild_id: int
        author_id: int
        used: str  # isoformat


EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOTE_STATS_TRACKING_START = datetime.datetime(2024, 2, 6, tzinfo=datetime.UTC)


class EmoteStatsPageSource(menus.ListPageSource):
    def __init__(self, entries: list[str], footer_text: str) -> None:
        super().__init__(entries, per_page=1)
        self.footer_text: str = footer_text

    @override
    async def format_page(self, menu: pages.Paginator, entry: str) -> discord.Embed:
        return discord.Embed(
            colour=const.Colour.blueviolet,
            title="Emote leaderboard: All time.",
            description=entry,
        ).set_footer(
            text=self.footer_text,
        )


class EmoteStats(StatsCog):
    """Usage Stats for Server Emotes.

    Rework over my old funky `top_emotes.py` code.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot)
        self._batch_total: defaultdict[int, Counter[int]] = defaultdict(Counter)
        self._batch_last_year: list[BatchLastYearEntry] = []
        self._batch_lock = asyncio.Lock()

        self.bulk_insert.add_exception_type(asyncpg.PostgresConnectionError)

    @override
    async def cog_load(self) -> None:
        self.bulk_insert.start()

    @override
    def cog_unload(self) -> None:
        self.bulk_insert.stop()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != const.Guild.community:
            # while we are testing this feature, let's only limit the data to the community server
            # maybe expand in future if needed? `guild_id` column is already implemented.
            return

        if message.author.bot:
            return

        matches = EMOJI_REGEX.findall(message.content)
        if not matches:
            return

        # remove duplicates per message (yes, I love spamming triple emotes.)
        matches = list(dict.fromkeys(matches))

        async with self._batch_lock:
            # TOTAL COUNT
            self._batch_total[message.guild.id].update(map(int, matches))

            # LAST YEAR COUNT
            self._batch_last_year.extend(
                [
                    {
                        "emote_id": int(x),
                        "guild_id": message.guild.id,
                        "author_id": message.author.id,
                        "used": message.created_at.isoformat(),
                    }
                    for x in matches
                ]
            )

    @aluloop(seconds=60.0)
    async def bulk_insert(self) -> None:
        async with self._batch_lock:
            # TOTAL COUNT
            transformed = [
                {"guild": guild_id, "emote": emote_id, "added": count}
                for guild_id, data in self._batch_total.items()
                for emote_id, count in data.items()
            ]
            query = """
                INSERT INTO emote_stats_total (guild_id, emote_id, total)
                    SELECT x.guild, x.emote, x.added
                    FROM jsonb_to_recordset($1::jsonb) AS
                    x(
                        guild BIGINT,
                        emote BIGINT,
                        added INT
                    )
                ON CONFLICT (guild_id, emote_id) DO UPDATE
                SET total = emote_stats_total.total + excluded.total;
            """
            await self.bot.pool.execute(query, transformed)
            self._batch_total.clear()

            # LAST YEAR COUNT
            if not self._batch_last_year:
                return

            query = """
                INSERT INTO emote_stats_last_year (emote_id, guild_id, author_id, used)
                    SELECT x.emote_id, x.guild_id, x.author_id, x.used
                    FROM jsonb_to_recordset($1::jsonb) AS
                    x(
                        emote_id BIGINT,
                        guild_id BIGINT,
                        author_id BIGINT,
                        used TIMESTAMP
                    )
                """

            await self.bot.pool.execute(query, self._batch_last_year)
            self._batch_last_year.clear()

    @commands.hybrid_group(name="emotestats")
    @checks.hybrid.is_community()
    async def emotestats(self, ctx: AluGuildContext) -> None:
        """Emote Stats Commands."""
        await ctx.send_help()

    @emotestats.command(name="server")
    @app_commands.choices(
        emote_type=[
            app_commands.Choice(name="All emotes", value="all"),
            app_commands.Choice(name="Only non-animated emotes", value="static"),
            app_commands.Choice(name="Only animated emotes", value="animated"),
        ],
        timeframe=[
            app_commands.Choice(name="All time total stats", value="total"),
            app_commands.Choice(name="Only last year emote usage stats", value="year"),
            app_commands.Choice(name="Only last month emote usage stats", value="month"),
        ],
    )
    async def emotestats_server(
        self,
        ctx: AluGuildContext,
        emote_type: Literal["all", "static", "animated"],
        timeframe: Literal["total", "year", "month"],
    ) -> None:
        """Show statistic about emote usage in this server."""
        if emote_type == "all":
            condition = lambda _: True
        elif emote_type == "static":
            condition: Callable[[discord.Emoji], bool] = lambda e: not e.animated
        elif emote_type == "animated":
            condition: Callable[[discord.Emoji], bool] = lambda e: e.animated

        emote_ids = [e.id for e in ctx.guild.emojis if not e.managed and condition(e)]

        if not emote_ids:
            msg = "This server does not have any custom emotes."
            raise errors.SomethingWentWrong(msg)

        # now we need to fill `rows` variable with list[tuple[int, int]] of list[(emote_id, usage_count)] format
        if timeframe == "total":
            query = """
                    SELECT emote_id, total
                    FROM emote_stats_total
                    WHERE guild_id = $1 AND emote_id = ANY($2::bigint[])
                    ORDER BY total DESC
                """
            rows: list[tuple[int, int]] = list(await self.bot.pool.fetch(query, ctx.guild.id, emote_ids))
        else:
            now = datetime.datetime.now(datetime.UTC)
            if timeframe == "month":
                track_point = now - datetime.timedelta(days=30)
                clause = f"AND used > '{track_point.isoformat()}'::date"
            elif timeframe == "year":
                clause = ""

            query = f"""
                SELECT emote_id, COUNT(*) as "total"
                FROM emote_stats_last_year
                WHERE guild_id = $1 AND emote_id = ANY($2::bigint[]) {clause}
                GROUP BY emote_id
                ORDER BY total DESC;
            """
            rows: list[tuple[int, int]] = list(await self.bot.pool.fetch(query, ctx.guild.id, emote_ids))

        rows.extend([(emote_id, 0) for emote_id in emote_ids if emote_id not in [row[0] for row in rows]])

        # all emotes total
        all_emotes_total = sum(t for _, t in rows)
        assert ctx.me.joined_at is not None
        all_emotes_per_day = self.usage_per_day(ctx.me.joined_at, all_emotes_total)

        offset = 0
        split_size = 20
        tables = []
        for batch in itertools.batched(rows, n=split_size):
            table = formats.NoBorderTable()
            table.set_columns(
                [
                    f"`{formats.new_indent('N', offset + 1, split_size)}`",
                    "\N{BLACK LARGE SQUARE}",  # "\N{FRAME WITH PICTURE}",
                    "`Name",
                    "Total",
                    "Percent",
                    "PerDay`",
                ],
                aligns=[">", "^", "<", ">", ">", ">"],
            )
            for counter, row in enumerate(batch, start=offset + 1):
                table.add_row(
                    [
                        f"`{formats.new_indent(counter, counter + 1, split_size)}`",
                        *self.emote_fmt(emote_id=row[0], count=row[1], total=all_emotes_total),
                    ]
                )

            # hijack the table widths since custom emotes rendering messes it up
            table._widths[1] = 3
            tables.append(table.render())
            offset += split_size

        paginator = pages.Paginator(
            ctx,
            EmoteStatsPageSource(
                tables,
                f"Total {all_emotes_total} emotes used: {all_emotes_per_day} per day",
            ),
        )
        await paginator.start()

    def emote_fmt(self, emote_id: int, count: int, total: int) -> tuple[str, str, str, str, str]:
        emote = self.bot.get_emoji(emote_id)
        if emote is None:
            full_name = f"[\N{WHITE QUESTION MARK ORNAMENT}](https://cdn.discordapp.com/emojis/{emote_id}.png)"
            emote = discord.Object(id=emote_id)
            colon_name = "**Unknown Emote**"
        else:
            full_name = str(emote)
            colon_name = emote.name

        per_day = self.usage_per_day(emote.created_at, count)
        percent = count / (total or 1)

        return full_name, f"`:{colon_name}:", str(count), f"{percent:.1%}", f"{per_day:.1f}`"

    @staticmethod
    def usage_per_day(dt: datetime.datetime, usages: int) -> float:
        base = EMOTE_STATS_TRACKING_START if dt < EMOTE_STATS_TRACKING_START else dt
        days = (datetime.datetime.now(datetime.UTC) - base).total_seconds() / 86400  # 86400 seconds in a day
        return usages / (int(days) or 1)  # or 1 takes care of days = 1 DivisionError


async def setup(bot: AluBot) -> None:
    await bot.add_cog(EmoteStats(bot))
