from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member
from discord.ext import commands

from utils import database as db
from utils.checks import is_owner
from utils.var import *
from utils.imgtools import url_to_img, img_to_file, get_text_wh

from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFilter, ImageFont

if TYPE_CHECKING:
    pass


async def welcome_image(session, member):
    image = Image.open('./media/welcome.png', mode='r')
    avatar = await url_to_img(session, member.display_avatar.url)
    avatar = avatar.resize((round(image.size[1] * 1.00), round(image.size[1] * 1.00)))

    width, height = image.size
    new_width, new_height = avatar.size

    left = int((width - new_width) / 2)
    top = int((height - new_height) / 2)

    mask_im = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, new_width, new_height), fill=255)
    mask_im.save('./media/mask_circle.jpg', quality=95)

    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
    mask_im_blur.save('./media/mask_circle_blur.jpg', quality=95)

    image.paste(avatar, (left, top), mask_im)

    font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 80)
    d = ImageDraw.Draw(image)
    msg = member.display_name
    w1, h1 = get_text_wh(msg, font)
    d.text(((width - w1) / 1 - 10, (height - h1) / 1 - 10), msg, fill=(255, 255, 255), font=font)

    font = ImageFont.truetype('./media/MonsieurLaDoulaise-Regular.ttf', 90)
    msg = "Welcome !"
    w2, h2 = get_text_wh(msg, font)
    d.text(((width - w2) / 1 - 10, (height - h2) / 1 - 10 - h1 - 10), msg, fill=(255, 255, 255), font=font)
    return image


async def welcome_message(session, member, back=0):
    image = await welcome_image(session, member)

    content_text = '**💜 Welcome to Aluerie ❤\'s server, {0} !** {1} {1} {1}\n'.format(
        member.mention, Ems.peepoWave)

    if back:
        content_text = '**💜 Welcome BACK to Aluerie ❤\'s server, {0} !** {1} {1} {1}\n'.format(
            member.mention, Ems.DankLove)

    if not member.bot:
        description = \
            f'**💜 {umntn(Uid.alu)} is our princess ' \
            f'and I\'m her bot ! {Ems.peepoRose} {Ems.peepoRose} {Ems.peepoRose}**\n'\
            f'1️⃣ Read the rules and useful info in <#724996010169991198> {Ems.PepoG}\n'\
            f'2️⃣ Choose some fancy roles in <#725941486063190076> {Ems.peepoNiceDay}\n'\
            f'3️⃣ Go to <#702561315478044807> or any other channel and chat with us {Ems.peepoComfy}\n'\
            f'4️⃣ Use `$help` in <#724986090632642653> to see insane Aluerie\'s coding skills {Ems.PogChampPepe}\n'\
            f'5️⃣ Have fun ! (but follow the rules {Ems.bubuGun} {Ems.bubuGun} {Ems.bubuGun} )'
    else:
        description = f'Chat, it\'s a new bot in our server. Use it wisely {Ems.peepoComfy}'

    em = Embed(
        color=Clr.prpl,
        description=description
    ).set_footer(text=f"With love, {member.guild.me.display_name}")
    return content_text, em, img_to_file(image)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = self.bot.get_guild(Sid.alu)
        if member.guild != guild:
            return
        bots_role = guild.get_role(Rid.bots)
        back = 0
        if member.bot:
            await member.add_roles(bots_role)
            await member.edit(nick=f"{member.display_name} | ")
        else:
            if db.session.query(db.m).filter_by(id=member.id).first() is None:
                db.add_row(db.m, member.id, name=member.name, lastseen=datetime.now(timezone.utc))
            else:
                back = 1
                db.set_value(db.m, member.id, name=member.name, lastseen=datetime.now(timezone.utc))
            for role_id in Rid.category_roles_ids:
                role = guild.get_role(role_id)
                await member.add_roles(role)
            if back == 0:
                role = guild.get_role(Rid.level_zero)
                await member.add_roles(role)

        content_text, embed, image_file = await welcome_message(self.bot.ses, member, back=back)
        await self.bot.get_channel(Cid.welcome).send(content=content_text, embed=embed, file=image_file)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != Sid.alu:
            return
        em = Embed(
            color=0x000000,
            description='{0} {0} {0}'.format(Ems.FeelsRainMan)
        ).set_author(
            name='{0} just left the server'.format(member.display_name),
            icon_url=member.display_avatar.url
        ).set_footer(
            text=f"With love, {member.guild.me.display_name}"
        )
        msg = await self.bot.get_channel(Cid.welcome).send(embed=em)
        await msg.add_reaction(Ems.FeelsRainMan)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member: Member):
        if guild.id != Sid.alu:
            return
        em = Embed(
            color=0x800000,
            description='{0} {0} {0}'.format(Ems.peepoPolice)
        ).set_author(
            name=f'{member.display_name} was just banned from the server',
            icon_url=member.display_avatar.url
        ).set_footer(text=f"With love, {guild.me.display_name}")
        msg = await self.bot.get_channel(Cid.welcome).send(embed=em)
        await msg.add_reaction(Ems.peepoPolice)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        if guild.id != Sid.alu:
            return
        em = Embed(
            color=0x00ff7f,
            description='{0} {0} {0}'.format(Ems.PogChampPepe)
        ).set_author(
            name=f'{member.display_name} was just unbanned from the server',
            icon_url=member.display_avatar.url
        ).set_footer(text=f"With love, {guild.me.display_name}")
        msg = await self.bot.get_channel(Cid.welcome).send(embed=em)
        await msg.add_reaction(Ems.PogChampPepe)


class Milestone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Sid.alu:
            return
        mile_rl = member.guild.get_role(Rid.milestone)
        milestone_achieved = db.get_value(db.b, Sid.alu, 'milestone_achieved')
        amount_members = member.guild.member_count

        if amount_members > milestone_achieved and amount_members % 50 == 0:
            milestone_achieved = amount_members
            db.set_value(db.b, Sid.alu, milestone_achieved=milestone_achieved)
            await member.add_roles(mile_rl)

            em = Embed(
                color=Clr.prpl,
                title=f'{Ems.PogChampPepe} Milestone reached !',
                description=
                f'Our server reached {milestone_achieved} members ! '
                f'{member.mention} is our latest milestone member '
                f'who gets a special lucky {mile_rl.mention} role. Congrats !'
            ).set_thumbnail(
                url=member.guild.icon_url
            ).set_footer(
                text=f"With love, {member.guild.me.display_name}"
            )
            await self.bot.get_channel(Cid.welcome).send(embed=em)

    @is_owner()
    @commands.command(hidden=True)
    async def welcome_preview(self, ctx, member: Member = None):
        """Get a rendered welcome message for a `{@user}`;"""
        mbr = member or ctx.message.author
        content_text, embed, image_file = await welcome_message(self.bot.ses, mbr)
        await ctx.reply(content=content_text, embed=embed, file=image_file)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
    await bot.add_cog(Milestone(bot))
