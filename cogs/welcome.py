from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from utils.checks import is_owner
from utils.const import CATEGORY_ROLES, Colour, Emote, Guild, Role, User

if TYPE_CHECKING:
    from utils import AluBot, AluContext


async def welcome_image(bot: AluBot, member: discord.User | discord.Member):
    image = Image.open('./assets/images/profile/welcome.png', mode='r')
    avatar = await bot.imgtools.url_to_img(member.display_avatar.url)
    avatar = avatar.resize((round(image.size[1] * 1.00), round(image.size[1] * 1.00)))

    width, height = image.size
    new_width, new_height = avatar.size

    left = int((width - new_width) / 2)
    top = int((height - new_height) / 2)

    mask_im = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, new_width, new_height), fill=255)
    mask_im.save('./assets/images/profile/mask_circle.jpg', quality=95)

    mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
    mask_im_blur.save('./assets/images/profile/mask_circle_blur.jpg', quality=95)

    image.paste(avatar, (left, top), mask_im)

    font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 80)
    d = ImageDraw.Draw(image)
    msg = member.display_name
    w1, h1 = bot.imgtools.get_text_wh(msg, font)
    d.text(((width - w1) / 1 - 10, (height - h1) / 1 - 10), msg, fill=(255, 255, 255), font=font)

    font = ImageFont.truetype('./assets/fonts/MonsieurLaDoulaise-Regular.ttf', 90)
    msg = "Welcome !"
    w2, h2 = bot.imgtools.get_text_wh(msg, font)
    d.text(((width - w2) / 1 - 10, (height - h2) / 1 - 10 - h1 - 10), msg, fill=(255, 255, 255), font=font)
    return image


async def welcome_message(
    bot: AluBot, member: discord.Member | discord.User, back: bool = False
) -> Tuple[str, discord.Embed, discord.File]:
    image = await welcome_image(bot, member)

    if back:
        wave_emote, the_word = Emote.DankLove, 'BACK'
    else:
        wave_emote, the_word = Emote.peepoWave, ''
    content_text = '**💜 Welcome {2} to Aluerie ❤\'s server, {0} !** {1} {1} {1}\n'.format(
        member.mention, wave_emote, the_word
    )

    if not member.bot:
        description = (
            f'**💜 {User.alu} is our princess '
            f'and I\'m her bot ! {Emote.peepoRose} {Emote.peepoRose} {Emote.peepoRose}**\n'
            f'1️⃣ Read the rules and useful info in <#724996010169991198> {Emote.PepoG}\n'
            f'2️⃣ Choose some fancy roles in <#725941486063190076> {Emote.peepoNiceDay}\n'
            f'3️⃣ Go to <#702561315478044807> or any other channel and chat with us {Emote.peepoComfy}\n'
            f'4️⃣ Use `$help` in <#724986090632642653> to see insane Aluerie\'s coding skills {Emote.PogChampPepe}\n'
            f'5️⃣ Have fun ! (but follow the rules {Emote.bubuGun} {Emote.bubuGun} {Emote.bubuGun} )'
        )
    else:
        description = f'Chat, it\'s a new bot in our server. Use it wisely {Emote.peepoComfy}'

    e = discord.Embed(description=description, color=Colour.prpl())
    e.set_footer(text=f"With love, {bot.community.guild.me.display_name}")
    return content_text, e, bot.imgtools.img_to_file(image)


class Welcome(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = self.bot.community.guild
        if member.guild != guild:
            return
        back = False
        if member.bot:
            await member.add_roles(self.bot.community.bots_role)
            await member.edit(nick=f"{member.display_name} | ")
        else:
            query = """ INSERT INTO users (id, name) 
                        VALUES ($1, $2) 
                        ON CONFLICT DO NOTHING
                        RETURNING True;
                    """
            value = await self.bot.pool.fetchval(query, member.id, member.name)
            back = value is not True

            for role_id in CATEGORY_ROLES:
                role: discord.Role = guild.get_role(role_id)  # type: ignore
                await member.add_roles(role)
            if not back:
                role: discord.Role = guild.get_role(Role.level_zero.id)  # type: ignore
                await member.add_roles(role)

        content_text, embed, image_file = await welcome_message(self.bot, member, back=back)
        await self.bot.community.welcome.send(content=content_text, embed=embed, file=image_file)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != Guild.community:
            return
        e = discord.Embed(description='{0} {0} {0}'.format(Emote.FeelsRainMan), colour=0x000000)
        e.set_author(name='{0} just left the server'.format(member.display_name), icon_url=member.display_avatar.url)
        e.set_footer(text=f"With love, {member.guild.me.display_name}")
        msg = await self.bot.community.welcome.send(embed=e)
        await msg.add_reaction(Emote.FeelsRainMan)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        if guild.id != Guild.community:
            return
        e = discord.Embed(description='{0} {0} {0}'.format(Emote.peepoPolice), color=0x800000)
        e.set_author(name=f'{member.display_name} was just banned from the server', icon_url=member.display_avatar.url)
        e.set_footer(text=f"With love, {guild.me.display_name}")
        msg = await self.bot.community.welcome.send(embed=e)
        await msg.add_reaction(Emote.peepoPolice)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.Member):
        if guild.id != Guild.community:
            return
        e = discord.Embed(description='{0} {0} {0}'.format(Emote.PogChampPepe), color=0x00FF7F)
        e.set_author(
            name=f'{member.display_name} was just unbanned from the server', icon_url=member.display_avatar.url
        )
        e.set_footer(text=f"With love, {guild.me.display_name}")
        msg = await self.bot.community.welcome.send(embed=e)
        await msg.add_reaction(Emote.PogChampPepe)

    @is_owner()
    @commands.command(hidden=True)
    async def welcome_preview(self, ctx: AluContext, member: Optional[discord.Member]):
        """Get a rendered welcome message for a `{@user}`."""
        person = member or ctx.author
        content_text, embed, image_file = await welcome_message(self.bot, person)
        await ctx.reply(content=content_text, embed=embed, file=image_file)


async def setup(bot: AluBot):
    await bot.add_cog(Welcome(bot))
