from __future__ import annotations

import asyncio
import datetime
import itertools
from typing import TYPE_CHECKING, Literal, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from tabulate import tabulate

from bot import AluCog, aluloop
from utils import const, errors, fmt, pages

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

    class RemoveLongGoneRow(TypedDict):
        id: int
        name: str
        last_seen: datetime.datetime

    class LeaderboardQueryRow(TypedDict):
        id: int
        exp: int
        rep: int

    class RankQueryRow(TypedDict):
        in_lvl: bool
        exp: int
        rep: int


__all__ = ("Levels",)


LAST_SEEN_TIMEOUT = 60

# fmt: off
exp_lvl_table = [
        5, 230, 600, 1080, 1660,  # 1-5
    2_260, 2980, 3730, 4620, 5550,  # 6-10 # "_" so rainbow indent doesn't make erroneous indent color :D
    6_520, 7530, 8580, 9805, 11055,  # 11-15
    12330, 13630, 14955, 16455, 18045,  # 16-20
    19645, 21495, 23595, 25945, 28545,  # 21-25
    32045, 36545, 42045, 48545, 56045,  # 26-30
]
# fmt: on


def get_level(exp: int) -> int:
    level = 0
    for item in exp_lvl_table:
        if item <= exp:
            level += 1
    return level


def get_exp_for_next_level(lvl: int) -> int:
    return exp_lvl_table[lvl]


