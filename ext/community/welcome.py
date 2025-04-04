from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bot import AluCog
from utils import const

if TYPE_CHECKING:
    from bot import AluBot, AluContext

    class SendWelcomeKwargs(TypedDict):
        content: str
        embed: discord.Embed
        file: discord.File

    class WelcomeMemberRow(TypedDict):
        roles: list[int]
        name: str


class Welcome(AluCog):
    async def welcome_image(self, member: discord.User | discord.Member) -> Image.Image:
        avatar_asset = await self.bot.transposer.url_to_image(member.display_avatar.url)

        def build_image() -> Image.Image:
            canvas = Image.open("./assets/images/profile/welcome.png", mode="r")
            avatar = avatar_asset.resize((round(canvas.size[1] * 1.00), round(canvas.size[1] * 1.00)))

            canvas_w, canvas_h = canvas.size
            avatar_w, avatar_h = avatar.size

            left = int((canvas_w - avatar_w) / 2)
            top = int((canvas_h - avatar_h) / 2)

            mask_im = Image.new("L", avatar.size, 0)
            draw = ImageDraw.Draw(mask_im)
            draw.ellipse((0, 0, avatar_w, avatar_h), fill=255)
            mask_im.save("./assets/images/profile/mask_circle.jpg", quality=95)

            mask_im_blur = mask_im.filter(ImageFilter.GaussianBlur(5))
            mask_im_blur.save("./assets/images/profile/mask_circle_blur.jpg", quality=95)

            canvas.paste(avatar, (left, top), mask_im)

            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 80)
            d = ImageDraw.Draw(canvas)
            msg = member.display_name
            w1, h1 = self.bot.transposer.get_text_wh(msg, font)
            d.text(((canvas_w - w1) / 1 - 10, (canvas_h - h1) / 1 - 10), msg, fill=(255, 255, 255), font=font)

            font = ImageFont.truetype("./assets/fonts/MonsieurLaDoulaise-Regular.ttf", 90)
            msg = "Welcome !"
            w2, h2 = self.bot.transposer.get_text_wh(msg, font)
            d.text(((canvas_w - w2) / 1 - 10, (canvas_h - h2) / 1 - 10 - h1 - 10), msg, fill=(255, 255, 255), font=font)
            return canvas

        return await asyncio.to_thread(build_image)

    async def get_send_welcome_kwargs(self, member: discord.Member, back: bool = False) -> SendWelcomeKwargs:
        image = await self.welcome_image(member)

        if back:
            wave_emote, the_word = const.Emote.DankLove, "BACK"
        else:
            wave_emote, the_word = const.Emote.DankHey, ""
        content_text = (
            f"**💜 Welcome {the_word} to Aluerie's server, {member.mention} !** {wave_emote} {wave_emote} {wave_emote}"
        )

        if not member.bot:
            description = (
                f"**💜 {const.User.aluerie} is our princess and I'm her bot ! {const.Emote.peepoRoseDank}**\n"
                f"{const.DIGITS[1]} Read the rules and useful info in {const.Channel.rules} {const.Emote.PepoG}\n"
                f"{const.DIGITS[2]} Choose some fancy roles in {const.Channel.role_selection} {const.Emote.peepoNiceDay}\n"  # noqa: E501
                f"{const.DIGITS[3]} Go to {const.Channel.general} or any other channel and chat with us {const.Emote.peepoComfy}\n"  # noqa: E501
                f"{const.DIGITS[4]} Check out <id:customize>, <id:guide>, <id:browse> {const.Emote.DankApprove}\n"
                # f"{const.DIGITS[5]} Use `/help` in {const.Channel.bot_spam} to see insane Aluerie's coding skills {const.Emote.PogChampPepe}\n"  # noqa: E501, ERA001
                f"{const.DIGITS[5]} Have fun ! (but follow the rules {const.Emote.bubuGun} )"
            )
        else:
            description = f"Chat, it's a new bot in our server. Use it wisely {const.Emote.peepoComfy}"

        embed = discord.Embed(color=const.Color.prpl, description=description)
        return {"content": content_text, "embed": embed, "file": self.bot.transposer.image_to_file(image)}

    @commands.Cog.listener("on_member_join")
    async def welcome_new_member(self, member: discord.Member) -> None:
        """Welcome new member.

        This listener also gives back to old returning members their roles and old nickname if any.
        """
        if member.guild.id != const.Guild.community:
            return

        back = False
        if member.bot:
            await member.add_roles(self.bot.community.bots_role)
        else:
            # human person

            # 1. add category roles
            category_roles = (role for role_id in const.CATEGORY_ROLES if (role := member.guild.get_role(role_id)))
            await member.add_roles(*category_roles)

            # 2. if it's returning person - give them their old roles, else give level 0 role
            # note: roles are kept updated by listener in this cog
            # note: nickname (name) is updated by a listener in community logger cog
            query = """
                INSERT INTO community_members (id, name)
                VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE
                    SET last_seen = (now() at time zone 'utc')
                RETURNING roles, name;
            """  # ^^^ https://stackoverflow.com/a/37543015/19217368
            # None if new person, record-dict otherwise
            new_row: WelcomeMemberRow | None = await self.bot.pool.fetchval(query, member.id, member.name)

            if bool(new_row):
                # returning person
                # autorole give back roles
                autorole_roles = (role for role_id in new_row["roles"] if (role := member.guild.get_role(role_id)))
                await member.add_roles(*autorole_roles)
                # give back their nickname
                await member.edit(nick=new_row["name"])
            # new person
            elif role := member.guild.get_role(const.Role.level_zero):
                await member.add_roles(role)

        send_kwargs = await self.get_send_welcome_kwargs(member, back=back)
        await self.bot.community.welcome.send(**send_kwargs)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != const.Guild.community:
            return
        embed = discord.Embed(color=0x000000).set_author(
            name=f"{member.display_name} just left the server",
            icon_url=member.display_avatar.url,
        )
        message = await self.bot.community.welcome.send(
            f"{const.Emote.SmogeInTheRain} {const.Emote.SmogeInTheRain} {const.Emote.SmogeInTheRain}", embed=embed
        )
        await message.add_reaction(const.Emote.SmogeInTheRain)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member) -> None:
        if guild.id != const.Guild.community:
            return
        embed = discord.Embed(color=0x800000).set_author(
            name=f"{member.display_name} was just banned from the server",
            icon_url=member.display_avatar.url,
        )
        message = await self.bot.community.welcome.send(
            f"{const.Emote.peepoPolice} {const.Emote.peepoPolice} {const.Emote.peepoPolice}", embed=embed
        )
        await message.add_reaction(const.Emote.peepoPolice)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.Member) -> None:
        if guild.id != const.Guild.community:
            return
        embed = discord.Embed(color=0x00FF7F).set_author(
            name=f"{member.display_name} was just unbanned from the server",
            icon_url=member.display_avatar.url,
        )
        msg = await self.bot.community.welcome.send(
            f"{const.Emote.PogChampPepe} {const.Emote.PogChampPepe} {const.Emote.PogChampPepe}", embed=embed
        )
        await msg.add_reaction(const.Emote.PogChampPepe)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def welcome_preview(self, ctx: AluContext, member: discord.Member = commands.Author) -> None:
        """Get a rendered welcome message for a `{@user}`.

        Used for testing purposes.
        """
        send_kwargs = await self.get_send_welcome_kwargs(member)
        await ctx.reply(**send_kwargs)

    @commands.Cog.listener("on_member_update")
    async def update_member_autoroles(self, before: discord.Member, after: discord.Member) -> None:
        """Update Member AutoRoles.

        We need to keep roles column in community_members table updated
        """
        if before.guild.id != const.Guild.community:
            return

        roles_to_insert = [role.id for role in after.roles if role.id not in const.CATEGORY_ROLES]
        query = "UPDATE community_members SET roles = $1::bigint[] WHERE id = $2"
        await self.bot.pool.execute(query, roles_to_insert, after.id)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Welcome(bot))
