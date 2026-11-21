# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Levels."""

from __future__ import annotations

import bisect
import datetime as dt
import itertools
import re
from typing import TYPE_CHECKING, Final, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from tabulate import tabulate

from core import Cog
from shared import clock, fmt, globs
from shared.concepts import loop
from utils import const, pages

if TYPE_CHECKING:
    from core import Bot, Interaction

    class RemoveLongGoneRow(TypedDict):
        id: int
        name: str
        last_seen: dt.datetime

    class LeaderboardQueryRow(TypedDict):
        id: int
        experience: int


__all__ = ("Levels",)


LAST_SEEN_TIMEOUT = 60
"""Seconds between messages that give experience: spamming doesn't level you up faster."""
LONG_GONE_AFTER = dt.timedelta(days=365)
"""Members who left the server and didn't come back for this long are removed from the database."""
THANKS_REGEX = re.compile(r"\b(?:thanks?|ty)\b", re.IGNORECASE)
"""Whole words only: a plain substring check would see "ty" in "pretty" or "party"."""

EXP_LEVEL_TABLE = (
    5,
    230,
    600,
    1080,
    1660,  # 1-5
    2260,
    2980,
    3730,
    4620,
    5550,  # 6-10
    6520,
    7530,
    8580,
    9805,
    11055,  # 11-15
    12330,
    13630,
    14955,
    16455,
    18045,  # 16-20
    19645,
    21495,
    23595,
    25945,
    28545,  # 21-25
    32045,
    36545,
    42045,
    48545,
    56045,  # 26-30
)
"""``EXP_LEVEL_TABLE[i]`` is the amount of experience needed to reach the level ``i + 1``."""

MAX_LEVEL = len(EXP_LEVEL_TABLE)


def get_level(exp: int) -> int:
    """Get the level of a member with the given experience."""
    return bisect.bisect_right(EXP_LEVEL_TABLE, exp)


def exp_to_reach(level: int) -> int:
    """Get the amount of experience needed to reach the level.

    Parameters
    ----------
    level
        The level, from 0 (everybody starts at it) to `MAX_LEVEL`. Anything above is treated as `MAX_LEVEL`.
    """
    if level <= 0:
        return 0
    return EXP_LEVEL_TABLE[min(level, MAX_LEVEL) - 1]