class Levels(AluCog):
    """Experience and Levels System.

    Just a lame XP per Message system with some fancy images and tables.
    """

    @override
    async def cog_load(self) -> None:
        self.remove_long_gone_members.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.remove_long_gone_members.cancel()
        await super().cog_unload()

    @app_commands.guilds(*const.MY_GUILDS)
    @app_commands.command(name="rank")
    @app_commands.rename(member_="member")
    async def rank(self, interaction: AluInteraction, member_: discord.Member | None = None) -> None:
        """View member's rank and experience level in this server.

        Parameters
        ----------
        member_: discord.User | None = None
            Member to check experience and rank of.
        """
        member = member_ or interaction.user

        if member.bot:
            msg = "Sorry! our system does not count experience for bots."
            raise errors.ErroneousUsage(msg)

        query = "SELECT in_lvl, exp, rep FROM community_members WHERE id=$1"
        row: RankQueryRow = await interaction.client.pool.fetchrow(query, member.id)
        if not row["in_lvl"]:
            msg = "You decided to opt out of the exp system before"
            raise errors.ErroneousUsage(msg)

        lvl = get_level(row["exp"])
        next_lvl_exp, prev_lvl_exp = get_exp_for_next_level(lvl), get_exp_for_next_level(lvl - 1)

        query = "SELECT COUNT(*) FROM community_members WHERE exp > $1"
        place: int = 1 + await interaction.client.pool.fetchval(query, row["exp"])

        member_avatar = await interaction.client.transposer.url_to_image(member.display_avatar.url)

        def build_image() -> Image.Image:
            """Build Rank Image."""
            canvas = Image.open("./assets/images/profile/welcome.png", mode="r")
            avatar = member_avatar.resize((round(canvas.size[1] * 1.00), round(canvas.size[1] * 1.00)))

            canvas_w, canvas_h = canvas.size
            avatar_w, avatar_h = avatar.size

            left = int(canvas_w - avatar_w)
            top = int((canvas_h - avatar_h) / 2)

            mask_im = Image.new("L", avatar.size, 0)
            draw = ImageDraw.Draw(mask_im)
            draw.ellipse((0, 0, avatar_w, avatar_h), fill=255)
            mask_im.save("./assets/images/profile/mask_circle.jpg", quality=95)

            mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
            mask_im_blur.save("./assets/images/profile/mask_circle_blur.jpg", quality=95)

            canvas.paste(avatar, (left, top), mask_im)

            d = ImageDraw.Draw(canvas)
            d.rectangle((0, canvas_h * 6 / 7, canvas_w, canvas_h), fill=(98, 98, 98))
            d.rectangle(
                (0, canvas_h * 6 / 7, (row["exp"] - prev_lvl_exp) / (next_lvl_exp - prev_lvl_exp) * canvas_w, canvas_h),
                fill=member.color.to_rgb(),
            )

            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 60)
            d.text((canvas_w / 4, 0), member.display_name, fill=(255, 255, 255), font=font)
            d.text((canvas_w / 4, canvas_h * 2 / 6), f"{fmt.ordinal(place)} rank", fill=(255, 255, 255), font=font)
            d.text((canvas_w / 4, canvas_h * 3 / 6), f"{fmt.ordinal(lvl)} level", fill=(255, 255, 255), font=font)
            d.text((canvas_w / 4, canvas_h * 4 / 6), f"{row['rep']} rep", fill=(255, 255, 255), font=font)

            msg = f"{row['exp']}/{next_lvl_exp} EXP"
            w4, _h4 = interaction.client.transposer.get_text_wh(msg, font)
            d.text((canvas_w - w4, canvas_h * 5 / 6), msg, fill=(255, 255, 255), font=font)
            return canvas

        rank_image = await asyncio.to_thread(build_image)
        file = interaction.client.transposer.image_to_file(rank_image, filename="rank.png")
        await interaction.response.send_message(file=file)

    @app_commands.guilds(*const.MY_GUILDS)
    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: AluInteraction, sort_by: Literal["exp", "rep"] = "exp") -> None:
        """View experience leaderboard for this server.

        Parameters
        ----------
        sort_by: Literal["exp", "rep"] = "exp"
            Choose how to sort leaderboard
        """
        guild = self.community.guild

        query = f"""
            SELECT id, exp, rep
            FROM community_members
            WHERE in_lvl=TRUE
            ORDER BY {sort_by} DESC;
        """
        rows: list[LeaderboardQueryRow] = await self.bot.pool.fetch(query)
        # clean up the rows from inactive members
        members = [(member, row) for row in rows if (member := guild.get_member(row["id"])) is not None]

        offset = 0
        split_size = 10
        tables: list[str] = []

        for batch in itertools.batched(members, n=split_size):
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
            template={
                "footer": {
                    "text": f"Sorted by {sort_by}",
                    "icon_url": guild.icon.url if guild.icon else discord.utils.MISSING,
                }
            },
        )
        await paginator.start()

    @commands.Cog.listener(name="on_message")
    async def experience_counting(self, message: discord.Message) -> None:
        """Message listener that counts experience points."""
        if message.author.bot:
            return

        if not message.guild or message.guild.id != const.Guild.community:
            return

        query = """
            WITH m AS (SELECT last_seen FROM community_members WHERE id=$1)
            UPDATE community_members
            SET msg_count = msg_count+1, last_seen = (now() at time zone 'utc')
            WHERE id = $1
            RETURNING (SELECT last_seen from m)
        """
        last_seen: datetime.datetime = await self.bot.pool.fetchval(query, message.author.id)

        author: discord.Member = message.author  # type: ignore[reportAssignmentType]
        now = datetime.datetime.now(datetime.UTC)
        if now - last_seen > datetime.timedelta(seconds=LAST_SEEN_TIMEOUT):
            query = "UPDATE community_members SET exp = exp+1 WHERE id = $1 RETURNING exp"
            exp = await self.bot.pool.fetchval(query, message.author.id)
            level = get_level(exp)

            if exp == get_exp_for_next_level(get_level(exp) - 1):
                level_up_role = discord.utils.get(message.guild.roles, name=f"Level #{level}")
                previous_level_role = discord.utils.get(message.guild.roles, name=f"Level #{level - 1}")
                if not level_up_role or not previous_level_role:
                    msg = "Roles were not found in the community guild"
                    raise ValueError(msg)

                text = f"{message.author.mention} just advanced to {level_up_role.mention} ! {const.Emote.PepoG}"
                embed = discord.Embed(color=const.Color.prpl, description=text)
                await message.channel.send(embed=embed)
                await author.remove_roles(previous_level_role)
                await author.add_roles(level_up_role)

    thanks_words = ("thanks", "ty", "thank")

    @app_commands.command(name="give-rep")
    @app_commands.guilds(const.Guild.community)
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(member="Member to give rep to")
    async def reputation(self, interaction: AluInteraction, member: discord.Member) -> None:
        """Give +1 to `@member`'s reputation."""
        if member == interaction.user or member.bot:
            msg = "You can't give reputation to yourself or bots."
            raise errors.ErroneousUsage(msg)
        query = "UPDATE community_members SET rep=rep+1 WHERE id=$1 RETURNING rep"
        reputation: int = await self.bot.pool.fetchval(query, member.id)
        embed = discord.Embed(
            color=discord.Color.green(),
            description=f"Added +1 reputation to **{member.display_name}**: now {reputation} reputation",
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener(name="on_message")
    async def reputation_counting(self, message: discord.Message) -> None:
        """Message listener that counts experience points."""
        if message.author.bot:
            return

        if not message.guild or message.guild.id != const.Guild.community:
            return

        for item in self.thanks_words:  # reputation part
            if item in message.content.lower():
                for member in message.mentions:
                    if member != message.author:
                        query = "UPDATE community_members SET rep=rep+1 WHERE id=$1"
                        await self.bot.pool.execute(query, member.id)

    @aluloop(time=datetime.time(hour=13, minute=13, tzinfo=datetime.UTC))
    async def remove_long_gone_members(self) -> None:
        """Remove long ago gone members.

        Just a small clean up task so we don't keep members who left long ago in the database.
        365 days is probably enough to warrant that they no longer come back.
        `community_members` table holds stuff like auto_roles, experience, msg_count.
        """
        if datetime.datetime.now(datetime.UTC).weekday() != 3:
            # let's do this task on Thursdays only, why not xd.
            return

        query = "SELECT id, last_seen, name FROM community_members"
        rows: list[RemoveLongGoneRow] = await self.bot.pool.fetch(query)

        for row in rows:
            guild = self.community.guild
            person = guild.get_member(row["id"])
            if person is None and discord.utils.utcnow() - row["last_seen"] > datetime.timedelta(days=365):
                query = "DELETE FROM community_members WHERE id=$1"
                await self.bot.pool.execute(query, row["id"])
                embed = discord.Embed(color=0xE6D690, description=f"id = {row['id']}").set_author(
                    name=f"{row['name']} was removed from the database"
                )
                await self.community.logs.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Levels(bot))
