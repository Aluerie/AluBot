from __future__ import annotations
from typing import TYPE_CHECKING, Literal

from discord import Embed, Member, utils, app_commands
from discord.ext import commands, tasks

from utils.var import *
from utils import database as db
from utils.format import ordinal, humanize_time
from utils.imgtools import url_to_img, img_to_file
from utils.discord import scnf, inout_to_10
from utils import pages

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from datetime import datetime, time, timedelta, timezone

if TYPE_CHECKING:
    from discord import Interaction

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
    msg = member.display_name
    #  w1, h1 = d.textsize(msg, font=font)
    d.text((width / 4, 0), msg, fill=(255, 255, 255), font=font)

    msg = f"{place_str} rank"
    #  w2, h2 = d.textsize(msg, font=font)
    d.text((width / 4, height * 2 / 6), msg, fill=(255, 255, 255), font=font)

    msg = f"LVL {lvl}"
    #  w3, h3 = d.textsize(msg, font=font)
    d.text((width / 4, height * 3 / 6), msg, fill=(255, 255, 255), font=font)

    msg = f"{rep} REP"
    #  w4, h4 = d.textsize(msg, font=font)
    d.text((width / 4, height * 4 / 6), msg, fill=(255, 255, 255), font=font)

    msg = f"{exp}/{next_lvl_exp} EXP"
    w4, h4 = d.textsize(msg, font=font)
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


async def rank_work(ctx, member):
    member = member or getattr(ctx, 'author') or getattr(ctx, 'user')
    mrow = db.session.query(db.m).filter_by(id=member.id).first()
    if not mrow.inlvl:
        return await ctx.reply(content="You decided to opt out of the exp system before")
    if member.bot:
        await ctx.reply(content='Sorry, our system does not count experience for bots.')
    lvl = get_level(mrow.exp)
    next_lvl_exp, prev_lvl_exp = get_exp_for_next_level(lvl), get_exp_for_next_level(lvl-1)

    place = 1 + db.session.query(db.m).where(db.m.exp > mrow.exp).count()
    bot = getattr(ctx, 'bot') or getattr(ctx, 'client')
    image = await rank_image(bot.ses, lvl, mrow.exp, mrow.rep, next_lvl_exp, prev_lvl_exp, ordinal(place), member)
    return img_to_file(image, filename='rank.png')


async def rank_usercmd(ntr: Interaction, member: Member):
    await ntr.response.send_message(file=await rank_work(ntr, member), ephemeral=True)


class ExperienceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.remove_inactive.start()
        self.help_category = 'Profile'
        self.ctx_menu1 = app_commands.ContextMenu(name="View User Avatar", callback=avatar_usercmd)
        self.bot.tree.add_command(self.ctx_menu1)
        self.ctx_menu2 = app_commands.ContextMenu(name="View User Server Rank", callback=rank_usercmd)
        self.bot.tree.add_command(self.ctx_menu2)

    @commands.hybrid_command(
        brief=Ems.slash,
        aliases=['ls'],
        usage='[member=you]',
        description='Show when `@member` was last seen'
    )
    @app_commands.describe(member='Member to check')
    async def lastseen(self, ctx, member: Member = None):
        """Show when `@member` was last seen on this server ;"""
        member = member or ctx.author
        lastseen = db.get_value(db.m, member.id, 'lastseen').replace(tzinfo=timezone.utc)
        dt_delta = datetime.now(timezone.utc) - lastseen
        answer_text = f'{member.mention} was last seen in this server {humanize_time(dt_delta)} ago'
        await ctx.reply(content=answer_text)

    @commands.hybrid_command(
        name='leaderboard',
        brief=Ems.slash,
        aliases=['l'],
        description='View server leaderboard'
    )
    @app_commands.describe(sort_by='Choose how to sort leaderboard')
    async def leaderboard(self, ctx, sort_by: Literal['exp', 'rep']):
        """View experience leaderboard for this server ;"""
        irene_server = self.bot.get_guild(Sid.irene)
        new_array = []

        match sort_by:
            case 'rep':
                db_col_desc = db.m.rep.desc()
            case 'exp':
                db_col_desc = db.m.exp.desc()
            case _:
                return ctx.reply('wrong sorting was given')

        for row in db.session.query(db.m).filter(db.m.inlvl == 1).order_by(db_col_desc):
            if (member := irene_server.get_member(row.id)) is None:
                continue
            new_array.append([member.mention, get_level(row.exp), row.exp, row.rep])

        split_size = 10
        places_list = [new_array[x:x+split_size] for x in range(0, len(new_array), split_size)]
        embeds_list = []
        offset = 1
        for item in places_list:
            embed = Embed(colour=Clr.prpl, title="Server Leaderboard")
            embed.set_footer(text=f'With love, {irene_server.me.display_name}')

            def indent(symbol):
                return str(symbol).ljust(len(str(offset - 1 + split_size)), " ")
            embed.description = '\n'.join(
                f'`{indent(i)}` {v[0]}\n`'
                f'{indent(" ")} level {v[1]}, {v[2]} exp| {v[3]} rep`'
                for i, v in enumerate(item, start=offset)
            )
            offset += split_size
            embeds_list.append(embed)
        paginator = pages.Paginator(pages=embeds_list)
        await paginator.send(ctx)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if self.bot.yen:
            return  # let's not mess up with Yennifer
        if msg.author.bot or msg.channel.id in Cid.blacklisted_array:
            return

        if msg.guild is not None and msg.guild.id in Sid.guild_ids:
            with db.session_scope() as ses:
                user = ses.query(db.m).filter_by(id=msg.author.id).first()  # exp part
                user.msg_count += 1
                dt_now = datetime.now(timezone.utc)
                if dt_now - user.lastseen.replace(tzinfo=timezone.utc) > timedelta(seconds=LAST_SEEN_TIMEOUT):
                    user.exp += 1
                    level = get_level(user.exp)
                    user.lastseen = dt_now
                    if user.exp == get_exp_for_next_level(get_level(user.exp) - 1):
                        level_up_role = utils.get(msg.guild.roles, name=f"Level #{level}")
                        previous_level_role = utils.get(msg.guild.roles, name=f"Level #{level - 1}")
                        embed = Embed(colour=Clr.prpl)
                        embed.description = '{0} just advanced to {1} ! {2} {2} {2}'\
                            .format(msg.author.mention, level_up_role.mention, Ems.PepoG)
                        await msg.channel.send(embed=embed)
                        await msg.author.remove_roles(previous_level_role)
                        await msg.author.add_roles(level_up_role)

                for item in thanks_words:  # reputation part
                    if item in msg.content.lower():
                        for member in msg.mentions:
                            if member != msg.author:
                                user = ses.query(db.m).filter_by(id=member.id).first()
                                user.rep += 1

    @commands.hybrid_command(
        brief=Ems.slash,
        name='avatar',
        description="View User Avatar",
        usage='[member=you]'
    )
    async def avatar_bridge(self, ctx, member: Member = None):
        """Show avatar for `@member` ;"""
        embed = await avatar_work(ctx, member)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        brief=Ems.slash,
        aliases=['r'],
        name='rank',
        description="View User Server Rank",
        usage='[member=you]'
    )
    async def rank_bridge(self, ctx,  *, member: Member = None):
        """Show `@member`'s rank, level and experience ;"""
        await ctx.reply(file=await rank_work(ctx, member))

    @commands.group()
    async def levels(self, ctx):
        """Group command about Levels, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @levels.command(usage='in/out')
    async def opt(self, ctx, in_or_out: inout_to_10):
        """Opt `in/out` of exp system notifs and all leaderboard presence ;"""
        db.set_value(db.m, ctx.author.id, inlvl=in_or_out)
        ans = f'{ctx.author.display_name} is now opted {in_or_out} of exp-system notifications and being in leaderboards'
        await ctx.reply(content=ans)

    @commands.hybrid_command(
        name='rep',
        brief=Ems.slash,
        description='Give +1 to @member reputation'
    )
    @commands.cooldown(1, 60*60, commands.BucketType.user)
    @app_commands.describe(member='Member to give rep to')
    async def rep(self, ctx, member: Member):
        """Give +1 to `@member`'s reputation ;"""
        if member == ctx.author or member.bot:
            await ctx.reply(content='You can\'t give reputation to yourself or bots')
        else:
            rep = db.inc_value(db.m, member.id, 'rep')
            answer_text = f'Added +1 reputation to **{member.display_name}**: now {rep} reputation'
            await ctx.reply(content=answer_text)

    @tasks.loop(time=time(hour=13, minute=13, tzinfo=timezone.utc))
    async def remove_inactive(self):
        with db.session_scope() as ses:
            for row in ses.query(db.m):
                irene_server = self.bot.get_guild(Sid.irene)
                person = irene_server.get_member(row.id)
                if person is None and datetime.now(timezone.utc) - row.lastseen > timedelta(days=30):
                    ses.delete(row)
                    embed = Embed(colour=0xE6D690)
                    embed.description = f'id = {row.id}'
                    embed.set_author(name=f'{row.name} was removed from datebase')
                    await irene_server.get_channel(Cid.logs).send(embed=embed)

    @remove_inactive.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ExperienceSystem(bot))
