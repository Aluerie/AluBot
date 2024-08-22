"""The features in this file are about getting a basic information from directly discord that
there is seemingly no easy way of getting in the app's UI itself (but would be nice).

For example, a command `/profile picture` will get an avatar picture for a mentioned @member.
This information is public and yet there is no easy way to get it without using tools like discord bots.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from utils import const

from ._base import InfoCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class DiscordInspect(InfoCog, name="Inspect Discord Info.", emote=const.Emote.PepoG):
    """Commands to inspect Discord members/roles/servers/etc and get more info about them."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ctx_menu_avatar = app_commands.ContextMenu(
            name="View User Avatar",
            callback=self.view_user_avatar,
        )

    @override
    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu_avatar)

    @override
    async def cog_unload(self) -> None:
        c = self.ctx_menu_avatar
        self.bot.tree.remove_command(c.name, type=c.type)

    def get_avatar_embed_worker(
        self,
        # ctx: AluGuildContext | discord.Interaction[AluBot],
        user: discord.User,
    ) -> discord.Embed:
        """"""
        embed = discord.Embed(colour=user.colour, title=f"Avatar for {user.display_name}").set_image(
            url=user.display_avatar.url
        )
        return embed

    async def view_user_avatar(self, interaction: discord.Interaction, user: discord.User) -> None:
        embed = self.get_avatar_embed_worker(user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.hybrid_group(name="profile")
    async def profile_group(self, ctx: AluContext) -> None:
        """Profile Commands."""
        await ctx.send_help(ctx.command)

    @profile_group.command(name="avatar")
    @app_commands.describe(user="User to view avatar of;")
    async def profile_avatar(self, ctx: AluContext, *, user: discord.User) -> None:
        """View @user's avatar picture."""
        await ctx.reply(embed=self.get_avatar_embed_worker(user))

    @profile_group.command(name="banner")
    @app_commands.describe(user="User to view banner of;")
    async def profile_banner(self, ctx: AluContext, *, user: discord.User) -> None:
        """View @user's banner picture."""
        # banner and accent_colour info is only available via Client.fetch_user().
        # https://discordpy.readthedocs.io/en/latest/api.html?highlight=user#discord.User.banner
        fetched_user = await self.bot.fetch_user(user.id)

        if banner := fetched_user.banner:
            embed = discord.Embed(colour=user.colour, title=f"Banner for {user.display_name}").set_image(url=banner.url)
            await ctx.reply(embed=embed)
        elif accent_colour := fetched_user.accent_colour:
            img = Image.new("RGB", (300, 300), accent_colour.to_rgb())
            file = ctx.bot.transposer.image_to_file(img, filename="colour.png")
            embed = discord.Embed(colour=user.colour, title=f"Banner for {user.display_name}").set_image(
                url=f"attachment://{file.filename}"
            )
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                colour=user.colour,
                title=f"Banner for {user.display_name}",
                description="The user did not set banner nor explicitly set their profile accent colour.",
            )
            await ctx.reply(embed=embed)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(DiscordInspect(bot))
