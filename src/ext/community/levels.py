# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Levels."""

from __future__ import annotations

import asyncio
import bisect
import datetime as dt
import functools
import itertools
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from tabulate import tabulate

from core import Cog
from shared import errors, fmt, globs
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
        exp: int
        rep: int

    class RankQueryRow(TypedDict):
        in_lvl: bool
        exp: int
        rep: int


__all__ = ("Levels",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

ASSETS = Path(__file__).resolve().parents[2] / "assets"

LAST_SEEN_TIMEOUT = 60
"""Seconds between messages that give experience: spamming doesn't level you up faster."""
LONG_GONE_AFTER = dt.timedelta(days=365)
"""Members who left the server and didn't come back for this long are removed from the database."""
THANKS_REGEX = re.compile(r"\b(?:thanks?|ty)\b", re.IGNORECASE)
"""Whole words only: a plain substring check would see "ty" in "pretty" or "party"."""

RANK_FONT = "Inter-Black-slnt=0.ttf"
RANK_FONT_SIZE = 60
MASK_SUPERSAMPLING = 4

# fmt: off
EXP_LEVEL_TABLE = (
        5, 230, 600, 1080, 1660,  # 1-5
    2_260, 2980, 3730, 4620, 5550,  # 6-10 # "_" so rainbow indent doesn't make erroneous indent color :D
    6_520, 7530, 8580, 9805, 11055,  # 11-15
    12330, 13630, 14955, 16455, 18045,  # 16-20
    19645, 21495, 23595, 25945, 28545,  # 21-25
    32045, 36545, 42045, 48545, 56045,  # 26-30
)
"""``EXP_LEVEL_TABLE[i]`` is the amount of experience needed to reach the level ``i + 1``."""
# fmt: on
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


@functools.cache
def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ASSETS / "fonts" / filename), size)


def _circle_mask(size: int) -> Image.Image:
    """Make an anti-aliased circular mask by drawing large and downscaling."""
    big_size = size * MASK_SUPERSAMPLING
    big = Image.new("L", (big_size, big_size), 0)
    ImageDraw.Draw(big).ellipse((0, 0, big_size - 1, big_size - 1), fill=255)
    return big.resize((size, size), Image.Resampling.LANCZOS)


