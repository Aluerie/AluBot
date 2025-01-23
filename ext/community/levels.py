from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Literal, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bot import aluloop
from utils import const, errors, formats, pages

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext

    class RemoveLongGoneRow(TypedDict):
        id: int
        name: str
        last_seen: datetime.datetime

    class LeaderboardQueryRow(TypedDict):
        id: int
        exp: int
        rep: int


LAST_SEEN_TIMEOUT = 60

# fmt: off
exp_lvl_table = [
        5, 230, 600, 1080, 1660,  # 1-5
    2_260, 2980, 3730, 4620, 5550,  # 6-10 # "_" so rainbow indent doesn't make erroneous indent colour :D
    6_520, 7530, 8580, 9805, 11055,  # 11-15
    12330, 13630, 14955, 16455, 18045,  # 16-20
    19645, 21495, 23595, 25945, 28545,  # 21-25
    32045, 36545, 42045, 48545, 56045,  # 26-30
]
# fmt: on


async def rank_image(
    bot: AluBot,
    lvl: int,
    exp: int,
    rep: int,
    next_lvl_exp: int,
    prev_lvl_exp: int,
    place_str: str,
    member: discord.Member,
) -> Image.Image:
    image = Image.open("./assets/images/profile/welcome.png", mode="r")
    avatar = await bot.transposer.url_to_image(member.display_avatar.url)
    avatar = avatar.resize((round(image.size[1] * 1.00), round(image.size[1] * 1.00)))

    width, height = image.size
    new_width, new_height = avatar.size

    left = int(width - new_width)
    top = int((height - new_height) / 2)
    # right = int((width + new_width) / 2)
    # bottom = int((height + new_height) / 2)

    mask_im = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, new_width, new_height), fill=255)
    mask_im.save("./assets/images/profile/mask_circle.jpg", quality=95)

    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
    mask_im_blur.save("./assets/images/profile/mask_circle_blur.jpg", quality=95)

    image.paste(avatar, (left, top), mask_im)

    d = ImageDraw.Draw(image)
    d.rectangle((0, height * 6 / 7, width, height), fill=(98, 98, 98))
    d.rectangle(
        (0, height * 6 / 7, (exp - prev_lvl_exp) / (next_lvl_exp - prev_lvl_exp) * width, height),
        fill=member.color.to_rgb(),
    )

    font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 60)
    d.text((width / 4, 0), member.display_name, fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 2 / 6), f"{place_str} rank", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 3 / 6), f"LVL {lvl}", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 4 / 6), f"{rep} REP", fill=(255, 255, 255), font=font)

    msg = f"{exp}/{next_lvl_exp} EXP"
    w4, h4 = bot.transposer.get_text_wh(msg, font)
    d.text((width - w4, height * 5 / 6), msg, fill=(255, 255, 255), font=font)
    return image


def get_level(exp: int) -> int:
    level = 0
    for item in exp_lvl_table:
        if item <= exp:
            level += 1
    return level


def get_exp_for_next_level(lvl: int) -> int:
    return exp_lvl_table[lvl]


