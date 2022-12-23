from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Literal, Union

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from discord import Embed, Member, utils, app_commands
from discord.ext import commands, tasks

from .utils.distools import inout_to_10, send_pages_list
from .utils.format import ordinal, humanize_time, indent
from .utils.imgtools import url_to_img, img_to_file, get_text_wh
from .utils.var import Ems, Sid, Cid, Cids, Clr

if TYPE_CHECKING:
    from discord import Interaction, Message
    from .utils.bot import AluBot
    from .utils.context import Context

LAST_SEEN_TIMEOUT = 60

exp_lvl_table = [
    5, 230, 600, 1080, 1660, 2260, 2980, 3730, 4620, 5550,
    6520, 7530, 8580, 9805, 11055, 12330, 13630, 14955, 16455, 18045,
    19645, 21495, 23595, 25945, 28545, 32045, 36545, 42045, 48545, 56045
]

thanks_words = ['thanks', 'ty', 'thank']


async def rank_image(session, lvl, exp, rep, next_lvl_exp, prev_lvl_exp, place_str, member):
    image = Image.open('./media/welcome.png', mode='r')
    avatar = await url_to_img(session, member.display_avatar.url)
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
    mask_im.save('./media/mask_circle.jpg', quality=95)

    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
    mask_im_blur.save('./media/mask_circle_blur.jpg', quality=95)

    image.paste(avatar, (left, top), mask_im)

    d = ImageDraw.Draw(image)
    d.rectangle([0, height * 6 / 7, width, height], fill=(98, 98, 98))
    d.rectangle([0, height * 6 / 7, (exp - prev_lvl_exp) / (next_lvl_exp - prev_lvl_exp) * width, height],
                fill=member.color.to_rgb())

    font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 60)
    d.text((width / 4, 0), member.display_name, fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 2 / 6), f"{place_str} rank", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 3 / 6), f"LVL {lvl}", fill=(255, 255, 255), font=font)
    d.text((width / 4, height * 4 / 6), f"{rep} REP", fill=(255, 255, 255), font=font)

    msg = f"{exp}/{next_lvl_exp} EXP"
    w4, h4 = get_text_wh(msg, font)
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


async def avatar_work(ctx, member):
    member = member or getattr(ctx, 'author') or getattr(ctx, 'user')
    embed = Embed(colour=member.colour, title=f'Avatar for {member.display_name}')
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f'With love, {ctx.guild.me.display_name}')
    return embed


async def avatar_usercmd(ntr: Interaction, mbr: Member):
    embed = await avatar_work(ntr, mbr)
    await ntr.response.send_message(embed=embed, ephemeral=True)


async def rank_work(ctx: Union[Context, Interaction], member: Member):
    member = member or getattr(ctx, 'author') or getattr(ctx, 'user')
    if member.bot:
        raise commands.BadArgument('Sorry! our system does not count experience for bots.')

    query = 'SELECT inlvl, exp, rep FROM users WHERE id=$1'
    row = await ctx.pool.fetchrow(query, member.id)
    if not row.inlvl:
        return await ctx.reply(content="You decided to opt out of the exp system before")
    lvl = get_level(row.exp)
    next_lvl_exp, prev_lvl_exp = get_exp_for_next_level(lvl), get_exp_for_next_level(lvl-1)

    query = 'SELECT count(*) FROM users WHERE exp > $1'
    place = 1 + await ctx.pool.fetchval(query, row.exp)
    bot = getattr(ctx, 'bot') or getattr(ctx, 'client')
    image = await rank_image(bot.ses, lvl, row.exp, row.rep, next_lvl_exp, prev_lvl_exp, ordinal(place), member)
    return img_to_file(image, filename='rank.png')


async def rank_usercmd(ntr: Interaction, member: Member):
    await ntr.response.send_message(file=await rank_work(ntr, member), ephemeral=True)


