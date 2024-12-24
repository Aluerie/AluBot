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

from bot import AluBot, aluloop
from utils import const, errors, formats, pages

from ._base import StatsCog

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluBot

    class BatchLastYearEntry(TypedDict):
        emote_id: int
        guild_id: int
        author_id: int
        used: str  # isoformat


EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOTE_STATS_TRACKING_START = datetime.datetime(2024, 2, 6, tzinfo=datetime.UTC)


class EmoteStatsPageSource(menus.ListPageSource):
    def __init__(self, entries: list[str], footer_text: str, query: str, guild_icon: discord.Asset | None) -> None:
        super().__init__(entries, per_page=1)
        self.footer_text: str = footer_text
        self.query: str = query
        self.guild_icon: discord.Asset | None = guild_icon

    @override
    async def format_page(self, menu: pages.Paginator, entry: str) -> discord.Embed:
        return (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title="Emote leaderboard",
                description=entry,
            )
            .set_author(name=self.query)
            .set_footer(
                icon_url=self.guild_icon,
                text=self.footer_text,
            )
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
        self.clean_up_old_records.start()

    @override
    def cog_unload(self) -> None:
        self.bulk_insert.stop()
        self.clean_up_old_records.stop()

    @commands.Cog.listener("on_message")
    async def insert_emote_usage_data_to_the_database(self, message: discord.Message) -> None:
        """Insert emote usage data to the database on discord message event.

        Parameters
        ----------
        message : discord.Message
            message to filter emotes from.

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
                ]
            )

    @aluloop(seconds=60.0)
    async def bulk_insert(self) -> None:
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
            async with self.bot.pool.acquire() as connection:
                tr = connection.transaction()
                await tr.start()

                try:
                    await connection.execute(query_total, transformed)
                    await connection.execute(query_last_year, self._batch_last_year)
                except Exception:
                    await tr.rollback()
                    raise
                else:
                    await tr.commit()

            self._batch_total.clear()
            self._batch_last_year.clear()

    emotestats_group = app_commands.Group(
        name="emote",
        description="\N{ROLLING ON THE FLOOR LAUGHING} Dota 2 FPC (Favourite Player+Character) commands.",
        guild_ids=const.MY_GUILDS,
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
        interaction: discord.Interaction[AluBot],
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

        if emote_type == "both":
            condition = lambda _: True
        elif emote_type == "static":
            condition: Callable[[discord.Emoji], bool] = lambda e: not e.animated
        elif emote_type == "animated":
            condition: Callable[[discord.Emoji], bool] = lambda e: e.animated

        assert interaction.guild  # guild only command
        emote_ids = [e.id for e in interaction.guild.emojis if e.is_usable() and condition(e)]

        if not emote_ids:
            msg = "This server does not have any custom emotes."
            raise errors.SomethingWentWrong(msg)

        # now we need to fill `rows` variable with list[tuple[int, int]] of list[(emote_id, usage_count)] format
        if timeframe == "all-time":
            query = """
                    SELECT emote_id, total
                    FROM emote_stats_total
                    WHERE guild_id = $1 AND emote_id = ANY($2::bigint[])
                    ORDER BY total DESC
                """
            rows: list[tuple[int, int]] = list(await self.bot.pool.fetch(query, interaction.guild.id, emote_ids))
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
            rows: list[tuple[int, int]] = list(await self.bot.pool.fetch(query, interaction.guild.id, emote_ids))

        rows.extend([(emote_id, 0) for emote_id in emote_ids if emote_id not in [row[0] for row in rows]])

        # all emotes total
        all_emotes_total = sum(t for _, t in rows)
        assert interaction.guild.me.joined_at is not None
        all_emotes_per_day = self.usage_per_day(interaction.guild.me.joined_at, all_emotes_total)

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
            interaction,
            EmoteStatsPageSource(
                tables,
                f"During the timeframe: total {all_emotes_total} emotes were used: {all_emotes_per_day:.0f} per day",
                f"Emote Type: {emote_type}, Timeframe: {'last' if timeframe != 'all-time' else ''} {timeframe}",
                interaction.guild.icon,
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

    @aluloop(time=datetime.time(hour=12, minute=11, second=45))
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
    async def emotestats_specific(self, interaction: discord.Interaction[AluBot], emote: str) -> None:
        """\N{ROLLING ON THE FLOOR LAUGHING} Show information and stats about specific emote.

        Parameters
        ----------
        emote
            Emote to get information/stats about.

        """
        assert interaction.guild

        emoji = discord.utils.find(lambda e: str(e) == emote, interaction.guild.emojis)
        if not emoji:
            # TODO: raise my own error actually;
            embed = discord.Embed(
                color=const.Colour.maroon,
                description=f"Didn't find any emotes matching the name `{emote}`",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title=f"`:{emoji.name}:`",
            )
            .set_author(name="Emote Stats")
            .set_thumbnail(url=emoji.url)
            .add_field(
                name="Emote Information",
                value=f"ID: `{emoji.id}`\nCreated: {formats.format_dt_tdR(emoji.created_at)}",
                inline=False,
            )
        )

        if emoji.guild_id == const.Guild.community:
            table = formats.NoBorderTable()
            table.set_columns(["`Time Period", "Usages", "Percent", "Per Day`"], aligns=["<", ">", ">", ">"])

            # all time total
            query = """
                    SELECT COALESCE(SUM(total), 0) AS "Count"
                    FROM emote_stats_total
                    WHERE guild_id = $1
                    GROUP BY guild_id;
                """
            all_emotes_total: int = await self.bot.pool.fetchval(query, interaction.guild.id)

            # all time this emote
            query = """
                    SELECT COALESCE(SUM(total), 0) AS "Count"
                    FROM emote_stats_total
                    WHERE emote_id=$1 AND guild_id = $2
                    GROUP BY emote_id;
                """
            emote_usage_total: int = await self.bot.pool.fetchval(query, emoji.id, interaction.guild.id)

            table.add_row(
                [
                    "`All-time",
                    emote_usage_total,
                    f"{emote_usage_total/all_emotes_total:.1%}",
                    f"{self.usage_per_day(emoji.created_at, emote_usage_total)}`",
                ]
            )

            query = """
                    SELECT COUNT(*) as "total"
                    FROM emote_stats_last_year
                    WHERE guild_id = $1;
                """
            all_emotes_last_year: int = await self.bot.pool.fetchval(query, interaction.guild.id)

            query = """
                    SELECT COUNT(*) as "total"
                    FROM emote_stats_last_year
                    WHERE emote_id = $1 AND guild_id = $2;
                """
            emote_usage_last_year: int = await self.bot.pool.fetchval(query, emoji.id, interaction.guild.id)

            table.add_row(
                [
                    "`Last Year",
                    emote_usage_last_year,
                    f"{emote_usage_last_year/all_emotes_last_year:.1%}",
                    f"{self.usage_per_day(
                        max(emoji.created_at, datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)),
                        emote_usage_last_year,
                    )}`",
                ]
            )

            server_stats = table.render()

        else:
            server_stats = (
                "Sorry! At the moment, we only track server stats for only Aluerie's Community Server emotes."
            )

        embed.add_field(
            name="Server Usage Stats",
            value=server_stats,
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(EmoteStats(bot))