class Levels(Cog):
    """Experience and Levels System.

    Just a lame XP per Message system with some fancy images and tables.
    """

    # TODO: fill this in. It used to be `community.logs` of the old helper object. While it is `0` the notifications
    # about removed members are only written to the bot's log.
    LOGS_CHANNEL_ID: Final = const.ChannelId(0)
    """Channel for the notifications about members who were removed from the database."""

    @override
    async def cog_load(self) -> None:
        self.register_existing_members.start()
        self.remove_long_gone_members.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.remove_long_gone_members.cancel()
        await super().cog_unload()

    # --- COMMANDS -----------------------------------------------------------------------------------------------------

    @app_commands.guilds(const.Guild.community)
    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: Interaction) -> None:
        """View experience leaderboard for this server."""
        guild = self.bot.community

        query = """
            SELECT id, experience
            FROM community_members
            ORDER BY experience DESC;
        """
        rows: list[LeaderboardQueryRow] = await self.bot.pool.fetch(query)
        # clean up the rows from inactive members
        members = [(member, row) for row in rows if (member := guild.get_member(row["id"])) is not None]

        offset = 0
        split_size = 10
        tables: list[str] = []

        for batch in itertools.batched(members, n=split_size):  # ruff: ignore[batched-without-explicit-strict]
            table = tabulate(
                tabular_data=[
                    [
                        # some absolutely insane tier alignment is going on here
                        # we use multi-lines table approach
                        # since we can't align mentions in discord properly due to non-monospace font
                        # we put mentions on one line and the data onto the second line and properly align those;
                        # we put invisible symbol to trick the tabulate to make two lines for those
                        (
                            f"{(label := '`' + fmt.label_indent(counter, counter - 1, split_size) + '`')}"
                            f"\n`{' ' * len(label)}"
                        ),
                        f"{member.mention}\n{' ' * len(member.mention)}",
                        f"‎\n{get_level(row['experience'])}",
                        f"‎\n{row['experience']}",
                    ]
                    for counter, (member, row) in enumerate(batch, start=offset + 1)
                ],
                headers=[
                    "`" + fmt.label_indent("N", offset + 1, split_size),
                    "Name",
                    "Level",
                    "Exp`",
                ],
                tablefmt="plain",
            )
            offset += split_size
            tables.append(table)

        paginator = pages.EmbedDescriptionPaginator(
            interaction,
            entries=tables,
            empty_description="Nobody is on the leaderboard yet.",
            template={
                "footer": {
                    "text": guild.name,
                    "icon_url": guild.icon.url if guild.icon is not None else discord.utils.MISSING,
                }
            },
        )
        await paginator.start()

    # --- LISTENERS ----------------------------------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Start tracking the experience of a new community member."""
        if member.guild.id != const.Guild.community or member.bot:
            return
        await self._register_members([member])

    async def _register_members(self, members: list[discord.Member]) -> None:
        """Create the database rows for the members that don't have one yet.

        Nothing else inserts into ``community_members``, while every query of this cog only updates existing rows.

        Parameters
        ----------
        members
            Members to register. Existing rows are left untouched (so the experience is never reset).
        """
        query = "INSERT INTO community_members (id, name) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING"
        await self.bot.pool.executemany(query, [(m.id, m.name) for m in members])

    @loop(count=1, wait_for_ready=True)
    async def register_existing_members(self) -> None:
        """Register the members who joined while the bot was offline (or before this cog tracked them)."""
        await self._register_members([m for m in self.bot.community.members if not m.bot])

    @commands.Cog.listener(name="on_message")
    async def experience_counting(self, message: discord.Message) -> None:
        """Message listener that counts experience points."""
        if message.author.bot or not message.guild or message.guild.id != const.Guild.community:
            return

        # `last_seen` is the value from *before* this update. There is no row if the member is not in the database.
        query = """
            WITH m AS (SELECT last_seen FROM community_members WHERE id = $1)
            UPDATE community_members
            SET message_count = message_count + 1, last_seen = now()
            WHERE id = $1
            RETURNING (SELECT last_seen FROM m)
        """
        last_seen: dt.datetime | None = await self.bot.pool.fetchval(query, message.author.id)
        if last_seen is None:
            return

        if clock.utcnow() - last_seen <= dt.timedelta(seconds=LAST_SEEN_TIMEOUT):
            return

        query = "UPDATE community_members SET experience = experience + 1 WHERE id = $1 RETURNING experience"
        exp: int | None = await self.bot.pool.fetchval(query, message.author.id)
        if exp is None:
            return

        level = get_level(exp)
        if level == 0 or exp != exp_to_reach(level):
            return  # no new level

        level_up_role = discord.utils.get(message.guild.roles, name=f"Level #{level}")
        if not level_up_role:
            msg = f"Role `Level #{level}` was not found in the community guild"
            raise ValueError(msg)
        previous_level_role = discord.utils.get(message.guild.roles, name=f"Level #{level - 1}")

        text = f"{message.author.mention} just advanced to {level_up_role.mention} ! {const.Emoji.PepoG}"
        embed = discord.Embed(color=globs.Color.PUCE, description=text)
        await message.channel.send(embed=embed)

        author = message.author
        assert isinstance(author, discord.Member)  # it's a guild message
        if previous_level_role:  # there is no role for the level 0
            await author.remove_roles(previous_level_role)
        await author.add_roles(level_up_role)

    # --- TASKS --------------------------------------------------------------------------------------------------------

    @loop(time=dt.time(hour=13, minute=13, tzinfo=dt.UTC), wait_for_ready=True)
    async def remove_long_gone_members(self) -> None:
        """Remove long ago gone members.

        Just a small clean up task so we don't keep members who left long ago in the database.
        365 days is probably enough to warrant that they no longer come back.
        `community_members` table holds stuff like auto_roles, experience, msg_count.
        """
        if clock.utcnow().weekday() != 3:
            # let's do this task on Thursdays only, why not xd.
            return

        guild = self.bot.community
        query = "SELECT id, last_seen, name FROM community_members WHERE last_seen < $1"
        rows: list[RemoveLongGoneRow] = await self.bot.pool.fetch(query, clock.utcnow() - LONG_GONE_AFTER)

        for row in rows:
            if guild.get_member(row["id"]) is not None:
                continue  # they are in the server: `last_seen` is only updated by messages, they might just be quiet

            await self.bot.pool.execute("DELETE FROM community_members WHERE id = $1", row["id"])
            logger.info("Removed {} ({}) from the database: gone for too long.", row["name"], row["id"])

            if self.LOGS_CHANNEL_ID:
                embed = discord.Embed(color=0xE6D690, description=f"id = {row['id']}").set_author(
                    name=f"{row['name']} was removed from the database"
                )
                await self.bot.get_text_channel_or_test(self.LOGS_CHANNEL_ID).send(embed=embed)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Levels(bot))