class ExperienceSystem(CommunityCog, name="Profile", emote=const.Emote.bubuAYAYA):
    """Commands about member profiles.

    There is a profile system in Irene's server: levelling experience,
    reputation and many other things (currency, custom profile) to come
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.view_user_rank = app_commands.ContextMenu(
            name="View User Server Rank",
            callback=self.context_menu_view_user_rank_callback,
            guild_ids=[const.Guild.community],
        )

    @override
    async def cog_load(self) -> None:
        self.remove_long_gone_members.start()
        self.bot.tree.add_command(self.view_user_rank)

    @override
    async def cog_unload(self) -> None:
        self.remove_long_gone_members.cancel()
        c = self.view_user_rank
        self.bot.tree.remove_command(c.name, type=c.type)

    async def context_menu_view_user_rank_callback(
        self, interaction: discord.Interaction[AluBot], member: discord.Member,
    ) -> None:
        await interaction.response.send_message(file=await self.rank_work(interaction, member), ephemeral=True)

    async def rank_work(
        self,
        ctx: AluGuildContext | discord.Interaction[AluBot],
        member: discord.Member,
    ) -> discord.File:
        """Get file that is image for rank/levels information for desired member."""
        member = member or ctx.author or ctx.user
        if member.bot:
            msg = "Sorry! our system does not count experience for bots."
            raise errors.ErroneousUsage(msg)

        query = "SELECT in_lvl, exp, rep FROM community_members WHERE id=$1"
        row = await ctx.client.pool.fetchrow(query, member.id)
        if not row.in_lvl:
            msg = "You decided to opt out of the exp system before"
            raise errors.ErroneousUsage(msg)
        lvl = get_level(row.exp)
        next_lvl_exp, prev_lvl_exp = get_exp_for_next_level(lvl), get_exp_for_next_level(lvl - 1)

        query = "SELECT COUNT(*) FROM community_members WHERE exp > $1"
        place = 1 + await ctx.client.pool.fetchval(query, row.exp)
        image = await rank_image(
            ctx.client, lvl, row.exp, row.rep, next_lvl_exp, prev_lvl_exp, formats.ordinal(place), member,
        )
        return ctx.client.transposer.image_to_file(image, filename="rank.png")

    @app_commands.guilds(const.Guild.community)
    @app_commands.command(name="rank")
    async def rank(self, interaction: discord.Interaction[AluBot], member: discord.Member) -> None:
        """View member's rank and level in this server."""
        await interaction.response.send_message(file=await self.rank_work(interaction, member), ephemeral=True)

    @app_commands.guilds(const.Guild.community)
    @app_commands.command(name="leaderboard")
    async def leaderboard(
        self, interaction: discord.Interaction[AluBot], sort_by: Literal["exp", "rep"] = "exp",
    ) -> None:
        """View experience leaderboard for this server.

        Parameters
        ----------
        sort_by
            Choose how to sort leaderboard
        """
        guild = self.community.guild

        new_array = []
        split_size = 10
        offset = 1
        cnt = offset

        query = f"""
            SELECT id, exp, rep
            FROM community_members
            WHERE in_lvl=TRUE
            ORDER BY {sort_by} DESC;
        """
        rows: list[LeaderboardQueryRow] = await self.bot.pool.fetch(query)
        for row in rows:
            if (member := guild.get_member(row["id"])) is None:
                continue
            new_array.append(
                f"{member.mention}\n`"
                f"{formats.indent(' ', cnt, offset, split_size)} "
                f"level {get_level(row["exp"])}, {row["exp"]} exp| {row["rep"]} rep`",
            )
            cnt += 1

        pgs = pages.EnumeratedPaginator(
            interaction,
            new_array,
            per_page=split_size,
            colour=const.Colour.blueviolet,
            title="Server Leaderboard",
        )
        await pgs.start()

    @commands.Cog.listener(name="on_message")
    async def experience_counting(self, message: discord.Message) -> None:
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

        author: discord.Member = message.author  # type: ignore
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
                embed = discord.Embed(
                    colour=const.Colour.blueviolet,
                    description=f"{message.author.mention} just advanced to {level_up_role.mention} ! {const.Emote.PepoG}",
                )
                await message.channel.send(embed=embed)
                await author.remove_roles(previous_level_role)
                await author.add_roles(level_up_role)

    thanks_words = ("thanks", "ty", "thank")

    @app_commands.command(name="give-rep")
    @app_commands.guilds(const.Guild.community)
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(member="Member to give rep to")
    async def reputation(self, interaction: discord.Interaction[AluBot], member: discord.Member) -> None:
        """Give +1 to `@member`'s reputation ;"""
        if member == interaction.user or member.bot:
            msg = "You can't give reputation to yourself or bots."
            raise errors.ErroneousUsage(msg)
        query = "UPDATE community_members SET rep=rep+1 WHERE id=$1 RETURNING rep"
        reputation: int = await self.bot.pool.fetchval(query, member.id)
        embed = discord.Embed(
            color=discord.Colour.green(),
            description=f"Added +1 reputation to **{member.display_name}**: now {reputation} reputation",
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener(name="on_message")
    async def reputation_counting(self, message: discord.Message) -> None:
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
                embed = discord.Embed(
                    colour=0xE6D690,
                    description=f"id = {row['id']}",
                ).set_author(name=f"{row['name']} was removed from the database")
                await self.community.logs.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ExperienceSystem(bot))
