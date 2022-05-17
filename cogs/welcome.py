from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member
from discord.ext import commands

from utils import database as db
from utils.var import *
from utils.imgtools import url_to_img, img_to_file

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
    # right = int((width + new_width) / 2)
    # bottom = int((height + new_height) / 2)

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
    w1, h1 = d.textsize(msg, font=font)
    d.text(((width - w1) / 1 - 10, (height - h1) / 1 - 10), msg, fill=(255, 255, 255), font=font)

    font = ImageFont.truetype('./media/MonsieurLaDoulaise-Regular.ttf', 90)
    d = ImageDraw.Draw(image)
    msg = "Welcome !"
    w2, h2 = d.textsize(msg, font=font)
    d.text(((width - w2) / 1 - 10, (height - h2) / 1 - 10 - h1 - 10), msg, fill=(255, 255, 255), font=font)
    return image


async def welcome_message(session, member, back=0):
    image = await welcome_image(session, member)

    content_text = '**💜 Welcome to Irène Adler ❤\'s server, {0} !** {1} {1} {1}\n'.format(
        member.mention, Ems.peepoWave)

    if back:
        content_text = '**💜 Welcome BACK to Irène Adler ❤\'s server, {0} !** {1} {1} {1}\n'.format(
            member.mention, Ems.peepoLove)

    if not member.bot:
        description = \
            f'**💜 {umntn(Uid.irene)} is our princess ' \
            f'and I\'m her bot ! {Ems.peepoRose} {Ems.peepoRose} {Ems.peepoRose}**\n'\
            f'1️⃣ Read the rules and useful info in <#724996010169991198> {Ems.PepoG}\n'\
            f'2️⃣ Choose some fancy roles in <#725941486063190076> {Ems.peepoNiceDay}\n'\
            f'3️⃣ Go to <#702561315478044807> or any other channel and chat with us {Ems.peepoComfy}\n'\
            f'4️⃣ Use `$help` in <#724986090632642653> to see insane Irene\'s coding skills {Ems.PogChampPepe}\n'\
            f'5️⃣ Have fun ! (but follow the rules {Ems.bubuGun} {Ems.bubuGun} {Ems.bubuGun} )'
    else:
        description = 'Chat, it\'s a new bot in our server. Use it wisely {0}'.format(Ems.peepoComfy)

    embed = Embed(color=Clr.prpl)
    embed.description = description
    embed.set_footer(text=f"With love, {member.guild.me.display_name}")
    return content_text, embed, img_to_file(image)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def welcome_preview(self, ctx, member: Member = None):
        mbr = member or ctx.message.author
        content_text, embed, image_file = await welcome_message(self.bot.ses, mbr)
        await ctx.reply(content=content_text, embed=embed, file=image_file)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        irene_server = self.bot.get_guild(Sid.irene)
        if member.guild != irene_server:
            return
        bots_role = irene_server.get_role(Rid.bots)
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
                role = irene_server.get_role(role_id)
                await member.add_roles(role)
            if back == 0:
                role = irene_server.get_role(Rid.level_zero)
                await member.add_roles(role)

        content_text, embed, image_file = await welcome_message(self.bot.ses, member, back=back)
        await self.bot.get_channel(Cid.welcome).send(content=content_text, embed=embed, file=image_file)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != Sid.irene:
            return
        author_text = '{0} just left the server'.format(member.display_name)
        embed = Embed(color=0x000000).set_author(name=author_text, icon_url=member.display_avatar.url)
        embed.description = '{0} {0} {0}'.format(Ems.FeelsRainMan)
        embed.set_footer(text=f"With love, {member.guild.me.display_name}")
        msg = await self.bot.get_channel(Cid.welcome).send(embed=embed)
        await msg.add_reaction(Ems.FeelsRainMan)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member: Member):
        if guild.id != Sid.irene:
            return
        author_text = f'{member.display_name} was just banned from the server'
        em = Embed(color=0x800000).set_author(name=author_text, icon_url=member.display_avatar.url)
        em.description = '{0} {0} {0}'.format(Ems.peepoPolice)
        em.set_footer(text=f"With love, {guild.me.display_name}")
        msg = await self.bot.get_channel(Cid.welcome).send(embed=em)
        await msg.add_reaction(Ems.peepoPolice)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        if guild.id != Sid.irene:
            return
        author_text = f'{member.display_name} was just unbanned from the server'
        em = Embed(color=0x00ff7f).set_author(name=author_text, icon_url=member.display_avatar.url)
        em.description = '{0} {0} {0}'.format(Ems.PogChampPepe)
        em.set_footer(text="With love, " + guild.me.display_name)
        msg = await self.bot.get_channel(Cid.welcome).send(embed=em)
        await msg.add_reaction(Ems.PogChampPepe)


class Milestone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Sid.irene:
            return
        irene_guild = member.guild
        mile_rl = irene_guild.get_role(Rid.milestone)
        milestone_achieved = db.get_value(db.g, Sid.irene, 'milestone_achieved')
        amount_members = irene_guild.member_count

        if amount_members > milestone_achieved and amount_members % 50 == 0:
            milestone_achieved = amount_members
            db.set_value(db.g, Sid.irene, milestone_achieved=milestone_achieved)
            await member.add_roles(mile_rl)

            em = Embed(color=Clr.prpl, title=f'{Ems.PogChampPepe} Milestone reached !')
            em.description = \
                f'Our server reached {milestone_achieved} members ! ' \
                f'{member.mention} is our latest milestone member '\
                f'who gets a special lucky {mile_rl.mention} role. Congrats !'
            em.set_thumbnail(url=member.guild.icon_url)
            em.set_footer(text=f"With love, {member.guild.me.display_name}")
            await self.bot.get_channel(Cid.welcome).send(embed=em)


class WelcomeAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'AdminTools'

    @commands.is_owner()
    @commands.command()
    async def welcome_preview(self, ctx, member: Member = None):
        """Get a rendered welcome message for a `{@user}`;"""
        mbr = member or ctx.message.author
        content_text, embed, image_file = await welcome_message(self.bot.ses, mbr)
        await ctx.reply(content=content_text, embed=embed, file=image_file)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
    await bot.add_cog(Milestone(bot))