def _build_rank_image(
    *,
    avatar_bytes: bytes,
    name: str,
    color: tuple[int, int, int],
    place: int,
    level: int,
    experience: int,
) -> Image.Image:
    """Blocking part of the rank image. Run it in a thread."""
    with Image.open(ASSETS / "images" / "profile" / "welcome.png") as template:
        canvas = template.convert("RGBA")
    canvas_w, canvas_h = canvas.size

    # the avatar is a circle as tall as the canvas, glued to the right side
    with Image.open(BytesIO(avatar_bytes)) as raw_avatar:
        avatar = raw_avatar.convert("RGBA").resize((canvas_h, canvas_h), Image.Resampling.LANCZOS)
    canvas.paste(avatar, (canvas_w - canvas_h, 0), _circle_mask(canvas_h))

    draw = ImageDraw.Draw(canvas)
    white = (255, 255, 255)
    font = _font(RANK_FONT, RANK_FONT_SIZE)

    # the progress bar to the next level; at the max level it's simply full
    prev_exp = exp_to_reach(level)
    if level >= MAX_LEVEL:
        progress, exp_text = 1.0, f"{experience} EXP (max level)"
    else:
        next_exp = exp_to_reach(level + 1)
        progress = min(max((experience - prev_exp) / (next_exp - prev_exp), 0.0), 1.0)
        exp_text = f"{experience}/{next_exp} EXP"
    bar_top = canvas_h * 6 / 7
    draw.rectangle((0, bar_top, canvas_w, canvas_h), fill=(98, 98, 98))
    draw.rectangle((0, bar_top, progress * canvas_w, canvas_h), fill=color)

    draw.text((canvas_w / 4, 0), name, fill=white, font=font)
    draw.text((canvas_w / 4, canvas_h * 2 / 6), f"{fmt.ordinal(place)} rank", fill=white, font=font)
    draw.text((canvas_w / 4, canvas_h * 3 / 6), f"{fmt.ordinal(level)} level", fill=white, font=font)
    draw.text((canvas_w, canvas_h * 5 / 6), exp_text, fill=white, font=font, anchor="ra")
    return canvas


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
        self.remove_long_gone_members.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.remove_long_gone_members.cancel()
        await super().cog_unload()

    ####################################################################################################################
    # COMMANDS
    ####################################################################################################################

    @app_commands.guilds(*const.MY_GUILDS)
    @app_commands.command(name="rank")
    @app_commands.rename(member_="member")
    async def rank(self, interaction: Interaction, member_: discord.Member | None = None) -> None:
        """View member's rank and experience level in this server.

        Parameters
        ----------
        member_
            Member to check experience and rank of.
        """
        member = member_ or interaction.user
        if not isinstance(member, discord.Member):
            msg = "This command only works in a server."
            raise errors.BadUserInputError(msg)

        if member.bot:
            msg = "Sorry! our system does not count experience for bots."
            raise errors.BadUserInputError(msg)

        query = "SELECT experience FROM community_members WHERE id = $1"
        experience: int | None = await self.bot.pool.fetchval(query, member.id)
        if experience is None:
            msg = f"I don't have any experience data about {member.display_name} yet."
            raise errors.BadUserInputError(msg)

        # building the image takes a while (the avatar download + the drawing), longer than 3 seconds on a bad day
        await interaction.response.defer()

        query = "SELECT COUNT(*) FROM community_members WHERE experience > $1"
        place: int = 1 + await self.bot.pool.fetchval(query, experience)
        avatar_bytes = await member.display_avatar.with_static_format("png").with_size(512).read()
        image = await asyncio.to_thread(
            _build_rank_image,
            avatar_bytes=avatar_bytes,
            name=member.display_name,
            color=member.color.to_rgb(),
            place=place,
            level=get_level(experience),
            experience=experience,
        )
        await interaction.followup.send(file=self.bot.image_to_file(image, filename="rank.png"))

    @app_commands.guilds(*const.MY_GUILDS)
    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: Interaction, sort_by: Literal["exp", "rep"] = "exp") -> None:
        """View experience leaderboard for this server.

        Parameters
        ----------
        sort_by
            Choose how to sort leaderboard.
        """
        guild = self.bot.community

        # `sort_by` is one of the two literals, discord doesn't let anything else in, so it's safe to format it in
        query = f"""
            SELECT id, exp, rep
            FROM community_members
            WHERE in_lvl = TRUE
            ORDER BY {sort_by} DESC;
        """  # ruff: ignore[hardcoded-sql-expression]
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
                        f"‎\n{get_level(row['exp'])}",
                        f"‎\n{row['exp']}",
                        f"‎\n{row['rep']}`",
                    ]
                    for counter, (member, row) in enumerate(batch, start=offset + 1)
                ],
                headers=[
                    "`" + fmt.label_indent("N", offset + 1, split_size),
                    "Name",
                    "Level",
                    "Exp",
                    "Rep`",
                ],
                tablefmt="plain",
            )
            offset += split_size
            tables.append(table)

        paginator = pages.EmbedDescriptionPaginator(
            interaction,
            tables,
            empty_description="Nobody is on the leaderboard yet.",
            template={
                "footer": {
                    "text": f"Sorted by {sort_by}",
                    "icon_url": guild.icon.url if guild.icon is not None else discord.utils.MISSING,
                }
            },
        )
        await paginator.start()

    @app_commands.command(name="give-rep")
    @app_commands.guilds(const.Guild.community)
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(member="Member to give rep to")
    async def reputation(self, interaction: Interaction, member: discord.Member) -> None:
        """Give +1 to `@member`'s reputation."""
        if member == interaction.user or member.bot:
            msg = "You can't give reputation to yourself or bots."
            raise errors.BadUserInputError(msg)

        query = "UPDATE community_members SET rep = rep + 1 WHERE id = $1 RETURNING rep"
        reputation: int | None = await self.bot.pool.fetchval(query, member.id)
        if reputation is None:
            msg = f"I don't have any data about {member.display_name} yet."
            raise errors.BadUserInputError(msg)

        embed = discord.Embed(
            color=discord.Color.green(),
            description=f"Added +1 reputation to **{member.display_name}**: now {reputation} reputation",
        )
        await interaction.response.send_message(embed=embed)

    ####################################################################################################################
    # LISTENERS
    ####################################################################################################################

    @commands.Cog.listener(name="on_message")
    async def experience_counting(self, message: discord.Message) -> None:
        """Message listener that counts experience points."""
        if message.author.bot or not message.guild or message.guild.id != const.Guild.community:
            return

        # `last_seen` is the value from *before* this update. There is no row if the member is not in the database.
        query = """
            WITH m AS (SELECT last_seen FROM community_members WHERE id = $1)
            UPDATE community_members
            SET msg_count = msg_count + 1, last_seen = (now() at time zone 'utc')
            WHERE id = $1
            RETURNING (SELECT last_seen FROM m)
        """
        last_seen: dt.datetime | None = await self.bot.pool.fetchval(query, message.author.id)
        if last_seen is None:
            return

        if discord.utils.utcnow() - last_seen <= dt.timedelta(seconds=LAST_SEEN_TIMEOUT):
            return

        # members who opted out (`in_lvl = FALSE`) do not get experience, hence no row to return for them
        query = "UPDATE community_members SET exp = exp + 1 WHERE id = $1 AND in_lvl RETURNING exp"
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

    @commands.Cog.listener(name="on_message")
    async def reputation_counting(self, message: discord.Message) -> None:
        """Message listener that gives reputation to the people who were thanked."""
        if message.author.bot or not message.guild or message.guild.id != const.Guild.community:
            return

        if not THANKS_REGEX.search(message.content):
            return

        # one thanks is one reputation, no matter how many thanking words are in the message
        member_ids = {m.id for m in message.mentions if m.id != message.author.id and not m.bot}
        if member_ids:
            query = "UPDATE community_members SET rep = rep + 1 WHERE id = ANY($1::bigint[])"
            await self.bot.pool.execute(query, list(member_ids))

    ####################################################################################################################
    # TASKS
    ####################################################################################################################

    @loop(time=dt.time(hour=13, minute=13, tzinfo=dt.UTC), wait_for_ready=True)
    async def remove_long_gone_members(self) -> None:
        """Remove long ago gone members.

        Just a small clean up task so we don't keep members who left long ago in the database.
        365 days is probably enough to warrant that they no longer come back.
        `community_members` table holds stuff like auto_roles, experience, msg_count.
        """
        if discord.utils.utcnow().weekday() != 3:
            # let's do this task on Thursdays only, why not xd.
            return

        guild = self.bot.community
        query = "SELECT id, last_seen, name FROM community_members WHERE last_seen < $1"
        rows: list[RemoveLongGoneRow] = await self.bot.pool.fetch(query, discord.utils.utcnow() - LONG_GONE_AFTER)

        for row in rows:
            if guild.get_member(row["id"]) is not None:
                continue  # they are in the server: `last_seen` is only updated by messages, they might just be quiet

            await self.bot.pool.execute("DELETE FROM community_members WHERE id = $1", row["id"])
            log.info("Removed %s (%s) from the database: gone for too long.", row["name"], row["id"])

            if self.LOGS_CHANNEL_ID:
                embed = discord.Embed(color=0xE6D690, description=f"id = {row['id']}").set_author(
                    name=f"{row['name']} was removed from the database"
                )
                await self.bot.get_text_channel_or_test(self.LOGS_CHANNEL_ID).send(embed=embed)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Levels(bot))
