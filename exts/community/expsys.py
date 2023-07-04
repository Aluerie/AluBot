from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Literal, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from utils import AluCog
from utils.const import Colour, Emote, Guild
from utils.formats import indent, ordinal
from utils.pagination import EnumeratedPages

from ._base import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot, AluGuildContext

LAST_SEEN_TIMEOUT = 60

# fmt: off
exp_lvl_table = [
    5, 230, 600, 1080, 1660, 2260, 2980, 3730, 4620, 5550, 6520, 7530, 8580, 9805, 11055, 12330, 13630, 
    14955, 16455, 18045, 19645, 21495, 23595, 25945, 28545, 32045, 36545, 42045, 48545, 56045,
]
# fmt: on
thanks_words = ['thanks', 'ty', 'thank']


async def rank_image(bot: AluBot, lvl, exp, rep, next_lvl_exp, prev_lvl_exp, place_str, member):
    image = Image.open('./assets/images/profile/welcome.png', mode='r')
    avatar = await bot.imgtools.url_to_img(member.display_avatar.url)
    avatar = avatar.resize((round(image.size[1] * 1.00), round(image.size[1] * 1.00)))

    width, height = image.size
    new_width, new_height = avatar.size

    left = int((width - new_width))
    top = int((height - new_height) / 2)
    # right = int((width + new_width) / 2)
    # bottom = int((height + new_height) / 2)

    mask_im = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, new_width, new_height), fill=255)
    mask_im.save('./assets/images/profile/mask_circle.jpg', quality=95)

    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
    mask_im_blur.save('./assets/images/profile/mask_circle_blur.jpg', quality=95)

    image.paste(avatar, (left, top), mask_im)

    d = ImageDraw.Draw(image)
    d.rectangle((0, height * 6 / 7, width, height), fill=(98, 98, 98))
    d.rectangle(
        (0, height * 6 / 7, (exp - prev_lvl_exp) / (next_lvl_exp - prev_lvl_exp) * width, height),
        fill=member.color.to_rgb(),
    )

    font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 60)
    d.text((width / 4, 0), member.display_name, fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 2 / 6), f"{place_str} rank", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 3 / 6), f"LVL {lvl}", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 4 / 6), f"{rep} REP", fill=(255, 255, 255), font=font)

    msg = f"{exp}/{next_lvl_exp} EXP"
    w4, h4 = bot.imgtools.get_text_wh(msg, font)
    d.text((width - w4, height * 5 / 6), msg, fill=(255, 255, 255), font=font)
    return image


def get_level(exp):
    level = 0
    for item in exp_lvl_table:
        if item <= exp:
            level += 1
    return level


def get_exp_for_next_level(lvl):
    return exp_lvl_table[lvl]


async def avatar_work(ctx, user: discord.User):
    user = user or getattr(ctx, 'author') or getattr(ctx, 'user')
    e = discord.Embed(colour=user.colour, title=f'Avatar for {user.display_name}')
    e.set_image(url=user.display_avatar.url)
    return e


async def avatar_user_cmd(ntr: discord.Interaction, user: discord.User):
    e = await avatar_work(ntr, user)
    await ntr.response.send_message(embed=e, ephemeral=True)


async def rank_work(ctx: Union[AluGuildContext, discord.Interaction[AluBot]], member: discord.Member):
    member = member or getattr(ctx, 'author') or getattr(ctx, 'user')
    if member.bot:
        raise commands.BadArgument('Sorry! our system does not count experience for bots.')

    query = 'SELECT inlvl, exp, rep FROM users WHERE id=$1'
    row = await ctx.client.pool.fetchrow(query, member.id)
    if not row.inlvl:
        raise commands.BadArgument("You decided to opt out of the exp system before")
    lvl = get_level(row.exp)
    next_lvl_exp, prev_lvl_exp = get_exp_for_next_level(lvl), get_exp_for_next_level(lvl - 1)

    query = 'SELECT count(*) FROM users WHERE exp > $1'
    place = 1 + await ctx.client.pool.fetchval(query, row.exp)
    bot = getattr(ctx, 'bot') or getattr(ctx, 'client')
    image = await rank_image(bot.ses, lvl, row.exp, row.rep, next_lvl_exp, prev_lvl_exp, ordinal(place), member)
    return ctx.client.imgtools.img_to_file(image, filename='rank.png')


async def rank_user_cmd(ntr: discord.Interaction[AluBot], member: discord.Member):
    await ntr.response.send_message(file=await rank_work(ntr, member), ephemeral=True)


