from __future__ import annotations

import asyncio
import datetime
import itertools
import logging
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any, Literal, TypedDict, override

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands
from tabulate import tabulate

from core import Cog
from shared import clock, errors, fmt
from shared.concepts import loop
from utils import const, pages

if TYPE_CHECKING:
    from collections.abc import Callable

    from core import Bot, Interaction

    class BatchLastYearEntry(TypedDict):
        emote_id: int
        guild_id: int
        author_id: int
        used: str  # isoformat


__all__ = ("EmoteStats",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOTE_STATS_TRACKING_START = datetime.datetime(2024, 2, 6, tzinfo=datetime.UTC)


def percent(count: int, total: int) -> str:
    """Format `count` as a percentage of `total` (an empty total is 0%, not an error)."""
    return f"{count / (total or 1):.1%}"


class EmoteStats(Cog):
    """Usage Stats for Server Emotes.

    Rework over my old funky `top_emotes.py` code.
    Currently only community server stats are supported.
    """

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self._batch_total: defaultdict[int, Counter[int]] = defaultdict(Counter)
        self._batch_last_year: list[BatchLastYearEntry] = []
        self._batch_lock = asyncio.Lock()

        self.bulk_insert.add_exception_type(asyncpg.PostgresConnectionError)

    @override
    async def cog_load(self) -> None:
        self.bulk_insert.start()
        self.clean_up_old_records.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.bulk_insert.stop()
        self.clean_up_old_records.stop()
        try:
            # whatever was collected in the last minute would be lost otherwise
            await self.flush_batches()
        except Exception:  # ruff: ignore[blind-except]
            log.exception("Could not save the last emote usage batch on unload.")
        await super().cog_unload()

    @commands.Cog.listener("on_message")
    async def create_emote_usage_batches(self, message: discord.Message) -> None:
        """Collects emote usage data in batches from discord messages to be ready for database INSERT.

        Parameters
        ----------
        message
            Message to filter emotes from.
        """
        if message.guild is None or message.guild.id != const.Guild.community:
            # while we are testing this feature, let's only limit the data to the community server
            # maybe expand in future if needed? `guild_id` column is already implemented.
            return

        if message.author.bot and not message.webhook_id:
            # exclude messages from bots but include webhooks so stuff like NQN can work with stats.
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
                ],
            )

    @loop(seconds=60.0)
    async def bulk_insert(self) -> None:
        """Bulk insert gathered emoji stats in the last minute."""
        await self.flush_batches()

    async def flush_batches(self) -> None:
        """Write the collected batches into the database (and forget them if it went well)."""
        async with self._batch_lock:
            if not self._batch_last_year:
                # there was no data to commit to the database.
                return

            # TOTAL COUNT
            transformed = [
                {"guild": guild_id, "emote": emote_id, "added": count}
                for guild_id, data in self._batch_total.items()
                for emote_id, count in data.items()
            ]
            query_total = """
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

            # LAST YEAR COUNT
            query_last_year = """
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
            # both tables or none: otherwise a retry of the batch would count some of it twice
            async with self.bot.pool.acquire() as connection, connection.transaction():
                await connection.execute(query_total, transformed)
                await connection.execute(query_last_year, self._batch_last_year)

            self._batch_total.clear()
            self._batch_last_year.clear()

    emotestats_group = app_commands.Group(
        name="emote-stats",
        description="\N{ROLLING ON THE FLOOR LAUGHING} Emote Stats commands.",
        guild_ids=[const.Guild.community],
    )

    @emotestats_group.command(name="server")
    @app_commands.choices(
        emote_type=[
            app_commands.Choice(name="All emotes", value="both"),
            app_commands.Choice(name="Only non-animated emotes", value="static"),
            app_commands.Choice(name="Only animated emotes", value="animated"),
        ],
        timeframe=[
            app_commands.Choice(name="All time", value="all-time"),
            app_commands.Choice(name="Only last year", value="year"),
            app_commands.Choice(name="Only last month", value="month"),
        ],
    )
    async def emotestats_server(
        self,
        interaction: Interaction,
        emote_type: Literal["both", "static", "animated"],
        timeframe: Literal["all-time", "year", "month"],
    ) -> None:
        """\N{ROLLING ON THE FLOOR LAUGHING} Show statistic about emote usage in this server.

        Parameters
        ----------
        emote_type
            Emote type to include in stats.
        timeframe
            Time period to filter results with.
        """
        condition_lookup: dict[Literal["both", "static", "animated"], Callable[[discord.Emoji], bool]] = {
            "both": lambda _: True,
            "static": lambda e: not e.animated,
            "animated": lambda e: e.animated,
        }
        condition = condition_lookup[emote_type]

        assert interaction.guild  # guild only command
        emote_ids = [e.id for e in interaction.guild.emojis if e.is_usable() and condition(e)]

        if not emote_ids:
            msg = "This server does not have any custom emotes."
            raise errors.BadUserInputError(msg)

        # now we need to fill `rows` variable with list[tuple[int, int]] of list[(emote_id, usage_count)] format
        if timeframe == "all-time":
            query = """
                SELECT emote_id, total
                FROM emote_stats_total
                WHERE guild_id = $1 AND emote_id = ANY($2::bigint[])
                ORDER BY total DESC
            """
            records = await self.bot.pool.fetch(query, interaction.guild.id, emote_ids)
        else:
            # "year" needs no filter: records older than a year are cleaned up by `clean_up_old_records`
            clause, args = "", []
            if timeframe == "month":
                # `used` is a `TIMESTAMP` (without a timezone) that is always kept in UTC, so is this parameter
                clause = "AND used > $3"
                args = [(clock.utcnow() - datetime.timedelta(days=30)).replace(tzinfo=None)]

            query = f"""
                SELECT emote_id, COUNT(*) as "total"
                FROM emote_stats_last_year
                WHERE guild_id = $1 AND emote_id = ANY($2::bigint[]) {clause}
                GROUP BY emote_id
                ORDER BY total DESC;
            """
            records = await self.bot.pool.fetch(query, interaction.guild.id, emote_ids, *args)

        rows: list[tuple[int, int]] = [(record[0], record[1]) for record in records]
        # emotes that were never used do not have any records at all, but they still belong to the leaderboard
        used_emote_ids = {emote_id for emote_id, _ in rows}
        rows.extend((emote_id, 0) for emote_id in emote_ids if emote_id not in used_emote_ids)

        # all emotes total
        all_emotes_total = sum(t for _, t in rows)
        assert interaction.guild.me.joined_at is not None
        all_emotes_per_day = self.usage_per_day(interaction.guild.me.joined_at, all_emotes_total)

        offset = 0
        split_size = 20
        tables: list[str] = []

        for batch in itertools.batched(rows, n=split_size):  # ruff: ignore[batched-without-explicit-strict]
            table = tabulate(
                tabular_data=[
                    [
                        f"`{fmt.label_indent(counter, counter - 1, split_size)}`",
                        *self.emote_fmt(emote_id=row[0], count=row[1], total=all_emotes_total),
                    ]
                    for counter, row in enumerate(batch, start=offset + 1)
                ],
                headers=[
                    f"`{fmt.label_indent('N', offset + 1, split_size)}`",
                    "\N{BLACK LARGE SQUARE}",  # "\N{FRAME WITH PICTURE}",
                    "`Name",
                    "Total",
                    "Percent",
                    "PerDay`",
                ],
                tablefmt="plain",
            )
            offset += split_size
            tables.append(table)

        paginator = pages.EmbedDescriptionPaginator(
            interaction,
            tables,
            template={
                "color": const.Palette.purple_500,
                "title": "Emote leaderboard",
                "author": {
                    "name": (
                        f"Emote Type: {emote_type}, Timeframe: {'last' if timeframe != 'all-time' else ''} {timeframe}"
                    ),
                },
                "footer": {
                    "text": (
                        f"During the timeframe: total {all_emotes_total} emotes were used; {all_emotes_per_day} per day"
                    ),
                    "icon_url": (
                        interaction.guild.icon.url if interaction.guild.icon is not None else discord.utils.MISSING
                    ),
                },
            },
        )
        await paginator.start()

    def emote_fmt(self, emote_id: int, count: int, total: int) -> tuple[str, str, str, str, str]:
        """Emote formatting.

        Returns
        -------
        tuple[str, str, str, str, str]
            Tuple of emote's full_name`, colon_name, usage count, percent, per_day usage count.
        """
        emote = self.bot.get_emoji(emote_id)
        if emote is None:
            full_name = f"[\N{WHITE QUESTION MARK ORNAMENT}](https://cdn.discordapp.com/emojis/{emote_id}.png)"
            colon_name = "**Unknown Emote**"
            created_at = discord.utils.snowflake_time(emote_id)
        else:
            full_name = str(emote)
            colon_name = emote.name
            created_at = emote.created_at

        per_day = self.usage_per_day(created_at, count)
        return full_name, f"`:{colon_name}:", str(count), percent(count, total), f"{per_day}`"

    @staticmethod
    def usage_per_day(dt: datetime.datetime, usages: int) -> str:
        """Usage per day formatting."""
        base = max(dt, EMOTE_STATS_TRACKING_START)
        days = (datetime.datetime.now(datetime.UTC) - base).total_seconds() / 86400  # 86400 seconds in a day
        return f"{usages / (int(days) or 1):.1f}"  # or 1 takes care of days = 1 DivisionError

    @loop(time=datetime.time(hour=12, minute=11, second=45))
    async def clean_up_old_records(self) -> None:
        """Clean up "way too old" records from the Last Year emote usage database.

        I'm kinda afraid of running out of memory so I'm just keeping a one year records max.
        If I'm proven wrong and we can hold much more data than this - I will consider extending the database.
        But for now - we clean up the database from 1 year+ records.

        Note that this doesn't affect `emote_stats_total` in any way. Everything is correct there.
        """
        async with self._batch_lock:
            clean_up_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)

            query = """
                    DELETE FROM emote_stats_last_year
                    WHERE used < $1::date
                """
            await self.bot.pool.execute(query, clean_up_dt)

    @emotestats_group.command(name="specific")
    async def emotestats_specific(self, interaction: Interaction, emote: str) -> None:
        """\N{ROLLING ON THE FLOOR LAUGHING} Show information and stats about specific emote.

        Parameters
        ----------
        emote
            Emote to get information/stats about.
        """
        assert interaction.guild

        emoji = discord.utils.find(lambda e: str(e) == emote, interaction.guild.emojis)
        if not emoji:
            msg = f"Didn't find any emotes matching the name `{emote}`"
            raise errors.BadUserInputError(msg)

        embed = (
            discord
            .Embed(color=const.Palette.purple_500, title=f"`:{emoji.name}:`")
            .set_author(name="Emote Stats")
            .set_thumbnail(url=emoji.url)
            .add_field(
                name="Emote Information",
                value=f"ID: `{emoji.id}`\nCreated: {clock.discord(emoji.created_at, 'd', 't', 'R')}",
                inline=False,
            )
        )

        if emoji.guild_id == const.Guild.community:
            # all time total
            query = """
                SELECT COALESCE(SUM(total), 0) AS "Count"
                FROM emote_stats_total
                WHERE guild_id = $1
                GROUP BY guild_id;
            """
            all_emotes_total: int = await self.bot.pool.fetchval(query, interaction.guild.id) or 0

            # all time this emote
            query = """
                SELECT COALESCE(SUM(total), 0) AS "Count"
                FROM emote_stats_total
                WHERE emote_id=$1 AND guild_id = $2
                GROUP BY emote_id;
            """
            emote_usage_total: int = await self.bot.pool.fetchval(query, emoji.id, interaction.guild.id) or 0

            all_time_period = [
                "All-time",
                emote_usage_total,
                percent(emote_usage_total, all_emotes_total),
                self.usage_per_day(emoji.created_at, emote_usage_total),
            ]

            # last year total
            query = """
                SELECT COUNT(*) as "total"
                FROM emote_stats_last_year
                WHERE guild_id = $1;
            """
            all_emotes_last_year: int = await self.bot.pool.fetchval(query, interaction.guild.id)

            # last year this emote
            query = """
                SELECT COUNT(*) as "total"
                FROM emote_stats_last_year
                WHERE emote_id = $1 AND guild_id = $2;
            """
            emote_usage_last_year: int = await self.bot.pool.fetchval(query, emoji.id, interaction.guild.id)

            last_year_period = [
                "Last Year",
                emote_usage_last_year,
                percent(emote_usage_last_year, all_emotes_last_year),
                self.usage_per_day(
                    max(emoji.created_at, datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)),
                    emote_usage_last_year,
                ),
            ]

            server_stats = fmt.codeblock(
                tabulate(
                    headers=["Period", "Usages", "Percent", "Per Day"],
                    tabular_data=[all_time_period, last_year_period],
                    tablefmt="plain",
                ),
                language="",
            )

        else:
            server_stats = (
                "Sorry! At the moment, we only track server stats for only Aluerie's Community Server emotes."
            )

        embed.add_field(name="Server Usage Stats", value=server_stats, inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(EmoteStats(bot))
