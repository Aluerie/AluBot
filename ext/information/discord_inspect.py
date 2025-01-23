"""DISCORD INSPECTIONS.

Maybe a bad name, but it is supposed to contain features to get information that can be gotten directly from discord,
but for some reason it is not easily available in the app UI itself.

Such as view somebody's avatar picture.
This information is public and yet there is no easy way to get it
without using tools like discord bots or css inspection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from PIL import Image

from utils import const

from ._base import InfoCog

if TYPE_CHECKING:
    from bot import AluBot


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
        """Embed for view user avatar related commands."""
        embed = discord.Embed(
            colour=user.colour,
            title=f"Avatar for {user.display_name}",
        ).set_image(url=user.display_avatar.url)
        return embed

    async def view_user_avatar(self, interaction: discord.Interaction, user: discord.User) -> None:
        """Callback for context menu command "View User Avatar"."""
        embed = self.get_avatar_embed_worker(user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    profile_group = app_commands.Group(
        name="profile",
        description="\N{IDENTIFICATION CARD} View discord user profile related data.",
    )

    @profile_group.command(name="avatar")
    async def profile_avatar(self, interaction: discord.Interaction[AluBot], user: discord.User) -> None:
        """\N{IDENTIFICATION CARD} View @user's avatar picture.

        Parameters
        ----------
        user:
            User to view avatar of.
        """
        await interaction.response.send_message(embed=self.get_avatar_embed_worker(user))

    @profile_group.command(name="banner")
    async def profile_banner(self, interaction: discord.Interaction[AluBot], user: discord.User) -> None:
        """\N{IDENTIFICATION CARD} View @user's banner picture.

        Parameters
        ----------
        user:
            User to view banner of.
        """
        # banner and accent_colour info is only available via Client.fetch_user().
        # https://discordpy.readthedocs.io/en/latest/api.html?highlight=user#discord.User.banner
        fetched_user = await self.bot.fetch_user(user.id)

        if banner := fetched_user.banner:
            # user set an image as a banner
            embed = discord.Embed(
                colour=user.colour,
                title=f"Banner for {user.display_name}",
            ).set_image(url=banner.url)
            await interaction.response.send_message(embed=embed)
        elif accent_colour := fetched_user.accent_colour:
            # user set some colour as a banner
            img = Image.new("RGB", (300, 300), accent_colour.to_rgb())
            file = interaction.client.transposer.image_to_file(img, filename="colour.png")
            embed = discord.Embed(
                colour=user.colour,
                title=f"Banner for {user.display_name}",
            ).set_image(url=f"attachment://{file.filename}")
            await interaction.response.send_message(embed=embed)
        else:
            # user does not have a banner set
            embed = discord.Embed(
                colour=user.colour,
                title=f"Banner for {user.display_name}",
                description="The user did not set a profile banner nor explicitly set their profile accent colour.",
            )
            await interaction.response.send_message(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DiscordInspect(bot))