class ExperienceSystem(CommunityCog, name='Profile'):
    """Commands about member profiles

    There is a profile system in Irene\'s server: levelling experience,
    reputation and many other things (currency, custom profile) to come
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ctx_menu1 = app_commands.ContextMenu(name="View User Avatar", callback=avatar_user_cmd)
        self.ctx_menu2 = app_commands.ContextMenu(name="View User Server Rank", callback=rank_user_cmd)

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Emote.bubuAyaya)

    async def cog_load(self) -> None:
        self.remove_inactive.start()
        self.bot.tree.add_command(self.ctx_menu1)
        self.bot.tree.add_command(self.ctx_menu2)

    async def cog_unload(self) -> None:
        self.remove_inactive.cancel()

    @commands.hybrid_command(name='leaderboard', aliases=['l'], description='View server leaderboard')
    @app_commands.describe(sort_by='Choose how to sort leaderboard')
    async def leaderboard(self, ctx, sort_by: Literal['exp', 'rep'] = 'exp'):
        """View experience leaderboard for this server ;"""
        guild = self.community.guild

        new_array = []
        split_size = 10
        offset = 1
        cnt = offset

        query = f"""SELECT id, exp, rep 
                    FROM users 
                    WHERE inlvl=TRUE
                    ORDER BY {sort_by} DESC;
                """
        rows = await self.bot.pool.fetch(query)
        for row in rows:  # type: ignore
            if (member := guild.get_member(row.id)) is None:
                continue
            new_array.append(
                f"{member.mention}\n`"
                f"{indent(' ', cnt, offset, split_size)} "
                f"level {get_level(row.exp)}, {row.exp} exp| {row.rep} rep`"
            )
            cnt += 1

        pgs = EnumeratedPages(
            ctx,
            new_array,
            per_page=split_size,
            colour=Colour.prpl(),
            title="Server Leaderboard",
            footer_text=f'With love, {guild.me.display_name}',
        )
        await pgs.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild and message.guild.id in [Guild.community]:
            query = """ WITH u AS (
                            SELECT lastseen FROM users WHERE id=$1
                        )           
                        UPDATE users 
                        SET msg_count=msg_count+1, lastseen=(now() at time zone 'utc')
                        WHERE id=$1
                        RETURNING (SELECT lastseen from u)
                    """
            lastseen = await self.bot.pool.fetchval(query, message.author.id)

            author: discord.Member = message.author  # type: ignore
            dt_now = discord.utils.utcnow()
            if dt_now - lastseen > datetime.timedelta(seconds=LAST_SEEN_TIMEOUT):
                query = 'UPDATE users SET exp=exp+1 WHERE id=$1 RETURNING exp'
                exp = await self.bot.pool.fetchval(query, message.author.id)
                level = get_level(exp)

                if exp == get_exp_for_next_level(get_level(exp) - 1):
                    level_up_role: Optional[discord.Role] = discord.utils.get(
                        message.guild.roles, name=f"Level #{level}"
                    )
                    previous_level_role: Optional[discord.Role] = discord.utils.get(
                        message.guild.roles, name=f"Level #{level - 1}"
                    )
                    if not level_up_role or not previous_level_role:
                        raise ValueError('Roles were not found in the community guild')
                    e = discord.Embed(colour=Colour.prpl())
                    e.description = '{0} just advanced to {1} ! ' '{2} {2} {2}'.format(
                        message.author.mention, level_up_role.mention, Emote.PepoG
                    )
                    await message.channel.send(embed=e)
                    await author.remove_roles(previous_level_role)
                    await author.add_roles(level_up_role)

            for item in thanks_words:  # reputation part
                if item in message.content.lower():
                    for member in message.mentions:
                        if member != message.author:
                            query = 'UPDATE users SET rep=rep+1 WHERE id=$1'
                            await self.bot.pool.execute(query, member.id)

    @commands.hybrid_command(name='rep', description='Give +1 to @member reputation')
    @commands.cooldown(1, 60 * 60, commands.BucketType.user)
    @app_commands.describe(member='Member to give rep to')
    async def rep(self, ctx, member: discord.Member):
        """Give +1 to `@member`'s reputation ;"""
        if member == ctx.author or member.bot:
            await ctx.reply(content='You can\'t give reputation to yourself or bots')
        else:
            query = 'UPDATE users SET rep=rep+1 WHERE id=$1 RETURNING rep'
            rep = await self.bot.pool.fetchval(query, member.id)
            answer_text = f'Added +1 reputation to **{member.display_name}**: now {rep} reputation'
            await ctx.reply(content=answer_text)

    @tasks.loop(time=datetime.time(hour=13, minute=13, tzinfo=datetime.timezone.utc))
    async def remove_inactive(self):
        query = "SELECT id, lastseen, name FROM users"
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            guild = self.community.guild
            person = guild.get_member(row.id)
            if person is None and discord.utils.utcnow() - row.lastseen > datetime.timedelta(days=30):
                query = 'DELETE FROM users WHERE id=$1'
                await self.bot.pool.execute(query, row.id)
                e = discord.Embed(description=f"id = {row.id}", colour=0xE6D690)
                e.set_author(name=f"{row.name} was removed from the database")
                await self.community.logs.send(embed=e)

    @remove_inactive.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(ExperienceSystem(bot))