class ExperienceSystem(commands.Cog, name='Profile'):
    """
    Commands about member profiles

    There is a profile system in Irene\'s server: levelling experience,
    reputation and many other things (currency, custom profile) to come
    """
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.bubuAyaya

        self.remove_inactive.start()

        self.ctx_menu1 = app_commands.ContextMenu(name="View User Avatar", callback=avatar_usercmd)
        self.bot.tree.add_command(self.ctx_menu1)

        self.ctx_menu2 = app_commands.ContextMenu(name="View User Server Rank", callback=rank_usercmd)
        self.bot.tree.add_command(self.ctx_menu2)

    def cog_unload(self) -> None:
        self.remove_inactive.cancel()

    @commands.hybrid_command(
        aliases=['ls'],
        usage='[member=you]',
        description='Show when `@member` was last seen'
    )
    @app_commands.describe(member='Member to check')
    async def lastseen(self, ctx, member: Member = None):
        """Show when `@member` was last seen on this server ;"""
        member = member or ctx.author
        query = 'SELECT lastseen FROM users WHERE id=$1'
        lastseen = await self.bot.pool.fetchval(query, member.id)
        dt_delta = datetime.now(timezone.utc) - lastseen
        answer_text = f'{member.mention} was last seen in this server {humanize_time(dt_delta)} ago'
        await ctx.reply(content=answer_text)

    @commands.hybrid_command(
        name='leaderboard',
        aliases=['l'],
        description='View server leaderboard'
    )
    @app_commands.describe(sort_by='Choose how to sort leaderboard')
    async def leaderboard(self, ctx, sort_by: Literal['exp', 'rep'] = 'exp'):
        """View experience leaderboard for this server ;"""
        guild = self.bot.get_guild(Sid.alu)

        new_array = []
        split_size = 10
        offset = 1
        cnt = offset

        query = f"""SELECT id, exp, rep 
                    FROM users 
                    WHERE inlvl!=0
                    ORDER BY {sort_by} DESC;
                """
        rows = await self.bot.pool.fetch(query)
        for row in rows:  # type: ignore
            if (member := guild.get_member(row.id)) is None:
                continue
            new_array.append(
                f"`{indent(cnt, cnt, offset, split_size)}` {member.mention}\n`"
                f"{indent(' ', cnt, offset, split_size)} "
                f"level {get_level(row.exp)}, {row.exp} exp| {row.rep} rep`"
            )
            cnt += 1

        await send_pages_list(
            ctx,
            new_array,
            split_size=split_size,
            colour=Clr.prpl,
            title="Server Leaderboard",
            footer_text=f'With love, {guild.me.display_name}'
        )

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        # if self.bot.test_flag:
        #    return  # let's not mess up with Yennifer
        if msg.author.bot or msg.channel.id in Cids.blacklisted_array:
            return

        if msg.guild is not None and msg.guild.id in Sid.guild_ids:

            query = """ WITH u AS (
                            SELECT lastseen FROM users WHERE id=$1
                        )           
                        UPDATE users 
                        SET msg_count=msg_count+1, lastseen=(now() at time zone 'utc')
                        WHERE id=$1
                        RETURNING (SELECT lastseen from u)
                    """
            lastseen = await self.bot.pool.fetchval(query, msg.author.id)

            dt_now = datetime.now(timezone.utc)
            if dt_now - lastseen > timedelta(seconds=LAST_SEEN_TIMEOUT):
                query = 'UPDATE users SET exp=exp+1 WHERE id=$1 RETURNING exp'
                exp = await self.bot.pool.fetchval(query, msg.author.id)
                level = get_level(exp)

                if exp == get_exp_for_next_level(get_level(exp) - 1):
                    level_up_role = utils.get(msg.guild.roles, name=f"Level #{level}")
                    previous_level_role = utils.get(msg.guild.roles, name=f"Level #{level - 1}")
                    em = Embed(colour=Clr.prpl)
                    em.description = (
                        '{0} just advanced to {1} ! '
                        '{2} {2} {2}'.format(msg.author.mention, level_up_role.mention, Ems.PepoG)
                    )
                    await msg.channel.send(embed=em)
                    await msg.author.remove_roles(previous_level_role)
                    await msg.author.add_roles(level_up_role)

            for item in thanks_words:  # reputation part
                if item in msg.content.lower():
                    for member in msg.mentions:
                        if member != msg.author:
                            query = 'UPDATE users SET rep=rep+1 WHERE id=$1'
                            await self.bot.pool.execute(query, member.id)

    @commands.hybrid_command(
        name='avatar',
        description="View User Avatar",
        usage='[member=you]'
    )
    async def avatar_bridge(self, ctx, member: Member = None):
        """Show avatar for `@member` ;"""
        embed = await avatar_work(ctx, member)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        aliases=['r'],
        name='rank',
        description="View User Server Rank",
        usage='[member=you]'
    )
    async def rank_bridge(self, ctx: Context,  *, member: Member = None):
        """Show `@member`'s rank, level and experience ;"""
        await ctx.reply(file=await rank_work(ctx, member))

    @commands.group()
    async def levels(self, ctx: Context):
        """Group command about Levels, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @levels.command(usage='in/out')
    async def opt(self, ctx: Context, in_or_out: inout_to_10):
        """Opt `in/out` of exp system notifs and all leaderboard presence ;"""
        query = f'UPDATE users SET inlvl={in_or_out} WHERE id=$1;'
        await self.bot.pool.execute(query, ctx.author.id)
        ans = f'{ctx.author.display_name} is now opted {in_or_out} of exp-system notifications and being in leaderboards'
        await ctx.reply(content=ans)

    @commands.hybrid_command(
        name='rep',
        description='Give +1 to @member reputation'
    )
    @commands.cooldown(1, 60*60, commands.BucketType.user)
    @app_commands.describe(member='Member to give rep to')
    async def rep(self, ctx, member: Member):
        """Give +1 to `@member`'s reputation ;"""
        if member == ctx.author or member.bot:
            await ctx.reply(content='You can\'t give reputation to yourself or bots')
        else:
            query = 'UPDATE users SET rep=rep+1 WHERE id=$1 RETURNING rep'
            rep = await self.bot.pool.fetchval(query, member.id)
            answer_text = f'Added +1 reputation to **{member.display_name}**: now {rep} reputation'
            await ctx.reply(content=answer_text) 

    @tasks.loop(time=time(hour=13, minute=13, tzinfo=timezone.utc))
    async def remove_inactive(self):
        query = "SELECT id, lastseen, name FROM users"
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            guild = self.bot.get_guild(Sid.alu)
            person = guild.get_member(row.id)
            if person is None and datetime.now(timezone.utc) - row.lastseen > timedelta(days=30):
                query = 'DELETE FROM users WHERE id=$1'
                await self.bot.pool.execute(query, row.id)
                em = Embed(
                    colour=0xE6D690,
                    description=f"id = {row.id}"
                ).set_author(
                    name=f"{row.name} was removed from the datebase"
                )
                await guild.get_channel(Cid.logs).send(embed=em)

    @remove_inactive.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ExperienceSystem(bot))
